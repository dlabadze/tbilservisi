# -*- coding: utf-8 -*-
from odoo import models

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def _action_create_account_move(self):
        res = super(HrPayslip, self)._action_create_account_move()
        for slip in self:
            move = slip.move_id
            if move:
                was_posted = move.state == 'posted'
                if was_posted:
                    move.button_draft()
                
                for line in move.line_ids:
                    if line.account_id and line.account_id.code == '3139':
                        account_ids = []
                        
                        department = slip.contract_id.department_id
                        if department and hasattr(department, 'analytic_account_id') and department.analytic_account_id:
                            account_ids.append(str(department.analytic_account_id.id))
                            
                        studio_depname = slip.contract_id.x_studio_depname
                        if studio_depname:
                            analytic_account = self.env['account.analytic.account'].search([('name', '=', studio_depname)], limit=1)
                            if analytic_account:
                                account_ids.append(str(analytic_account.id))
                                
                        if account_ids:
                            combined_key = ",".join(account_ids)
                            distribution = dict(line.analytic_distribution or {})
                            distribution = {k: v for k, v in distribution.items() if v != 100.0}
                            distribution[combined_key] = 100.0
                            line.write({'analytic_distribution': distribution})
                
                if was_posted:
                    move.action_post()
        return res
