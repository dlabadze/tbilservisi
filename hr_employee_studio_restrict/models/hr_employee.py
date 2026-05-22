from odoo import models, fields

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    x_studio_contractwage = fields.Monetary(
        string="ხელფასი",
        related="contract_id.wage",
        readonly=True,
        tracking=100
    )
