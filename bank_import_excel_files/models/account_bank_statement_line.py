from odoo import models, fields, api,_

class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    saidentifikacio_code = fields.Char(string='საიდენტიფიკაციო კოდი')


    @api.depends('partner_id', 'name', 'date')
    def _compute_display_name(self):
        for line in self:
            if line.partner_id:
                line.display_name = f"{line.partner_id.name} - {line.name or ''}"
            else:
                line.display_name = line.name or _("Statement Line")