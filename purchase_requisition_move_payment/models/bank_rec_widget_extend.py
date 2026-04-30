# -*- coding: utf-8 -*-
from odoo import models, fields, api


class BankRecWidgetExtend(models.AbstractModel):
    _inherit = 'bank.rec.widget'

    show_purchase_requisition_button = fields.Boolean(
        string='Show Purchase Requisition Button',
        compute='_compute_show_purchase_requisition_button',
    )

    @api.depends('state')
    def _compute_show_purchase_requisition_button(self):
        for wizard in self:
            wizard.show_purchase_requisition_button = wizard.state == 'valid'

    def action_open_purchase_requisition_wizard(self):
        self.ensure_one()
        if not self.st_line_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': 'Select Purchase Requisition',
            'res_model': 'purchase.requisition.payment.wizard',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {
                'default_st_line_id': self.st_line_id.id,
            },
        }
