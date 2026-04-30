from odoo import models, fields

class StockLocation(models.Model):
    _inherit = 'stock.location'

    is_temp = fields.Boolean(string='Is Temp', default=False)
    location_address = fields.Char(string='Address')
    warehouse_partner_id = fields.Many2one(related='warehouse_id.partner_id', string='Warehouse Partner', readonly=True)
