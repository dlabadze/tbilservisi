from odoo import models


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def action_payslip_done(self):
        res = super(HrPayslip, self).action_payslip_done()
        assignment_rules = self.env['hr.payslip.account.filter'].search([])

        if not assignment_rules:
            return res

        for slip in self:
            if not slip.move_id:
                continue

            employee_partner = (
                    slip.employee_id.work_contact_id or
                    slip.employee_id.user_id.partner_id or
                    slip.employee_id.user_partner_id
            )

            for rule in assignment_rules:
                target_partner = rule.partner_id or employee_partner

                if not target_partner:
                    continue

                target_codes = rule.category_ids.mapped('code')
                target_slip_lines = slip.line_ids.filtered(lambda l: l.salary_rule_id.category_id.code in target_codes)

                if not target_slip_lines:
                    continue

                target_names = set(target_slip_lines.mapped('salary_rule_id.name') + target_slip_lines.mapped('name'))

                lines_to_fix = slip.move_id.line_ids.filtered(
                    lambda l: l.account_id.id in rule.account_ids.ids and l.name in target_names
                )

                if lines_to_fix:
                    lines_to_fix.write({'partner_id': target_partner.id})

        return res