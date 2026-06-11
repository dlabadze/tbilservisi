{
	'name': 'Fuel Management Excel Import',
	'version': '18.0.1.0.0',
	'license': 'LGPL-3',
	'depends': ['fuel_management', 'hr', 'stock', 'account', 'analytic', 'stock_internal_account_corr'],
	'data': [
		'security/ir.model.access.csv',
		'wizard/fuel_excel_upload_wizard_views.xml',
		'wizard/fuel_management_journal_wizard_views.xml',
		'views/fuel_management_views.xml',
	],
	'installable': True,
	'application': False,
	'auto_install': False,
}
