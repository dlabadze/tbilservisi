{
    'name': 'Global List View Customizations',
    'version': '1.0',
    'category': 'Hidden/Tools',
    'summary': 'Wraps text in list views and makes headers/columns sticky',
    'description': """
This module globally tweaks Odoo list (tree) views:
- Allows text to wrap into multiple lines (prevents truncation with ellipsis).
- Keeps the table column headers sticky at the top when scrolling through many lines.
- Lets a list opt in (via class="o_sticky_cols_2" on the <list>) to freeze its
  first two columns while scrolling horizontally.
    """,
    'author': 'FMG',
    'website': '',
    'depends': ['web'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'fmg_list_view_custom/static/src/scss/list_view_custom.scss',
            'fmg_list_view_custom/static/src/js/sticky_columns.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
