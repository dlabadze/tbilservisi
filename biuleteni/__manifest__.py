{
    'name': 'Biuleteni',
    'version': '1.0',
    'summary': 'Paid Sick Leave',
    'category': 'HR',
    'depends': ['base', 'hr', 'hr_contract', 'mail'],
    'data': [
        'security/ir.model.access.csv',

        'views/biuleteni_view.xml',
        'views/shvebuleba_view.xml',
        'views/hr_inheritings.xml',
        'views/zeganakveturi_saati_view.xml',
        'views/zeganakveturi_import_wizard_view.xml',
        'views/shvebuleba_generate_wizard_view.xml',

        # Your dakaveba views (NO inherit)
        'views/dakaveba_view.xml',

        # Wizard view (must be here)
        'views/dakaveba_import_wizard_view.xml',

        'views/tserili_view.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'biuleteni/static/src/js/dakaveba_import_button.js',
            'biuleteni/static/src/xml/dakaveba_import_button.xml',
            'biuleteni/static/src/css/biuleteni_lines.css',
        ],
    },
    'sequence': 999,
    'installable': True,
    'application': True,
}
