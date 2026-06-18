import base64
import io

import xlsxwriter

from odoo import fields, models


class XazinaDakavebebiExcel(models.TransientModel):
    _name = 'xazina.dakavebebi.excel'
    _description = 'Xazina Dakavebebi Excel'

    date = fields.Date(string='თარიღი', required=True)

    def action_generate_excel(self):
        self.ensure_one()

        moves = self.env['account.move'].sudo().search([
            ('state', '=', 'posted'),
            ('date', '=', self.date),
            ('journal_id.name', '=', 'Salaries'),
        ])

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('დაკავებები')

        header_fmt = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'bg_color': '#D7E4BC',
            'text_wrap': True,
        })
        cell_fmt = workbook.add_format({'border': 1})
        num_fmt = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})

        headers = [
            'თანამშრომელი',
            'პირადი ნომერი',
            'სოლიდარობა',
            'პროფკავშირი მერია (ხელფასი)',
            'პროფკავშირი მერია (ბიულეტენი)',
            'პროფკავშირი (ხელფასი)',
            'პროფკავშირი (ბიულეტენი)',
            'ფიტპასი',
            'ალიმენტი',
            'აღსრულება',
            'ჯარიმა',
            'სხვა დაკავება',
            'დაზღვევა',
            'ფონდი',
        ]
        col_widths = [40, 20, 14, 22, 24, 20, 22, 12, 12, 14, 12, 16, 14, 12]

        sheet.set_row(0, 30)
        for col, (h, w) in enumerate(zip(headers, col_widths)):
            sheet.write(0, col, h, header_fmt)
            sheet.set_column(col, col, w)

        partners = {}

        for move in moves:
            structs = move.payslip_ids.mapped('struct_id.name')
            is_salary = 'ხელფასის დარიცხვა' in structs
            is_bulletin = 'ბიულეტენი' in structs

            pid = None
            name = ''
            vat = ''
            ded = {
                'solidarity': 0.0,
                'profk_meria_salary': 0.0,
                'profk_meria_bulletin': 0.0,
                'profk_salary': 0.0,
                'profk_bulletin': 0.0,
                'fitpasi': 0.0,
                'alimenti': 0.0,
                'agsruleba': 0.0,
                'jarima': 0.0,
                'sxva_dakaveba': 0.0,
                'dazghveva': 0.0,
            }

            for line in move.line_ids:
                code = line.account_id.code
                if code == '3139' and line.partner_id:
                    pid = line.partner_id.id
                    name = line.partner_id.name or ''
                    vat = line.partner_id.vat or ''
                elif code == '3133.05':
                    ded['solidarity'] += line.credit
                elif code == '3133.10':
                    if is_salary:
                        ded['profk_meria_salary'] += line.credit
                    elif is_bulletin:
                        ded['profk_meria_bulletin'] += line.credit
                elif code == '3133.09':
                    if is_salary:
                        ded['profk_salary'] += line.credit
                    elif is_bulletin:
                        ded['profk_bulletin'] += line.credit
                elif code == '3133.11':
                    ded['fitpasi'] += line.credit
                elif code == '3133.20':
                    ded['alimenti'] += line.credit
                elif code == '3133.02':
                    ded['agsruleba'] += line.credit
                elif code == '3133.07':
                    ded['jarima'] += line.credit
                elif code == '3133.23':
                    ded['sxva_dakaveba'] += line.credit
                elif code == '3133.26':
                    ded['dazghveva'] += line.credit

            if pid:
                if pid not in partners:
                    partners[pid] = {'name': name, 'vat': vat,
                                     **{k: 0.0 for k in ded}}
                for k in ded:
                    partners[pid][k] += ded[k]

        row = 1
        for data in partners.values():
            sheet.write(row, 0, data['name'], cell_fmt)
            sheet.write(row, 1, data['vat'], cell_fmt)
            sheet.write(row, 2, data['solidarity'], num_fmt)
            sheet.write(row, 3, data['profk_meria_salary'], num_fmt)
            sheet.write(row, 4, data['profk_meria_bulletin'], num_fmt)
            sheet.write(row, 5, data['profk_salary'], num_fmt)
            sheet.write(row, 6, data['profk_bulletin'], num_fmt)
            sheet.write(row, 7, data['fitpasi'], num_fmt)
            sheet.write(row, 8, data['alimenti'], num_fmt)
            sheet.write(row, 9, data['agsruleba'], num_fmt)
            sheet.write(row, 10, data['jarima'], num_fmt)
            sheet.write(row, 11, data['sxva_dakaveba'], num_fmt)
            sheet.write(row, 12, data['dazghveva'], num_fmt)
            sheet.write(row, 13, '', cell_fmt)
            row += 1

        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.read())

        attachment = self.env['ir.attachment'].create({
            'name': f'dakavebebi_{self.date}.xlsx',
            'type': 'binary',
            'datas': file_data,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }
