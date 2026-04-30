from odoo import models, fields, api

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    approval_count = fields.Integer(compute='_compute_approval_count', string='Approval Count')

    def _compute_approval_count(self):
        for employee in self:
            employee.approval_count = self.env['approval.request'].search_count([
                ('brdzaneba_employee_id', '=', employee.id)
            ])

    # def action_open_employee_approvals(self):
    #     self.ensure_one()
    #     return {
    #         'name': 'Employee Approvals',
    #         'type': 'ir.actions.act_window',
    #         'res_model': 'approval.request',
    #         'view_mode': 'list,form',
    #         'domain': [('brdzaneba_employee_id', '=', self.id)],
    #         'context': {'default_brdzaneba_employee_id': self.id},
    #         'target': 'current',
    #     }

    def action_open_employee_approvals(self):
        self.ensure_one()
        return {
            'name': 'Employee Approvals',
            'type': 'ir.actions.act_window',
            'res_model': 'approval.request',
            'view_mode': 'list,form',
            'context': {
                'search_default_filter_brdzaneba_employee': 1,
                'default_brdzaneba_employee_id': self.id,
            },
            'target': 'current',
        }

