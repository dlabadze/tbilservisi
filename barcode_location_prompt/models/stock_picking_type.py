from odoo import models, fields


class StockPickingType(models.Model):
    """
    Extend stock.picking.type to add auto-add product field for barcode operations.
    """
    _inherit = "stock.picking.type"

    car_sawvav_product_id = fields.Many2one(
        'product.product',
        string='ავტომატური პროდუქტი',
        help='ეს პროდუქტი ავტომატურად დაემატება move line-ებში როცა ამ ტიპის ოპერაცია შეიქმნება ან გაიხსნება barcode ინტერფეისში.',
    )

