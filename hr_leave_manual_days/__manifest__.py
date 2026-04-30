{
    'name': 'HR Leave Manual Days Override',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Time Off',
    'summary': 'Manually override the number of days for leave requests',
    'depends': ['hr_holidays'],
    'data': [
        'views/hr_leave_views.xml',
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
}
