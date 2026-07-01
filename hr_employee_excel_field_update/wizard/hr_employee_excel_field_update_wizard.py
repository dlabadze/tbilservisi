# -*- coding: utf-8 -*-
import base64
import io
import logging
from datetime import date, datetime

import pandas as pd

from odoo import fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

IDENTIFICATION_FIELD = 'identification_id'
HEADER_ROW_INDEX = 0
DATA_START_ROW_INDEX = 2

# Optional many2one lookup field per employee field (Studio/custom models).
MANY2ONE_LOOKUP_FIELDS = {
    'x_studio_location': 'x_locaiton',
    'x_studio_country': 'x_county',
}


class HrEmployeeExcelFieldUpdateWizard(models.TransientModel):
    _name = 'hr.employee.excel.field.update.wizard'
    _description = 'HR Employee Excel Field Update Wizard'

    excel_file = fields.Binary(string='Excel File', required=True)
    filename = fields.Char(string='Filename')
    missed_file = fields.Binary(string='Missed Rows', readonly=True)
    missed_filename = fields.Char(string='Missed Filename', readonly=True)
    result_message = fields.Text(string='Result', readonly=True)

    def action_import_excel(self):
        self.ensure_one()
        if not self.excel_file:
            raise UserError(_('Please upload an Excel file.'))

        try:
            dataframe = pd.read_excel(
                io.BytesIO(base64.b64decode(self.excel_file)),
                header=None,
                dtype=object,
                engine='openpyxl',
            )
        except Exception as exc:
            raise UserError(_('Excel file could not be read: %s') % exc) from exc

        if dataframe.shape[0] < DATA_START_ROW_INDEX + 1:
            raise UserError(_('Excel file must contain a header row, label row, and at least one data row.'))

        field_names = self._parse_header_row(dataframe.iloc[HEADER_ROW_INDEX])
        if IDENTIFICATION_FIELD not in field_names:
            raise UserError(
                _('Column "%(field)s" is required in the first row (technical field names).')
                % {'field': IDENTIFICATION_FIELD}
            )

        employee_model = self.env['hr.employee']
        updated_count = 0
        skipped_count = 0
        missed_rows = []

        for row_index in range(DATA_START_ROW_INDEX, len(dataframe)):
            row = dataframe.iloc[row_index]
            identification_id = self._normalize_identification(
                row.iloc[field_names.index(IDENTIFICATION_FIELD)]
            )
            if not identification_id:
                skipped_count += 1
                continue

            employee = employee_model.with_context(active_test=False).search(
                [('identification_id', '=', identification_id)],
                limit=1,
            )
            if not employee:
                missed_rows.append({
                    'identification_id': identification_id,
                    'error': _('Employee not found'),
                })
                skipped_count += 1
                continue

            vals = {}
            for col_index, field_name in enumerate(field_names):
                if not field_name or field_name == IDENTIFICATION_FIELD:
                    continue
                if field_name not in employee_model._fields:
                    _logger.warning(
                        'Skipping unknown hr.employee field "%s" at column %s',
                        field_name,
                        col_index + 1,
                    )
                    continue

                raw_value = row.iloc[col_index]
                if self._is_empty(raw_value):
                    continue

                try:
                    converted = self._convert_value(
                        employee_model,
                        field_name,
                        raw_value,
                    )
                except UserError as exc:
                    missed_rows.append({
                        'identification_id': identification_id,
                        'error': '%s: %s' % (field_name, exc.args[0]),
                    })
                    vals = None
                    break

                if converted is not False and converted is not None:
                    vals[field_name] = converted

            if vals is None:
                skipped_count += 1
                continue
            if not vals:
                skipped_count += 1
                continue

            employee.write(vals)
            updated_count += 1

        message = _('Updated employees: %s') % updated_count
        if skipped_count:
            message += '\n' + _('Skipped rows: %s') % skipped_count

        write_vals = {'result_message': message}
        if missed_rows:
            write_vals.update({
                'missed_file': self._build_missed_excel(missed_rows),
                'missed_filename': 'missed_employee_updates.xlsx',
            })
        else:
            write_vals.update({
                'missed_file': False,
                'missed_filename': False,
            })
        self.write(write_vals)

        notification_type = 'warning' if missed_rows else 'success'
        params = {
            'title': _('Import Complete'),
            'message': message,
            'type': notification_type,
            'sticky': bool(missed_rows),
        }
        if missed_rows:
            params['next'] = {
                'type': 'ir.actions.act_url',
                'url': (
                    '/web/content?model=%s&id=%s&field=missed_file'
                    '&filename_field=missed_filename&download=true'
                ) % (self._name, self.id),
                'target': 'self',
            }

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': params,
        }

    @staticmethod
    def _parse_header_row(header_row):
        field_names = []
        for value in header_row.tolist():
            field_name = str(value or '').strip()
            if field_name.lower() in ('', 'nan', 'none'):
                field_names.append('')
            else:
                field_names.append(field_name)
        return field_names

    @staticmethod
    def _normalize_identification(value):
        value_str = str(value or '').strip()
        if not value_str or value_str.lower() == 'nan':
            return ''
        if '.' in value_str and value_str.replace('.', '', 1).isdigit():
            value_str = value_str.split('.')[0]
        return value_str

    @staticmethod
    def _is_empty(value):
        if value is None:
            return True
        if isinstance(value, float) and pd.isna(value):
            return True
        value_str = str(value).strip()
        return not value_str or value_str.lower() == 'nan'

    def _convert_value(self, employee_model, field_name, value):
        field = employee_model._fields[field_name]
        if field.type == 'char' or field.type == 'text':
            return str(value).strip()
        if field.type == 'integer':
            return int(float(str(value).replace(',', '.').strip()))
        if field.type == 'float' or field.type == 'monetary':
            return float(str(value).replace(' ', '').replace(',', '.').strip())
        if field.type == 'boolean':
            return str(value).strip().lower() in ('1', 'true', 'yes', 'y', 'დიახ')
        if field.type == 'date':
            return self._convert_date(value)
        if field.type == 'datetime':
            return self._convert_datetime(value)
        if field.type == 'selection':
            return self._convert_selection(employee_model, field_name, value)
        if field.type == 'many2one':
            return self._convert_many2one(employee_model, field_name, value)
        raise UserError(_('Unsupported field type "%s" for field "%s".') % (field.type, field_name))

    @staticmethod
    def _convert_date(value):
        if isinstance(value, datetime):
            return value.date().strftime('%Y-%m-%d')
        if isinstance(value, date):
            return value.strftime('%Y-%m-%d')
        value_str = str(value).strip()
        if 'T' in value_str:
            value_str = value_str.split('T', 1)[0]
        for pattern in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y'):
            try:
                return datetime.strptime(value_str, pattern).strftime('%Y-%m-%d')
            except ValueError:
                continue
        raise UserError(_('Invalid date: %s') % value)

    @staticmethod
    def _convert_datetime(value):
        if isinstance(value, datetime):
            return value.strftime('%Y-%m-%d %H:%M:%S')
        if isinstance(value, date):
            return datetime.combine(value, datetime.min.time()).strftime('%Y-%m-%d %H:%M:%S')
        value_str = str(value).strip().replace('T', ' ')
        for pattern in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%d.%m.%Y'):
            try:
                parsed = datetime.strptime(value_str, pattern)
                return parsed.strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                continue
        raise UserError(_('Invalid datetime: %s') % value)

    def _convert_selection(self, employee_model, field_name, value):
        field = employee_model._fields[field_name]
        value_str = str(value).strip()
        selection_values = field.selection
        if callable(selection_values):
            selection_values = selection_values(employee_model)
        elif isinstance(selection_values, str):
            selection_values = getattr(employee_model, selection_values)()

        normalized_input = value_str.lower()
        for key, label in selection_values or []:
            label_text = label
            if isinstance(label, dict):
                label_text = label.get(self.env.lang) or next(iter(label.values()), '')
            if normalized_input == str(key).strip().lower():
                return key
            if normalized_input == str(label_text).strip().lower():
                return key
        raise UserError(_('Invalid selection value: %s') % value_str)

    def _convert_many2one(self, employee_model, field_name, value):
        field = employee_model._fields[field_name]
        relation_model = self.env[field.comodel_name]
        value_str = str(value).strip()
        lookup_field = MANY2ONE_LOOKUP_FIELDS.get(field_name, 'name')
        if lookup_field not in relation_model._fields:
            for candidate in ('name', 'x_name', 'display_name'):
                if candidate in relation_model._fields:
                    lookup_field = candidate
                    break
            else:
                raise UserError(_('Cannot resolve many2one lookup for %s') % field_name)

        record = relation_model.search([(lookup_field, '=', value_str)], limit=1)
        if not record and lookup_field != 'name' and 'name' in relation_model._fields:
            record = relation_model.search([('name', '=', value_str)], limit=1)
        if not record:
            raise UserError(_('Record not found: %s') % value_str)
        return record.id

    @staticmethod
    def _build_missed_excel(missed_rows):
        missed_df = pd.DataFrame(missed_rows, columns=['identification_id', 'error'])
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            missed_df.to_excel(writer, index=False)
        output.seek(0)
        return base64.b64encode(output.read())
