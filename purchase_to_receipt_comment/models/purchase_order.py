from odoo import api, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def button_confirm(self):
        """
        On PO confirmation, ensure the created incoming receipts (stock.picking)
        receive the PO's Studio comment value into the Studio field on picking.
        """
        result = super().button_confirm()
        # Write after super so pickings are created
        for order in self:
            # Safely get the Studio field value from PO; may not exist on some DBs
            po_comment = getattr(order, "x_studio_comment", False)
            # Identify incoming pickings linked to this PO
            pickings = order.picking_ids.filtered(
                lambda p: p.picking_type_id and p.picking_type_id.code == "incoming"
            )
            if not pickings:
                continue
            # Write value to Studio field on picking; ignore if field absent
            try:
                pickings.write({"x_studio_text_field_75h_1j6i8foen": po_comment or False})
            except Exception:
                # If the Studio field does not exist on this DB, skip silently
                # to avoid blocking PO confirmation.
                continue
        return result


