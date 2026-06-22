from odoo import api, fields, models


class CollectiveChangePosition(models.Model):
    _inherit = 'collective.change.position'

    brdzaneba_safudzveli = fields.Text(string='საფუძველი')
    marked_employee_count = fields.Integer(
        string='მონიშნული თანამშრომლების რაოდენობა',
        compute='_compute_marked_employee_count',
    )

    @api.depends('collective_ch_position_emp_ids.is_checked')
    def _compute_marked_employee_count(self):
        for record in self:
            record.marked_employee_count = len(record.collective_ch_position_emp_ids.filtered('is_checked'))

    def create_approval_request(self):
        category = self.env['approval.category'].sudo().search([('name', '=', 'გადაყვანა')], limit=1)
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
                    'collective_change_position_id': record.id,
                    'brdzaneba_salary': record.salary,
                    'brdzaneba_date': record.registration_date,
                    'brdzaneba_safudzveli': record.brdzaneba_safudzveli,
                })
                request.sudo().action_confirm()
                request.sudo().action_approve()


class CollectiveChangePositionEmps(models.Model):
    _inherit = 'collective.change.position.emps'

    line_number = fields.Integer(
        string='N',
        compute='_compute_line_number',
    )

    @api.depends('collective_change_position_id', 'collective_change_position_id.collective_ch_position_emp_ids')
    def _compute_line_number(self):
        for record in self:
            record.line_number = 0
            if not record.collective_change_position_id or not record.id:
                continue
            ordered_lines = record.collective_change_position_id.collective_ch_position_emp_ids.sorted(key=lambda line: line.id)
            line_index = {line.id: idx + 1 for idx, line in enumerate(ordered_lines)}
            record.line_number = line_index.get(record.id, 0)
