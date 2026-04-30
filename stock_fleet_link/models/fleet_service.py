from odoo import api, fields, models


class FleetVehicleLogServices(models.Model):
    _inherit = 'fleet.vehicle.log.services'

    stock_picking_id = fields.Many2one(
        comodel_name='stock.picking',
        string='Stock Picking',
        domain="[('picking_type_code', '=', 'internal')]",
        help='Link to an internal transfer',
    )

    def _create_product_lines_from_picking(self):
        """Create fleet.service.product.line records from the linked picking.

        - product_id: product on the stock move
        - quantity: prefer done qty; fallback to planned qty
        - price_unit: product standard cost
        """
        self.ensure_one()
        picking = self.stock_picking_id
        if not picking or picking.picking_type_code != 'internal':
            return

        # Avoid duplicates if lines already exist
        if getattr(self, 'product_line_ids', False) and self.product_line_ids:
            return

        ServiceProductLine = self.env['fleet.service.product.line']

        line_vals_list = []
        for move in picking.move_ids_without_package:
            product = move.product_id
            if not product:
                continue

            # Prefer done quantity (sum of move lines), fallback to planned quantity
            qty_done = 0.0
            if move.move_line_ids:
                qty_done = sum(move.move_line_ids.mapped('qty_done'))
            quantity = qty_done or move.product_uom_qty or 0.0
            if quantity <= 0:
                continue

            price_unit = product.standard_price or 0.0

            line_vals_list.append({
                'service_id': self.id,
                'product_id': product.id,
                'quantity': quantity,
                'price_unit': price_unit,
            })

        if line_vals_list:
            ServiceProductLine.create(line_vals_list)

        # If parent has helper to recompute amount from lines, call it
        if hasattr(self, '_recompute_amount_from_lines'):
            self._recompute_amount_from_lines()

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for service in records:
            # Populate product lines if a picking is linked at creation
            try:
                service._create_product_lines_from_picking()
            except Exception:
                # Do not break service creation due to line creation
                pass
        return records

    def write(self, vals):
        res = super().write(vals)
        # If picking was just set, attempt to create product lines
        if 'stock_picking_id' in vals:
            for service in self:
                try:
                    service._create_product_lines_from_picking()
                except Exception:
                    # Keep write robust
                    pass
        return res


