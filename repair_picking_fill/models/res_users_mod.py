from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'

    x_repair_partner_id = fields.Many2one(
        'res.partner',
        string="Repair Default Partner",
        help="Default Partner for Repair Orders created by this user."
    )
