# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError


PICKING_BASIS_FIELD = 'x_studio_text_field_75h_1j6i8foen'
ACCOUNT_MOVE_BASIS_FIELD = 'basis'


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    stock_account_corr_id = fields.Many2one(
        'account.account',
        string='Debit Correction Account',
        domain="[('deprecated', '=', False)]",
        help='Debit account to use on stock accounting entries when a move-specific account is not set.',
        check_company=True,
    )

    analytic_distribution_corr = fields.Json(
        string='Analytic Distribution',
        help='Analytic distribution to apply on the corrected debit line when a move-specific distribution is not set.',
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

    @api.depends('picking_type_id.code')
    def _compute_is_internal_transfer_corr(self):
        for picking in self:
            picking.is_internal_transfer_corr = picking.picking_type_id.code == 'internal'

    def _get_account_move_basis_vals_corr(self):
        self.ensure_one()
        if (
            PICKING_BASIS_FIELD not in self._fields
            or ACCOUNT_MOVE_BASIS_FIELD not in self.env['account.move']._fields
        ):
            return {}
        return {ACCOUNT_MOVE_BASIS_FIELD: self[PICKING_BASIS_FIELD]}

    def action_correct_debit_account_entries(self):
        self.ensure_one()

        if self.picking_type_id.code != 'internal':
            raise UserError(_('This action is only available for Internal Transfers.'))

        if self.state != 'done':
            raise UserError(_('Picking must be in Done state to correct debit accounts.'))

        if self.location_dest_id.usage != 'inventory':
            raise UserError(_(
                'Debit account correction is only available for operations where destination location is Inventory Loss. '
                'Current destination location: %s'
            ) % self.location_dest_id.display_name)

        corrected_lines = self.env['account.move.line']
        moves_without_account = self.env['stock.move']
        moves_without_lines = self.env['stock.move']

        for move in self.move_ids.filtered('product_id'):
            correction_account = move._get_debit_correction_account()
            if not correction_account:
                moves_without_account |= move
                continue

            move_lines = move._get_related_account_move_lines_corr().filtered(
                lambda line: line.move_id.state == 'posted' and line.balance > 0
            )
            if not move_lines:
                moves_without_lines |= move
                continue

            base_distribution = move._get_debit_correction_analytic_distribution() or {}
            for line in move_lines:
                line_vals = {'account_id': correction_account.id}
                merged = {**base_distribution}
                if line.analytic_distribution:
                    merged.update(line.analytic_distribution)
                if merged:
                    line_vals['analytic_distribution'] = merged
                line.with_context(check_move_validity=False).write(line_vals)
                corrected_lines |= line

        basis_vals = self._get_account_move_basis_vals_corr()
        if basis_vals and corrected_lines:
            corrected_lines.mapped('move_id').write(basis_vals)

        if moves_without_account:
            move_names = '\n'.join([
                f"- {move.name} ({move.product_id.display_name})"
                for move in moves_without_account
            ])
            raise UserError(_(
                'Please set debit correction account for all moves.\n\n'
                'For each move, set either:\n'
                '- Debit Correction Account on the move, OR\n'
                '- Debit Correction Account on the picking\n\n'
                'Moves without account:\n%s'
            ) % move_names)

        if not corrected_lines:
            if moves_without_lines:
                raise UserError(_('No posted debit accounting lines were found for this picking.'))
            raise UserError(_('No debit lines were corrected.'))

        action = {
            'type': 'ir.actions.act_window',
            'name': _('Corrected Journal Entries'),
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'target': 'current',
            'domain': [('id', 'in', corrected_lines.mapped('move_id').ids)],
        }
        if len(corrected_lines.mapped('move_id')) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': corrected_lines.move_id.id,
                'domain': [],
            })
        return action
