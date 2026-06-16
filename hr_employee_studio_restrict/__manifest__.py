{
    'name': 'HR Employee Studio Field Restrict',
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'license': 'LGPL-3',
    'depends': ['hr', 'web_studio','partner_employee_pen', 'employee_field_tracking'],
    'data': [
        'security/hr_employee_security.xml',
        'security/ir.model.access.csv',
        'views/hr_employee_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
