{
    "name": "Unscrapped Stock Report",
    "version": "18.0.1.0.0",
    "summary": "Report products currently in stock that were not scrapped within a date range",
    "depends": ["stock"],
    "data": [
        "security/ir.model.access.csv",
        "wizard/unscrapped_stock_wizard_views.xml",
        "views/unscrapped_stock_report_views.xml",
        "views/menu_views.xml",
    ],
    "author": "Custom",
    "license": "LGPL-3",
    "category": "Inventory",
    "installable": True,
    "application": False,
}
