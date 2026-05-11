from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _must_check_constrains_date_sequence(self):
        if self.env.context.get("dv_skip_date_sequence_constraint"):
            return False
        return super()._must_check_constrains_date_sequence()

