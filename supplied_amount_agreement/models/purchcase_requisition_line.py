from odoo import fields, api, models


class PurchaseRequisitionLine(models.Model):
    _inherit = 'purchase.requisition.line'

    supplied_amount = fields.Float(compute="_compute_supplied_amount", store=True)

    @api.depends('requisition_id.purchase_ids', 'requisition_id.purchase_ids.amount_total')
    def _compute_supplied_amount(self):
        for line in self:
            line.supplied_amount = sum(line.requisition_id.purchase_ids.mapped('amount_total'))
            line.remaining_amount = (line.product_qty * line.price_unit) - line.supplied_amount