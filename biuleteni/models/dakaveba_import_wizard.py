import base64
import pandas as pd
import io
import logging


from odoo import models, fields
from odoo.exceptions import UserError
from odoo.tools import html_escape

_logger = logging.getLogger(__name__)


class DakavebaImportWizard(models.TransientModel):
    _name = 'dakaveba.import.wizard'
    _description = 'Dakaveba Excel Import Wizard'

    # ---------------------------------------------------------
    # WIZARD FIELDS
    # ---------------------------------------------------------
    file_data = fields.Binary("Excel ფაილი", required=True)
    file_name = fields.Char("ფაილის სახელი")
    date = fields.Date(string="თარიღი", required=True, default=fields.Date.context_today)
    department_id = fields.Many2one("hr.department", string="დეპარტამენტი", required=True)
    dakaveba_type = fields.Selection(
        [
            ('zeganakveturi', 'ზეგანაკვეთური'),
            ('jarima', 'ჯარიმა'),
            ('disciplinaruli_jarima', 'დისციპლინარული ჯარიმა'),
            ('sxva', 'სხვა დანარჩენი'),
        ],
        string="ტიპი",
        required=True,
        default='zeganakveturi',
    )
    comment = fields.Char(string="კომენტარი")

    start_row = fields.Integer(string="საწყისი სტრიქონი", default=1)
    end_row = fields.Integer(string="ბოლო სტრიქონი")

    # ---------------------------------------------------------
    # MAIN IMPORT
    # ---------------------------------------------------------
    def action_import(self):
        try:
            _logger.info("🚀 Starting Dakaveba Import")

            # Parse Excel
            data_rows = self._parse_excel()
            _logger.info(f"📊 Parsed {len(data_rows)} rows")

            # Create dakaveba + lines
            main_record, result_msg = self._import_lines(data_rows)

            # Log message in chatter
            main_record.message_post(
                body=html_escape(result_msg),
                subtype_xmlid='mail.mt_note'
            )

            # Open created record
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'dakaveba',
                'view_mode': 'form',
                'res_id': main_record.id,
                'target': 'current',
            }

        except Exception as e:
            _logger.error("❌ Dakaveba import error", exc_info=True)
            raise UserError(f"დაფიქსირდა შეცდომა: {str(e)}")

    # ---------------------------------------------------------
    # PROCESS LINES & CREATE MAIN RECORD
    # ---------------------------------------------------------
    def _import_lines(self, data_rows):

        # Georgian month names
        ge_months = {
            1: "იანვარი", 2: "თებერვალი", 3: "მარტი", 4: "აპრილი",
            5: "მაისი", 6: "ივნისი", 7: "ივლისი", 8: "აგვისტო",
            9: "სექტემბერი", 10: "ოქტომბერი", 11: "ნოემბერი", 12: "დეკემბერი",
        }
        month_name = ge_months[self.date.month]

        # Auto name: დაკავება + <type label> + Month + Year
        type_label = dict(self._fields['dakaveba_type'].selection).get(self.dakaveba_type, '')
        auto_name = f"დაკავება {type_label} {month_name} {self.date.year}".strip()

        # Create parent record
        main = self.env['dakaveba'].create({
            'name': auto_name,
            'date': self.date,
            'department_id': self.department_id.id,
            'dakaveba_type': self.dakaveba_type,
            'comment': self.comment or '',
            'state': 'draft',
        })

        created = 0
        skipped = []

        # Loop through cleaned rows
        for excel_row_num, row in data_rows:
            try:
                # Column 2 = identification (index 1)
                personal_number = str(row[1]).strip() if len(row) > 1 else ""

                # Column 10 = amount (index 9)
                amount = self._to_float(row[9]) if len(row) > 9 else 0.0

                if not personal_number or personal_number.lower() == "nan":
                    continue

                # Find employee
                employee = self.env['hr.employee'].search([
                    ('identification_id', '=', personal_number)
                ], limit=1)

                if not employee:
                    skipped.append(f"სტრიქონი {excel_row_num}: {personal_number}")
                    continue

                # Create line
                self.env['dakaveba.det'].create({
                    'dakaveba_id': main.id,
                    'employee_id': employee.id,
                    'amount': amount,
                })

                created += 1

            except Exception as err:
                _logger.error(f"❌ Row {excel_row_num} failed: {err}")

        if created == 0:
            raise UserError("ვერცერთი ჩანაწერი ვერ ჩაიტვირთა. გადაამოწმეთ Excel ფაილი.")

        # Build result message
        msg = f"ჩაიტვირთა {created} ჩანაწერი"
        if skipped:
            msg += f"\nგამოტოვა {len(skipped)} ჩანაწერი:\n" + "\n".join(skipped[:20])
            if len(skipped) > 20:
                msg += "\n..."

        return main, msg

    # ---------------------------------------------------------
    # PARSE EXCEL (NO AUTOSKIP)
    # ---------------------------------------------------------
    def _parse_excel(self):
        if not self.file_data:
            raise UserError("გთხოვთ აირჩიოთ Excel ფაილი.")

        data = base64.b64decode(self.file_data)

        # No skiprows, no header removal, nothing Removed!
        df = pd.read_excel(io.BytesIO(data), header=None, dtype=str, engine="openpyxl")

        # Apply selected row range
        start = max((self.start_row or 1) - 1, 0)
        end = self.end_row if self.end_row else None
        df = df.iloc[start:end]

        clean = []

        for idx, row in df.iterrows():
            row_list = row.tolist()
            clean.append((idx + 1, row_list))  # excel row number = idx+1

        if not clean:
            raise UserError("მითითებულ სტრიქონებში მონაცემი ვერ მოიძებნა.")

        return clean

    # ---------------------------------------------------------
    # SAFE FLOAT PARSER
    # ---------------------------------------------------------
    def _to_float(self, val):
        try:
            return float(str(val).replace(",", "."))
        except:
            return 0.0
