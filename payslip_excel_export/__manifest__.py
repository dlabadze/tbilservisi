{
    'name': 'Payslip Excel Export',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Export payslips to Excel with attendance day-type counts',
    'depends': [
        'hr_payroll',
        'hr_attendance',
        'hr_work_entry_contract_enterprise',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/payslip_excel_export_wizard_view.xml',
        'views/payslip_excel_export_menu.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
