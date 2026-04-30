{
    'name': 'Pension Upload',
    'version': '1.0.0',
    'category': 'Human Resources',
    'summary': 'Upload Excel to update employee pension status',
    'depends': [
        'base',
        'hr',
        'import_employee_phone_number', 
        'partner_employee_pen', # I should depend on this because x_studio_pension is likely defined there or used there, actually looking at the file partner_employee_pen/models/hr_employee.py it seems x_studio_pension exists on hr.employee but the syncing logic is there. The user said "x_studio_pension" is the field name. 
        # Wait, if `partner_employee_pen` is where `x_studio_pension` is handled (syncing to partner), I should probably depend on it to ensure field existence if it's not a studio field but defined in python.
        # In `partner_employee_pen/models/hr_employee.py`, it does `emp.x_studio_pension`. It doesn't define it. It inherits. 
        # This implies `x_studio_pension` is likely a Studio field or defined elsewhere. 
        # However, `partner_employee_pen` creates the sync logic.
        # I'll stick to 'base', 'hr', 'import_employee_phone_number'. I won't explicitly depend on `partner_employee_pen` unless I need its code, but users usually have it installed. 
        # Actually, adding `partner_employee_pen` as dependency is safer if I want to ensure my module installs after it if there are interactions, but purely for this I just need to write to the field on hr.employee.
        # Let's add 'partner_employee_pen' just to be safe as it seems related to the business logic of pensions.
    ],
    'data': [
        'security/ir.model.access.csv',
        'wizard/pension_upload_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
}
