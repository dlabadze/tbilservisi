{
    'name': 'Partner Car Registration',
    'version': '1.0.0',
    'summary': 'Register cars for partners with VAT and name information',
    'description': '''
        Partner Car Registration Module
        ================================
        Allows registering car numbers for partners:
        - Select partner (res.partner)
        - Displays partner VAT and name
        - Enter car number (Car_Nom)
    ''',
    'author': 'Your Company',
    'depends': ['base', 'contacts'],
    'data': [
        'security/ir.model.access.csv',
        'views/partner_car_views.xml',
    ],
    'installable': True,
    'application': False,
}
