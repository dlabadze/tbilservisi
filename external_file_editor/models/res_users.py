from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    password_fileeditor = fields.Char(string='File Editor Password')
