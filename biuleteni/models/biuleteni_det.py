from odoo import models, fields, api
from odoo.exceptions import UserError

class BiuleteniDet(models.Model):
    _name = 'biuleteni_det'
    _description = 'ბიულეტენის დეტალიზაცია'
    _order = 'date_start, month'
    biuleteni_id = fields.Many2one('biuleteni', string='ბიულეტენი', ondelete='cascade')

    contract_id = fields.Many2one('hr.contract', string='ხელშეკრულება')
    wage = fields.Float(string='ხელფასი')
    date_start = fields.Date(string="დაწ თარიღი")
    date_end = fields.Date(string="დას თარიღი")
    month = fields.Char(string="თვე")

    samushdge = fields.Integer(string="სამუშაო დღეების რაოდენობა")
    missed_days = fields.Integer(string="გაცდენილი დღეები")
    daily_wage = fields.Float(string="დღიური ხელფასი")
    line_total = fields.Float(string="დასარიცხი თანხა", readonly=True)

    attendance_det_id = fields.Many2one('biuleteni.attendance', string='დასწრება')

    @api.onchange('samushdge', 'missed_days', 'wage')
    def _onchange_recalculate(self):
        for rec in self:
            if rec.samushdge <= 0:
                rec.daily_wage = 0
                rec.line_total = 0
                continue
            rec.daily_wage = rec.wage / rec.samushdge
            rec.line_total = rec.daily_wage * rec.missed_days

    def action_open_attendance(self):
        """Opens the related attendance record."""
        self.ensure_one()
        if not self.attendance_det_id:
            raise UserError("ამ დეტალზე დასწრების ჩანაწერი არ არსებობს.")

        return {
            'type': 'ir.actions.act_window',
            'name': 'დასწრების დეტალები',
            'res_model': 'biuleteni.attendance',
            'view_mode': 'form',
            'res_id': self.attendance_det_id.id,
            'target': 'current',
        }
