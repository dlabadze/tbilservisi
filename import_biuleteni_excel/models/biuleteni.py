from odoo import _, api, fields, models


class Biuleteni(models.Model):
    _inherit = "biuleteni"

    imported_total_amount = fields.Float(string="Imported Total Amount", default=0.0)
    total_amount = fields.Float(
        string="სულ დასარიცხი თანხა",
        compute="_compute_totals",
        inverse="_inverse_total_amount",
        store=True,
        readonly=False,
    )

    def action_open_excel_import_wizard(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Biuleteni Excel Import"),
            "res_model": "biuleteni.excel.import.wizard",
            "view_mode": "form",
            "target": "new",
        }

    @api.depends("biuleteni_line_ids", "biuleteni_line_ids.missed_days", "biuleteni_line_ids.line_total", "imported_total_amount")
    def _compute_totals(self):
        super()._compute_totals()
        for rec in self:
            # Keep imported amount when there are no detail lines;
            # if lines exist, normal compute result stays.
            if not rec.biuleteni_line_ids:
                rec.total_amount = rec.imported_total_amount or 0.0

    def _inverse_total_amount(self):
        for rec in self:
            rec.imported_total_amount = rec.total_amount or 0.0
