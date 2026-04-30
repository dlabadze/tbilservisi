from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = "account.move"

    identification_code = fields.Char(string="ს/კ (საიდენტიფიკაციო)", compute="_onchange_partner_id_set_identification_code",store=True,readonly=False)
    basis = fields.Text(string="საფუძველი")
    contract_num = fields.Char(string="კონტრაქტის ნომერი")
    danishnuleba = fields.Char(string="დანიშნულება")
    factura_num = fields.Char(string='ფაქტურის id', readonly=False)
    invoice_number = fields.Char(string='ზედნადების ნომერი',readonly=False)


    @api.onchange('combined_invoice_id')
    def _onchange_combined_invoice_id(self):
        if self.combined_invoice_id:
            self.factura_num = self.combined_invoice_id.factura_num
            self.invoice_number = self.combined_invoice_id.invoice_number


    @api.onchange('factura_num')
    def _onchange_factura_num(self):
        if self.combined_invoice_id:
            self.combined_invoice_id.factura_num = self.factura_num
            self.combined_invoice_id.invoice_number = self.invoice_number

    @api.depends('partner_id')
    def _onchange_partner_id_set_identification_code(self):
        for rec in self:
            if rec.partner_id:
                rec.identification_code = rec.partner_id.vat
            else:
                rec.identification_code = False