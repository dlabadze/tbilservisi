from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'

    default_repair_partner_id = fields.Many2one(
        'res.partner',
        string="Default Repair Partner"
    )
