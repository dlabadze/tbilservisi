from odoo import models, fields, api


class HrEmployeeTracking(models.Model):
    _inherit = 'hr.employee'

    dep_numbering = fields.Integer(string='დეპარტამენტის ნომერი', compute = '_compute_dep_numbering')

    @api.depends('department_id')
    def _compute_dep_numbering(self):
        for employee in self:
            if employee.department_id:
                employee.dep_numbering = employee.department_id.dep_numbering or 0
            else:
                employee.dep_numbering = 0