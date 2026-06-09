from odoo import models, fields, api
from datetime import timedelta

PERSONAL_APPLICATION_CATEGORIES = [10, 11, 12, 13,44,25,45,46,47,48,49]


class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    brdzaneba_job_vacancy_count = fields.Integer(
        string="ვაკანსიების რაოდენობა",
        related='brdzaneba_job_id.vacancy_count',
        readonly=True,
        store=False,
    )

    release_date = fields.Date(
        string="გათავისუფლების თარიღი",
        compute="_compute_release_date",
        store=True,
        readonly=False,
    )

    @api.depends('brdzaneba_end_date', 'category_id')
    def _compute_release_date(self):
        for rec in self:
            if rec.category_id and rec.category_id.id in [24, 25, 26, 27] and rec.brdzaneba_end_date:
                rec.release_date = rec.brdzaneba_end_date - timedelta(days=1)
            else:
                rec.release_date = False

    @api.onchange('category_id', 'brdzaneba_employee_id', 'brdzaneba_date')
    def _onchange_brdzaneba_safudzveli(self):
        for rec in self:
            if rec.category_id and rec.category_id.id in PERSONAL_APPLICATION_CATEGORIES:
                parts = []
                if rec.brdzaneba_employee_id:
                    parts.append(rec.brdzaneba_employee_id.name + 'ს')
                parts.append('პირადი განცხადება')
                if rec.brdzaneba_date:
                    parts.append(rec.brdzaneba_date.strftime('%d.%m.%Y'))
                rec.brdzaneba_safudzveli = ' '.join(parts)

    @api.onchange('category_id')
    def _onchange_brdzaneba_shtati(self):
        for rec in self:
            if rec.category_id and rec.category_id.id == 11:
                rec.brdzaneba_shtati = 'შტატგარეშე'
            else :
                rec.brdzaneba_shtati = False