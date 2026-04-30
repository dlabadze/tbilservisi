from odoo import models, fields

class ProductTemplateBuyerInfo(models.Model):
    _name = 'product.template.buyer.info'
    _description = 'Product Template Buyer Info'

    product_tmpl_id = fields.Many2one('product.template', string='Product Template')
    partner_id = fields.Many2one('res.partner', string='Buyer')
    price = fields.Float(string='Price')
    buyer_tin = fields.Char(related='partner_id.vat', string='Buyer TIN', readonly=True)
    barcode = fields.Char(string='Barcode')
    koef = fields.Float(string='Coefficient')
