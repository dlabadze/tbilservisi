from odoo import models, fields


class HrEmployeeTracking(models.Model):
    _inherit = 'hr.employee'

    mobile_phone = fields.Char(tracking=True)
    x_studio_homephone = fields.Char(tracking=True)
    x_studio_pension = fields.Boolean(tracking=True)
    x_studio_insurance = fields.Float(tracking=True)
    x_studio_fitpass = fields.Float(tracking=True)
    x_studio_fondi_solidaroba = fields.Float(tracking=True)
    x_studio_charity = fields.Float(tracking=True)
    x_studio_profkav = fields.Float(tracking=True)
    x_studio_profm = fields.Float(tracking=True)
    x_studio_alimenti = fields.Float(tracking=True)
    x_studio_alimentiper = fields.Float(tracking=True)
    x_studio_agsruleba = fields.Float(tracking=True)
    x_studio_agsrulebaper = fields.Float(tracking=True)
    x_studio_shegavati = fields.Float(tracking=True)
    x_studio_start_date_1 = fields.Date(tracking=True)
    bank_account_id = fields.Many2one('res.partner.bank', tracking=True)

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        if not self.env.context.get('from_employee_module'):
            return super(HrEmployee, self.with_context(active_test=False))._search(
                domain, offset=offset, limit=limit, order=order
            )
        return super()._search(domain, offset=offset, limit=limit, order=order)

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        if not self.env.context.get('from_employee_module'):
            return super(HrEmployee, self.with_context(active_test=False)).name_search(
                name=name, args=args, operator=operator, limit=limit
            )
        return super().name_search(name=name, args=args, operator=operator, limit=limit)
