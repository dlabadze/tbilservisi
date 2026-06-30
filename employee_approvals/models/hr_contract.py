from odoo import models, api, _
from odoo.exceptions import ValidationError
from odoo.osv import expression

class HrContract(models.Model):
    _inherit = 'hr.contract'

    @api.constrains('employee_id', 'state', 'kanban_state', 'date_start', 'date_end')
    def _check_current_contract(self):
        for contract in self.filtered(lambda c: (c.state not in ['draft', 'cancel'] or c.state == 'draft' and c.kanban_state == 'done') and c.employee_id):
            domain = [
                ('id', '!=', contract.id),
                ('employee_id', '=', contract.employee_id.id),
                ('company_id', '=', contract.company_id.id),
                '|',
                    ('state', 'in', ['open', 'close']),
                    '&',
                        ('state', '=', 'draft'),
                        ('kanban_state', '=', 'done') # replaces incoming
            ]

            if not contract.date_end:
                start_domain = []
                end_domain = ['|', ('date_end', '>=', contract.date_start), ('date_end', '=', False)]
            else:
                start_domain = [('date_start', '<=', contract.date_end)]
                end_domain = ['|', ('date_end', '>', contract.date_start), ('date_end', '=', False)]

            domain = expression.AND([domain, start_domain, end_domain])
            if self.search_count(domain):
                raise ValidationError(
                    _(
                        'შეტყობინება!  თანამშრომელზე ერთდროულად ორი კონტრაქტის გატარება ვერ მოხდება. (გარდა დრაფტის და გაუქმებული კონტრაქტისა) თანამშრომელი: %(employee_name)s',
                        employee_name=contract.employee_id.name
                    )
                )
