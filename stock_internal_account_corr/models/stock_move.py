# -*- coding: utf-8 -*-

from odoo import api, fields, models


PICKING_BASIS_FIELD = 'x_studio_text_field_75h_1j6i8foen'
ACCOUNT_MOVE_BASIS_FIELD = 'basis'


class StockMove(models.Model):
    _inherit = 'stock.move'

    move_account_corr_id = fields.Many2one(
        'account.account',
        string='Debit Correction Account',
        domain="[('deprecated', '=', False)]",
        help='Debit account to use on this move stock accounting entries. If empty, the picking account is used.',
        check_company=True,
    )

    analytic_distribution_corr = fields.Json(
        string='Analytic Distribution',
        help='Analytic distribution to apply on this move corrected debit line. If empty, the picking distribution is used.',
    )

    analytic_precision = fields.Integer(
        store=False,
        default=lambda self: self.env['decimal.precision'].precision_get('Percentage Analytic'),
    )

    is_internal_transfer_corr = fields.Boolean(
        string='Is Internal Transfer',
        compute='_compute_is_internal_transfer_corr',
        store=True,
    )

    @api.depends('picking_id.picking_type_id.code')
    def _compute_is_internal_transfer_corr(self):
        for move in self:
            move.is_internal_transfer_corr = (
                move.picking_id
                and move.picking_id.picking_type_id.code == 'internal'
            )

    def _get_debit_correction_account(self):
        self.ensure_one()
        if not self.picking_id or self.picking_id.picking_type_id.code != 'internal':
            return self.env['account.account']
        if self.picking_id.location_dest_id.usage != 'inventory':
            return self.env['account.account']
        return self.move_account_corr_id or self.picking_id.stock_account_corr_id

    def _get_debit_correction_analytic_distribution(self):
        self.ensure_one()
        if self.move_account_corr_id:
            return self.analytic_distribution_corr or self.picking_id.analytic_distribution_corr
        return self.picking_id.analytic_distribution_corr

    def _get_debit_correction_basis_vals(self):
        self.ensure_one()
        if (
            not self.picking_id
            or PICKING_BASIS_FIELD not in self.picking_id._fields
            or ACCOUNT_MOVE_BASIS_FIELD not in self.env['account.move']._fields
        ):
            return {}
        return {ACCOUNT_MOVE_BASIS_FIELD: self.picking_id[PICKING_BASIS_FIELD]}

    def _get_related_account_move_lines_corr(self):
        self.ensure_one()
        account_moves = self.env['account.move']
        if 'account_move_ids' in self._fields:
            account_moves |= self.account_move_ids

        valuation_layers = self.env['stock.valuation.layer'].search([
            ('stock_move_id', '=', self.id),
        ])
        account_moves |= valuation_layers.mapped('account_move_id')
        return account_moves.line_ids

    def _prepare_account_move_line(self, qty, cost, credit_account_id, debit_account_id, svl_id, description):
        self.ensure_one()
        correction_account = self._get_debit_correction_account()
        if correction_account:
            debit_account_id = correction_account.id

        move_lines = super()._prepare_account_move_line(
            qty, cost, credit_account_id, debit_account_id, svl_id, description
        )

        analytic_distribution = self._get_debit_correction_analytic_distribution() if correction_account else False
        if correction_account and analytic_distribution:
            for command in move_lines:
                if not isinstance(command, (list, tuple)) or len(command) < 3:
                    continue
                line_vals = command[2]
                if not isinstance(line_vals, dict):
                    continue
                if line_vals.get('account_id') == correction_account.id:
                    line_vals['analytic_distribution'] = analytic_distribution

        return move_lines

    def _prepare_account_move_vals(self, credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost):
        vals = super()._prepare_account_move_vals(
            credit_account_id, debit_account_id, journal_id, qty, description, svl_id, cost
        )
        vals.update(self._get_debit_correction_basis_vals())
        return vals
