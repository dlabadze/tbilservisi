import base64
import io
from datetime import datetime

import pandas as pd

from odoo import _, fields, models
from odoo.exceptions import UserError


class ShvebulebaExcelImportWizard(models.TransientModel):
    _name = "shvebuleba.excel.import.wizard"
    _description = "Shvebuleba Excel Import Wizard"

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
        required_columns = ["პირადობა", "თანხა", "დაწყება", "დასრულება"]
        missing_columns = [column for column in required_columns if column not in dataframe.columns]
        if missing_columns:
            raise UserError(_("Missing required column(s): %s") % ", ".join(missing_columns))

        employee_model = self.env["hr.employee"]
        shvebuleba_model = self.env["shvebuleba"]
        created_count = 0
        missing_rows = []

        for row_index, row in dataframe.iterrows():
            personal_number = self._clean_string_before_dot(row.get("პირადობა"))
            amount = self._to_safe_float(row.get("თანხა"))
            start_date = self._parse_day_month_year(row.get("დაწყება"))
            end_date = self._parse_day_month_year(row.get("დასრულება"))

            employee = employee_model.search([("identification_id", "=", personal_number)], limit=1)
            if not employee:
                missing_rows.append(
                    self._build_missed_row(
                        row_index=row_index,
                        personal_number=personal_number,
                        amount=amount,
                        start_date=start_date,
                        end_date=end_date,
                        reason=_("Employee not found by პირადობა: %s") % personal_number,
                    )
                )
                continue

            shvebuleba_model.create({
                "emp_id": employee.id,
                "daricshve": amount,
                "imported_daricshve": amount,
                "startdate": start_date,
                "end_datee": end_date,
                "state": "validated",
                "validatio": True,
            })
            created_count += 1

        row_count = len(dataframe.index)
        message = _("Created: %s / %s") % (created_count, row_count)
        if missing_rows:
            message += _("\nMissing rows: %s") % len(missing_rows)
            missed_binary = self._build_missed_excel(missing_rows)
            attachment = self.env["ir.attachment"].create({
                "name": "shvebuleba_missing_rows.xlsx",
                "type": "binary",
                "datas": missed_binary,
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
    def _build_missed_row(row_index, personal_number, amount, start_date, end_date, reason):
        return {
            "row_number": int(row_index) + 2,
            "პირადობა": personal_number or "",
            "თანხა": amount or 0.0,
            "დაწყება": start_date or "",
            "დასრულება": end_date or "",
            "reason": reason or "",
        }

    @staticmethod
    def _build_missed_excel(missing_rows):
        missing_df = pd.DataFrame(
            missing_rows,
            columns=["row_number", "პირადობა", "თანხა", "დაწყება", "დასრულება", "reason"],
        )
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            missing_df.to_excel(writer, index=False)
        output.seek(0)
        return base64.b64encode(output.read())
