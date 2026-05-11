from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = "stock.move"

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


