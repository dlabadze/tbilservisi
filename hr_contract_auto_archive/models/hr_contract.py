from odoo import models, fields, api

class HrContract(models.Model):
    _inherit = 'hr.contract'

    @api.model
    def _cron_archive_expired_employees(self):
        today = fields.Date.today()
        expired_contracts = self.search([
            ('date_end', '<', today),
            ('state', '!=', 'cancel'),
            ('employee_id.active', '=', True),
        ])
        employees_to_archive = expired_contracts.mapped('employee_id')
        for employee in employees_to_archive:
            active_contracts = self.search([
                ('employee_id', '=', employee.id),
                ('date_end', '>=', today),
                ('state', 'not in', ['cancel']),
            ])
            if not active_contracts:
                employee.active = False