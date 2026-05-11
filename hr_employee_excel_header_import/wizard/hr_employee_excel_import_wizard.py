import base64
import io
from datetime import datetime

import pandas as pd

from odoo import fields, models, _
from odoo.exceptions import UserError


import logging
_logger = logging.getLogger(__name__)

# Format:
# (excel_column, hr_employee_field, value_type, required_flag[, many2one_lookup_field])
# required_flag: "always" | "non_always"
EXCEL_TO_ODOO_MAPPING = (
    ("პირადი ნომერი", "identification_id", "char", 'always'),
    ("თანამშრომელი", "name", "char", 'always'),
    ("პასპორტის ნომერი", "passport_id", "char", 'always'),
    ("ფაქტიური მისამართი", "private_street", "char", 'always'),
    ("დაბადების თარიღი", "birthday", "date", 'always'),
    ("სქესი", "gender", "selection", 'always'),
    ("კორპორატიული ნომერი", "work_phone", "char", 'always'),
    ("მობილურის ნომერი", "private_phone", "char", 'always'),
    ("ბავშვების რაოდენობა", "children", "int", 'non_always'),
    ("სამხედრო ვალდებულება", "x_studio_militarystatus", "selection", 'non_always'),
    ("დაბადების ადგილი", "x_studio_location", "many2one", "non_always", "x_locaiton"),
    ("ტაბელის კოდი", "x_studio_tabeli", "char", 'non_always'),
    ("მამის სახელი", "x_studio_fathername", "char", 'non_always'),
    ("პირველადი მიღების თარიღი", "x_studio_migdate", "date", 'non_always'),
    ("ეროვნება", "x_studio_country", "many2one", "non_always", "x_county"),
    ("ნასამართლეობა", "x_studio_conviction", "selection", "non_always"),
    ("მოქალაქეობა", "x_studio_citizenship", "selection", "non_always"),
    ("განათლება", "x_studio_education", "selection", "non_always"),
    ("შტატი", "x_studio_shtati", "selection", "non_always"),
    ("ოჯახური მდგომარება", "x_studio_marital", "selection", "non_always"),
)


