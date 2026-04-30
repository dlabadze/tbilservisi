from odoo import models, fields

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    rs_acc = fields.Char(string='rs.ge ექაუნთი')
    rs_pass = fields.Char(string='rs.ge პაროლი')
