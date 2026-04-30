# -*- coding: utf-8 -*-

from odoo import fields, models


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        help='Analytic account used for this department (e.g. in fuel journal entries). '
             'If not set, fuel journal entries will try to find an analytic account by department name.',
    )
