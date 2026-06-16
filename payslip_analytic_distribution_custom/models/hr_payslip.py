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

    x_worked_days_attendance = fields.Float(string="ნამუშევარი დღეები", compute='_compute_x_attendance_rate', store=True)
    x_worked_days_rate = fields.Float(string="დღიური ხელფასი", compute='_compute_x_attendance_rate', store=True)

    @api.depends('payslip_id.employee_id', 'payslip_id.date_from', 'payslip_id.date_to', 'payslip_id.contract_id.wage')
    def _compute_x_attendance_rate(self):
        for wd in self:
            payslip = wd.payslip_id
            if not payslip or not payslip.employee_id or not payslip.date_from or not payslip.date_to:
                wd.x_worked_days_attendance = 0.0
                wd.x_worked_days_rate = 0.0
                continue
                
            date_from = payslip.date_from
            date_to = payslip.date_to
            employee = payslip.employee_id
            contract = payslip.contract_id

            if date_from.month == 12:
                next_month = date_from.replace(year=date_from.year + 1, month=1, day=1)
            else:
                next_month = date_from.replace(month=date_from.month + 1, day=1)

            days_in_month = (next_month - date_from.replace(day=1)).days

            attendances = self.env['hr.attendance'].search([
                ('employee_id', '=', employee.id),
                ('check_in', '>=', date_from),
                ('check_in', '<=', date_to)
            ])

            d_days = set() 
            num_x = 0

            for att in attendances:
                if att.check_in:
                    day = att.check_in.date()
                    if att.x_studio_selection_field_99n_1j76jab36 == 'D':
                        d_days.add(day)
                    if att.x_studio_selection_field_99n_1j76jab36 == 'X':
                        num_x += 1
                        
            wd.x_worked_days_attendance = num_x
            
            effective_days = days_in_month - len(d_days)

            if effective_days > 0 and contract:
                result = contract.wage / effective_days
            else:
                result = 0.0 
                
            wd.x_worked_days_rate = result