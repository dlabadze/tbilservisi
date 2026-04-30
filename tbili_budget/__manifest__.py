{
    'name': 'Tbilisi Budget - Purchase Management',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Purchase-focused Budget Planning for Tbilisi',
    'description': """
Tbilisi Budget - Purchase Management
====================================
This module provides purchase-focused budget planning capabilities:
- Budget tracking
- CPV code management
- Purchase procurement planning
- Integration with purchase orders
- Analytic accounting support
- Purchase requisition management

Note: This is a purchase-focused variant without inventory request functionality.
""",
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'account',
        'analytic',
        'account_budget',
        'base',
        'website',
        'purchase_requisition',
        'web_studio',
        'stock',
        'purchase_stock'
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/purchase_plan_tags.xml',
        'views/budget_views.xml',
        'views/account_analytic_views.xml',
        'views/purchase_plans.xml',
        'views/visual_report_template.xml',
    ],
    'assets': {
        'web.assets_backend': [
            '/tbili_budget/static/src/js/main.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',

}