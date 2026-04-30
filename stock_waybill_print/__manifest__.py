# -*- coding: utf-8 -*-
{
    'name': 'Stock Waybill Print (Complex)',
    'version': '1.0',
    'category': 'Inventory/Reporting',
    'summary': 'Custom complex Waybill (Zednadebi) report for stock pickings',
    'description': """
        This module adds a new printable report for Stock Pickings (Transfers)
        that matches the complex Georgian Waybill (Sasaqonlo Zednadebi) layout.
        The layout is static for verification purposes.     ....................TbilService...............
    """,
    'author': 'FMG',
    'depends': ['stock'],
    'data': [
        'views/report_waybill.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
