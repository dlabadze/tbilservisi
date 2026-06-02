from odoo import models, fields, api


class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    brdzaneba_job_vacancy_count = fields.Integer(
        string="ვაკანსიების რაოდენობა",
        related='brdzaneba_job_id.vacancy_count',
        readonly=True,
        store=False,
    )
