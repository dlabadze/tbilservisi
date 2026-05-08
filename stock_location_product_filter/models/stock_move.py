from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    on_hand_at_source = fields.Float(
        string="ნაშთი საწყობში",
        compute="_compute_on_hand_at_source",
        digits="Product Unit of Measure",
        compute_sudo=True,
    )
    product_id_domain = fields.Binary(
        compute='_compute_product_id_domain',
        store=False,
    )

    @api.depends('location_id', 'picking_id.picking_type_id', 'repair_line_type')
    def _compute_product_id_domain(self):
        for move in self:
            is_internal = move.picking_id.picking_type_id.code == 'internal'
            is_repair_add = bool(move.repair_id) and move.repair_line_type == 'add'

            if not move.location_id or not (is_internal or is_repair_add):
                move.product_id_domain = []
                continue

            quants = self.env['stock.quant'].search([
                ('location_id', '=', move.location_id.id),
                ('quantity', '>', 0),
            ])
            move.product_id_domain = [('id', 'in', quants.mapped('product_id').ids)]

    @api.depends('location_id', 'product_id', 'picking_id.location_id', 'picking_id.picking_type_id')
    def _compute_on_hand_at_source(self):
        for move in self:
            move.on_hand_at_source = 0.0

        # Use move.location_id, not picking.location_id
        grouped = {}
        for move in self:
            picking = move.picking_id
            if (
                    move.product_id
                    and move.location_id
                    and move.location_id.usage in ("internal", "transit")
                    and picking
                    and picking.picking_type_id
                    and picking.picking_type_id.code == "internal"
            ):
                # Key on move's own source location, not picking header location
                company_id = picking.company_id.id if picking.company_id else None
                key = (move.location_id.id, company_id)
                grouped.setdefault(key, []).append(move)

        for (source_location_id, company_id), moves in grouped.items():
            product_ids = list({m.product_id.id for m in moves})
            if not product_ids:
                continue

            location = self.env["stock.location"].browse(source_location_id)
            if not location or not location.parent_path:
                continue

            # Build params — omit company filter if no company (quants may have company_id = False)
            params = [f"{location.parent_path}%", tuple(product_ids)]
            company_clause = ""
            if company_id:
                company_clause = "AND q.company_id = %s"
                params.insert(1, company_id)

            query = f"""
                SELECT q.product_id, COALESCE(SUM(q.quantity - q.reserved_quantity), 0) AS available
                  FROM stock_quant q
                  JOIN stock_location l ON l.id = q.location_id
                 WHERE l.parent_path LIKE %s
                   AND l.usage = 'internal'
                   {company_clause}
                   AND q.product_id IN %s
                 GROUP BY q.product_id
            """
            self.env.cr.execute(query, tuple(params))
            qty_by_product = dict(self.env.cr.fetchall() or [])

            for m in moves:
                qty = qty_by_product.get(m.product_id.id, 0.0)
                if m.product_uom and m.product_uom != m.product_id.uom_id:
                    qty = m.product_id.uom_id._compute_quantity(qty, m.product_uom)
                m.on_hand_at_source = qty