from odoo import api, models


class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    @api.onchange('category_id', 'brdzaneba_employee_id', 'brdzaneba_date')
    def _onchange_transfer_brdzaneba_safudzveli(self):
        for rec in self:
            if not rec._is_transfer_brdzaneba_category():
                continue

            parts = []
            if rec.brdzaneba_employee_id and rec.brdzaneba_employee_id.name:
                parts.append(rec.brdzaneba_employee_id.name)
            if rec.brdzaneba_date:
                parts.append(rec.brdzaneba_date.strftime('%d.%m.%Y'))

            rec.brdzaneba_safudzveli = ' '.join(parts) if parts else False

    def _is_transfer_brdzaneba_category(self):
        self.ensure_one()
        if not self.category_id:
            return False

        category_name = (self.category_id.name or '').strip().lower()
        return self.category_id.id == 14 or 'გადაყვან' in category_name
