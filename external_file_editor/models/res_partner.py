from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    password_fileeditor = fields.Char(string='File Editor Password')
