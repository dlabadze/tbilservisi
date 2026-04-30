import logging
from odoo import models, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    @api.ondelete(at_uninstall=False)
    def _unlink_except_done_or_cancel(self):
        if not self._context.get('force_delete'):
            return super()._unlink_except_done_or_cancel()

    def _create_and_process_reverse_move_lines(self):
        reverse_move_lines = self.env['stock.move.line']
        reversed_count = 0
        
        for ml in self:
            if ml.state != 'done':
                continue
            if not ml.product_id.is_storable:
                continue
            if ml.quantity <= 0:
                continue
            
            try:
                # Create reverse stock.move first
                reverse_move_vals = {
                    'name': _('Reverse: %s') % (ml.move_id.name or ml.reference or 'Move Line'),
                    'product_id': ml.product_id.id,
                    'product_uom_qty': ml.quantity,
                    'product_uom': ml.product_uom_id.id,
                    'location_id': ml.location_dest_id.id,
                    'location_dest_id': ml.location_id.id,
                    'company_id': ml.company_id.id,
                    'state': 'draft',
                    'origin': _('Reverse deletion of %s') % (ml.reference or ml.id),
                }
                reverse_move = self.env['stock.move'].sudo().create(reverse_move_vals)
                
                # Create reverse move line with swapped locations
                reverse_ml_vals = {
                    'move_id': reverse_move.id,
                    'product_id': ml.product_id.id,
                    'product_uom_id': ml.product_uom_id.id,
                    'quantity': ml.quantity,
                    'location_id': ml.location_dest_id.id,  
                    'location_dest_id': ml.location_id.id,
                    'lot_id': ml.lot_id.id if ml.lot_id else False,
                    'package_id': ml.result_package_id.id if ml.result_package_id else False,
                    'result_package_id': ml.package_id.id if ml.package_id else False,
                    'owner_id': ml.owner_id.id if ml.owner_id else False,
                    'company_id': ml.company_id.id,
                    'state': 'draft',
                }
                reverse_ml = self.env['stock.move.line'].sudo().with_context(inventory_mode=True).create(reverse_ml_vals)                
                # Set move to confirmed state
                reverse_move.write({'state': 'confirmed'})
                
                # Process the reverse move line through _action_done to update quants
                reverse_ml._action_done()
                
                # Mark move as done
                reverse_move.write({'state': 'done'})
                
                reverse_move_lines |= reverse_ml
                reversed_count += 1
                
                _logger.info(
                    "Created and processed reverse move line %s for original %s: %s x %s from %s to %s",
                    reverse_ml.id, ml.id, ml.quantity, ml.product_id.display_name,
                    ml.location_dest_id.complete_name, ml.location_id.complete_name
                )
            except Exception as e:
                _logger.warning(
                    "Failed to create reverse move line for %s: %s",
                    ml.id, str(e)
                )
                raise UserError(_("Failed to create reverse operation for move line %s: %s") % (ml.id, str(e)))
        
        return reverse_move_lines, reversed_count

    def action_clean_related_data_force(self):
        selected_lines = self
        if not selected_lines:
            raise UserError(_("No records selected."))
        
        related_moves = selected_lines.mapped('move_id')
        move_ids = related_moves.ids
        
        # Get related records
        related_account_moves = self.env['account.move'].search([
            ('stock_move_id', 'in', move_ids)
        ])
        account_move_ids = related_account_moves.ids
        
        related_account_move_lines = self.env['account.move.line']
        if account_move_ids:
            related_account_move_lines = self.env['account.move.line'].search([
                ('move_id', 'in', account_move_ids)
            ])
        
        related_svls = self.env['stock.valuation.layer'].search([
            ('stock_move_id', 'in', move_ids)
        ])
        
        # Check for hashed entries
        if related_account_move_lines:
            hashed_lines = related_account_move_lines.filtered(lambda l: l.move_id.inalterable_hash)
            if hashed_lines:
                raise UserError(_(
                    "Cannot delete: Related journal items belong to locked entries:\n"
                    "Journal Entries: %s"
                ) % ', '.join(hashed_lines.mapped('move_id.name')))
        
        # CREATE AND PROCESS REVERSE MOVE LINES FOR  QUANTS
        reverse_move_lines, reversed_quants = selected_lines._create_and_process_reverse_move_lines()
        reverse_moves = reverse_move_lines.mapped('move_id')
        _logger.info("Created and processed %s reverse move lines to update quants", reversed_quants)
        
        cr = self.env.cr
        
        #Unreconcile account move lines
        if related_account_move_lines:
            aml_ids = related_account_move_lines.ids
            # Delete reconciliations
            cr.execute("""
                DELETE FROM account_partial_reconcile
                WHERE debit_move_id IN %s OR credit_move_id IN %s
            """, (tuple(aml_ids), tuple(aml_ids)))
            
            # Clear full_reconcile_id
            cr.execute("""
                UPDATE account_move_line 
                SET full_reconcile_id = NULL, reconciled = FALSE
                WHERE id IN %s
            """, (tuple(aml_ids),))
        
        # Reset account.move state to 'draft'
        if account_move_ids:
            cr.execute("""
                UPDATE account_move 
                SET state = 'draft'
                WHERE id IN %s AND state = 'posted'
            """, (tuple(account_move_ids),))
        
        # Reset stock.move state to 'cancel' or 'draft'
        if move_ids:
            cr.execute("""
                UPDATE stock_move 
                SET state = CASE 
                    WHEN state = 'done' THEN 'cancel'
                    WHEN state != 'cancel' THEN 'draft'
                    ELSE state
                END
                WHERE id IN %s
            """, (tuple(move_ids),))
        
        cr.commit()
        
        self.env.registry.clear_cache()
        selected_lines = self.browse(selected_lines.ids)
        related_moves = self.env['stock.move'].browse(move_ids)
        related_account_moves = self.env['account.move'].browse(account_move_ids)
        if related_account_move_lines:
            related_account_move_lines = self.env['account.move.line'].browse(related_account_move_lines.ids)
        
        #Delete
        deleted_counts = {'aml': 0, 'svl': 0, 'sml': 0, 'quants_reversed': reversed_quants}
        
        if related_account_move_lines:
            deleted_counts['aml'] = len(related_account_move_lines)
            related_account_move_lines.sudo().with_context(tracking_disable=True).unlink()
        
        if related_svls:
            deleted_counts['svl'] = len(related_svls)
            related_svls.sudo().unlink()
        
        deleted_counts['sml'] = len(selected_lines)
        selected_lines.with_context(force_delete=True).unlink()
        
        # Delete the reverse move lines and their stock.moves
        if reverse_move_lines:
            # Reset reverse moves state
            if reverse_moves:
                cr.execute("""
                    UPDATE stock_move 
                    SET state = 'cancel'
                    WHERE id IN %s
                """, (tuple(reverse_moves.ids),))
                self.env.registry.clear_cache()
                reverse_moves = self.env['stock.move'].browse(reverse_moves.ids)
            
            reverse_move_lines.with_context(force_delete=True).unlink()
            reverse_moves.sudo().unlink()
            _logger.info("Deleted %s reverse move lines and %s reverse moves", reversed_quants, len(reverse_moves))
        
        # Delete empty account moves
        if account_move_ids:
            empty_moves = self.env['account.move'].browse(account_move_ids).filtered(
                lambda m: not m.line_ids
            )
            if empty_moves:
                empty_moves.unlink()
        
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Success'),
                'message': _('Deleted: %s stock move line(s), %s journal item(s), %s valuation layer(s). Reversed %s quant operation(s).') % (
                    deleted_counts['sml'], deleted_counts['aml'], deleted_counts['svl'], deleted_counts['quants_reversed']
                ),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_display_related_data(self):
        selected_lines = self
        if not selected_lines:
            raise UserError(_("No records selected."))
        
        related_moves = selected_lines.mapped('move_id')
        move_ids = related_moves.ids
        
        related_account_moves = self.env['account.move'].search([
            ('stock_move_id', 'in', move_ids)
        ])
        account_move_ids = related_account_moves.ids
        
        related_account_move_lines = self.env['account.move.line']
        if account_move_ids:
            related_account_move_lines = self.env['account.move.line'].search([
                ('move_id', 'in', account_move_ids)
            ])
        
        related_svls = self.env['stock.valuation.layer'].search([
            ('stock_move_id', 'in', move_ids)
        ])
        
        # Count quants that will be affected (done move lines with storable products)
        quants_to_reverse = selected_lines.filtered(
            lambda ml: ml.state == 'done' and ml.product_id.is_storable and ml.quantity > 0
        )
        
        # Log detailed analysis
        log_message = "\n" + "=" * 60 + "\n"
        log_message += " [RELATED DATA ANALYSIS] \n"
        log_message += "=" * 60 + "\n"
        log_message += f" 1. Selected Stock Move Lines: {len(selected_lines)} | IDs: {selected_lines.ids}\n"
        log_message += f" 2. Related Stock Moves:        {len(related_moves)} | IDs: {related_moves.ids}\n"
        log_message += f" 3. Valuation Layers:          {len(related_svls)} | IDs: {related_svls.ids}\n"
        log_message += f" 4. Journal Entries:            {len(related_account_moves)} | IDs: {related_account_moves.ids}\n"
        log_message += f" 5. Journal Items:              {len(related_account_move_lines)} | IDs: {related_account_move_lines.ids}\n"
        log_message += f" 6. Quant Operations to Reverse: {len(quants_to_reverse)}\n"
        
        if related_moves:
            log_message += f"\n Stock Moves:\n"
            for move in related_moves:
                log_message += f"   - {move.name} (ID: {move.id}, State: {move.state})\n"
        
        if related_account_moves:
            log_message += f"\n Journal Entries:\n"
            for am in related_account_moves:
                log_message += f"   - {am.name} (ID: {am.id}, State: {am.state})\n"
        
        if related_account_move_lines:
            log_message += f"\n Journal Items:\n"
            for aml in related_account_move_lines[:10]:  # Limit to first 10
                log_message += f"   - {aml.display_name} (ID: {aml.id}, Account: {aml.account_id.code if aml.account_id else 'N/A'}, Reconciled: {aml.reconciled})\n"
            if len(related_account_move_lines) > 10:
                log_message += f"   ... and {len(related_account_move_lines) - 10} more\n"
        
        if related_svls:
            log_message += f"\n Valuation Layers:\n"
            for svl in related_svls[:10]:  # Limit to first 10
                log_message += f"   - ID: {svl.id}, Product: {svl.product_id.display_name}, Qty: {svl.quantity}, Value: {svl.value}\n"
            if len(related_svls) > 10:
                log_message += f"   ... and {len(related_svls) - 10} more\n"
        
        if quants_to_reverse:
            log_message += f"\n Quant Operations to Reverse:\n"
            for ml in quants_to_reverse[:10]:
                qty = ml.product_uom_id._compute_quantity(ml.quantity, ml.product_id.uom_id, rounding_method='HALF-UP')
                log_message += f"   - {ml.product_id.display_name}: {qty} {ml.product_id.uom_id.name} ({ml.location_dest_id.complete_name} -> {ml.location_id.complete_name})\n"
            if len(quants_to_reverse) > 10:
                log_message += f"   ... and {len(quants_to_reverse) - 10} more\n"
        
        log_message += "=" * 60 + "\n"
        
        _logger.info(log_message)
        
        # Display notification
        message_parts = []
        message_parts.append(_("Related Data Analysis:"))
        message_parts.append(_("- Selected Stock Move Lines: %s") % len(selected_lines))
        message_parts.append(_("- Related Stock Moves: %s") % len(related_moves))
        message_parts.append(_("- Valuation Layers: %s") % len(related_svls))
        message_parts.append(_("- Journal Entries: %s") % len(related_account_moves))
        message_parts.append(_("- Journal Items: %s") % len(related_account_move_lines))
        message_parts.append(_("- Quant Operations to Reverse: %s") % len(quants_to_reverse))
        message_parts.append(_("\nCheck server logs for detailed information."))
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Related Data'),
                'message': '\n'.join(message_parts),
                'type': 'info',
                'sticky': True,
            }
        }

