from odoo import fields, models, api, _
from odoo.exceptions import UserError


class SalaryImport(models.Model):
    _inherit = 'salary.import'


    def action_generate_excel(self):
        lines = self.env['salary.import.line'].search([('import_id', 'in', self.ids)])
        raise UserError(lines)
