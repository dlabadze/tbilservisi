import base64
import io

import pandas as pd

from odoo import models, fields, _
from odoo.exceptions import UserError

# (ექსელის სათაური, purchase.requisition ველი, ტიპი)
# char | float | date | bool | selection | text
# supplier_id_code: ექსელიდან VAT → res.partner ძებნა → vendor_id (არ იწერება supplier_id_code, relatedა)
PURCHASE_REQUISITION_IMPORT_MAP = (
    ('Start Date', 'date_start', 'date'),
    ('End Date', 'date_end', 'date'),
    ('მომწოდებლის საიდ. კოდი', 'supplier_id_code', 'char'),
    ('მოწოდების თარიღი', 'delivery_date', 'date'),
    ('შესყიდვის საშუალება', 'purchase_method', 'selection'),
    ('შესყიდვის საფუძველი', 'purchase_basis', 'selection'),
    ('საფუძველი', 'basis', 'char'),
    ('ხელშეკრულების N', 'contract_number', 'char'),
    ('SPA ან CMR ნომერი', 'spa_or_cmr_number', 'char'),
    ('პირგასამტეხლო', 'pirgasamtexlo', 'float'),
    ('ხელშეკრულების თანხა', 'contract_amount', 'float'),
    ('მიღება-ჩაბარების თანხა', 'receipt_delivery_amount', 'float'),
    ('გადახდილი თანხა', 'paid_amount', 'float'),
    ('დარჩენილი თანხა', 'remaining_amount', 'float'),
    ('მოწოდების ტიპი', 'delivery_type', 'selection'),
    ('დღგს ჩათვლით?', 'vat_included', 'selection'),
    ('ხელშეკრულების სტატუსი', 'contract_status', 'selection'),
    ('შენიშვნა', 'notes', 'text'),
)


class ImportPurchaseRequisitionWizard(models.TransientModel):
    _name = 'import.purchase.requisition.wizard'
    _description = 'Import Purchase Requisitions from Excel'

    excel_file = fields.Binary(string='Excel ფაილი', required=True)
    file_name = fields.Char(string='ფაილის სახელი')

    def _cell_str(self, val):
        if pd.isna(val):
            return False
        if isinstance(val, float) and val.is_integer():
            return str(int(val))
        text = str(val).strip()
        return text or False

    def _cell_float(self, val):
        if pd.isna(val):
            return None
        if isinstance(val, str):
            cleaned = val.strip().replace('\u00a0', '').replace(' ', '')
            if cleaned.count(',') == 1 and '.' not in cleaned:
                cleaned = cleaned.replace(',', '.')
            else:
                cleaned = cleaned.replace(',', '')
            num = pd.to_numeric(cleaned, errors='coerce')
        else:
            num = pd.to_numeric(val, errors='coerce')
        if pd.isna(num):
            return None
        return float(num)

    def _resolve_vendor_id_from_vat(self, raw):
        """VAT / საიდ. კოდი → res.partner → vendor_id."""
        vat = self._cell_str(raw)
        if not vat:
            return False
        Partner = self.env['res.partner'].sudo()
        partner = Partner.search([('vat', '=', vat)], limit=1)
        if not partner:
            partner = Partner.search([('vat', 'ilike', vat)], limit=1)
        return partner.id if partner else False

    def _resolve_selection_value(self, field_name, raw):
        """ექსელის ტექსტი ან გასაღები → Selection key."""
        Requisition = self.env['purchase.requisition']
        field = Requisition._fields.get(field_name)
        if not field or field.type != 'selection':
            return self._cell_str(raw)
        if hasattr(field, '_description_selection'):
            items = field._description_selection(self.env)
        else:
            sel = field.selection
            items = sel(Requisition) if callable(sel) else (sel or [])
        if not items:
            return False
        if isinstance(raw, float) and float(raw).is_integer():
            s_key = str(int(raw))
        else:
            s_key = self._cell_str(raw)
        if not s_key:
            return False
        for key, label in items:
            if key == s_key:
                return key
        for key, label in items:
            if label and str(label).strip() == s_key:
                return key
        s_lower = s_key.lower()
        for key, label in items:
            if label and str(label).strip().lower() == s_lower:
                return key
        return False

    def _row_to_vals(self, row, df_columns):
        vals = {}
        for excel_h, fname, ftype in PURCHASE_REQUISITION_IMPORT_MAP:
            if excel_h not in df_columns:
                continue
            raw = row[excel_h]
            if pd.isna(raw):
                continue
            if fname == 'supplier_id_code':
                vid = self._resolve_vendor_id_from_vat(raw)
                if vid:
                    vals['vendor_id'] = vid
                continue
            if ftype == 'char':
                vals[fname] = self._cell_str(raw)
            elif ftype == 'float':
                num = self._cell_float(raw)
                if num is not None:
                    vals[fname] = num
            elif ftype == 'date':
                dt = pd.to_datetime(raw, errors='coerce', dayfirst=True)
                if not pd.isna(dt):
                    vals[fname] = dt.date()
            elif ftype == 'bool':
                s = str(raw).strip().lower()
                vals[fname] = s not in ('0', 'false', 'no', 'არა', '') and s not in ('none',)
            elif ftype == 'selection':
                sel = self._resolve_selection_value(fname, raw)
                if sel:
                    vals[fname] = sel
            elif ftype == 'text':
                vals[fname] = str(raw).strip() if str(raw).strip() else False
        vals.pop('supplier_id_code', None)
        return vals

    def action_import(self):
        self.ensure_one()
        if not PURCHASE_REQUISITION_IMPORT_MAP:
            raise UserError(
                _('შეავსეთ PURCHASE_REQUISITION_IMPORT_MAP wizard ფაილში (ექსელი → Odoo ველი).')
            )
        if not self.excel_file:
            raise UserError(_('გთხოვთ ატვირთოთ ექსელის ფაილი.'))
        filename_lower = (self.file_name or '').lower()
        if not filename_lower.endswith('.xlsx'):
            raise UserError(_('გთხოვთ ატვირთოთ .xlsx ფაილი.'))

        try:
            file_data = base64.b64decode(self.excel_file)
            df = pd.read_excel(io.BytesIO(file_data), header=0)
        except Exception as e:
            raise UserError(_('ფაილის წაკითხვა ვერ მოხერხდა: %s') % e) from e

        if df.empty:
            raise UserError(_('ექსელი ცარიელია.'))

        df.columns = [str(c).strip() if c is not None else '' for c in df.columns]
        excel_headers = [h for h, _f, _t in PURCHASE_REQUISITION_IMPORT_MAP]
        missing = [h for h in excel_headers if h not in df.columns]
        if missing:
            raise UserError(
                _('ექსელში აკლია სვეტ(ებ)ი: %s') % ', '.join(missing)
            )

        Requisition = self.env['purchase.requisition']
        company = self.env.company
        created = 0
        for _idx, row in df.iterrows():
            vals = self._row_to_vals(row, df.columns)
            if not vals:
                continue
            vals.setdefault('company_id', company.id)
            Requisition.create(vals)
            created += 1

        if not created:
            raise UserError(_('ვერც ერთი ჩანაწერი არ შეიქმნა.'))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('იმპორტი'),
                'message': _('შეიქმნა %s შესყიდვის შეთანხმება.') % created,
                'type': 'success',
            },
        }
