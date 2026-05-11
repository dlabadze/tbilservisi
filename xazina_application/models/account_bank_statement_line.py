from odoo import models, fields


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    xazina_id = fields.Many2one(
        'xazina',
        string='ხაზინა',
        ondelete='set null',
        index=True,
    )

    def unlink(self):
        xazina_records = self.mapped('xazina_id').filtered(lambda x: x.state == 'validated')
        result = super().unlink()
        if xazina_records:
            xazina_records.write({'state': 'draft'})
        return result
