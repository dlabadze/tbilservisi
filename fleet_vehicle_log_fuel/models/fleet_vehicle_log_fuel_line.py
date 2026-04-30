# Copyright 2025
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class FleetVehicleLogFuelLine(models.Model):
    _name = "fleet.vehicle.log.fuel.line"
    _description = "Fuel log extra line"

    fuel_log_id = fields.Many2one(
        comodel_name="fleet.vehicle.log.fuel",
        string="Fuel Log",
        required=True,
        ondelete="cascade",
        index=True,
    )
    date = fields.Date(string="თარიღი")
    card_number = fields.Char(string="ბარათის N")
    station = fields.Char(string="სადგური")
    quantity = fields.Float(string="რაოდენობა")


