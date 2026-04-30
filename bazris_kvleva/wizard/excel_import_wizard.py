import base64
import io
from odoo import models, fields, api, _
from odoo.exceptions import UserError
try:
    import openpyxl
except ImportError:
    openpyxl = None


class ExcelImportWizard(models.TransientModel):
    _name = 'bazris.kvleva.excel.import.wizard'
    _description = 'Excel Import Wizard for Bazris Kvleva'

    excel_file = fields.Binary(string='Excel File', required=True)
    filename = fields.Char(string='Filename')

    def action_import(self):
        """Import data from Excel file"""
        if not openpyxl:
            raise UserError(_('Please install openpyxl library: pip install openpyxl'))
        
        if not self.excel_file:
            raise UserError(_('Please select an Excel file to import.'))

        try:
            # Decode the file
            file_data = base64.b64decode(self.excel_file)
            workbook = openpyxl.load_workbook(io.BytesIO(file_data))
            worksheet = workbook.active

            # Read data rows starting from row 6
            bazris_kvleva_obj = self.env['bazris.kvleva']
            created_records = []
            
            # Column mapping: B=1, C=2, D=3, E=4, F=5, G=6, H=7, I=8, J=9, K=10, L=11, M=12
            # openpyxl uses 0-based indexing, so B=1, C=2, etc.
            for row_idx, row in enumerate(worksheet.iter_rows(min_row=6, values_only=False), start=6):
                # Skip empty rows
                if not any(cell.value for cell in row):
                    continue
                
                # Map Excel columns to fields (columns B-M, indices 1-12)
                # Column B (index 1): line_number
                line_number = None
                if len(row) > 1 and row[1].value is not None:
                    try:
                        line_number = int(row[1].value)
                    except (ValueError, TypeError):
                        line_number = None
                
                # Column C (index 2): job_id - search by name in hr.department
                job_id = False
                if len(row) > 2 and row[2].value:
                    dept_name = str(row[2].value).strip()
                    if dept_name:
                        department = self.env['hr.department'].search([('name', '=', dept_name)], limit=1)
                        if department:
                            job_id = department.id
                
                # Column D (index 3): saf_number
                saf_number = str(row[3].value) if len(row) > 3 and row[3].value else ''
                
                # Column E (index 4): saf_date
                saf_date = self._parse_date(row[4].value) if len(row) > 4 and row[4].value else False
                
                # Column F (index 5): purchase_object
                purchase_object = str(row[5].value) if len(row) > 5 and row[5].value else ''
                
                # Column G (index 6): last_date
                last_date = self._parse_date(row[6].value) if len(row) > 6 and row[6].value else False
                
                # Column H (index 7): status
                status = str(row[7].value) if len(row) > 7 and row[7].value else ''
                
                # Column I (index 8): bazris_kvlevis_nomeri
                bazris_kvlevis_nomeri = str(row[8].value) if len(row) > 8 and row[8].value else ''
                
                # Column J (index 9): sap_number
                sap_number = str(row[9].value) if len(row) > 9 and row[9].value else ''
                
                # Column K (index 10): sap_date
                sap_date = self._parse_date(row[10].value) if len(row) > 10 and row[10].value else False
                
                # Column L (index 11): shenishvna
                shenishvna = str(row[11].value) if len(row) > 11 and row[11].value else ''
                
                # Column M (index 12): shemsrulebeli_id - search by name in bazris.kvlevis.tanamshromlebi
                shemsrulebeli_id = False
                if len(row) > 12 and row[12].value:
                    tanamshromlebi_name = str(row[12].value).strip()
                    if tanamshromlebi_name:
                        tanamshromlebi = self.env['bazris.kvlevis.tanamshromlebi'].search([('name', '=', tanamshromlebi_name)], limit=1)
                        if tanamshromlebi:
                            shemsrulebeli_id = tanamshromlebi.id
                        else:
                            # Create new record if not found
                            tanamshromlebi = self.env['bazris.kvlevis.tanamshromlebi'].create({'name': tanamshromlebi_name})
                            shemsrulebeli_id = tanamshromlebi.id
                
                values = {
                    'line_number': line_number,
                    'job_id': job_id,
                    'saf_number': saf_number,
                    'saf_date': saf_date,
                    'purchase_object': purchase_object,
                    'last_date': last_date,
                    'status': status,
                    'bazris_kvlevis_nomeri': bazris_kvlevis_nomeri,
                    'sap_number': sap_number,
                    'sap_date': sap_date,
                    'shenishvna': shenishvna,
                    'shemsrulebeli_id': shemsrulebeli_id,
                }
                
                # Create record
                try:
                    record = bazris_kvleva_obj.create(values)
                    created_records.append(record)
                except Exception as e:
                    raise UserError(_('Error creating record at row %s: %s') % (row_idx, str(e)))

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Import Successful'),
                    'message': _('Successfully imported %s records.') % len(created_records),
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            raise UserError(_('Error importing Excel file: %s') % str(e))

    def _parse_date(self, value):
        """Parse date from Excel cell value"""
        if not value:
            return False
        if isinstance(value, str):
            from datetime import datetime
            try:
                return datetime.strptime(value, '%Y-%m-%d').date()
            except:
                try:
                    return datetime.strptime(value, '%d/%m/%Y').date()
                except:
                    return False
        elif hasattr(value, 'date'):
            return value.date()
        return False

