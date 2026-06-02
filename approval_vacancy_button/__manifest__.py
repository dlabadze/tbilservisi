{
    'name': 'Approval Job Vacancy Count',
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'depends': [
        'approvals',
        'hr_approval_mod',
        'employee_vacancy_info',
    ],
    'data': [
        'views/approval_request_vacancy_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
