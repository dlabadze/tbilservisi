from odoo import models, fields, api

PERSONAL_APPLICATION_CATEGORIES = [10, 11, 12, 13]


class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    brdzaneba_job_vacancy_count = fields.Integer(
        string="ვაკანსიების რაოდენობა",
        related='brdzaneba_job_id.vacancy_count',
        readonly=True,
        store=False,
    )

    @api.onchange('category_id', 'brdzaneba_employee_id', 'brdzaneba_date')
    def _onchange_brdzaneba_safudzveli(self):
        for rec in self:
            if rec.category_id and rec.category_id.id in PERSONAL_APPLICATION_CATEGORIES:
                parts = []
                if rec.brdzaneba_employee_id:
                    parts.append(rec.brdzaneba_employee_id.name)
                parts.append('პირადი განცხადება')
                if rec.brdzaneba_date:
                    parts.append(fields.Date.to_string(rec.brdzaneba_date))
                rec.brdzaneba_safudzveli = ', '.join(parts)

