from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import date, timedelta
from calendar import monthrange


class Biuleteni(models.Model):
    _name = 'biuleteni'
    _description = 'ანაზღაურებადი ბიულეტენი'
    _order = 'date desc, id desc'

    # --- States ---
    state = fields.Selection([
        ('draft', 'დრაფტი'),
        ('validated', 'დადასტურებული')
    ], default='draft', string='სტატუსი')

    # --- Main fields ---
    date = fields.Date(string="თარიღიდან", required=True, default=fields.Date.context_today)
    date_2 = fields.Date(string="თარიღამდე", required=True, default=fields.Date.context_today)
    month_selection = fields.Selection([
        ('1', 'იანვარი'),
        ('2', 'თებერვალი'),
        ('3', 'მარტი'),
        ('4', 'აპრილი'),
        ('5', 'მაისი'),
        ('6', 'ივნისი'),
        ('7', 'ივლისი'),
        ('8', 'აგვისტო'),
        ('9', 'სექტემბერი'),
        ('10', 'ოქტომბერი'),
        ('11', 'ნოემბერი'),
        ('12', 'დეკემბერი'),
    ], string='საანგარიშო თვე')
    parent_department_id = fields.Many2one(
        'hr.department',
        string="განყოფილება",
        domain="[('parent_id', '=', False)]",
    )
    department_id = fields.Many2one(
        'hr.department',
        string="სამსახური",
        domain="[('parent_id', '=', parent_department_id)] if parent_department_id else []",
    )
    employee_id = fields.Many2one(
        'hr.employee',
        string="თანამშრომელი",
        required=True,
        domain="[('department_id', '=', department_id)] if department_id else []",
    )
    docnum = fields.Char(string="საავადმყოფო ფურცლის ნომერი")

    sick_days = fields.Integer(
        string="ბიულეტენის დღეების რაოდენობა",
        compute='_compute_totals',
        store=True,
        readonly=True,
    )
    total_amount = fields.Float(
        string="სულ დასარიცხი თანხა",
        compute='_compute_totals',
        store=True,
        readonly=True,
    )

    biuleteni_line_ids = fields.One2many('biuleteni_det', 'biuleteni_id', string='დეტალიზაცია')

    @api.depends('biuleteni_line_ids', 'biuleteni_line_ids.missed_days', 'biuleteni_line_ids.line_total')
    def _compute_totals(self):
        for rec in self:
            rec.sick_days = sum(rec.biuleteni_line_ids.mapped('missed_days'))
            rec.total_amount = sum(rec.biuleteni_line_ids.mapped('line_total'))

    # --- Employee info (computed, stored for grouping) ---
    identification_id = fields.Char(
        string="პირადი ნომერი",
        compute='_compute_employee_info',
        store=False,
    )
    job_id = fields.Many2one(
        'hr.job',
        string="თანამდებობა",
        related='employee_id.job_id',
        store=True,
    )
    last_biuleteni_info = fields.Char(
        string="ბოლო რეგისტრირებული ბიულეტენი",
        compute='_compute_last_biuleteni_info',
        store=False,
    )
    overlap_info = fields.Text(
        string="თანაკვეთები სხვა ბიულეტენებთან",
        compute='_compute_overlap_info',
        store=False,
    )

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        for rec in self:
            if rec.employee_id and rec.employee_id.department_id:
                rec.department_id = rec.employee_id.department_id
                rec.parent_department_id = rec.employee_id.department_id.parent_id or False

    @api.onchange('department_id')
    def _onchange_department_id(self):
        for rec in self:
            if rec.department_id:
                if rec.department_id.parent_id:
                    rec.parent_department_id = rec.department_id.parent_id
                if rec.employee_id and rec.employee_id.department_id != rec.department_id:
                    rec.employee_id = False

    @api.onchange('parent_department_id')
    def _onchange_parent_department_id(self):
        for rec in self:
            if rec.parent_department_id and rec.department_id:
                if rec.department_id.parent_id != rec.parent_department_id:
                    rec.department_id = False
                    rec.employee_id = False

    @api.depends('employee_id')
    def _compute_employee_info(self):
        for rec in self:
            rec.identification_id = rec.employee_id.identification_id if rec.employee_id else ''

    @api.depends('employee_id', 'date', 'date_2')
    def _compute_last_biuleteni_info(self):
        for rec in self:
            if not rec.employee_id:
                rec.last_biuleteni_info = ''
                continue
            domain = [
                ('employee_id', '=', rec.employee_id.id),
                ('date', '!=', False),
                ('date_2', '!=', False),
            ]
            if isinstance(rec.id, int):
                domain.append(('id', '!=', rec.id))
            last = rec.env['biuleteni'].search(domain, order='date_2 desc, id desc', limit=1)
            if last:
                rec.last_biuleteni_info = "%s - %s" % (
                    last.date.strftime('%d.%m.%Y'),
                    last.date_2.strftime('%d.%m.%Y'),
                )
            else:
                rec.last_biuleteni_info = ''

    @api.depends('employee_id', 'date', 'date_2')
    def _compute_overlap_info(self):
        for rec in self:
            if not rec.employee_id or not rec.date or not rec.date_2:
                rec.overlap_info = ''
                continue
            domain = [
                ('employee_id', '=', rec.employee_id.id),
                ('date', '<=', rec.date_2),
                ('date_2', '>=', rec.date),
            ]
            if isinstance(rec.id, int):
                domain.append(('id', '!=', rec.id))
            overlaps = rec.env['biuleteni'].search(domain)
            if not overlaps:
                rec.overlap_info = ''
                continue
            lines = []
            for o in overlaps:
                start = max(o.date, rec.date)
                end = min(o.date_2, rec.date_2)
                lines.append(
                    "არჩეულ თანამშრომელს აქვს ბიულეტენებს შორის თანაკვეთა %s - %s"
                    % (start.strftime('%d.%m.%Y'), end.strftime('%d.%m.%Y'))
                )
            rec.overlap_info = "\n".join(lines)

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
    def action_calculate_biuleteni(self):
        """Calculate missed days and compensation per month and contract, with Georgian month names."""
        self.ensure_one()

        if not self.employee_id or not self.date or not self.date_2:
            raise UserError("გთხოვთ მიუთითოთ თანამშრომელი და თარიღები.")

        Contract = self.env['hr.contract']
        Attendance = self.env['hr.attendance']

        # 1️⃣ Find all active contracts in the period
        contracts = Contract.search([
            ('employee_id', '=', self.employee_id.id),
            ('date_start', '<=', self.date_2),
            '|',
            ('date_end', '>=', self.date),
            ('date_end', '=', False),
        ])
        if not contracts:
            raise UserError("მითითებულ პერიოდში შრომითი ხელშეკრულება ვერ მოიძებნა.")

        # Clear old lines
        self.biuleteni_line_ids.unlink()

        # 2️⃣ Attendance data
        missed = Attendance.search([
            ('employee_id', '=', self.employee_id.id),
            ('x_studio_selection_field_99n_1j76jab36', '=', 'G'),
            ('check_in', '>=', self.date),
            ('check_in', '<=', self.date_2),
        ])
        missed_dates = set(a.check_in.date() for a in missed if a.check_in)

        # ❗ Days off must include ALL D-days for correct monthly wage calc
        days_off = Attendance.search([
            ('employee_id', '=', self.employee_id.id),
            ('x_studio_selection_field_99n_1j76jab36', '=', 'D'),
        ])

        # Group ALL D-days by (year, month)
        days_off_by_month = {}
        for a in days_off:
            if a.check_in:
                d = a.check_in.date()
                key = (d.year, d.month)
                days_off_by_month.setdefault(key, set()).add(d)

        # 3️⃣ Georgian month names
        georgian_months = {
            1: "იანვარი", 2: "თებერვალი", 3: "მარტი", 4: "აპრილი",
            5: "მაისი", 6: "ივნისი", 7: "ივლისი", 8: "აგვისტო",
            9: "სექტემბერი", 10: "ოქტომბერი", 11: "ნოემბერი", 12: "დეკემბერი"
        }

        # 4️⃣ Working days per month = all days - D-days in that month
        def get_working_days_for_month(year, month):
            _, days_in_month = monthrange(year, month)
            start = date(year, month, 1)
            all_days = {start + timedelta(days=i) for i in range(days_in_month)}

            off_days = days_off_by_month.get((year, month), set())
            return len(all_days - off_days)

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

        # 6️⃣ Create lines for each (contract + month)
        for (contract_id, year, month), missed_days in contract_month_days.items():
            contract = contracts.filtered(lambda x: x.id == contract_id)
            if not contract:
                continue
            c = contract[0]

            working_days = get_working_days_for_month(year, month)
            daily_wage = (c.wage / working_days) if working_days else 0
            line_total = daily_wage * missed_days
            month_name = f"{georgian_months.get(month, str(month))} {year}"

            det = self.env['biuleteni_det'].create({
                'biuleteni_id': self.id,
                'contract_id': c.id,
                'month': month_name,
                'wage': c.wage,
                'date_start': c.date_start,
                'date_end': c.date_end,
                'samushdge': working_days,
                'missed_days': missed_days,
                'daily_wage': daily_wage,
                'line_total': line_total,
            })

            month_start = date(year, month, 1)
            month_end = date(year, month, monthrange(year, month)[1])

            attendance_records = Attendance.search([
                ('employee_id', '=', self.employee_id.id),
                ('check_in', '>=', month_start),
                ('check_in', '<=', month_end),
            ], order='check_in asc')

            attendance_values = {'biuleteni_det_id': det.id}
            for rec in attendance_records:
                if rec.check_in:
                    d = rec.check_in.date()
                    day_field = f'day{d.day}'
                    if day_field in self.env['biuleteni.attendance']._fields:
                        attendance_values[day_field] = rec.x_studio_selection_field_99n_1j76jab36 or ''

            attendance = self.env['biuleteni.attendance'].create(attendance_values)
            det.attendance_det_id = attendance.id


class HREmployee(models.Model):
    _inherit = 'hr.employee'

    biuleteni_ids = fields.One2many(
        'biuleteni', 'employee_id', string='ბიულეტენები'
    )


class HRDepartment(models.Model):
    _inherit = 'hr.department'

    @api.depends('name')
    def _compute_display_name(self):
        if not self.env.context.get('biuleteni_dept_name'):
            return super()._compute_display_name()
        for dept in self:
            dept.display_name = dept.name or ''
