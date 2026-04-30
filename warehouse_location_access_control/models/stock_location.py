# -*- coding: utf-8 -*-

from odoo import models, api


class StockLocation(models.Model):
    _inherit = 'stock.location'

    def _get_allowed_location_ids_from_context(self):
        """(Disabled) Helper method for additional location restrictions.

        We now rely only on the domain defined on `stock.picking.location_id`,
        so this method always returns None (no extra filtering here).
        """
        return None

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """Override name_search to restrict locations for Internal Transfers based on user permissions"""
        args = list(args or [])
        
        allowed_ids = self._get_allowed_location_ids_from_context()
        if allowed_ids is not None:
            if allowed_ids:
                args = [('id', 'in', allowed_ids)] + args
            else:
                # No allowed locations - return empty
                return []
        
        return super(StockLocation, self).name_search(name=name, args=args, operator=operator, limit=limit)

    @api.model
    def search(self, args, offset=0, limit=None, order=None):
        """Override search to restrict locations for Internal Transfers based on user permissions"""
        args = list(args or [])
        
        allowed_ids = self._get_allowed_location_ids_from_context()
        if allowed_ids is not None:
            if allowed_ids:
                args = [('id', 'in', allowed_ids)] + args
            else:
                # No allowed locations - return empty recordset
                return self.browse()
        
        return super(StockLocation, self).search(args, offset=offset, limit=limit, order=order)

