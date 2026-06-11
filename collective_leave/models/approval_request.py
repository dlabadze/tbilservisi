from odoo import fields, models


class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    collective_leave_id = fields.Many2one(
        comodel_name='collective.leave',
        string='კოლექტიური შვებულება',
    )
    collective_change_position_id = fields.Many2one(
        comodel_name='collective.change.position',
        string='კოლექტიური თანამდებობის ცვლილება',
    )
    collective_danishvna_id = fields.Many2one(
        comodel_name="collective.danishvna",
        string="კოლექტიური დანიშვნა",
    )
