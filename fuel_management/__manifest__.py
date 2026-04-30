{
	'name': 'Fuel Management',
	'version': '18.0.1.0.0',
	'category': 'Operations/Fleet',
	'summary': 'Fuel management records with departments and vehicles',
	'description': 'Custom module to manage fuel usage linked to departments and fleet vehicles.',
	'author': 'Custom',
	'website': 'https://example.com',
	'license': 'LGPL-3',
	'depends': ['base', 'hr', 'fleet', 'stock', 'product', 'mail'],
	'data': [
		'security/ir.model.access.csv',
		'views/fuel_management_views.xml',
		'views/fleet_vehicle_inherit_views.xml',
		'wizard/fuel_date_wizard_views.xml',
		'wizard/recalc_balances_wizard_views.xml',
	],
	'assets': {
		'web.assets_backend': [
			'fuel_management/static/src/css/list_fixes.css',
			'fuel_management/static/src/js/date_filter_button.js',
			'fuel_management/static/src/xml/date_filter_button.xml',
		],
		'web.assets_qweb': [
			'fuel_management/static/src/xml/date_filter_button.xml',
		],
	},
	'installable': True,
	'application': True,
}


