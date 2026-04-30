from odoo import models, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    def _get_sequence_format_param(self, previous_group):
        if self.move_type == 'in_invoice' and self.invoice_date:
            original_date = self.date
            try:
                self.date = self.invoice_date
                return super(AccountMove, self)._get_sequence_format_param(previous_group)
            finally:
                self.date = original_date

        return super(AccountMove, self)._get_sequence_format_param(previous_group)

    @api.depends('posted_before', 'state', 'journal_id', 'date', 'invoice_date')
    def _compute_name(self):
        super(AccountMove, self)._compute_name()