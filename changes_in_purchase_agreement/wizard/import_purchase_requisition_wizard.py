import base64
import io

import pandas as pd

from odoo import models, fields, _
from odoo.exceptions import UserError

_DEPT_COL = '__dept_col__'  # sentinel for position-based column Y (index 24)

# (ექსელის სათაური, purchase.requisition ველი, ტიპი)
# char | float | date | bool | selection | text | department
# supplier_id_code: ექსელიდან VAT → res.partner ძებნა → vendor_id (არ იწერება supplier_id_code, relatedა)
PURCHASE_REQUISITION_IMPORT_MAP = (
    ('Start Date', 'date_start', 'date'),
    ('End Date', 'date_end', 'date'),
    ('Vendor', 'supplier_name', 'char'),
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
    ('CPV კოდი', 'basis', 'char'),
    (_DEPT_COL, 'department_id', 'department'),
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

    def _resolve_vendor_id_from_vat(self, raw, name=None):
        """VAT / საიდ. კოდი → res.partner → vendor_id. Creates partner if not found."""
        vat = self._cell_str(raw)
        if not vat:
            return False
        Partner = self.env['res.partner'].sudo()
        partner = Partner.search([('vat', '=', vat)], limit=1)
        if not partner:
            partner = Partner.search([('vat', 'ilike', vat)], limit=1)
        if not partner:
            partner = Partner.create({
                'name': name or vat,
                'vat': vat,
            })
        return partner.id

    def _resolve_department_id(self, raw):
        name = self._cell_str(raw)
        if not name:
            return False
        dept = self.env['hr.department'].search([('name', '=', name)], limit=1)
        if not dept:
            dept = self.env['hr.department'].search([('name', 'ilike', name)], limit=1)
        return dept.id if dept else False

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
            if fname == 'supplier_name':
                continue
            if fname == 'supplier_id_code':
                name_raw = row['Vendor'] if 'Vendor' in df_columns else None
                name = self._cell_str(name_raw) if name_raw is not None and not pd.isna(name_raw) else None
                vals['vendor_id'] = self._resolve_vendor_id_from_vat(raw, name=name)
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
            elif ftype == 'department':
                dept_id = self._resolve_department_id(raw)
                if dept_id:
                    vals[fname] = dept_id
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
        if len(df.columns) > 24:
            cols = list(df.columns)
            cols[24] = _DEPT_COL
            df.columns = cols
        excel_headers = [h for h, _f, _t in PURCHASE_REQUISITION_IMPORT_MAP if h != _DEPT_COL]
        missing = [h for h in excel_headers if h not in df.columns]
        if missing:
            raise UserError(
                _('ექსელში აკლია სვეტ(ებ)ი: %s') % ', '.join(missing)
            )

        Requisition = self.env['purchase.requisition']
        RequisitionLine = self.env['purchase.requisition.line']
        company = self.env.company
        default_product = self.env['product.product'].search(
            [('default_code', '=', '04923')], limit=1
        )
        created = 0
        for _idx, row in df.iterrows():
            vals = self._row_to_vals(row, df.columns)
            if not vals:
                continue
            vals.setdefault('company_id', company.id)
            requisition = Requisition.create(vals)
            if default_product:
                if requisition.delivery_type == 'მოკლევადიანი':
                    total_amount = requisition.contract_amount or 0.0
                elif requisition.delivery_type == 'გრძელვადიანი':
                    total_amount = (requisition.contract_amount or 0.0) * requisition._current_year_fraction()
                else:
                    total_amount = 0.0
                line_vals = {
                    'requisition_id': requisition.id,
                    'product_id': default_product.id,
                    'product_qty': 1,
                    'total_amount': total_amount,
                    'price_unit': total_amount,
                }
                if requisition.purchase_plan_id:
                    line_vals['purchase_plan_id'] = requisition.purchase_plan_id.id
                if requisition.purchase_plan_line_id:
                    line_vals['purchase_plan_line_id'] = requisition.purchase_plan_line_id.id
                RequisitionLine.create(line_vals)
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
