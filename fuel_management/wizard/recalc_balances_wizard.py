from odoo import api, fields, models


class FuelRecalcBalancesWizard(models.TransientModel):
	_name = 'fuel.management.recalc.wizard'
	_description = 'Fuel Management Recalculate Start Values'

	date_from = fields.Datetime(string='საწყისი თარიღი', required=True)
	date_to = fields.Datetime(string='საბოლოო თარიღი', required=True)

	def action_recalculate(self):
		self.ensure_one()
		Fuel = self.env['fuel.management']

		# All records in range
		records_in_range = Fuel.search([
			('date', '>=', self.date_from),
			('date', '<=', self.date_to),
		])
		if not records_in_range:
			return {'type': 'ir.actions.act_window_close'}

		# Process per vehicle
		vehicle_ids = records_in_range.mapped('vehicle_id').ids
		if vehicle_ids:
			for vehicle_id in vehicle_ids:
				vehicle_domain = [('vehicle_id', '=', vehicle_id)]

				# Find last record before date_from for this vehicle
				prev_rec = Fuel.search(vehicle_domain + [('date', '<', self.date_from)], order='date desc, id desc', limit=1)

				# Update all in-range for this vehicle if previous exists
				if prev_rec:
					to_update = records_in_range.filtered(lambda r: r.vehicle_id.id == vehicle_id)
					if to_update:
						values = {}
						if prev_rec.final_balance:
							values['start_balance'] = prev_rec.final_balance
						if prev_rec.odometer:
							values['start_odometer'] = prev_rec.odometer
						if prev_rec.total_worked_hours:
							values['start_worked_hours'] = prev_rec.total_worked_hours
						if values:
							to_update.write(values)

		# Calculate dependent fields for each record in range
		for rec in records_in_range:
			update_vals = {}

			# Consumed quantity
			start_balance = rec.start_balance or 0.0
			filled_qty = rec.filled_qty or 0.0
			other_received = rec.other_received or 0.0
			other_transferred = rec.other_transferred or 0.0
			final_balance = rec.final_balance or 0.0
			consumed = (start_balance + filled_qty + other_received - other_transferred) - final_balance
			if rec.consumed_qty != consumed:
				update_vals['consumed_qty'] = consumed

			# Monthly mileage / odometer interdependency
			start_odo = rec.start_odometer or 0.0
			odo = rec.odometer or 0.0
			month_mileage = rec.monthly_mileage or 0.0
			if (not month_mileage) and odo and start_odo:
				# monthly_mileage = odometer - start_odometer
				update_vals['monthly_mileage'] = odo - start_odo
			elif (not odo) and month_mileage and start_odo:
				# odometer = start_odometer + monthly_mileage
				update_vals['odometer'] = start_odo + month_mileage

			# Worked hours / total worked hours interdependency
			start_hours = rec.start_worked_hours or 0.0
			worked = rec.worked_hours or 0.0
			total_hours = rec.total_worked_hours or 0.0
			if (not worked) and total_hours and start_hours:
				# worked_hours = total_worked_hours - start_worked_hours
				update_vals['worked_hours'] = total_hours - start_hours
			elif (not total_hours) and worked and start_hours:
				# total_worked_hours = start_worked_hours + worked_hours
				update_vals['total_worked_hours'] = start_hours + worked

			if update_vals:
				rec.write(update_vals)

		# Return filtered list view
		return {
			'type': 'ir.actions.act_window',
			'name': 'Fuel Management',
			'res_model': 'fuel.management',
			'view_mode': 'list,form',
			'domain': [('date', '>=', self.date_from), ('date', '<=', self.date_to)],
			'target': 'current',
		}


