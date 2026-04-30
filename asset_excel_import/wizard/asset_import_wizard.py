import base64
import io
import logging

import pandas as pd

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AssetImportWizard(models.TransientModel):
    _name = 'asset.import.wizard'
    _description = 'Asset Excel Import Wizard'

    # Step 1 fields
    file_data = fields.Binary("Excel File", required=True)
    file_name = fields.Char("File Name")
    state = fields.Selection([
        ('upload', 'Upload'),
        ('mapping', 'Map Columns'),
    ], default='upload', string="Step")

    # Step 2 fields
    mapping_ids = fields.One2many(
        'asset.import.wizard.mapping', 'wizard_id', string="Column Mappings"
    )

    # ──────────────────────────────────────────────
    # Step 1 → Read Excel columns and go to mapping
    # ──────────────────────────────────────────────
    def action_load_columns(self):
        self.ensure_one()
        if not self.file_data:
            raise UserError("Please upload an Excel file first.")

        data = base64.b64decode(self.file_data)
        df = self._read_excel(data, nrows=0)

        columns = list(df.columns)
        if not columns:
            raise UserError("No columns found in the Excel file.")

        # Remove old mappings and create new ones
        self.mapping_ids.unlink()
        mapping_vals = []
        for idx, col_name in enumerate(columns):
            col_label = str(col_name).strip()
            if not col_label or col_label.lower() == 'nan':
                col_label = f"Column {idx + 1}"
            mapping_vals.append((0, 0, {
                'column_index': idx,
                'column_name': col_label,
            }))

        self.write({
            'state': 'mapping',
            'mapping_ids': mapping_vals,
        })

        return self._reopen_wizard()

    # ──────────────────────────────────────────────
    # Step 2 → Import assets from Excel
    # ──────────────────────────────────────────────
    def action_import(self):
        self.ensure_one()

        # Validate at least one mapping is set
        active_mappings = self.mapping_ids.filtered(lambda m: m.field_id)
        if not active_mappings:
            raise UserError("Please map at least one column to an asset field.")

        # Read full Excel data
        data = base64.b64decode(self.file_data)
        df = self._read_excel(data)

        created = 0
        skipped = []

        for row_idx, row in df.iterrows():
            excel_row_num = row_idx + 2  # +2 because header=row1, data starts row2
            try:
                asset_vals = self._build_asset_vals(row, active_mappings, excel_row_num, skipped)
                if asset_vals is None:
                    continue

                self.env['account.asset'].create(asset_vals)
                created += 1

            except Exception as e:
                _logger.error("Row %s import error: %s", excel_row_num, e)
                skipped.append(f"Row {excel_row_num}: {str(e)}")

        if created == 0:
            raise UserError(
                "No assets were created. Check your Excel data and mappings.\n"
                + "\n".join(skipped[:30])
            )

        # Build result message
        msg = f"Successfully created {created} asset(s)."
        if skipped:
            msg += f"\nSkipped {len(skipped)} row(s):\n" + "\n".join(skipped[:30])

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Import Complete',
                'message': msg,
                'type': 'success' if not skipped else 'warning',
                'sticky': True,
            }
        }

    # ──────────────────────────────────────────────
    # Build vals dict for one asset row
    # ──────────────────────────────────────────────
    def _build_asset_vals(self, row, mappings, excel_row_num, skipped):
        vals = {}
        row_list = row.tolist()

        for mapping in mappings:
            idx = mapping.column_index
            if idx >= len(row_list):
                continue

            raw_value = str(row_list[idx]).strip()
            if not raw_value or raw_value.lower() == 'nan':
                continue

            field_name = mapping.field_id.name
            field_ttype = mapping.field_id.ttype
            match_type = mapping.match_type

            # ── Many2one matching by name ──
            if match_type == 'employee':
                employee = self.env['hr.employee'].search([
                    ('name', '=ilike', raw_value)
                ], limit=1)
                if not employee:
                    skipped.append(
                        f"Row {excel_row_num}: Employee '{raw_value}' not found"
                    )
                    continue
                vals[field_name] = employee.id
                continue

            if match_type == 'department':
                department = self.env['hr.department'].search([
                    ('name', '=ilike', raw_value)
                ], limit=1)
                if not department:
                    skipped.append(
                        f"Row {excel_row_num}: Department '{raw_value}' not found"
                    )
                    continue
                vals[field_name] = department.id
                continue

            # ── Direct value assignment based on field type ──
            if field_ttype in ('float', 'monetary'):
                vals[field_name] = self._to_float(raw_value)
            elif field_ttype == 'integer':
                vals[field_name] = int(self._to_float(raw_value))
            elif field_ttype == 'boolean':
                vals[field_name] = raw_value.lower() in ('true', '1', 'yes')
            elif field_ttype == 'date':
                vals[field_name] = self._parse_date(raw_value)
            elif field_ttype == 'many2one':
                # Generic many2one: search by name in the related model
                related_model = mapping.field_id.relation
                if related_model:
                    record = self.env[related_model].search([
                        ('name', '=ilike', raw_value)
                    ], limit=1)
                    if record:
                        vals[field_name] = record.id
                    else:
                        skipped.append(
                            f"Row {excel_row_num}: '{raw_value}' not found in {related_model}"
                        )
            elif field_ttype == 'selection':
                # Try to match selection value or label
                vals[field_name] = raw_value
            else:
                # char, text, html — assign directly
                vals[field_name] = raw_value

        if not vals:
            return None
        return vals

    # ──────────────────────────────────────────────
    # Go back to upload step
    # ──────────────────────────────────────────────
    def action_back(self):
        self.ensure_one()
        self.write({'state': 'upload'})
        return self._reopen_wizard()

    # ──────────────────────────────────────────────
    # Helper: reopen wizard form
    # ──────────────────────────────────────────────
    def _reopen_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    # ──────────────────────────────────────────────
    # Helper: read Excel (supports .xls and .xlsx)
    # ──────────────────────────────────────────────
    @staticmethod
    def _read_excel(data, nrows=None):
        buf = io.BytesIO(data)
        kwargs = {'header': 0, 'dtype': str}
        if nrows is not None:
            kwargs['nrows'] = nrows
        # Try .xlsx first, fall back to .xls
        try:
            return pd.read_excel(buf, engine='openpyxl', **kwargs)
        except Exception:
            buf.seek(0)
            return pd.read_excel(buf, engine='xlrd', **kwargs)

    # ──────────────────────────────────────────────
    # Helper: safe float
    # ──────────────────────────────────────────────
    @staticmethod
    def _to_float(val):
        try:
            return float(str(val).replace(",", ".").replace(" ", ""))
        except (ValueError, TypeError):
            return 0.0

    # ──────────────────────────────────────────────
    # Helper: parse date
    # ──────────────────────────────────────────────
    @staticmethod
    def _parse_date(val):
        from datetime import datetime
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d.%m.%Y', '%d-%m-%Y'):
            try:
                return datetime.strptime(val, fmt).date()
            except ValueError:
                continue
        return False


class AssetImportWizardMapping(models.TransientModel):
    _name = 'asset.import.wizard.mapping'
    _description = 'Asset Import Column Mapping'

    wizard_id = fields.Many2one('asset.import.wizard', required=True, ondelete='cascade')
    column_index = fields.Integer("Column Index")
    column_name = fields.Char("Excel Column", readonly=True)
    field_id = fields.Many2one(
        'ir.model.fields',
        string="Asset Field",
        domain="[('model', '=', 'account.asset'), ('store', '=', True), "
               "('ttype', 'not in', ['one2many', 'many2many', 'binary'])]",
    )
    match_type = fields.Selection([
        ('direct', 'Direct Value'),
        ('employee', 'Match Employee by Name'),
        ('department', 'Match Department by Name'),
    ], string="Match Type", default='direct')
