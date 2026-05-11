{
    "name": "Import Shvebuleba Excel",
    "version": "18.0.1.0.0",
    "category": "Human Resources",
    "summary": "Import Shvebuleba records from Excel list header button",
    "depends": ["biuleteni"],
    "external_dependencies": {
        "python": ["pandas", "openpyxl"],
    },
    "data": [
        "security/ir.model.access.csv",
        "wizard/shvebuleba_excel_import_wizard_views.xml",
        "views/shvebuleba_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
    "license": "LGPL-3",
}
