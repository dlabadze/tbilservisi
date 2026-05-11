{
    "name": "HR Employee Header Excel Import",
    "version": "18.0.1.0.0",
    "category": "Human Resources",
    "summary": "Import employee fields from Excel using list header button",
    "depends": ["hr"],
    "external_dependencies": {
        "python": ["pandas", "openpyxl"],
    },
    "data": [
        "security/ir.model.access.csv",
        "wizard/hr_employee_excel_import_wizard_views.xml",
        "views/hr_employee_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}
