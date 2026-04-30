# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_compare


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    stock_account_ang = fields.Many2one(
        'account.account',
        string='Reconciliation Account',
        domain="[('deprecated', '=', False)]",
        help='Account to use for reconciliation of internal transfer accounting entries. '
             'This account will be used if move_account_ang is not set on individual moves.',
        check_company=True,
    )
    
    analytic_distribution = fields.Json(
        string='Analytic Distribution',
        help='Analytic distribution to be used for reconciliation of internal transfer accounting entries. '
             'This distribution will be used if analytic_distribution is not set on individual moves.',
    )
    
    analytic_precision = fields.Integer(
        store=False,
        default=lambda self: self.env['decimal.precision'].precision_get('Percentage Analytic'),
    )

    def _check_internal_transfer(self):
        """Check if this picking is an internal transfer"""
        return self.picking_type_id.code == 'internal'

    def action_confirm(self):
        """Do not merge moves with the same product only for picking type "ჩამოწერა"."""
        no_merge = self.filtered(lambda p: p.picking_type_id.name == "ჩამოწერა")
        if no_merge:
            no_merge._check_company()
            no_merge.mapped('package_level_ids').filtered(
                lambda pl: pl.state == 'draft' and not pl.move_ids
            )._generate_moves()
            draft_moves = no_merge.move_ids.filtered(lambda m: m.state == 'draft')
            if draft_moves:
                draft_moves._action_confirm(merge=False)
            no_merge.move_ids.filtered(
                lambda m: m.state not in ('draft', 'cancel', 'done')
            )._trigger_scheduler()
            other = self - no_merge
            if other:
                return super(StockPicking, other).action_confirm()
            return True
        return super().action_confirm()

    @api.depends('picking_type_id.code')
    def _compute_is_internal(self):
        """Compute if picking is internal transfer"""
        for picking in self:
            picking.is_internal_transfer = picking._check_internal_transfer()

    is_internal_transfer = fields.Boolean(
        string='Is Internal Transfer',
        compute='_compute_is_internal',
        store=True,
    )
    
    is_reconciled = fields.Boolean(
        string='Is Reconciled',
        compute='_compute_is_reconciled',
        store=True,
        help='Indicates if the accounting entries for this picking have been reconciled.',
    )
    
    @api.depends('move_ids.account_move_ids.line_ids.reconciled', 'state')
    def _compute_is_reconciled(self):
        """Compute if picking accounting entries are reconciled"""
        for picking in self:
            if picking.state != 'done' or not picking._check_internal_transfer():
                picking.is_reconciled = False
                continue
            
            # Check if destination location is inventory loss
            if picking.location_dest_id.usage != 'inventory':
                picking.is_reconciled = False
                continue
            
            # Get all account move lines from stock moves
            all_account_move_lines = self.env['account.move.line']
            for move in picking.move_ids:
                all_account_move_lines |= move._get_all_related_aml()
            
            # Filter only posted moves
            account_move_lines = all_account_move_lines.filtered(
                lambda aml: aml.move_id.state == 'posted'
            )
            
            if not account_move_lines:
                picking.is_reconciled = False
                continue
            
            # Check if all relevant lines are reconciled
            reconciled = True
            for move in picking.move_ids:
                if not move.product_id:
                    continue
                
                product_category = move.product_id.categ_id
                if not product_category:
                    continue
                
                output_account = product_category.property_stock_account_output_categ_id
                if not output_account:
                    continue
                
                # Get account move lines for this move that belong to the output account
                move_aml = move._get_all_related_aml().filtered(
                    lambda aml: aml.move_id.state == 'posted' 
                    and aml.account_id == output_account
                )
                
                # Check if all lines are reconciled
                if move_aml and not all(move_aml.mapped('reconciled')):
                    reconciled = False
                    break
            
            picking.is_reconciled = reconciled

    def action_reconcile_account_entries(self):
        """
        Action to reconcile account move lines created from stock moves.
        Reconciliation logic:
        - Check if destination location is inventory loss (usage == 'inventory')
        - For each product in the operation, find its category
        - Get property_stock_account_output_categ_id from the category
        - Create a journal entry in Miscellaneous journal
        - Reconcile the new journal entry lines with existing account move lines
        """
        self.ensure_one()
        
        if not self._check_internal_transfer():
            raise UserError(_('This action is only available for Internal Transfers.'))
        
        if self.state != 'done':
            raise UserError(_('Picking must be in Done state to reconcile accounting entries.'))
        
        # Check if destination location is inventory loss
        if self.location_dest_id.usage != 'inventory':
            raise UserError(_(
                'Reconciliation is only available for operations where destination location is Inventory Loss. '
                'Current destination location: %s'
            ) % self.location_dest_id.display_name)
        
        # Get Miscellaneous journal (type='general')
        journal = self.env['account.journal'].search([
            ('type', '=', 'general'),
            ('company_id', '=', self.company_id.id)
        ], limit=1)
        
        if not journal:
            raise UserError(_('Miscellaneous journal not found. Please create a journal with type "General".'))
        
        # Get all account move lines from stock moves
        all_account_move_lines = self.env['account.move.line']
        for move in self.move_ids:
            all_account_move_lines |= move._get_all_related_aml()
        
        # Filter only posted moves
        account_move_lines = all_account_move_lines.filtered(
            lambda aml: aml.move_id.state == 'posted' and not aml.reconciled
        )
        
        # Check if already reconciled first
        if self.is_reconciled:
            raise UserError(_('This operation has already been reconciled.'))
        
        if not account_move_lines:
            # Check if there are any account move lines at all
            all_posted_lines = all_account_move_lines.filtered(
                lambda aml: aml.move_id.state == 'posted'
            )
            if all_posted_lines:
                raise UserError(_('All accounting entries for this picking are already reconciled.'))
            else:
                raise UserError(_('No accounting entries found for this picking. Please ensure the picking has been validated and accounting entries have been created.'))
        
        # Group lines by product and get reconciliation accounts
        reconciliation_data = []
        moves_without_account = []
        
        for move in self.move_ids:
            if not move.product_id:
                continue
            
            # Get product category
            product_category = move.product_id.categ_id
            if not product_category:
                continue
            
            # Get output account from category (this will be CREDIT)
            output_account = product_category.property_stock_account_output_categ_id
            if not output_account:
                continue
            
            # Get reconciliation account (this will be DEBIT)
            # If line move_account_ang is empty -> account = picking.stock_account_ang, analytic = picking's
            # If line move_account_ang is set -> account = move.move_account_ang, analytic = move's or picking's
            if move.move_account_ang:
                recon_account = move.move_account_ang
                analytic_dist = move.analytic_distribution or self.analytic_distribution
            else:
                recon_account = self.stock_account_ang
                analytic_dist = self.analytic_distribution
            
            # Validation: if account is empty, add to error list
            if not recon_account:
                moves_without_account.append(move)
                continue
            
            # Get account move lines for this move that belong to the output account
            move_aml = move._get_all_related_aml().filtered(
                lambda aml: aml.move_id.state == 'posted' 
                and aml.account_id == output_account
                and not aml.reconciled
            )
            
            if not move_aml:
                continue
            
            # Calculate total amount (absolute value of balance)
            total_amount = abs(sum(move_aml.mapped('balance')))
            
            if total_amount < 0.01:  # Skip if amount is zero
                continue
            
            reconciliation_data.append({
                'output_account': output_account,
                'recon_account': recon_account,
                'amount': total_amount,
                'lines': move_aml,
                'move': move,
                'analytic_dist': analytic_dist,
            })
        
        # Validation: if any move doesn't have reconciliation account, show error
        if moves_without_account:
            move_names = '\n'.join([f"- {m.name} ({m.product_id.name})" for m in moves_without_account])
            raise UserError(_(
                'Please set reconciliation account for all moves.\n\n'
                'For each move, you must set either:\n'
                '- Move Account (move_account_ang) on the move, OR\n'
                '- Stock Account (stock_account_ang) on the picking\n\n'
                'Moves without account:\n%s'
            ) % move_names)
        
        if not reconciliation_data:
            raise UserError(_(
                'No account move lines found for reconciliation. '
                'Please check that products have stock output accounts configured in their categories.'
            ))
        
        # Create journal entry lines for reconciliation
        move_line_vals = []
        lines_to_reconcile_by_account = {}
        
        for data in reconciliation_data:
            output_account = data['output_account']
            recon_account = data['recon_account']
            amount = data['amount']
            lines = data['lines']
            move = data['move']
            # Analytic: when account was from picking (move_account_ang empty) = picking's; when from move = move's or picking's (stored in data)
            analytic_dist = data['analytic_dist']
            
            # Generate matching number for this reconciliation
            matching_number = f"REC-{self.id}-{move.id}"
            
            # Debit: recon_account (stock_account_ang or move_account_ang)
            # This is the reconciliation account - analytic distribution should only be applied here
            debit_vals = {
                'name': _('Reconciliation for %s') % self.name,
                'account_id': recon_account.id,
                'debit': amount,
                'credit': 0.0,
                'partner_id': False,
                'matching_number': matching_number,
            }
            if analytic_dist:
                debit_vals['analytic_distribution'] = analytic_dist
            move_line_vals.append(debit_vals)
            
            # Credit: output_account (property_stock_account_output_categ_id)
            # This is NOT the reconciliation account - do NOT apply analytic distribution here
            credit_vals = {
                'name': _('Reconciliation for %s') % self.name,
                'account_id': output_account.id,
                'debit': 0.0,
                'credit': amount,
                'partner_id': False,
                'matching_number': matching_number,
            }
            # Analytic distribution should NOT be applied to the credit line (output account)
            move_line_vals.append(credit_vals)
            
            # Store lines for reconciliation
            if output_account not in lines_to_reconcile_by_account:
                lines_to_reconcile_by_account[output_account] = self.env['account.move.line']
            lines_to_reconcile_by_account[output_account] |= lines
        
        if not move_line_vals:
            raise UserError(_('No lines to reconcile.'))
        
        # Create the journal entry (use picking date_done as move date)
        move_vals = {
            'journal_id': journal.id,
            'date': self.date_done or fields.Date.context_today(self),
            'ref': _('Reconciliation for %s') % self.name,
            'move_type': 'entry',
            'line_ids': [(0, 0, line_vals) for line_vals in move_line_vals],
        }
        
        reconciliation_move = self.env['account.move'].create(move_vals)
        reconciliation_move._post()
        
        # Reconcile the new lines with existing lines (one new credit line per reconciliation_data entry)
        reconciled_count = 0
        for idx, data in enumerate(reconciliation_data):
            output_account = data['output_account']
            recon_account = data['recon_account']
            lines = data['lines']
            matching_number = f"REC-{self.id}-{data['lines'][0].move_id.stock_move_id.id if data['lines'][0].move_id.stock_move_id else 'unknown'}"
            
            # Get the single new credit line for this entry (move_line_vals order: debit0, credit0, debit1, credit1, ...)
            credit_line_index = idx * 2 + 1
            if credit_line_index >= len(reconciliation_move.line_ids):
                continue
            new_credit_line = reconciliation_move.line_ids[credit_line_index]
            if new_credit_line.account_id != output_account or new_credit_line.credit <= 0:
                continue
            
            # Only reconcile lines that are not already reconciled
            if output_account.reconcile:
                lines_to_reconcile = lines.filtered(lambda l: not l.reconciled)
                if not lines_to_reconcile:
                    continue
                if new_credit_line.reconciled:
                    continue
                lines_to_reconcile.write({'matching_number': matching_number})
                all_lines = lines_to_reconcile | new_credit_line
                try:
                    all_lines.reconcile()
                    reconciled_count += len(all_lines)
                except Exception as e:
                    raise UserError(_(
                        'Error reconciling lines for account %s: %s'
                    ) % (output_account.display_name, str(e)))
        
        if reconciled_count > 0:
            return {
                'type': 'ir.actions.act_window',
                'name': _('Reconciliation Entry'),
                'res_model': 'account.move',
                'res_id': reconciliation_move.id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            raise UserError(_('No lines were reconciled.'))
