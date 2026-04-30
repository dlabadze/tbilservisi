from odoo import models, fields, api


class BazrisKvleva(models.Model):
    _name = 'bazris.kvleva'
    _description = 'Bazris Kvleva'
    _order = 'line_number'

    line_number = fields.Integer(string='N')
    job_id = fields.Many2one('hr.department', string='სამსახური')
    saf_number = fields.Char(string='საფუძვლის წერილის ნომერი')
    saf_date = fields.Date(string='საფუძვლის წერილის თარიღი')
    purchase_object = fields.Char(string='შესყიდვის ობიექტი')
    last_date = fields.Date(string='ბოლო ვადა')
    status = fields.Selection([
        ('mimdinare', 'მიმდინარე'),
        ('dasakorektirebeli', 'დასაკორექტირებელი'),
        ('shetsqvetili', 'შეწყვეტილი'),
        ('dasrulebuli', 'დასრულებული'),
    ], string='მიმდინარეობის სტადია')
    bazris_kvlevis_nomeri = fields.Char(string='ბაზრის კვლევის რეგისტრაციის ნომერი')
    sap_number = fields.Char(string='საპასუხო წერილის ნომერი')
    sap_date = fields.Date(string='საპასუხო წერილის თარიღი')
    shenishvna = fields.Char(string='შენიშვნა')
    shemsrulebeli_id = fields.Many2one('bazris.kvlevis.tanamshromlebi', string='შემსრულებელი', required=False)
    safudzvlis_werilis_tarigebi_ids = fields.One2many('safudzvlis.werilis.tarigebi', 'bazris_kvleva_id', string='საფუძვლის წერილის თარიღები')

