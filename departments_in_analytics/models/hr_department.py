from odoo import api, fields, models


class HrDepartment(models.Model):
    _inherit = 'hr.department'

    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        copy=False,
        ondelete='set null',
    )

    @api.model_create_multi
    def create(self, vals_list):
        departments = super().create(vals_list)
        for dept in departments:
            dept._sync_analytic_account()
        return departments

    def write(self, vals):
        res = super().write(vals)
        if 'name' in vals or 'parent_id' in vals:
            for dept in self:
                if 'name' in vals:
                    existing = self.env['account.analytic.account'].sudo().search(
                        [('name', '=', dept.name)], limit=1
                    )
                    if existing:
                        dept.sudo().analytic_account_id = existing
                    elif dept.analytic_account_id:
                        dept.analytic_account_id.sudo().name = dept.name
                if 'parent_id' in vals and dept.analytic_account_id:
                    plan_name = 'სამსახური' if dept.parent_id else 'დეპარტამენტი'
                    plan = self.env['account.analytic.plan'].sudo().search(
                        [('name', '=', plan_name)], limit=1
                    )
                    if plan:
                        dept.analytic_account_id.sudo().plan_id = plan
        return res

    def _sync_analytic_account(self):
        if self.analytic_account_id:
            return
        existing = self.env['account.analytic.account'].sudo().search(
            [('name', '=', self.name)], limit=1
        )
        if existing:
            self.sudo().analytic_account_id = existing
            return
        plan_name = 'სამსახური' if self.parent_id else 'დეპარტამენტი'
        plan = self.env['account.analytic.plan'].sudo().search([('name', '=', plan_name)], limit=1)
        if not plan:
            return
        analytic = self.env['account.analytic.account'].sudo().create({
            'name': self.name,
            'plan_id': plan.id,
        })
        self.sudo().analytic_account_id = analytic

    def action_sync_analytic_account(self):
        for dept in self:
            plan_name = 'სამსახური' if dept.parent_id else 'დეპარტამენტი'
            plan = self.env['account.analytic.plan'].sudo().search(
                [('name', '=', plan_name)], limit=1
            )
            existing = self.env['account.analytic.account'].sudo().search(
                [('name', '=', dept.name)], limit=1
            )
            if existing:
                if plan:
                    existing.sudo().plan_id = plan
                dept.sudo().analytic_account_id = existing
            else:
                if not plan:
                    continue
                analytic = self.env['account.analytic.account'].sudo().create({
                    'name': dept.name,
                    'plan_id': plan.id,
                })
                dept.sudo().analytic_account_id = analytic
