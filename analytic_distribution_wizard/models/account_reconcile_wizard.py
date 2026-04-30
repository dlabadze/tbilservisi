from odoo import models, fields, api


class AccountReconcileWizard(models.TransientModel):
    _inherit = 'account.reconcile.wizard'

    analytic_distribution = fields.Json(
        string='Analytic Distribution',
    )
    analytic_precision = fields.Integer(
        store=False,
        default=lambda self: self.env['decimal.precision'].precision_get('Percentage Analytic'),
    )

    def _create_write_off_lines(self, partner=None):

        commands = super(AccountReconcileWizard, self)._create_write_off_lines(partner=partner)

        if self.analytic_distribution:
            for command in commands:
                vals = command[2]

                if vals.get('account_id') == self.account_id.id:
                    vals['analytic_distribution'] = self.analytic_distribution

        return commands
