from odoo import models, fields, api, _
import json

class HrEmployeeDuplicateWizard(models.TransientModel):
    _name = 'hr.employee.duplicate.wizard'
    _description = 'დუბლიკატი თანამშრომლის მართვა'

    employee_id = fields.Many2one('hr.employee', string='დაარქივებული თანამშრომელი', readonly=True)
    identification_id = fields.Char(string='პირადი ნომერი', readonly=True)
    new_employee_vals = fields.Text(string='ახალი მონაცემები', hidden=True)

    def action_unarchive(self):
        self.ensure_one()
        if self.employee_id:
            # Re-Unarchive with skip_vat_sync to ensure it works
            employee = self.employee_id.with_context(skip_vat_sync=True)
            employee.write({'active': True})
            
            if hasattr(employee, 'work_contact_id') and employee.work_contact_id:
                employee.work_contact_id.write({'active': True})
            if employee.user_id and hasattr(employee.user_id, 'partner_id') and employee.user_id.partner_id:
                employee.user_id.partner_id.write({'active': True})

            # To avoid the "Oh snap!" visual leftover from the background form,
            # we will use an act_url to force a full browser shift.
            # This is the 'cleanest' way to dump the background form's error state.
            url = '/odoo/hr.employee/%s' % self.employee_id.id
            
            return {
                'type': 'ir.actions.act_url',
                'url': url,
                'target': 'self',
            }
