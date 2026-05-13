from odoo import models, api

class ProductProduct(models.Model):
    _inherit = 'product.product'

    def _prepare_sellers(self, params=False):
        return super(ProductProduct, self.sudo())._prepare_sellers(params)

    def _compute_display_name(self):
        self_sudo = self.sudo()
        for product, product_sudo in zip(self, self_sudo):
            if product_sudo.default_code:
                product.display_name = '[%s] %s' % (
                    product_sudo.default_code,
                    product_sudo.name
                )
            else:
                product.display_name = product_sudo.name