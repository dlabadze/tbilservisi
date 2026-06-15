{
    'name': 'Employee Field Tracking',
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'depends': [
        'hr',
        'web_studio',
        'asset_movement'
    ],
    'data': [
        'views/hr_job_view.xml',
        'views/asset_movement_form_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
