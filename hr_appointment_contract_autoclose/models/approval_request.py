import logging
from datetime import timedelta

from odoo import models


_logger = logging.getLogger(__name__)


class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    def _handle_appointment(self):
        self.ensure_one()
        self._validate_required_fields()

        cancel_end_date = self.brdzaneba_start_date - timedelta(days=1)
        self._cancel_running_contracts(self.brdzaneba_employee_id, cancel_end_date)

        vals = self._get_contract_vals()
        contract = self.env['hr.contract'].create(vals)
        _logger.info(
            "Appointment: Cancelled old contracts and created new contract ID=%s for employee '%s'",
            contract.id,
            self.brdzaneba_employee_id.name,
        )
        self._write_shtati_to_employee()
