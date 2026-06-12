from odoo import models, fields


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    x_studio_parent_id = fields.Many2one('hr.department', tracking=True)
    name = fields.Char(tracking=True)
    parent_id = fields.Many2one('hr.department', tracking=True)
    manager_id = fields.Many2one('hr.employee', tracking=True)
    x_studio_location = fields.Many2one('stock.location', tracking=True)
