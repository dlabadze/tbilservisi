from odoo import api, models, fields


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _resolve_location_and_picking_code(self):
        """Best-effort resolution of source location and picking type code.

        This mirrors patterns seen in stock modules: look at explicit context
        keys first, then active records from picking/move/move.line.
        Returns tuple (location_id:int|None, picking_code:str|None).
        """
        ctx = self.env.context or {}

        # 1) Direct context hints used commonly by stock views
        location_id = (
            ctx.get("filter_location_id")
            or ctx.get("default_location_id")
            or ctx.get("location_id")
        )

        picking_code = None
        default_pt_id = ctx.get("default_picking_type_id")
        if default_pt_id:
            pt = self.env["stock.picking.type"].browse(default_pt_id)
            if pt:
                picking_code = pt.code

        # 2) Derive from active record if available
        active_model = ctx.get("active_model")
        active_id = ctx.get("active_id")
        if active_model and active_id:
            if active_model == "stock.picking":
                picking = self.env["stock.picking"].browse(active_id)
                if picking:
                    location_id = location_id or (picking.location_id.id or None)
                    picking_code = picking_code or picking.picking_type_id.code
            elif active_model == "stock.move":
                move = self.env["stock.move"].browse(active_id)
                if move:
                    location_id = location_id or (move.location_id.id or None)
                    if move.picking_id:
                        picking_code = picking_code or move.picking_id.picking_type_id.code
            elif active_model == "stock.move.line":
                mline = self.env["stock.move.line"].browse(active_id)
                if mline:
                    location_id = location_id or (mline.location_id.id or None)
                    if mline.picking_id:
                        picking_code = picking_code or mline.picking_id.picking_type_id.code

        return location_id, picking_code

    def _get_allowed_products_for_location_from_context(self):
        """Return list of product IDs allowed by location context.

        Applies when a source location can be resolved and picking type is
        'internal'. Location usage must be internal/transit. The goal is to
        show products available at this source location.
        """
        location_id, picking_code = self._resolve_location_and_picking_code()
        if not location_id or picking_code != "internal":
            return None

        # Ensure we only consider relevant location usages
        location = self.env["stock.location"].browse(location_id)
        if not location or location.usage not in ("internal", "transit"):
            return None

        # Use fast helper from picking model with caching and parent_path SQL
        company_id = self.env.company.id if self.env.company else None
        return self.env["stock.picking"]._get_allowed_product_ids_for_location(location_id, company_id=company_id)

    on_hand_at_source = fields.Float(
        string="On Hand at Source",
        compute="_compute_on_hand_at_source",
        digits="Product Unit of Measure",
        compute_sudo=True,
    )

    def _compute_on_hand_at_source(self):
        # Resolve source location from context (same logic as filtering)
        location_id, picking_code = self._resolve_location_and_picking_code()
        # Default to 0.0
        quantities_by_product = {pid: 0.0 for pid in self.ids}
        if location_id:
            location = self.env["stock.location"].browse(location_id)
            if location and location.usage in ("internal", "transit") and self.ids:
                # Expand to internal child locations only
                child_internal_ids = self.env["stock.location"].search([
                    ("id", "child_of", location_id),
                    ("usage", "=", "internal"),
                ]).ids
                if child_internal_ids:
                    params = [tuple(child_internal_ids), tuple(self.ids)]
                    where_company = ""
                    if self.env.company:
                        where_company = " AND q.company_id = %s"
                        params.append(self.env.company.id)
                    query = f"""
                        SELECT q.product_id, COALESCE(SUM(q.quantity - q.reserved_quantity), 0) AS available
                          FROM stock_quant q
                         WHERE q.location_id IN %s
                           AND q.product_id IN %s
                           {where_company}
                         GROUP BY q.product_id
                    """
                    self.env.cr.execute(query, tuple(params))
                    for pid, available in self.env.cr.fetchall():
                        quantities_by_product[pid] = available or 0.0
        for product in self:
            product.on_hand_at_source = quantities_by_product.get(product.id, 0.0)

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        args = list(args or [])
        allowed = self._get_allowed_products_for_location_from_context()
        if allowed is not None:
            if allowed:
                args = [("id", "in", allowed)] + args
            else:
                # No products available at the location: return empty
                return []
        return super().name_search(name=name, args=args, operator=operator, limit=limit)

    @api.model
    def search(self, args, offset=0, limit=None, order=None):
        args = list(args or [])
        allowed = self._get_allowed_products_for_location_from_context()
        if allowed is not None:
            if allowed:
                args = [("id", "in", allowed)] + args
            else:
                # No products available at the location: return empty recordset
                return self.browse()
        return super().search(args, offset=offset, limit=limit, order=order)

    @api.model
    def search_count(self, args, limit=None):
        args = list(args or [])
        allowed = self._get_allowed_products_for_location_from_context()
        if allowed is not None:
            if allowed:
                args = [("id", "in", allowed)] + args
            else:
                # No products available at the location: zero results
                return 0
        return super().search_count(args, limit=limit)

    def _search(self, args, offset=0, limit=None, order=None, **kwargs):
        """Ensure domain restriction also applies to generic searches (Search More).

        Some flows bypass search() and call _search() directly (e.g., list dialogs),
        so we inject the allowed product constraint here too.
        """
        args = list(args or [])
        allowed = self._get_allowed_products_for_location_from_context()
        if allowed is not None:
            if allowed:
                args = [("id", "in", allowed)] + args
            else:
                return []
        # Do not forward unknown kwargs (different addons define different signatures)
        return super()._search(args, offset=offset, limit=limit, order=order)


