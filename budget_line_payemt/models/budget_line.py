from odoo import api, fields, models


class BudgetLine(models.Model):
    _inherit = 'budget.line'

    payment_move_line_ids = fields.Many2many(
        'account.move.line',
        compute='_compute_payment_move_line_ids',
        string='Payments',
        store=False,
    )

    @staticmethod
    def _extract_distribution_account_ids(analytic_distribution):
        account_ids = set()
        if not isinstance(analytic_distribution, dict):
            return account_ids

        for key in analytic_distribution.keys():
            key_parts = str(key).split(',')
            for key_part in key_parts:
                key_part = key_part.strip()
                if key_part.isdigit():
                    account_ids.add(int(key_part))
        return account_ids

    @api.depends('account_id')
    def _compute_payment_move_line_ids(self):
        empty_lines = self.env['account.move.line']
        records_with_account = self.filtered('account_id')
        account_ids = set(records_with_account.mapped('account_id').ids)

        distribution_map = {account_id: empty_lines for account_id in account_ids}
        if account_ids:
            candidate_lines = self.env['account.move.line'].search([
                ('analytic_distribution', '!=', False)
            ])
            for line in candidate_lines:
                analytic_account_ids = self._extract_distribution_account_ids(line.analytic_distribution)
                for analytic_account_id in analytic_account_ids:
                    if analytic_account_id in distribution_map:
                        distribution_map[analytic_account_id] |= line

        for record in self:
            if not record.account_id:
                record.payment_move_line_ids = False
                continue
            record.payment_move_line_ids = distribution_map.get(record.account_id.id, empty_lines)

    def action_open_budget_line_form(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Budget Line',
            'res_model': 'budget.line',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'current',
        }

    def action_view_payments(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Payments',
            'res_model': 'account.move.line',
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.payment_move_line_ids.ids)],
            'target': 'current',
        }
