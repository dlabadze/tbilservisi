# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.api import NewId
from odoo.osv import expression


class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    def _get_wizard_period_dates(self):
        """Batch dates: from opened payslip run, or default_date_* in context."""
        ctx = self.env.context
        if ctx.get('active_model') == 'hr.payslip.run' and ctx.get('active_id'):
            run = self.env['hr.payslip.run'].browse(ctx['active_id'])
            if run.exists():
                return run.date_start, run.date_end
        ds = ctx.get('default_date_start')
        de = ctx.get('default_date_end')
        if ds and de:
            return fields.Date.to_date(ds), fields.Date.to_date(de)
        return None, None

    def _employee_matches_period_including_archived(self, employee, date_from, date_to):
        """Active employees: same as standard domain. Archived: need open/close contract overlapping the batch."""
        if employee.active:
            return True
        if not date_from or not date_to:
            return False
        contracts = employee._get_contracts(date_from, date_to, states=['open', 'close'])
        return bool(contracts)

    department_ids = fields.Many2many(
        'hr.department',
        'hr_payslip_employees_multi_department_rel',
        'wizard_id',
        'department_id',
        string='Departments',
        help='Employees in any of these department trees (including sub-departments). '
             'Combined with the Department field using OR: employees match either filter.',
    )

    def _department_root_int_ids(self):
        """Stable int ids for department_id + department_ids (skip NewId during onchange)."""
        seen = set()
        ordered = []
        if self.department_id and not isinstance(self.department_id.id, NewId):
            ordered.append(self.department_id.id)
            seen.add(self.department_id.id)
        for dep in self.department_ids:
            if isinstance(dep.id, NewId):
                continue
            if dep.id not in seen:
                ordered.append(dep.id)
                seen.add(dep.id)
        return ordered

    def _sync_wizard_employees(self):
        """Single place: domain search + archived-in-period filter."""
        for wizard in self:
            domain = wizard.get_employees_domain()
            date_from, date_to = wizard._get_wizard_period_dates()
            candidates = self.env['hr.employee'].with_context(active_test=False).search(domain)
            if date_from and date_to:
                candidates = candidates.filtered(
                    lambda e: wizard._employee_matches_period_including_archived(e, date_from, date_to)
                )
            else:
                candidates = candidates.filtered(lambda e: e.active)
            wizard.employee_ids = candidates

    @api.depends(
        'structure_id',
        'department_id',
        'department_ids',
        'structure_type_id',
        'job_id',
    )
    def _compute_employee_ids(self):
        self._sync_wizard_employees()

    @api.onchange(
        'structure_id',
        'department_id',
        'department_ids',
        'structure_type_id',
        'job_id',
    )
    def _onchange_hr_payslip_filter_sync_employees(self):
        """Many2many tags often need onchange so employee_ids refreshes before save."""
        self._sync_wizard_employees()

    @api.depends('department_id')
    def _compute_job_id(self):
        return super()._compute_job_id()

    def get_employees_domain(self):
        # Rebuild standard domain (do not call super) so onchange never passes NewId into SQL.
        domain = self._get_available_contracts_domain()
        if self.structure_type_id and not isinstance(self.structure_type_id.id, NewId):
            domain = expression.AND([
                domain,
                [('structure_type_id', '=', self.structure_type_id.id)],
            ])
        if self.job_id and not isinstance(self.job_id.id, NewId):
            domain = expression.AND([
                domain,
                [('job_id', '=', self.job_id.id)],
            ])
        if self.structure_id and not isinstance(self.structure_id.id, NewId):
            stype = self.structure_id.type_id
            if stype and not isinstance(stype.id, NewId):
                domain = expression.AND([
                    domain,
                    [('structure_type_id', '=', stype.id)],
                ])
        # Union of department_id + department_ids: all departments under any selected root.
        root_ids = self._department_root_int_ids()
        if root_ids:
            subtree = self.env['hr.department'].sudo().search([('id', 'child_of', root_ids)])
            if subtree.ids:
                domain = expression.AND([domain, [('department_id', 'in', subtree.ids)]])
        return domain
