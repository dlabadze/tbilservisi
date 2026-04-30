from odoo import models, fields


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    manual_days_override = fields.Boolean(
        string="Manual Days Entry",
        help="If enabled, leave requests of this type require the user to "
             "manually enter the number of days instead of auto-calculating "
             "from the date range (useful for rolling/flexible schedules)."
    )
