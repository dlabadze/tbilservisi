from odoo import models, fields, api, Command
from odoo.exceptions import UserError
from datetime import datetime, time, timedelta


class ApprovalCategory(models.Model):
    _inherit = 'approval.category'

    has_brdzaneba = fields.Selection([
        ('required', 'Required'),
        ('optional', 'Optional'),
        ('no', 'None')
    ], string="ბრძანება", default='no')


class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    def init(self):
        # Ensure required columns exist before FK checks in mixed install/upgrade flows.
        self._cr.execute("ALTER TABLE approval_request ADD COLUMN IF NOT EXISTS brdzaneba_date date")
        self._cr.execute("ALTER TABLE approval_request ADD COLUMN IF NOT EXISTS brdzaneba_employee_id integer")
        self._cr.execute("ALTER TABLE approval_request ADD COLUMN IF NOT EXISTS brdzaneba_start_date date")
        self._cr.execute("ALTER TABLE approval_request ADD COLUMN IF NOT EXISTS brdzaneba_end_date date")
        self._cr.execute("ALTER TABLE approval_request ADD COLUMN IF NOT EXISTS brdzaneba_department_id integer")
        self._cr.execute("ALTER TABLE approval_request ADD COLUMN IF NOT EXISTS brdzaneba_job_id integer")
        self._cr.execute("ALTER TABLE approval_request ADD COLUMN IF NOT EXISTS brdzaneba_shtati varchar")
        self._cr.execute("ALTER TABLE approval_request ADD COLUMN IF NOT EXISTS brdzaneba_safudzveli text")
        self._cr.execute("ALTER TABLE approval_request ADD COLUMN IF NOT EXISTS brdzaneba_salary double precision")
        self._cr.execute("ALTER TABLE approval_request ADD COLUMN IF NOT EXISTS release_date date")

    has_brdzaneba = fields.Selection(related="category_id.has_brdzaneba")
    brdzaneba_kind = fields.Selection([
        ('appointment', 'დანიშვნა'),
        ('temporary_appointment', 'დანიშვნა დროებით'),
    ], string="ბრძანების ტიპი", compute='_compute_brdzaneba_kind', store=False)

    brdzaneba_date = fields.Date(string="ბრძანების თარიღი")
    brdzaneba_employee_id = fields.Many2one('hr.employee', string="თანამშრომელი")
    brdzaneba_identification_id = fields.Char(related="brdzaneba_employee_id.identification_id", string="საიდენტიფიკაციო")
    brdzaneba_current_department_id = fields.Many2one('hr.department', related="brdzaneba_employee_id.department_id", string="მიმდინარე სტრუქტურული ერთეული")
    brdzaneba_current_job_id = fields.Many2one('hr.job', related="brdzaneba_employee_id.job_id", string="მიმდინარე თანამდებობა")
    brdzaneba_start_date = fields.Date(string="დაწყების თარიღი")
    brdzaneba_end_date = fields.Date(string="დასრულების თარიღი")
    brdzaneba_department_id = fields.Many2one('hr.department', string="სტრუქტურული ერთეული")
    brdzaneba_job_id = fields.Many2one('hr.job', string="თანამდებობა", domain="[('department_id', '=', brdzaneba_department_id)]")
    brdzaneba_shtati = fields.Selection([
        ('შტატი', 'შტატი'),
        ('შტატგარეშე', 'შტატგარეშე'),
        ('მოვალეობის შემსრულებელი', 'მოვალეობის შემსრულებელი')
    ], string="შტატიანობა")
    brdzaneba_safudzveli = fields.Text(string="საფუძველი")
    brdzaneba_salary = fields.Float(string="ხელფასი")

    # Compatibility fallback for Studio-based views on replicated databases.
    x_studio_wagecurr = fields.Many2one('res.currency', string="Wage Currency")

    release_date = fields.Date(
        string="გათავისუფლების თარიღი",
        store=True,
        readonly=False,
    )

    @api.depends('category_id')
    def _compute_brdzaneba_kind(self):
        for rec in self:
            category_name = (rec.category_id.name or '').strip() if rec.category_id else ''
            if category_name == 'დანიშვნა':
                rec.brdzaneba_kind = 'appointment'
            elif category_name == 'დანიშვნა დროებით':
                rec.brdzaneba_kind = 'temporary_appointment'
            else:
                rec.brdzaneba_kind = False

    @api.onchange('release_date', 'category_id')
    def _onchange_end_date(self):
        for rec in self:
            if rec.category_id and rec.category_id.id in [24, 25, 26, 27, 29, 30, 32] and rec.release_date:
                rec.brdzaneba_end_date = rec.release_date - timedelta(days=1)

class HrDepartment(models.Model):
    _inherit = 'hr.department'

    def _compute_display_name(self):
        super()._compute_display_name()
        if self.env.context.get('show_short_name'):
            for dept in self:
                dept.display_name = dept.name