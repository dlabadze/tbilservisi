from odoo import models, fields, api, _

class Employee(models.Model):
    _inherit = 'hr.employee'

    leave_manager_id = fields.Many2one(
        'res.users',
        string="Leave Manager",
        ondelete='set null',
        tracking=True,
        help=(
            'Select the user responsible for approving "Time Off" of this employee.\n'
            'If empty, the approval is done by an Administrator or Approver '
            '(determined in settings/users).'
        ),
    )


class EmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    leave_manager_id = fields.Many2one(
        'res.users',
        string="Leave Manager",
        readonly=True,
    )