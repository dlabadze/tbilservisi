from odoo import models, fields, api, Command
from odoo.exceptions import UserError
from datetime import datetime, time

class ApprovalCategory(models.Model):
    _inherit = 'approval.category'

    has_brdzaneba = fields.Selection([
        ('required', 'Required'),
        ('optional', 'Optional'),
        ('no', 'None')
    ], string="ბრძანება", default='no')


class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    has_brdzaneba = fields.Selection(related="category_id.has_brdzaneba")

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

class HrDepartment(models.Model):
    _inherit = 'hr.department'

    def _compute_display_name(self):
        super()._compute_display_name()
        if self.env.context.get('show_short_name'):
            for dept in self:
                dept.display_name = dept.name