# -*- coding: utf-8 -*-

{
    'name': 'Stock Valuation Layer Date Change',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Change date for selected stock valuation layers',
    'depends': ['stock_account'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_valuation_layer_date_change_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
