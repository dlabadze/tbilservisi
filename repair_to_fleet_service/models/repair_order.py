from odoo import api, fields, models, _


class RepairOrder(models.Model):
    _inherit = 'repair.order'

    service_ids = fields.One2many(
        'fleet.vehicle.log.services',
        'repair_id',
        string='Services',
        readonly=True,
    )
    service_count = fields.Integer(
        string='Services',
        compute='_compute_service_count',
        store=False,
    )

    def _compute_service_count(self):
        for rec in self:
            rec.service_count = self.env['fleet.vehicle.log.services'].sudo().search_count([('repair_id', '=', rec.id)])

    def action_open_services(self):
        self.ensure_one()
        action = self.env.ref('fleet.fleet_vehicle_log_services_action').read()[0]
        action['domain'] = [('repair_id', '=', self.id)]
        action['context'] = {'default_repair_id': self.id}
        return action

    def action_repair_end(self):
        res = super().action_repair_end()
        self._rtfs_create_fleet_services_for_repairs()
        return res

    # Extra safety in case another flow uses a different end method name
    def action_repair_done(self):
        res = super().action_repair_done()
        self._rtfs_create_fleet_services_for_repairs()
        return res

    def _rtfs_create_fleet_services_for_repairs(self):
        """Create fleet services and product lines when repair ends if there are 'add' lines."""
        Service = self.env['fleet.vehicle.log.services'].sudo()
        ServiceType = self.env['fleet.service.type'].sudo()
        Move = self.env['stock.move'].sudo()
        Line = self.env['fleet.service.product.line'].sudo()

        # Ensure the service type "შიდა ჩამოწერა" exists
        service_type = ServiceType.search([('name', '=', 'შიდა ჩამოწერა')], limit=1)
        if not service_type:
            service_type = ServiceType.create({'name': 'შიდა ჩამოწერა'})

        has_studio_field_x_repair = 'x_studio_repair' in Service._fields

        for repair in self:
            # Require vehicle selection
            vehicle = getattr(repair, 'x_studio_fleet_id', False)
            if not vehicle:
                continue

            # collect relevant stock moves for this repair with line type == 'add'
            domain = [('repair_id', '=', repair.id)]
            # honor custom field if present
            if 'repair_line_type' in Move._fields:
                domain.append(('repair_line_type', '=', 'add'))
            else:
                # If the custom field does not exist, skip since we cannot determine "add" lines
                continue

            moves = Move.search(domain)
            if not moves:
                continue

            # Avoid duplicates by linking to the repair
            existing = Service.search([('repair_id', '=', repair.id)], limit=1)
            if existing:
                service = existing
            else:
                service_vals = {
                    'vehicle_id': vehicle.id,
                    'service_type_id': service_type.id,
                    'description': repair.name or '',
                    'repair_id': repair.id,
                }
                # schedule_date -> date (force date only)
                sched = getattr(repair, 'schedule_date', False)
                if sched:
                    service_vals['date'] = fields.Date.to_date(sched)
                if has_studio_field_x_repair:
                    service_vals['x_studio_repair'] = repair.id
                service = Service.create(service_vals)

            # Create product lines from repair using helper (pattern from stock_fleet_link)
            service._create_product_lines_from_repair(repair)


