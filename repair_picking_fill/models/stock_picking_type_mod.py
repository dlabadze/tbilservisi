from odoo import models, fields

class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    default_repair_partner_id = fields.Many2one(
        'res.partner',
        string="Default Repair Partner"
    )
