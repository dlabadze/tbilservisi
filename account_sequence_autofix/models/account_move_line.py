from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _dv_autofix_parent_move_sequences(self):
        moves = self.mapped("move_id").filtered(lambda move: move.state == "posted")
        if moves:
            moves.with_context(
                dv_skip_sequence_autofix=True,
                dv_skip_sequence_autofix_constraint=True,
                dv_skip_date_sequence_constraint=True,
                check_move_validity=False,
                skip_account_move_synchronization=True,
                skip_readonly_check=True,
            )._dv_autofix_date_sequence()
        return True

    def action_reconcile(self):
        self._dv_autofix_parent_move_sequences()
        return super().action_reconcile()

    def reconcile(self):
        if self:
            self._dv_autofix_parent_move_sequences()
        return super().reconcile()
