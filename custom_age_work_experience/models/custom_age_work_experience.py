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

    @api.depends('contract_ids')
    def _compute_work_experience(self):
        for employee in self:
            # Calculate work experience based on contracts
            total_months = 0

            # Get all valid contracts (running or completed)
            valid_contracts = employee.env['hr.contract'].search([
                ('employee_id', '=', employee.id),
                ('state', 'in', ['draft','open', 'close', 'done'])
            ])

            for contract in valid_contracts:
                # Determine end date
                end_date = contract.date_end or date.today()

                # Calculate months worked for this contract
                if contract.date_start:
                    # Calculate months between start and end date
                    months = relativedelta(end_date, contract.date_start).years * 12 + \
                             relativedelta(end_date, contract.date_start).months

                    # Ensure we don't count negative months
                    total_months += max(0, months + 1)  # Add 1 to include the start month

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