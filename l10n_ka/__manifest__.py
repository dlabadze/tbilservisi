{
    'name': 'Georgia - Translations',
    'version': '18.0.1.0.0',
    'category': 'Localizations/Translations',
    'summary': 'Georgian (ka_GE) translations for Odoo',
    'description': 'Georgian language translations for the Odoo web interface.',
    'author': 'Gazi',
    'website': '',
    'license': 'LGPL-3',
    'depends': [
        'web', 'mail', 'calendar', 'documents', 'documents_spreadsheet', 'spreadsheet_edition',
        'approvals', 'sign', 'base_import',
        'hr_contract', 'hr_holidays', 'hr_attendance', 'hr_maintenance', 'hr_recruitment',
        'hr_work_entry', 'hr_skills', 'hr_contract_sign', 'hr_payroll',
        'hr_work_entry_contract', 'hr_work_entry_contract_enterprise', 'hr_payroll_holidays',
        'web_gantt', 'contacts'
    ],
    'data': [
        'views/mail_activity_schedule_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'l10n_ka/static/src/js/l10n_ka_locale_patch.js',
        ],
    },
    'installable': True,
    'auto_install': False,
}
