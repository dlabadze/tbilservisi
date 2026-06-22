from odoo import models, fields, api
from datetime import timedelta

PERSONAL_APPLICATION_CATEGORIES = [10, 11, 12,25,44,45,46,47,48,49]
VACATION_DAYS = [46,47, 48, 49]
VACAYS = [45,46,47,48,49]


class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    brdzaneba_job_vacancy_count = fields.Integer(
        string="ვაკანსიების რაოდენობა",
        related='brdzaneba_job_id.vacancy_count',
        readonly=True,
        store=False,
    )
    safudzvelis_date = fields.Date(string="საფუძველის თარიღი")
    dasaqviti_amount = fields.Float(string="დასაქვითი თანხა")
    brdzanebis_nomeri = fields.Char(string="ბრძანების ნომერი")
    new_surname = fields.Char(string="ახალი გვარი")



    @api.onchange('category_id', 'brdzaneba_employee_id', 'brdzaneba_date', 'safudzvelis_date')
    def _onchange_brdzaneba_safudzveli(self):
        for rec in self:
            if rec.category_id and rec.category_id.id in PERSONAL_APPLICATION_CATEGORIES:
                parts = []
                if rec.brdzaneba_employee_id:
                    parts.append(rec.brdzaneba_employee_id.name + 'ს')
                parts.append('პირადი განცხადება')
                if rec.category_id.id == 25:
                    if rec.safudzvelis_date:
                        parts.append(rec.safudzvelis_date.strftime('%d.%m.%Y'))
                else:
                    if rec.brdzaneba_date:
                        parts.append(rec.brdzaneba_date.strftime('%d.%m.%Y'))
                rec.brdzaneba_safudzveli = ' '.join(parts)
            elif rec.category_id and rec.safudzvelis_date:
                rec.brdzaneba_safudzveli = rec.safudzvelis_date.strftime('%d.%m.%Y') if rec.safudzvelis_date else False


    @api.onchange('category_id')
    def _onchange_brdzaneba_shtati(self):
        for rec in self:
            if rec.category_id and rec.category_id.id == 11:
                rec.brdzaneba_shtati = 'შტატგარეშე'
            elif rec.category_id and rec.category_id.id in [12,44]:
                rec.brdzaneba_shtati = 'შტატი'
            elif rec.category_id and rec.category_id.id == 10:
                rec.brdzaneba_shtati = 'მოვალეობის შემსრულებელი'
            else :
                rec.brdzaneba_shtati = False



    @api.onchange('category_id')
    def _onchange_x_studio_time_off_type(self):
        for rec in self:
            if rec.category_id and rec.category_id.id in VACAYS:
                if rec.category_id.id == 45:
                    rec.x_studio_time_off_type = 1
                elif rec.category_id.id == 46:
                    rec.x_studio_time_off_type = 6
                elif rec.category_id.id == 47:
                    rec.x_studio_time_off_type = 4
                elif rec.category_id.id == 48:
                    rec.x_studio_time_off_type = 3
                elif rec.category_id.id == 49:
                    rec.x_studio_time_off_type = 3

    @api.onchange('category_id', 'brdzaneba_start_date', 'brdzaneba_end_date')
    def _onchange_x_studio_dgeebi_real(self):
        for rec in self:
            if rec.category_id and rec.category_id.id in VACATION_DAYS:
                if rec.brdzaneba_start_date and rec.brdzaneba_end_date:
                    dgeebi_real = (rec.brdzaneba_end_date - rec.brdzaneba_start_date).days
                    rec.x_studio_dgeebi_real = dgeebi_real + 1
                else:
                    rec.x_studio_dgeebi_real = 0
