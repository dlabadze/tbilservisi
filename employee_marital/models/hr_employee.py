from odoo import models, fields, api, _
from odoo.exceptions import UserError

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    marital = fields.Selection(
        [('single', 'მარტოხელა'),
         ('married', 'დაოჯახებული'),
         ('widowed', 'ქვრივი'),
         ('divorced', 'განქორწინებული'),
         ('დასაოჯახებელი','დასაოჯახებელი'),
         ('მრავალშვილიანი','მრავალშვილიანი'),
         ('მარტოხელა დედა','მარტოხელა დედა'),
         ],
        string='Marital Status',
        default='single',
        help="Marital Status of Employee"
    )