import base64
import io
from datetime import datetime

import pandas as pd

from odoo import _, fields, models
from odoo.exceptions import UserError

LEAVE_TYPE_NAME = "შვებულება პირადი"


class LeaveAllocationImportWizard(models.TransientModel):
    _name = "leave.allocation.import.wizard"
    _description = "Leave Allocation Excel Import Wizard"

    excel_field = fields.Binary(string="Excel File", required=True)
    filename = fields.Char(string="Filename")

    def action_generate(self):
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
        required_columns = ["თარიღი", "პირადინომ", "თანამშრომელი", "დღეები"]
        missing_columns = [column for column in required_columns if column not in dataframe.columns]
        if missing_columns:
            raise UserError(
                _("Missing required column(s): %s.\nColumns found in file: %s")
                % (", ".join(missing_columns), ", ".join(dataframe.columns))
            )

        employee_model = self.env["hr.employee"].sudo()
        allocation_model = self.env["hr.leave.allocation"].sudo()

        holiday_status = self.env["hr.leave.type"].sudo().search([("name", "=", LEAVE_TYPE_NAME)], limit=1)
        if not holiday_status:
            raise UserError(_("Time Off Type '%s' not found.") % LEAVE_TYPE_NAME)

        created_count = 0
        missing_rows = []
        created_allocations = allocation_model.browse()

        for row_index, row in dataframe.iterrows():
            date_from = self._parse_day_month_year(row.get("თარიღი"))
            personal_number = self._clean_string_before_dot(row.get("პირადინომ"))
            employee_name = str(row.get("თანამშრომელი") or "").strip()
            days = self._to_safe_float(row.get("დღეები"))

            employee = employee_model.search([("identification_id", "=", personal_number)], limit=1)
            if not employee:
                missing_rows.append(
                    self._build_missed_row(
                        row_index=row_index,
                        date_from=date_from,
                        personal_number=personal_number,
                        employee_name=employee_name,
                        days=days,
                        reason=_("Employee not found by პირადინომ: %s") % personal_number,
                    )
                )
                continue

            allocation = allocation_model.create({
                "employee_id": employee.id,
                "number_of_days": days,
                "date_from": date_from,
                "holiday_status_id": holiday_status.id,
                "allocation_type": "accrual",
            })
            created_allocations |= allocation
            created_count += 1

        if created_allocations:
            created_allocations.action_approve()

        row_count = len(dataframe.index)
        message = _("Created: %s / %s") % (created_count, row_count)
        if missing_rows:
            message += _("\nMissing rows: %s") % len(missing_rows)
            missed_binary = self._build_missed_excel(missing_rows)
            attachment = self.env["ir.attachment"].sudo().create({
                "name": "leave_allocation_missing_rows.xlsx",
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

    def _clean_string_before_dot(self, value):
        value_str = str(value or "").strip()
        if not value_str or value_str.lower() == "nan":
            return ""
        return value_str.split(".", 1)[0]

    def _parse_day_month_year(self, value):
        value_str = str(value or "").strip()
        if not value_str or value_str.lower() == "nan":
            return False
        for pattern in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(value_str, pattern).strftime("%Y-%m-%d")
            except ValueError:
                continue
        raise UserError(_("Invalid date format: %s. Expected dd/mm/yyyy.") % value_str)

    def _to_safe_float(self, value):
        value_str = str(value or "").strip()
        if not value_str or value_str.lower() == "nan":
            return 0.0
        value_str = value_str.replace(",", ".")
        try:
            return float(value_str)
        except ValueError:
            return 0.0

    def _build_missed_row(self, row_index, date_from, personal_number, employee_name, days, reason):
        return {
            "row_number": int(row_index) + 2,
            "თარიღი": date_from or "",
            "პირადინომ": personal_number or "",
            "თანამშრომელი": employee_name or "",
            "დღეები": days or 0.0,
            "reason": reason or "",
        }

    def _build_missed_excel(self, missing_rows):
        missing_df = pd.DataFrame(
            missing_rows,
            columns=["row_number", "თარიღი", "პირადინომ", "თანამშრომელი", "დღეები", "reason"],
        )
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            missing_df.to_excel(writer, index=False)
        output.seek(0)
        return base64.b64encode(output.read())
