# Copyright 2022 ForgeFlow S.L.  <https://www.forgeflow.com>
# Copyright 2024 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class FleetVehicleLogFuel(models.Model):
    _name = "fleet.vehicle.log.fuel"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "service_type_id"
    _description = "Fuel log for vehicles"

    active = fields.Boolean(default=True)
    vehicle_id = fields.Many2one(
        "fleet.vehicle",
        "Vehicle",
        required=True,
        help="Vehicle concerned by this log",
    )
    amount = fields.Monetary("Cost")
    description = fields.Char()
    odometer_id = fields.Many2one(
        "fleet.vehicle.odometer",
        "Odometer",
        required=False,
        help="Odometer measure of the vehicle at the moment of this log",
    )
    odometer = fields.Float(
        compute="_compute_odometer",
        store=True,
        inverse="_inverse_odometer",
        string="Odometer Value",
        required=False,
        help="Odometer measure of the vehicle at the moment of this log",
    )
    odometer_unit = fields.Selection(related="vehicle_id.odometer_unit", string="Unit")
    date = fields.Date(
        help="Date when the cost has been executed",
        default=fields.Date.context_today,
    )
    company_id = fields.Many2one(
        "res.company", "Company", default=lambda self: self.env.company
    )
    currency_id = fields.Many2one("res.currency", related="company_id.currency_id")
    purchaser_id = fields.Many2one(
        "res.partner",
        string="Driver",
        compute="_compute_purchaser_id",
        store=True,
    )
    inv_ref = fields.Char("Vendor Reference")
    vendor_id = fields.Many2one("res.partner", "Vendor")
    notes = fields.Text()
    fuel_type_text = fields.Char(string="საწვავის ტიპი")
    card_number = fields.Char(string="ბარათის N")
    total_quantity = fields.Float(
        string="სულ ჩასხმული რაოდენობა",
        compute="_compute_total_quantity",
        store=True,
    )
    license_plate = fields.Char(
        related="vehicle_id.license_plate",
        string="სახელმწიფო ნომერი",
        store=True,
        readonly=True,
    )
    service_type_id = fields.Many2one(
        "fleet.service.type",
        "Service Type",
        required=False,
        default=lambda self: self.env.ref(
            "fleet.type_service_refueling", raise_if_not_found=False
        ),
    )
    state = fields.Selection(
        [
            ("todo", "To Do"),
            ("running", "Running"),
            ("done", "Done"),
            ("cancelled", "Cancelled"),
        ],
        default="todo",
        string="Stage",
    )
    liter = fields.Float()
    price_per_liter = fields.Float()
    service_id = fields.Many2one(
        comodel_name="fleet.vehicle.log.services", readonly=True, copy=False
    )
    line_ids = fields.One2many(
        comodel_name="fleet.vehicle.log.fuel.line",
        inverse_name="fuel_log_id",
        string="ხაზები",
    )

    @api.onchange("total_quantity", "price_per_liter", "amount")
    def _onchange_liter_price_amount(self):
        liter = float(self.total_quantity)
        price_per_liter = float(self.price_per_liter)
        amount = float(self.amount)
        if price_per_liter == 0:
            # If unit price is zero, force cost to zero and do not infer unit price
            if amount != 0:
                self.amount = 0.0
        elif liter > 0 and round(liter * price_per_liter, 2) != amount:
            self.amount = round(liter * price_per_liter, 2)
        elif amount > 0 and liter > 0 and round(amount / liter, 2) != price_per_liter:
            self.price_per_liter = round(amount / liter, 2)
        # Do not attempt to set total quantity here; it is computed from lines

    @api.depends("odometer_id", "odometer_id.value")
    def _compute_odometer(self):
        for record in self.filtered("odometer_id"):
            record.odometer = record.odometer_id.value

    def _inverse_odometer(self):
        for record in self:
            if record.odometer:
                record.odometer_id = self.env["fleet.vehicle.odometer"].create(
                    record._prepare_fleet_vehicle_odometer_vals()
                )

    @api.depends("line_ids.quantity")
    def _compute_total_quantity(self):
        for record in self:
            record.total_quantity = sum(record.line_ids.mapped("quantity"))

    def _sync_amount_price_with_quantity(self):
        for record in self:
            quantity = float(sum(record.line_ids.mapped("quantity")))
            price_per_liter = float(record.price_per_liter or 0.0)
            amount = float(record.amount or 0.0)
            updates = {}
            if price_per_liter == 0:
                if amount != 0:
                    updates["amount"] = 0.0
            elif (
                quantity > 0
                and round(quantity * price_per_liter, 2) != round(amount, 2)
            ):
                updates["amount"] = round(quantity * price_per_liter, 2)
            elif (
                amount > 0
                and quantity > 0
                and round(amount / quantity, 2) != round(price_per_liter, 2)
            ):
                updates["price_per_liter"] = round(amount / quantity, 2)
            if updates:
                record.with_context(skip_sync_amount=True).write(updates)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        # After lines are created, sync amount/price based on total quantity
        for rec in records:
            rec._sync_amount_price_with_quantity()
        return records

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get("skip_sync_amount"):
            self._sync_amount_price_with_quantity()
        return res

    @api.depends("vehicle_id")
    def _compute_purchaser_id(self):
        for service in self:
            service.purchaser_id = service.vehicle_id.driver_id

    def button_running(self):
        self.filtered(lambda x: x.state == "todo").state = "running"
        return True

    def _prepare_fleet_vehicle_odometer_vals(self):
        return {
            "value": self.odometer,
            "date": self.date or fields.Date.context_today(self),
            "vehicle_id": self.vehicle_id.id,
        }

    def _prepare_fleet_vehicle_log_services_vals(self):
        return {
            "service_type_id": self.service_type_id.id,
            "description": self.description,
            "vehicle_id": self.vehicle_id.id,
            "amount": self.amount,
            "odometer": self.odometer,
            "vendor_id": self.vendor_id.id if self.vendor_id else False,
            "state": "done",
        }

    def button_todo(self):
        records = self.filtered(lambda x: x.state == "cancelled")
        records.state = "todo"
        return True

    def button_done(self):
        for item in self.filtered(lambda x: x.state == "running"):
            if item.service_type_id:
                item.service_id = self.env["fleet.vehicle.log.services"].create(
                    item._prepare_fleet_vehicle_log_services_vals()
                )
            else:
                item.service_id = False
            item.state = "done"
        return True

    def button_cancel(self):
        records = self.filtered(lambda x: x.state in ["todo", "running", "done"])
        records.mapped("service_id").sudo().unlink()
        records.state = "cancelled"
        return True
