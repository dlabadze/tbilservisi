from odoo import api, fields, models


class Waybill(models.Model):
    _inherit = "waybill"

    is_purchase_processed = fields.Boolean(
        string="Already In Purchases",
        compute="_compute_is_purchase_processed",
    )
    is_sale_processed = fields.Boolean(
        string="Already In Sales",
        compute="_compute_is_sale_processed",
    )

    @api.depends("waybill_number")
    def _compute_is_purchase_processed(self):
        for record in self:
            record.is_purchase_processed = False

        waybills_with_number = self.filtered(lambda w: w.waybill_number)
        if not waybills_with_number:
            return

        numbers = {
            (record.waybill_number or "").strip()
            for record in waybills_with_number
            if record.waybill_number
        }
        if not numbers:
            return

        processed_numbers = set()
        number_list = list(numbers)

        purchase_orders_by_origin = self.env["purchase.order"].sudo().search_read(
            [
                ("origin", "in", number_list),
                ("state", "!=", "cancel"),
            ],
            ["origin"],
        )
        for purchase_order in purchase_orders_by_origin:
            origin = (purchase_order.get("origin") or "").strip()
            if origin:
                processed_numbers.add(origin)

        account_move_model = self.env["account.move"].sudo()
        if "invoice_number" in account_move_model._fields:
            vendor_bills = account_move_model.search_read(
                [
                    ("move_type", "in", ["in_invoice", "in_refund"]),
                    ("state", "!=", "cancel"),
                    ("invoice_number", "in", number_list),
                ],
                ["invoice_number"],
            )
            for bill in vendor_bills:
                invoice_number = (bill.get("invoice_number") or "").strip()
                if invoice_number:
                    processed_numbers.add(invoice_number)

        for record in waybills_with_number:
            record.is_purchase_processed = (record.waybill_number or "").strip() in processed_numbers

    @api.depends("waybill_number")
    def _compute_is_sale_processed(self):
        for record in self:
            record.is_sale_processed = False

        waybills_with_number = self.filtered(lambda w: w.waybill_number)
        if not waybills_with_number:
            return

        numbers = {
            (record.waybill_number or "").strip()
            for record in waybills_with_number
            if record.waybill_number
        }
        if not numbers:
            return

        processed_numbers = set()
        number_list = list(numbers)

        sale_order_model = self.env["sale.order"].sudo()
        if "invoice_number" in sale_order_model._fields:
            sale_orders = sale_order_model.search_read(
                [
                    ("state", "!=", "cancel"),
                    ("invoice_number", "in", number_list),
                ],
                ["invoice_number"],
            )
            for sale_order in sale_orders:
                invoice_number = (sale_order.get("invoice_number") or "").strip()
                if invoice_number:
                    processed_numbers.add(invoice_number)

        account_move_model = self.env["account.move"].sudo()
        if "invoice_number" in account_move_model._fields:
            customer_invoices = account_move_model.search_read(
                [
                    ("move_type", "in", ["out_invoice", "out_refund"]),
                    ("state", "!=", "cancel"),
                    ("invoice_number", "in", number_list),
                ],
                ["invoice_number"],
            )
            for invoice in customer_invoices:
                invoice_number = (invoice.get("invoice_number") or "").strip()
                if invoice_number:
                    processed_numbers.add(invoice_number)

        for record in waybills_with_number:
            record.is_sale_processed = (record.waybill_number or "").strip() in processed_numbers
