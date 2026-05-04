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

    def _compute_on_hand_at_source(self):
        # Default all to 0.0
        for move in self:
            move.on_hand_at_source = 0.0

        # Group eligible moves by (source_location_id, company_id)
        grouped = {}
        for move in self:
            picking = move.picking_id
            if (
                move.product_id
                and picking
                and picking.picking_type_id
                and picking.picking_type_id.code == "internal"
                and picking.location_id
                and picking.location_id.usage in ("internal", "transit")
            ):
                key = (picking.location_id.id, picking.company_id.id if picking.company_id else None)
                grouped.setdefault(key, []).append(move)

        for (root_location_id, company_id), moves in grouped.items():
            # Collect unique product ids
            product_ids = list({m.product_id.id for m in moves})
            if not product_ids:
                continue

            location = self.env["stock.location"].browse(root_location_id)
            if not location or not location.parent_path:
                continue

            # Build query using parent_path LIKE for fast child selection; restrict to internal usage
            where_company = " AND q.company_id = %s" if company_id else ""
            params = [f"{location.parent_path}%"]
            if company_id:
                params.append(company_id)
            params.append(tuple(product_ids))
            query = f"""
                SELECT q.product_id, COALESCE(SUM(q.quantity - q.reserved_quantity), 0) AS available
                  FROM stock_quant q
                  JOIN stock_location l ON l.id = q.location_id
                 WHERE l.parent_path LIKE %s
                   AND l.usage = 'internal'
                   {where_company}
                   AND q.product_id IN %s
                 GROUP BY q.product_id
            """
            self.env.cr.execute(query, tuple(params))
            qty_by_product = dict(self.env.cr.fetchall() or [])

            # Assign per move, converting to the move's UoM when needed
            for m in moves:
                qty = qty_by_product.get(m.product_id.id, 0.0)
                if m.product_uom and m.product_uom != m.product_id.uom_id:
                    qty = m.product_id.uom_id._compute_quantity(qty, m.product_uom)
                m.on_hand_at_source = qty


