{
    'name': 'approval_modification',
    'version': '1.2',
    'summary': 'approval modification',
    'category': 'HR',
    'depends': [
        'base',
        'approvals',
        'hr',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_approval_mod_view.xml',
    ],
    #'sequence': 999,
    'installable': True,
    'application': False,
}
