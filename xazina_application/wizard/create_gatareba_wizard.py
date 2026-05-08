from odoo import models, fields, api, _
from odoo.exceptions import UserError

JOURNAL_ID = 82
TRANSIT_ACCOUNT = {
    'გადარიცხვები': '1201',
    'შემოსავლები': '1243',
}


class CreateGatarebWizard(models.TransientModel):
    _name = 'create.gatareba.wizard'
    _description = 'გატარებების შექმნის ვიზარდი'

    xazina_type = fields.Selection([
        ('შემოსავლები', 'შემოსავლები'),
        ('გადარიცხვები', 'გადარიცხვები'),
    ], string='ხაზინის ტიპი', required=True)

    journal_id = fields.Many2one(
        'account.journal',
        string='ჟურნალი',
    )
    transit_account_code = fields.Char(
        string='შუალედური ანგარიში',
        compute='_compute_transit_info',
    )
    xazina_ids = fields.Many2many(
        'xazina',
        string='ხაზინის ჩანაწერები',
    )
    record_count = fields.Integer(
        string='ჩანაწერების რაოდენობა',
        compute='_compute_record_count',
    )

    @api.depends('xazina_ids')
    def _compute_record_count(self):
        for rec in self:
            rec.record_count = len(rec.xazina_ids)

    @api.depends('xazina_type')
    def _compute_transit_info(self):
        for rec in self:
            if rec.xazina_type == 'შემოსავლები':
                rec.transit_account_code = TRANSIT_ACCOUNT.get('შემოსავლები', '')
            else:
                rec.transit_account_code = False

    def _get_journal(self):
        journal = self.journal_id or self.env['account.journal'].browse(JOURNAL_ID)
        if not journal.exists():
            raise UserError(_('ჟურნალი ID=%d ვერ მოიძებნა. შეამოწმეთ კონფიგურაცია.') % JOURNAL_ID)
        return journal

    def _get_transit_account(self):
        code = TRANSIT_ACCOUNT.get(self.xazina_type)
        if not code:
            raise UserError(_('შუალედური ანგარიში განსაზღვრული არ არის ამ ტიპისთვის.'))
        account = self.env['account.account'].search(
            [('code', '=like', code + '%'), ('company_ids', 'in', self.env.company.id)],
            limit=1,
        )
        if not account:
            raise UserError(_('შუალედური ანგარიში კოდით "%s" ვერ მოიძებნა.') % code)
        return account

    def action_create_gatarebebi(self):
        self.ensure_one()

        records = self.xazina_ids
        if not records:
            raise UserError(_('გასაგზავნი ჩანაწერები არ მოიძებნა.'))

        journal = self._get_journal()
        transit_account = self._get_transit_account()

        # გადარიცხვები = outgoing = negative amount
        # შემოსავლები  = incoming = positive amount
        amount_sign = -1 if self.xazina_type == 'გადარიცხვები' else 1

        created_lines = self.env['account.bank.statement.line']

        for xazina in records:
            if not xazina.date:
                raise UserError(
                    _('ჩანაწერს "%s" არ აქვს თარიღი მითითებული.')
                    % (xazina.request_number or str(xazina.id))
                )
            if not xazina.amount_in_gel:
                continue  # skip zero-amount rows

            ref_parts = [
                xazina.request_number,
                xazina.commintment_number,
                xazina.payment_purpose,
            ]
            ref = ' | '.join(p for p in ref_parts if p) or '/'

            line_vals = {
                'journal_id': journal.id,
                'date': xazina.date,
                'amount': amount_sign * xazina.amount_in_gel,
                'payment_ref': ref,
                'partner_name': xazina.reciever_name or False,
                'narration': xazina.payment_foundation or False,
            }
            line = self.env['account.bank.statement.line'].create(line_vals)

            # For 'შემოსავლები', we automatically set the transit account (1243) and post.
            # For 'გადარიცხვები', we leave it in suspense/draft as per "standard program" behavior for reconciliation.
            if self.xazina_type == 'შემოსავლები':
                move = line.move_id
                bank_account_id = journal.default_account_id.id
                counterpart_lines = move.line_ids.filtered(
                    lambda l: l.account_id.id != bank_account_id
                )
                if counterpart_lines:
                    move.button_draft()
                    counterpart_lines.with_context(check_move_validity=False).write(
                        {'account_id': transit_account.id}
                    )
                    move.action_post()

            created_lines |= line

        if not created_lines:
            raise UserError(_('გატარებები ვერ შეიქმნა. შეამოწმეთ თანხები.'))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('გატარებები შეიქმნა'),
                'message': _('%d საბანკო ჩანაწერი წარმატებით შეიქმნა.') % len(created_lines),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }
