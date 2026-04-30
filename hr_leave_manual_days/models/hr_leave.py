from odoo import models, fields, api


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    leave_type_manual_days = fields.Boolean(
        related='holiday_status_id.manual_days_override',
        string="Manual Days Type",
    )
    number_of_days_manual = fields.Float(
        string="Manual Days",
        help="Manually entered days to deduct from the allocation."
    )

    @api.depends(
        'request_date_from', 'request_date_to',
        'request_hour_from', 'request_hour_to',
        'request_date_from_period', 'request_unit_half',
        'request_unit_hours', 'employee_id',
        'holiday_status_id', 'holiday_status_id.manual_days_override',
        'number_of_days_manual',
    )
    def _compute_number_of_days(self):
        super()._compute_number_of_days()
        for leave in self:
            if leave.holiday_status_id.manual_days_override:
                leave.number_of_days = leave.number_of_days_manual

    def _apply_manual_days(self):
        for leave in self:
            if leave.holiday_status_id.manual_days_override:
                hours_per_day = 8.0
                if leave.employee_id and leave.employee_id.resource_calendar_id:
                    hours_per_day = leave.employee_id.resource_calendar_id.hours_per_day or 8.0
                vals = {
                    'number_of_days': leave.number_of_days_manual,
                    'number_of_hours': leave.number_of_days_manual * hours_per_day,
                }
                super(HrLeave, leave).write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        leaves = super().create(vals_list)
        leaves._apply_manual_days()
        return leaves

    def write(self, vals):
        res = super().write(vals)
        relevant = {'number_of_days_manual', 'holiday_status_id',
                    'request_date_from', 'request_date_to'}
        if relevant & set(vals.keys()):
            self._apply_manual_days()
        return res
