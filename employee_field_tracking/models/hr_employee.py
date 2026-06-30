from odoo import models, fields, api


class HrEmployeeTracking(models.Model):
    _inherit = 'hr.employee'

    mobile_phone = fields.Char(tracking=False)
    x_studio_homephone = fields.Char(tracking=False)
    x_studio_pension = fields.Boolean(tracking=False)
    x_studio_insurance = fields.Float(tracking=False)
    x_studio_fitpass = fields.Float(tracking=False)
    x_studio_fondi_solidaroba = fields.Float(tracking=False)
    x_studio_charity = fields.Float(tracking=False)
    x_studio_profkav = fields.Float(tracking=False)
    x_studio_profm = fields.Float(tracking=False)
    x_studio_alimenti = fields.Float(tracking=False)
    x_studio_alimentiper = fields.Float(tracking=False)
    x_studio_agsruleba = fields.Float(tracking=False)
    x_studio_agsrulebaper = fields.Float(tracking=False)
    x_studio_shegavati = fields.Float(tracking=False)
    x_studio_start_date_1 = fields.Date(tracking=False)
    bank_account_id = fields.Many2one('res.partner.bank', tracking=False)



