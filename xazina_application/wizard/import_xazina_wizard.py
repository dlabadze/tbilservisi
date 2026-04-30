import base64
import io

import pandas as pd

from odoo import models, fields, _
from odoo.exceptions import UserError


class ImportXazinaWizard(models.TransientModel):
    _name = 'import.xazina.wizard'
    _description = 'Import Xazina Wizard'

    xazina_type = fields.Selection([
        ('შემოსავლები', 'შემოსავლები'),
        ('გადარიცხვები', 'გადარიცხვები'),
    ], string='ხაზინის ტიპი', required=True)
    excel_file = fields.Binary(string='Excel ფაილი', required=True)
    file_name = fields.Char(string='ფაილის სახელი')

    def action_generate_records(self):
        self.ensure_one()
        if not self.excel_file:
            raise UserError(_('გთხოვთ ატვირთოთ ექსელის ფაილი.'))
        
        try:
            file_data = base64.b64decode(self.excel_file)
            filename_lower = (self.file_name or '').lower()
            data = []
            if filename_lower.endswith('.xlsx'):
                data = pd.read_excel(io.BytesIO(file_data))
            else:
                raise UserError(_('გთხოვთ ატვირთოთ ექსელის ფაილი სწორი ფორმატში. (.xlsx)'))
            
            if data.empty:
                raise UserError(_('ექსელის ფაილი ცარიელია.'))
            data['თარიღი'] = pd.to_datetime(data['თარიღი'], errors='coerce')
            info = []
            for _idx, row in data.iterrows():
                record_date = row['თარიღი']
                if pd.isna(record_date):
                    continue
                info.append({
                    'date': record_date.date(),
                    'year': row.get('წელი'),
                    'xazina_type': self.xazina_type,
                })
            if info:
                self.env['xazina'].create(info)
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _(f'ექსელის ატვირთვა'),
                        'message': _(f'{self.xazina_type}ს ექსელის ატვირთვა წარმატებით დასრულდა.\n'
                        f'შეიქმნა {len(info)} ჩანაწერი.'
                        ),
                        'type': 'success',
                    }
                }
            raise UserError(str(info))
        except UserError:
            raise
        except Exception as e:
            raise UserError(_('დაფიქსირდა შეცდომა ფაილის წაკითხვისას: %s') % e) from e