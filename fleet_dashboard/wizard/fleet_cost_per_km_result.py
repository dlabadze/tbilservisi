from odoo import fields, models


class FleetCostPerKmResult(models.TransientModel):
    """One row per vehicle for the Cost-per-km report.

    Populated by fleet.dashboard.wizard.action_open_report when
    report_type == 'cost_per_km'. Lives in transient storage so each
    wizard run gets its own snapshot.
    """
    _name = 'fleet.cost.per.km.result'
    _description = 'ავტოპარკი — ღირებულება კმ-ზე (ავტომობილზე, პერიოდში)'
    _order = 'cost_per_km desc'

    wizard_id = fields.Many2one('fleet.dashboard.wizard', ondelete='cascade')
    vehicle_id = fields.Many2one('fleet.vehicle', string='ავტომობილი', required=True)
    date_from = fields.Date(string='დან', readonly=True)
    date_to = fields.Date(string='მდე', readonly=True)
    odometer_start = fields.Float(string='სპიდომეტრი (დასაწყისი)', readonly=True)
    odometer_end = fields.Float(string='სპიდომეტრი (ბოლო)', readonly=True)
    km_driven = fields.Float(string='გავლილი კმ', readonly=True, aggregator='sum')
    total_spend = fields.Float(string='ჯამური ხარჯი', readonly=True, aggregator='sum')
    service_count = fields.Integer(string='სერვისების რაოდ.', readonly=True, aggregator='sum')
    cost_per_km = fields.Float(
        string='ღირებულება / კმ',
        readonly=True,
        aggregator=None,
        digits=(16, 4),
        help="ჯამური ხარჯი ÷ გავლილი კმ არჩეულ პერიოდში. ცარიელი, თუ გავლილი კმ ნულია.",
    )
    currency_id = fields.Many2one('res.currency', string='ვალუტა', readonly=True)

    def action_open_vehicle(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.vehicle_id.display_name,
            'res_model': 'fleet.vehicle',
            'res_id': self.vehicle_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_services(self):
        """Open the services list filtered to this vehicle and the
        wizard's date range."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f"Services — {self.vehicle_id.display_name}",
            'res_model': 'fleet.vehicle.log.services',
            'view_mode': 'list,form',
            'domain': [
                ('vehicle_id', '=', self.vehicle_id.id),
                ('date', '>=', self.date_from),
                ('date', '<=', self.date_to),
            ],
            'target': 'current',
        }


class FleetNoServiceResult(models.TransientModel):
    """One row per vehicle for the No-service-in-period report."""
    _name = 'fleet.no.service.result'
    _description = 'ავტოპარკი — უმომსახურებო ავტომობილები პერიოდში'
    _order = 'days_since_last_service desc, vehicle_id'

    wizard_id = fields.Many2one('fleet.dashboard.wizard', ondelete='cascade')
    vehicle_id = fields.Many2one('fleet.vehicle', string='ავტომობილი', required=True)
    last_service_date = fields.Date(string='ბოლო სერვისი', readonly=True)
    last_service_id = fields.Many2one(
        'fleet.vehicle.log.services', string='ბოლო სერვისის ჩანაწერი', readonly=True,
    )
    days_since_last_service = fields.Integer(
        string='დღე ბოლო სერვისიდან', readonly=True, aggregator='avg',
    )
    has_ever_been_serviced = fields.Boolean(string='ოდესმე მომსახურებული', readonly=True)

    def action_open_last_service(self):
        self.ensure_one()
        if not self.last_service_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': self.last_service_id.display_name,
            'res_model': 'fleet.vehicle.log.services',
            'res_id': self.last_service_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_vehicle(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.vehicle_id.display_name,
            'res_model': 'fleet.vehicle',
            'res_id': self.vehicle_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
