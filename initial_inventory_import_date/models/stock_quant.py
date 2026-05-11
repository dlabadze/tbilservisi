# -*- coding: utf-8 -*-

from odoo import fields, models


class StockQuant(models.Model):
    _inherit = "stock.quant"

    def _get_inventory_move_values(
        self, qty, location_id, location_dest_id, package_id=False, package_dest_id=False
    ):
        vals = super()._get_inventory_move_values(
            qty, location_id, location_dest_id, package_id, package_dest_id
        )
        inventory_datetime = self.env.context.get("dv_initial_inventory_datetime")
        if inventory_datetime:
            inventory_datetime = fields.Datetime.to_datetime(inventory_datetime)
            vals["date"] = inventory_datetime
            for command in vals.get("move_line_ids", []):
                if command[0] == 0 and isinstance(command[2], dict):
                    command[2]["date"] = inventory_datetime
        return vals
