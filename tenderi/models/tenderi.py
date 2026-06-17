from odoo import models, fields, api


class Tenderi(models.Model):
    _name = 'tenderi'
    _description = 'Tenderi'

    department_id = fields.Many2one('hr.department', string='სამსახური')
    purchase_object = fields.Char(string='შესყიდვის ობიექტი')
    cpv_code = fields.Char(string='CPV')
    estimated_cost = fields.Float(string='სავარაუდო ღირებულება')
    tender_notice_number = fields.Char(string='სატენდერო განცხადების ნომერი')
    publicaiton_date = fields.Date(string='გამოცხადების თარიღი')
    open_date = fields.Date(string='გახსნის თარიღი')
    tender_status = fields.Selection([
        ('არ შედგა', 'არ შედგა'),
        ('გამოცხადებულია', 'გამოცხადებულია'),
        ('დასრულებულია უარყოფითი შედეგით', 'დასრულებულია უარყოფითი შედეგით'),
        ('მიმდინარეობს ხელშეკრულების მომზადება', 'მიმდინარეობს ხელშეკრულების მომზადება'),
        ('შერჩევა/შეფასება', 'შერჩევა/შეფასება'),
        ('შეწყვეტილია', 'შეწყვეტილია'),
        ('ხელშეკრულება დადებულია', 'ხელშეკრულება დადებულია')], string='ტენდერის სტატუსი')
    tenderer = fields.Many2one('res.partner', string='პრეტენდენტი')
    final_price = fields.Float(string='საბოლოო ღირებულება')
    funding_year = fields.Char(string='დაფინანსების წელი')
    shesyidvis_safudzveli = fields.Selection([
        ('geo_tender', 'GEO ტენდერი'),
        ('el_tender', 'ელ. ტენდერი')], string='შესყიდვის საფუძველი')
    purchase_plan_line_id = fields.Many2one('purchase.plan.line', string='შესყიდვის გეგმის ხაზი')
    amount_in_plan_line = fields.Boolean(string='თანხა გეგმის ხაზზე', default=False, copy=False)
    tender_type = fields.Selection([
        ('ერთ_წლიანი', 'ერთ წლიანი'),
        ('მრავალ_წლიანი', 'მრავალ წლიანი')
    ],string="ტენდერის ტიპი",
    )
    year_1 = fields.Char(string='წელი 1')
    year_2 = fields.Char(string='წელი 2')
    year_3 = fields.Char(string='წელი 3')
    percent_1 = fields.Float(string='პროცენტი 1')
    percent_2 = fields.Float(string='პროცენტი 2')
    percent_3 = fields.Float(string='პროცენტი 3')

    def _compute_final_price_for_plan(self):
        today_year = str(fields.Date.today().year)
        if self.tender_type == 'მრავალ_წლიანი':
            if today_year == self.year_1:
                percent = self.percent_1
            elif today_year == self.year_2:
                percent = self.percent_2
            elif today_year == self.year_3:
                percent = self.percent_3
            else:
                percent = 0.0
            return self.final_price * percent
        return self.final_price or 0.0

    @api.model_create_multi
    def create(self, vals_list):
        add_statuses = {
            'შერჩევა/შეფასება',
            'გამოცხადებულია',
            'მიმდინარეობს ხელშეკრულების მომზადება',
        }
        records = super().create(vals_list)
        for rec in records:
            if rec.tender_status not in add_statuses:
                continue
            if not rec.purchase_plan_line_id:
                continue
            final_price = rec._compute_final_price_for_plan()
            rec.purchase_plan_line_id.tender_amount = (rec.purchase_plan_line_id.tender_amount or 0.0) + final_price
            rec.amount_in_plan_line = True
        return records

    def write(self, vals):
        add_statuses = {
            'შერჩევა/შეფასება',
            'გამოცხადებულია',
            'მიმდინარეობს ხელშეკრულების მომზადება',
        }
        subtract_statuses = {'ხელშეკრულება დადებულია'}

        old_status_by_id = {}
        if 'tender_status' in vals:
            old_status_by_id = {rec.id: rec.tender_status for rec in self}

        res = super().write(vals)

        if 'tender_status' not in vals:
            return res

        for rec in self:
            old_status = old_status_by_id.get(rec.id)
            new_status = rec.tender_status
            if old_status == new_status:
                continue
            if not rec.purchase_plan_line_id:
                continue
            
            final_price = rec._compute_final_price_for_plan()
            plan_line = rec.purchase_plan_line_id

            if new_status in add_statuses and not rec.amount_in_plan_line:
                plan_line.tender_amount = (plan_line.tender_amount or 0.0) + final_price
                rec.amount_in_plan_line = True
            elif new_status == False and rec.amount_in_plan_line:
                plan_line.tender_amount = (plan_line.tender_amount or 0.0) - final_price
                rec.amount_in_plan_line = False

        return res