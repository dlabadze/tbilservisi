{
    'name': 'HR Employee Studio Field Restrict',
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'license': 'LGPL-3',
    'depends': ['hr', 'web_studio'],
    'data': [
        'security/hr_employee_security.xml',
        'views/hr_employee_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
