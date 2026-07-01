# -*- coding: utf-8 -*-
{
    'name': 'HR Employee Excel Field Update',
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Update hr.employee fields from Excel using technical field names',
    'description': 'Upload Excel files to update employee fields by identification_id.',
    'depends': [
        'hr',
        'import_employee_phone_number',
    ],
    'external_dependencies': {
        'python': ['pandas', 'openpyxl'],
    },
    'data': [
        'security/ir.model.access.csv',
        'wizard/hr_employee_excel_field_update_wizard_views.xml',
        'views/menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
