{
    'name': 'Global List View Customizations',
    'version': '1.0',
    'category': 'Hidden/Tools',
    'summary': 'Wraps text in list views and makes headers sticky',
    'description': """
This module globally tweaks Odoo list (tree) views:
- Allows text to wrap into multiple lines (prevents truncation with ellipsis).
- Keeps the table column headers sticky at the top when scrolling through many lines.
    """,
    'author': 'FMG',
    'website': '',
    'depends': ['web'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'fmg_list_view_custom/static/src/scss/list_view_custom.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
