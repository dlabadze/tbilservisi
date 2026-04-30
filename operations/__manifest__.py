{
    'name': "ოპერაციები",
    'summary': "დასაქმებულების ოპერაციები: კონტრაქტი, ხელფასი, პოზიცია და სხვა",
    'description': """
ეს მოდული განკუთვნილია დასაქმებულების ოპერაციებისთვის:
 - კონტრაქტების მართვა
 - ხელფასის ინფორმაცია
 - პოზიციები და სამუშაო სტატუსი
    """,
    'category': 'Human Resources',
    'version': '1.0',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'hr',
        'hr_contract',
        'hr_payroll',
    ],

    'data': [
        'security/ir.model.access.csv',
        'views/operations_menu.xml',
        'views/employee_operations_views.xml',
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
}
