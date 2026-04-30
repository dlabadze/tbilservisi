from odoo import api, fields, models


class FuelManagement(models.Model):
	_name = 'fuel.management'
	_description = 'Fuel Management'
	_order = 'date desc, id desc'
	_inherit = ['mail.thread', 'mail.activity.mixin']

	date = fields.Datetime(string='თარიღი', default=fields.Datetime.now, required=True, tracking=True)

	# Parent Department (დეპარტამენტი) - choose among top-level departments by default
	parent_department_id = fields.Many2one(
		'hr.department',
		string='დეპარტამენტი',
	)

	# Child Department (სამსახური) - filtered by the selected parent department
	department_id = fields.Many2one(
		'hr.department',
		string='სამსახური',
	)

	# Employee (თანამშრომელი) - optional
	employee_id = fields.Many2one(
		'hr.employee',
		string='თანამშრომელი',
		tracking=True,
	)

	# Vehicle (სახელმწიფო ნომერი)
	vehicle_id = fields.Many2one(
		'fleet.vehicle',
		string='სახელმწიფო ნომერი',
		tracking=True,
	)

	# Fuel Type (საწვავის ტიპი) - choose product, auto from vehicle Studio field x_studio_product
	fuel_product_id = fields.Many2one(
		'product.product',
		string='საწვავის ტიპი',
		tracking=True,
	)

	# Fuel (საწვავი) - auto fetched from vehicle studio field after choosing the car
	fuel = fields.Char(
		string='საწვავი',
		compute='_compute_fuel',
		store=False,
		tracking=True,
	)

	# Ownership Type (საკუთრეობის ტიპი) - auto from vehicle Studio field
	ownership_type = fields.Char(
		string='საკუთრეობის ტიპი',
		compute='_compute_ownership_type',
		store=False,
		tracking=True,
	)

	# Write-off Location (ჩამოწერის ლოკაცია) - auto from department Studio field
	writeoff_location_id = fields.Many2one(
		'stock.location',
		string='ჩამოწერის ლოკაცია',
		compute='_compute_writeoff_location',
		store=False,
		tracking=True,
	)

	start_balance = fields.Float(string='საწყისი ნაშთი', tracking=True)
	filled_qty = fields.Float(string='ჩასხმული რაოდენობა', tracking=True)
	other_received = fields.Float(string='სხვა მიღებული', tracking=True)
	other_transferred = fields.Float(string='სხვა გადაცემული', tracking=True)
	final_balance = fields.Float(string='საბოლოო ნაშთი', tracking=True)
	consumed_qty = fields.Float(string='გახარჯული რაოდენობა', tracking=True)
	start_odometer = fields.Float(string='საწყისი ოდომეტრის ჩვენება', tracking=True)
	odometer = fields.Float(string='ოდომეტრის ჩვენება', tracking=True)
	monthly_mileage = fields.Float(string='თვის გარბენი', tracking=True)
	worked_hours = fields.Float(string='ნამუშევარი საათი', tracking=True)
	total_worked_hours = fields.Float(string='ჯამური ნამუშევარი საათი', tracking=True)
	start_worked_hours = fields.Float(string='საწყისი ნამუშევარი საათი', tracking=True)

	@api.onchange('vehicle_id')
	def _onchange_vehicle_set_fuel_product(self):
		for record in self:
			product_to_set = False
			vehicle = record.vehicle_id
			field_name = 'x_studio_product'
			if vehicle and field_name in vehicle._fields:
				field_def = vehicle._fields[field_name]
				raw_val = vehicle[field_name]
				# If it's a proper many2one, branch by its comodel
				if field_def.type == 'many2one' and raw_val:
					if field_def.comodel_name == 'product.product':
						product_to_set = raw_val if raw_val.exists() else False
					elif field_def.comodel_name == 'product.template':
						# Use the main variant
						product_to_set = raw_val.product_variant_id if raw_val.exists() else False
				# Fallback: if Studio stored a plain id, try to browse product.product
				elif raw_val:
					try:
						int_id = int(raw_val)
						pp = self.env['product.product'].browse(int_id)
						product_to_set = pp if pp.exists() else False
					except Exception:
						product_to_set = False
			record.fuel_product_id = product_to_set.id if product_to_set else False

	@api.depends('vehicle_id')
	def _compute_fuel(self):
		# Tries common Studio field names and falls back to empty if not present
		possible_field_names = [
			'x_studio_fuel',
			'x_studio_fuel_type',
			'x_studio_sawvavi',
			'x_studio_',
			'x_fuel',
		]
		for record in self:
			value_to_set = False
			vehicle = record.vehicle_id
			if vehicle:
				for field_name in possible_field_names:
					if field_name in vehicle._fields:
						raw_val = vehicle[field_name]
						if raw_val:
							# If Many2one, use display_name; else cast to string
							try:
								# Recordset (Many2one) has display_name
								value_to_set = raw_val.display_name
							except Exception:
								value_to_set = str(raw_val)
							break
			record.fuel = value_to_set

	@api.depends('vehicle_id')
	def _compute_ownership_type(self):
		# Technical name provided by user: x_studio_many2one_field_ak_1j6s6rutr
		target_field = 'x_studio_many2one_field_ak_1j6s6rutr'
		for record in self:
			text_value = False
			vehicle = record.vehicle_id
			if vehicle and target_field in vehicle._fields:
				raw_val = vehicle[target_field]
				if raw_val:
					try:
						text_value = raw_val.display_name
					except Exception:
						text_value = str(raw_val)
			record.ownership_type = text_value

	@api.depends('department_id')
	def _compute_writeoff_location(self):
		# Department Studio field assumed: x_studio_location (likely Many2one to stock.location)
		target_field = 'x_studio_location'
		for record in self:
			location = False
			dept = record.department_id
			if dept and target_field in dept._fields:
				location = dept[target_field] or False
			record.writeoff_location_id = location


