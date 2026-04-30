from odoo import api, fields, models


class FleetServiceProductLine(models.Model):
    _name = 'fleet.service.product.line'
    _description = 'Fleet Service Product Line'
    _order = 'id desc'

    service_id = fields.Many2one(
        'fleet.vehicle.log.services',
        string='Service',
        required=True,
        ondelete='cascade',
        index=True,
    )
    product_id = fields.Many2one('product.product', string='Product', required=True)
    name = fields.Char(string='Name')
    product_ref = fields.Char(string='Reference')
    barcode = fields.Char(string='Barcode')
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure')
    quantity = fields.Float(string='Quantity', digits='Product Unit of Measure', default=1.0)
    price_unit = fields.Monetary(string='Unit Price', currency_field='currency_id', default=0.0)
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='service_id.currency_id',
        store=True,
        readonly=True,
    )
    subtotal = fields.Monetary(
        string='Amount', currency_field='currency_id', compute='_compute_subtotal', store=True
    )

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            product = line.product_id
            if product:
                line.name = product.display_name or product.name
                line.product_ref = product.default_code or False
                line.barcode = product.barcode or False
                line.uom_id = product.uom_id.id
                line.price_unit = product.list_price or 0.0

    @api.depends('quantity', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = (line.quantity or 0.0) * (line.price_unit or 0.0)

    # Keep the parent service amount in sync whenever lines change
    def _recompute_service_amount(self):
        services = self.mapped('service_id')
        if services:
            services._recompute_amount_from_lines()

    def create(self, vals_list):
        records = super().create(vals_list)
        records._recompute_service_amount()
        return records

    def write(self, vals):
        res = super().write(vals)
        self._recompute_service_amount()
        return res

    def unlink(self):
        services = self.mapped('service_id')
        res = super().unlink()
        services._recompute_amount_from_lines()
        return res


class FleetVehicleLogServices(models.Model):
    _inherit = 'fleet.vehicle.log.services'

    product_line_ids = fields.One2many(
        'fleet.service.product.line', 'service_id', string='Product Lines'
    )

    def _recompute_amount_from_lines(self):
        for service in self:
            total = sum(service.product_line_ids.mapped('subtotal'))
            service.amount = total

    @api.onchange('product_line_ids', 'product_line_ids.quantity', 'product_line_ids.price_unit')
    def _onchange_product_lines_update_amount(self):
        self._recompute_amount_from_lines()


