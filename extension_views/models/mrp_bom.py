from odoo import models, fields

class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    landed_cost = fields.Float(string='Landed Cost')
