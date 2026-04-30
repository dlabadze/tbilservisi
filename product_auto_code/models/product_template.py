from odoo import models, api, _, fields
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    min_amount = fields.Integer(string='მინიმალური რაოდენობა')

    @api.model
    def create(self, vals):
        if vals.get('default_code'):
            existing = self.env['product.template'].search([
                ('default_code', '=', vals['default_code'])
            ], limit=1)
            if existing:
                raise ValidationError(_("პროდუქტის კოდი '%s' უკვე არსებობს!") % vals['default_code'])

        if not vals.get('default_code'):
            vals['default_code'] = self._generate_next_code()

        result = super().create(vals)

        # After template creation, ensure all its variants have the code synced
        result._sync_code_to_variants()

        return result

    def write(self, vals):
        if 'default_code' in vals and vals['default_code']:
            for rec in self:
                existing = self.env['product.template'].search([
                    ('id', '!=', rec.id),
                    ('default_code', '=', vals['default_code'])
                ], limit=1)
                if existing:
                    raise ValidationError(_("პროდუქტის კოდი '%s' უკვე არსებობს!") % vals['default_code'])

        result = super().write(vals)

        # If default_code was updated, sync to all variants
        if 'default_code' in vals:
            for rec in self:
                rec._sync_code_to_variants()

        return result

    def _generate_next_code(self):
        """Generate the next available sequential code."""
        all_codes = self.env['product.template'].search([
            ('default_code', '!=', False)
        ]).mapped('default_code')

        used_numbers = set()
        for code in all_codes:
            try:
                used_numbers.add(int(code))
            except Exception:
                continue

        next_number = 1
        while next_number in used_numbers:
            next_number += 1

        return f"{next_number:05d}"

    def _sync_code_to_variants(self):
        """Sync the template's default_code to all its variants' stored field."""
        for rec in self:
            if rec.default_code and rec.product_variant_ids:
                # Direct SQL update to ensure immediate visibility
                self.env.cr.execute(
                    "UPDATE product_product SET default_code = %s WHERE product_tmpl_id = %s",
                    (rec.default_code, rec.id)
                )
                # Invalidate cache so UI reflects the change
                rec.product_variant_ids.invalidate_recordset(['default_code'])

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        if name:
            domain = ['|', ('default_code', operator, name), ('name', operator, name)]
            return self.search(domain + args, limit=limit).name_get()
        return self.search(args, limit=limit).name_get()

    def name_get(self):
        res = []
        for rec in self:
            if rec.default_code:
                label = f"[{rec.default_code}] {rec.name}"
            else:
                label = rec.name
            res.append((rec.id, label))
        return res


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # expose template's default_code on the variant so UI and search see it immediately
    default_code = fields.Char(related='product_tmpl_id.default_code', readonly=True, store=True)

    @api.model
    def create(self, vals):
        """Ensure template has a code before variant creation."""
        # If creating via quick-create, template might be created first
        # We need to ensure the template gets a code
        product = super().create(vals)

        tmpl = product.product_tmpl_id
        if tmpl and not tmpl.default_code:
            # Generate and assign code to template
            new_code = tmpl._generate_next_code()
            tmpl.write({'default_code': new_code})

            # Immediately sync to this variant
            self.env.cr.execute(
                "UPDATE product_product SET default_code = %s WHERE id = %s",
                (new_code, product.id)
            )
            product.invalidate_recordset(['default_code'])
        elif tmpl and tmpl.default_code:
            # Template has code but variant might not have it synced yet
            self.env.cr.execute(
                "UPDATE product_product SET default_code = %s WHERE id = %s",
                (tmpl.default_code, product.id)
            )
            product.invalidate_recordset(['default_code'])

        return product

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        """Search by variant name OR template.default_code so quick-create products are searchable by code."""
        args = args or []
        if name:
            domain = ['|', ('default_code', operator, name), ('name', operator, name)]
            return self.search(domain + args, limit=limit).name_get()
        return self.search(args, limit=limit).name_get()

    def name_get(self):
        """Show [CODE] Name in variant pickers (uses related default_code)."""
        res = []
        for rec in self:
            code = rec.default_code
            if code:
                label = f"[{code}] {rec.name}"
            else:
                label = rec.name
            res.append((rec.id, label))
        return res
