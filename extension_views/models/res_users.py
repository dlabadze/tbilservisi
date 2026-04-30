from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'

    rs_acc = fields.Char(string='rs.ge ექაუნთი')
    rs_pass = fields.Char(string='rs.ge პაროლი')
    rs_fasi = fields.Boolean(string='რს ფასის გადაცემა შიდა გადაზიდვაზე')
