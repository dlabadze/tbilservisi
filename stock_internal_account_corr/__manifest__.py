# -*- coding: utf-8 -*-
{
    'name': 'Stock Internal Transfer Account Correction',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Use selected accounts as debit accounts on internal stock accounting entries',
    'description': """
Stock Internal Transfer Account Correction
==========================================
This module lets users choose debit correction accounts on internal stock
operations and applies them directly to the stock accounting entries.
    """,
    'depends': ['stock_account', 'account', 'analytic'],
    'data': [
        'views/stock_picking_views.xml',
        'views/stock_move_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
