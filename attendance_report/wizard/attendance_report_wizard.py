from odoo import models, fields, api
from datetime import datetime
import calendar

class AttendanceReportWizard(models.TransientModel):
    _name = 'attendance.report.wizard'
    _description = 'Attendance Report Wizard'

    department_id = fields.Many2one('hr.department', string='დეპარტამენტი')
    job_id = fields.Many2one('hr.job', string='სამსახური')
    date = fields.Date(string='თარიღი', default=fields.Date.context_today, required=True)
    employee_ids = fields.Many2many('hr.employee', string='თანამშრომლები')

    def action_print_report(self):
        return {
            'type': 'ir.actions.act_url',
            'url': f'/report/pdf/attendance_report.attendance_report_template/{self.id}',
            'target': 'new',
        }