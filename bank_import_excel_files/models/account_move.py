from odoo import api,models, fields

class AccountMove(models.Model):
    _inherit = 'account.move'



    @api.depends('partner_id.name', 'date', 'state', 'move_type', 'name', 'ref')
    @api.depends_context('input_full_display_name')
    def _compute_display_name(self):
        for move in self:
            if not move.id or not move.name or move.name == '/':
                move.display_name = 'New'
            else:
                move.display_name = move._get_move_display_name(show_ref=True)