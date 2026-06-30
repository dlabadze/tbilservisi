{
    "name": "Leave Allocation Import Excel",
    "version": "18.0.1.0.0",
    "category": "Human Resources",
    "summary": "Import hr.leave.allocation records from an Excel file",
    "depends": ["hr_holidays"],
    "external_dependencies": {
        "python": ["pandas", "openpyxl"],
    },
    "data": [
        "security/ir.model.access.csv",
        "wizard/leave_allocation_import_wizard_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}
