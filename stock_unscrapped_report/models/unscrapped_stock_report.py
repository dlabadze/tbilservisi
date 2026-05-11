from odoo import fields, models


class UnscrappedStockReportLine(models.TransientModel):
    _name = "unscrapped.stock.report.line"
    _description = "Unscrapped Stock Report Line"
    _order = "location_id, product_id"

    wizard_id = fields.Many2one(
        "unscrapped.stock.wizard", ondelete="cascade", index=True
    )
    location_id = fields.Many2one("stock.location", string="Location", required=True)
    warehouse_id = fields.Many2one("stock.warehouse", string="Warehouse")
    product_id = fields.Many2one("product.product", string="Product", required=True)
    categ_id = fields.Many2one("product.category", string="Product Category")
    product_default_code = fields.Char(string="Internal Reference")
    product_name = fields.Char(string="Product Name")
    quantity = fields.Float(string="Quantity", digits="Product Unit of Measure")
    uom_id = fields.Many2one("uom.uom", string="Unit of Measure")
