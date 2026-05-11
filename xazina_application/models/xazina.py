from odoo import models, fields, api, _


class Xazina(models.Model):
    _name = 'xazina'
    _description = 'Xazina'

    date = fields.Date(string='თარიღი')
    year = fields.Char(string='წელი')
    request_number = fields.Char(string='მოთხოვნილი N')
    commintment_number = fields.Char(string='ვალდებულების N')
    finance_source = fields.Char(string='დაფინანსების წყარო')
    commintment_foundation = fields.Char(string='ვალდებულების საფუძველი')
    note_1 = fields.Char(string='შენიშვნა 1')
    note_2 = fields.Char(string='შენიშვნა 2')
    note_3 = fields.Char(string='შენიშვნა 3')
    payment_foundation = fields.Char(string='გადახდის საფუძველი')
    payment_form = fields.Char(string='ანაზღაურების ფორმა')
    analytic_account_id = fields.Many2one('account.analytic.account', string='მუხლის კოდი')
    amount_in_gel = fields.Float(string='თანხა ლარში')
    reciever_name = fields.Char(string='მიმღების სახელი')
    reciever_inn = fields.Char(string='მიმღების საიდენტიფიკაციო კოდი')
    reciever_bank_code = fields.Char(string='მიმღების ბანკის კოდი')
    reciever_bank_name = fields.Char(string='მიმღების ბანკის სახელი')
    reciever_account = fields.Char(string='მიმღების ანგარიში')
    sabiujeto_shemosavlis_saxazino_kodi = fields.Char(string='საბიუჯეტო შემოსავლის სახაზინო კოდი')
    payment_purpose = fields.Char(string='გადახდის დანიშნულება')
    expense_subtype = fields.Char(string='ხარჯის ქვეტიპი')
    saxazino_kodi = fields.Char(string='სახაზინო კოდი')
    xazina_type = fields.Selection([
        ('შემოსავლები', 'შემოსავლები'),
        ('გადარიცხვები', 'გადარიცხვები'),
    ], string='ხაზინის ტიპი', default='შემოსავლები')
    state = fields.Selection([
        ('draft', 'დრაფტი'),
        ('validated', 'გატარებული'),
    ], string='სტატუსი', default='draft')

    bank_statement_line_ids = fields.One2many(
        'account.bank.statement.line',
        'xazina_id',
        string='საბანკო ჩანაწერები',
    )
    bank_line_count = fields.Integer(
        string='საბანკო ჩანაწერების რაოდენობა',
        compute='_compute_bank_line_count',
    )

    @api.depends('bank_statement_line_ids')
    def _compute_bank_line_count(self):
        for rec in self:
            rec.bank_line_count = len(rec.bank_statement_line_ids)

    def action_view_bank_lines(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('საბანკო ჩანაწერები'),
            'res_model': 'account.bank.statement.line',
            'view_mode': 'list,form',
            'domain': [('xazina_id', '=', self.id)],
            'context': {'create': False},
        }

    def action_return_to_draft(self):
        for rec in self:
            for line in rec.bank_statement_line_ids:
                move = line.move_id
                if move and move.state == 'posted':
                    move.button_draft()
            rec.state = 'draft'

    def action_open_xazina_income_import_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'ექსელის ატვირთვა',
            'res_model': 'import.xazina.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                "default_xazina_type": "შემოსავლები"
            },
        }
    
    def action_open_xazina_payment_import_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'ექსელის ატვირთვა',
            'res_model': 'import.xazina.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                "default_xazina_type": "გადარიცხვები"
            },
        }

    def action_open_create_gatareba_wizard(self):
        active_ids = self.env.context.get('active_ids', self.ids)
        records = self.browse(active_ids)
        if not records:
            records = self

        # Determine xazina_type from the selected records
        xazina_type = records[:1].xazina_type if records else 'შემოსავლები'

        wizard = self.env['create.gatareba.wizard'].create({
            'xazina_type': xazina_type,
            'xazina_ids': [(6, 0, records.ids)],
            'journal_id': 82,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': 'გატარებების შექმნა',
            'res_model': 'create.gatareba.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }

