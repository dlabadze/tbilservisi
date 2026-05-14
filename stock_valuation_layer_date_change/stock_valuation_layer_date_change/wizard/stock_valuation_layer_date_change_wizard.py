# -*- coding: utf-8 -*-

from odoo import _, fields, models
from odoo.exceptions import UserError


class StockValuationLayerDateChangeWizard(models.TransientModel):
    _name = 'stock.valuation.layer.date.change.wizard'
    _description = 'Change Stock Valuation Layer Date'

    date = fields.Datetime(
        string='New Date',
        required=True,
        default=fields.Datetime.now,
    )

    def action_apply_date_change(self):
        self.ensure_one()

        if self.env.context.get('active_model') != 'stock.valuation.layer':
            raise UserError(_('This action can only be used from stock valuation layers.'))

        layers = self.env['stock.valuation.layer'].browse(self.env.context.get('active_ids', [])).exists()
        if not layers:
            raise UserError(_('Please select at least one stock valuation layer.'))

        layers.check_access('write')

        self.env.cr.execute(
            """
            UPDATE stock_valuation_layer
               SET create_date = %s
             WHERE id = ANY(%s)
            """,
            [self.date, layers.ids],
        )
        layers.invalidate_recordset(['create_date'])

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Date Updated'),
                'message': _('%s valuation layer(s) were updated.') % len(layers),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
