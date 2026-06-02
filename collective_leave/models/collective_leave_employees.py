from odoo import fields, models


class CollectiveLeaveEmployees(models.Model):
    _name = 'collective.leave.employees'
    _description = 'Collective Leave Employees'

    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string='თანამშრომელი',
    )
    department_id = fields.Many2one(
        related='employee_id.department_id',
        string='სამსახური',
        store=True,
    )
    job_id = fields.Many2one(
        related='employee_id.job_id',
        string='თანამდებობა',
        store=True,
    )
    collective_leave_id = fields.Many2one(
        comodel_name='collective.leave',
        string='კოლექტიური შვებულება',
    )
    is_checked = fields.Boolean(
        string='მონიშვნა',
        default=False,
    )
