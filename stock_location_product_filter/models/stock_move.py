from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

    on_hand_at_source = fields.Float(
        string="ნაშთი საწყობში",
        compute="_compute_on_hand_at_source",
        digits="Product Unit of Measure",
        compute_sudo=True,
    )

    allowed_product_ids = fields.Many2many(
        comodel_name="product.product",
        compute="_compute_allowed_product_ids",
        string="Allowed Products",
        compute_sudo=True,
    )

    @api.depends("location_id", "picking_id", "picking_id.picking_type_id", "picking_id.location_id", "picking_id.company_id")
    def _compute_allowed_product_ids(self):
        for move in self:
            product_ids = []
            picking = move.picking_id
            if (
                picking
                and picking.picking_type_id
                and picking.picking_type_id.code == "internal"
                and picking.location_id
                and picking.location_id.usage in ("internal", "transit")
            ):
                product_ids = self._compute_allowed_products_for_location(picking.location_id.id, company_id=picking.company_id.id) or []
            move.allowed_product_ids = [(6, 0, product_ids)]

    @api.onchange("location_id", "picking_id")
    def _onchange_location_set_product_domain(self):
        if not self:
            return
        move = self[0]
        domain = []
        picking = move.picking_id
        if picking and picking.picking_type_id and picking.picking_type_id.code == "internal" and picking.location_id:
            allowed_ids = self._compute_allowed_products_for_location(picking.location_id.id, company_id=picking.company_id.id)
            if allowed_ids is not None:
                domain = [("id", "in", allowed_ids or [-1])]
        return {"domain": {"product_id": domain}}

    def _compute_allowed_products_for_location(self, location_id, company_id=None):
        if not location_id:
            return None
        location = self.env["stock.location"].browse(location_id)
        if not location or location.usage not in ("internal", "transit"):
            return None
        # Expand child locations once, restrict to internal usage for strictness
        location_ids = self.env["stock.location"].search([("id", "child_of", location_id), ("usage", "=", "internal")]).ids
        if not location_ids:
            return []
        # Company filter: strict to provided company if any
        where_company = "company_id = %s" if company_id else "TRUE"
        query = f"""
            SELECT product_id
              FROM stock_quant
             WHERE location_id IN %s
               AND {where_company}
             GROUP BY product_id
            HAVING SUM(quantity) > SUM(reserved_quantity)
        """
        params = [tuple(location_ids)] + ([company_id] if company_id else [])
        self.env.cr.execute(query, params)
        rows = self.env.cr.fetchall()
        return [r[0] for r in rows]

    @api.depends(
        "product_id",
        "product_uom",
        "picking_id",
        "picking_id.picking_type_id",
        "picking_id.location_id",
        "picking_id.company_id",
    )
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


