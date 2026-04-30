# -*- coding: utf-8 -*-

from odoo import models, fields, api


class StockMove(models.Model):
    _inherit = 'stock.move'

    move_account_ang = fields.Many2one(
        'account.account',
        string='Reconciliation Account',
        domain="[('deprecated', '=', False)]",
        help='Account to use for reconciliation of this move\'s accounting entries. '
             'If not set, the Stock Account from picking will be used.',
        check_company=True,
    )
    
    analytic_distribution = fields.Json(
        string='Analytic Distribution',
        help='Analytic distribution to be used for reconciliation of this move\'s accounting entries. '
             'If not set, the Analytic Distribution from picking will be used.',
    )
    
    analytic_precision = fields.Integer(
        store=False,
        default=lambda self: self.env['decimal.precision'].precision_get('Percentage Analytic'),
    )

    @api.depends('picking_id.picking_type_id.code')
    def _compute_is_internal(self):
        """Compute if move is part of internal transfer"""
        for move in self:
            move.is_internal_transfer = (
                move.picking_id and 
                move.picking_id.picking_type_id.code == 'internal'
            )

    is_internal_transfer = fields.Boolean(
        string='Is Internal Transfer',
        compute='_compute_is_internal',
        store=True,
    )

