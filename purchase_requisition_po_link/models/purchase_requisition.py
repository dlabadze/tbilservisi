from odoo import api, fields, models, _


class PurchaseRequisition(models.Model):
    _inherit = 'purchase.requisition'

    po_link_ids = fields.One2many(
        comodel_name='purchase.order',
        inverse_name='requisition_link_id',
        string='შესყიდვის ორდერები',
    )
    po_link_count = fields.Integer(
        compute='_compute_po_link_count',
        string='შესყიდვის ორდერების რაოდენობა',
    )

    @api.depends('po_link_ids')
    def _compute_po_link_count(self):
        for rec in self:
            rec.po_link_count = len(rec.po_link_ids)

    def action_view_purchase_orders_linked(self):
        self.ensure_one()
        return {
            'name': _('შესყიდვის ორდერები'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('requisition_link_id', '=', self.id)],
            'context': {
                **self.env.context,
                'default_requisition_link_id': self.id,
            },
        }
