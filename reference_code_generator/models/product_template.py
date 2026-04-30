from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = "product.template"

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
        # Fill gaps in 1..99999 first
        limit_5 = 100000
        for candidate in range(1, limit_5):
            if candidate not in numeric_codes:
                return str(candidate).zfill(5)
        # If all 5-digit numbers are used, continue with max + 1
        max_value = max(numeric_codes) if numeric_codes else 0
        return str(max_value + 1).zfill(5)

    def action_generate_reference_code(self):
        self.ensure_one()
        # Work on new (unsaved) and saved records
        template = self.sudo()

        template_has_default_code = "default_code" in template._fields

        # Check current values without forcing a write yet
        current_value = ""
        if template_has_default_code:
            current_value = (template.default_code or "").strip() if template.default_code else ""
        else:
            # use variant when template field not available
            variant = template.product_variant_id
            current_value = (variant.default_code or "").strip() if variant else ""

        if current_value:
            raise UserError(_("Internal Reference (default_code) is already set."))

        next_code = self._rcg_compute_next_code()

        # For new records, assign to cache; for existing, write works too
        if template_has_default_code:
            template.default_code = next_code
        else:
            variant = template.product_variant_id
            if not variant:
                # Ensure a variant exists in cache or DB
                try:
                    template._create_variant_ids()
                    variant = template.product_variant_id
                except Exception:
                    variant = None
            if variant:
                variant.default_code = next_code
            else:
                # As a last resort, write on template if field becomes available later
                # but avoid crashing; show feedback
                raise UserError(_("Could not assign the code to any variant."))

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


