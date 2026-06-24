# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.osv import expression


class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    danamatebi_ids = fields.Many2many(
        'zeganakveturi_saati',
        string='დანამატები',
    )

    @api.depends(
        'structure_id',
        'department_id',
        'structure_type_id',
        'job_id',
        'danamatebi_ids',
    )
    def _compute_employee_ids(self):
        super()._compute_employee_ids()

    @api.onchange('danamatebi_ids')
    def _onchange_danamatebi_ids(self):
        self._compute_employee_ids()

    def get_employees_domain(self):
        domain = super().get_employees_domain()
        if self.danamatebi_ids.ids:
            allowed_ids = self.danamatebi_ids.mapped('zeganakveturi_saati_line_ids.employee_id').ids
            domain = expression.AND([domain, [('id', 'in', allowed_ids)]])
        return domain
