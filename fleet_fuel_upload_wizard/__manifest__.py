# -*- coding: utf-8 -*-
{
	'name': 'Fleet Fuel Upload Wizard',
	'summary': 'Adds an Action to upload fuel data via wizard for Fleet Fuel Logs',
	'version': '18.0.1.0.0',
	'category': 'Fleet',
	'author': 'dvsport',
	'license': 'LGPL-3',
	'depends': ['base', 'fleet', 'fleet_vehicle_log_fuel'],
	'data': [
		'security/ir.model.access.csv',
		'views/fleet_fuel_upload_views.xml',
		'views/fleet_fuel_upload_list_inherit.xml',
	],
	'assets': {
		'web.assets_backend': [
			'fleet_fuel_upload_wizard/static/src/js/import_button.js',
			'fleet_fuel_upload_wizard/static/src/xml/import_button.xml',
		],
	},
	'installable': True,
	'application': False,
}
