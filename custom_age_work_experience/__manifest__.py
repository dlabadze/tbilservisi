# -*- coding: utf-8 -*-
{
    'name': 'Extended Employee Details',
    'version': '1.0',
    'category': 'Human Resources',
    'sequence': 10,
    'summary': 'Adds automatic age and work experience calculation',
    'description': """
    This module extends employee records with:
    - Automatic age calculation based on birthdate
    - Automatic work experience calculation based on contracts
    """,
    'author': 'Your Company Name',
    'website': 'https://www.yourcompany.com',
    'depends': ['hr', 'hr_contract'],
    'data': [
        'views/hr_employee_view.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}