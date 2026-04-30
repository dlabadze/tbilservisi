# -*- coding: utf-8 -*-
import base64
import io

import pandas as pd

from odoo import fields, models, _
from odoo.exceptions import UserError


class EmployeeFieldsUpdateWizard(models.TransientModel):
    _name = 'employee.fields.update.wizard'
    _description = 'Employee Fields Update Wizard'

    excel_file = fields.Binary(string='Excel File', required=True)
    filename = fields.Char(string='Filename')
    missed_file = fields.Binary(string='Missed Excel', readonly=True)
    missed_filename = fields.Char(string='Missed Filename', readonly=True)
    result_message = fields.Text(string='Result', readonly=True)

    def action_confirm(self):
        self.ensure_one()
        if not self.excel_file:
            raise UserError(_('Please upload an Excel file.'))

        file_data = base64.b64decode(self.excel_file)
        try:
            dataframe = pd.read_excel(io.BytesIO(file_data), dtype=str, engine='openpyxl')
        except Exception as exc:
            raise UserError(_('Excel file could not be read: %s') % exc) from exc

        dataframe.columns = [str(col).strip() for col in dataframe.columns]
        required_columns = [
            'პირადი ნომერი',
            'ქველმოქმედება',
            'სოლიდარობის ფონდი',
            'პროფკავშირი',
            'პროფკავშირი მერია',
            'აღსრულება %',
            'აღსრულება',
            'ალიმენტი',
            'ალიმენტი %',
        ]
        missing_columns = [col for col in required_columns if col not in dataframe.columns]
        if missing_columns:
            raise UserError(
                _('Missing required column(s): %s') % ', '.join(missing_columns)
            )

        field_map = {
            'ქველმოქმედება': 'x_studio_charity',
            'სოლიდარობის ფონდი': 'x_studio_fondi_solidaroba',
            'პროფკავშირი': 'x_studio_profkav',
            'პროფკავშირი მერია': 'x_studio_profm',
            'აღსრულება %': 'x_studio_agsrulebaper',
            'აღსრულება': 'x_studio_agsruleba',
            'ალიმენტი': 'x_studio_alimenti',
            'ალიმენტი %': 'x_studio_alimentiper',
        }

        updated_count = 0
        missed_rows = []
        employee_model = self.env['hr.employee']

        for _row_index, row in dataframe.iterrows():
            personal_number = self._normalize_identification(row.get('პირადი ნომერი'))
            if not personal_number:
                continue

            employee = employee_model.search(
                [('identification_id', '=', personal_number)],
                limit=1
            )
            if not employee:
                missed_rows.append({
                    'პირადი ნომერი': personal_number,
                    'შეცდომა': 'თანამშრომლის მოძებნა ვერ მოხერხდა',
                })
                continue

            vals = {}
            for excel_col, field_name in field_map.items():
                vals[field_name] = self._to_float(row.get(excel_col))
            employee.write(vals)
            updated_count += 1

        result = _('განახლდა თანამშრომლების ჩანაწერები: %s') % updated_count
        if missed_rows:
            result_message = result + '\n' + _('ვერ მოიძებნა თანამშრომელი: %s') % len(missed_rows)
            missed_binary = self._build_missed_excel(missed_rows)
            self.write({
                'missed_file': missed_binary,
                'missed_filename': 'missed_employees.xlsx',
                'result_message': result_message,
            })
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Import Complete'),
                    'message': result_message,
                    'type': 'warning',
                    'sticky': True,
                    'next': {
                        'type': 'ir.actions.act_url',
                        'url': '/web/content?model=%s&id=%s&field=missed_file&filename_field=missed_filename&download=true' % (
                            self._name, self.id
                        ),
                        'target': 'self',
                    },
                }
            }
        else:
            result_message = result + '\n' + _('ვერ მოიძებნა თანამშრომელი: 0')
            self.write({
                'missed_file': False,
                'missed_filename': False,
                'result_message': result_message,
            })
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Import Complete'),
                    'message': result_message,
                    'type': 'success',
                    'sticky': False,
                }
            }

    def _reopen_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('თანამშრომლის ველების განახლება'),
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    @staticmethod
    def _normalize_identification(value):
        value_str = str(value or '').strip()
        if not value_str or value_str.lower() == 'nan':
            return ''
        if '.' in value_str:
            value_str = value_str.split('.')[0]
        return value_str

    @staticmethod
    def _to_float(value):
        value_str = str(value or '').strip()
        if not value_str or value_str.lower() == 'nan':
            return 0.0
        value_str = value_str.replace(' ', '').replace(',', '.')
        try:
            return float(value_str)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _build_missed_excel(missed_rows):
        missed_df = pd.DataFrame(missed_rows, columns=['პირადი ნომერი', 'შეცდომა'])
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            missed_df.to_excel(writer, index=False)
        output.seek(0)
        return base64.b64encode(output.read())
