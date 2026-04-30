{
    "name": "Product UoM Force Change",
    "summary": "Force change product UoM and update existing operations",
    "version": "18.0.1.0.0",
    "category": "Inventory",
    "depends": ["product", "stock", "sale_management", "purchase", "account"],
    "data": [
        "security/ir.model.access.csv",
        "views/product_uom_force_change_wizard_views.xml",
        "views/product_template_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
}
