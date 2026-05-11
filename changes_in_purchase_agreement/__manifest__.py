{
    'name': 'Changes in Purchase Agreement',
    'version': '18.0.1.0.0',
    'category': 'Uncategorized',
    'depends': ['base', 'purchase', 'purchase_requisition', 'tbili_budget', 'hr'],
    'external_dependencies': {
        'python': ['pandas', 'openpyxl'],
    },
    'data': [
        'security/ir.model.access.csv',
        'wizard/import_purchase_requisition_wizard_views.xml',
        'views/purchase_requistion_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}