{
    'name': 'Purchase Order Return Status',
    'version': '18.0.1.0.0',
    'summary': 'Show returned purchase orders in the Purchase order list view',
    'category': 'Purchase',
    'author': 'Custom',
    'depends': ['purchase'],
    'data': [
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
