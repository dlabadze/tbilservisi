from odoo import fields, models


class CollectiveDanishvna(models.Model):
    _inherit = 'collective.danishvna'

    brdzaneba_safudzveli = fields.Text(string='საფუძველი')

    def create_approval_request(self):
        category = self.env['approval.category'].sudo().search([('name', '=', 'დანიშვნა')], limit=1)
        for record in self:
            existing_employees = record.approval_request_ids.mapped('brdzaneba_employee_id').ids
            for employee in record.employee_ids:
                if employee.id in existing_employees:
                    continue
                request = self.env['approval.request'].sudo().create({
                    'request_owner_id': self.env.user.id,
                    'category_id': category.id,
                    'brdzaneba_employee_id': employee.id,
                    'brdzaneba_start_date': record.start_date,
                    'brdzaneba_end_date': record.end_date,
                    'brdzaneba_department_id': record.new_department_id.id,
                    'brdzaneba_job_id': record.new_job_id.id,
                    'collective_danishvna_id': record.id,
                    'brdzaneba_salary': record.salary,
                    'brdzaneba_date': record.registration_date,
                    'brdzaneba_safudzveli': record.brdzaneba_safudzveli,
                })
                request.sudo().action_confirm()
                request.sudo().action_approve()
