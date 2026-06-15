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
                        distribution = dict(line.analytic_distribution or {})
                        
                        department = slip.contract_id.department_id
                        if department and hasattr(department, 'analytic_account_id') and department.analytic_account_id:
                            distribution[str(department.analytic_account_id.id)] = 100.0
                            
                        studio_depname = slip.contract_id.x_studio_depname
                        if studio_depname:
                            analytic_account = self.env['account.analytic.account'].search([('name', '=', studio_depname)], limit=1)
                            if analytic_account:
                                distribution[str(analytic_account.id)] = 100.0
                                
                        if distribution:
                            line.write({'analytic_distribution': distribution})
                
                if was_posted:
                    move.action_post()
        return res
