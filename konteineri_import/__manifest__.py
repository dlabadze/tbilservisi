{
    'name': 'Attendance API Import',
    'version': '1.0',
    'category': 'Human Resources',
    'summary': 'Import attendance from external API',
    'description': 'Imports hr.attendance from external API using privateNumber',
    'depends': [
        'hr',
        'hr_attendance',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/attendance_import_cron.xml',      # ✅ REQUIRED
        'views/import_attendance_wizard_view.xml',
        'views/attendance_import_job_view.xml',
    ],
    'installable': True,
    'application': False,
}
