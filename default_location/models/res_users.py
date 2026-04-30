from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    def_location_id = fields.Many2one(
        comodel_name="stock.location",
        string="Default Internal Source Location",
        domain=[("usage", "=", "internal")],
        help=(
            "If set, this location will be used as the default source location "
            "when you create an Internal Transfer in Inventory."
        ),
    )


