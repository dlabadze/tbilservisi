import base64
import io
from datetime import datetime

import pandas as pd

from odoo import _, fields, models
from odoo.exceptions import UserError


class TseriliExcelImportWizard(models.TransientModel):
    _name = "tserili.excel.import.wizard"
    _description = "Tserili Excel Import Wizard"

    excel_field = fields.Binary(string="Excel File", required=True)
    filename = fields.Char(string="Filename")

    def action_import_excel(self):
        self.ensure_one()
        if not self.excel_field:
            raise UserError(_("Please upload an Excel file."))

        file_content = base64.b64decode(self.excel_field)
        try:
            dataframe = pd.read_excel(
                io.BytesIO(file_content),
                dtype=str,
                header=0,
                engine="openpyxl",
            )
        except Exception as exc:
            raise UserError(_("Excel file could not be read: %s") % exc) from exc

        dataframe.columns = [str(column).strip() for column in dataframe.columns]
        required_columns = ["თარიღი", "თანამშრომელი", "თანხა +", "თანხა -"]
        missing_columns = [column for column in required_columns if column not in dataframe.columns]
        if missing_columns:
            raise UserError(_("Missing required column(s): %s") % ", ".join(missing_columns))

        employee_model = self.env["hr.employee"]
        tserili_model = self.env["tserili"]
        created_count = 0
        missing_rows = []

        for row_index, row in dataframe.iterrows():
            date_value = self._parse_day_month_year(row.get("თარიღი"))
            personal_number = self._clean_string_before_dot(row.get("თანამშრომელი"))
            amount_plus = self._to_safe_float(row.get("თანხა +"))
            amount_minus = self._to_safe_float(row.get("თანხა -"))

            employee = employee_model.search([("identification_id", "=", personal_number)], limit=1)
            if not employee:
                missing_rows.append({
                    "row_number": int(row_index) + 2,
                    "identification_id": personal_number or "",
                    "date": date_value or "",
                    "reason": _("Employee not found by identification_id"),
                })
                continue

            tserili_model.create({
                "date": date_value,
                "employee_id": employee.id,
                "parent_department_id": employee.department_id.parent_id.id or False,
                "department_id": employee.department_id.id or False,
                "amount_plus": amount_plus,
                "amount_minus": amount_minus,
                "state": "validated",
            })
            created_count += 1

        row_count = len(dataframe.index)
        message = _("Created: %s / %s") % (created_count, row_count)

        if missing_rows:
            message += _("\nMissing rows: %s") % len(missing_rows)
            attachment = self.env["ir.attachment"].create({
                "name": "tserili_missing_rows.xlsx",
                "type": "binary",
                "datas": self._build_missing_excel(missing_rows),
                "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "res_model": self._name,
                "res_id": self.id,
            })
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Import Complete"),
                    "message": message,
                    "type": "warning",
                    "sticky": True,
                    "next": {
                        "type": "ir.actions.act_url",
                        "url": "/web/content/%s?download=true" % attachment.id,
                        "target": "self",
                    },
                },
            }

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Import Complete"),
                "message": message,
                "type": "success",
                "sticky": False,
            },
        }

    @staticmethod
    def _clean_string_before_dot(value):
        value_str = str(value or "").strip()
        if not value_str or value_str.lower() == "nan":
            return ""
        return value_str.split(".", 1)[0]

    @staticmethod
    def _parse_day_month_year(value):
        value_str = str(value or "").strip()
        if not value_str or value_str.lower() == "nan":
            return False
        for pattern in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(value_str, pattern).strftime("%Y-%m-%d")
            except ValueError:
                continue
        raise UserError(_("Invalid date format: %s. Expected day-month-year.") % value_str)

    @staticmethod
    def _to_safe_float(value):
        value_str = str(value or "").strip()
        if not value_str or value_str.lower() == "nan":
            return 0.0
        value_str = value_str.replace(",", ".")
        try:
            return float(value_str)
        except ValueError:
            return 0.0

    @staticmethod
    def _build_missing_excel(missing_rows):
        missing_df = pd.DataFrame(
            missing_rows,
            columns=["row_number", "identification_id", "date", "reason"],
        )
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            missing_df.to_excel(writer, index=False)
        output.seek(0)
        return base64.b64encode(output.read())
