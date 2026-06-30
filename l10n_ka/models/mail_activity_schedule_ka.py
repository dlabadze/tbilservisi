from odoo import fields, models


class MailActivityScheduleKa(models.TransientModel):
    _inherit = "mail.activity.schedule"

    # Force Georgian labels in activity popup.
    plan_id = fields.Many2one(string="გეგმა")
    date_deadline = fields.Date(string="ვადა")
