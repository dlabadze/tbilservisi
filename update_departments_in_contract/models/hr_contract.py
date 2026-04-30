from odoo import models


class HrContract(models.Model):
    _inherit = "hr.contract"

    def action_open_department_update_wizard(self):
        active_ids = self.env.context.get("active_ids", self.ids)
        return {
            "type": "ir.actions.act_window",
            "name": "Update Department",
            "res_model": "update.contract.department.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "active_model": "hr.contract",
                "active_ids": active_ids,
            },
        }
