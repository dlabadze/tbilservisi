# -*- coding: utf-8 -*-
from odoo import api, SUPERUSER_ID


def post_init_hook(cr, registry):
	env = api.Environment(cr, SUPERUSER_ID, {})
	model_ref = env.ref('fleet_vehicle_log_fuel.model_fleet_vehicle_log_fuel', raise_if_not_found=False)
	if not model_ref:
		return
	# Ensure view exists
	view = env.ref('fleet_fuel_upload_wizard.view_fleet_fuel_upload_wizard_form', raise_if_not_found=False)
	# Find existing action if any to avoid duplicates
	existing = env['ir.actions.act_window'].search([
		('res_model', '=', 'fleet.fuel.upload.wizard'),
		('binding_model_id', '=', model_ref.id),
	])
	if existing:
		return
	vals = {
		'name': 'საწვავების ატვირთვა',
		'res_model': 'fleet.fuel.upload.wizard',
		'view_mode': 'form',
		'target': 'new',
		'binding_model_id': model_ref.id,
	}
	if view:
		vals['view_id'] = view.id
	env['ir.actions.act_window'].create(vals)
