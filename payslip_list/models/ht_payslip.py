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
    line_overtime_deduction = fields.Float(
        string='ზეგანაკვეთურის დაქვითვა',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_gross = fields.Float(
        string='დარიცხული ხელფასი',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_pension = fields.Float(
        string='საპენსიო 2%',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_taxable = fields.Float(
        string='დასაბეგრი ხელფასი',
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
    line_insurance = fields.Float(
        string='სტანდარტ დაზღვევა',
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
    line_charity = fields.Float(
        string='ქველმოქმედება',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_execution = fields.Float(
        string='სააღსრულებო ფურცელი',
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
    line_disciplinary_fine = fields.Float(
        string='დისციპლინარული ჯარიმა',
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
    line_alimony = fields.Float(
        string='ალიმენტი',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_other_deductions = fields.Float(
        string='სხვადასხვა',
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
    line_bulletin = fields.Float(
        string='ბიულეტენი',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_overtime = fields.Float(
        string='ზეგანაკვეთური',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_bonus = fields.Float(
        string='პრემია/წახალისება/ჯილდო',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_supplement = fields.Float(
        string='დანამატი',
        compute='_compute_lines',
        store=True,
        group_operator='sum'
    )
    line_illuminations = fields.Float(
        string='ილუმინაციები',
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
    line_compensation = fields.Float(
        string='კომპენსაცია',
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

    @api.depends('contract_id', 'contract_id.wage')
    def _compute_contract_wage(self):
        for slip in self:
            slip.line_contract_wage = slip.contract_id.wage if slip.contract_id else 0.0

    @api.depends('line_ids.total', 'line_ids.salary_rule_id.name')
    def _compute_lines(self):
        code_to_field = {
            'ხელფასი': 'line_salary',
            'შვებულება': 'line_leave',
            'წერილი +': 'line_letter_plus',
            'წერილი -': 'line_letter_minus',
            'ზეგანაკვეთურის დაქვითვა': 'line_overtime_deduction',
            'დარიცხული ხელფასი': 'line_gross',
            'საპენსიო 2%': 'line_pension',
            'დასაბეგრი ხელფასი': 'line_taxable',
            'საშემოსავლო': 'line_income_tax',
            'ხელზე ასაღები ხელფასი': 'line_net',
            'სტანდარტ დაზღვევა': 'line_insurance',
            'ფიტპასი': 'line_fitpass',
            'სოლიდარობის ფონდი': 'line_solidarity',
            'ქველმოქმედება': 'line_charity',
            'სააღსრულებო ფურცელი': 'line_execution',
            'პროფკავშირი': 'line_prof_union',
            'პროფკავშირი მერია': 'line_prof_union_meria',
            'დისციპლინარული ჯარიმა': 'line_disciplinary_fine',
            'ჯარიმა': 'line_fine',
            'ალიმენტი': 'line_alimony',
            'სხვადასხვა': 'line_other_deductions',
            'გადასარიცხი ხელფასი': 'line_transfer_salary',
            'ბიულეტენი': 'line_bulletin',
            'ზეგანაკვეთური': 'line_overtime',
            'პრემია/წახალისება/ჯილდო': 'line_bonus',
            'დანამატი': 'line_supplement',
            'ილუმინაციები': 'line_illuminations',
            'დახმარება': 'line_help',
            'კომპენსაცია': 'line_compensation',

            'ზეგანაკვეთური ხელფასი': 'line_overtime',
            'სულ დარიცხული': 'line_gross',
            'საპენსიო ფონდი': 'line_pension',
            'დასაბეგრი დარიცხვა': 'line_taxable',
            'დაზღვევა': 'line_insurance',
            'საარსრულებო ფურცელი': 'line_execution',
            'სხვა დაკავებები': 'line_other_deductions',
            'პრემია': 'line_bonus',
        }

        for slip in self:
            code_map = {l.salary_rule_id.name.strip(): l.total for l in slip.line_ids if l.salary_rule_id}

            for field_name in set(code_to_field.values()):
                setattr(slip, field_name, 0.0)
            
            slip.line_tax_exemption = 0.0

            for rule_name, total_amt in code_map.items():
                if rule_name in code_to_field:
                    field_name = code_to_field[rule_name]
                    current_val = getattr(slip, field_name)
                    setattr(slip, field_name, current_val + total_amt)
                elif rule_name == 'საშემოსავლო შეღავათი':
                    slip.line_tax_exemption += total_amt
