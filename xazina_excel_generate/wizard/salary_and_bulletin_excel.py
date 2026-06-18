import base64
import io

import xlsxwriter

from odoo import fields, models


class SalaryAndBulletinExcel(models.TransientModel):
    _name = 'salary.and.bulletin.excel'
    _description = 'Salary and Bulletin Excel Generator'

    date = fields.Date(string='თარიღი', required=True)

    def _get_employee_info(self, partner_id):
        employee = self.env['hr.employee'].sudo().search(
            [('work_contact_id', '=', partner_id)], limit=1
        )
        if not employee:
            return '', '', ''
        dept = employee.department_id
        while dept.parent_id:
            dept = dept.parent_id
        return (
            dept.name or '',
            employee.department_id.name or '',
            employee.job_id.name or '',
        )

    def action_generate_excel(self):
        self.ensure_one()

        moves = self.env['account.move'].sudo().search([
            ('state', '=', 'posted'),
            ('date', '=', self.date),
            ('journal_id.name', '=', 'Salaries'),
        ])

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('ხელფასი და ბიულეტენი')

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
            'თანამშრომლის დასახელება',
            'პირადი ნომერი',
            'დეპარტამენი',
            'სამსახური',
            'თანამდებობა',
            'ხელფასი',
            'ბიულეტენი',
        ]
        col_widths = [40, 20, 25, 25, 25, 15, 15]

        sheet.set_row(0, 30)
        for col, (h, w) in enumerate(zip(headers, col_widths)):
            sheet.write(0, col, h, header_fmt)
            sheet.set_column(col, col, w)

        partners = {}

        for move in moves:
            pid = None
            name = ''
            vat = ''
            salary = 0.0
            bulletin = 0.0

            for line in move.line_ids:
                code = line.account_id.code
                if code == '3139' and line.partner_id:
                    pid = line.partner_id.id
                    name = line.partner_id.name or ''
                    vat = line.partner_id.vat or ''
                elif code == '7410.01':
                    salary += line.debit
                elif code == '7410.03':
                    bulletin += line.debit

            if pid:
                if pid not in partners:
                    dept_root, dept, job = self._get_employee_info(pid)
                    partners[pid] = {
                        'name': name, 'vat': vat,
                        'dept_root': dept_root, 'dept': dept, 'job': job,
                        'salary': 0.0, 'bulletin': 0.0,
                    }
                partners[pid]['salary'] += salary
                partners[pid]['bulletin'] += bulletin

        row = 1
        for data in partners.values():
            sheet.write(row, 0, data['name'], cell_fmt)
            sheet.write(row, 1, data['vat'], cell_fmt)
            sheet.write(row, 2, data['dept_root'], cell_fmt)
            sheet.write(row, 3, data['dept'], cell_fmt)
            sheet.write(row, 4, data['job'], cell_fmt)
            sheet.write(row, 5, data['salary'], num_fmt)
            sheet.write(row, 6, data['bulletin'], num_fmt)
            row += 1

        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.read())

        attachment = self.env['ir.attachment'].create({
            'name': f'salary_bulletin_{self.date}.xlsx',
            'type': 'binary',
            'datas': file_data,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }
