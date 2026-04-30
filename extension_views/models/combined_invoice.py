from odoo import models, fields

class CombinedInvoiceModel(models.Model):
    _name = 'combined.invoice.model'
    _description = 'Combined Invoice Model'

    invoice_number = fields.Char(string='Invoice Number')
    invoice_id = fields.Char(string='Invoice ID')
    factura_num = fields.Char(string='Factura Number')
    get_invoice_id = fields.Char(string='Get Invoice ID')
    account_move_id = fields.Many2one('account.move', string='Account Move')
