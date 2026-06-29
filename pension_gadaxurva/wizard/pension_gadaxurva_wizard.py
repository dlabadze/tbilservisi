# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.exceptions import UserError
import base64
from io import BytesIO


class PensionGadaxurvaWizard(models.TransientModel):
    _name = 'pension.gadaxurva.wizard'
    _description = 'საპენსიო გადახურვა'

    date = fields.Date(string='თარიღი', required=True, default=fields.Date.context_today)
    excel_file = fields.Binary(string='Excel ფაილი', required=True)
    excel_filename = fields.Char(string='ფაილის სახელი')

    def action_generate(self):
        self.ensure_one()
        data = base64.b64decode(self.excel_file)
        rows = self._read_excel(data)
        if not rows:
            raise UserError('ფაილში მონაცემები ვერ მოიძებნა.')

        account_debit = self.env['account.account'].search(
            [('code', '=', '3133.28')], limit=1
        )
        account_credit = self.env['account.account'].search(
            [('code', '=', '3133.27')], limit=1
        )
        if not account_debit:
            raise UserError('ანგარიში 3133.28 ვერ მოიძებნა.')
        if not account_credit:
            raise UserError('ანგარიში 3133.27 ვერ მოიძებნა.')

        journal = self.env['account.journal'].search(
            [('name', '=', 'general')], limit=1
        )
        if not journal:
            raise UserError('საერთო ჟურნალი ვერ მოიძებნა.')

        line_vals = []
        missing_partners = []

        for row in rows:
            partner = self._find_partner(row['partner_name'], row['partner_vat'])
            if not partner:
                missing_partners.append(
                    '%s (%s)' % (row['partner_name'], row['partner_vat'])
                )
                continue

            line_vals.append((0, 0, {
                'account_id': account_debit.id,
                'partner_id': partner.id,
                'debit': row['amount'],
                'credit': 0.0,
                'name': row['partner_name'],
            }))
            line_vals.append((0, 0, {
                'account_id': account_credit.id,
                'partner_id': False,
                'debit': 0.0,
                'credit': row['amount'],
                'name': row['partner_name'],
            }))

        if missing_partners:
            raise UserError(
                'შემდეგი პარტნიორები ვერ მოიძებნა:\n' + '\n'.join(missing_partners)
            )

        if not line_vals:
            raise UserError('გასატარებელი ჩანაწერები ვერ მოიძებნა.')

        self.env['account.move'].create({
            'date': self.date,
            'journal_id': journal.id,
            'line_ids': line_vals,
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'წარმატება',
                'message': 'საპენსიო გატარება შეიქმნა.',
                'type': 'success',
                'sticky': False,
            },
        }

    def _read_excel(self, data):
        try:
            import openpyxl
        except ImportError:
            raise UserError('openpyxl ბიბლიოთეკა არ არის დაინსტალირებული.')

        rows = []
        try:
            wb = openpyxl.load_workbook(BytesIO(data), data_only=True)
            ws = wb.active
            for idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
                if idx < 8:
                    continue
                partner_name = row[1] if len(row) > 1 else None   # column B
                partner_vat = row[2] if len(row) > 2 else None    # column C
                amount_raw = row[3] if len(row) > 3 else None     # column D

                if not partner_name and not partner_vat:
                    continue

                try:
                    amount = float(amount_raw) if amount_raw not in (None, '') else 0.0
                except (ValueError, TypeError):
                    amount = 0.0

                if amount <= 0:
                    continue

                rows.append({
                    'partner_name': str(partner_name).strip() if partner_name else '',
                    'partner_vat': str(partner_vat).strip() if partner_vat else '',
                    'amount': amount,
                })
        except Exception as e:
            raise UserError('Excel ფაილის წაკითხვა ვერ მოხერხდა: %s' % e)
        return rows

    def _find_partner(self, name, vat):
        if vat:
            partner = self.env['res.partner'].search([('vat', '=', vat)], limit=1)
            if partner:
                return partner
        if name:
            partner = self.env['res.partner'].search([('name', '=', name)], limit=1)
            if partner:
                return partner
        return False
