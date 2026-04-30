from odoo import fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    requisition_link_id = fields.Many2one(
        comodel_name='purchase.requisition',
        string='შესყიდვის ხელშეკრულება',
        copy=False,
        check_company=True,
        index=True,
    )
