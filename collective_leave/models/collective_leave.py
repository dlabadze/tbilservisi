import base64
import io
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CollectiveLeave(models.Model):
    _name = 'collective.leave'
    _description = 'Collective Leave'

    name = fields.Char(
        string='სახელი',
        required=True,
        readonly=True,
        default='New',
        copy=False,
    )
    department_id = fields.Many2one(
        comodel_name='hr.department',
        string='სამსახური',
        required=True,
    )
    job_id = fields.Many2one(
        comodel_name='hr.job',
        string='თანამდებობა',
        domain="[('department_id', '=', department_id)]",
    )
    start_day =  fields.Date(
        string='საწყისი თარიღი',
        required=True,
    )
    end_day = fields.Date(
        string='დასრულების თარიღი',
        required=True,
    )
    days = fields.Integer(
        string='დღეების რაოდენობა',
        compute='_compute_days',
        store=True,
        readonly=False,
    )
    collective_leave_emp_ids = fields.One2many(
        comodel_name='collective.leave.employees',
        inverse_name='collective_leave_id',
        string='თანამშრომელები',
    )
    employee_ids = fields.Many2many(
        comodel_name='hr.employee',
        string='მონიშნულები',
        compute='_compute_employee_ids',
        store=True,
    )
    approval_request_ids = fields.One2many(
        comodel_name='approval.request',
        inverse_name='collective_leave_id',
        string='ბრძანებები',
    )
    approval_request_count = fields.Integer(
        compute='_compute_approval_request_count',
    )
    leave_type_id = fields.Many2one(
        comodel_name="hr.leave.type",
        string="შვებულების ტიპი",
        default=lambda self: self.env['hr.leave.type'].search([('name', '=', 'შვებულება პირადი')], limit=1),
    )

    @api.depends('start_day', 'end_day')
    def _compute_days(self):
        for record in self:
            if not record.start_day or not record.end_day:
                record.days = 0
                continue

            holidays = self.env['resource.calendar.leaves'].search([
                ('resource_id', '=', False),
            ]).filtered(lambda h: h.date_from.date() <= record.end_day and h.date_to.date() >= record.start_day)

            holiday_dates = set()
            for h in holidays:
                d = h.date_from.date()
                end = h.date_to.date()
                while d <= end:
                    holiday_dates.add(d)
                    d += timedelta(days=1)

            count = 0
            current = record.start_day
            while current <= record.end_day:
                if current.weekday() != 6 and current not in holiday_dates:
                    count += 1
                current += timedelta(days=1)

            record.days = count

    def _compute_approval_request_count(self):
        for record in self:
            record.approval_request_count = len(record.approval_request_ids)

    def action_open_approval_requests(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'ბრძანებები',
            'res_model': 'approval.request',
            'view_mode': 'list,form',
            'domain': [('collective_leave_id', '=', self.id)],
            'context': {'default_collective_leave_id': self.id},
        }

    @api.depends('collective_leave_emp_ids.is_checked')
    def _compute_employee_ids(self):
        for record in self:
            checked = record.collective_leave_emp_ids.filtered('is_checked')
            record.employee_ids = checked.mapped('employee_id')

    def action_compute_employees(self):
        for record in self:
            existing_ids = record.collective_leave_emp_ids.mapped('employee_id').ids
            employees = self.env['hr.employee'].sudo().search([
                ('department_id', '=', record.department_id.id),
                ('id', 'not in', existing_ids),
            ])
            if record.job_id and employees:
                employees = employees.filtered(lambda e: e.job_id.id == record.job_id.id)

            year = record.start_day.year if record.start_day else False
            if year and record.leave_type_id:
                already_have_leave = self.env['hr.leave'].sudo().search([
                    ('holiday_status_id', '=', record.leave_type_id.id),
                    ('state', 'not in', ['refuse']),
                    ('date_from', '>=', fields.Datetime.to_datetime(fields.Date.today().replace(year=year, month=1, day=1))),
                    ('date_from', '<', fields.Datetime.to_datetime(fields.Date.today().replace(year=year + 1, month=1, day=1))),
                    ('employee_id', 'in', employees.ids),
                ]).mapped('employee_id').ids
                employees = employees.filtered(lambda e: e.id not in already_have_leave)

            record.collective_leave_emp_ids = [
                (0, 0, {'employee_id': emp.id})
                for emp in employees
            ]

    def create_approval_request(self):
        category = self.env['approval.category'].sudo().search([('name', '=', 'შვებულება პირადი')], limit=1)
        for record in self:
            existing_employees = record.approval_request_ids.mapped('brdzaneba_employee_id').ids
            for employee in record.employee_ids:
                if employee.id in existing_employees:
                    continue
                request = self.env['approval.request'].sudo().create({
                    'request_owner_id': self.env.user.id,
                    'category_id': category.id,
                    'brdzaneba_employee_id': employee.id,
                    'brdzaneba_start_date': record.start_day,
                    'brdzaneba_end_date': record.end_day,
                    'x_studio_dgeebi_real': record.days,
                    'collective_leave_id': record.id,
                    'x_studio_time_off_type': record.leave_type_id.id if record.leave_type_id else False,
                })
                request.sudo().action_confirm()
                request.sudo().action_approve()


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('collective.leave') or 'New'
        return super().create(vals_list)

    def action_generate_excel(self):
        self.ensure_one()

        try:
            import xlsxwriter
        except ImportError:
            raise UserError(_('xlsxwriter ბიბლიოთეკა საჭიროა Excel-ის გენერაციისთვის.'))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('თანამშრომლები')

        header_fmt = workbook.add_format({
            'bold': True,
            'bg_color': '#4472C4',
            'font_color': '#FFFFFF',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
        })
        cell_fmt = workbook.add_format({
            'border': 1,
            'valign': 'vcenter',
        })
        num_fmt = workbook.add_format({
            'border': 1,
            'valign': 'vcenter',
            'align': 'center',
        })

        COLUMNS = [
            ('N', 5, num_fmt),
            ('სამსახური', 30, cell_fmt),
            ('თანამდებობა', 30, cell_fmt),
            ('თანამშრომელი', 30, cell_fmt),
            ('პირადი ნომერი', 18, cell_fmt),
            ('საწყისი თარიღი', 16, cell_fmt),
            ('დასრულების თარიღი', 18, cell_fmt),
        ]

        sheet.set_row(0, 30)
        for col_idx, col_def in enumerate(COLUMNS):
            sheet.write(0, col_idx, col_def[0], header_fmt)
            sheet.set_column(col_idx, col_idx, col_def[1])

        sheet.freeze_panes(1, 0)

        start_day = self.start_day.strftime('%d.%m.%Y') if self.start_day else ''
        end_day = self.end_day.strftime('%d.%m.%Y') if self.end_day else ''

        for row_idx, employee in enumerate(self.employee_ids, start=1):
            values = [
                row_idx,
                employee.department_id.display_name or '',
                employee.job_id.display_name or '',
                employee.name or '',
                employee.identification_id or '',
                start_day,
                end_day,
            ]
            for col_idx, value in enumerate(values):
                sheet.write(row_idx, col_idx, value, COLUMNS[col_idx][2])

        workbook.close()
        output.seek(0)
        excel_data = base64.b64encode(output.read())

        filename = 'collective_leave_{}_{}.xlsx'.format(
            (self.name or 'export').replace('/', '-'),
            fields.Date.today(),
        )

        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': excel_data,
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': (
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            ),
        })

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/{}?download=true'.format(attachment.id),
            'target': 'new',
        }
