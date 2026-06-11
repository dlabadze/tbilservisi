from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    kveba_gadakhurva_debit_account_id = fields.Many2one(
        'account.account',
        string='გადახურვა დებეტი',
        check_company=True,
    )
    kveba_gadakhurva_credit_account_id = fields.Many2one(
        'account.account',
        string='გადახურვა კრედიტი',
        check_company=True,
    )


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    kveba_gadakhurva_debit_account_id = fields.Many2one(
        related='company_id.kveba_gadakhurva_debit_account_id',
        string='გადახურვა დებეტი',
        readonly=False,
    )
    kveba_gadakhurva_credit_account_id = fields.Many2one(
        related='company_id.kveba_gadakhurva_credit_account_id',
        string='გადახურვა კრედიტი',
        readonly=False,
    )
