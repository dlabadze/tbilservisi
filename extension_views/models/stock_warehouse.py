from odoo import models, fields

class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    rs_acc = fields.Char(string='rs.ge ექაუნთი')
    rs_pass = fields.Char(string='rs.ge პაროლი')
    additional_address = fields.Char(string='Additional Address')
