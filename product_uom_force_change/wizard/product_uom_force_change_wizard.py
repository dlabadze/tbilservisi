from odoo import _, fields, models
from odoo.exceptions import UserError


class ProductUomForceChangeWizard(models.TransientModel):
    _name = "product.uom.force.change.wizard"
    _description = "განზომილების ერთეულის შეცვლა"

    product_tmpl_id = fields.Many2one(
        "product.template", string="დასახელება", required=True, readonly=True
    )
    current_uom_id = fields.Many2one(
        "uom.uom", string="განზ. ერთეული", readonly=True
    )
    new_uom_id = fields.Many2one(
        "uom.uom", string="ახალი განზ. ერთეული", required=True
    )
    apply_on_purchase_uom = fields.Boolean(default=True)
    confirm_no_conversion = fields.Boolean(default=True)

    def action_apply(self):
        self.ensure_one()

        product_tmpl = self.product_tmpl_id.sudo()
        new_uom = self.new_uom_id.sudo()
        old_uom = product_tmpl.uom_id.sudo()

        if not product_tmpl:
            raise UserError(_("Product was not found."))

        if not new_uom:
            raise UserError(_("აირჩიეთ ახალი განზომილების ერთეული."))

        if old_uom == new_uom and product_tmpl.uom_po_id == new_uom:
            return {"type": "ir.actions.act_window_close"}

        product_ids = product_tmpl.product_variant_ids.ids
        update_counts = {}

        self._update_product_template_uom(product_tmpl, new_uom)
        self._update_product_template_purchase_uom(product_tmpl, new_uom)

        update_specs = [
            ("stock.move", "product_uom", [("product_id", "in", product_ids)]),
            ("stock.move.line", "product_uom_id", [("product_id", "in", product_ids)]),
            ("sale.order.line", "product_uom", [("product_id", "in", product_ids)]),
            ("purchase.order.line", "product_uom", [("product_id", "in", product_ids)]),
            ("account.move.line", "product_uom_id", [("product_id", "in", product_ids)]),
        ]

        for model_name, field_name, domain in update_specs:
            updated = self._bulk_update_uom_field(model_name, field_name, domain, new_uom.id)
            if updated:
                update_counts[model_name] = updated

        self.env.invalidate_all()

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("განზომილების ერთეული განახლდა"),
                "message": _("განზომილების ერთეული წარმატებით შეიცვალა"),
                "sticky": False,
                "type": "success",
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def _update_product_template_uom(self, product_tmpl, new_uom):
        self.env.cr.execute(
            """
            UPDATE product_template
               SET uom_id = %s
             WHERE id = %s
            """,
            (new_uom.id, product_tmpl.id),
        )

    def _update_product_template_purchase_uom(self, product_tmpl, new_uom):
        self.env.cr.execute(
            """
            UPDATE product_template
               SET uom_po_id = %s
             WHERE id = %s
            """,
            (new_uom.id, product_tmpl.id),
        )

    def _bulk_update_uom_field(self, model_name, field_name, domain, new_uom_id):
        try:
            model = self.env[model_name]
        except KeyError:
            return 0

        if field_name not in model._fields:
            return 0

        records = model.sudo().with_context(active_test=False).search(domain)
        if not records:
            return 0

        self.env.cr.execute(
            f'UPDATE "{model._table}" SET "{field_name}" = %s WHERE id = ANY(%s)',
            (new_uom_id, records.ids),
        )
        return len(records)
