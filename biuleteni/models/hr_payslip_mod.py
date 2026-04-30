from odoo import models, fields
from dateutil.relativedelta import relativedelta

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def _get_worked_day_lines(self, domain=None, check_out_of_contract=True):
        """Override to exclude public holidays when contract has ended mid-period."""
        res = []
        self.ensure_one()
        contract = self.contract_id
        if contract.resource_calendar_id:
            res = super()._get_worked_day_lines(domain=domain, check_out_of_contract=check_out_of_contract)
            if not check_out_of_contract:
                return res

            out_days, out_hours = 0, 0
            reference_calendar = self._get_out_of_contract_calendar()

            # 🧩 Fix: prevent public holidays after contract end from being counted
            if contract.date_end and contract.date_end < self.date_to:
                start = fields.Datetime.to_datetime(contract.date_end) + relativedelta(days=1)
                stop = fields.Datetime.to_datetime(self.date_to) + relativedelta(hour=23, minute=59)

                public_types = self.env['hr.work.entry.type'].search([
                    '|', ('is_public_holiday', '=', True),
                    ('code', '=', 'PUBLIC')
                ])
                domain_exclude = [
                    '|',
                    ('work_entry_type_id', '=', False),
                    '&',
                    ('work_entry_type_id.is_leave', '=', False),
                    ('work_entry_type_id', 'not in', public_types.ids),
                ]

                out_time = reference_calendar.get_work_duration_data(
                    start, stop,
                    compute_leaves=False,
                    domain=domain_exclude
                )
                out_days += out_time['days']
                out_hours += out_time['hours']

            # Replace out-of-contract line if necessary
            if out_days or out_hours:
                work_entry_type = self.env.ref('hr_payroll.hr_work_entry_type_out_of_contract', raise_if_not_found=False)
                if work_entry_type:
                    res = [r for r in res if r['work_entry_type_id'] != work_entry_type.id]
                    res.append({
                        'sequence': work_entry_type.sequence,
                        'work_entry_type_id': work_entry_type.id,
                        'number_of_days': out_days,
                        'number_of_hours': out_hours,
                    })
        return res
