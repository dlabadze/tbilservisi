{
    'name': 'Update Departments In Contract',
    'version': '18.0.1.0.0',
    'depends': ['hr_contract'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/update_contract_department_wizard_views.xml',
        'views/hr_contract_views.xml',
    ],
    'installable': True,
    'application': False,
}