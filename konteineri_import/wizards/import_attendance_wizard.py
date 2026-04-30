from odoo import models, fields, api

class ImportAttendanceWizard(models.TransientModel):
    _name = 'import.attendance.wizard'

    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    identification_id = fields.Char(string="Identification Number")

    def action_import(self):
        # 1. Identify which employees to import
        if self.identification_id:
            employees = self.env['hr.employee'].search([
                ('identification_id', '=', self.identification_id)
            ])
        else:
            employees = self.env['hr.employee'].search([
                ('identification_id', '!=', False)
            ])

        if not employees:
            return {'type': 'ir.actions.act_window_close'}

        # 2. Split into batches (e.g., 20 employees per job)
        BATCH_SIZE = 20
        # Convert recordset to list/ids for slicing if needed, 
        # but iterating with slicing on recordset works in newer Odoo versions or via ids.
        employee_ids = employees.ids
        
        for i in range(0, len(employee_ids), BATCH_SIZE):
            batch_ids = employee_ids[i : i + BATCH_SIZE]
            
            self.env['attendance.import.job'].create({
                'date_from': self.date_from,
                'date_to': self.date_to,
                'employee_ids': [(6, 0, batch_ids)], # One2many/Many2many syntax
                'state': 'pending', 
            })

        return {'type': 'ir.actions.act_window_close'}
