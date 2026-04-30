{
    "name": "Barcode Location Prompt",
    "summary": "Always prompt for destination location when scanning barcodes for internal transfers",
    "version": "18.0.3.0.5",
    "author": "Custom",
    "website": "",
    "category": "Inventory/Barcode",
    "license": "LGPL-3",
    "depends": ["stock", "stock_barcode"],
    "data": [
        "views/stock_move_line_views.xml",
        "views/stock_picking_type_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "barcode_location_prompt/static/src/css/barcode_quantity.css",
            "barcode_location_prompt/static/src/js/barcode_quantity_input.js",
        ],
    },
    "application": False,
    "installable": True,
    "auto_install": False,
}


