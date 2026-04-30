{
    'name': 'Location Access Control',
    'version': '18.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Restrict access to locations based on user permissions',
    'description': """
Location Access Control
=======================

This module allows you to restrict user access to specific locations
in Odoo 18 inventory operations (Internal Transfers, Pickings, etc.).

Features:
---------
* Assign allowed locations to users
* Automatic filtering of location fields in Internal Transfers based on user's allowed locations
* Domain restriction for location_id and location_dest_id fields
* Default location selection when user has only one allowed location

Security:
---------
* Users can only select locations they have access to in Internal Transfers
* System/view locations are always visible for navigation purposes

Configuration:
--------------
1. Go to Settings > Users & Companies > Users
2. Select a user
3. In the "Allowed Locations" tab, select the locations the user can access

Note: If a user has no allowed locations assigned, they will see all locations
(backward compatibility). To restrict access, explicitly assign locations.
    """,
    'author': 'DvSport',
    'depends': ['base', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'security/ir.rule.xml',
        'views/res_users_views.xml',
        'views/stock_picking_view.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}

