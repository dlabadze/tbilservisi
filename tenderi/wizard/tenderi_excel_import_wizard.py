# -*- coding: utf-8 -*-
import base64
from io import BytesIO
from datetime import datetime

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class TenderiExcelImportWizard(models.TransientModel):
    _name = 'tenderi.excel.import.wizard'
    _description = 'Tenderi Excel Import Wizard'

    excel_file = fields.Binary(string='Excel File', required=True)
    filename = fields.Char(string='Filename')

    def _parse_date(self, value, datemode=0):
        """Parse date from Excel cell (support datetime, xlrd serial, string)."""
        if value is None or value == '':
            return False
        if hasattr(value, 'date'):
            return value.date() if hasattr(value, 'date') else value
        if isinstance(value, (int, float)) and datemode is not None:
            try:
                import xlrd
                return xlrd.xldate_as_datetime(value, datemode).date()
            except Exception:
                pass
        if isinstance(value, str):
            value = value.strip()
            for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d.%m.%Y', '%Y/%m/%d'):
                try:
                    return datetime.strptime(value, fmt).date()
                except ValueError:
                    continue
        return False

    def _read_xlsx(self, file_data):
        """Read .xlsx and return (sheet_data as list of rows, datemode None)."""
        try:
            import openpyxl
        except ImportError:
            raise UserError(_('openpyxl library not installed. Please install: pip install openpyxl'))
        workbook = openpyxl.load_workbook(BytesIO(file_data), read_only=True, data_only=True)
        sheet = workbook.active
        data = []
        for row in sheet.iter_rows(values_only=True):
            data.append(list(row) if row else [])
        return data, None

    def _read_xls(self, file_data):
        """Read .xls and return (sheet_data as list of rows, datemode)."""
        try:
            import xlrd
        except ImportError:
            raise UserError(_('xlrd library not installed. Please install: pip install xlrd'))
        workbook = xlrd.open_workbook(file_contents=file_data)
        sheet = workbook.sheet_by_index(0)
        datemode = workbook.datemode
        data = []
        for row_idx in range(sheet.nrows):
            row = []
            for col_idx in range(sheet.ncols):
                cell_value = sheet.cell_value(row_idx, col_idx)
                if sheet.cell_type(row_idx, col_idx) == 3:  # XL_CELL_DATE
                    try:
                        cell_value = xlrd.xldate_as_datetime(cell_value, datemode)
                    except Exception:
                        pass
                row.append(cell_value)
            data.append(row)
        return data, datemode

    def _cell(self, row, col_index, default=None):
        if col_index >= len(row):
            return default
        val = row[col_index]
        if val is None or (isinstance(val, str) and not val.strip()):
            return default
        return val

    def _cell_float(self, row, col_index):
        val = self._cell(row, col_index)
        if val is None:
            return 0.0
        try:
            return float(val)
        except (TypeError, ValueError):
            return 0.0

    def action_confirm(self):
        self.ensure_one()
        if not self.excel_file:
            raise UserError(_('Please upload an Excel file.'))
        file_data = base64.b64decode(self.excel_file)
        fn = (self.filename or '').lower()
        if fn.endswith('.xlsx'):
            sheet_data, datemode = self._read_xlsx(file_data)
        elif fn.endswith('.xls'):
            sheet_data, datemode = self._read_xls(file_data)
        else:
            raise UserError(_('Unsupported format. Please use .xlsx or .xls file.'))

        if not sheet_data or len(sheet_data) < 7:
            raise UserError(_('Excel must have at least 7 rows. Data starts at row 7.'))

        # C=2 dept, D=3 purchase_object, E=4 cpv_code, F=5 estimated_cost, H=7 tender_notice_number,
        # I=8 publicaiton_date, J=9 open_date, K=10 tender_status, L=11 tenderer, M=12 final_price,
        # O=14 funding_year, P=15 shesyidvis_safudzveli
        COL_C, COL_D, COL_E, COL_F, COL_H, COL_I, COL_J, COL_K, COL_L, COL_M, COL_O, COL_P = (
            2, 3, 4, 5, 7, 8, 9, 10, 11, 12, 14, 15
        )
        start_row_index = 6  # row 7 (1-based)
        created = []
        for row_idx in range(start_row_index, len(sheet_data)):
            row = sheet_data[row_idx]
            if not row:
                continue
            if not any(
                x is not None and (str(x).strip() if isinstance(x, str) else True)
                for x in (row[COL_C:COL_P + 1] if len(row) > COL_P else row[COL_C:])
            ):
                continue
            dept_name = self._cell(row, COL_C)
            department_id = False
            if dept_name is not None and str(dept_name).strip():
                dept = self.env['hr.department'].search([('name', 'ilike', str(dept_name).strip())], limit=1)
                if dept:
                    department_id = dept.id
            purchase_object = self._cell(row, COL_D) or ''
            if isinstance(purchase_object, str):
                purchase_object = purchase_object.strip()
            cpv_code = self._cell(row, COL_E)
            cpv_code = str(cpv_code).strip() if cpv_code is not None else ''
            estimated_cost = self._cell_float(row, COL_F)
            tender_notice_number = self._cell(row, COL_H)
            tender_notice_number = str(tender_notice_number).strip() if tender_notice_number is not None else ''
            pub_val = self._cell(row, COL_I)
            publicaiton_date = self._parse_date(pub_val, datemode) if pub_val is not None else False
            open_val = self._cell(row, COL_J)
            open_date = self._parse_date(open_val, datemode) if open_val is not None else False
            tender_status = self._cell(row, COL_K)
            tender_status = str(tender_status).strip() if tender_status is not None else ''
            tenderer_name = self._cell(row, COL_L)
            tenderer_id = False
            if tenderer_name is not None and str(tenderer_name).strip():
                partner = self.env['res.partner'].search([
                    ('name', 'ilike', str(tenderer_name).strip())
                ], limit=1)
                if partner:
                    tenderer_id = partner.id
            final_price = self._cell_float(row, COL_M)
            funding_year = self._cell(row, COL_O)
            funding_year = str(funding_year).strip() if funding_year is not None else ''
            shesyidvis_safudzveli = self._cell(row, COL_P)
            shesyidvis_safudzveli = str(shesyidvis_safudzveli).strip() if shesyidvis_safudzveli is not None else ''
            shesyidvis_safudzvelis_value = ''
            if shesyidvis_safudzveli == 'GEO ტენდერი':
                shesyidvis_safudzvelis_value = 'geo_tender'
            elif shesyidvis_safudzveli == 'ელ. ტენდერი':
                shesyidvis_safudzvelis_value = 'el_tender'

            vals = {
                'department_id': department_id,
                'purchase_object': purchase_object or '',
                'cpv_code': cpv_code,
                'estimated_cost': estimated_cost,
                'tender_notice_number': tender_notice_number,
                'publicaiton_date': publicaiton_date,
                'open_date': open_date,
                'tender_status': tender_status,
                'tenderer': tenderer_id,
                'final_price': final_price,
                'funding_year': funding_year,
                'shesyidvis_safudzveli': shesyidvis_safudzvelis_value,
            }
            rec = self.env['tenderi'].create(vals)
            created.append(rec)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Import successful'),
                'message': _('%s tenderi record(s) created.') % len(created),
                'type': 'success',
                'sticky': False,
            },
        }
