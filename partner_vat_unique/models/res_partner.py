from odoo import models, api, _
from odoo.exceptions import ValidationError

class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.constrains("vat")
    def _check_unique_vat(self):
        # Allow bypass for our wizard
        if self.env.context.get('skip_vat_sync'):
            return
            
        for partner in self:
            if not partner.vat:
                continue

            # Check ALL records (Active AND Archived) as requested
            duplicate = self.with_context(active_test=False).search([
                ("id", "!=", partner.id),
                ("vat", "=", partner.vat),
            ], limit=1)

            if duplicate:
                raise ValidationError(
                    _("A contact with this VAT / Personal ID already exists:\n%s")
                    % duplicate.display_name
                )
