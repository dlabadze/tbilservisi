from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)
from odoo.exceptions import ValidationError
from odoo.tools import float_compare, float_is_zero


class RepairOrder(models.Model):
    _inherit = 'repair.order'

    @api.model
    def default_get(self, fields_list):
        res = super(RepairOrder, self).default_get(fields_list)

        # Optimization: Only look for partner if needed
        if 'partner_id' in fields_list and not res.get('partner_id'):
            picking_type = False
            
            # 1. Try to find picking_type_id in default values
            if res.get('picking_type_id'):
                picking_type = self.env['stock.picking.type'].browse(res['picking_type_id'])
            
            # 2. If not in defaults, Repair मॉडल usually sets a default one 
            # (e.g. via _default_picking_type in original Odoo, but we are in default_get now)
            # If standard Odoo default_get didn't validly set it, we might check env.context or company defaults
            
            # If we found a type and it has a default partner
            if picking_type and picking_type.default_repair_partner_id:
                res['partner_id'] = picking_type.default_repair_partner_id.id
                
        return res

    @api.onchange('picking_type_id')
    def _onchange_picking_type_id_partner(self):
        if self.picking_type_id and self.picking_type_id.default_repair_partner_id:
            # Only set if partner is empty to avoid overwriting user selection
            if not self.partner_id:
                self.partner_id = self.picking_type_id.default_repair_partner_id

    # ---------------------------------------------------------
    # Source Picking
    # ---------------------------------------------------------
    picking_id_2 = fields.Many2one(
        'stock.picking',
        string="Source Picking",
    )

    # ---------------------------------------------------------
    # STORED allowed pickings (USED BY XML DOMAIN)
    # ---------------------------------------------------------
    allowed_picking_ids = fields.Many2many(
        'stock.picking',
        compute='_compute_allowed_picking_ids',
        store=False,
        readonly=True,
    )

    testingfield = fields.Text(string="თესთინგ")


    def action_repair_end(self):
        """
        Override to force the date context when clicking 'End Repair'.
        This ensures generated accounting entries match the repair's schedule date
        instead of the current date, protecting the sequence numbering.
        """
        for repair in self:
            dt = repair.schedule_date or fields.Datetime.now()
            d = fields.Date.to_date(dt)

            # Force context for the entire chain of calls (stock moves -> account moves)
            res = super(RepairOrder, repair.with_context(
                force_period_date=d,
                force_date=d,
            )).action_repair_end()
            
            return res

    def action_repair_done(self):
        for repair in self:
            dt = repair.schedule_date or fields.Datetime.now()
            d = fields.Date.to_date(dt)

            # 1) Force accounting valuation date at posting time
            super(RepairOrder, repair.with_context(
                force_period_date=d,
                force_date=d,
            )).action_repair_done()

            # 2) Force stock dates AFTER done (Odoo may overwrite them during _action_done)
            moves = (repair.move_ids | repair.move_id).filtered(lambda m: m.state != "cancel")
            if moves:
                moves.sudo().write({"date": dt})
                moves.move_line_ids.sudo().write({"date": dt})

        return True

    # ---------------------------------------------------------
    # COMPUTE ALLOWED PICKINGS
    # ---------------------------------------------------------
    @api.depends('product_location_src_id')
    def _compute_allowed_picking_ids(self):
        Repair = self.env['repair.order']

        for rec in self:
            # If repair source location is not ready → no pickings
            if not rec.product_location_src_id:
                rec.allowed_picking_ids = [(6, 0, [])]
                continue

            # Pickings already used in other repairs
            used_picking_ids = Repair.search([
                ('picking_id_2', '!=', False),
                ('id', '!=', rec.id),
            ]).mapped('picking_id_2').ids

            domain = [
                ('state', '=', 'done'),
                ('picking_type_id.code', 'in', ['internal', 'incoming']),
                ('location_dest_id', '=', rec.product_location_src_id.id),
                ('id', 'not in', used_picking_ids),
            ]

            pickings = self.env['stock.picking'].search(domain)

            rec.allowed_picking_ids = [(6, 0, pickings.ids)]

    # ---------------------------------------------------------
    # ON PICKING CHANGE → FILL REPAIR LINES
    # ---------------------------------------------------------
    @api.onchange('picking_id_2')
    def _onchange_picking_id_2(self):
        self.move_ids = [(5, 0, 0)]

        picking = self.picking_id_2
        if not picking:
            return

        lines = []

        for move in picking.move_ids:
            if not move.product_id or move.product_uom_qty <= 0:
                continue

            # REMOVE
            lines.append((0, 0, {
                'repair_line_type': 'remove',
                'product_id': move.product_id.id,
                'product_uom': move.product_uom.id,
                'product_uom_qty': move.product_uom_qty,
            }))

            # ADD
            lines.append((0, 0, {
                'repair_line_type': 'add',
                'product_id': move.product_id.id,
                'product_uom': move.product_uom.id,
                'product_uom_qty': move.product_uom_qty,
            }))

        self.move_ids = lines






