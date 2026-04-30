from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class RepairOrder(models.Model):
    _inherit = "repair.order"

    @api.constrains("picking_type_id", "location_id")
    def _rlpf_check_location_required_for_repair(self):
        for rec in self:
            code = (getattr(getattr(rec, "picking_type_id", False), "code", "") or "").lower()
            if code == "repair" and not rec.location_id:
                raise ValidationError(_("როცა ოპერაციის ტიპი არის Repair, აუცილებელია Location ველის შევსება."))


