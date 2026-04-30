from odoo import api, models, fields


class AccountMove(models.Model):
    _inherit = 'account.move'

    identification_code = fields.Char(string='ს/კ (საიდენტიფიკაციო)', compute='_compute_code')

    @api.onchange('line_ids')
    def _onchange_line_ids_propagate_partner(self):
        for line in self.line_ids:
            if line.partner_id:
                self.partner_id = line.partner_id
                self.identification_code = line.partner_id.vat or False
                break


    @api.depends('line_ids.partner_id')
    def _compute_code(self):
        for move in self:
            move.identification_code = False

            for line in move.line_ids:
                if line.partner_id:
                    move.identification_code = line.partner_id.vat
                    break