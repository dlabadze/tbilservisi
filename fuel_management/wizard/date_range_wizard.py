from odoo import api, fields, models


class FuelManagementDateWizard(models.TransientModel):
	_name = 'fuel.management.date.wizard'
	_description = 'Fuel Management Date Range Wizard'

	date_from = fields.Datetime(string='საწყისი თარიღი')
	date_to = fields.Datetime(string='საბოლოო თარიღი')

	def action_open_records(self):
		self.ensure_one()
		domain = []
		if self.date_from:
			domain.append(('date', '>=', self.date_from))
		if self.date_to:
			domain.append(('date', '<=', self.date_to))
		return {
			'type': 'ir.actions.act_window',
			'name': 'Fuel Management',
			'res_model': 'fuel.management',
			'view_mode': 'list,form',
			'domain': domain,
			'target': 'current',
			'context': dict(self.env.context),
		}


