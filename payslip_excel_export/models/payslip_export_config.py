from odoo import api, fields, models

VIRTUAL_ATT_X = '__att_x__'
VIRTUAL_ATT_D = '__att_d__'
VIRTUAL_ATT_G = '__att_g__'

class PayslipExportConfig(models.Model):
    _name = 'payslip.export.config'
    _description = 'Payslip Export Column Configuration'

    column_ids = fields.One2many(
        'payslip.export.config.column',
        'config_id',
        string='Saved Columns',
    )

    @api.model
    def get_config(self):
        config = self.search([], limit=1)
        if not config:
            config = self.create({})
        return config

    def save_columns(self, wizard_column_ids):
        self.ensure_one()
        self.column_ids.unlink()
        vals_list = []
        for col in wizard_column_ids.sorted('sequence'):
            vals_list.append({
                'config_id': self.id,
                'sequence':    col.sequence,
                'field_name':  col.field_name or False,
                'virtual_key': col.virtual_key or False,
                'label':       col.label,
                'col_width':   col.col_width,
            })
        if vals_list:
            self.env['payslip.export.config.column'].create(vals_list)


class PayslipExportConfigColumn(models.Model):
    _name = 'payslip.export.config.column'
    _description = 'Payslip Export Config Column'
    _order = 'sequence, id'

    config_id = fields.Many2one(
        'payslip.export.config',
        ondelete='cascade',
        required=True,
    )
    sequence = fields.Integer(default=10)
    
    field_name = fields.Selection(
        selection='_get_payslip_fields',
        string='Field',
    )
    virtual_key = fields.Selection([
        (VIRTUAL_ATT_X, 'დასწრება (X)'),
        (VIRTUAL_ATT_D, 'დასვენება (D)'),
        (VIRTUAL_ATT_G, 'გაცდენა (G)'),
    ], string='Virtual Column')
    
    label     = fields.Char(required=True)
    col_width = fields.Integer(default=16)

    @api.model
    def _get_payslip_fields(self):
        fields_records = self.env['ir.model.fields'].sudo().search([
            ('model', '=', 'hr.payslip'),
            ('ttype', 'not in', ['one2many', 'many2many', 'binary', 'html'])
        ])
        return [(f.name, f.field_description) for f in fields_records]
