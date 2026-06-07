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
        store=True,
        readonly=True,
    )

    @api.depends(
        'picking_ids',
        'picking_ids.location_dest_id',
        'picking_ids.location_dest_id.usage'
    )
    def _compute_return_status(self):
        for order in self:
            returned = order.picking_ids.filtered(
                lambda p: p.location_dest_id
                and p.location_dest_id.usage == 'supplier'
            )

            order.return_status = (
                'returned' if returned else 'received'
            )