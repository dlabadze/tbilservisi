# -*- coding: utf-8 -*-

from odoo import _, fields, models
from odoo.exceptions import UserError


class AccountMoveRepostDateChangeWizard(models.TransientModel):
    _name = 'account.move.repost.date.change.wizard'
    _description = 'Repost Account Moves With New Date'

    date = fields.Date(
        string='New Accounting Date',
        required=True,
        default=fields.Date.context_today,
    )
    renumber_mode = fields.Selection(
        selection=[
            ('auto', 'Renumber only if the old number does not match the new date'),
            ('always', 'Always assign a new number'),
        ],
        string='Numbering',
        required=True,
        default='auto',
    )
    allow_unreconcile = fields.Boolean(
        string='Allow removing reconciliations',
        help='Resetting a reconciled entry to draft removes its payment/reconciliation links.',
    )

    def _get_active_moves(self):
        if self.env.context.get('active_model') != 'account.move':
            raise UserError(_('This action can only be used from journal entries.'))

        moves = self.env['account.move'].browse(self.env.context.get('active_ids', [])).exists()
        if not moves:
            raise UserError(_('Please select at least one journal entry.'))
        return moves

    def _check_moves_can_be_reposted(self, moves):
        not_posted = moves.filtered(lambda move: move.state != 'posted')
        if not_posted:
            raise UserError(_(
                'Only posted journal entries can be reposted with this action.\n'
                'Not posted entries: %s'
            ) % ', '.join(not_posted.mapped('display_name')))

        locked = moves.filtered('inalterable_hash')
        if locked:
            raise UserError(_(
                'Locked journal entries cannot be reset to draft.\n'
                'Locked entries: %s'
            ) % ', '.join(locked.mapped('display_name')))

        cancel_request_moves = moves.filtered('need_cancel_request')
        if cancel_request_moves:
            raise UserError(_(
                'Some entries require a cancellation request before they can be reset to draft.\n'
                'Entries: %s'
            ) % ', '.join(cancel_request_moves.mapped('display_name')))

        reconciled_moves = moves.filtered(
            lambda move: any(
                line.reconciled or line.matched_debit_ids or line.matched_credit_ids
                for line in move.line_ids
            )
        )
        if reconciled_moves and not self.allow_unreconcile:
            raise UserError(_(
                'Some entries are reconciled. Resetting them to draft will remove payment/reconciliation links.\n'
                'Enable "Allow removing reconciliations" if you still want to continue.\n'
                'Entries: %s'
            ) % ', '.join(reconciled_moves.mapped('display_name')))

        for move in moves:
            lock_dates = move._get_violated_lock_dates(self.date, move._affect_tax_report())
            if lock_dates:
                lock_date_info = self.env['res.company']._format_lock_dates(lock_dates)
                raise UserError(_(
                    'The new date is locked for %(entry)s.\n'
                    'Please choose a date after: %(lock_date_info)s.'
                ) % {
                    'entry': move.display_name,
                    'lock_date_info': lock_date_info,
                })

    def action_repost_with_new_date(self):
        self.ensure_one()

        moves = self._get_active_moves()
        moves.check_access('write')
        self._check_moves_can_be_reposted(moves)

        processed_count = 0
        for move in moves.sorted(lambda move: (move.date, move.id)):
            move = move.with_company(move.company_id).with_context(
                dv_repost_date_skip_sequence_constraint=True,
                skip_readonly_check=True,
                check_move_validity=False,
                skip_account_move_synchronization=True,
            )

            with self.env.cr.savepoint():
                move.button_draft()
                move.write({'date': self.date})

                if self.renumber_mode == 'always' or not move._sequence_matches_date():
                    move._dv_clear_sequence_for_repost_date()

                move.with_context(
                    dv_repost_date_skip_sequence_constraint=True,
                    skip_readonly_check=True,
                )._post(soft=False)
                processed_count += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Entries Reposted'),
                'message': _('%s journal entry(ies) were reposted with the new date.') % processed_count,
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
