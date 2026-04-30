from odoo import models, fields


class AccountAccount(models.Model):
    _inherit = 'account.account'

    is_non_partner_account = fields.Boolean(string='Is Non Partner Account', default=False)
    is_product_account = fields.Boolean(string='Is Product Account', default=False)
    is_partner_and_sub_account = fields.Boolean(string='Is Partner and Sub Account', default=False)
    is_partner_account = fields.Boolean(string='Is Partner Account', default=False)
    also_include_in_report = fields.Boolean(string='Also Include in Report', default=False)

    child_ids = fields.Many2many(
        'account.account',
        'account_account_hierarchy_rel',
        'parent_account_id',
        'child_account_id',
        string='Sub Accounts',
    )
