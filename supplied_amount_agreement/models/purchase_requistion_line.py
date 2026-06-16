from odoo import fields, api, models


class PurchaseRequisitionLine(models.Model):
    _inherit = 'purchase.requisition.line'

    supplied_amount = fields.Float(compute="_compute_supplied_amount", store=True)

    @api.depends('purchase_ids', 'purchase_ids.amount_total')
    def _compute_supplied_amount(self):
        for line in self:
            line.supplied_amount = line.purchase_ids.mapped('amount_total')