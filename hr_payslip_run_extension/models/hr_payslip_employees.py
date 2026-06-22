# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.api import NewId
from odoo.osv import expression


class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    danamatebi_id = fields.Many2one(
        'zeganakveturi_saati',
        string='დანამატები',
    )

    @api.depends(
        'structure_id',
        'department_id',
        'structure_type_id',
        'job_id',
        'danamatebi_id',
    )
    def _compute_employee_ids(self):
        super()._compute_employee_ids()

    @api.onchange('danamatebi_id')
    def _onchange_danamatebi_id(self):
        self._compute_employee_ids()

    def get_employees_domain(self):
        domain = super().get_employees_domain()
        if self.danamatebi_id and not isinstance(self.danamatebi_id.id, NewId):
            allowed_ids = self.danamatebi_id.zeganakveturi_saati_line_ids.employee_id.ids
            domain = expression.AND([domain, [('id', 'in', allowed_ids)]])
        return domain
