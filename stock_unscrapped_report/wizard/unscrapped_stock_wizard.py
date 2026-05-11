from odoo import _, fields, models
from odoo.exceptions import UserError


class UnscrappedStockWizard(models.TransientModel):
    _name = "unscrapped.stock.wizard"
    _description = "Unscrapped Stock Report Wizard"

    date_start = fields.Date(string="Date Start", required=True)
    date_end = fields.Date(string="Date End", required=True)
    line_ids = fields.One2many(
        "unscrapped.stock.report.line", "wizard_id", string="Result Lines"
    )

    def _get_scrapped_product_ids(self):
        """Return product IDs that had any scrap activity in [date_start, date_end].

        Two sources count as 'scrap activity':
        1. stock.scrap records in state 'done' within the range.
        2. stock.move records in state 'done' within the range whose
           destination location is flagged as a scrap location.
        """
        self.ensure_one()
        date_from = fields.Datetime.to_datetime(self.date_start)
        date_to = fields.Datetime.to_datetime(self.date_end)
        # Include the entire end day.
        date_to = date_to.replace(hour=23, minute=59, second=59)

        scrap_records = self.env["stock.scrap"].search(
            [
                ("state", "=", "done"),
                ("date_done", ">=", date_from),
                ("date_done", "<=", date_to),
            ]
        )
        product_ids = set(scrap_records.product_id.ids)

        scrap_locations = self.env["stock.location"].search(
            [("scrap_location", "=", True)]
        )
        if scrap_locations:
            scrap_moves = self.env["stock.move"].search(
                [
                    ("state", "=", "done"),
                    ("date", ">=", date_from),
                    ("date", "<=", date_to),
                    ("location_dest_id", "in", scrap_locations.ids),
                ]
            )
            product_ids.update(scrap_moves.product_id.ids)

        return product_ids

    def action_generate_report(self):
        self.ensure_one()
        if self.date_start > self.date_end:
            raise UserError(_("Date Start must be earlier than or equal to Date End."))

        self.line_ids.unlink()

        scrapped_product_ids = self._get_scrapped_product_ids()

        quant_domain = [
            ("location_id.usage", "=", "internal"),
            ("quantity", ">", 0),
        ]
        if scrapped_product_ids:
            quant_domain.append(("product_id", "not in", list(scrapped_product_ids)))

        # Aggregate quants by (location, product) to collapse lot/package splits.
        grouped = self.env["stock.quant"]._read_group(
            domain=quant_domain,
            groupby=["location_id", "product_id"],
            aggregates=["quantity:sum"],
        )

        line_vals = []
        for location, product, qty_sum in grouped:
            if not qty_sum or qty_sum <= 0:
                continue
            line_vals.append(
                {
                    "wizard_id": self.id,
                    "location_id": location.id,
                    "warehouse_id": location.warehouse_id.id or False,
                    "product_id": product.id,
                    "categ_id": product.categ_id.id,
                    "product_default_code": product.default_code or "",
                    "product_name": product.display_name,
                    "quantity": qty_sum,
                    "uom_id": product.uom_id.id,
                }
            )

        if line_vals:
            self.env["unscrapped.stock.report.line"].create(line_vals)

        action = self.env["ir.actions.actions"]._for_xml_id(
            "stock_unscrapped_report.action_unscrapped_stock_report_line"
        )
        action["domain"] = [("wizard_id", "=", self.id)]
        action["context"] = {
            "search_default_group_location": 1,
            "create": False,
            "edit": False,
            "delete": False,
        }
        return action
