from odoo import fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    vehicle_id = fields.Many2one(
        comodel_name='fleet.vehicle',
        string='Vehicle',
        help='Vehicle related to this transfer',
    )

    def _action_done(self):
        res = super()._action_done()
        for picking in self:
            # Only for internal transfers with a selected vehicle
            if picking.picking_type_id and picking.picking_type_id.code == 'internal' and picking.vehicle_id:
                existing = self.env['fleet.vehicle.log.services'].sudo().search([
                    ('stock_picking_id', '=', picking.id)
                ], limit=1)
                if existing:
                    continue

                # Ensure service type "შიდა ჩამოწერა" exists
                service_type = self.env['fleet.service.type'].sudo().search([
                    ('name', '=', 'შიდა ჩამოწერა')
                ], limit=1)
                if not service_type:
                    service_type = self.env['fleet.service.type'].sudo().create({'name': 'შიდა ჩამოწერა'})

                service_vals = {
                    'vehicle_id': picking.vehicle_id.id,
                    'stock_picking_id': picking.id,
                    'service_type_id': service_type.id,
                    'description': f"Internal transfer {picking.name}",
                }
                self.env['fleet.vehicle.log.services'].sudo().create(service_vals)
        return res


