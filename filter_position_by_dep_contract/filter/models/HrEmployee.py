from odoo import models, fields, api

class HrContract(models.Model):
    _inherit = 'employee.operation'

    available_job_ids = fields.Many2many(
        'hr.job',
        compute='_compute_available_job_ids',
        string='Available Job Positions',
        store=False
    )

    @api.depends('x_studio_department')
    def _compute_available_job_ids(self):
        for operation in self:
            if operation.x_studio_department:
                operation.available_job_ids = self.env['hr.job'].search([
                    ('x_studio_department', '=', operation.x_studio_department.id)
                ])
            else:
                operation.available_job_ids = self.env['hr.job'].search([])

    @api.onchange('x_studio_position')
    def _onchange_job_id(self):
        if self.x_studio_position and not self.x_studio_department:
            self.x_studio_department = self.job_id.x_studio_department
            self.x_studio_wage1 = self.x_studio_position.x_studio_expected_salary