class HrEmployeeExcelImportWizard(models.TransientModel):
    _name = "hr.employee.excel.import.wizard"
    _description = "HR Employee Excel Import Wizard"

    excel_file = fields.Binary(string="Excel File", required=True)
    filename = fields.Char(string="Filename")

    def action_import_excel(self):
        self.ensure_one()
        if not self.excel_file:
            raise UserError(_("Please upload an Excel file."))
        if not EXCEL_TO_ODOO_MAPPING:
            raise UserError(_("Please fill EXCEL_TO_ODOO_MAPPING in python file first."))

        file_content = base64.b64decode(self.excel_file)
        try:
            # Excel header must be first row.
            dataframe = pd.read_excel(io.BytesIO(file_content), dtype=str, header=0, engine="openpyxl")
        except Exception as exc:
            raise UserError(_("Excel file could not be read: %s") % exc) from exc

        dataframe.columns = [str(col).strip() for col in dataframe.columns]

        parsed_mapping = self._parse_mapping()
        required_columns = [item["excel_column"] for item in parsed_mapping if item["required_flag"] == "always"]
        missing_columns = [column for column in required_columns if column not in dataframe.columns]
        if missing_columns:
            raise UserError(_("Missing required column(s): %s") % ", ".join(missing_columns))

        employee_model = self.env["hr.employee"]
        identification_column = "პირადი ნომერი"
        name_column = "თანამშრომელი"
        created_count = 0
        skipped_count = 0
        missed_rows = []

        for _row_index, row in dataframe.iterrows():
            identification_id = self._to_str(row.get(identification_column))
            employee_name = self._to_str(row.get(name_column))

            if not identification_id:
                skipped_count += 1
                missed_rows.append(self._build_missed_row(identification_id, employee_name))
                continue

            existing_employee = employee_model.search([("identification_id", "=", identification_id)], limit=1)
            if existing_employee:
                skipped_count += 1
                missed_rows.append(self._build_missed_row(identification_id, employee_name))
                continue

            values = {}
            for item in parsed_mapping:
                excel_column = item["excel_column"]
                if excel_column not in dataframe.columns:
                    continue
                field_name = item["field_name"]
                field_type = item["field_type"]
                related_lookup = item.get("related_lookup")
                raw_value = row.get(excel_column)
                values[field_name] = self._convert_value(employee_model, field_name, raw_value, field_type, related_lookup)

            partner = self.env["res.partner"].search([("vat", "=", identification_id)], limit=1)
            if not partner:
                partner = self.env["res.partner"].create({
                    "name": employee_name or identification_id,
                    "vat": identification_id,
                })
            values["work_contact_id"] = partner.id

            try:
                employee_model.create(values)
                created_count += 1
            except Exception as exc:
                _logger.error(f"Error creating employee:{exc}")
                skipped_count += 1
                missed_rows.append(self._build_missed_row(identification_id, employee_name))

        message = _("Created employees: %s") % created_count
        if skipped_count:
            message += _("\nMissed rows: %s") % skipped_count

        if missed_rows:
            missed_binary = self._build_missed_excel(missed_rows)
            attachment = self.env["ir.attachment"].create({
                "name": "missed_rows.xlsx",
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

    def _parse_mapping(self):
        parsed = []
        for entry in EXCEL_TO_ODOO_MAPPING:
            if len(entry) < 4:
                raise UserError(_("Each mapping entry must contain at least 4 values."))
            excel_column, field_name, field_type, required_flag = entry[:4]
            related_lookup = entry[4] if len(entry) > 4 else None
            parsed.append({
                "excel_column": excel_column,
                "field_name": field_name,
                "field_type": field_type,
                "required_flag": required_flag,
                "related_lookup": related_lookup,
            })
        return parsed

    @staticmethod
    def _to_str(value):
        value_str = str(value or "").strip()
        if not value_str or value_str.lower() == "nan":
            return ""
        if "." in value_str and value_str.replace(".", "", 1).isdigit():
            value_str = value_str.split(".")[0]
        return value_str

    def _convert_value(self, employee_model, field_name, value, field_type, related_lookup=None):
        value_str = self._to_str(value)
        if not value_str:
            return "" if field_type == "char" else False

        if field_type == "float":
            try:
                return float(value_str.replace(",", "."))
            except ValueError:
                return 0.0
        if field_type == "int":
            try:
                return int(float(value_str.replace(",", ".")))
            except ValueError:
                return 0
        if field_type == "bool":
            return value_str.lower() in ("1", "true", "yes", "y")
        if field_type == "date":
            return self._convert_date(value_str)
        if field_type == "selection":
            return self._convert_selection_from_label(employee_model, field_name, value_str)
        if field_type == "many2one":
            hr_field = employee_model._fields.get(field_name)
            if not hr_field or not getattr(hr_field, "comodel_name", False):
                return False
            relation_model = self.env[hr_field.comodel_name]
            lookup_field = related_lookup or "name"
            if lookup_field not in relation_model._fields:
                if "name" in relation_model._fields:
                    lookup_field = "name"
                elif "x_name" in relation_model._fields:
                    lookup_field = "x_name"
                else:
                    return False
            relation_record = relation_model.search([(lookup_field, "=", value_str)], limit=1)
            return relation_record.id if relation_record else False
        return value_str

    def _convert_selection_from_label(self, employee_model, field_name, value_str):
        field = employee_model._fields.get(field_name)
        if not field or field.type != "selection":
            return value_str

        selection_values = field.selection
        if callable(selection_values):
            selection_values = selection_values(employee_model)
        elif isinstance(selection_values, str):
            selection_values = getattr(employee_model, selection_values)()

        normalized_input = value_str.strip().lower()
        for key, label in selection_values or []:
            if normalized_input == str(key).strip().lower():
                return key
            if normalized_input == str(label).strip().lower():
                return key
        return False

    @staticmethod
    def _convert_date(value_str):
        # Accept day-month-year inputs from Excel and convert to Odoo format.
        for pattern in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(value_str, pattern).strftime("%Y-%m-%d")
            except ValueError:
                continue
        raise UserError(_("Invalid date format: %s. Expected day/month/year.") % value_str)

    @staticmethod
    def _build_missed_row(identification_id, name):
        return {
            "identification_id": identification_id or "",
            "name": name or "",
            "error": "ვერ მოხდა შეტვირთვა",
        }

    @staticmethod
    def _build_missed_excel(missed_rows):
        missed_df = pd.DataFrame(missed_rows, columns=["identification_id", "name", "error"])
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            missed_df.to_excel(writer, index=False)
        output.seek(0)
        return base64.b64encode(output.read())
