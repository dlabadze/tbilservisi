from odoo import fields, api, models


class CollectiveDanishvnaEmps(models.Model):
    _name = 'collective.danishvna.emps'
    _description = 'Collective Danishvna Emps'

    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string='თანამშრომელი',
    )
    collective_danishvna_id = fields.Many2one(
        comodel_name='collective.danishvna',
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

