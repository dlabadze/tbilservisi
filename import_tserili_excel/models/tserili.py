from odoo import _, models


class Tserili(models.Model):
    _inherit = "tserili"

    def action_open_excel_import_wizard(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Tserili Excel Import"),
            "res_model": "tserili.excel.import.wizard",
            "view_mode": "form",
            "target": "new",
        }
