from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import pandas as pd
import io
import logging
from datetime import datetime
from odoo.tools import html_escape

_logger = logging.getLogger(__name__)


class ZeganakveturiSaati(models.Model):
    _name = 'zeganakveturi_saati'
    _description = 'zeganakveturi_saati'
    _inherit = 'mail.thread'
    _order = 'date desc, id desc'

    # --- States ---
    state = fields.Selection([
        ('draft', 'დრაფტი'),
        ('validated', 'დადასტურებული')
    ], default='draft', string='სტატუსი', tracking=True)


    # --- Type field (NEW) ---
    entry_type = fields.Selection([
        ('premia', 'პრემია'),
        ('zeganakveturi_saati', 'ზეგანაკვეთური საათი'),
        ('zeganakveturi_gamodzaxeba', 'ზეგანაკვეთური გამოძახება'),
        ('danamati', 'დანამატი'),
        ('waxaliseba', 'წახალისება'),
        ('iluminaciebi', 'ილუმინაციები'),
        ('daxmareba', 'დახმარება'),
        ('kompensacia', 'კომპენსაცია'),
    ], string="ტიპი", required=True, default='zeganakveturi_saati')

    # --- Main fields ---
    name = fields.Char(string="დასახელება")
    date = fields.Date(string="თარიღი", required=True, default=fields.Date.context_today)
    comment = fields.Char(string="კომენტარი")

    total_amount = fields.Float(
        string="ასანაზღაურებელი თანხის ჯამი",
        compute="_compute_total_amount",
        store=True
    )

    zeganakveturi_saati_line_ids = fields.One2many(
        'zeganakveturi_saati_det',
        'zeganakveturi_saati_id',
        string='დეტალიზაცია'
    )

    # --- Compute total amount ---
    @api.depends('zeganakveturi_saati_line_ids.amount')
    def _compute_total_amount(self):
        for rec in self:
            rec.total_amount = sum(rec.zeganakveturi_saati_line_ids.mapped('amount'))

    # --- Actions ---
    def action_validate(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError("მხოლოდ დრაფტი ჩანაწერის დადასტურებაა შესაძლებელი.")
            rec.state = 'validated'

    def action_reset_draft(self):
        for rec in self:
            if rec.state != 'validated':
                raise UserError("მხოლოდ validated ჩანაწერის დაბრუნებაა შესაძლებელი draft-ზე.")
            rec.state = 'draft'




class ZeganakveturiImportWizard(models.TransientModel):
    _name = 'zeganakveturi.import.wizard'
    _description = 'excel importing wizard for zeganakveturi_saati'

    file_data = fields.Binary('Excel ფაილი', required=True)
    file_name = fields.Char('ფაილის სახელი')
    date = fields.Date(string='თარიღი', required=True, default=fields.Date.context_today)
    start_row = fields.Integer(string='საწყისი სტრიქონი', default=1)
    end_row = fields.Integer(string='ბოლო სტრიქონი')
    # --- Type field (NEW) ---
    entry_type = fields.Selection([
        ('premia', 'პრემია'),
        ('zeganakveturi_saati', 'ზეგანაკვეთური საათი'),
        ('zeganakveturi_gamodzaxeba', 'ზეგანაკვეთური გამოძახება'),
        ('danamati', 'დანამატი'),
        ('waxaliseba', 'წახალისება'),
        ('iluminaciebi', 'ილუმინაციები'),
        ('daxmareba', 'დახმარება'),
        ('kompensacia', 'კომპენსაცია'),
    ], string="ტიპი", required=True, default='zeganakveturi_saati')
    comment = fields.Char(string='კომენტარი')

    PREMIA_STYLE_TYPES = (
        'premia',
        'danamati',
        'waxaliseba',
        'iluminaciebi',
        'daxmareba',
        'kompensacia',
    )

    def action_import(self):
        try:
            _logger.info("🚀 Starting overtime import")
            data_rows = self._parse_excel_file()
            _logger.info(f"📊 Parsed %s rows from Excel", len(data_rows))

            main_record, result_msg = self._import_overtime_lines(data_rows)

            # ✅ Post message safely (plain text fallback)
            # If your chatter renders <br/> literally, remove .replace('<br/>') below
            msg_html = html_escape(result_msg)

            main_record.message_post(
                body=msg_html,
                message_type='comment',
                subtype_xmlid='mail.mt_note',
            )

            # ✅ Open the created record
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'zeganakveturi_saati',
                'view_mode': 'form',
                'res_id': main_record.id,
                'target': 'current',
                'context': self.env.context,
            }

        except Exception as e:
            _logger.error("❌ Import failed", exc_info=True)
            raise UserError(f"დაფიქსირდა შეცდომა: {str(e)}")

    def _import_overtime_lines(self, data_rows):
        """Reads Excel and imports overtime data (employee, worked_hours, hourly_rate)"""
        main = self.env['zeganakveturi_saati'].create({
            'name': f"{dict(self._fields['entry_type'].selection).get(self.entry_type)} {self.date.strftime('%B %Y')}",
            'date': self.date,
            'entry_type': self.entry_type,
            'comment': self.comment or '',
            'state': 'draft',
        })

        created = 0
        skipped = []

        start_idx = max((self.start_row or 1) - 1, 0)
        skip = 0 if self.entry_type in self.PREMIA_STYLE_TYPES else 6

        # later, in the loop:
        for idx_in_df, row in enumerate(data_rows, start=start_idx + skip + 1):
            try:
                if self.entry_type in self.PREMIA_STYLE_TYPES:
                    emp_raw = row[1] if len(row) > 1 else None
                    amount = self._to_float(row[7]) if len(row) > 7 else 0.0
                    worked_hours = 1
                    hourly_rate = amount
                else:
                    emp_raw = row[3] if len(row) > 3 else None
                    worked_hours = self._to_float(row[35]) if len(row) > 35 else 0.0
                    hourly_rate = self._to_float(row[36]) if len(row) > 36 else 0.0
                    amount = worked_hours * hourly_rate

                if not emp_raw or str(emp_raw).strip().lower() == 'nan':
                    continue

                emp_number = str(emp_raw).strip()

                employee = self.env['hr.employee'].search([
                    ('identification_id', '=', emp_number)
                ], limit=1)

                if not employee:
                    skipped.append(f"სტრიქონი {idx_in_df}: {emp_number}")  # 👈 real Excel row number
                    continue

                self.env['zeganakveturi_saati_det'].create({
                    'zeganakveturi_saati_id': main.id,
                    'employee_id': employee.id,
                    'worked_hours': worked_hours,
                    'hourly_rate': hourly_rate,
                    'amount': amount,
                })
                created += 1

            except Exception as row_err:
                _logger.error(f"❌ Row {idx_in_df} failed: {row_err}")

        if created == 0:
            raise UserError("ვერცერთი ჩანაწერი ვერ ჩაიტვირთა. შეამოწმეთ Excel სვეტი D (პირადი ნომრები)")

        msg = f"ჩაიტვირთა {created} ჩანაწერი"
        if skipped:
            msg += f"\nგამოტოვა {len(skipped)} ჩანაწერი\n\nგამოტოვებული ჩანაწერები:\n" + "\n".join(skipped[:15])
            if len(skipped) > 15:
                msg += "\n..."

        _logger.info(f"✅ Import done: {msg}")

        # 🔹 Show message as popup after opening record
        return main, msg

    def _to_float(self, value):
        try:
            return float(str(value).replace(',', '.'))
        except Exception:
            return 0.0

    def _parse_excel_file(self):
        """Excel reader with preserved leading zeros and row range support"""
        if not self.file_data:
            raise UserError("გთხოვთ აირჩიოთ Excel ფაილი.")

        data = base64.b64decode(self.file_data)

        try:
            # For premia-style types: do NOT skip rows (user defines start_row)
            skip = 0 if self.entry_type in self.PREMIA_STYLE_TYPES else 6

            # dtype=str ensures all data (especially IDs) are read as strings
            df = pd.read_excel(io.BytesIO(data), header=None, dtype=str, skiprows=skip, engine='openpyxl')
        except Exception:
            df = pd.read_excel(io.BytesIO(data), header=None, dtype=str, skiprows=skip)

        # 🔹 Apply user-specified row range
        start_idx = max((self.start_row or 1) - 1, 0)
        end_idx = self.end_row if self.end_row else None
        df = df.iloc[start_idx:end_idx]

        clean_rows = []
        for _, row in df.iterrows():
            row_list = row.tolist()
            if any(str(c).strip() and str(c).lower() != 'nan' for c in row_list):
                clean_rows.append(row_list)

        if not clean_rows:
            raise UserError("ფაილი ცარიელია ან მითითებულ სტრიქონებში მონაცემები ვერ მოიძებნა.")

        return clean_rows
