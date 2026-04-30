from odoo import models


class AccountReconcileWizard(models.TransientModel):
    _inherit = "account.reconcile.wizard"

    def _dv_get_reconcile_lines(self):
        lines = self.env["account.move.line"]
        for field_name in ("move_line_ids", "line_ids", "account_move_line_ids"):
            if field_name in self._fields:
                lines |= self[field_name]
        return lines

    def reconcile(self):
        lines = self._dv_get_reconcile_lines()
        if lines:
            lines._dv_autofix_parent_move_sequences()
        return super().reconcile()
