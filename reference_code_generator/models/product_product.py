from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _rcg_get_existing_numeric_codes_from_templates(self):
        ProductTemplate = self.env["product.template"]
        if "default_code" not in ProductTemplate._fields:
            return []
        records = ProductTemplate.with_context(active_test=False).sudo().search_read(
            domain=[("default_code", "!=", False)],
            fields=["default_code"],
        )
        numeric_values = []
        for record in records:
            code = record.get("default_code")
            if not code:
                continue
            code_str = str(code).strip()
            if code_str.isdigit():
                try:
                    numeric_values.append(int(code_str))
                except Exception:
                    continue
        return numeric_values

    def _rcg_get_existing_numeric_codes_from_variants(self):
        ProductProduct = self.env["product.product"]
        records = ProductProduct.with_context(active_test=False).sudo().search_read(
            domain=[("default_code", "!=", False)],
            fields=["default_code"],
        )
        numeric_values = []
        for record in records:
            code = record.get("default_code")
            if not code:
                continue
            code_str = str(code).strip()
            if code_str.isdigit():
                try:
                    numeric_values.append(int(code_str))
                except Exception:
                    continue
        return numeric_values

    def _rcg_compute_next_code(self):
        numeric_codes = set(self._rcg_get_existing_numeric_codes_from_templates())
        if not numeric_codes:
            numeric_codes = set(self._rcg_get_existing_numeric_codes_from_variants())
        limit_5 = 100000
        for candidate in range(1, limit_5):
            if candidate not in numeric_codes:
                return str(candidate).zfill(5)
        max_value = max(numeric_codes) if numeric_codes else 0
        return str(max_value + 1).zfill(5)

    def action_generate_reference_code(self):
        self.ensure_one()
        variant = self.sudo()
        current_value = (variant.default_code or "").strip() if variant.default_code else ""
        if current_value:
            raise UserError(_("Internal Reference (default_code) is already set."))

        next_code = self._rcg_compute_next_code()
        variant.default_code = next_code

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Code Generated"),
                "message": _("Generated code: %s") % next_code,
                "type": "success",
                "sticky": False,
            },
        }


