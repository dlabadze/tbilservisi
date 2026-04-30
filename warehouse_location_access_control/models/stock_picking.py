# -*- coding: utf-8 -*-

from odoo import models, api, fields


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    # Many2many is simpler/safer here: we only need a list of ids for domains,
    # we don't need a real inverse One2many relation.
    allowed_location_ids = fields.Many2many(
        comodel_name='stock.location',
        string='Allowed Locations',
        compute='_compute_allowed_location_ids',
        store=False,
    )

    @api.depends('picking_type_id', 'picking_type_id.code')
    def _compute_allowed_location_ids(self):
        """Compute allowed location IDs for domain restriction - only for Internal Transfers"""
        user = self.env.user
        Location = self.env['stock.location']
        for record in self:
            # When user has specific allowed locations, always use those
            if record.picking_type_id and record.picking_type_id.code == 'internal':
                if user.allowed_location_ids:
                    record.allowed_location_ids = user.allowed_location_ids
                else:
                    # User has no explicit restrictions -> allow ALL non-view locations
                    record.allowed_location_ids = Location.search([('usage', '!=', 'view')])
            else:
                # For non-internal transfers there should be NO restriction -> all locations
                record.allowed_location_ids = Location.search([('usage', '!=', 'view')])

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        """Override fields_get to set domain for location_id based on context"""
        res = super(StockPicking, self).fields_get(allfields, attributes)
        
        user = self.env.user
        if not user.allowed_location_ids:
            # No restrictions - allow all locations
            return res
        
        allowed_ids = user.allowed_location_ids.ids
        if not allowed_ids:
            return res
        
        # Check if we're creating/editing an Internal Transfer
        picking_type_id = self.env.context.get('default_picking_type_id')
        active_id = self.env.context.get('active_id')
        
        # Try to get picking_type_id from active record if exists
        if not picking_type_id and active_id:
            picking = self.browse(active_id)
            if picking.exists():
                picking_type_id = picking.picking_type_id.id
        
        # If picking_type_id is not available, check if we should restrict anyway
        # For safety, we'll only restrict if we know it's an internal transfer
        if picking_type_id:
            picking_type = self.env['stock.picking.type'].browse(picking_type_id)
            if picking_type.code == 'internal':
                # Only restrict location_id, not location_dest_id
                if 'location_id' in res:
                    res['location_id']['domain'] = [('id', 'in', allowed_ids)]
        
        return res

    @api.model
    def default_get(self, fields_list):
        """Set default location_id for Internal Transfers if user has only one allowed location"""
        res = super(StockPicking, self).default_get(fields_list)
        
        # Check if this is Internal Transfer creation
        picking_type_id = self.env.context.get('default_picking_type_id') or res.get('picking_type_id')
        
        if picking_type_id:
            picking_type = self.env['stock.picking.type'].browse(picking_type_id)
            if picking_type.code == 'internal':
                user = self.env.user
                # Check if user has location restrictions
                if user.allowed_location_ids:
                    allowed_ids = user.allowed_location_ids.ids
                    if allowed_ids:
                        # Always set the FIRST allowed location as default (user's first choice)
                        # but don't override if a default is already defined
                        if (fields_list is None or 'location_id' in fields_list) and not res.get('location_id'):
                            res['location_id'] = allowed_ids[0]
        
        return res

    @api.onchange('picking_type_id', 'allowed_location_ids')
    def _onchange_picking_type_location_domain(self):
        """Set domain for location_id when picking type changes - only for Internal Transfers"""
        # Force recompute of allowed_location_ids
        self._compute_allowed_location_ids()
        return self._set_location_domain()
    
    @api.onchange('location_id', 'location_dest_id')
    def _onchange_location_domain(self):
        """Set domain when location fields change - only for Internal Transfers"""
        return self._set_location_domain()
    
    def _set_location_domain(self):
        """Set domain for location_id - can be called from onchange or other methods"""
        user = self.env.user
        
        # Only restrict for Internal Transfers
        if self.picking_type_id and self.picking_type_id.code == 'internal':
            if user.allowed_location_ids:
                allowed_ids = user.allowed_location_ids.ids
                if allowed_ids:
                    # Auto-select the FIRST allowed location if location_id is not set
                    if not self.location_id:
                        self.location_id = allowed_ids[0]
                    
                    # Only restrict location_id, not location_dest_id
                    return {'domain': {'location_id': [('id', 'in', allowed_ids)]}}
        
        # No restrictions or not internal transfer - return empty domain (all locations available)
        return {'domain': {}}
    

