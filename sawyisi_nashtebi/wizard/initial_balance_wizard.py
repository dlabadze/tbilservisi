import base64
from io import BytesIO
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import openpyxl
import logging

_logger = logging.getLogger(__name__)


class InitialBalanceWizard(models.TransientModel):
    _name = 'initial.balance.wizard'
    _description = 'Initial Balance Wizard'

    excel_file = fields.Binary('Excel File', required=True)
    excel_filename = fields.Char('Excel File Name')

    def action_import_initial_balance(self):
        self.ensure_one()
        
        if not self.excel_file:
            raise UserError(_("Please upload an Excel file."))
        
        # Fixed date: December 31, 2025
        move_date = fields.Date.from_string('2025-12-31')
        
        # Search for journal by name
        journal = self.env['account.journal'].sudo().search([('name', '=', 'Opening Entries Journal')], limit=1)
        if not journal:
            raise UserError(_("Journal 'Opening Entries Journal' not found. Please create it first."))
        
        # Decode the file
        try:
            file_data = base64.b64decode(self.excel_file)
            file_stream = BytesIO(file_data)
        except Exception as e:
            raise UserError(_("Error decoding Excel file: %s") % str(e))

        # Load excel
        try:
            workbook = openpyxl.load_workbook(file_stream, data_only=True, read_only=True)
            sheet = workbook.active
            max_row = sheet.max_row
        except Exception as e:
            raise UserError(_("Error loading Excel file. Please make sure it's a valid Excel file (.xlsx): %s") % str(e))
        
        _logger.info(f"Starting import of {max_row - 1} rows...")
        
        # Pre-load all accounts (batch operation for performance)
        _logger.info("Pre-loading accounts...")
        all_accounts = self.env['account.account'].sudo().search([])
        accounts_by_code = {acc.code: acc for acc in all_accounts}
        _logger.info(f"Loaded {len(accounts_by_code)} accounts")
        
        # Pre-load all partners (batch operation for performance)
        _logger.info("Pre-loading partners...")
        all_partners = self.env['res.partner'].sudo().search([])
        partners_by_vat = {}
        partners_by_name = {}
        
        for partner in all_partners:
            if partner.vat:
                partners_by_vat[partner.vat] = partner
            if partner.name:
                # Store normalized name for case-insensitive matching
                partners_by_name[partner.name.lower().strip()] = partner
        
        _logger.info(f"Loaded {len(all_partners)} partners ({len(partners_by_vat)} with VAT)")
        
        # Prepare move lines
        move_lines = []
        errors = []
        processed_count = 0
        
        # Read all rows at once for better performance
        _logger.info("Reading Excel rows...")
        rows_data = []
        for row_num in range(2, max_row + 1):
            rows_data.append({
                'row_num': row_num,
                'account_code': sheet[f'A{row_num}'].value,
                'identification_id': sheet[f'B{row_num}'].value,
                'partner_name': sheet[f'C{row_num}'].value,
                'amount': sheet[f'D{row_num}'].value,
            })
        
        workbook.close()
        _logger.info(f"Read {len(rows_data)} rows from Excel")
        
        # Process all rows
        _logger.info("Processing rows...")
        for row_data in rows_data:
            row_num = row_data['row_num']
            account_code = row_data['account_code']
            identification_id = row_data['identification_id']
            partner_name = row_data['partner_name']
            amount_cell = row_data['amount']
            
            # Skip empty rows
            if not account_code or not amount_cell:
                continue
            
            # Clean account code
            account_code = str(account_code).strip()
            
            # Parse amount
            try:
                amount = float(amount_cell)
            except (ValueError, TypeError):
                errors.append(f"Row {row_num}: Invalid amount '{amount_cell}'")
                continue
            
            if amount == 0:
                continue
            
            # Find account from pre-loaded dictionary (no database query!)
            account = accounts_by_code.get(account_code)
            if not account:
                errors.append(f"Row {row_num}: Account '{account_code}' not found")
                continue
            
            # Determine debit/credit based on account code
            debit = 0.0
            credit = 0.0
            
            if account_code.startswith('14') or account_code == "9999.02":
                debit = amount
            elif account_code in ["9999.01", "3121", "3280"] or account_code.startswith('31'):
                credit = amount
            else:
                # Default: if amount is positive, debit; if negative, credit
                if amount > 0:
                    debit = amount
                else:
                    credit = abs(amount)
            
            # Find partner from pre-loaded dictionaries (no database query!)
            partner = False
            identification_id_clean = None
            
            if identification_id:
                # Clean identification_id
                identification_id_str = str(identification_id).strip()
                
                # If contains ".", keep only left part
                if '.' in identification_id_str:
                    identification_id_str = identification_id_str.split('.')[0]
                
                # Remove any non-digit characters (no padding)
                identification_id_clean = ''.join(filter(str.isdigit, identification_id_str))
                
                if identification_id_clean:
                    # Search partner by VAT in pre-loaded dictionary
                    partner = partners_by_vat.get(identification_id_clean)
            
            # If partner not found by VAT, try by name
            if not partner and partner_name:
                partner_name_str = str(partner_name).strip().lower()
                if partner_name_str:
                    # Search in pre-loaded dictionary
                    partner = partners_by_name.get(partner_name_str)
            
            # If partner still not found, create new partner
            if not partner and (identification_id_clean or partner_name):
                # Before creating, do a final database check to avoid duplicates
                # Check by VAT first
                if identification_id_clean:
                    partner = self.env['res.partner'].sudo().search([('vat', '=', identification_id_clean)], limit=1)
                    if partner:
                        # Found in database, add to cache for future lookups
                        partners_by_vat[identification_id_clean] = partner
                        if partner.name:
                            partners_by_name[partner.name.lower().strip()] = partner
                
                # Check by exact name match if still not found
                if not partner and partner_name:
                    partner_name_clean = str(partner_name).strip()
                    partner = self.env['res.partner'].sudo().search([('name', '=', partner_name_clean)], limit=1)
                    if partner:
                        # Found in database, add to cache for future lookups
                        if identification_id_clean:
                            partners_by_vat[identification_id_clean] = partner
                        partners_by_name[partner_name_clean.lower()] = partner
                
                # Only create if really not found
                if not partner:
                    partner_vals = {}
                    
                    # Set partner name
                    if partner_name:
                        partner_vals['name'] = str(partner_name).strip()
                    elif identification_id_clean:
                        partner_vals['name'] = identification_id_clean
                    else:
                        partner_vals['name'] = f'Partner Row {row_num}'
                    
                    # Check if name starts with company prefixes
                    company_prefixes = ["შპს ", "ააიპ ", "სს ", "იმ "]
                    is_company = any(partner_vals['name'].startswith(prefix) for prefix in company_prefixes)
                    
                    if is_company:
                        partner_vals['is_company'] = True
                        partner_vals['company_type'] = 'company'
                    
                    # Set VAT if available
                    if identification_id_clean:
                        partner_vals['vat'] = identification_id_clean
                    
                    # Create the partner
                    try:
                        partner = self.env['res.partner'].sudo().create(partner_vals)
                        
                        # Add to dictionaries for future lookups in same import
                        if identification_id_clean:
                            partners_by_vat[identification_id_clean] = partner
                        if partner.name:
                            partners_by_name[partner.name.lower().strip()] = partner
                        
                        _logger.info(f"Row {row_num}: Created new partner '{partner.name}' (VAT: {identification_id_clean or 'N/A'})")
                    except Exception as e:
                        _logger.warning(f"Row {row_num}: Could not create partner: {e}")
                        partner = False
            
            # Prepare line name
            line_name = f'{account_code}'
            if partner:
                line_name += f' - {partner.name}'
            elif partner_name:
                line_name += f' - {partner_name}'
            
            # Create move line
            line_vals = {
                'account_id': account.id,
                'name': line_name,
                'debit': debit,
                'credit': credit,
            }
            
            # Add partner if found
            if partner:
                line_vals['partner_id'] = partner.id
            
            move_lines.append((0, 0, line_vals))
            processed_count += 1
            
            # Log progress every 500 rows
            if processed_count % 500 == 0:
                _logger.info(f"Processed {processed_count} lines...")
        
        _logger.info(f"Finished processing. Total lines: {processed_count}")
        
        # Show errors if any
        if errors:
            error_message = "\n".join(errors[:50])  # Show only first 50 errors
            if len(errors) > 50:
                error_message += f"\n\n... and {len(errors) - 50} more errors"
            raise UserError(_("Errors found during import:\n\n%s") % error_message)
        
        # Calculate totals to check if balanced
        if move_lines:
            total_debit = sum(line[2].get('debit', 0) for line in move_lines)
            total_credit = sum(line[2].get('credit', 0) for line in move_lines)
            difference = total_debit - total_credit
            
            _logger.info(f"Total Debit: {total_debit:.2f}")
            _logger.info(f"Total Credit: {total_credit:.2f}")
            _logger.info(f"Difference: {difference:.2f}")
            
            # Check if balanced
            if abs(difference) > 0.01:  # Allow 0.01 difference for rounding
                raise UserError(_(
                    "The journal entry is not balanced!\n\n"
                    "Total Debit: %.2f\n"
                    "Total Credit: %.2f\n"
                    "Difference: %.2f\n\n"
                    "Please check your Excel file. The sum of all debits must equal the sum of all credits."
                ) % (total_debit, total_credit, difference))
            
            _logger.info(f"Creating journal entry with {len(move_lines)} lines...")
            
            try:
                move = self.env['account.move'].sudo().create({
                    'move_type': 'entry',
                    'date': move_date,
                    'journal_id': journal.id,
                    'ref': 'საწყისი ნაშთები',
                    'line_ids': move_lines,
                })
                
                _logger.info(f"Journal entry created successfully: {move.name}")
            except Exception as e:
                _logger.error(f"Error creating journal entry: {e}")
                raise UserError(_(
                    "Error creating journal entry:\n\n%s\n\n"
                    "Total lines: %d\n"
                    "Total Debit: %.2f\n"
                    "Total Credit: %.2f"
                ) % (str(e), len(move_lines), total_debit, total_credit))
            
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'res_id': move.id,
                'view_mode': 'form',
                'target': 'current',
            }
        else:
            raise UserError(_("No valid data found in Excel file"))

