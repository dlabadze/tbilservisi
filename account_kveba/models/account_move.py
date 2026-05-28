from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = 'account.move'


    def action_create_picking_chamowera(self):
        pass