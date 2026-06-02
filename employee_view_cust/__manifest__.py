{
    'name': 'Employee View Customization',
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Custom employee form view',
    'depends': ['hr'],
    'data': [
        'views/employee_form_custom_view.xml',
        'views/list_view_first.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}