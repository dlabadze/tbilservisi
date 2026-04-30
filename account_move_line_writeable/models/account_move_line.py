from odoo import models, fields, api

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self._sync_price_from_debit_credit(vals)
        return super().create(vals_list)

    def write(self, vals):
        self._sync_price_from_debit_credit(vals)
        return super().write(vals)

    @api.model
    def _sync_price_from_debit_credit(self, vals):

        debit = vals.get('debit')
        credit = vals.get('credit')

        if debit is not None and debit != 0.0:
            vals['price_unit'] = debit
            vals['quantity'] = 1.0

        elif credit is not None and credit != 0.0:
            vals['price_unit'] = -credit
            vals['quantity'] = 1.0