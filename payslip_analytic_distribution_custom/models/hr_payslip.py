from odoo import models
import logging
_logger = logging.getLogger(__name__)

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def _action_create_account_move(self):
        res = super(HrPayslip, self)._action_create_account_move()
        for slip in self:
            move = slip.move_id
            if move:
                was_posted = move.state == 'posted'
                if was_posted:
                    move.button_draft()

                for line in move.line_ids:
                    if line.account_id and line.account_id.code == '3139':
                        account_ids = []

                        # Plan - დეპარტამენტი
                        department = slip.contract_id.department_id
                        if department:
                            dept_display = department.with_context(lang='ka_GE').display_name
                            dept_name = dept_display.split('/')[0].strip()
                            dept_analytic = self.env['account.analytic.account'].search([
                                ('name', '=', dept_name),
                            ], limit=1)
                            if dept_analytic:
                                account_ids.append(str(dept_analytic.id))
                            else:
                                _logger.warning("NO DEPT ANALYTIC FOUND FOR: %s", dept_name)

                        studio_depname = slip.contract_id.x_studio_depname
                        if studio_depname:
                            service_analytic = self.env['account.analytic.account'].search([
                                ('name', '=', studio_depname),
                                ('plan_id.name', '=', 'სამსახური'),
                            ], limit=1)
                            if service_analytic:
                                account_ids.append(str(service_analytic.id))
                            else:
                                _logger.warning("NO SERVICE ANALYTIC FOUND FOR: %s", studio_depname)

                        if account_ids:
                            # Combine IDs into a single comma-separated key for one line
                            combined_key = ",".join(account_ids)
                            distribution = {combined_key: 100.0}
                            line.write({'analytic_distribution': distribution})

                if was_posted:
                    move.action_post()
        return res