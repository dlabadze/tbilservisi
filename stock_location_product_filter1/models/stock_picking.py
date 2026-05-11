from odoo import api, fields, models
from odoo.tools import ormcache


class StockPicking(models.Model):
    _inherit = "stock.picking"

    allowed_product_ids_cached = fields.Many2many(
        comodel_name="product.product",
        compute="_compute_allowed_product_ids_cached",
        string="Allowed Products (Cached)",
        compute_sudo=True,
    )

    @api.depends("location_id", "picking_type_id", "company_id")
    def _compute_allowed_product_ids_cached(self):
        for picking in self:
            product_ids = []
            if (
                picking.picking_type_id
                and picking.picking_type_id.code == "internal"
                and picking.location_id
                and picking.location_id.usage in ("internal", "transit")
            ):
                product_ids = self._get_allowed_product_ids_for_location(
                    picking.location_id.id, company_id=picking.company_id.id
                )
            picking.allowed_product_ids_cached = [(6, 0, product_ids)]

    @api.model
    @ormcache("root_location_id", "company_id")
    def _get_allowed_product_ids_for_location(self, root_location_id, company_id=None):
        if not root_location_id:
            return []
        # Use parent_path LIKE for fast child selection and restrict to internal usage
        location = self.env["stock.location"].browse(root_location_id)
        if not location or not location.parent_path:
            return []
        where_company = "AND q.company_id = %s" if company_id else ""
        params = [f"{location.parent_path}%"]
        if company_id:
            params.append(company_id)
        query = f"""
            SELECT q.product_id
            FROM stock_quant q
            JOIN stock_location l ON l.id = q.location_id
            WHERE l.parent_path LIKE %s
              AND l.usage = 'internal'
              {where_company}
            GROUP BY q.product_id
            HAVING SUM(q.quantity) > SUM(q.reserved_quantity)
        """
        self.env.cr.execute(query, tuple(params))
        return [row[0] for row in self.env.cr.fetchall()]


