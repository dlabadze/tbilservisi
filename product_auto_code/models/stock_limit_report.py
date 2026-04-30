from odoo import models, fields
from odoo.tools import drop_view_if_exists


class StockLimitReport(models.Model):
    _name = 'stock.limit.report'
    _description = 'საწყობი - ნაშთის ლიმიტები'
    _auto = False

    product_id = fields.Many2one('product.product', string='პროდუქტი', readonly=True)
    default_code = fields.Char(string='კოდი', readonly=True)
    min_amount = fields.Integer(string='მინიმალური რაოდენობა', readonly=True)
    available_quantity = fields.Float(string='ხელმისაწვდომი რაოდენობა', readonly=True)
    location_id = fields.Many2one('stock.location', string='ლოკაცია', readonly=True)

    def init(self):
        drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    sq.id,
                    sq.product_id,
                    pt.default_code,
                    pt.min_amount,
                    sq.location_id,
                    (sq.quantity - COALESCE(sq.reserved_quantity, 0)) AS available_quantity
                FROM stock_quant sq
                JOIN product_product pp ON sq.product_id = pp.id
                JOIN product_template pt ON pp.product_tmpl_id = pt.id
                JOIN stock_location sl ON sq.location_id = sl.id
                WHERE sl.usage = 'internal'
                  AND (
                    (sq.quantity - COALESCE(sq.reserved_quantity, 0)) < COALESCE(pt.min_amount, 0)
                    OR ((sq.quantity - COALESCE(sq.reserved_quantity, 0)) < 0 AND COALESCE(pt.min_amount, 0) = 0)
                  )
            )
        """ % self._table)
