from odoo import models, fields, api, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    partner_car_id = fields.Many2one('partner.car', string='მძღოლი')
    driver_name = fields.Char(related='partner_car_id.partner_name')
    driver_id = fields.Char(related='partner_car_id.partner_vat')
    car_number = fields.Char(related='partner_car_id.car_nom')