from odoo import models, fields, api
from odoo.exceptions import UserError
from calendar import monthrange

class ShvebulebaGenerateWizard(models.TransientModel):
    _name = 'shvebuleba.generate.wizard'
    _description = 'Generate Shvebuleba Records From Orders'

    date = fields.Date(string="თარიღი", required=True)
    department_id = fields.Many2one('hr.department', string='განყოფილება', required=True)

    def action_generate(self):
        self.ensure_one()

        Operation = self.env['approval.request']
        Shvebuleba = self.env['shvebuleba']

        # --- MONTH RANGE ---
        year = self.date.year
        month = self.date.month
        last_day = monthrange(year, month)[1]

        month_start = self.date.replace(day=1)
        month_end = self.date.replace(day=last_day)

                # --- Allowed leave types ---
        allowed_types = [
            #"შვებულება ანაზღაურებადი",
            45,46,
            #"შვებულება დეკრეტული",
            #"შვებულება პირადი",
            #"შვებულება პირადი (კოლექტიური)",
        ]

        # 1) FIND ALL OPERATIONS ACTIVE IN THIS MONTH
        ops = Operation.search([
            ('brdzaneba_current_department_id', '=', self.department_id.id),
            ('brdzaneba_start_date', '<=', month_end),
            ('brdzaneba_end_date', '>=', month_start),
            ('request_status', '=', 'approved'),
            ('category_id', 'in', allowed_types),
        ])

        if not ops:
            raise UserError("მითითებულ თარიღზე ამ განყოფილებაში თანამშრომლის ბრძანება არ მოიძებნა.")

        # 2) Create shvebuleba for each employee
        for op in ops:
            employee = op.brdzaneba_employee_id
            if not employee:
                continue

            # --- DUPLICATE CHECK ---
            existing = Shvebuleba.search([
                ('emp_id', '=', employee.id),
                #('ganyofile', '=', self.department_id.name),
                ('orderdate', '>=', month_start),
                ('orderdate', '<=', month_end),
            ], limit=1)

            if existing:
                # Employee already has shvebuleba this month → skip
                continue

            # Create shvebuleba record
            sh = Shvebuleba.create({
                'emp_id': employee.id,
                'orderdate': self.date,
                'startdate': month_start,
                'end_datee': month_end,
                'ganyofile': self.department_id.name,
                'ordertype': 'შვებულება',
            })

            # Run calculation
            sh.action_calculate_shvebuleba()

        # 3) OPEN SHVEBULEBA LIST VIEW (NO FILTERS)
        return {
            'type': 'ir.actions.act_window',
            'name': 'შვებულებები',
            'res_model': 'shvebuleba',
            'view_mode': 'list,form',
            'target': 'current',
        }
