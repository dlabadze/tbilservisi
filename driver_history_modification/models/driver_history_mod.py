from odoo import models, fields, api


class FleetVehicleAssignationLog(models.Model):
    _inherit = 'fleet.vehicle.assignation.log'

    # make driver NOT required at model level
    driver_id = fields.Many2one(
        'res.partner',
        string="Driver",
        required=False,
    )

    # add department field
    department_id = fields.Many2one(
        'hr.department',
        string="დეპარტამენტი"
    )


        # Child department (filtered by parent)
    sub_department_id = fields.Many2one(
        'hr.department',
        string="სამსახური"
    )



    @api.onchange('department_id')
    def _onchange_department_id_clear_child(self):
        for rec in self:
            rec.sub_department_id = False