import re

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class PurchaseRequisition(models.Model):
    _inherit = 'purchase.requisition'

    delivery_type = fields.Selection(
        selection=[
            ('მოკლევადიანი', 'ერთწლიანი'),
            ('გრძელვადიანი', 'მრავალწლიანი'),
        ],
        string='მოწოდების ტიპი',
    )
    purchase_method = fields.Selection(
        selection=[
            ('1', 'კონსოლიდირებული შესყიდვა'),
            ('2', 'გამარტივებული შესყიდვა'),
            ('3', 'ელექტრონული'),
            ('4', 'კონკურსი'),
            ('5', 'სპეც. წესი (გამარტივებული)'),
            ('6', 'სპეც. წესი (GEO ტენდერი)'),
        ],
        string='შესყიდვის საშუალება',
    )
    purchase_basis = fields.Selection(
        selection=[
            ('1', 'ზღვრების შესაბამისად'),
            ('2', 'ექსკლუზივი'),
            ('3', 'გადაუდებელი'),
            ('4', 'ხარისხის გაუარესება'),
            ('5', '"დ" ქვეპუნქტი'),
            ('6', 'ნორმატიული აქტით დადგენილი გადასახადები'),
            ('7', 'განსაზღვრული წლოვანების ავტოსატრანსპორტო საშუალებები'),
            ('8', 'წარმომადგენლობითი ხარჯები'),
        ],
        string='შესყიდვის საფუძველი',
    )
    pirgasamtexlo = fields.Float(string='პირგასამტეხლო', digits=(5, 2))
    purchase_plan_id = fields.Many2one('purchase.plan', string='purchase plan')
    purchase_plan_line_id = fields.Many2one(
        comodel_name='purchase.plan.line',
        string='purchase plan line',
    )
    supplier_id_code = fields.Char(related='vendor_id.vat')
    date_1 = fields.Char(string='თარიღი')
    date_2 = fields.Char(string='თარიღი')
    date_3 = fields.Char(string='თარიღი')

    percentage_1 = fields.Float(string='პროცენტი', digits=(5, 2))
    percentage_2 = fields.Float(string='პროცენტი', digits=(5, 2))
    percentage_3 = fields.Float(string='პროცენტი', digits=(5, 2))
    department_id = fields.Many2one('hr.department', string='სამსახური')
    spa_or_cmr_number = fields.Char(string='SPA ან CMR ნომერი')

    @api.constrains('percentage_1', 'percentage_2', 'percentage_3')
    def _check_percentages_sum(self):
        for rec in self:
            total = rec.percentage_1 + rec.percentage_2 + rec.percentage_3
            if total > 1:
                total = total * 100
                raise ValidationError(
                    _('პროცენტების ჯამი არუნდა აღემატებოდეს 100%-ს! '
                      f'მიმდინარე ჯამი: {total:.2f}%')
                )

    def write(self, vals):
        res = super().write(vals)
        header_keys = (
            'delivery_type',
            'date_1', 'date_2', 'date_3',
            'percentage_1', 'percentage_2', 'percentage_3',
        )
        if any(k in vals for k in header_keys):
            lines = self.env['purchase.requisition.line'].search(
                [('requisition_id', 'in', self.ids)]
            )
            lines._recompute_pcon_for_plan_lines()
        return res


class PurchaseRequisitionLine(models.Model):
    _inherit = 'purchase.requisition.line'

    @api.model
    def _percentage_to_fraction(self, value):
        """Accept 0–1 (fraction) or 0–100 (percent); return fraction of base amount."""
        if value is None or value is False:
            return 0.0
        p = float(value)
        if p > 1.0:
            return p / 100.0
        return p

    def _parse_year_from_char(self, date_str):
        if not date_str:
            return None
        s = str(date_str).strip()
        if not s:
            return None
        match = re.search(r'\b(19|20)\d{2}\b', s)
        if match:
            return int(match.group(0))
        return None

    def _long_term_fraction_for_current_year(self, requisition):
        """Match context year to date_1 / date_2 / date_3 and return the paired percentage as fraction."""
        if not requisition:
            return None
        year = fields.Date.context_today(self).year
        slots = (
            (requisition.date_1, requisition.percentage_1),
            (requisition.date_2, requisition.percentage_2),
            (requisition.date_3, requisition.percentage_3),
        )
        for date_val, pct_val in slots:
            slot_year = self._parse_year_from_char(date_val)
            if slot_year == year:
                return self._percentage_to_fraction(pct_val)
        return None

    def _pcon_line_contribution(self):
        """Amount that rolls into purchase.plan.line pcon_am for this requisition line."""
        self.ensure_one()
        req = self.requisition_id
        line_total = self.line_total or 0.0
        if not req or req.delivery_type != 'გრძელვადიანი':
            return line_total
        base = line_total
        if not base and self.total_amount:
            base = float(self.total_amount)
        if not base:
            return 0.0
        fraction = self._long_term_fraction_for_current_year(req)
        if fraction is None:
            return 0.0
        return base * fraction

    @api.model
    def _recompute_plan_line_pcon_am(self, plan_line_id):
        if not plan_line_id:
            return
        lines = self.search([('purchase_plan_line_id', '=', plan_line_id)])
        total = sum(line._pcon_line_contribution() for line in lines)
        plan_line = self.env['purchase.plan.line'].browse(plan_line_id)
        tender_amount = getattr(plan_line, 'tender_amount', 0.0) or 0.0
        self.env.cr.execute(
            """
            UPDATE purchase_plan_line
            SET pcon_am = %s,
                pc_re_am = pu_ac_am - %s - %s
            WHERE id = %s
            """,
            (total, total, tender_amount, plan_line_id),
        )

    def _recompute_pcon_for_plan_lines(self):
        for pid in set(self.mapped('purchase_plan_line_id').ids):
            if pid:
                self._recompute_plan_line_pcon_am(pid)

    def _force_update_plan_amounts(self):
        plan_ids = set()
        for line in self:
            if line.purchase_plan_line_id:
                plan_ids.add(line.purchase_plan_line_id.id)
        for pid in plan_ids:
            self._recompute_plan_line_pcon_am(pid)

    def write(self, vals):
        old_plan_lines = self.mapped('purchase_plan_line_id')
        res = super().write(vals)
        for pl in old_plan_lines | self.mapped('purchase_plan_line_id'):
            if pl:
                self._recompute_plan_line_pcon_am(pl.id)
        return res

    def unlink(self):
        plan_lines = self.mapped('purchase_plan_line_id')
        res = super().unlink()
        for pl in plan_lines:
            if pl:
                self._recompute_plan_line_pcon_am(pl.id)
        return res

