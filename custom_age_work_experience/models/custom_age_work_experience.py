# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import date
from dateutil.relativedelta import relativedelta

class HrEmployeeExtendedDetails(models.Model):
    _inherit = 'hr.employee'

    # Age Calculation Field
    age = fields.Integer(
        string='Age',
        compute='_compute_age',
        store=True,
        readonly=True
    )

    # Work Experience Calculation Field
    work_experience_months = fields.Integer(
        string='Work Experience (Months)',
        compute='_compute_work_experience',
        store=True,
        readonly=True,
        help="Total months worked based on all contracts"
    )

    @api.depends('birthday')
    def _compute_age(self):
        for record in self:
            if record.birthday:
                today = date.today()
                record.age = today.year - record.birthday.year - (
                        (today.month, today.day) < (record.birthday.month, record.birthday.day)
                )
            else:
                record.age = 0

    @api.depends('contract_ids', 'contract_ids.state', 'contract_ids.date_start', 'contract_ids.date_end')
    def _compute_work_experience(self):
        today = date.today()
        for employee in self:
            total_months = 0

            # Get all valid contracts, sorted by start date descending
            valid_contracts = employee.env['hr.contract'].search([
                ('employee_id', '=', employee.id),
                ('state', 'in', ['draft', 'open', 'close', 'done']),
                ('date_start', '!=', False)
            ], order='date_start desc')

            if valid_contracts:
                # The newest contract determines the end of the calculation
                chain_end_date = valid_contracts[0].date_end
                
                # Cap the end date to today
                if not chain_end_date or chain_end_date > today:
                    effective_end_date = today
                else:
                    effective_end_date = chain_end_date
                
                chain_start_date = valid_contracts[0].date_start
                previous_start = valid_contracts[0].date_start

                # Walk through contracts backwards to find the continuous chain
                for i in range(1, len(valid_contracts)):
                    contract = valid_contracts[i]
                    contract_end = contract.date_end or today
                    
                    # Gap calculation: previous_start - contract_end
                    # If gap is <= 1 day, it's considered continuous (e.g., Dec 31 to Jan 1 is 1 day gap)
                    gap = (previous_start - contract_end).days
                    if gap <= 1:
                        chain_start_date = contract.date_start
                        previous_start = contract.date_start
                    else:
                        break # Chain broken
                
                # Calculate total months from chain start to effective end
                if chain_start_date <= effective_end_date:
                    delta = relativedelta(effective_end_date, chain_start_date)
                    months = delta.years * 12 + delta.months
                    total_months = max(0, months + 1)

            employee.work_experience_months = total_months

    def _compute_work_experience_trigger(self):
        """
        Method to manually trigger work experience recomputation
        Can be called after contract changes
        """
        for employee in self:
            employee._compute_work_experience()


            # -*- coding: utf-8 -*-


class HrContractExtension(models.Model):
    _inherit = 'hr.contract'

    @api.model_create_multi
    def create(self, vals_list):
        contracts = super().create(vals_list)

        # Trigger work experience recomputation for affected employees
        employees = contracts.mapped('employee_id')
        employees._compute_work_experience()

        return contracts

    def write(self, vals):
        result = super().write(vals)

        # Trigger work experience recomputation for affected employees
        employees = self.mapped('employee_id')
        employees._compute_work_experience()

        return result