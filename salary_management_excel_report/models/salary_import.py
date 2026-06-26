import io
import base64
from odoo import models, fields, api
from odoo.exceptions import UserError

try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None


class SalaryImport(models.Model):
    _inherit = 'salary.import'

    def action_generate_excel(self):
        if not xlsxwriter:
            raise UserError("The 'xlsxwriter' library is not installed.")

        # 1. Fetch all lines related to the selected salary import records
        lines = self.env['salary.import.line'].search([('import_id', 'in', self.ids)])
        
        if not lines:
            raise UserError("No salary lines found to export.")

        # 2. Group and aggregate data by partner_id to merge duplicates
        grouped_data = {}
        for line in lines:
            partner = line.partner_id
            if not partner:
                continue  # Skip lines without a partner
            
            partner_id = partner.id
            
            if partner_id not in grouped_data:
                grouped_data[partner_id] = {
                    'vat': partner.vat or '',
                    'name': partner.name or '',
                    'total_salary': 0.0,
                    'base_salary': 0.0,
                    'pension': 0.0,
                    'company_tax': 0.0,
                    'net_amount': 0.0
                }
            
            # Sum up all financial fields for duplicate partners
            grouped_data[partner_id]['total_salary'] += line.total_salary or 0.0
            grouped_data[partner_id]['base_salary'] += line.base_salary or 0.0
            grouped_data[partner_id]['pension'] += line.pension or 0.0
            grouped_data[partner_id]['company_tax'] += line.company_tax or 0.0
            grouped_data[partner_id]['net_amount'] += line.net_amount or 0.0

        # 3. Setup Excel workbook
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Salary Report')

        # Styles
        header_format = workbook.add_format({
            'bold': True, 'font_size': 11, 'bg_color': '#E0E0E0', 'border': 1, 'align': 'center'
        })
        data_format = workbook.add_format({'font_size': 10, 'border': 1})
        amount_format = workbook.add_format({'font_size': 10, 'border': 1, 'num_format': '#,##0.00'})

        # Column Headers (Updated with your new columns)
        headers = [
            'თანამშრომლის პირადი ნომერი', 
            'დასახელება',                  
            'Total Salary',               
            'Base Salary',
            'Pension',
            'Company Tax',
            'Net Amount'
        ]
        
        for col_num, header_title in enumerate(headers):
            worksheet.write(0, col_num, header_title, header_format)

        # 4. Populate Excel with merged data
        row_num = 1
        for partner_info in grouped_data.values():
            worksheet.write(row_num, 0, partner_info['vat'], data_format)
            worksheet.write(row_num, 1, partner_info['name'], data_format)
            worksheet.write(row_num, 2, partner_info['total_salary'], amount_format)
            worksheet.write(row_num, 3, partner_info['base_salary'], amount_format)
            worksheet.write(row_num, 4, partner_info['pension'], amount_format)
            worksheet.write(row_num, 5, partner_info['company_tax'], amount_format)
            worksheet.write(row_num, 6, partner_info['net_amount'], amount_format)
            row_num += 1

        # Adjust column widths for clean visibility
        worksheet.set_column('A:B', 25)
        worksheet.set_column('C:G', 15)

        workbook.close()
        output.seek(0)

        # 5. Generate and return download action
        file_data = base64.b64encode(output.read())
        output.close()

        attachment = self.env['ir.attachment'].create({
            'name': 'Salary_Management_Report.xlsx',
            'type': 'binary',
            'datas': file_data,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }