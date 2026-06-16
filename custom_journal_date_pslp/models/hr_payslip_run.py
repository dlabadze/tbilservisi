from odoo import models, fields, api

class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    journal_entry_date = fields.Date(
        string='Journal Entry Date',
        help="If set, this date will be used as the Accounting Date for all payslips in this batch."
    )
    structure_id = fields.Many2one(
        comodel_name='hr.payroll.structure',
        string='სახელფასო სტრუქტურა',
        help='Default salary structure applied to all payslips generated in this batch.',
    )