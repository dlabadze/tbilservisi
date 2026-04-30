{
    'name': 'Purchase Requisition Move Payment',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'depends': ['base', 'account', 'web', 'account_accountant', 'purchase_requisition', 'tbili_budget', 'xazina_application'],
    'data': [
        'security/ir.model.access.csv',
        'views/purchase_requisition_payment_wizard_view.xml',
        'views/xazina_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'purchase_requisition_move_payment/static/src/js/purchase_requisition_button.js',
            'purchase_requisition_move_payment/static/src/xml/purchase_requisition_button.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
