from odoo import models, fields, api

class StockMove(models.Model):
    _inherit = 'stock.move'

    line_number = fields.Integer(
        string='#',
        compute='_compute_line_number',
        store=False
    )

    @api.depends('picking_id.move_ids_without_package')
    def _compute_line_number(self):
        for move in self:
            move.line_number = 0
        for picking in self.mapped('picking_id'):
            moves = picking.move_ids_without_package
            for idx, move in enumerate(moves, start=1):
                move.line_number = idx
