from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    return_status = fields.Selection(
        selection=[
            ('received', 'მიღებულია'),
            ('returned', 'დაბრუნებულია'),
        ],
        string='სტატუსი',
        compute='_compute_return_status',
        readonly=True,
        store=False,
    )

    def _compute_return_status(self):
        StockPicking = self.env['stock.picking']

        for order in self:
            returned = StockPicking.search_count([
                ('purchase_id', '=', order.id),
                ('location_dest_id.usage', '=', 'supplier'),
            ])

            order.return_status = (
                'returned' if returned else 'received'
            )