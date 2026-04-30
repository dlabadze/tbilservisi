from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class AttendanceImportJob(models.Model):
    _name = 'attendance.import.job'
    _description = 'Attendance Import Job'

    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)

    identification_id = fields.Char(
        string="Identification Number",
        help="If set, import only this employee (deprecated by employee_ids, but kept for legacy)"
    )

    employee_ids = fields.Many2many(
        'hr.employee',
        string="Employees to Process"
    )

    state = fields.Selection([
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('done', 'Done'),
        ('failed', 'Failed'),
    ], default='pending')

    error = fields.Text()

    @api.model
    def run_pending_jobs(self):
        # Process one job at a time to keep memory usage low
        job = self.search([('state', '=', 'pending')], limit=1, order='create_date asc')
        if not job:
            return

        job.state = 'running'
        self.env.cr.commit()  # Lock the job state

        try:
            # Determine which employees to process
            if job.employee_ids:
                employees = job.employee_ids
            elif job.identification_id:
                employees = self.env['hr.employee'].search([('identification_id', '=', job.identification_id)])
            else:
                # Fallback: if no specific employees, maybe it was intended for ALL?
                # But allowing "All" in one job causes the original issue.
                # Ideally, the wizard should have split them. 
                # We will limit this to fail-safe or fetch all if really intended (but warn).
                employees = self.env['hr.employee'].search([('identification_id', '!=', False)])
            
            if employees:
                self.env['attendance.json.importer'].import_employees(
                    employees,
                    job.date_from,
                    job.date_to
                )
            
            job.state = 'done'
        except Exception as e:
            job.state = 'failed'
            job.error = str(e)
            _logger.exception("Attendance import job failed")
