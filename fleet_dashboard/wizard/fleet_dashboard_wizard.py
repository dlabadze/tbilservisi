from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


PERIOD_SELECTION = [
    ('today', 'დღეს'),
    ('last_7', 'ბოლო 7 დღე'),
    ('last_30', 'ბოლო 30 დღე'),
    ('last_90', 'ბოლო 90 დღე'),
    ('last_6m', 'ბოლო 6 თვე'),
    ('last_12m', 'ბოლო 12 თვე'),
    ('this_month', 'ამ თვეში'),
    ('last_month', 'გასულ თვეში'),
    ('this_quarter', 'ამ კვარტალში'),
    ('this_year', 'ამ წელს'),
    ('last_year', 'გასულ წელს'),
    ('custom', 'მორგებული პერიოდი'),
]

REPORT_SELECTION = [
    ('overview', 'მიმოხილვა (ჯგუფების გარეშე)'),
    ('most_serviced', 'ყველაზე ხშირად მომსახურებული ავტომობილები'),
    ('most_expensive', 'ყველაზე ძვირადღირებული ავტომობილები'),
    ('top_parts', 'ყველაზე ხშირად გამოყენებული ნაწილები'),
    ('top_expensive_parts', 'ყველაზე ძვირადღირებული ნაწილები'),
    ('by_workshop', 'საამქროების მიხედვით'),
    ('by_vendor', 'მომწოდებლების მიხედვით'),
    ('by_service_type', 'სერვისის ტიპის მიხედვით'),
    ('cost_per_km', 'ღირებულება კმ-ზე (ავტომობილზე)'),
    ('no_service', 'უმომსახურებო ავტომობილები პერიოდში'),
]

REPORT_GROUPBY = {
    'overview': [],
    'most_serviced': ['vehicle_id'],
    'most_expensive': ['vehicle_id'],
    'top_parts': ['product_id'],
    'top_expensive_parts': ['product_id'],
    'by_workshop': ['workshop_id'],
    'by_vendor': ['vendor_id'],
    'by_service_type': ['service_type_id'],
}

SPECIAL_REPORTS = {'cost_per_km', 'no_service'}


