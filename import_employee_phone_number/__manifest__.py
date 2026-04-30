# -*- coding: utf-8 -*-
{
    'name': 'Import Employee Phone Number',
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Import employee phone numbers from Excel file',
    'depends': [
        'base',
        'hr',
        'account',
        'hr_payroll',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/employee_phone_import_wizard_views.xml',
        'wizard/insurance_import_wizard_views.xml',
        'wizard/fitpass_import_wizard_views.xml',
        'wizard/account_import_wizard_views.xml',
        'wizard/salary_components_import_wizard_views.xml',
        'wizard/income_benefit_import_wizard_views.xml',
        'views/hr_employee_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

