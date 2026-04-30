from odoo import models, fields, api

class ShvebulebaAttendance(models.Model):
    _name = 'shvebuleba.attendance'
    _description = 'დასწრების დეტალები (შვებულება)'

    shvebuleba_det_id = fields.Many2one(
        'shvebuleba_det',
        string='შვებულება დეტალი',
        ondelete='cascade'
    )

    # 🧮 Computed display fields
    month = fields.Char(string='თვე', compute='_compute_display_fields', store=False)
    employee_id = fields.Many2one('hr.employee', string='თანამშრომელი', compute='_compute_display_fields', store=False)

    @api.depends('shvebuleba_det_id')
    def _compute_display_fields(self):
        for rec in self:
            det = rec.shvebuleba_det_id
            rec.month = det.month or ''
            rec.employee_id = det.shvebuleba_id.emp_id if det and det.shvebuleba_id else False

    # 🗓 Day fields
    day1 = fields.Char(string="1")
    day2 = fields.Char(string="2")
    day3 = fields.Char(string="3")
    day4 = fields.Char(string="4")
    day5 = fields.Char(string="5")
    day6 = fields.Char(string="6")
    day7 = fields.Char(string="7")
    day8 = fields.Char(string="8")
    day9 = fields.Char(string="9")
    day10 = fields.Char(string="10")
    day11 = fields.Char(string="11")
    day12 = fields.Char(string="12")
    day13 = fields.Char(string="13")
    day14 = fields.Char(string="14")
    day15 = fields.Char(string="15")
    day16 = fields.Char(string="16")
    day17 = fields.Char(string="17")
    day18 = fields.Char(string="18")
    day19 = fields.Char(string="19")
    day20 = fields.Char(string="20")
    day21 = fields.Char(string="21")
    day22 = fields.Char(string="22")
    day23 = fields.Char(string="23")
    day24 = fields.Char(string="24")
    day25 = fields.Char(string="25")
    day26 = fields.Char(string="26")
    day27 = fields.Char(string="27")
    day28 = fields.Char(string="28")
    day29 = fields.Char(string="29")
    day30 = fields.Char(string="30")
    day31 = fields.Char(string="31")
