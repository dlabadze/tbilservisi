from odoo import models, fields, api


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    journal_entry_date = fields.Date(
        string='Journal Entry Date',
        help="Force a specific date for the Journal Entry of this payslip."
    )

    def _action_create_account_move(self):
        res = super(HrPayslip, self)._action_create_account_move()
        for slip in self:
            target_date = slip.journal_entry_date or (
                    slip.payslip_run_id and slip.payslip_run_id.journal_entry_date)

            if target_date:
                move = slip.move_id
                if move and move.date != target_date:

                    if move.state == 'draft':
                        move.write({'date': target_date})

                    elif move.state == 'posted':
                        move.button_draft()
                        move.write({'date': target_date})

        return res

    def _get_payslip_lines(self):
        lines = super()._get_payslip_lines()
        for line in lines:
            rule = self.env['hr.salary.rule'].browse(line.get('salary_rule_id'))
            if rule:
                line['name'] = rule.name
        return lines