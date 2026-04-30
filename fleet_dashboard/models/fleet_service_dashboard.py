from odoo import fields, models, tools


class FleetServiceDashboard(models.Model):
    """Read-only analytics view over fleet.service.product.line.

    One row per line. `service_count` is 1 on the first line of each service
    and 0 on the rest, so SUM(service_count) gives a correct distinct-service
    count when grouping by vehicle/workshop.
    """
    _name = 'fleet.service.dashboard'
    _description = 'ავტოპარკის სერვისის ანალიტიკა'
    _auto = False
    _rec_name = 'vehicle_id'
    # Default sort: highest spend first. The wizard overrides per report
    # type via the action's `order` key, but this is what graph/pivot use
    # when no override is provided.
    _order = 'subtotal desc, date desc'

    date = fields.Date(string='თარიღი', readonly=True)
    service_id = fields.Many2one('fleet.vehicle.log.services', string='სერვისი', readonly=True)
    service_type_id = fields.Many2one('fleet.service.type', string='სერვისის ტიპი', readonly=True)
    vehicle_id = fields.Many2one('fleet.vehicle', string='ავტომობილი', readonly=True)
    product_id = fields.Many2one('product.product', string='ნაწილი / პროდუქტი', readonly=True)
    vendor_id = fields.Many2one('res.partner', string='მომწოდებელი', readonly=True)
    workshop_id = fields.Many2one(
        'stock.location',
        string='საამქრო',
        readonly=True,
        help="კომპონენტის წყარო ლოკაცია რემონტზე (x_studio_saamqro).",
    )
    company_id = fields.Many2one('res.company', string='კომპანია', readonly=True)
    currency_id = fields.Many2one('res.currency', string='ვალუტა', readonly=True)

    quantity = fields.Float(string='რაოდენობა', readonly=True, aggregator='sum')
    price_unit = fields.Float(string='ერთეულის ფასი', readonly=True, aggregator='avg')
    subtotal = fields.Float(string='ჯამი', readonly=True, aggregator='sum')
    service_count = fields.Integer(string='სერვისების რაოდ.', readonly=True, aggregator='sum')
    line_count = fields.Integer(string='სტრიქონების რაოდ.', readonly=True, aggregator='sum')

    def action_open_service(self):
        """Open the parent fleet.vehicle.log.services form for this row."""
        self.ensure_one()
        if not self.service_id:
            return False
        return {
            'type': 'ir.actions.act_window',
            'name': self.service_id.display_name,
            'res_model': 'fleet.vehicle.log.services',
            'res_id': self.service_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)

        # Some Studio fields on fleet.service.product.line are stored as
        # related/computed fields without their own columns. Probe the real
        # table columns and degrade gracefully when one isn't present.
        self.env.cr.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'fleet_service_product_line'
        """)
        line_cols = {r[0] for r in self.env.cr.fetchall()}

        date_expr = (
            "COALESCE(l.x_studio_date, s.date)"
            if 'x_studio_date' in line_cols else "s.date"
        )
        vehicle_expr = (
            "COALESCE(l.x_studio_vehicle_id, s.vehicle_id)"
            if 'x_studio_vehicle_id' in line_cols else "s.vehicle_id"
        )
        workshop_expr = (
            "l.x_studio_saamqro" if 'x_studio_saamqro' in line_cols else "NULL::integer"
        )

        self.env.cr.execute(f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    l.id                                          AS id,
                    {date_expr}                                   AS date,
                    l.service_id                                  AS service_id,
                    s.service_type_id                             AS service_type_id,
                    {vehicle_expr}                                AS vehicle_id,
                    l.product_id                                  AS product_id,
                    s.vendor_id                                   AS vendor_id,
                    {workshop_expr}                               AS workshop_id,
                    l.currency_id                                 AS currency_id,
                    s.company_id                                  AS company_id,
                    l.quantity                                    AS quantity,
                    l.price_unit                                  AS price_unit,
                    l.subtotal                                    AS subtotal,
                    1                                             AS line_count,
                    CASE WHEN ROW_NUMBER() OVER (
                            PARTITION BY l.service_id ORDER BY l.id
                         ) = 1 THEN 1 ELSE 0 END                  AS service_count
                FROM fleet_service_product_line l
                LEFT JOIN fleet_vehicle_log_services s ON s.id = l.service_id
            )
        """)
