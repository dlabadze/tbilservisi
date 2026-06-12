from odoo import fields, models, api
import logging
_logger = logging.getLogger(__name__)


class CollectiveDanishVNA(models.Model):
    _name = "collective.danishvna"
    _description = "Collective Danishvna"

    registration_date = fields.Date(string='რეგისტრაციის თარიღი', required=True)
    start_date = fields.Date(string='დაწყების თარიღი', required=True)
    end_date = fields.Date(string='დასრულების თარიღი', required=True)

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


    collective_danishvna_emp_ids = fields.One2many(
        comodel_name='collective.danishvna.emps', 
        inverse_name='collective_danishvna_id',
        string='თანამშრომელები',
    )

    employee_ids = fields.Many2many(
        comodel_name='hr.employee',
        string='თანამშრომელები',
        compute='_compute_employee_ids',
        store=True,
    )

    approval_request_ids = fields.One2many(
        comodel_name='approval.request',
        inverse_name='collective_danishvna_id',
        string='ბრძანებები',
    )
    approval_request_count = fields.Integer(
        compute='_compute_approval_request_count',
    )
    salary = fields.Float(string="ხელფასი")

    @api.onchange("new_job_id")
    def _onchange_salary(self):
        if self.new_job_id and 'x_studio_expected_salary' in self.new_job_id._fields:
            self.salary = self.new_job_id.x_studio_expected_salary
        else:
            self.salary = 0.0

    @api.depends('collective_danishvna_emp_ids.is_checked')
    def _compute_employee_ids(self):
        for record in self:
            record.employee_ids = record.collective_danishvna_emp_ids.filtered('is_checked').mapped('employee_id')

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
            existing_ids = record.collective_danishvna_emp_ids.mapped('employee_id').ids
            employees = self.env['hr.employee'].sudo().search([
                ('department_id', '=', record.department_id.id),
                ('job_id', '=', record.job_id.id),
                ('id', 'not in', existing_ids),
            ])
            record.collective_danishvna_emp_ids = [
                (0, 0, {'employee_id': emp.id})
                for emp in employees
            ]

    def _compute_approval_request_count(self):
        for record in self:
            record.approval_request_count = len(record.approval_request_ids)

    def action_open_approval_requests(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'ბრძანებები',
            'res_model': 'approval.request',
            'view_mode': 'list,form',
            'domain': [('collective_danishvna_id', '=', self.id)],
            'context': {'default_collective_danishvna_id': self.id},
        }


    def create_approval_request(self):
        category = self.env['approval.category'].sudo().search([('name', '=', 'დანიშვნა')], limit=1)
        _logger.info(f"Category: {category}")
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
                    'brdzaneba_salary': record.salary
                })
                _logger.info(f"Created Request: {request}")
                request.sudo().action_confirm()
                request.sudo().action_approve()