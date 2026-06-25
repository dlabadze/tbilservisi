{
    'name': "Kveba Account Moves",
    'version': '1.0',
    'depends': ['account', 'account_kveba', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'views/kveba_account_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}