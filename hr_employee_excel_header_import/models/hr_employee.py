from odoo import models, _


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def action_open_excel_header_import_wizard(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Employee Excel Import"),
            "res_model": "hr.employee.excel.import.wizard",
            "view_mode": "form",
            "target": "new",
        }
