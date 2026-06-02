from odoo import api, fields, models


class CollectiveLeave(models.Model):
    _name = 'collective.leave'
    _description = 'Collective Leave'

    name = fields.Char(
        string='სახელი',
        required=True,
        readonly=True,
        default='New',
        copy=False,
    )
    department_id = fields.Many2one(
        comodel_name='hr.department',
        string='სამსახური',
        required=True,
    )
    job_id = fields.Many2one(
        comodel_name='hr.job',
        string='თანამდებობა',
        required=True,
        domain="[('department_id', '=', department_id)]",
    )
    start_day =  fields.Date(
        string='საწყისი თარიღი',
        required=True,
    )
    end_day = fields.Date(
        string='დასრულების თარიღი',
        required=True,
    )
    days = fields.Integer(
        string='დღეების რაოდენობა',
        required=True,
    )
    collective_leave_emp_ids = fields.One2many(
        comodel_name='collective.leave.employees',
        inverse_name='collective_leave_id',
        string='თანამშრომელები',
    )
    employee_ids = fields.Many2many(
        comodel_name='hr.employee',
        string='მონიშნულები',
        compute='_compute_employee_ids',
        store=True,
    )
    approval_request_ids = fields.One2many(
        comodel_name='approval.request',
        inverse_name='collective_leave_id',
        string='ბრძანებები',
    )
    approval_request_count = fields.Integer(
        compute='_compute_approval_request_count',
    )

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
            'domain': [('collective_leave_id', '=', self.id)],
            'context': {'default_collective_leave_id': self.id},
        }

    @api.depends('collective_leave_emp_ids.is_checked')
    def _compute_employee_ids(self):
        for record in self:
            checked = record.collective_leave_emp_ids.filtered('is_checked')
            record.employee_ids = checked.mapped('employee_id')

    def action_compute_employees(self):
        for record in self:
            existing_ids = record.collective_leave_emp_ids.mapped('employee_id').ids
            employees = self.env['hr.employee'].sudo().search([
                ('department_id', '=', record.department_id.id),
                ('job_id', '=', record.job_id.id),
                ('id', 'not in', existing_ids),
            ])
            record.collective_leave_emp_ids = [
                (0, 0, {'employee_id': emp.id})
                for emp in employees
            ]

    def create_approval_request(self):
        category = self.env['approval.category'].sudo().search([('name', '=', 'შვებულება პირადი')], limit=1)
        for record in self:
            for employee in record.employee_ids:
                self.env['approval.request'].sudo().create({
                    'request_owner_id': self.env.user.id,
                    'category_id': category.id,
                    'brdzaneba_employee_id': employee.id,
                    'brdzaneba_start_date': record.start_day,
                    'brdzaneba_end_date': record.end_day,
                    'x_studio_dgeebi_real': record.days,
                    'collective_leave_id': record.id,
                })


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('collective.leave') or 'New'
        return super().create(vals_list)
