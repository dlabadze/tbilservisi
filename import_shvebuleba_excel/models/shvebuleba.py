from odoo import _, api, fields, models


class Shvebuleba(models.Model):
    _inherit = "shvebuleba"

    imported_daricshve = fields.Float(string="Imported Daricshve", default=0.0)
    daricshve = fields.Float(
        string="დარიცხული შვებულება",
        compute="_compute_daricshve",
        inverse="_inverse_daricshve",
        store=True,
        readonly=False,
    )

    def action_open_excel_import_wizard(self):
        return {
            "type": "ir.actions.act_window",
            "name": _("Shvebuleba Excel Import"),
            "res_model": "shvebuleba.excel.import.wizard",
            "view_mode": "form",
            "target": "new",
        }

    @api.depends("shvebuleba_line_ids.line_total", "imported_daricshve")
    def _compute_daricshve(self):
        super()._compute_daricshve()
        for rec in self:
            if not rec.shvebuleba_line_ids:
                rec.daricshve = rec.imported_daricshve or 0.0

    def _inverse_daricshve(self):
        for rec in self:
            rec.imported_daricshve = rec.daricshve or 0.0
