from odoo import fields, api, models


class CollectiveChangePositionEmps(models.Model):
    _name = 'collective.change.position.emps'
    _description = 'Collective Change Position Emps'

    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string='თანამშრომელი',
    )
    collective_change_position_id = fields.Many2one(
        comodel_name='collective.change.position',
        string='კოლექტიური რეგისტრაცია',
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
    is_checked = fields.Boolean(
        string='მონიშვნა',
        default=False,
    )
