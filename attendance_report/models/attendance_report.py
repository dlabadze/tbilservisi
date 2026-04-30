from odoo import models, api, fields
import calendar
from datetime import timedelta


class AttendanceReport(models.AbstractModel):
    _name = 'report.attendance_report.attendance_report_template'

    @api.model
    def _get_report_values(self, docids, data=None):
        wizards = self.env['attendance.report.wizard'].browse(docids)
        if not wizards:
            return {}
        wizard = wizards[0]

        month_start = wizard.date.replace(day=1)
        last_day = calendar.monthrange(month_start.year, month_start.month)[1]
        next_month_start = month_start + timedelta(days=last_day)

        domain = []
        if wizard.employee_ids:
            domain.append(('id', 'in', wizard.employee_ids.ids))
        else:
            if wizard.department_id:
                domain.append(('department_id', '=', wizard.department_id.id))
            if wizard.job_id:
                domain.append(('job_id', '=', wizard.job_id.id))

        employees = self.env['hr.employee'].search(domain)
        report_data = []

        totals = {
            'x': 0, 'b': 0, 'd': 0, 'g': 0, 's': 0, 'empty': 0, 'hours': 0
        }

        for emp in employees:
            attendances = self.env['hr.attendance'].search([
                ('employee_id', '=', emp.id),
                ('check_in', '>=', month_start),
                ('check_in', '<', next_month_start)
            ])

            day_map = {att.check_in.day: att.x_studio_selection_field_99n_1j76jab36 for att in attendances if
                       att.check_in}

            vals = [v for v in day_map.values() if v]

            line_x = vals.count('X')
            line_b = vals.count('B')
            line_d = vals.count('D')
            line_g = vals.count('G')
            line_s = vals.count('S')
            line_empty = last_day - len(vals)

            report_data.append({
                'name': emp.name,
                'job': emp.job_id.name or '',
                'identification_id': emp.identification_id or '',
                'days': day_map,
                'total_x': line_x,
                'total_b': line_b,
                'total_d': line_d,
                'total_g': line_g,
                'total_s': line_s,
                'total_empty': line_empty
            })

            totals['x'] += line_x
            totals['b'] += line_b
            totals['d'] += line_d
            totals['g'] += line_g
            totals['s'] += line_s
            totals['empty'] += line_empty
            totals['hours'] += sum(attendances.mapped('worked_hours'))

        georgian_months = {
            1: 'იანვარი', 2: 'თებერვალი', 3: 'მარტი', 4: 'აპრილი',
            5: 'მაისი', 6: 'ივნისი', 7: 'ივლისი', 8: 'აგვისტო',
            9: 'სექტემბერი', 10: 'ოქტომბერი', 11: 'ნოემბერი', 12: 'დეკემბერი'
        }
        month_name = georgian_months.get(wizard.date.month, '')
        month_label = f"{month_name} {wizard.date.year}"

        return {
            'doc_ids': docids,
            'doc_model': 'attendance.report.wizard',
            'data': data,
            'docs': wizard,
            'report_lines': report_data or [],
            'days_in_month': range(1, last_day + 1),
            'last_day': last_day,
            'month_label': month_label,
            'totals': totals,
        }