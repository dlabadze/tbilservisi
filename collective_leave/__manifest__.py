{
    'name': 'Collective Leave',
    'version': '1.0',
    'depends': ['hr','approvals'],
    'data': [
        'security/ir.model.access.csv',
        'views/collective_leave_views.xml',
        'views/collective_change_position_views.xml',
        'views/collective_danishvna_views.xml',
        'views/menus.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}