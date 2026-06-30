{
    'name': 'Approval Category Fields Visibility',
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'depends': [
        'approvals',
        'approval_vacancy_button',
        'web_studio',
        'hr_approval_mod',
    ],
    'data': [
        'views/approval_request_view.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
