from odoo import api, models, fields


class StockPicking(models.Model):
    _inherit = "stock.picking"

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # Determine picking type from defaults or context
        picking_type_id = res.get("picking_type_id") or self.env.context.get("default_picking_type_id")
        if picking_type_id:
            picking_type = self.env["stock.picking.type"].browse(picking_type_id)
            if picking_type and picking_type.code == "internal":
                default_location = self.env.user.def_location_id
                if default_location:
                    # Force the user's default as source location for internal transfers
                    res["location_id"] = default_location.id
        return res

    @api.onchange("picking_type_id")
    def _onchange_set_default_location_from_user(self):
        if not self.picking_type_id or self.picking_type_id.code != "internal":
            return
        user = self.env.user
        default_location = user.def_location_id
        if default_location:
            # Prefer source location (location_id) when creating internal transfer
            if not self.location_id:
                self.location_id = default_location
            # If destination is empty and source is set to user's default, keep dest untouched
            # No automatic destination change to avoid side effects

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Apply only for internal transfers and when not explicitly provided
            picking_type_id = vals.get("picking_type_id")
            location_id = vals.get("location_id")
            if picking_type_id and not location_id:
                picking_type = self.env["stock.picking.type"].browse(picking_type_id)
                if picking_type and picking_type.code == "internal":
                    user = self.env.user
                    if user.def_location_id:
                        vals["location_id"] = user.def_location_id.id
        return super().create(vals_list)


