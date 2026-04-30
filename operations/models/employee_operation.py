from odoo import models, fields, api


class EmployeeOperation(models.Model):
    _name = 'employee.operation'
    _description = 'ოპერაციები დასაქმებულებზე'

    name = fields.Char(
        string="ოპერაციის დასახელება",
        required=True,
        translate=True
    )
