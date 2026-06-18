{
    'name': 'Batch Payslip Department Selection',
    'version': '1.1.0',
    'summary': 'Select child departments and skip employees who would get a blank payslip',
    'description': """
Batch Payslip Department Selection
==================================

Adds to the "Generate Payslips" wizard:

* Selection of specific child departments.
* When a Salary Structure is chosen, employees who would get a BLANK payslip
  (no salary-rule conditions are met for them) are removed from the selection,
  so Generate only ever creates real payslips. The check reads the structure's
  rules in memory - no trial payslip is created and no payslip number is used.
""",
    'category': 'Human Resources/Payroll',
    'author': 'Your Company',
    'license': 'LGPL-3',

    'depends': [
        'hr',
        'hr_payroll',   # ENTERPRISE payroll (required)
    ],

    'data': [
        'views/batch_payslip_modification_view.xml',
    ],

    'installable': True,
    'application': False,
}