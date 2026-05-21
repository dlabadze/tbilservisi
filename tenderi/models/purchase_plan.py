from odoo import models, fields, api


class PurchasePlanLine(models.Model):
    _inherit = 'purchase.plan.line'

    with_preiskuranti = fields.Boolean(string='პრეისკურანტით?')
    tender_amount = fields.Monetary(string='ტენდერის თანხა')
    remaining_resources_amount = fields.Monetary(string='დარჩენილი რესურსი ხელშეკრულებით', compute='_compute_remaining_resources_amount', store=True)
    purchase_plan_type = fields.Selection(selection=[('1', 'ერთწლიანი'), ('2', 'მრავალწლიანი')], string='შესყიდვის ტიპი')

    @api.depends('tender_amount', 'pu_ac_am', 'pcon_am')
    def _compute_remaining_resources_amount(self):
        for record in self:
            record.remaining_resources_amount = record.pu_ac_am - record.pcon_am - record.tender_amount

    @api.depends('pu_ac_am', 'pcon_am', 'tender_amount')
    def _compute_pc_re_am(self):
        super()._compute_pc_re_am()
        for record in self:
            record.pc_re_am = (record.pc_re_am or 0.0) - (record.tender_amount or 0.0)