# -*- coding: utf-8 -*-

import logging

from odoo import models, fields, api
from odoo.osv import expression
from odoo.exceptions import ValidationError
_logger = logging.getLogger(__name__)


class _UncomputedPayrollData:
    """Stand-in for payroll values that do not exist yet at selection time:
    categories, worked days, inputs, intermediate rule results and the payslip
    itself.

    Every access RAISES on purpose. A salary-rule condition that reads any of
    these (e.g. ``categories.BASIC > 0`` or ``worked_days.WORK100``) therefore
    cannot be judged during the pre-filter, the error is caught upstream, and
    the employee is KEPT. We never guess a zero and wrongly drop a payable
    employee. Only conditions that rely solely on the real ``employee`` /
    ``contract`` records (or plain Python) are evaluated for real - and for
    those the result is exactly what generation would decide.
    """

    def __getattr__(self, name):
        raise AttributeError(name)

    def __getitem__(self, name):
        raise KeyError(name)


class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    department_ids = fields.Many2many(
        'hr.department',
        string="Departments",
        domain="[('parent_id', 'child_of', department_id)]",
    )

    employee_ids = fields.Many2many(
        'hr.employee', 'hr_employee_group_rel', 'payslip_id', 'employee_id', 'Employees',
        compute='_compute_employee_ids', store=True, readonly=False,
    )

    # ------------------------------------------------------------------
    # Candidate employees: valid contract + matching structure type
    # (cheap, fully reliable layer)
    # ------------------------------------------------------------------
    def _get_employees_domain(self):
        # Base domain from standard Odoo = employees with a running contract.
        domain = self._get_available_contracts_domain()

        domain = expression.AND([
            domain,
            ['|', ('active', '=', False), ('active', '=', True)]
        ])

        # Explicit child-department selection (this module's original feature).
        if self.department_id and self.department_ids:
            domain = expression.AND([domain, [('department_id', 'in', self.department_ids.ids)]])
        elif self.department_id:
            domain = expression.AND([domain, [('department_id', 'child_of', self.department_id.id)]])

        # Restrict to a single effective salary-structure type: the explicitly
        # chosen type if set, otherwise the type of the chosen structure.
        # Using one value avoids the contradictory double-filter (two AND'd
        # structure_type_id equalities) that could silently return 0 employees.
        effective_type = self.structure_type_id or self.structure_id.type_id
        if effective_type:
            domain = expression.AND([domain, [('structure_type_id', '=', effective_type.id)]])

        if self.job_id:
            domain = expression.AND([domain, [('job_id', '=', self.job_id.id)]])

        return domain

    @api.depends('structure_id', 'department_id', 'structure_type_id', 'job_id', 'department_ids')
    def _compute_employee_ids(self):
        # Pure search -> assignment. Only active employees (archived employees
        # have no running contract for the period and would only yield blank
        # payslips). The blank-rule filtering happens separately (onchange /
        # compute_sheet), never here, to avoid recursive recomputation.
        for wizard in self:
            wizard.employee_ids = self.env['hr.employee'].with_context(active_test=False).search(wizard._get_employees_domain())

    # ------------------------------------------------------------------
    # Blank-payslip pre-filter: read the structure's rule conditions in
    # memory. No payslip is created, so no SLIP/ sequence is consumed.
    # ------------------------------------------------------------------
    def _get_probe_localdict(self, employee, contract):
        # Real data we have (employee/contract) is evaluated faithfully; every
        # not-yet-computed payroll value raises, forcing a "keep" on any rule
        # whose condition depends on it.
        uncomputed = _UncomputedPayrollData()
        return {
            'employee': employee,
            'contract': contract,
            'current_contract': contract,
            'payslip': uncomputed,
            'categories': uncomputed,
            'rules': uncomputed,
            'result_rules': uncomputed,
            'worked_days': uncomputed,
            'inputs': uncomputed,
            'payslips': uncomputed,
        }

    def _would_be_blank(self, employee, rules):
        """True if no salary rule's condition can fire for this employee, i.e.
        the generated payslip would have no lines. Conservative: any
        uncertainty (missing method, un-evaluable condition) returns False so
        the employee is kept."""
        contract = employee.with_context(active_test=False).contract_id
        if not contract:
            return False
        localdict = self._get_probe_localdict(employee, contract)
        for rule in rules:
            satisfy = getattr(rule, '_satisfy_condition', None)
            if satisfy is None:
                return False  # unexpected payroll API -> don't drop anyone
            try:
                if satisfy(localdict):
                    return False  # at least one line would be produced
            except Exception:
                # Condition depends on data not available at selection time
                # (worked days, inputs, ...). Keep the employee to be safe.
                return False
        return True

    def _filter_blank_employees(self, employees):
        self.ensure_one()
        structure = self.structure_id
        if not structure or not employees:
            return employees
        rules = structure.rule_ids.sorted('sequence')
        if not rules:
            return employees  # nothing to judge -> leave the list untouched

        payable = self.env['hr.employee']
        for employee in employees:
            if not self._would_be_blank(employee, rules):
                payable |= employee

        dropped = employees - payable
        if dropped:
            _logger.info(
                "Batch payslip: skipping %s employee(s) who would get a blank "
                "payslip under structure '%s': %s",
                len(dropped), structure.display_name, ", ".join(dropped.mapped('name')),
            )
        return payable

    @api.onchange('structure_id', 'department_id', 'structure_type_id', 'job_id', 'department_ids')
    def _onchange_filter_blank_employees(self):
        """As soon as the structure (or any filter) is chosen, drop employees
        who would get a blank payslip so the user sees only payable ones.
        This only mutates the in-memory selection - no records are written."""
        if self.structure_id and self.employee_ids:
            self.employee_ids = self._filter_blank_employees(self.employee_ids)

    def compute_sheet(self):
        """Authoritative re-filter immediately before generation, so blank
        payslips are never created even if the on-screen list was refreshed by
        a recompute in between."""
        for wizard in self:
            if wizard.structure_id and wizard.employee_ids:
                wizard.employee_ids = wizard._filter_blank_employees(wizard.employee_ids)
        return super().compute_sheet()
