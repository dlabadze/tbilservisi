from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    unit_id = fields.Selection([
        ('1', 'ცალი'),
        ('3', 'გრამი'),
        ('4', 'ლიტრი'),
        ('5', 'ტონა'),
        ('7', 'სანტიმეტრი'),
        ('8', 'მეტრი'),
        ('9', 'კილომეტრი'),
        ('10', 'კვ.სმ'),
        ('11', 'კვ.მ'),
        ('12', 'მ³'),
        ('13', 'მილილიტრი'),
        ('2', 'კგ'),
        ('99', 'სხვა')
    ], string='ერთეული rs.ge')

    unit_txt = fields.Char(string='სხვა ერთეული')
    buyer_info_ids = fields.One2many('product.template.buyer.info', 'product_tmpl_id', string='Buyer Info')
