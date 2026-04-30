from odoo import api, fields, models


class AssetOperationType(models.Model):
    _name = "asset.operation.type"
    _description = "Asset Operation Type"

    name = fields.Char(required=True)


class AssetMovement(models.Model):
    _name = "asset.movement"
    _description = "Asset Movement"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    date = fields.Date(string="Date", required=True)
    operation_type_id = fields.Many2one('asset.operation.type', string="Operation Type", required=True)
    employee_id = fields.Many2one('hr.employee', string="Employee")
    location = fields.Many2one('hr.department', string="Location")
    department_id = fields.Many2one('hr.department', string="Department", related='location.parent_id', store=True, readonly=True)
    line_ids = fields.One2many('asset.movement.line', 'movement_id', string="Assets")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed')
    ], string='Status', default='draft', required=True, tracking=True)

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        if self.employee_id and self.employee_id.department_id:
            self.location = self.employee_id.department_id
            # department_id ავტომატურად შეივსება related ველის მეშვეობით
        else:
            self.location = False

    def action_confirm(self):
        """დაადასტურე გადაადგილება"""
        self.write({'state': 'confirmed'})
        
        # განაახლე ძირითადი საშუალებების ველები
        for line in self.line_ids:
            if line.asset_id:
                line.asset_id.write({
                    'x_studio_char_field_3d3_1j6a7c8e7': self.employee_id.name if self.employee_id else False,
                    'x_studio_char_field_76r_1j6a79iuk': self.location.name if self.location else False,
                    'x_studio_char_field_9ct_1j6a2j8b6': self.department_id.name if self.department_id else False,
                })

    def action_draft(self):
        """დაბრუნება Draft-ში"""
        self.write({'state': 'draft'})


class AssetMovementLine(models.Model):
    _name = "asset.movement.line"
    _description = "Asset Movement Line"

    movement_id = fields.Many2one('asset.movement', string="Movement", required=True, ondelete="cascade")
    asset_id = fields.Many2one('account.asset', string="Asset", required=True)
    note = fields.Text(string="Note")

    # საჭირო related ველები, რომ აქტივის ბარათში გამოჩნდეს
    date = fields.Date(related="movement_id.date", store=True, readonly=True)
    operation_type_id = fields.Many2one(related="movement_id.operation_type_id", store=True, readonly=True)
    location = fields.Many2one(related="movement_id.location", store=True, readonly=True)
    department_id = fields.Many2one(related="movement_id.department_id", store=True, readonly=True)
    employee_id = fields.Many2one(related="movement_id.employee_id", store=True, readonly=True)


class AccountAsset(models.Model):
    _inherit = "account.asset"

    movement_line_ids = fields.One2many(
        'asset.movement.line', 'asset_id', string="Movements"
    )
