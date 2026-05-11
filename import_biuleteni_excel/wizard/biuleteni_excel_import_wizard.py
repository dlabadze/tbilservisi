import base64
import io
from datetime import datetime

import pandas as pd

from odoo import _, fields, models
from odoo.exceptions import UserError


class BiuleteniExcelImportWizard(models.TransientModel):
    _name = "biuleteni.excel.import.wizard"
    _description = "Biuleteni Excel Import Wizard"

    excel_field = fields.Binary(string="Excel File", required=True)
    filename = fields.Char(string="Filename")

    def action_import_excel(self):
        self.ensure_one()
        if not self.excel_field:
            raise UserError(_("Please upload an Excel file."))

        file_content = base64.b64decode(self.excel_field)
        try:
            # Header is on the first row in Excel.
            dataframe = pd.read_excel(
                io.BytesIO(file_content),
                dtype=str,
                header=0,
                engine="openpyxl",
            )
        except Exception as exc:
            raise UserError(_("Excel file could not be read: %s") % exc) from exc

        headers = [str(column).strip() for column in dataframe.columns]
        dataframe.columns = headers
        
        required_columns = ["ს/ფ ნომერი", "გახსნა", "დახურვა", "თანხა", "თვე", "პირადობა"]
        missing_columns = [column for column in required_columns if column not in dataframe.columns]
        if missing_columns:
            raise UserError(_("მითითებული ს/ფ ნომერი არ მოიძებნა ბილეტენში: %s") % ", ".join(missing_columns))
        
        employee_model = self.env["hr.employee"]
        biuleteni_model = self.env["biuleteni"]
        month_map = self._get_month_label_to_key_map()
        created_count = 0
        missing_rows = []

        for row_index, row in dataframe.iterrows():
            personal_number = self._clean_string_before_dot(row.get("პირადობა"))
            s_f_number = self._clean_string_before_dot(row.get("ს/ფ ნომერი"))
            open_date = self._parse_day_month_year(row.get("გახსნა"))
            close_date = self._parse_day_month_year(row.get("დახურვა"))
            amount = self._to_safe_float(row.get("თანხა"))
            month = str(row.get("თვე") or "").strip()

            month_selection = month_map.get(month.strip().lower())

            employee = employee_model.search([("identification_id", "=", personal_number)], limit=1)
            if not employee:
                missing_rows.append(
                    self._build_missed_row(
                        personal_number,
                        s_f_number,
                        _("თანამშრომელი ვერ მოიძებნა პირადობით: %s") % personal_number,
                        row_index,
                    )
                )
                continue
            department = employee.department_id.id if employee.department_id else False
            parent_department = employee.department_id.parent_id.id if employee.department_id and employee.department_id.parent_id else False
            biuleteni_model.create({
                "employee_id": employee.id,
                "docnum": s_f_number,
                "date": open_date,
                "date_2": close_date,
                "month_selection": month_selection,
                "total_amount": amount,
                "imported_total_amount": amount,
                "department_id": department,
                "parent_department_id": parent_department,
                "state": "validated",
            })
            created_count += 1

        row_count = len(dataframe.index)
        missed_count = len(missing_rows)
        message = _("Imported: %s / %s") % (created_count, row_count)
        if missed_count:
            message += _("\nMissing rows: %s") % missed_count

        if missing_rows:
            missed_binary = self._build_missed_excel(missing_rows)
            attachment = self.env["ir.attachment"].create({
                "name": "biuleteni_missing_rows.xlsx",
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
        for pattern in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"):
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

    def _get_month_label_to_key_map(self):
        field = self.env["biuleteni"]._fields.get("month_selection")
        selection = field.selection if field else []
        if callable(selection):
            selection = selection(self.env["biuleteni"])
        return {str(label).strip().lower(): key for key, label in (selection or [])}

    @staticmethod
    def _build_missed_row(personal_number, s_f_number, reason, row_index):
        return {
            "row_number": int(row_index) + 2,
            "personal_number": personal_number or "",
            "docnum": s_f_number or "",
            "reason": reason or "",
        }

    @staticmethod
    def _build_missed_excel(missing_rows):
        missed_df = pd.DataFrame(missing_rows, columns=["row_number", "personal_number", "docnum", "reason"])
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            missed_df.to_excel(writer, index=False)
        output.seek(0)
        return base64.b64encode(output.read())
