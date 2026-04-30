from odoo import models, api, _, fields
from odoo.exceptions import RedirectWarning
import json

class ResPartner(models.Model):
    _inherit = "res.partner"

    def _check_unique_vat(self):
        """ Override the constraint from partner_vat_unique to show our 
            Georgian window if the duplicate is an archived employee.
        """
        for partner in self:
            if not partner.vat or self.env.context.get('skip_vat_sync'):
                continue

            # Look for ANY duplicate
            duplicate = self.with_context(active_test=False).search([
                ("id", "!=", partner.id),
                ("vat", "=", partner.vat),
            ], limit=1)

            if duplicate and not duplicate.active:
                # Check if this archived partner is linked to an archived employee
                employee = self.env['hr.employee'].with_context(active_test=False).search([
                    ('work_contact_id', '=', duplicate.id),
                    ('active', '=', False)
                ], limit=1)
                
                if employee:
                    # Hijack the error and show the RedirectWarning instead of Oh snap!
                    action = self.env.ref('hr_employee_id_duplicate.action_hr_employee_duplicate_wizard')
                    
                    # Prepare values for the wizard (passing current partner's name if we are in create)
                    # Note: Since RedirectWarning interrupts, we just need to pass enough info
                    # to the wizard to handle the unarchiving.
                    raise RedirectWarning(
                        _("ყოფილი თანამშრომელი, გსურთ არქივიდან ამოღება?"),
                        action.id,
                        _("დიახ"),
                        {
                            'default_employee_id': employee.id,
                            'default_identification_id': partner.vat,
                        }
                    )

        # If we didn't raise our specific warning, let the original module do its job
        return super(ResPartner, self)._check_unique_vat()
