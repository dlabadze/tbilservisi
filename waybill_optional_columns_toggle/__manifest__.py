{
    'name': 'RS Waybill Optional Columns Toggle',
    'version': '18.0.1.0.0',
    'summary': 'Enable show/hide columns for RS Waybill purchase and sale lists',
    'category': 'Inventory',
    'depends': ['waybill_management_custom'],
    'data': [
        'views/waybill_optional_columns_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
