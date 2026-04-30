from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    on_hand_at_repair = fields.Float(
        string="On Hand",
        compute="_compute_on_hand_at_repair",
        digits="Product Unit of Measure",
        compute_sudo=True,
    )

    def _rlpf_resolve_repair_and_location(self):
        """Resolve (repair, location_id, line_type) from context.
        Only applies within a real repair.order context.
        Prefers explicit context hints (when editing repair lines), then header.
        Returns (repair_record_or_None, location_id_or_None, line_type_or_None)."""
        ctx = self.env.context or {}

        # Hard guard: only act when repair scope is explicitly set by the UI
        if not ctx.get("rlpf_repair_context"):
            return None, None, None

        # Line type hint is expected to be provided by the repair line field context
        line_type = ctx.get("default_repair_line_type") or ctx.get("repair_line_type")

        # Try to resolve repair.order
        try:
            Repair = self.env["repair.order"]
        except KeyError:
            # If Repair is not installed, never apply
            return None, None, None

        repair = None
        active_id = ctx.get("active_id")
        if active_id:
            rec = Repair.browse(active_id)
            if rec.exists():
                repair = rec
        if not repair:
            active_ids = ctx.get("active_ids") or []
            if active_ids:
                rec = Repair.browse(active_ids[0])
                if rec.exists():
                    repair = rec
        if not repair:
            default_id = ctx.get("default_repair_id")
            if default_id:
                rec = Repair.browse(default_id)
                if rec.exists():
                    repair = rec

        # We are in explicit repair scope; continue even if record not yet saved

        # Resolve location: prefer explicit hint from repair line field context, else header
        location_id = (
            ctx.get("filter_location_id")
            or ctx.get("default_location_id")
            or ctx.get("location_id")
        )
        if not location_id:
            location = getattr(repair, "location_id", False)
            location_id = location.id if location else None
        return repair, location_id, line_type

    def _rlpf_allowed_products_for_location(self, location_id, company_id=None):
        """Return product IDs with available stock under location_id internal subtree."""
        if not location_id:
            return None
        location = self.env["stock.location"].browse(location_id)
        if not location or location.usage not in ("internal", "transit"):
            return None
        loc_ids = self.env["stock.location"].search(
            [("id", "child_of", location_id), ("usage", "=", "internal")]
        ).ids
        if not loc_ids:
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
        params = [tuple(loc_ids)] + ([company_id] if company_id else [])
        self.env.cr.execute(query, params)
        return [row[0] for row in self.env.cr.fetchall()]

    def _compute_on_hand_at_repair(self):
        location_id = None
        company_id = self.env.company.id if self.env.company else None
        # Resolve location from current context/active repair
        repair, location_id, _line_type = self._rlpf_resolve_repair_and_location()
        quantities_by_product = {pid: 0.0 for pid in self.ids}
        if location_id and self.ids:
            location = self.env["stock.location"].browse(location_id)
            if location and location.usage in ("internal", "transit"):
                child_internal_ids = self.env["stock.location"].search([
                    ("id", "child_of", location_id),
                    ("usage", "=", "internal"),
                ]).ids
                if child_internal_ids:
                    params = [tuple(child_internal_ids), tuple(self.ids)]
                    where_company = ""
                    if company_id:
                        where_company = " AND q.company_id = %s"
                        params.append(company_id)
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
            product.on_hand_at_repair = quantities_by_product.get(product.id, 0.0)

    @staticmethod
    def _rlpf_args_have_id_lookup(args):
        """True if domain already restricts by id (e.g. internal fetch by id).

        When Odoo fetches a Many2one for display (reports, mail, compute), it
        searches by explicit id list. Filtering those would hide legitimate
        records and surface as a misleading AccessError.
        """
        for leaf in args or []:
            if isinstance(leaf, (list, tuple)) and len(leaf) == 3 and leaf[0] == "id":
                return True
        return False

    def _rlpf_inject_repair_domain(self, args):
        """If in repair.order context and product_location_src_id is set,
        and the repair line type is 'add', prepend domain restricting products
        to those available at the repair's source location. This affects dropdown
        and Search More. Outside repair context it must be a no-op."""
        args = list(args or [])
        ctx = self.env.context or {}
        # Hard guard: only act when repair scope is explicitly set by the UI
        if not ctx.get("rlpf_repair_context"):
            return args
        # Never restrict explicit id lookups (display fetches, computes, reports)
        if self._rlpf_args_have_id_lookup(args):
            return args
        repair, location_id, line_type = self._rlpf_resolve_repair_and_location()
        # Enforce operation type == 'repair'
        if repair:
            picking_type_code = (getattr(getattr(repair, "picking_type_id", False), "code", "") or "").lower()
            if picking_type_code != "repair":
                return args
        # Apply ONLY within repair context and primarily for 'add' type lines.
        # If line_type is missing in context (UI may not pass it), treat as 'add'.
        if line_type is not None and line_type != "add":
            return args
        if not location_id:
            return args
        company_id = None
        if repair and repair.company_id:
            company_id = repair.company_id.id
        else:
            company_id = self.env.company.id if self.env.company else None
        allowed = self._rlpf_allowed_products_for_location(location_id, company_id=company_id)
        if allowed is None:
            return args
        if not allowed:
            # Force empty result
            return [("id", "in", [-1])]
        return [("id", "in", allowed)] + args

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        args = self._rlpf_inject_repair_domain(args)
        return super().name_search(name=name, args=args, operator=operator, limit=limit)

    @api.model
    def search(self, args, offset=0, limit=None, order=None):
        args = self._rlpf_inject_repair_domain(args)
        return super().search(args, offset=offset, limit=limit, order=order)

    @api.model
    def search_count(self, args, limit=None):
        args = self._rlpf_inject_repair_domain(args)
        return super().search_count(args, limit=limit)

    def _search(self, args, offset=0, limit=None, order=None, **kwargs):
        args = self._rlpf_inject_repair_domain(args)
        return super()._search(args, offset=offset, limit=limit, order=order)


