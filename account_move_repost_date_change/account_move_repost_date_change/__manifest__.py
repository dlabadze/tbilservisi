# -*- coding: utf-8 -*-

{
    'name': 'Account Move Repost Date Change',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Reset posted journal entries to draft and repost them with a new date',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_move_repost_date_change_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
