{
    'name': 'Account Kveba',
    'version': '18.0.1.1.0',
    'depends': ['account', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'views/generate_kveba_wizard_views.xml',
        'views/account_move_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}