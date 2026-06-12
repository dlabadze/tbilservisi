from odoo import models, fields


class HrJob(models.Model):
    _inherit = 'hr.job'

    department_id = fields.Many2one('hr.department', tracking=True)
    no_of_recruitment = fields.Float(tracking=True)
    x_studio_expected_salary = fields.Float(tracking=True)
    name = fields.Char(tracking=True)
    date = fields.Date(tracking=True, string='თარიღი')

