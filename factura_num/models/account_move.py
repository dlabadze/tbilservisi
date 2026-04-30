from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'

    combined_invoice_id = fields.Many2one(
        'combined.invoice.model',
        string='Combined Invoice'
    )

    get_invoice_id = fields.Char(
        string='ფაქტურის ნომერი',
        compute='_compute_get_invoice_id',
        # inverse='_inverse_get_invoice_id',
        store=False
    )

    @api.depends('combined_invoice_id.get_invoice_id')
    def _compute_get_invoice_id(self):
        for rec in self:
            rec.get_invoice_id = rec.combined_invoice_id.get_invoice_id or False

    # def _inverse_get_invoice_id(self):
    #     for rec in self:
    #         if rec.combined_invoice_id:
    #             rec.combined_invoice_id.get_invoice_id = rec.get_invoice_id

    @api.onchange('line_ids')
    def _onchange_line_partner(self):
        if self.partner_id:
            return

        partner = self.line_ids.filtered(lambda l: l.partner_id)[:1].partner_id

        if partner:
            self.partner_id = partner
            self.identification_code = partner.vat or False
