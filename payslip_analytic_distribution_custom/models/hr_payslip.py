from odoo import models, fields, api
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
                            combined_key = ",".join(account_ids)
                            distribution = {combined_key: 100.0}
                            line.write({'analytic_distribution': distribution})

                if was_posted:
                    move.action_post()
        return res


class HrPayslipWorkedDays(models.Model):
    _inherit = 'hr.payslip.worked_days'
    x_worked_days_attendance = fields.Float(string="ნამუშევარი დღეების რაოდენობა", compute='_compute_x_attendance_rate', store=True)
    x_worked_days_rate = fields.Float(string="Rate", compute='_compute_x_attendance_rate', store=True)

    @api.depends('payslip_id.employee_id', 'payslip_id.date_from', 'payslip_id.date_to', 'payslip_id.contract_id.wage',
                 'payslip_id.worked_days_line_ids.number_of_days')
    def _compute_x_attendance_rate(self):
        for wd in self:
            slip = wd.payslip_id
            if not slip or not slip.employee_id or not slip.date_from or not slip.date_to:
                wd.x_worked_days_attendance = 0.0
                wd.x_worked_days_rate = 0.0
                continue

            attendances = self.env['hr.attendance'].search([
                ('employee_id', '=', slip.employee_id.id),
                ('check_in', '>=', slip.date_from),
                ('check_out', '<=', slip.date_to),
                ('x_studio_selection_field_99n_1j76jab36', '=', 'X')
            ])
            num_x = len(attendances)
            wd.x_worked_days_attendance = num_x

            if num_x > 0 and slip.contract_id:
                # Sum of number_of_days in worked_days_line_ids
                total_days = sum(line.number_of_days for line in slip.worked_days_line_ids)
                if total_days > 0:
                    wd.x_worked_days_rate = (slip.contract_id.wage / total_days) * num_x
                else:
                    wd.x_worked_days_rate = 0.0
            else:
                wd.x_worked_days_rate = 0.0