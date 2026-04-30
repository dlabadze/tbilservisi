from odoo import models, fields, api, _
from odoo.exceptions import RedirectWarning
import json

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    @api.model_create_multi
    def create(self, vals_list):
        if len(vals_list) == 1 and not self.env.context.get('skip_duplicate_id_check'):
            vals = vals_list[0]
            identification_id = vals.get('identification_id')
            if identification_id:
                # Search for archived employee with same ID
                duplicate = self.search([
                    ('identification_id', '=', identification_id),
                    ('active', '=', False)
                ], limit=1)
                
                if duplicate:
                    action = self.env.ref('hr_employee_id_duplicate.action_hr_employee_duplicate_wizard')
                    
                    serializable_vals = {}
                    for key, value in vals.items():
                        if isinstance(value, models.BaseModel):
                            serializable_vals[key] = value.id
                        else:
                            serializable_vals[key] = value
                    
                    raise RedirectWarning(
                        _("ყოფილი თანამშრომელი, გსურთ არქივიდან ამოღება?"),
                        action.id,
                        _("დუბლიკატის მართვა"),
                        {
                            'default_employee_id': duplicate.id,
                            'default_identification_id': identification_id,
                            'default_new_employee_vals': json.dumps(serializable_vals),
                        }
                    )
        
        return super(HrEmployee, self).create(vals_list)
