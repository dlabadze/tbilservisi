from odoo import models, fields, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    driver_department_id = fields.Many2one(
        'hr.department',
        string="Driver Department",
        compute='_compute_driver_department_id',
        store=True,
    )

    @api.depends(
        'date',
        'move_id.stock_move_id.x_studio_transport',
        'move_id.stock_move_id.x_studio_transport.log_drivers.date_start',
        'move_id.stock_move_id.x_studio_transport.log_drivers.date_end',
        'move_id.stock_move_id.x_studio_transport.log_drivers.sub_department_id',
    )
    def _compute_driver_department_id(self):
        for line in self:
            line.driver_department_id = False
            vehicle = line.move_id.stock_move_id.x_studio_transport
            if not vehicle or not line.date:
                continue
            aml_date = line.date
            for log in vehicle.log_drivers:
                if not log.date_start:
                    continue
                if log.date_end:
                    if log.date_start <= aml_date <= log.date_end:
                        line.driver_department_id = log.sub_department_id
                        break
                else:
                    if aml_date >= log.date_start:
                        line.driver_department_id = log.sub_department_id
                        break
