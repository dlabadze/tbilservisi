from odoo import models, fields, api


class StockMoveLineBarcodeLocation(models.Model):
    """
    Override stock.move.line to provide unrestricted location choices
    in barcode interface for destination location.
    """
    _inherit = "stock.move.line"

    @api.depends('picking_id', 'picking_id.location_dest_id', 'picking_id.picking_type_id')
    def _compute_picking_location_dest_id(self):
        """
        Override to return warehouse view location instead of specific destination.
        This allows XML domain ('id', 'child_of', picking_location_dest_id') 
        to show ALL locations in the warehouse.
        """
        for line in self:
            if line.picking_id and line.picking_id.picking_type_id and line.picking_id.picking_type_id.warehouse_id:
                # Return warehouse view location (root) to allow all children
                line.picking_location_dest_id = line.picking_id.picking_type_id.warehouse_id.view_location_id
            else:
                # Fallback to original
                line.picking_location_dest_id = line.picking_id.location_dest_id if line.picking_id else False
    
    picking_location_dest_id = fields.Many2one(
        'stock.location',
        compute='_compute_picking_location_dest_id',
        store=False,
    )

    @api.onchange("picking_id", "product_id", "location_id")
    def _onchange_unrestrict_destination_locations(self):
        """
        Return domain that allows ALL internal/transit locations.
        """
        return {
            "domain": {
                "location_dest_id": [
                    ("usage", "!=", "view"),
                    "|",
                    ("company_id", "=", False),
                    ("company_id", "=", self.env.company.id),
                ]
            }
        }
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        """
        Override to ensure product's default UoM is always used.
        Prevents UoM category mismatch errors.
        """
        res = super()._onchange_product_id()
        
        # Always use product's default UoM to avoid category mismatch
        if self.product_id and self.product_id.uom_id:
            self.product_uom_id = self.product_id.uom_id
        
        return res
    
    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create to force product's UoM and prevent category mismatch.
        This is crucial for barcode interface where products are added programmatically.
        """
        for vals in vals_list:
            product_id = vals.get('product_id')
            if product_id:
                product = self.env['product.product'].browse(product_id)
                if product and product.uom_id:
                    # Force product's default UoM to prevent category mismatch
                    vals['product_uom_id'] = product.uom_id.id
        
        return super().create(vals_list)
