from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CreateGatarebаWizard(models.TransientModel):
    _name = 'create.gatareba.wizard'
    _description = 'გატარებების შექმნის ვიზარდი'

    xazina_type = fields.Selection([
        ('შემოსავლები', 'შემოსავლები'),
        ('გადარიცხვები', 'გადარიცხვები'),
    ], string='ხაზინის ტიპი', required=True)

    journal_id = fields.Many2one(
        'account.journal',
        string='ჟურნალი',
        required=True,
    )
    debit_account_id = fields.Many2one(
        'account.account',
        string='დებეტის ანგარიში',
        required=True,
    )
    credit_account_id = fields.Many2one(
        'account.account',
        string='კრედიტის ანგარიში',
        required=True,
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

    def action_create_gatarebebi(self):
        self.ensure_one()

        records = self.xazina_ids
        if not records:
            raise UserError(_('გასაგზავნი ჩანაწერები არ მოიძებნა.'))

        created_moves = self.env['account.move']

        for xazina in records:
            if not xazina.date:
                raise UserError(
                    _('ჩანაწერს "%s" არ აქვს თარიღი მითითებული.')
                    % (xazina.request_number or xazina.id)
                )
            if not xazina.amount_in_gel:
                continue

            ref_parts = [
                xazina.request_number,
                xazina.commintment_number,
                xazina.payment_purpose,
            ]
            ref = ' | '.join(p for p in ref_parts if p)

            move_vals = {
                'move_type': 'entry',
                'date': xazina.date,
                'journal_id': self.journal_id.id,
                'ref': ref or False,
                'narration': xazina.payment_foundation or False,
                'line_ids': [
                    (0, 0, {
                        'account_id': self.debit_account_id.id,
                        'debit': xazina.amount_in_gel,
                        'credit': 0.0,
                        'name': xazina.payment_purpose or xazina.reciever_name or '/',
                        'analytic_distribution': (
                            {str(xazina.analytic_account_id.id): 100}
                            if xazina.analytic_account_id else False
                        ),
                    }),
                    (0, 0, {
                        'account_id': self.credit_account_id.id,
                        'debit': 0.0,
                        'credit': xazina.amount_in_gel,
                        'name': xazina.payment_purpose or xazina.reciever_name or '/',
                        'analytic_distribution': (
                            {str(xazina.analytic_account_id.id): 100}
                            if xazina.analytic_account_id else False
                        ),
                    }),
                ],
            }
            move = self.env['account.move'].create(move_vals)
            created_moves |= move

        if not created_moves:
            raise UserError(_('გატარებები ვერ შეიქმნა. შეამოწმეთ თანხები (ნული ან ცარიელი).'))

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('გატარებები შეიქმნა'),
                'message': _('%d გატარება წარმატებით შეიქმნა.') % len(created_moves),
                'type': 'success',
                'next': {
                    'type': 'ir.actions.act_window',
                    'name': _('გატარებები'),
                    'res_model': 'account.move',
                    'view_mode': 'list,form',
                    'domain': [('id', 'in', created_moves.ids)],
                    'target': 'current',
                },
            },
        }
