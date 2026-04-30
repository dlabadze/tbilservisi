from odoo import api, fields, models


class FleetVehicleLogServices(models.Model):
    _inherit = 'fleet.vehicle.log.services'

    repair_id = fields.Many2one(
        'repair.order',
        string='Repair Order',
        ondelete='set null',
        index=True,
    )

    def action_open_repair(self):
        self.ensure_one()
        if not self.repair_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': self.repair_id.name or 'Repair',
            'res_model': 'repair.order',
            'view_mode': 'form',
            'res_id': self.repair_id.id,
            'target': 'current',
            'context': {},
        }

    def _create_product_lines_from_repair(self, repair):
        """Create fleet.service.product.line from repair stock moves where repair_line_type == 'add'."""
        self.ensure_one()
        if not repair:
            return

        # Avoid duplicates if lines already exist
        if getattr(self, 'product_line_ids', False) and self.product_line_ids:
            return

        Move = self.env['stock.move'].sudo()
        moves = Move.search([
            ('repair_id', '=', repair.id),
            ('repair_line_type', '=', 'add'),
        ])
        if not moves:
            return

        ServiceProductLine = self.env['fleet.service.product.line'].sudo()
        line_vals_list = []
        for move in moves:
            product = move.product_id
            if not product:
                continue

            # Quantity: prefer custom field 'quantity' then qty_done then planned
            quantity = getattr(move, 'quantity', None)
            if quantity is None:
                qty_done = 0.0
                if move.move_line_ids:
                    qty_done = sum(move.move_line_ids.mapped('qty_done'))
                quantity = qty_done or move.product_uom_qty or 0.0
            if quantity <= 0:
                continue

            # Unit price from product template standard cost
            tmpl = getattr(product, 'product_tmpl_id', False)
            if tmpl and hasattr(tmpl, 'standard_price'):
                price_unit = tmpl.standard_price or 0.0
            else:
                price_unit = getattr(product, 'standard_price', 0.0) or 0.0

            # Additional fields requested from template, with variant fallback
            product_ref = None
            barcode = None
            uom_id = False
            if tmpl:
                product_ref = getattr(tmpl, 'default_code', None) or getattr(product, 'default_code', None)
                barcode = getattr(tmpl, 'barcode', None) or getattr(product, 'barcode', None)
                uom_id = (getattr(tmpl, 'uom_id', False) and tmpl.uom_id.id) or \
                         (getattr(product, 'uom_id', False) and product.uom_id.id)

            line_vals_list.append({
                'service_id': self.id,
                'product_id': product.id,
                'name': getattr(product, 'display_name', None) or getattr(product, 'name', '') or '',
                'quantity': quantity,
                'price_unit': price_unit,
                'product_ref': product_ref or False,
                'barcode': barcode or False,
                'uom_id': uom_id or False,
            })

        if line_vals_list:
            ServiceProductLine.create(line_vals_list)


