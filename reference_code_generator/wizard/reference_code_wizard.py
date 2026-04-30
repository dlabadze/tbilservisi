from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ReferenceCodeGeneratorWizard(models.TransientModel):
    _name = "reference.code.generator.wizard"
    _description = "Generate default_code for product template"

    generated_code = fields.Char(string="Generated Code", readonly=True)

    def _get_existing_numeric_codes_from_templates(self):
        ProductTemplate = self.env["product.template"]
        if "default_code" not in ProductTemplate._fields:
            return []
        # Fetch only the field we need for performance
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
                    # Skip non-integer convertible values
                    continue
        return numeric_values

    def _get_existing_numeric_codes_from_variants(self):
        ProductProduct = self.env["product.product"]
        # Fetch only the field we need for performance
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

    def _compute_next_code(self):
        # Prefer template-level codes when available, else fallback to variants
        numeric_codes = set(self._get_existing_numeric_codes_from_templates())
        if not numeric_codes:
            numeric_codes = set(self._get_existing_numeric_codes_from_variants())
        limit_5 = 100000
        for candidate in range(1, limit_5):
            if candidate not in numeric_codes:
                return str(candidate).zfill(5)
        max_value = max(numeric_codes) if numeric_codes else 0
        return str(max_value + 1).zfill(5)

    def action_generate(self):
        self.ensure_one()
        template = self.env["product.template"].browse(self.env.context.get("active_id")).sudo()
        if not template or not template.exists():
            raise UserError(_("No product template found to generate code for."))

        # Determine where to write the code:
        template_has_default_code = "default_code" in template._fields

        # Check if field already set on template (if exists), else check first variant
        target_current_value = None
        if template_has_default_code:
            target_current_value = (template.default_code or "").strip() if template.default_code else ""
        else:
            # Fallback to first variant
            first_variant = template.product_variant_id
            target_current_value = (first_variant.default_code or "").strip() if first_variant else ""

        if target_current_value:
            raise UserError(_("Internal Reference (default_code) is already set."))

        # Generate next code
        next_code = self._compute_next_code()

        # Write it
        if template_has_default_code:
            template.write({"default_code": next_code})
        else:
            # Fallback: write on first variant
            if not template.product_variant_id:
                # Ensure at least one variant exists
                template._create_variant_ids()
            template.product_variant_id.write({"default_code": next_code})

        self.generated_code = next_code
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
        }


