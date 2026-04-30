import logging

from odoo import models
from odoo.tools import SQL

_logger = logging.getLogger(__name__)


class PartnerLedgerCustomHandler(models.AbstractModel):
    _inherit = "account.partner.ledger.report.handler"

    def _get_additional_column_aml_values(self):
        """Add a NULL placeholder so the base handler finds 'partner_vat' in the
        SQL result dict and renders an empty cell for every move line."""
        _logger.info(
            "[partner_ledger_extension] _get_additional_column_aml_values called -> adding partner_vat to SQL"
        )
        return SQL("NULL AS partner_vat,")

    def _get_report_line_partners(self, options, partner, partner_values, level_shift=0):
        """Show the partner VAT in the Partner VAT column on grouped partner
        header lines only. Move lines show an empty cell automatically."""
        line = super()._get_report_line_partners(
            options, partner, partner_values, level_shift=level_shift
        )

        expr_labels = [c.get("expression_label") for c in options.get("columns", [])]
        _logger.info(
            "[partner_ledger_extension] _get_report_line_partners partner=%s vat=%s columns=%s",
            partner.name if partner else None,
            (partner.vat or "") if partner else "",
            expr_labels,
        )

        if partner and line.get("columns"):
            vat = partner.vat or ""
            for idx, col in enumerate(options["columns"]):
                if col["expression_label"] == "partner_vat" and idx < len(line["columns"]):
                    line["columns"][idx] = {"name": vat, "no_format": vat}
                    _logger.info(
                        "[partner_ledger_extension] set partner_vat at idx=%s for partner=%s",
                        idx,
                        partner.name,
                    )
                    break
            else:
                _logger.warning(
                    "[partner_ledger_extension] partner_vat column NOT FOUND in options['columns']"
                )

        return line
