from odoo import models, fields, api


class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    second_unit_cost = fields.Float(string='Second Unit Cost', compute='_compute_second_unit_cost', store=True)

    @api.depends('quantity', 'reference', 'value')
    def _compute_second_unit_cost(self):
        for rec in self:
            if rec.quantity > 0:
                another_layer = self.env['stock.valuation.layer'].search([
                    ('product_id', '=', rec.product_id.id),
                    ('reference', '=', rec.reference),
                ], order='create_date desc')
                if another_layer:
                    total_value = sum(another_layer.mapped('value'))
                    rec.second_unit_cost = total_value / rec.quantity
                else:
                    rec.second_unit_cost = rec.unit_cost
            else:
                rec.second_unit_cost = 0