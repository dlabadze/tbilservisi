from odoo import models, fields


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    get_invoice_id = fields.Char(
        string='Invoice',
        related='move_id.get_invoice_id',
        readonly=True,
        store=False,
    )

    get_invoice_id_helper = fields.Char(
        string='Invoice Helper',
        related='move_id.get_invoice_id_helper',
        readonly=True,
        store=False,
    )

    move_id_comment = fields.Text(related='move_id.comment', string='კომენტარი', readonly=True)
