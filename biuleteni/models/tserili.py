from odoo import models, fields, api
from odoo.exceptions import UserError


class Tserili(models.Model):
    _name = 'tserili'
    _description = 'Tserili'
    _order = 'date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    date = fields.Date(string="თარიღი", required=True, default=fields.Date.context_today, tracking=True)

    employee_id = fields.Many2one(
        'hr.employee',
        string="თანამშრომელი",
        required=True,
        tracking=True,
    )

    identification_id = fields.Char(
        string="პირადი ნომერი",
        related='employee_id.identification_id',
        store=True,
    )

    department_id = fields.Many2one(
        'hr.department',
        string="სამსახური",
        related='employee_id.department_id',
        store=True,
    )

    parent_department_id = fields.Many2one(
        'hr.department',
        string="დეპარტამენტი",
        related='employee_id.department_id.parent_id',
        store=True,
    )

    job_id = fields.Many2one(
        'hr.job',
        string="თანამდებობა",
        related='employee_id.job_id',
        store=True,
    )

    amount_plus = fields.Float(string="თანხა +", tracking=True)
    amount_minus = fields.Float(string="თანხა -", tracking=True)

    comment = fields.Char(string="კომენტარი")

    state = fields.Selection([
        ('draft', 'დრაფტი'),
        ('validated', 'დადასტურებული'),
    ], string="სტატუსი", default='draft', tracking=True)

    def action_validate(self):
        for rec in self:
            if not rec.employee_id:
                raise UserError("ვალიდაციისთვის საჭიროა თანამშრომელი.")
            rec.state = 'validated'
        return True

    def action_reset_draft(self):
        for rec in self:
            rec.state = 'draft'
        return True
