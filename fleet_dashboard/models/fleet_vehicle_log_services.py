from odoo import api, fields, models


class FleetVehicleLogServices(models.Model):
    _inherit = 'fleet.vehicle.log.services'

    reference = fields.Char(
        string='Reference',
        copy=False,
        readonly=False,
        index=True,
        help="Auto-generated service reference. Not required — you can edit or clear it.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('reference'):
                vals['reference'] = self.env['ir.sequence'].next_by_code(
                    'fleet.vehicle.log.services'
                ) or '/'
        return super().create(vals_list)
