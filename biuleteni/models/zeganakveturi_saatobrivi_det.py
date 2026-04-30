from odoo import models, fields, api


class ZeganakveturiSaatiDet(models.Model):
    _name = 'zeganakveturi_saati_det'
    _description = 'zeganakveturi_saati_det'
    _order = 'id desc'

    zeganakveturi_saati_id = fields.Many2one(
        'zeganakveturi_saati',
        string='მთავარი ჩანაწერი',
        required=True,
        ondelete='cascade'
    )

    entry_type = fields.Selection(
        related='zeganakveturi_saati_id.entry_type',
        store=True,
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

    worked_hours = fields.Float(
        string="ზეგანაკვეთური საათები",
        required=True
    )

    hourly_rate = fields.Float(
        string="ტარიფი",
        required=True
    )

    amount = fields.Float(
        string="ჯამური თანხა",
        compute="_compute_amount",
        store=True
    )

    @api.depends('worked_hours', 'hourly_rate')
    def _compute_amount(self):
        for line in self:
            line.amount = line.worked_hours * line.hourly_rate



class HREmployee(models.Model):
    _inherit = 'hr.employee'

    _rec_names_search = ['name', 'identification_id']

    zeganakveturi_saati_ids = fields.One2many(
        'zeganakveturi_saati_det', 'employee_id', string='ზეგანაკვეთური საათები'
    )
