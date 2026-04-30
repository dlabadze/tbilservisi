from odoo.exceptions import UserError
from odoo import models, _


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def action_delete_related_account_moves(self):
        selected_stock_move_lines = self
        if not selected_stock_move_lines:
            raise UserError(_("No records selected."))

        stock_moves = selected_stock_move_lines.mapped('move_id')

        related_account_moves = self.env['account.move'].search([
            ('stock_move_id', 'in', stock_moves.ids)
        ])

        if not related_account_moves:
            return True

        if any(move.inalterable_hash for move in related_account_moves):
            locked_names = ", ".join(related_account_moves.filtered(lambda m: m.inalterable_hash).mapped('name'))
            raise UserError(_("Cannot delete: Some entries are locked/hashed: %s") % locked_names)

        related_account_moves.button_draft()
        related_account_moves.unlink()
        stock_moves.write({'state': 'draft'})

        return True