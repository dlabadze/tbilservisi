from odoo import models, fields,api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    get_invoice_id_helper = fields.Char(
        string='ფაქტურის ნომერი',
        # compute='_compute_get_invoice_id',
        store=True,
        readonly=False
    )
    get_zednd_number_helper = fields.Char(
        string='ზედნადების ნომერი',
        compute='_compute_get_zednd_number',
        store=True,
        readonly=False
    )

    # @api.depends('combined_invoice_id.get_invoice_id')
    # def _compute_get_invoice_id(self):
    #     # raise UserError(self)
    #     for record in self:
    #         if record.combined_invoice_id.get_invoice_id and record.get_invoice_id:
    #             record.get_invoice_id_helper = record.get_invoice_id
    #         else:
    #             record.get_invoice_id_helper = record.get_invoice_id_helper

    # def _compute_get_invoice_id(self):
    #     _logger.info("_compute_get_invoice_id")
    #     for rec in self:
    #         if not rec.get_invoice_id_helper:
    #             rec.get_invoice_id_helper = rec.get_invoice_id
    #         else:
    #             rec.get_invoice_id_helper = rec.get_invoice_id_helper

    @api.depends('combined_invoice_id.invoice_number')
    def _compute_get_zednd_number(self):
        for record in self:
            if record.combined_invoice_id.invoice_number and record.invoice_number:
                record.get_zednd_number_helper = record.invoice_number
            else:
                record.get_zednd_number_helper = record.get_zednd_number_helper

    def action_update_invoice_id_helper(self):
        """Update get_invoice_id_helper field for selected records"""
        for record in self:
            _logger.info('==============================================')
            _logger.info(f"=={record.get_invoice_id}==")
            _logger.info(f"=={record.get_invoice_id_helper}==")
            if not record.get_invoice_id_helper and record.get_invoice_id:
                _logger.info(record.get_invoice_id)
                _logger.info(record.get_invoice_id_helper)
                record.write({'get_invoice_id_helper': record.get_invoice_id})
                _logger.info(record.get_invoice_id_helper)

