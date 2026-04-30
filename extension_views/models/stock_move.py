from odoo import models, fields, api

class StockMove(models.Model):
    _inherit = 'stock.move'

    barcode = fields.Char(related='product_id.barcode', string="Barcode", store=True, readonly=False)
    unit_id = fields.Selection([
        ('1', 'ცალი'),
        ('2', 'კგ'),
        ('3', 'გრამი'),
        ('4', 'ლიტრი'),
        ('5', 'ტონა'),
        ('7', 'სანტიმეტრი'),
        ('8', 'მეტრი'),
        ('9', 'კილომეტრი'),
        ('10', 'კვ.სმ'),
        ('11', 'კვ.მ'),
        ('12', 'მ³'),
        ('13', 'მილილიტრი'),
        ('99', 'სხვა'),
    ], related='product_id.unit_id', string="rs.ge ერთეული", store=True, readonly=False)
    unit_txt = fields.Char(related='product_id.unit_txt', string="სხვა ერთეული", store=True, readonly=False)
    rs_quantity = fields.Float(string='RS Quantity', help='Quantity to send to RS.GE for correction', default=0.0)

    cost_including_tax = fields.Float(string="Cost Including Tax", compute='_compute_cost_including_tax', store=True, readonly=False)
    tax_included = fields.Boolean(string="Tax Included", default=False, readonly=False)
    tax_id = fields.Many2one('account.tax', string='Tax', store=True, readonly=False)
    unit_price = fields.Float(string="Unit Price")
    total_price = fields.Float(string="Total Price")

    @api.onchange('unit_price', 'tax_id', 'quantity', 'state')
    def _compute_cost_including_tax(self):
        for line in self:
            if line.tax_id:
                # Check if tax is already included in the price
                if line.tax_id.price_include or line.tax_included:
                    # Tax is already included, just multiply by quantity
                    line.cost_including_tax = line.unit_price * line.product_uom_qty
                else:
                    # Tax is not included, add it
                    tax_rate = 1 + line.tax_id.amount / 100
                    line.cost_including_tax = line.unit_price * tax_rate * line.product_uom_qty
            else:
                # No tax, just price * quantity
                line.cost_including_tax = line.unit_price * line.product_uom_qty

    @api.model
    def create(self, vals):
        move = super(StockMove, self).create(vals)

        if move.sale_line_id:
            move._set_price_and_tax_from_order_line(move.sale_line_id, 'sale')
        elif move.purchase_line_id:
            move._set_price_and_tax_from_order_line(move.purchase_line_id, 'purchase')

        return move

    def _set_price_and_tax_from_order_line(self, order_line, order_type):
        # Set the unit price from the order line
        self.write({
            'unit_price': order_line.price_unit,
            'total_price': order_line.price_total,
        })

        # Check each tax in order_line tax field and assign it to stock.move.tax_id
        if order_type == 'sale':
            taxes = order_line.tax_id
        else:  # purchase
            taxes = order_line.taxes_id

        if taxes:
            tax = taxes.filtered(lambda t: t.type_tax_use == order_type)
            if tax:
                self.write({
                    'tax_id': tax[0].id  # Use the first tax (or modify logic as needed)
                })

        # Recalculate the cost including tax after setting the price and tax
        self._compute_cost_including_tax()

    @api.onchange('product_id')
    def _onchange_product_id(self):
        "Automatically set tax_id from product when product is selected"
        if not self.product_id:
            self.tax_id = False
            if not self.name:
                self.name = ''
            return
        
        # Set name from product if not already set (default Odoo behavior)
        if not self.name or self.name == '':
            self.name = self.product_id.name
        
        # Determine if it's a sale or purchase move based on picking type
        order_type = 'sale'
        if self.picking_id and self.picking_id.picking_type_id:
            if self.picking_id.picking_type_id.code == 'incoming':
                order_type = 'purchase'
        
        # Get taxes from product
        if order_type == 'sale':
            taxes = self.product_id.taxes_id
        else:  # purchase
            taxes = self.product_id.supplier_taxes_id
        
        # Set tax_id to first matching tax (similar to sale order line behavior)
        if taxes:
            tax = taxes.filtered(lambda t: t.type_tax_use == order_type)
            if tax:
                self.tax_id = tax[0].id
            else:
                self.tax_id = False
        else:
            self.tax_id = False

    def _set_tax_from_product(self):
        "Set tax from product, similar to sale order line default behavior"
        if not self.product_id:
            return
        
        # Determine if it's a sale or purchase move based on picking type
        order_type = 'sale'
        if self.picking_id and self.picking_id.picking_type_id:
            if self.picking_id.picking_type_id.code == 'incoming':
                order_type = 'purchase'
        
        # Get taxes from product
        if order_type == 'sale':
            taxes = self.product_id.taxes_id
        else:  # purchase
            taxes = self.product_id.supplier_taxes_id
        
        if taxes:
            # Filter taxes by type_tax_use
            tax = taxes.filtered(lambda t: t.type_tax_use == order_type)
            if tax:
                self.write({
                    'tax_id': tax[0].id
                })
