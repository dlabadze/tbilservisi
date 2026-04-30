from odoo import api, models


class StockMove(models.Model):
    _inherit = "stock.move"

    @api.onchange("repair_id", "repair_line_type", "type", "product_id")
    def _onchange_repair_restrict_product_domain(self):
        """Restrict product selection on repair lines when type is 'add'.

        Applies only when editing stock.move lines inside repair.order:
        - Parent record is a repair.order (resolved from context)
        - line type is 'add' (supports custom 'reapir_line_type' or standard 'type')
        The allowed products are those available (quantity > reserved) in source location:
        - repair.order.location_id
        """
        if not self:
            return

        ctx = self.env.context or {}
        line = self[0]
        # Determine selected line type
        line_type = getattr(line, "repair_line_type", None) or getattr(line, "type", None)

        if line_type != "add":
            return

        # Prefer explicit link from the line, else resolve from context
        repair = getattr(line, "repair_id", False) or self._resolve_repair_from_context(ctx)
        if not repair:
            return

        # Apply only when the repair picking type code is 'repair'
        picking_type_code = (getattr(getattr(repair, "picking_type_id", False), "code", "") or "").lower()
        if picking_type_code != "repair":
            return

        # Only filter if header has explicit location_id set
        location = getattr(repair, "location_id", False)
        domain = []
        if location and location.exists():
            allowed_ids = self._rlpf_compute_allowed_products_for_location(location.id, company_id=repair.company_id.id)
            if allowed_ids is not None:
                domain = [("id", "in", allowed_ids or [-1])]
        return {"domain": {"product_id": domain}}

    def _resolve_repair_from_context(self, ctx):
        """Safely resolve repair.order from context. Returns record or None.
        Works even if the Repair app is not installed (no crash)."""
        try:
            Repair = self.env["repair.order"]
        except KeyError:
            return None
        active_id = ctx.get("active_id")
        if active_id:
            rec = Repair.browse(active_id)
            if rec.exists():
                return rec
        active_ids = ctx.get("active_ids") or []
        if active_ids:
            rec = Repair.browse(active_ids[0])
            if rec.exists():
                return rec
        default_id = ctx.get("default_repair_id")
        if default_id:
            rec = Repair.browse(default_id)
            if rec.exists():
                return rec
        return None

    def _rlpf_compute_allowed_products_for_location(self, location_id, company_id=None):
        """Return product IDs with available stock in the given location subtree."""
        if not location_id:
            return None
        location = self.env["stock.location"].browse(location_id)
        if not location or location.usage not in ("internal", "transit"):
            return None
        # Only internal child locations
        location_ids = self.env["stock.location"].search(
            [("id", "child_of", location_id), ("usage", "=", "internal")]
        ).ids
        if not location_ids:
            return []
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


