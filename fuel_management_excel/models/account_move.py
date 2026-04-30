from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = 'account.move'

    fuel_management_id = fields.Many2one('fuel.management', string='Fuel Management', readonly=True)