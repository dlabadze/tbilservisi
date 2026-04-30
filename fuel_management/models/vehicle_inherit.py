from odoo import api, fields, models, _
from odoo.exceptions import UserError


class FleetVehicle(models.Model):
    _inherit = 'fleet.vehicle'

    fuel_management_count = fields.Integer(
        string='Fuel Records',
        compute='_compute_fuel_management_count',
        readonly=True,
    )

    def _compute_fuel_management_count(self):
        counts_by_vehicle = {vid: 0 for vid in self.ids}
        if self.ids:
            data = self.env['fuel.management'].read_group(
                [('vehicle_id', 'in', self.ids)],
                ['vehicle_id'],
                ['vehicle_id'],
            )
            for row in data:
                vid = row['vehicle_id'][0]
                counts_by_vehicle[vid] = row['vehicle_id_count']
        for vehicle in self:
            vehicle.fuel_management_count = counts_by_vehicle.get(vehicle.id, 0)

    def action_open_fuel_management(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Fuel Management'),
            'res_model': 'fuel.management',
            'view_mode': 'list,form',
            'domain': [('vehicle_id', '=', self.id)],
            'target': 'current',
            'context': dict(self.env.context, default_vehicle_id=self.id),
        }

    def unlink(self):
        Fuel = self.env['fuel.management'].sudo()
        for vehicle in self:
            if Fuel.search_count([('vehicle_id', '=', vehicle.id)], limit=1):
                raise UserError(
                    _("Cannot delete this vehicle because fuel management records exist.")
                )
        return super().unlink()

