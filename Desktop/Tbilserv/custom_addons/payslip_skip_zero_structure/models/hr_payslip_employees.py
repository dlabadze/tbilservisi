# -*- coding: utf-8 -*-
import logging

from odoo import fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    def _get_selected_structure(self):
        self.ensure_one()
        if self.structure_id:
            return self.structure_id
        run_id = self.env.context.get('active_id')
        if not run_id:
            return self.env['hr.payroll.structure']
        run = self.env['hr.payslip.run'].browse(run_id)
        if run.exists() and 'structure_id' in run._fields and run.structure_id:
            return run.structure_id
        return self.env['hr.payroll.structure']

    def _get_batch_period_dates(self):
        ctx = self.env.context
        if ctx.get('active_model') == 'hr.payslip.run' and ctx.get('active_id'):
            run = self.env['hr.payslip.run'].browse(ctx['active_id'])
            if run.exists():
                return run.date_start, run.date_end
        date_from = ctx.get('default_date_start')
        date_to = ctx.get('default_date_end')
        return (
            fields.Date.to_date(date_from) if date_from else None,
            fields.Date.to_date(date_to) if date_to else None,
        )

    def _get_employee_salarytypes_field(self, employee):
        for field_name in ('x_studio_salarytypes',):
            if field_name in employee._fields:
                return field_name
        return None

    def _get_component_rule(self, component):
        """Salary component rule is stored on x_studio_ or x_studio_comptypes."""
        for field_name in ('x_studio_', 'x_studio_comptypes', 'x_studio_rule'):
            if field_name in component._fields:
                rule = component[field_name]
                if rule:
                    return rule
        return self.env['hr.salary.rule']

    def _get_structure_rule_ids(self, structure):
        if 'rule_ids' in structure._fields and structure.rule_ids:
            return set(structure.rule_ids.ids)
        return set(self.env['hr.salary.rule'].search([
            ('struct_id', '=', structure.id),
        ]).ids)

    def _component_applies_to_period(self, component, date_from, date_to):
        start = component.x_studio_start if 'x_studio_start' in component._fields else False
        end = component.x_studio_end if 'x_studio_end' in component._fields else False
        if date_from and start and start > date_from:
            return False
        if date_to and end and end < date_to:
            return False
        return True

    def _employee_has_nonzero_structure_amount(self, employee, structure, date_from, date_to):
        salarytypes_field = self._get_employee_salarytypes_field(employee)
        if not salarytypes_field:
            return True

        rule_ids = self._get_structure_rule_ids(structure)
        if not rule_ids:
            return True

        total = 0.0
        for component in employee[salarytypes_field]:
            rule = self._get_component_rule(component)
            if not rule or rule.id not in rule_ids:
                continue
            if not self._component_applies_to_period(component, date_from, date_to):
                continue
            amount = component.x_studio_compamount if 'x_studio_compamount' in component._fields else 0.0
            total += amount or 0.0

        return not employee.company_id.currency_id.is_zero(total)

    def _filter_employees_for_structure(self, structure):
        date_from, date_to = self._get_batch_period_dates()
        return self.employee_ids.filtered(
            lambda employee: self._employee_has_nonzero_structure_amount(
                employee, structure, date_from, date_to
            )
        )

    def compute_sheet(self):
        self.ensure_one()
        structure = self._get_selected_structure()
        if not structure:
            return super().compute_sheet()

        eligible_employees = self._filter_employees_for_structure(structure)
        skipped_employees = self.employee_ids - eligible_employees
        if skipped_employees:
            _logger.info(
                "Skipping %s employee(s) with zero salary amount for structure %s: %s",
                len(skipped_employees),
                structure.display_name,
                ', '.join(skipped_employees.mapped('name')),
            )

        if not eligible_employees:
            raise UserError(_(
                'No employees have a non-zero salary amount for salary structure "%(structure)s".',
                structure=structure.display_name,
            ))

        self.employee_ids = eligible_employees
        return super(HrPayslipEmployees, self.with_context(
            active_employee_ids=eligible_employees.ids,
        )).compute_sheet()
