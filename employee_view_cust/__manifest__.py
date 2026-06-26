{
    'name': 'Employee View Customization',
    'version': '18.0.1.0.0',
    'category': 'Human Resources',
    'summary': 'Custom employee form view',
    'depends': ['hr', 'custom_age_work_experience', 'web_studio', 'hr_attendance', 'hr_holidays','hr_employee_studio_restrict'],
    'data': [
        'views/employee_form_custom_view.xml',
        'views/list_view_first.xml',
        'views/hr_list_view.xml',
        'views/hr_search_view.xml',
        'views/hr_attendance_holidays_tree.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}