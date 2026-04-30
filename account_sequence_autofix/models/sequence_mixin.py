from odoo import api, models


class SequenceMixin(models.AbstractModel):
    _inherit = "sequence.mixin"

    @api.constrains(lambda self: (self._sequence_field, self._sequence_date_field))
    def _constrains_date_sequence(self):
        if self and self._name == "account.move":
            return True
        return super()._constrains_date_sequence()
