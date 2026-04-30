from odoo import api, fields, models, _
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)


class FuelManagement(models.Model):
	_inherit = 'fuel.management'

	# Computed from vehicle_id: newest log_driver (by id) sets employee_id, department_id, parent_department_id
	employee_id = fields.Many2one(
		'hr.employee',
		string='თანამშრომელი',
		compute='_compute_from_vehicle_log_driver',
		store=True,
		readonly=False,
	)
	department_id = fields.Many2one(
		'hr.department',
		string='სამსახური',
		compute='_compute_from_vehicle_log_driver',
		store=True,
		readonly=False,
	)
	parent_department_id = fields.Many2one(
		'hr.department',
		string='დეპარტამენტი',
		compute='_compute_from_vehicle_log_driver',
		store=True,
		readonly=False,
	)

	picking_id = fields.Many2one('stock.picking', string='Stock Picking', readonly=True)
	fuel_product_id = fields.Many2one('product.product', string='Fuel Product', required=False)
	journal_entry_ids = fields.One2many(
		'account.move',
		'fuel_management_id',
		string='Journal Entries',
		readonly=True,
	)
	# writeoff_location_id = fields.Many2one('stock.location', string='Write-off Location', required=False)

	@api.depends('vehicle_id', 'vehicle_id.log_drivers', 'vehicle_id.log_drivers.driver_employee_id', 'vehicle_id.log_drivers.sub_department_id', 'vehicle_id.log_drivers.department_id')
	def _compute_from_vehicle_log_driver(self):
		"""From vehicle_id get log_drivers, sort newest (highest id); set department_id=sub_department_id, parent_department_id=department_id, employee_id=driver_employee_id."""
		for rec in self:
			if not rec.vehicle_id or 'log_drivers' not in rec.vehicle_id._fields:
				rec.employee_id = False
				rec.department_id = False
				rec.parent_department_id = False
				continue
			log_drivers = rec.vehicle_id.log_drivers.sorted(key=lambda r: r.id, reverse=True)
			if not log_drivers:
				rec.employee_id = False
				rec.department_id = False
				rec.parent_department_id = False
				continue
			newest = log_drivers[0]
			rec.employee_id = newest.driver_employee_id if hasattr(newest, 'driver_employee_id') and newest.driver_employee_id else False
			rec.department_id = newest.sub_department_id if hasattr(newest, 'sub_department_id') and newest.sub_department_id else False
			rec.parent_department_id = newest.department_id if hasattr(newest, 'department_id') and newest.department_id else False

	def unlink(self):
		"""Prevent deletion of records that have a linked stock picking"""
		for record in self:
			if record.picking_id:
				raise UserError(_(
					'Cannot delete fuel management record (ID: %s) because it has a linked stock picking. '
					'Please delete or unlink the stock picking first.'
				) % record.id)
		return super(FuelManagement, self).unlink()

	def action_view_picking(self):
		"""Open the related stock.picking form view"""
		self.ensure_one()
		if not self.picking_id:
			return {
				'type': 'ir.actions.client',
				'tag': 'display_notification',
				'params': {
					'title': _('Warning'),
					'message': _('No stock picking linked to this record.'),
					'type': 'warning',
				}
			}
		return {
			'type': 'ir.actions.act_window',
			'name': _('Stock Picking'),
			'res_model': 'stock.picking',
			'res_id': self.picking_id.id,
			'view_mode': 'form',
			'target': 'current',
		}

	def action_view_journal_entries(self):
		"""Open list view of account.move filtered by fuel_management_id"""
		self.ensure_one()
		return {
			'type': 'ir.actions.act_window',
			'name': _('Journal Entries'),
			'res_model': 'account.move',
			'view_mode': 'list,form',
			'domain': [('fuel_management_id', '=', self.id)],
			'target': 'current',
		}

	def action_create_fuel_writeoff(self):
		"""
		Create a separate stock.picking record for fuel write-off (საწვავის ჩამოწერა)
		for each selected record
		"""
		# Validate all selected records
		errors = []
		for record in self:
			if record.picking_id:
				errors.append(_('Record ID %s already has a stock picking created.') % record.id)
			if not record.fuel_product_id:
				errors.append(_('Record ID %s: Please select a fuel product.') % record.id)
			if not record.writeoff_location_id:
				errors.append(_('Record ID %s: Please configure write-off location.') % record.id)
			if not record.consumed_qty or record.consumed_qty <= 0:
				errors.append(_('Record ID %s: Consumed quantity must be greater than zero.') % record.id)
		
		if errors:
			raise UserError('\n'.join(errors))

		# Get the stock picking type for internal transfers
		picking_type = self.env['stock.picking.type'].search([
			('code', '=', 'internal'),
			('warehouse_id', '!=', False)
		], limit=1)

		if not picking_type:
			raise UserError(_('No internal picking type found. Please configure stock operations first.'))

		# Use picking type's default source location
		if not picking_type.default_location_src_id:
			raise UserError(_('Please configure default source location for the picking type.'))
		
		source_location = picking_type.default_location_src_id
		
		# Create a separate stock picking for each selected record
		created_pickings = self.env['stock.picking']
		
		for record in self:
			# Build description: department_id.display_name | vehicle_id.display_name
			description_parts = []
			if record.department_id:
				description_parts.append(record.department_id.display_name)
			if record.vehicle_id:
				description_parts.append(record.vehicle_id.display_name)
			description = ' | '.join(description_parts) if description_parts else record.fuel_product_id.name
			
			# Create individual stock picking for this record
			chamoweris_sawyobi = self.env['stock.location'].search([
				('name', '=', 'ჩამოწერის საწყობი')], limit=1)
			picking_vals = {
				'picking_type_id': picking_type.id,
				'location_id': record.writeoff_location_id.id,
				'location_dest_id': chamoweris_sawyobi.id,
				'origin': f'Fuel Management: {record.id}',
				'scheduled_date': record.date,
				'date_of_transfer': record.date,
			}

			picking = self.env['stock.picking'].create(picking_vals)
			created_pickings |= picking
			
			# Create stock.move for this record
			move_vals = {
				'name': description,
				'product_id': record.fuel_product_id.id,
				'product_uom_qty': record.consumed_qty,
				'product_uom': record.fuel_product_id.uom_id.id,
				'picking_id': picking.id,
				'location_id': record.writeoff_location_id.id,
				'location_dest_id': chamoweris_sawyobi.id,
				'description_picking': description,
			}
			
			move = self.env['stock.move'].create(move_vals)
			
			# Link the picking to this fuel management record
			record.picking_id = picking.id
			
			# Confirm the picking
			picking.action_confirm()
			
			# Manually create move line with quantity done to force transfer
			move_line_vals = {
				'move_id': move.id,
				'product_id': record.fuel_product_id.id,
				'product_uom_id': record.fuel_product_id.uom_id.id,
				'location_id': record.writeoff_location_id.id,
				'location_dest_id': chamoweris_sawyobi.id,
				'quantity': record.consumed_qty,
				'picking_id': picking.id,
			}
			self.env['stock.move.line'].create(move_line_vals)
			
		# Validate the picking to set it to done state
		picking.button_validate()
		
		# Set the transfer date after validation
		picking.date_done = record.date
		
		# Update account.move.line names with department and vehicle info
		# Search for account move lines that reference this picking
		account_move_lines = self.env['account.move.line'].search([
			'|', '|',
			('move_id.name', 'ilike', picking.name),
			('move_id.ref', 'ilike', picking.name),
			('move_id.stock_move_id.picking_id', '=', picking.id)
		])
		
		if account_move_lines:
			# Build the suffix: | department_id.display_name | vehicle_id.display_name
			suffix_parts = []
			if record.department_id:
				suffix_parts.append(record.department_id.display_name)
			if record.vehicle_id:
				suffix_parts.append(record.vehicle_id.display_name)
			
			if suffix_parts:
				suffix = ' | ' + ' | '.join(suffix_parts)
				for line in account_move_lines:
					line.name = line.name + suffix

		# Return action to open the created pickings
		if len(created_pickings) == 1:
			# If only one picking created, open it in form view
			return {
				'type': 'ir.actions.act_window',
				'name': _('Stock Picking'),
				'res_model': 'stock.picking',
				'res_id': created_pickings.id,
				'view_mode': 'form',
				'target': 'current',
			}
		else:
			# If multiple pickings created, open them in tree view
			return {
				'type': 'ir.actions.act_window',
				'name': _('Stock Pickings'),
				'res_model': 'stock.picking',
				'domain': [('id', 'in', created_pickings.ids)],
				'view_mode': 'list,form',
				'target': 'current',
			}

	def action_generate_journal_entry(self):
		"""
		Generate journal entry for fuel write-off
		"""
		_logger.info(f"=======action_generate_journal_entry=======")
		_logger.info(f"self: {self}")
		account_1619 = self.env['account.account'].sudo().search([('code', '=', '1619')], limit=1)
		account_3135 = self.env['account.account'].sudo().search([('code', '=', '3135')], limit=1)
		account_3322 = self.env['account.account'].sudo().search([('code', '=', '3322')], limit=1)
		account_3330 = self.env['account.account'].sudo().search([('code', '=', '3330')], limit=1)
		account_7410_11 = self.env['account.account'].sudo().search([('code', '=', '7410.11')], limit=1)
		account_3133_28 = self.env['account.account'].sudo().search([('code', '=', '3133.28')], limit=1)
		account_7452_02_02 = self.env['account.account'].sudo().search([('code', '=', '7452.02.02')], limit=1)
		account_7452_02_01 = self.env['account.account'].sudo().search([('code', '=', '7452.02.01')], limit=1)
		# Analytic distribution from department
		if not all([account_1619, account_3135, account_7452_02_02, account_7452_02_01,  account_3322, account_3330, account_7410_11, account_3133_28]):
			raise UserError(_("Required accounts not found. Please check account codes: 1619, 3135, 7452.02.02, 7452.02.01, 3322, 3330, 7410.11, 3133.28"))

		journal = self.env['account.journal'].sudo().search([('name', '=', 'საწვავი')], limit=1)
		if not journal:
			raise UserError(_("Journal 'საწვავი' is not found"))

		created_moves = self.env['account.move']
		for rec in self:
			account_7452_02 = False
			if rec.x_studio_related_field_2oj_1jhbg5h8s == 'დიზელი':
				account_7452_02 = account_7452_02_02
			elif rec.x_studio_related_field_2oj_1jhbg5h8s == 'ბენზინი':
				account_7452_02 = account_7452_02_01

			if rec.ownership_type != 'იჯარით აღებული':
				continue
			product_id = rec.fuel_product_id
			if not product_id:
				raise UserError(_('No fuel product selected.'))
			vehicle_id = rec.vehicle_id
			drivers = vehicle_id.log_drivers
			driver_list = []
			for driver in drivers:
				if driver.driver_employee_id:
					driver_list.append(driver.driver_employee_id)
			
			employee = driver_list[0] if driver_list else False
			_logger.info(f"employee: {employee}")
			if not employee:
				raise UserError(_('No employee selected.'))
			
			partner = employee.work_contact_id
			if not partner:
				raise UserError(_('No partner selected.'))

			# Analytic distribution from hr.department: use department's analytic account or find by name
			analytic_account = self.env['account.analytic.account']
			if rec.department_id:
				if hasattr(rec.department_id, 'analytic_account_id') and rec.department_id.analytic_account_id:
					analytic_account = rec.department_id.analytic_account_id
				if not analytic_account:
					analytic_account = self.env['account.analytic.account'].search([
						('name', '=', rec.department_id.name)
					], limit=1)
				if not analytic_account and rec.department_id.complete_name:
					analytic_account = self.env['account.analytic.account'].search([
						('name', '=', rec.department_id.complete_name)
					], limit=1)
			analytic_distribution = {str(analytic_account.id): 100.0} if analytic_account else False

			invoice_lines = []
			cost = product_id.standard_price
			quantity = rec.consumed_qty
			base_amount = quantity * cost
			has_pension = hasattr(partner, 'x_studio_') and partner.x_studio_

			 # Line 1: (3132 - 1619) - საწვავი
			invoice_lines.append((0, 0, {
                'account_id': account_3135.id,
                'partner_id': partner.id,
                'name': f'{partner.name}',
                'quantity': quantity,
                'product_id': product_id.id,
                'price_unit': cost,
                'debit': base_amount,
                'credit': 0.0,
            }))

			line_vals_1619 = {
                'account_id': account_1619.id,
                'partner_id': partner.id,
                'name': f'{partner.name}',
                'quantity': quantity,
                'product_id': product_id.id,
                'price_unit': cost,
                'debit': 0.0,
                'credit': base_amount,
            }
			invoice_lines.append((0, 0, line_vals_1619))

			if has_pension:
				ammount_7452_02 = base_amount * 1.505102041
				amount_3322 = base_amount * 0.295
				amount_3330 = base_amount * 0.18
				amount_pension = base_amount * 0.030102041

				# Line 2: 7411 - 3132
				line_7411 = {'account_id': account_7452_02.id, 'name': f'{partner.name}', 'debit': ammount_7452_02, 'credit': 0.0}
				if analytic_distribution:
					line_7411['analytic_distribution'] = analytic_distribution
				invoice_lines.append((0, 0, line_7411))

				invoice_lines.append((0, 0, {
					'account_id': account_3135.id,
					'partner_id': partner.id,
					'name': f'{partner.name}',
					'debit': 0.0,
					'credit': ammount_7452_02,
				}))

				# Line 3: 3132 - 3322
				invoice_lines.append((0, 0, {
					'account_id': account_3135.id,
					'partner_id': partner.id,
					'name': f'{partner.name}',
					'debit': amount_3322,
					'credit': 0.0,
				}))

				invoice_lines.append((0, 0, {
					'account_id': account_3322.id,
					'name': f'{partner.name}',
					'debit': 0.0,
					'credit': amount_3322,
				}))

				# Line 4: 3132 - 3330
				invoice_lines.append((0, 0, {
					'account_id': account_3135.id,
					'partner_id': partner.id,
					'name': f'{partner.name}',
					'debit': amount_3330,
					'credit': 0.0,
				}))

				invoice_lines.append((0, 0, {
					'account_id': account_3330.id,
					'name': f'{partner.name}',
					'debit': 0.0,
					'credit': amount_3330,
				}))

				# Line 5: 7410.11 - 3133.28
				line_7410_11 = {'account_id': account_7410_11.id, 'name': f'{partner.name}', 'debit': amount_pension, 'credit': 0.0}
				if analytic_distribution:
					line_7410_11['analytic_distribution'] = analytic_distribution
				invoice_lines.append((0, 0, line_7410_11))
				
				invoice_lines.append((0, 0, {
					'account_id': account_3133_28.id,
					'partner_id': partner.id,
					'name': f'{partner.name}',
					'debit': 0.0,
					'credit': amount_pension,
				}))

				# Line 6: 3132 - 3133.28
				invoice_lines.append((0, 0, {
					'account_id': account_3135.id,
					'partner_id': partner.id,
					'name': f'{partner.name}',
					'debit': amount_pension,
					'credit': 0.0,
				}))

				invoice_lines.append((0, 0, {
					'account_id': account_3133_28.id,
					'partner_id': partner.id,
					'name': f'{partner.name}',
					'debit': 0.0,
					'credit': amount_pension,
				}))
			else:
				ammount_7452_02 = base_amount * 1.475
				amount_3322 = base_amount * 0.295
				amount_3330 = base_amount * 0.18

				# Line 2: 7411 - 3132
				line_7411_no_pen = {'account_id': account_7452_02.id, 'name': f'{partner.name}', 'debit': ammount_7452_02, 'credit': 0.0}
				if analytic_distribution:
					line_7411_no_pen['analytic_distribution'] = analytic_distribution
				invoice_lines.append((0, 0, line_7411_no_pen))

				invoice_lines.append((0, 0, {
					'account_id': account_3135.id,
					'partner_id': partner.id,
					'name': f'{partner.name}',
					'debit': 0.0,
					'credit': ammount_7452_02,
				}))

				# Line 3: 3132 - 3322
				invoice_lines.append((0, 0, {
					'account_id': account_3135.id,
					'partner_id': partner.id,
					'name': f'{partner.name}',
					'debit': amount_3322,
					'credit': 0.0,
				}))

				invoice_lines.append((0, 0, {
					'account_id': account_3322.id,
					'name': f'{partner.name}',
					'debit': 0.0,
					'credit': amount_3322,
				}))

				# Line 4: 3132 - 3330
				invoice_lines.append((0, 0, {
					'account_id': account_3135.id,
					'partner_id': partner.id,
					'name': f'{partner.name}',
					'debit': amount_3330,
					'credit': 0.0,
				}))

				invoice_lines.append((0, 0, {
					'account_id': account_3330.id,
					'name': f'{partner.name}',
					'debit': 0.0,
					'credit': amount_3330,
				}))
			
			if invoice_lines:
				move_date = self.env.context.get('journal_entry_date') or rec.date
				move = self.env['account.move'].create({
					'move_type': 'entry',
					'journal_id': journal.id,
					'date': move_date,
					'line_ids': invoice_lines,
					'fuel_management_id': rec.id,
				})
				created_moves |= move

		count = len(created_moves)
		if count == 0:
			return {
				'type': 'ir.actions.client',
				'tag': 'display_notification',
				'params': {
					'title': _('Warning'),
					'message': _('No journal entries were created. Selected records may not match criteria (ownership type საკუთარი).'),
					'type': 'warning',
					'sticky': False,
				}
			}
		# Return act_window directly with explicit views to avoid frontend .map() on undefined
		return {
			'type': 'ir.actions.act_window',
			'name': _('Journal Entries'),
			'res_model': 'account.move',
			'domain': [('id', 'in', created_moves.ids)],
			'view_mode': 'list,form',
			'views': [(False, 'list'), (False, 'form')],
			'target': 'current',
		}

	def action_calculate_consumed_qty(self):
		"""
		Calculate consumed quantity for fuel management records
		"""
		for rec in self:
			rec.consumed_qty = rec.start_balance + rec.filled_qty + \
				rec.other_received - rec.other_transferred - rec.final_balance