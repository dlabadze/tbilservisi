{
    'name': 'Purchase Order — Purchase Requisition link',
    'version': '18.0.1.0.0',
    'category': 'Purchases',
    'summary': 'შესყიდვის ორდერისა და შესყიდვის მოთხოვნის (Purchase Requisition) კავშირი',
    'depends': ['purchase_requisition'],
    'data': [
        'views/purchase_requisition_views.xml',
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
