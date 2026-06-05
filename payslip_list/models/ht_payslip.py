from odoo import models, fields, api


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    line_contract_wage = fields.Float(
        string='საშტატო ხელფასი',
        compute='_compute_contract_wage',
        store=True,
        group_operator='sum'
    )
    line_salary = fields.Float(
        string='ხელფასი',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_leave = fields.Float(
        string='შვებულება',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_bulletin = fields.Float(
        string='ბიულეტენი',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_bonus = fields.Float(
        string='პრემია',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_help = fields.Float(
        string='დახმარება',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_overtime = fields.Float(
        string='ზეგანაკვეთური ხელფასი',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_letter_plus = fields.Float(
        string='წერილი +',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_letter_minus = fields.Float(
        string='წერილი -',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_gross = fields.Float(
        string='სულ დარიცხული',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_pension = fields.Float(
        string='საპენსიო ფონდი',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_taxable = fields.Float(
        string='დასაბეგრი დარიცხვა',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_tax_exemption = fields.Float(
        string='საშემოსავლო შეღავათი',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_income_tax = fields.Float(
        string='საშემოსავლო',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_net = fields.Float(
        string='ხელზე ასაღები ხელფასი',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_charity = fields.Float(
        string='ქველმოქმედება',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_execution = fields.Float(
        string='საარსრულებო ფურცელი',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_alimony = fields.Float(
        string='ალიმენტი',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_insurance = fields.Float(
        string='დაზღვევა',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_fitpass = fields.Float(
        string='ფიტპასი',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_solidarity = fields.Float(
        string='სოლიდარობის ფონდი',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_prof_union = fields.Float(
        string='პროფკავშირი',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_prof_union_meria = fields.Float(
        string='პროფკავშირი მერია',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_fine = fields.Float(
        string='ჯარიმა',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_other_deductions = fields.Float(
        string='სხვა დაკავებები',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_transfer_salary = fields.Float(
        string='გადასარიცხი ხელფასი',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )

    @api.depends('contract_id', 'contract_id.wage')
    def _compute_contract_wage(self):
        for slip in self:
            slip.line_contract_wage = slip.contract_id.wage if slip.contract_id else 0.0

    @api.depends('line_ids.total', 'line_ids.salary_rule_id.name')
    def _compute_lines(self):
        code_to_field = {
            'ხელფასი': 'line_salary',
            'შვებულება': 'line_leave',
            'ბიულეტენი': 'line_bulletin',
            'პრემია': 'line_bonus',
            'დახმარება': 'line_help',
            'ზეგანაკვეთური ხელფასი': 'line_overtime',
            'წერილი +': 'line_letter_plus',
            'წერილი -': 'line_letter_minus',
            'სულ დარიცხული': 'line_gross',
            'საპენსიო ფონდი': 'line_pension',
            'დასაბეგრი დარიცხვა': 'line_taxable',
            'საშემოსავლო შეღავათი': 'line_tax_exemption',
            'საშემოსავლო': 'line_income_tax',
            'ხელზე ასაღები ხელფასი': 'line_net',
            'ქველმოქმედება': 'line_charity',
            'საარსრულებო ფურცელი': 'line_execution',
            'ალიმენტი': 'line_alimony',
            'დაზღვევა': 'line_insurance',
            'ფიტპასი': 'line_fitpass',
            'სოლიდარობის ფონდი': 'line_solidarity',
            'პროფკავშირი': 'line_prof_union',
            'პროფკავშირი მერია': 'line_prof_union_meria',
            'ჯარიმა': 'line_fine',
            'სხვა დაკავებები': 'line_other_deductions',
            'გადასარიცხი ხელფასი': 'line_transfer_salary',
        }

        for slip in self:
            code_map = {l.salary_rule_id.name: l.total for l in slip.line_ids}

            for field_name in code_to_field.values():
                setattr(slip, field_name, 0.0)

            for code, field_name in code_to_field.items():
                if code in code_map:
                    setattr(slip, field_name, code_map[code])
