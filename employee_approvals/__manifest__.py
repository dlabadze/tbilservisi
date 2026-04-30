{
    'name': 'Approval In Employee Card',
    'version': '18.0.1.0.0',
    'depends': ['hr','hr_contract','approvals','hr_approval_mod'],
    'data': [
        'views/hr_employee_form_view.xml',
        'views/approval_search_field.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
