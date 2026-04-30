# -*- coding: utf-8 -*-
{
    'name': 'Employee Fields Update Import',
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Update employee float fields from Excel',
    'depends': [
        'import_employee_phone_number',
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/employee_fields_update_wizard_views.xml',
        'views/employee_fields_update_menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
