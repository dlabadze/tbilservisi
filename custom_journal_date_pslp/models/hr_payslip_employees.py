from odoo import api, fields, models


class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        run_id = self.env.context.get('active_id')
        if run_id and 'structure_id' in fields_list:
            run = self.env['hr.payslip.run'].browse(run_id)
            if run.structure_id:
                defaults['structure_id'] = run.structure_id.id
        return defaults
