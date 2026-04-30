# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    allowed_location_ids = fields.Many2many(
        'stock.location',
        'user_allowed_location_rel',
        'user_id',
        'location_id',
        string='Allowed Locations',
        help='Locations this user can access. If empty, user can access all locations.',
        domain=[('usage', '!=', 'view')],  # Exclude view locations from selection
    )


