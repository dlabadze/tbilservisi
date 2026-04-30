{
    'name': 'Repair Order Picking Auto-Fill',
    'version': '1.0',
    'category': 'Repair',
    'summary': 'Auto-fill repair add/remove lines from stock picking lines',
    'depends': ['repair', 'stock'],
    'data': [
        'views/repair_order_mod_view.xml',
        #'views/res_users_mod_view.xml',
        'views/stock_picking_type_mod_view.xml',
    ],
    'installable': True,
    'application': False,
}