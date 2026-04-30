{
    'name': 'Attendance Report',
    'version': '18.0.1.0.0',
    'depends': ['hr', 'hr_attendance'],
    'data': [
        'security/ir.model.access.csv',
        'views/paperformat.xml',
        'views/attendance_report.xml',
        'wizard/attendance_report_wizard_views.xml',
        'wizard/menu.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
