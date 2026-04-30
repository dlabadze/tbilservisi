{
    'name': 'Employee ID Duplicate Check',
    'version': '18.0.1.0.0',
    'summary': 'Checks for duplicate identification_id in archived employees',
    'category': 'Human Resources/Employees',
    'author': 'Antigravity',
    'depends': ['hr'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/hr_employee_duplicate_wizard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hr_employee_id_duplicate/static/src/js/redirect_interceptor.js',
            'hr_employee_id_duplicate/static/src/xml/dialog_templates.xml',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
