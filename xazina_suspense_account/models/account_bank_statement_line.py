from odoo import models, api

JOURNAL_CODE = 'BNK15'
SUSPENSE_CODE = '1243'

class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    def _get_default_journal(self):
        return super()._get_default_journal()

    def _prepare_move_line_default_vals(self, counterpart_account_id=None):

        vals_list = super()._prepare_move_line_default_vals(
            counterpart_account_id=counterpart_account_id
        )

        if self.journal_id.code != JOURNAL_CODE:
            return vals_list

        treasury_suspense = self.env['account.account'].search([
            ('code', '=', SUSPENSE_CODE),
            ('company_ids', 'in', self.company_id.id),
        ], limit=1)

        if not treasury_suspense:
            return vals_list

        default_suspense_id = self.journal_id.suspense_account_id.id

        for line_vals in vals_list:
            if line_vals.get('account_id') == default_suspense_id:
                line_vals['account_id'] = treasury_suspense.id

        return vals_list
