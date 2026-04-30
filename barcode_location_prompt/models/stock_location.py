from odoo import models, api


class StockLocationBarcodeUnrestricted(models.Model):
    """
    Override stock.location to remove domain restrictions
    when searching for destination locations in barcode interface.
    """
    _inherit = "stock.location"

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        """
        Override search to remove child_of restrictions from domain.
        Only applies when called from barcode interface context.
        """
        # Only modify domain when in barcode context
        if not self.env.context.get('barcode_view') and not self.env.context.get('from_barcode'):
            return super()._search(domain, offset=offset, limit=limit, order=order)
        
        # Check if domain has child_of restriction
        has_child_restriction = any(
            isinstance(item, (list, tuple)) and len(item) >= 3 and 
            item[1] in ('child_of', 'parent_of')
            for item in domain
        )
        
        if not has_child_restriction:
            return super()._search(domain, offset=offset, limit=limit, order=order)
        
        # Build new domain without child_of/parent_of
        new_domain = []
        skip_next_operator = False
        i = 0
        
        while i < len(domain):
            item = domain[i]
            
            # Check if this is a child_of/parent_of condition
            if isinstance(item, (list, tuple)) and len(item) >= 3 and item[1] in ('child_of', 'parent_of'):
                # Skip this condition and mark to handle operator
                skip_next_operator = True
                i += 1
                continue
            
            # Handle operators
            if item in ('&', '|', '!'):
                if skip_next_operator:
                    skip_next_operator = False
                    i += 1
                    continue
            
            new_domain.append(item)
            i += 1
        
        # Clean up leading operators
        while new_domain and new_domain[0] in ('&', '|', '!'):
            new_domain.pop(0)
        
        # Clean up trailing operators  
        while new_domain and new_domain[-1] in ('&', '|', '!'):
            new_domain.pop()
        
        return super()._search(new_domain if new_domain else [], offset=offset, limit=limit, order=order)
