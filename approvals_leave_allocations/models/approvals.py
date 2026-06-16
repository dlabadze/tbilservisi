from odoo import fields, api, models, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)



class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    def _create_piradi_leave_allocation(self):
        leave_type = self.env['hr.leave.type'].sudo().search(
            [('name', '=', 'შვებულება პირადი')], limit=1
        )
        accrual_plan = self.env['hr.leave.accrual.plan'].sudo().search(
            [('name', '=', 'შვებულება პირადი')], limit=1
        )
        if not leave_type or not accrual_plan:
            raise UserError(_("Leave type and accrual plan not found"))

        existing = self.env['hr.leave.allocation'].sudo().search([
            ('employee_id', '=', self.brdzaneba_employee_id.id),
            ('holiday_status_id', '=', leave_type.id),
            ('date_to', '=', False),
        ], limit=1)
        if existing:
            return

        allocation = self.env['hr.leave.allocation'].sudo().create({
            'employee_id': self.brdzaneba_employee_id.id,
            'holiday_status_id': leave_type.id,
            'accrual_plan_id': accrual_plan.id,
            'date_from': self.brdzaneba_start_date,
            'date_to': False,
            'allocation_type': 'accrual',
            'state': 'confirm',
            'number_of_days': 24,
        })
        allocation.action_approve()

    def _should_create_allocation(self):
        return (
            self.request_status == 'approved'
            and self.brdzaneba_employee_id
            and self.brdzaneba_start_date
            and 'დანიშვნა' in (self.category_id.name or '')
        )

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record._should_create_allocation():
                record._create_piradi_leave_allocation()
        return records

    def write(self, vals):
        result = super().write(vals)
        for record in self:
            if record._should_create_allocation():
                _logger.info(f"||Creating leave allocation for {record.brdzaneba_employee_id.name}")
                record._create_piradi_leave_allocation()
        return result