class FleetDashboardWizard(models.TransientModel):
    _name = 'fleet.dashboard.wizard'
    _description = 'ავტოპარკის ანალიტიკა — პერიოდისა და ფილტრების არჩევა'

    report_type = fields.Selection(
        REPORT_SELECTION,
        string='რეპორტი',
        default='overview',
        required=True,
    )
    period = fields.Selection(
        PERIOD_SELECTION,
        string='პერიოდი',
        default='this_year',
        required=True,
    )
    date_from = fields.Date(string='დან')
    date_to = fields.Date(string='მდე')

    vehicle_ids = fields.Many2many('fleet.vehicle', string='ავტომობილები')
    product_ids = fields.Many2many('product.product', string='ნაწილები / პროდუქტები')
    vendor_ids = fields.Many2many(
        'res.partner',
        string='მომწოდებლები',
        domain=[('is_company', '=', True)],
    )
    service_type_ids = fields.Many2many('fleet.service.type', string='სერვისის ტიპები')
    workshop_ids = fields.Many2many(
        'stock.location',
        string='საამქროები',
        help="კომპონენტის წყარო ლოკაცია რემონტზე (x_studio_saamqro).",
    )

    view_mode = fields.Selection(
        [
            ('graph', 'გრაფიკი'),
            ('pivot', 'პივოტი'),
            ('list', 'სია'),
            ('kanban', 'კანბანი'),
        ],
        string='გახსენი როგორც',
        default='graph',
        required=True,
    )
    top_n = fields.Selection(
        [
            ('10', 'ტოპ 10'),
            ('20', 'ტოპ 20'),
            ('50', 'ტოპ 50'),
            ('100', 'ტოპ 100'),
            ('0', 'ყველა'),
        ],
        string='ჩვენება',
        default='10',
        required=True,
        help="დაჯგუფებული რეპორტებისთვის ნაჩვენებია მხოლოდ ტოპ N (ხარჯის ან რაოდენობის მიხედვით).",
    )

    @api.onchange('period')
    def _onchange_period(self):
        """Pre-fill date_from/date_to so user sees the resolved range,
        can tweak it, and gets visual confirmation before running."""
        today = fields.Date.context_today(self)
        start, end = self._resolve_period(self.period, today)
        if self.period != 'custom':
            self.date_from = start
            self.date_to = end

    @staticmethod
    def _resolve_period(period, today):
        if period == 'today':
            return today, today
        if period == 'last_7':
            return today - relativedelta(days=7), today
        if period == 'last_30':
            return today - relativedelta(days=30), today
        if period == 'last_90':
            return today - relativedelta(days=90), today
        if period == 'last_6m':
            return today - relativedelta(months=6), today
        if period == 'last_12m':
            return today - relativedelta(months=12), today
        if period == 'this_month':
            return today.replace(day=1), today
        if period == 'last_month':
            first_this = today.replace(day=1)
            first_last = first_this - relativedelta(months=1)
            last_last = first_this - relativedelta(days=1)
            return first_last, last_last
        if period == 'this_quarter':
            q_start_month = ((today.month - 1) // 3) * 3 + 1
            return today.replace(month=q_start_month, day=1), today
        if period == 'this_year':
            return today.replace(month=1, day=1), today
        if period == 'last_year':
            first_this = today.replace(month=1, day=1)
            first_last = first_this - relativedelta(years=1)
            last_last = first_this - relativedelta(days=1)
            return first_last, last_last
        return None, None  # custom — user fills in manually

    def action_open_report(self):
        self.ensure_one()

        today = fields.Date.context_today(self)
        if self.period == 'custom':
            if not self.date_from or not self.date_to:
                raise UserError(
                    "მორგებული პერიოდისთვის შეავსე ორივე — \"დან\" და \"მდე\" თარიღი."
                )
            if self.date_from > self.date_to:
                raise UserError("\"დან\" თარიღი უნდა იყოს \"მდე\" თარიღამდე ან იმავე დღეს.")
            start, end = self.date_from, self.date_to
        else:
            start, end = self._resolve_period(self.period, today)

        if self.report_type == 'cost_per_km':
            return self._action_cost_per_km(start, end)
        if self.report_type == 'no_service':
            return self._action_no_service(start, end)

        domain = [('date', '>=', start), ('date', '<=', end)]
        if self.vehicle_ids:
            domain.append(('vehicle_id', 'in', self.vehicle_ids.ids))
        if self.product_ids:
            domain.append(('product_id', 'in', self.product_ids.ids))
        if self.vendor_ids:
            domain.append(('vendor_id', 'in', self.vendor_ids.ids))
        if self.service_type_ids:
            domain.append(('service_type_id', 'in', self.service_type_ids.ids))
        if self.workshop_ids:
            domain.append(('workshop_id', 'in', self.workshop_ids.ids))

        group_fields = REPORT_GROUPBY.get(self.report_type, [])

        # Sort by subtotal for "expensive" reports, by count otherwise
        sort_field = 'subtotal' if 'expensive' in self.report_type else 'service_count'
        order = f'{sort_field} desc'

        # Build the action context. We DON'T add `search_default_g_month`
        # here because adding a second groupby breaks bar-by-measure
        # sorting — the user can still toggle Month grouping in the UI.
        context = {
            f'search_default_g_{self._group_key(g)}': 1
            for g in group_fields
        }
        # graph_measure / graph_order tell the graph view which measure to
        # use and how to order bars (by measure value, not group key).
        context['graph_measure'] = sort_field
        context['graph_order'] = 'DESC'
        context['pivot_measures'] = [sort_field]

        # Top-N restriction: pick the top N values for the primary group field,
        # then narrow the domain to dashboard rows belonging to those groups.
        # This makes graph/pivot views actually show "top 10" (limit alone
        # doesn't do that — it only paginates lists).
        limit_n = int(self.top_n or 0)
        if group_fields and limit_n:
            primary = group_fields[0]
            top_groups = self.env['fleet.service.dashboard'].read_group(
                domain=domain,
                fields=[f'{sort_field}:sum'],
                groupby=[primary],
                orderby=f'{sort_field} desc',
                limit=limit_n,
                lazy=False,
            )
            top_ids = [
                row[primary][0] for row in top_groups
                if row.get(primary)
            ]
            if top_ids:
                domain.append((primary, 'in', top_ids))

        view_modes = {
            'graph': 'graph,pivot,list,kanban',
            'pivot': 'pivot,graph,list,kanban',
            'list': 'list,graph,pivot,kanban',
            'kanban': 'kanban,graph,pivot,list',
        }

        report_label = dict(REPORT_SELECTION).get(self.report_type, 'რეპორტი')
        n_label = 'ყველა' if not limit_n else f'ტოპ {limit_n}'
        title = (
            f"{report_label} ({n_label}) — "
            f"{start.strftime('%Y-%m-%d')} → {end.strftime('%Y-%m-%d')}"
        )

        action = {
            'type': 'ir.actions.act_window',
            'name': title,
            'res_model': 'fleet.service.dashboard',
            'view_mode': view_modes[self.view_mode],
            'domain': domain,
            'context': context,
            'target': 'current',
            'search_view_id': (
                self.env.ref('fleet_dashboard.view_fleet_service_dashboard_search').id,
                'search',
            ),
            'order': order,
        }
        # `limit` here paginates list views; for graph/pivot the domain
        # restriction above is what enforces top-N.
        if limit_n:
            action['limit'] = limit_n
        return action

    @staticmethod
    def _group_key(field_name):
        # Maps dashboard field names → search-view filter suffixes
        mapping = {
            'vehicle_id': 'vehicle',
            'product_id': 'product',
            'workshop_id': 'workshop',
            'vendor_id': 'vendor',
            'service_type_id': 'type',
        }
        return mapping.get(field_name, field_name)

    # ------------------------------------------------------------------
    # Cost per km
    # ------------------------------------------------------------------

    def _action_cost_per_km(self, start, end):
        """Compute total spend ÷ km driven, per vehicle, for the period.

        Km comes from fleet.vehicle.odometer (max − min in period).
        Spend comes from fleet.service.product.line.subtotal (using either
        the line's x_studio_date or the parent service's date — same
        COALESCE logic as the analytics view).

        Vehicle filter (wizard.vehicle_ids) is honored. Other filters
        (workshop/vendor/...) are intentionally ignored: cost-per-km is
        only meaningful at the vehicle level over a clean km baseline.
        """
        Result = self.env['fleet.cost.per.km.result'].sudo()
        Result.search([('wizard_id', '=', self.id)]).unlink()

        vehicle_filter = self.vehicle_ids.ids or None
        company_currency = self.env.company.currency_id

        # 1) Spend per vehicle in period — pulled from the SQL analytics view
        #    so it matches what the rest of the dashboard would show.
        spend_domain = [('date', '>=', start), ('date', '<=', end)]
        if vehicle_filter:
            spend_domain.append(('vehicle_id', 'in', vehicle_filter))
        spend_rows = self.env['fleet.service.dashboard'].read_group(
            domain=spend_domain,
            fields=['subtotal:sum', 'service_count:sum'],
            groupby=['vehicle_id'],
            lazy=False,
        )
        spend_by_vehicle = {
            row['vehicle_id'][0]: {
                'spend': row.get('subtotal') or 0.0,
                'services': row.get('service_count') or 0,
            }
            for row in spend_rows if row.get('vehicle_id')
        }

        # 2) Odometer min/max per vehicle in period
        odo_domain = [('date', '>=', start), ('date', '<=', end)]
        if vehicle_filter:
            odo_domain.append(('vehicle_id', 'in', vehicle_filter))
        odo_rows = self.env['fleet.vehicle.odometer'].read_group(
            domain=odo_domain,
            fields=['value:max', 'value:min'],
            groupby=['vehicle_id'],
            lazy=False,
        )
        # Odoo 18 read_group returns 'value_max' / 'value_min' when both
        # aggregations are requested. Fall back to 'value' just in case
        # only one aggregation was applied.
        odo_by_vehicle = {
            row['vehicle_id'][0]: {
                'max': row.get('value_max', row.get('value', 0.0)) or 0.0,
                'min': row.get('value_min', 0.0) or 0.0,
            }
            for row in odo_rows if row.get('vehicle_id')
        }

        # 3) Build result rows for the union of both sets, so vehicles with
        #    spend-but-no-odometer (and vice versa) still show up.
        vehicle_ids = set(spend_by_vehicle) | set(odo_by_vehicle)
        if not vehicle_ids:
            raise UserError("ამ პერიოდში არჩეული ავტომობილებისთვის მონაცემები არ არის.")

        rows = []
        for vehicle_id in vehicle_ids:
            spend_info = spend_by_vehicle.get(vehicle_id, {})
            odo_info = odo_by_vehicle.get(vehicle_id, {})
            odo_min = odo_info.get('min', 0.0)
            odo_max = odo_info.get('max', 0.0)
            km = max(odo_max - odo_min, 0.0)
            spend = spend_info.get('spend', 0.0)
            cost_per_km = (spend / km) if km > 0 else 0.0
            rows.append({
                'wizard_id': self.id,
                'vehicle_id': vehicle_id,
                'date_from': start,
                'date_to': end,
                'odometer_start': odo_min,
                'odometer_end': odo_max,
                'km_driven': km,
                'total_spend': spend,
                'service_count': spend_info.get('services', 0),
                'cost_per_km': cost_per_km,
                'currency_id': company_currency.id,
            })
        created = Result.create(rows)

        # Apply top_n — keep only the top N rows by cost_per_km desc
        # (with km > 0 first, then zero-km rows so they don't dominate).
        limit_n = int(self.top_n or 0)
        if limit_n:
            keep = created.sorted(
                key=lambda r: (-1 if r.km_driven > 0 else 0, -r.cost_per_km),
            )[:limit_n]
            (created - keep).unlink()

        n_label = 'ყველა' if not limit_n else f'ტოპ {limit_n}'
        title = (
            f"ღირებულება კმ-ზე ({n_label}) — "
            f"{start.strftime('%Y-%m-%d')} → {end.strftime('%Y-%m-%d')}"
        )
        return {
            'type': 'ir.actions.act_window',
            'name': title,
            'res_model': 'fleet.cost.per.km.result',
            'view_mode': 'list,graph,pivot',
            'domain': [('wizard_id', '=', self.id)],
            'context': {
                'search_default_filter_with_km': 1,
                'graph_measure': 'cost_per_km',
                'graph_order': 'DESC',
                'pivot_measures': ['cost_per_km', 'total_spend', 'km_driven'],
            },
            'target': 'current',
        }

    # ------------------------------------------------------------------
    # No service in period
    # ------------------------------------------------------------------

    def _action_no_service(self, start, end):
        """List vehicles that have NO service log in [start, end]."""
        Result = self.env['fleet.no.service.result'].sudo()
        Result.search([('wizard_id', '=', self.id)]).unlink()

        # Vehicles to check — filtered set if user picked any, otherwise
        # every active vehicle.
        vehicle_domain = [('active', '=', True)]
        if self.vehicle_ids:
            vehicle_domain.append(('id', 'in', self.vehicle_ids.ids))
        all_vehicles = self.env['fleet.vehicle'].search(vehicle_domain)

        # Vehicles WITH a service line in the period — exclude these.
        # Use the dashboard view because it already handles the
        # x_studio_date / parent-date COALESCE.
        serviced_rows = self.env['fleet.service.dashboard'].read_group(
            domain=[
                ('date', '>=', start),
                ('date', '<=', end),
                ('vehicle_id', 'in', all_vehicles.ids),
            ],
            fields=['vehicle_id'],
            groupby=['vehicle_id'],
            lazy=False,
        )
        serviced_ids = {r['vehicle_id'][0] for r in serviced_rows if r.get('vehicle_id')}
        not_serviced = all_vehicles.filtered(lambda v: v.id not in serviced_ids)

        if not not_serviced:
            raise UserError(
                "ყველა არჩეულ ავტომობილს ჰქონდა მინიმუმ ერთი სერვისი ამ პერიოდში."
            )

        # Find each vehicle's most recent service ever, for context.
        last_services = self.env['fleet.vehicle.log.services'].read_group(
            domain=[('vehicle_id', 'in', not_serviced.ids)],
            fields=['vehicle_id', 'date:max'],
            groupby=['vehicle_id'],
            lazy=False,
        )
        last_date_by_vehicle = {
            r['vehicle_id'][0]: r.get('date')
            for r in last_services if r.get('vehicle_id')
        }

        # Look up the actual last-service record for each vehicle so the
        # user can click through.
        last_record_by_vehicle = {}
        for vehicle_id, last_date in last_date_by_vehicle.items():
            if not last_date:
                continue
            rec = self.env['fleet.vehicle.log.services'].search(
                [('vehicle_id', '=', vehicle_id), ('date', '=', last_date)],
                order='id desc', limit=1,
            )
            if rec:
                last_record_by_vehicle[vehicle_id] = rec.id

        rows = []
        for vehicle in not_serviced:
            last_date = last_date_by_vehicle.get(vehicle.id)
            days_since = (end - last_date).days if last_date else 99999
            rows.append({
                'wizard_id': self.id,
                'vehicle_id': vehicle.id,
                'last_service_date': last_date or False,
                'last_service_id': last_record_by_vehicle.get(vehicle.id, False),
                'days_since_last_service': days_since,
                'has_ever_been_serviced': bool(last_date),
            })
        created = Result.create(rows)

        # Apply top_n — keep N most overdue (highest days_since)
        limit_n = int(self.top_n or 0)
        if limit_n:
            keep = created.sorted(
                key=lambda r: -r.days_since_last_service,
            )[:limit_n]
            (created - keep).unlink()

        n_label = 'ყველა' if not limit_n else f'ტოპ {limit_n}'
        title = (
            f"უმომსახურებო ავტომობილები ({n_label}) — "
            f"{start.strftime('%Y-%m-%d')} → {end.strftime('%Y-%m-%d')}"
        )
        return {
            'type': 'ir.actions.act_window',
            'name': title,
            'res_model': 'fleet.no.service.result',
            'view_mode': 'list,graph',
            'domain': [('wizard_id', '=', self.id)],
            'context': {
                'graph_measure': 'days_since_last_service',
                'graph_order': 'DESC',
            },
            'target': 'current',
        }
