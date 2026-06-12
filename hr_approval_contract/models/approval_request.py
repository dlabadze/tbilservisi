import logging
from datetime import timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

APPOINTMENT_CATEGORIES = [
    10,
    1,
    11,
    12,
]

TRANSFER_CATEGORIES = [
    14,
]

TERMINATION_CATEGORIES = [
    24,
    25,
    26,
    27,
    29,
    30,
]


class ApprovalRequest(models.Model):
    _inherit = 'approval.request'


    def _get_contract_vals(self):
        self.ensure_one()
        vals = {
            'employee_id': self.brdzaneba_employee_id.id,
            'date_start': self.brdzaneba_start_date,
            'department_id': self.brdzaneba_department_id.id if self.brdzaneba_department_id else False,
            'job_id': self.brdzaneba_job_id.id if self.brdzaneba_job_id else False,
            'wage': self.brdzaneba_salary or 0.0,
            'state': 'open',
        }
        if self.brdzaneba_end_date:
            vals['date_end'] = self.brdzaneba_end_date

        Contract = self.env['hr.contract']
        if 'x_studio_shtati' in Contract._fields and self.brdzaneba_shtati:
            vals['x_studio_shtati'] = self.brdzaneba_shtati

        employee_name = self.brdzaneba_employee_id.name if self.brdzaneba_employee_id else _('Unknown')
        category_name = self.category_id.id if self.category_id else ''
        vals['name'] = f"{employee_name} – ({self.brdzaneba_start_date})"

        return vals


    def _cancel_running_contracts(self, employee, end_date):

        running_contracts = self.env['hr.contract'].search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'open'),
        ])
        for contract in running_contracts:
            contract.write({
                'date_end': end_date,
                'state': 'cancel',
            })
            _logger.info(
                "Contract %s (ID=%s) cancelled with end_date=%s for employee %s",
                contract.name, contract.id, end_date, employee.name,
            )

    def action_approve(self, approver=None):
        result = super().action_approve(approver=approver)

        for request in self:
            if request.request_status == 'approved':
                request._process_contract_automation()

        return result

    def _check_fully_approved(self):
        self.ensure_one()
        return self.request_status == 'approved'

    def _update_request_status(self):
        super()._update_request_status()
        for request in self:
            if request.request_status == 'approved':
                request._process_contract_automation()

    def _process_contract_automation(self):

        self.ensure_one()

        if self.contract_auto_done:
            return

        category_id = self.category_id.id if self.category_id else ''

        try:
            if category_id in APPOINTMENT_CATEGORIES:
                self._handle_appointment()
                self.contract_auto_done = True

            elif category_id in TRANSFER_CATEGORIES:
                self._handle_transfer()
                self.contract_auto_done = True

            elif category_id in TERMINATION_CATEGORIES:
                self._handle_termination()
                self.contract_auto_done = True

        except Exception as exc:
            _logger.error(
                "Contract automation failed for ApprovalRequest ID=%s, category='%s': %s",
                self.id, category_id, exc,
            )
            raise

    def _handle_appointment(self):
        self.ensure_one()
        self._validate_required_fields()

        vals = self._get_contract_vals()
        contract = self.env['hr.contract'].create(vals)
        _logger.info(
            "Appointment: Created contract ID=%s for employee '%s'",
            contract.id, self.brdzaneba_employee_id.name,
        )
        self._write_shtati_to_employee()

    def _handle_transfer(self):

        self.ensure_one()
        self._validate_required_fields()

        if not self.brdzaneba_start_date:
            raise UserError(_("brdzaneba_start_date is required for a Transfer operation."))

        cancel_end_date = self.brdzaneba_start_date
        self._cancel_running_contracts(self.brdzaneba_employee_id, cancel_end_date)

        vals = self._get_contract_vals()
        contract = self.env['hr.contract'].create(vals)
        _logger.info(
            "Transfer: Cancelled old contracts and created new contract ID=%s for employee '%s'",
            contract.id, self.brdzaneba_employee_id.name,
        )
        self._write_shtati_to_employee()

    def _handle_termination(self):

        self.ensure_one()

        if not self.brdzaneba_employee_id:
            raise UserError(_("No employee specified on this Approval Request."))

        if not self.brdzaneba_end_date:
            raise UserError(_("brdzaneba_end_date is required for a Termination operation."))

        category_id = self.category_id.id if self.category_id else ''
        if category_id in [24, 25, 26, 27, 29]:
            termination_end_date = self.release_date - timedelta(days=1)
        else:
            termination_end_date = self.brdzaneba_start_date - timedelta(days=1)

        self._cancel_running_contracts(self.brdzaneba_employee_id, termination_end_date)

        self.brdzaneba_employee_id.write({'active': False})
        _logger.info(
            "Termination: Cancelled contracts and archived employee '%s'",
            self.brdzaneba_employee_id.name,
        )

    def _write_shtati_to_employee(self):
        self.ensure_one()
        employee = self.brdzaneba_employee_id
        if employee and self.brdzaneba_shtati and 'x_studio_shtati' in employee._fields:
            employee.write({'x_studio_shtati': self.brdzaneba_shtati})
            _logger.info(
                "Updated x_studio_shtati='%s' on employee '%s'",
                self.brdzaneba_shtati, employee.name,
            )

    def _validate_required_fields(self):
        self.ensure_one()
        errors = []
        if not self.brdzaneba_employee_id:
            errors.append(_("Employee (brdzaneba_employee_id)"))
        if not self.brdzaneba_start_date:
            errors.append(_("Start Date (brdzaneba_start_date)"))
        if not self.brdzaneba_salary and self.brdzaneba_salary != 0:
            errors.append(_("Salary (brdzaneba_salary)"))
        if errors:
            raise UserError(
                _("The following required fields are missing on the Approval Request:\n%s")
                % "\n".join(f"  • {e}" for e in errors)
            )

    contract_auto_done = fields.Boolean(
        string='Contract Automation Executed',
        default=False,
        copy=False,
        help="Technical flag set to True once the contract automation has run "
             "for this approval, preventing duplicate processing.",
    )
