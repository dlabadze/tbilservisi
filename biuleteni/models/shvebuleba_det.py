from odoo import models, fields, api
from odoo.exceptions import UserError  # ← Add this line

class ShvebulebaDet(models.Model):
    _name = 'shvebuleba_det'
    _description = 'shvebuleba_det'
    _order = 'date_start, month'

    shvebuleba_id = fields.Many2one('shvebuleba', string='შვებულება', ondelete='cascade')
    contract_id = fields.Many2one('hr.contract', string='ხელშეკრულება')
    wage = fields.Float(string='ხელფასი')
    date_start = fields.Date(string="დაწყების თარიღი")
    date_end = fields.Date(string="დასრულების თარიღი")
    month = fields.Char(string="თვე")
    samushdge   = fields.Integer(string="სამუშაო დღეების რაოდენობა")
    shvebu_date = fields.Integer(string="შვებულება დღეები")
    daily_wage = fields.Float(string="დღიური ხელფასი")
    line_total = fields.Float(string="დასარიცხი თანხა", readonly=True)

    attendance_det_id = fields.Many2one('shvebuleba.attendance', string='დასწრება')


    @api.onchange('samushdge', 'shvebu_date', 'wage')
    def _onchange_recalculate(self):
        """Recalculate wage and totals when work days change."""
        for rec in self:
            if rec.samushdge <= 0:
                rec.daily_wage = 0
                rec.line_total = 0
                continue

            rec.daily_wage = rec.wage / rec.samushdge
            rec.line_total = rec.daily_wage * rec.shvebu_date

    def action_open_attendance(self):
        """Opens the related attendance record."""
        self.ensure_one()
        if not self.attendance_det_id:
            raise UserError("ამ დეტალზე დასწრების ჩანაწერი არ არსებობს.")

        return {
            'type': 'ir.actions.act_window',
            'name': 'დასწრების დეტალები',
            'res_model': 'shvebuleba.attendance',
            'view_mode': 'form',
            'res_id': self.attendance_det_id.id,
            'target': 'current',
        }