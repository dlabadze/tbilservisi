from odoo import models, fields, api

class EmployeeOperation(models.Model):
    _inherit = 'employee.operation'

    available_job_ids = fields.Many2many(
        'hr.job',
        compute='_compute_available_job_ids',
        string='Available Job Positions',
        store=False
    )

    is_wage_set = fields.Boolean(default=False)
    x_studio_wage1 = fields.Float(string='ხელფასი',compute='_compute_x_studio_wage',store = True, readonly=False)


    @api.depends('x_studio_department')
    def _compute_available_job_ids(self):
        for operation in self:
            if operation.x_studio_department:
                operation.available_job_ids = self.env['hr.job'].search([
                    ('department_id', '=', operation.x_studio_department.id)
                ])
            else:
                operation.available_job_ids = self.env['hr.job'].search([])

    @api.onchange('x_studio_position')
    def _onchange_job_id(self):
        if self.x_studio_position and not self.x_studio_department:
            self.x_studio_department = self.x_studio_position.department_id.id
        self.is_wage_set = True

    @api.depends('x_studio_position')
    def _compute_x_studio_wage(self):
        for operation in self:
            if operation.x_studio_position and operation.is_wage_set:
                operation.x_studio_wage1 = operation.x_studio_position.x_studio_expected_salary
            operation.is_wage_set = False