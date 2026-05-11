from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _must_check_constrains_date_sequence(self):
        # Odoo 18 enforces date-based sequences through `sequence.mixin`.
        # When we adjust valuation/accounting for already-posted stock valuation entries,
        # we may need to draft/repost moves and align dates/numbers. During that flow,
        # the (date, sequence) pair can temporarily be inconsistent.
        # We only bypass the constraint for our controlled flow.
        if self.env.context.get("dv_skip_date_sequence_constraint"):
            return False
        return super()._must_check_constrains_date_sequence()

