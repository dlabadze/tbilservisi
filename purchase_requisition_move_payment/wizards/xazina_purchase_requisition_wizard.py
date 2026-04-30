# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class XazinaPurchaseRequisitionWizard(models.TransientModel):
    _name = 'xazina.purchase.requisition.wizard'
    _description = 'Xazina Purchase Requisition Wizard'

    xazina_id = fields.Many2one(
        'xazina',
        string='Xazina Record',
        required=True,
        readonly=True,
    )

    transaction_amount = fields.Float(
        string='Transaction Amount',
        related='xazina_id.amount_in_gel',
        readonly=True,
        digits=(16, 2),
    )

    purchase_requisition_id = fields.Many2one(
        'purchase.requisition',
        string='Purchase Requisition',
        required=True,
    )

    current_paid_amount = fields.Float(
        string='Current Paid Amount',
        compute='_compute_current_paid_amount',
        readonly=True,
        digits=(16, 2),
    )

    new_paid_amount = fields.Float(
        string='New Paid Amount',
        compute='_compute_new_paid_amount',
        readonly=True,
        digits=(16, 2),
    )

    @api.depends('purchase_requisition_id', 'purchase_requisition_id.paid_amount')
    def _compute_current_paid_amount(self):
        for wizard in self:
            req = wizard.purchase_requisition_id
            wizard.current_paid_amount = req.paid_amount if req else 0.0

    @api.depends('current_paid_amount', 'transaction_amount')
    def _compute_new_paid_amount(self):
        for wizard in self:
            wizard.new_paid_amount = wizard.current_paid_amount + abs(wizard.transaction_amount or 0.0)

    def action_confirm(self):
        self.ensure_one()
        if not self.purchase_requisition_id:
            raise UserError('Please select a Purchase Requisition.')

        contract_amount = self.purchase_requisition_id.contract_amount or 0.0
        remaining_amount = contract_amount - self.new_paid_amount

        self.purchase_requisition_id.write({
            'paid_amount': self.new_paid_amount,
            'remaining_amount': remaining_amount,
        })

        _logger.info(
            'Updated purchase.requisition %s: paid_amount from %s to %s, remaining_amount to %s (xazina: %s)',
            self.purchase_requisition_id.id,
            self.current_paid_amount,
            self.new_paid_amount,
            remaining_amount,
            self.xazina_id.id,
        )

        return {'type': 'ir.actions.act_window_close'}

    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}
