{
    'name': 'Invoice Number Field',
    'version': '18.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Add Invoice Number field to Account Move Lines',
    'description': """
        This module adds a get_invoice_id field to account.move.line
        to display the invoice number in move line views.
    """,
    'author': 'Tbilservisi',
    'depends': ['account', 'extension_views', 'factura_num'],
    'data': [
        'views/account_move_line_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

