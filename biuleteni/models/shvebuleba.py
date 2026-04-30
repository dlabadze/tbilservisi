from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import date, timedelta
from calendar import monthrange


class Shvebuleba(models.Model):
    _name = 'shvebuleba'
    _description = 'shvebuleba'
    _order = 'orderdate desc, id desc'

    # --- States ---
    state = fields.Selection([
        ('draft', 'დრაფტი'),
        ('validated', 'დადასტურებული')
    ], default='draft', string='სტატუსი')
    emp_id    = fields.Many2one('hr.employee', string="გვარი სახელი", required=True)
    tabnum = fields.Char(string="ტაბელის ნომერი", compute='_compute_employee_fields', store=True)
    pirnum = fields.Char(string="პირადი ნომერი", compute='_compute_employee_fields', store=True)
    positn = fields.Char(string="თანამდებობა", compute='_compute_employee_fields', store=True)
    orderdate = fields.Date(string="ბრძანების თარიღი", required=True, default=fields.Date.context_today)
    ordernumb = fields.Char(string="ბრძანების ნომერი")
    ordertype = fields.Char(string="ბრძანების ტიპი")
    startdate = fields.Date(string="საწყისი თარიღი", required=True, default=fields.Date.context_today)
    end_datee = fields.Date(string="ბოლო თარიღი", required=True, default=fields.Date.context_today)
    daricxelf = fields.Float(string="დარიცხული ხელფასი")
    #daricshve = fields.Float(string="დარიცხული შვებულება")
    amountday = fields.Integer(string="დღეების რაოდენობა")
    ganyofile = fields.Char(string="განყოფილება")
    dateofopp = fields.Date(string="თარიღი", required=True, default=fields.Date.context_today)
    validatio = fields.Boolean(string="დამტკიცებულია", default=False)
    calamountday = fields.Integer(string="კალენდარული დღეების რაოდენობა")

    shvebuleba_line_ids = fields.One2many('shvebuleba_det', 'shvebuleba_id', string='დეტალები')


    daricshve = fields.Float(
        string="დარიცხული შვებულება",
        compute="_compute_daricshve",
        store=True,
    )

    @api.depends('shvebuleba_line_ids.line_total')
    def _compute_daricshve(self):
        for rec in self:
            rec.daricshve = sum(line.line_total for line in rec.shvebuleba_line_ids)    

    # 🧮 Compute employee details
    @api.depends('emp_id')
    def _compute_employee_fields(self):
        for rec in self:
            emp = rec.emp_id
            rec.tabnum = emp.x_studio_tabeli or ''
            rec.pirnum = emp.identification_id or ''
            rec.positn = emp.job_id.name if emp.job_id else ''
            rec.ganyofile = emp.department_id.name if emp.department_id else ''



    # --- Actions ---
    def action_validate(self):
        self.ensure_one()
        if self.state != 'draft':
            raise UserError("მხოლოდ დრაფტი ჩანაწერის დადასტურებაა შესაძლებელი.")
        self.write({'state': 'validated'})

    def action_reset_draft(self):
        self.ensure_one()
        if self.state != 'validated':
            raise UserError("მხოლოდ validated ჩანაწერის დაბრუნებაა შესაძლებელი draft-ზე.")
        self.write({'state': 'draft'})     


    # --- Main calculation ---
    def action_calculate_shvebuleba(self):
        """Calculate missed days and compensation per month and contract, with Georgian month names."""
        self.ensure_one()
        if not self.emp_id or not self.startdate or not self.end_datee:
            raise UserError("გთხოვთ მიუთითოთ თანამშრომელი და თარიღები.")

        Contract = self.env['hr.contract']
        Attendance = self.env['hr.attendance']

        # 1️⃣ Find all active contracts in range
        contracts = Contract.search([
            ('employee_id', '=', self.emp_id.id),
            ('date_start', '<=', self.end_datee),
            '|',
            ('date_end', '>=', self.startdate),
            ('date_end', '=', False),
        ])
        if not contracts:
            raise UserError("მითითებულ პერიოდში შრომითი ხელშეკრულება ვერ მოიძებნა.")

        # Clear old lines
        self.shvebuleba_line_ids.unlink()

        # 2️⃣ Attendance data
        missed = Attendance.search([
            ('employee_id', '=', self.emp_id.id),
            ('x_studio_selection_field_99n_1j76jab36', '=', 'S'),
            ('check_in', '>=', self.startdate),
            ('check_in', '<=', self.end_datee),
        ])
        missed_dates = set(a.check_in.date() for a in missed if a.check_in)

        days_off = Attendance.search([
            ('employee_id', '=', self.emp_id.id),
            ('x_studio_selection_field_99n_1j76jab36', '=', 'D'),
            ('check_in', '>=', self.startdate),
            ('check_in', '<=', self.end_datee),
        ])
        days_off_dates = set(a.check_in.date() for a in days_off if a.check_in)

        # 3️⃣ Georgian month names
        georgian_months = {
            1: "იანვარი", 2: "თებერვალი", 3: "მარტი", 4: "აპრილი",
            5: "მაისი", 6: "ივნისი", 7: "ივლისი", 8: "აგვისტო",
            9: "სექტემბერი", 10: "ოქტომბერი", 11: "ნოემბერი", 12: "დეკემბერი"
        }

        # 4️⃣ Helper: working days per month
        def get_working_days_for_month(year, month):
            _, days_in_month = monthrange(year, month)
            month_start = date(year, month, 1)
            all_days = {month_start + timedelta(days=i) for i in range(days_in_month)}
            return len(all_days - days_off_dates)

        # 5️⃣ Group missed days by (contract, year, month)
        contract_month_days = {}
        for d in missed_dates:
            for c in contracts:
                start = c.date_start
                end = c.date_end or date.today()
                if start <= d <= end:
                    key = (c.id, d.year, d.month)
                    contract_month_days[key] = contract_month_days.get(key, 0) + 1
                    break

        # 6️⃣ Create lines per (contract + month)
        total_days = 0
        total_amount = 0

        for (contract_id, year, month), missed_days in contract_month_days.items():
            contract = contracts.filtered(lambda x: x.id == contract_id)
            if not contract:
                continue
            c = contract[0]
            working_days = get_working_days_for_month(year, month)
            daily_wage = (c.wage / working_days) if working_days else 0
            line_total = daily_wage * missed_days
            month_name = f"{georgian_months.get(month, str(month))} {year}"

            det = self.env['shvebuleba_det'].create({
                'shvebuleba_id': self.id,
                'contract_id': c.id,
                'month': month_name,
                'wage': c.wage,
                'date_start': c.date_start,
                'date_end': c.date_end,
                'shvebu_date': missed_days,
                'daily_wage': daily_wage,
                'line_total': line_total,
                'samushdge': working_days,
            })

            # ✅ attendance range = intersection of contract + month + user range
            month_start = date(year, month, 1)
            month_end = date(year, month, monthrange(year, month)[1])
            start_limit = max(c.date_start, self.startdate, month_start)
            end_limit = min(c.date_end or date.today(), self.end_datee, month_end)

            attendance_records = Attendance.search([
                ('employee_id', '=', self.emp_id.id),
                ('check_in', '>=', start_limit),
                ('check_in', '<=', end_limit),
            ], order='check_in asc')

            attendance_values = {'shvebuleba_det_id': det.id}
            for rec in attendance_records:
                if rec.check_in:
                    d = rec.check_in.date()
                    day_field = f'day{d.day}'
                    if day_field in self.env['shvebuleba.attendance']._fields:
                        attendance_values[day_field] = rec.x_studio_selection_field_99n_1j76jab36 or ''

            attendance = self.env['shvebuleba.attendance'].create(attendance_values)
            det.attendance_det_id = attendance.id
            #samuraod     +=
            total_days   += missed_days
            total_amount += line_total

        self.amountday    = total_days
        self.daricxelf    = total_amount 
        self.daricshve    = total_amount   

        
class HREmployee(models.Model):
    _inherit = 'hr.employee'

    shvebuleba_ids = fields.One2many(
        'shvebuleba', 'emp_id', string='შვებულებები'
    )           
