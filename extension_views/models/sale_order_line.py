from odoo import models, fields
import logging

_logger = logging.getLogger(__name__)

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'
    barcode = fields.Char(related='product_id.barcode', string="ბარკოდი", store=True)
    unit_id = fields.Selection(related='product_id.unit_id', string = 'ერთეული rs.ge', store=True)
    unit_txt = fields.Char(related='product_id.unit_txt', string = 'სხვა ერთეული', store=True)

    def _prepare_stock_moves(self, picking):
        self.ensure_one()
        res = super(SaleOrderLine, self)._prepare_stock_moves(picking)
        for move_values in res:
            move_values.update({
                'unit_price': self.price_unit,
                'total_price': self.price_total,
            })
        return res
