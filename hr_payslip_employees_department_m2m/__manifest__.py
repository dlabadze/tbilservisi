# -*- coding: utf-8 -*-
{
    'name': 'Payslip by Employees — Multi Departments',
    'version': '18.0.1.0.1',
    'summary': 'Department tags on the generate-payslips wizard; includes archived employees with a contract in the batch period.',
    'category': 'Human Resources',
    'depends': ['hr_payroll'],
    'data': [
        'views/hr_payslip_by_employees_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
