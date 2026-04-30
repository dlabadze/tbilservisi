from odoo import api, fields, models


class PartnerCar(models.Model):
    _name = "partner.car"
    _description = "Partner Car Registration"
    _rec_name = "partner_name"

    partner_id = fields.Many2one('res.partner', string="Partner", required=True)
    partner_vat = fields.Char(string="VAT", related='partner_id.vat', readonly=True, store=True)
    car_nom = fields.Char(string="Car Number", required=True)
    partner_name = fields.Char(string="Partner Name", related='partner_id.name', readonly=True, store=True)