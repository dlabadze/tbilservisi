# -*- coding: utf-8 -*-

from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _must_check_constrains_date_sequence(self):
        if self.env.context.get('dv_repost_date_skip_sequence_constraint'):
            return False
        return super()._must_check_constrains_date_sequence()

    def _dv_clear_sequence_for_repost_date(self):
        """Clear the assigned number so Odoo can assign one for the new date."""
        for move in self:
            vals = {}
            if move.name and move.name != '/':
                vals['name'] = '/'
            if 'sequence_prefix' in move._fields and move.sequence_prefix:
                vals['sequence_prefix'] = False
            if 'sequence_number' in move._fields and move.sequence_number:
                vals['sequence_number'] = False

            if vals:
                move.with_context(
                    check_move_validity=False,
                    skip_account_move_synchronization=True,
                    skip_readonly_check=True,
                    dv_repost_date_skip_sequence_constraint=True,
                ).write(vals)
