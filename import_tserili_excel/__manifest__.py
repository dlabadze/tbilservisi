{
    "name": "Import Tserili Excel",
    "version": "18.0.1.0.0",
    "category": "Human Resources",
    "summary": "Import Tserili records from Excel list header button",
    "depends": ["biuleteni"],
    "external_dependencies": {
        "python": ["pandas", "openpyxl"],
    },
    "data": [
        "security/ir.model.access.csv",
        "wizard/tserili_excel_import_wizard_views.xml",
        "views/tserili_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}
