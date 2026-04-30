# -*- coding: utf-8 -*-
from odoo import models


class XazinaExtend(models.Model):
    _inherit = 'xazina'

    def action_open_purchase_requisition_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Select Purchase Requisition',
            'res_model': 'xazina.purchase.requisition.wizard',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {
                'default_xazina_id': self.id,
            },
        }
