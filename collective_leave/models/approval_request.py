from odoo import fields, models


class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    collective_leave_id = fields.Many2one(
        comodel_name='collective.leave',
        string='კოლექტიური შვებულება',
    )