class StockMove(models.Model):
    _inherit = 'stock.move'

    x_basis_text = fields.Text(string="Basis Text")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            repair_id = vals.get('repair_id')
            if not repair_id:
                continue

            repair = self.env['repair.order'].browse(repair_id)
            picking = repair.picking_id_2
            picking_name = picking.name if picking else ''

            vals['x_basis_text'] = (
                f"შეკეთება N: {repair.name}\n"
                f"გადაწერა N: {picking_name}\n"
                f"მანქანის ნომერი : {repair.x_studio_fleet_id.license_plate or ''}\n"
                "საფუძველზე"
            )

        return super().create(vals_list)



class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model_create_multi
    def create(self, vals_list):
        # ---------------------------------------------------------
        # FIX: Force Date from Context (to avoid Sequence Error)
        # ---------------------------------------------------------
        
        ctx_date = self._context.get('force_period_date') or self._context.get('force_date')
        
        _logger.info("REPAIR DEBUG: AccountMove create called. Context Date: %s", ctx_date)
        
        if ctx_date:
            for vals in vals_list:
                _logger.info("REPAIR DEBUG: Original Vals: %s", vals)
                
                vals['date'] = ctx_date
                
                # If name is missing or "TEMP", force it to '/' to trigger Odoo's sequence logic.
                current_name = vals.get('name')
                if not current_name or (isinstance(current_name, str) and 'TEMP' in current_name):
                     vals['name'] = '/'
                     _logger.info("REPAIR DEBUG: Forcing name to '/' for regeneration")

                # Try to find the sequence explicitly (legacy support)
                new_name = False
                if vals.get('journal_id'):
                    journal = self.env['account.journal'].browse(vals['journal_id'])
                    if getattr(journal, 'sequence_id', False):
                        new_name = journal.sequence_id.with_context(ir_sequence_date=ctx_date).next_by_id()
                        _logger.info("REPAIR DEBUG: Found explicit sequence, new name: %s", new_name)
                
                if new_name:
                    vals['name'] = new_name

                _logger.info("REPAIR DEBUG: Final Vals: %s", vals)

        # Pass ir_sequence_date in context to ensure the Sequence Generator uses it
        if ctx_date:
            moves = super(AccountMove, self.with_context(ir_sequence_date=ctx_date)).create(vals_list)
        else:
            moves = super().create(vals_list)

        for am in moves:
            # Only valuation entries created from stock
            if am.stock_move_id and not am.basis:
                txt = am.stock_move_id.x_basis_text
                if txt:
                    am.basis = txt

        return moves

    @api.constrains('name', 'date', 'journal_id', 'state')
    def _constrains_date_sequence(self):
        # FIX: Bypass sequence/date mismatch constraint if we are forcing the date.
        # This allows the Repair to proceed even if Odoo generates a "Feb" sequence for a "Jan" date
        # (which can happen if the journal "Last Sequence" was Feb).
        # The user can then Resequence later if strictly needed.
        if self._context.get('force_period_date') or self._context.get('force_date'):
            return
        return super()._constrains_date_sequence()


class FleetVehicleLogServices(models.Model):
    _inherit = 'fleet.vehicle.log.services'

    def copy(self, default=None):
        self.ensure_one()

        if not isinstance(default, dict):
            default = {}

        if self.product_line_ids:
            default['product_line_ids'] = [
                (0, 0, {
                    'product_id': line.product_id.id,
                    'quantity': line.quantity,
                    'price_unit': line.price_unit,
                    'product_ref': line.product_ref,
                    'uom_id': line.uom_id.id,
                    #'tax_ids': [(6, 0, line.tax_ids.ids)],
                    #'description': line.description,
                    # ❌ DO NOT SET subtotal (computed)
                })
                for line in self.product_line_ids
            ]

        return super().copy(default)