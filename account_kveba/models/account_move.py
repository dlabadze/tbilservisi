from datetime import datetime, timedelta
from odoo import models, fields, api, _


class AccountMove(models.Model):
    _inherit = 'account.move'


    def action_create_picking_chamowera(self):
        self.ensure_one()

        picking_type = self.env['stock.picking.type'].sudo().search([
            ('name', '=', 'ჩამოწერა'),
            ('code', '=', 'internal'),
        ], limit=1)

        source_loc = self.env['stock.location'].sudo().search([
            ('name', '=', 'ზოგადი')
        ], limit=1)

        dest_loc = self.env['stock.location'].sudo().search([
            ('name', '=', 'ჩამოწერის საწყობი')
        ], limit=1)

        product_name = self.journal_id.name if self.journal_id else False
        product = self.env['product.product'].sudo().search([
            ('name', '=', product_name)
        ], limit=1)

        if not picking_type or not source_loc or not product and not dest_loc:
            return

        dest_loc = picking_type.default_location_dest_id or source_loc

        picking = self.env['stock.picking'].sudo().create({
            'picking_type_id': picking_type.id,
            'location_id': source_loc.id,
            'location_dest_id': dest_loc.id,
            'origin': self.name,
            'date_of_transfer': datetime.combine(self.date, datetime.min.time()) + timedelta(hours=8),
        })

        self.env['stock.move'].sudo().create({
            'picking_id': picking.id,
            'name': product.name,
            'product_id': product.id,
            'product_uom_qty': 1.0,
            'product_uom': product.uom_id.id,
            'location_id': source_loc.id,
            'location_dest_id': dest_loc.id,
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'res_id': picking.id,
            'view_mode': 'form',
            'target': 'current',
        }