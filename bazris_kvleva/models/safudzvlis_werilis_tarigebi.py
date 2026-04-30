from odoo import models, fields, api


class SafudzvlisWerilisTarigebi(models.Model):
    _name = 'safudzvlis.werilis.tarigebi'
    _description = 'Safudzvlis Werilis Tarigebi'
    _order = 'tarigi desc, werilis_nomeri'

    bazris_kvleva_id = fields.Many2one('bazris.kvleva', string='Bazris Kvleva', required=True, ondelete='cascade')
    werilis_nomeri = fields.Char(string='წერილის ნომერი', required=True)
    tarigi = fields.Date(string='თარიღი', required=True)

