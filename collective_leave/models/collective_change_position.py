from odoo import fields, models, api


class CollectiveChangePosition(models.Model):
    _name = 'collective.change.position'
    _description = 'Collective Change Position'

    registration_date = fields.Date(string='რეგისტრაციის თარიღი', required=True)
    start_date = fields.Date(string='დაწყების თარიღი', required=True)
    end_date = fields.Date(string='დასასრული თარიღი', required=True)

    department_id = fields.Many2one('hr.department', string='სამსახური', required=True)
    parent_department_id = fields.Many2one(
        'hr.department',
        string='დეპარტამენტი',
        compute='_compute_parent_department_id',
        store=True,
        readonly=True,
    )

    job_id = fields.Many2one(
        comodel_name='hr.job',
        string='თანამდებობა',
        required=True,
        domain="[('department_id', '=', department_id)]",
        )

    new_department_id = fields.Many2one('hr.department', string='ახალი სამსახური', required=True)
    new_parent_department_id = fields.Many2one(
        'hr.department',
        string='ახალი დეპარტამენტი',
        compute='_compute_parent_department_id',
        store=True,
        readonly=True,
    )

    new_job_id = fields.Many2one(
        comodel_name='hr.job',
        string='ახალი თანამდებობა',
        required=True,
        domain="[('department_id', '=', new_department_id)]",
    )

    collective_ch_position_emp_ids = fields.One2many(
        comodel_name='collective.change.position.emps', 
        inverse_name='collective_change_position_id',
        string='თანამშრომელები',
    )

    employee_ids = fields.Many2many(
        comodel_name='hr.employee',
        string='თანამშრომელები',
        compute='_compute_employee_ids',
        store=True,
    )

    @api.depends('collective_ch_position_emp_ids.is_checked')
    def _compute_employee_ids(self):
        for record in self:
            record.employee_ids = record.collective_ch_position_emp_ids.filtered('is_checked').mapped('employee_id')

    @api.depends('department_id.parent_path', 'new_department_id.parent_path')
    def _compute_parent_department_id(self):
        for record in self:
            department = record.department_id
            while department.parent_id:
                department = department.parent_id
            record.parent_department_id = department

            new_department = record.new_department_id
            while new_department.parent_id:
                new_department = new_department.parent_id
            record.new_parent_department_id = new_department

    def action_compute_employees(self):
        for record in self:
            existing_ids = record.collective_ch_position_emp_ids.mapped('employee_id').ids
            employees = self.env['hr.employee'].sudo().search([
                ('department_id', '=', record.department_id.id),
                ('job_id', '=', record.job_id.id),
                ('id', 'not in', existing_ids),
            ])
            record.collective_ch_position_emp_ids = [
                (0, 0, {'employee_id': emp.id})
                for emp in employees
            ]

