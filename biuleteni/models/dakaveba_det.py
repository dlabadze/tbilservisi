from odoo import models, fields


class DakavebaDet(models.Model):
    _name = 'dakaveba.det'
    _description = 'Dakaveba Detail'

    dakaveba_id = fields.Many2one(
        'dakaveba',
        string="დაკავება",
        ondelete='cascade'
    )

    employee_id = fields.Many2one(
        'hr.employee',
        string="თანამშრომელი",
        required=True
    )

    identification_id = fields.Char(
        string="პირადი ნომერი",
        related='employee_id.identification_id',
        store=True,
    )

    department_id = fields.Many2one(
        'hr.department',
        string="სამსახური",
        related='employee_id.department_id',
        store=True,
    )

    parent_department_id = fields.Many2one(
        'hr.department',
        string="დეპარტამენტი",
        related='employee_id.department_id.parent_id',
        store=True,
    )

    job_id = fields.Many2one(
        'hr.job',
        string="თანამდებობა",
        related='employee_id.job_id',
        store=True,
    )

    amount = fields.Float(
        string="თანხა",
        required=True
    )
