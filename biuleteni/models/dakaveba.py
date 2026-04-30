from odoo import models, fields, api
from odoo.exceptions import UserError


class Dakaveba(models.Model):
    _name = 'dakaveba'
    _description = 'Dakaveba'
    _order = 'date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # ---------------------------------------------------------
    # BASIC FIELDS
    # ---------------------------------------------------------
    name = fields.Char(string="დასახელება", tracking=True)
    date = fields.Date(string="თარიღი", required=True, default=fields.Date.context_today, tracking=True)

    dakaveba_type = fields.Selection(
        [
            ('zeganakveturi', 'ზეგანაკვეთური'),
            ('jarima', 'ჯარიმა'),
            ('disciplinaruli_jarima', 'დისციპლინარული ჯარიმა'),
            ('sxva', 'სხვა დანარჩენი დაკავებები'),
        ],
        string="ტიპი",
        required=True,
        tracking=True,
    )

    department_id = fields.Many2one('hr.department', string="დეპარტამენტი", tracking=True)
    comment = fields.Char(string="კომენტარი")

    # ---------------------------------------------------------
    # STATE FIELD
    # ---------------------------------------------------------
    state = fields.Selection([
        ('draft', 'დრაფტი'),
        ('validated', 'დადასტურებული'),
    ], string="სტატუსი", default='draft', tracking=True)

    # ---------------------------------------------------------
    # LINES
    # ---------------------------------------------------------
    line_ids = fields.One2many('dakaveba.det', 'dakaveba_id', string="დეტალიზაცია")

    # ---------------------------------------------------------
    # TOTAL
    # ---------------------------------------------------------
    total_amount = fields.Float(string="სულ თანხა", compute="_compute_total", store=True)

    @api.depends('line_ids.amount')
    def _compute_total(self):
        for rec in self:
            rec.total_amount = sum(rec.line_ids.mapped('amount'))

    # ---------------------------------------------------------
    # ACTIONS (VALIDATE / RESET)
    # ---------------------------------------------------------
    def action_validate(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError("ვალიდაციისთვის საჭიროა დეტალები.")
            rec.state = 'validated'
        return True

    def action_reset_draft(self):
        for rec in self:
            rec.state = 'draft'
        return True
