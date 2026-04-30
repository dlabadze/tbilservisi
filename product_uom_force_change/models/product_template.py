from odoo import models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def action_open_uom_force_change_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "განზომილების ერთეულის შეცვლა",
            "res_model": "product.uom.force.change.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_product_tmpl_id": self.id,
                "default_current_uom_id": self.uom_id.id,
                "default_new_uom_id": self.uom_id.id,
                "default_apply_on_purchase_uom": True,
                "default_confirm_no_conversion": True,
            },
        }
