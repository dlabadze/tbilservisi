{
    'name': 'Product Auto Code',
    'version': '1.0',
    'category': 'Inventory',
    'summary': 'Auto-generate numeric internal reference codes for products',
    'depends': ['product', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_template_view.xml',
        'views/product_product_view.xml',
        'views/stock_limit_report_views.xml',
    ],
    'installable': True,
    'application': False,
}
