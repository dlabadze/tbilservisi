from odoo import fields, models
from odoo.exceptions import UserError


class UpdateContractDepartmentWizard(models.TransientModel):
    _name = "update.contract.department.wizard"
    _description = "Update Contract Department Wizard"

    department_id = fields.Many2one("hr.department", required=True)

    def action_confirm(self):
        self.ensure_one()
        active_ids = self.env.context.get("active_ids", [])
        contracts = self.env["hr.contract"].sudo().browse(active_ids).exists()

        if contracts:
            contracts.write({'state': 'draft'})
            contracts.write({'department_id': self.department_id.id})
            contracts.write({'state': 'open'})

        return {"type": "ir.actions.act_window_close"}
