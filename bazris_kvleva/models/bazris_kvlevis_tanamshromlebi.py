from odoo import models, fields, api


class BazrisKvlevisTanamshromlebi(models.Model):
    _name = 'bazris.kvlevis.tanamshromlebi'
    _description = 'Bazris Kvlevis Tanamshromlebi'
    _rec_name = 'name'
    _order = 'name'

    name = fields.Char(string='Name', required=True)

