import base64
from io import BytesIO
from odoo import fields, models, _
from odoo.exceptions import UserError


class KvebaAccountMoveWizard(models.TransientModel):
    _name = 'kveba.account.move.wizard'
    _description = 'Kveba Account Move Wizard'

    date = fields.Date('Date', required=True)
    excel_file = fields.Binary('Excel File', required=True)
    excel_filename = fields.Char('Excel File Name')

    def _get_analytic_distribution(self, employee):
        """Return analytic_distribution dict for an employee based on their department.

        Includes both the department's analytic account and the top-level parent's analytic
        account (50/50 when both exist, 100% when only one is found).
        """
        if not employee or not employee.department_id:
            return {}

        dept = employee.department_id

        # Walk up to find the top-level (last) parent
        top = dept
        while top.parent_id:
            top = top.parent_id

        dept_analytic = self.env['account.analytic.account'].sudo().search(
            [('name', '=', dept.name)], limit=1
        )
        top_analytic = self.env['account.analytic.account'].sudo().search(
            [('name', '=', top.name)], limit=1
        ) if top.id != dept.id else dept_analytic

        if dept_analytic and top_analytic and dept_analytic.id != top_analytic.id:
            return {str(dept_analytic.id): 100.0, str(top_analytic.id): 100.0}
        analytic = dept_analytic or top_analytic
        return {str(analytic.id): 100.0} if analytic else {}

    def _build_missed_partners_excel(self, missed_partners):
        import pandas as pd
        df = pd.DataFrame(missed_partners, columns=['რიგი', 'სახელი', 'პირადი ნომერი'])
        stream = BytesIO()
        with pd.ExcelWriter(stream, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='ვერ მოიძებნა')
        return base64.b64encode(stream.getvalue()).decode()

    def action_generate_journal_entries(self):
        self.ensure_one()

        try:
            import pandas as pd
            file_data = base64.b64decode(self.excel_file)
            df = pd.read_excel(BytesIO(file_data), header=None)
        except Exception as e:
            raise UserError(_("Error loading Excel file: %s") % str(e))

        # Row 6 in Excel = index 5 (0-based); columns D-H = indices 3-7
        col_indices = [3, 4, 5, 6, 7]
        col_letters = ['D', 'E', 'F', 'G', 'H']

        account_pairs = []
        for col_idx, col_letter in zip(col_indices, col_letters):
            header = df.iloc[5, col_idx]
            if not header or str(header).strip() == 'nan':
                account_pairs.append(None)
                continue
            header_str = str(header).replace('/', '.')
            parts = header_str.split('-', 1)
            if len(parts) != 2:
                account_pairs.append(None)
                continue
            debit_code = parts[0].strip()
            credit_code = parts[1].strip()
            debit_account = self.env['account.account'].sudo().search([('code', '=', debit_code)], limit=1)
            credit_account = self.env['account.account'].sudo().search([('code', '=', credit_code)], limit=1)
            if not debit_account:
                raise UserError(_("Account not found for code: %s (column %s, debit)") % (debit_code, col_letter))
            if not credit_account:
                raise UserError(_("Account not found for code: %s (column %s, credit)") % (credit_code, col_letter))
            account_pairs.append((debit_account, credit_account))

        all_lines = []
        missed_partners = []

        # Data starts at row 8 in Excel = index 7 (0-based)
        for row_idx in range(7, len(df)):
            employee_name = df.iloc[row_idx, 1]  # column B
            partner_vat = df.iloc[row_idx, 2]    # column C

            name_empty = not employee_name or str(employee_name) == 'nan'
            vat_empty = not partner_vat or str(partner_vat) == 'nan'
            if name_empty and vat_empty:
                continue

            partner = False
            employee = False
            vat_str = ''

            if not vat_empty:
                vat_str = str(partner_vat)
                if '.' in vat_str:
                    vat_str = vat_str.split('.')[0]

                # Always search employee so we can get department for analytic
                employee = self.env['hr.employee'].sudo().search(
                    [('identification_id', '=', vat_str), ('active', 'in', [True, False])],
                    limit=1,
                )
                partner = self.env['res.partner'].sudo().search([('vat', '=', vat_str)], limit=1)
                if not partner:
                    partner = employee.work_contact_id if employee else False

            if not partner:
                missed_partners.append([
                    row_idx + 1,
                    str(employee_name) if not name_empty else '',
                    vat_str,
                ])
                continue

            name = str(employee_name) if not name_empty else ''
            analytic_dist = self._get_analytic_distribution(employee)

            for col_idx, pair in zip(col_indices, account_pairs):
                if not pair:
                    continue
                val = df.iloc[row_idx, col_idx]
                try:
                    amount = float(val) if val and str(val) != 'nan' else 0.0
                except (ValueError, TypeError):
                    amount = 0.0
                if not amount:
                    continue

                debit_account, credit_account = pair

                debit_vals = {
                    'account_id': debit_account.id,
                    'partner_id': partner.id,
                    'name': name,
                    'debit': amount,
                    'credit': 0.0,
                }
                if analytic_dist and debit_account.code and debit_account.code[0] in ('3', '7'):
                    debit_vals['analytic_distribution'] = analytic_dist

                credit_vals = {
                    'account_id': credit_account.id,
                    'partner_id': partner.id,
                    'name': name,
                    'debit': 0.0,
                    'credit': amount,
                }
                if analytic_dist and credit_account.code and credit_account.code[0] in ('3', '7'):
                    credit_vals['analytic_distribution'] = analytic_dist

                all_lines.append((0, 0, debit_vals))
                all_lines.append((0, 0, credit_vals))

        if not all_lines and missed_partners:
            excel_data = self._build_missed_partners_excel(missed_partners)
            attachment = self.env['ir.attachment'].sudo().create({
                'name': 'missed_partners.xlsx',
                'datas': excel_data,
                'res_model': self._name,
                'res_id': 0,
                'type': 'binary',
            })
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('პარტნიორები ვერ მოიძებნა'),
                    'message': _('არცერთი ჩანაწერი არ შეიქმნა. %d პარტნიორი ვერ მოიძებნა.') % len(missed_partners),
                    'type': 'danger',
                    'sticky': True,
                    'next': {
                        'type': 'ir.actions.act_url',
                        'url': '/web/content/%s?download=true' % attachment.id,
                        'target': 'self',
                    },
                },
            }

        if not all_lines:
            raise UserError(_("No data found in the Excel file (starting from row 8)"))

        journal = self.env['account.journal'].sudo().search([('name', '=', 'კვება')], limit=1)
        if not journal:
            raise UserError(_("Journal 'კვება' not found"))

        move = self.env['account.move'].sudo().create({
            'move_type': 'entry',
            'date': self.date,
            'journal_id': journal.id,
            'line_ids': all_lines,
        })

        if missed_partners:
            excel_data = self._build_missed_partners_excel(missed_partners)
            attachment = self.env['ir.attachment'].sudo().create({
                'name': 'missed_partners.xlsx',
                'datas': excel_data,
                'res_model': self._name,
                'res_id': 0,
                'type': 'binary',
            })
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('გატარება დასრულდა'),
                    'message': _('გატარება შეიქმნა. %d პარტნიორი ვერ მოიძებნა — იხილეთ ფაილი.') % len(missed_partners),
                    'type': 'warning',
                    'sticky': True,
                    'next': {
                        'type': 'ir.actions.act_url',
                        'url': '/web/content/%s?download=true' % attachment.id,
                        'target': 'self',
                    },
                },
            }

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'res_id': move.id,
            'view_mode': 'form',
            'target': 'current',
        }
