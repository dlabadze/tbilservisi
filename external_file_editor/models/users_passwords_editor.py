from odoo import fields, models


class UsersPasswordsForEditor(models.Model):
    _name = 'users.passwords.for.editor'
    _description = 'User Passwords for File Editor'

    user_id = fields.Many2one('res.users', string='User', required=True, ondelete='cascade')
    password = fields.Char(string='Password')
