# -*- coding: utf-8 -*-

{
    "name": "Initial Inventory Import With Date",
    "version": "18.0.1.0.0",
    "category": "Inventory/Inventory",
    "summary": "Import opening stock balances from XLSX with stock valuation/accounting date",
    "depends": ["stock_account"],
    "data": [
        "security/ir.model.access.csv",
        "views/initial_inventory_import_views.xml",
    ],
    "external_dependencies": {
        "python": ["openpyxl"],
    },
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
