from odoo import models, api

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    @api.depends('product_id.display_name')
    def _compute_price_unit_and_date_planned_and_name(self):
        return super()._compute_price_unit_and_date_planned_and_name()
