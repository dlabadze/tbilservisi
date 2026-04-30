from odoo import models, api, fields
import logging

_logger = logging.getLogger(__name__)


class StockPickingBarcodePrompt(models.Model):
    """
    Override stock.picking to ensure destination location is always prompted
    when scanning barcodes for internal transfers.
    """
    _inherit = "stock.picking"

    def _get_stock_barcode_data(self):
        """
        Override barcode data to include ALL available locations
        instead of only children of the picking's destination.
        
        Also auto-adds product from picking_type.x_studio_car_sawvav if:
        - The field is set with a product
        - The product is not already in move lines
        - This is the first time opening the picking in barcode
        
        Additionally sets date_of_transfer to current datetime when opening in barcode.
        """
        self = self.with_context(barcode_view=True, from_barcode=True)
        data = super()._get_stock_barcode_data()
        
        self._set_date_of_transfer()
        self._auto_add_car_sawvav_product()
        
        if data and isinstance(data, dict):
            all_locations = self.env['stock.location'].search([
                ('usage', 'in', ['internal', 'transit']),
                '|',
                ('company_id', '=', False),
                ('company_id', '=', self.env.company.id),
            ], order='complete_name')
            
            location_keys = [
                'destination_locations_ids',
                'source_location_ids',
            ]
            
            for key in location_keys:
                if key in data:
                    data[key] = all_locations.ids
        
        return data

    def _set_date_of_transfer(self):
        """
        Set date_of_transfer to current datetime when opening picking in barcode interface.
        Only sets if the field exists and is not already set.
        """
        self.ensure_one()
        
        if not hasattr(self, 'date_of_transfer'):
            return
        
        if not self.date_of_transfer:
            try:
                self.date_of_transfer = fields.Datetime.now()
            except Exception as e:
                _logger.warning("Failed to set date_of_transfer for picking %s: %s", self.name, str(e))

    def _auto_add_car_sawvav_product(self):
        """
        Auto-add product from picking_type.car_sawvav_product_id to move lines
        if it's not already present.
        """
        self.ensure_one()
        
        context_key = f'car_sawvav_added_{self.id}'
        if self.env.context.get(context_key):
            return
        
        if not self.picking_type_id:
            return
        
        car_product = self.picking_type_id.car_sawvav_product_id
        if not car_product and hasattr(self.picking_type_id, 'x_studio_car_sawvav'):
            car_product = self.picking_type_id.x_studio_car_sawvav
        
        if not car_product:
            return
        
        if not car_product.uom_id:
            return
        
        self.env.flush_all()
        self.invalidate_recordset(['move_line_ids'])
        
        existing_line = self.move_line_ids.filtered(
            lambda line: line.product_id == car_product
        )
        
        if existing_line:
            return
        
        vals = {
            'picking_id': self.id,
            'product_id': car_product.id,
            'product_uom_id': car_product.uom_id.id,
            'location_id': self.location_id.id,
            'location_dest_id': self.location_dest_id.id,
            'quantity': 0,
        }
        
        try:
            self.env.context = dict(self.env.context, **{context_key: True})
            self.env['stock.move.line'].create(vals)
            self.env.flush_all()
        except Exception as e:
            _logger.error("Failed to create move line: %s", str(e))

    @api.model
    def _get_new_picking_values(self, picking_type, location_id=False, location_dest_id=False):
        """
        Override to prevent auto-setting location from default location logic.
        """
        self = self.with_context(barcode_view=True, from_barcode=True)
        return super()._get_new_picking_values(picking_type, location_id, location_dest_id)

    @api.model
    def create(self, vals_list):
        """
        Override create to add barcode context for internal transfers
        and auto-add car_sawvav product if configured.
        """
        if isinstance(vals_list, dict):
            vals_list = [vals_list]
        
        for vals in vals_list:
            picking_type_id = vals.get('picking_type_id')
            if picking_type_id:
                picking_type = self.env['stock.picking.type'].browse(picking_type_id)
                if picking_type.code == 'internal' and not vals.get('location_id'):
                    self = self.with_context(barcode_view=True, from_barcode=True)
                    break
        
        pickings = super(StockPickingBarcodePrompt, self).create(vals_list)
        
        for picking in pickings:
            try:
                picking._auto_add_car_sawvav_product()
            except Exception as e:
                _logger.warning("Failed to auto-add car_sawvav product for picking %s: %s", 
                              picking.name, str(e))
        
        return pickings

    @api.model
    def get_move_lines_by_picking_name(self, picking_name):
        """
        Get move lines for a picking by its name.
        Used by barcode interface to update quantities.
        """
        picking = self.search([('name', '=', picking_name)], limit=1)
        if not picking:
            return []
        
        result = []
        for idx, line in enumerate(picking.move_line_ids, start=1):
            result.append({
                'id': line.id,
                'virtual_id': idx,
                'product_id': line.product_id.id,
                'product_name': line.product_id.name,
                'quantity': line.quantity,
            })
        
        return result

    @api.model
    def update_move_line_quantity(self, move_line_id, quantity):
        """
        Update move line quantity.
        """
        try:
            move_line = self.env['stock.move.line'].browse(move_line_id)
            if not move_line.exists():
                return {'success': False, 'error': 'Move line not found'}
            
            move_line.write({'quantity': quantity})
            
            return {
                'success': True,
                'quantity': move_line.quantity
            }
        except Exception as e:
            _logger.error("Error updating move line quantity: %s", str(e))
            return {'success': False, 'error': str(e)}
