from odoo import models, api


class HrContract(models.Model):
    _inherit = 'hr.contract'

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        if 'work_entry_source' in fields_list:
            defaults['work_entry_source'] = 'attendance'
        return defaults