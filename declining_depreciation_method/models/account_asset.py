# -*- coding: utf-8 -*-
import calendar
from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountAsset(models.Model):
    _inherit = 'account.asset'

    method = fields.Selection(
        selection_add=[('declining_nbv', 'ნაშთის შემცირებით')],
        ondelete={'declining_nbv': 'set default'},
    )

    # -------------------------------------------------------------------------
    # Board generation
    # -------------------------------------------------------------------------

    def compute_depreciation_board(self, date=False):
        """Odoo Enterprise: regenerate depreciation schedule (name may vary by version)."""
        ours = self.filtered(lambda a: a.method == 'declining_nbv')
        rest = self - ours
        res = True
        if rest:
            res = super(AccountAsset, rest).compute_depreciation_board(date)
        ours._declining_nbv_compute_board(date)
        return res

    def _compute_board_amount(self, *args, **kwargs):
        """Make enterprise internals compatible with custom method key.

        Odoo EE internals (dispose/sell/re-evaluate/pause) call this method and
        branch by `self.method`. For custom key `declining_nbv` upstream code
        may not initialize local variables and crashes. We delegate to super()
        while temporarily using a native declining method key.
        """
        self.ensure_one()
        if self.method != 'declining_nbv':
            return super()._compute_board_amount(*args, **kwargs)

        fallback_method = self._declining_nbv_standard_method_key() or 'degressive'
        original_method = self.method
        try:
            self.with_context(check_move_validity=False).write({'method': fallback_method})
            return super(AccountAsset, self)._compute_board_amount(*args, **kwargs)
        finally:
            self.with_context(check_move_validity=False).write({'method': original_method})

    def _declining_nbv_compute_board(self, restart_date=False):
        """Pure declining on net book value; last line clears remaining depreciable amount."""
        Line, _lines_field = self.env['account.asset']._declining_nbv_board_spec()
        if Line._name == 'account.move':
            self._declining_nbv_compute_board_account_move(restart_date)
            return
        for asset in self:
            asset.ensure_one()
            if asset.state not in ('draft', 'open'):
                continue
            amount_fname = asset._asset_line_amount_field(Line)
            date_fname = asset._asset_line_date_field(Line)
            rel_lines = asset._asset_depreciation_lines_rel()

            rate = asset._declining_nbv_rate()
            if rate <= 0.0:
                raise UserError(_('Set a positive Declining Factor for this depreciation method.'))

            n_total = int(asset.method_number or 0)
            period_months = int(asset.method_period or 0) or 12
            if n_total <= 0:
                raise UserError(_('Duration (number of depreciations) must be positive.'))

            currency = asset.company_id.currency_id
            original = asset._asset_original_value()
            salvage = asset._asset_salvage_value()

            lines = rel_lines.filtered(lambda l: asset._declining_nbv_line_is_posted(l))
            posted = lines.sorted(key=lambda l: getattr(l, date_fname) or date.min)
            n_posted = len(posted)
            if n_posted >= n_total:
                continue

            accum_posted = sum(
                currency.round(float(getattr(l, amount_fname, 0.0) or 0.0)) for l in posted
            )
            opening_nbv = currency.round(original - accum_posted)
            min_book = currency.round(salvage)
            remaining_depreciable = currency.round(opening_nbv - min_book)
            if currency.is_zero(remaining_depreciable) or remaining_depreciable < 0:
                continue

            to_generate = n_total - n_posted
            asset._unlink_unposted_depreciation_lines()

            schedule_start = asset._declining_nbv_schedule_start()
            seq_base = n_posted

            book = opening_nbv
            for k in range(to_generate):
                seq = seq_base + k + 1
                is_last = k == to_generate - 1
                global_idx = n_posted + k
                p_start, p_end = asset._declining_nbv_period_bounds(
                    schedule_start, period_months, global_idx
                )
                if is_last:
                    amount = currency.round(book - min_book)
                    if amount < 0.0:
                        amount = 0.0
                else:
                    fraction = asset._declining_nbv_year_fraction(p_start, p_end)
                    raw = book * rate * fraction
                    amount = currency.round(raw)
                    max_amt = currency.round(book - min_book)
                    if amount > max_amt:
                        amount = max_amt
                book = currency.round(book - amount)

                vals = asset._declining_nbv_prepare_line_vals(
                    Line,
                    amount_fname,
                    date_fname,
                    p_end,
                    amount,
                    seq,
                )
                Line.create(vals)

    def _declining_nbv_compute_board_account_move(self, restart_date=False):
        """Odoo 18 EE: reuse standard draft moves, then overwrite dates/amounts."""
        for asset in self:
            asset.ensure_one()
            if asset.state not in ('draft', 'open'):
                continue

            asset._declining_nbv_prepare_standard_account_move_board(restart_date)

            rate = asset._declining_nbv_rate()
            if rate <= 0.0:
                raise UserError(_('Set a positive Declining Factor for this depreciation method.'))

            n_total = int(asset.method_number or 0)
            period_months = int(asset.method_period or 0) or 12
            if n_total <= 0:
                raise UserError(_('Duration (number of depreciations) must be positive.'))

            currency = asset.company_id.currency_id
            original = asset._asset_original_value()
            salvage = asset._asset_salvage_value()
            rel_lines = asset._asset_depreciation_lines_rel()

            posted = rel_lines.filtered(lambda m: m.state == 'posted').sorted(key=lambda m: m.date or date.min)
            drafts = (rel_lines - posted).sorted(key=lambda m: (m.date or date.min, m.id))
            n_posted = len(posted)
            if n_posted >= n_total:
                continue

            accum_posted = sum(
                currency.round(asset._declining_nbv_depreciation_amount_from_move(m)) for m in posted
            )
            opening_nbv = currency.round(original - accum_posted)
            min_book = currency.round(salvage)
            if currency.is_zero(opening_nbv - min_book) or opening_nbv < min_book:
                continue

            to_generate = n_total - n_posted
            if len(drafts) < to_generate:
                raise UserError(
                    _(
                        'Standard Odoo generated %(got)s draft depreciation entries, but %(need)s are needed.'
                    )
                    % {'got': len(drafts), 'need': to_generate}
                )
            if len(drafts) > to_generate:
                drafts[to_generate:].unlink()
                drafts = drafts[:to_generate]

            schedule_start = asset._declining_nbv_schedule_start()
            book = opening_nbv

            for k in range(to_generate):
                is_last = k == to_generate - 1
                global_idx = n_posted + k
                p_start, p_end = asset._declining_nbv_period_bounds(
                    schedule_start, period_months, global_idx
                )
                if is_last:
                    amount = currency.round(book - min_book)
                    if amount < 0.0:
                        amount = 0.0
                else:
                    fraction = asset._declining_nbv_year_fraction(p_start, p_end)
                    raw = book * rate * fraction
                    amount = currency.round(raw)
                    max_amt = currency.round(book - min_book)
                    if amount > max_amt:
                        amount = max_amt
                book = currency.round(book - amount)
                move = drafts[k]
                asset._declining_nbv_apply_amount_to_move(move, amount, p_start, p_end)

    def _declining_nbv_prepare_standard_account_move_board(self, restart_date=False):
        """Generate draft depreciation moves via native Odoo flow, not custom move creation."""
        self.ensure_one()
        fallback_method = self._declining_nbv_standard_method_key()
        if not fallback_method:
            raise UserError(_('Could not find a native depreciation method to bootstrap draft moves.'))

        original_method = self.method
        if original_method == fallback_method:
            super(AccountAsset, self).compute_depreciation_board(restart_date)
            return
        try:
            self.write({'method': fallback_method})
            super(AccountAsset, self).compute_depreciation_board(restart_date)
        finally:
            self.write({'method': original_method})

    def _declining_nbv_standard_method_key(self):
        """Pick a native method key that enterprise supports in this DB."""
        self.ensure_one()
        method_info = self.fields_get(['method']).get('method', {})
        selections = [key for key, _label in method_info.get('selection', [])]
        for key in (
            'degressive_then_linear',
            'declining_then_linear',
            'degressive',
            'declining',
            'linear',
        ):
            if key in selections:
                return key
        return False

    def _declining_nbv_apply_amount_to_move(self, move, amount, period_start, period_end):
        """Adjust existing draft depreciation move to match declining_nbv amount/dates."""
        self.ensure_one()
        amount = float(amount or 0.0)
        expense_acc = self._declining_nbv_expense_account()

        move_vals = {}
        if 'date' in move._fields:
            move_vals['date'] = period_end
        if 'asset_depreciation_beginning_date' in move._fields:
            move_vals['asset_depreciation_beginning_date'] = period_start
        if 'asset_depreciation_end_date' in move._fields:
            move_vals['asset_depreciation_end_date'] = period_end
        if 'asset_depreciation_ending_date' in move._fields:
            move_vals['asset_depreciation_ending_date'] = period_end
        if move_vals:
            move.write(move_vals)

        expense_line = move.line_ids.filtered(lambda l: l.account_id == expense_acc)[:1]
        counterpart_line = (move.line_ids - expense_line)[:1]
        if not expense_line:
            expense_line = move.line_ids.filtered(lambda l: (l.debit or 0.0) >= (l.credit or 0.0))[:1]
            counterpart_line = (move.line_ids - expense_line)[:1]
        if not expense_line or not counterpart_line:
            raise UserError(_('Could not identify debit/credit lines on depreciation move %s.') % move.display_name)

        expense_line.with_context(check_move_validity=False).write({'debit': amount, 'credit': 0.0})
        counterpart_line.with_context(check_move_validity=False).write({'debit': 0.0, 'credit': amount})

    def _declining_nbv_depreciation_amount_from_move(self, move):
        """Depreciation expense for one posted entry (Dr expense, Cr accum.)."""
        self.ensure_one()
        expense_acc = self._declining_nbv_expense_account()
        lines = move.line_ids.filtered(lambda l: l.account_id == expense_acc)
        return float(sum(lines.mapped('debit')) - sum(lines.mapped('credit')))

    def _declining_nbv_expense_account(self):
        self.ensure_one()
        for fn in (
            'account_depreciation_expense_id',
            'expense_account_id',
            'depreciation_expense_account_id',
        ):
            if fn in self._fields and getattr(self, fn, False):
                return getattr(self, fn)
        raise UserError(
            _('No depreciation expense account on the asset (configure the P&L depreciation account on the asset).')
        )

    def _declining_nbv_accumulated_account(self):
        self.ensure_one()
        for fn in (
            'account_depreciation_id',
            'account_accumulated_depreciation_id',
            'accumulated_depreciation_account_id',
        ):
            if fn in self._fields and getattr(self, fn, False):
                return getattr(self, fn)
        raise UserError(
            _("No accumulated depreciation account on the asset (configure depreciation / balance sheet account).")
        )

    def _declining_nbv_create_depreciation_move(self, amount, move_date):
        self.ensure_one()
        Move = self.env['account.move']
        Line = self.env['account.move.line']
        if not self.journal_id:
            raise UserError(_('Set a journal on the asset.'))
        expense = self._declining_nbv_expense_account()
        accum = self._declining_nbv_accumulated_account()
        label = _('Depreciation: %(name)s') % {'name': self.name or ''}

        line_cmd_e = {'account_id': expense.id, 'name': label, 'debit': amount, 'credit': 0.0}
        line_cmd_a = {'account_id': accum.id, 'name': label, 'debit': 0.0, 'credit': amount}

        if 'analytic_distribution' in Line._fields and getattr(self, 'analytic_distribution', None):
            ad = self.analytic_distribution
            line_cmd_e['analytic_distribution'] = ad
            line_cmd_a['analytic_distribution'] = ad
        elif 'analytic_account_id' in Line._fields and getattr(self, 'analytic_account_id', None):
            aa = self.analytic_account_id
            line_cmd_e['analytic_account_id'] = aa.id
            line_cmd_a['analytic_account_id'] = aa.id

        aml_allowed = set(Line._fields)
        line_cmd_e = {k: v for k, v in line_cmd_e.items() if k in aml_allowed}
        line_cmd_a = {k: v for k, v in line_cmd_a.items() if k in aml_allowed}

        move_vals = {
            'move_type': 'entry',
            'journal_id': self.journal_id.id,
            'date': move_date,
            'ref': label,
            'company_id': self.company_id.id,
            'line_ids': [(0, 0, line_cmd_e), (0, 0, line_cmd_a)],
        }
        link = self._declining_nbv_move_asset_link_field()
        if not link and 'asset_id' in Move._fields:
            if Move._fields['asset_id'].comodel_name == 'account.asset':
                link = 'asset_id'
        if not link:
            raise UserError(
                _('Could not find a Many2one from account.move to account.asset to link depreciation moves.')
            )
        move_vals[link] = self.id

        if 'currency_id' in Move._fields:
            move_vals['currency_id'] = self.company_id.currency_id.id

        allowed = set(Move._fields)
        move_vals = {k: v for k, v in move_vals.items() if k in allowed}
        return Move.create(move_vals)

    @api.model
    def _declining_nbv_move_asset_link_field(self):
        Move = self.env['account.move']
        prefer = []
        other = []
        for fname, field in Move._fields.items():
            if field.type != 'many2one' or field.comodel_name != 'account.asset':
                continue
            if 'deprec' in fname.lower() or fname == 'asset_id':
                prefer.append(fname)
            else:
                other.append(fname)
        names = prefer + other
        return names[0] if names else None

    def _unlink_unposted_depreciation_lines(self):
        rel = self._asset_depreciation_lines_rel()
        unposted = rel.filtered(lambda l: not self._declining_nbv_line_is_posted(l))
        if unposted:
            unposted.unlink()

    def _declining_nbv_prepare_line_vals(self, Line, amount_fname, date_fname, line_date, amount, seq):
        self.ensure_one()
        vals = {
            'asset_id': self.id,
            amount_fname: amount,
            date_fname: line_date,
        }
        if 'name' in Line._fields:
            vals['name'] = _('Depreciation: %(name)s #%(seq)s') % {'name': self.name or '', 'seq': seq}
        if 'sequence' in Line._fields:
            vals['sequence'] = seq
        return vals

    def _declining_nbv_schedule_start(self):
        """Day one of period 0 (same anchor Odoo uses for the whole depreciation table)."""
        self.ensure_one()
        start = getattr(self, 'prorata_date', False) or getattr(self, 'acquisition_date', False)
        if not start:
            start = getattr(self, 'date', False) or fields.Date.today()
        return start

    def _declining_nbv_last_day_of_month(self, d):
        """Last calendar day of month containing d."""
        _, last = calendar.monthrange(d.year, d.month)
        return date(d.year, d.month, last)

    def _declining_nbv_period_bounds(self, schedule_start, period_months, global_index):
        """Inclusive [start, end] per period; posting date uses end (p_end).

        - Annual board (method_period == 12): each period ends on 31 Dec; period 0 starts on
          activation / prorata so the first charge is prorated by days to year-end.
        - Monthly board (method_period == 1): each period ends on the last day of that month;
          period 0 starts on activation through month-end (partial month by days).
        - Other periods (e.g. quarterly): unchanged (fixed length from acquisition anchor).
        """
        self.ensure_one()
        if period_months == 12:
            return self._declining_nbv_period_bounds_years(schedule_start, global_index)
        if period_months == 1:
            return self._declining_nbv_period_bounds_months(schedule_start, global_index)
        period_start = schedule_start + relativedelta(months=global_index * period_months)
        period_end = schedule_start + relativedelta(months=(global_index + 1) * period_months) - timedelta(
            days=1
        )
        return period_start, period_end

    def _declining_nbv_period_bounds_years(self, schedule_start, global_index):
        """Calendar-year periods; first period partial from schedule_start through 31 Dec that year."""
        y0 = schedule_start.year
        if global_index == 0:
            return schedule_start, date(y0, 12, 31)
        yi = y0 + global_index
        return date(yi, 1, 1), date(yi, 12, 31)

    def _declining_nbv_period_bounds_months(self, schedule_start, global_index):
        """Month-boundary periods; first month partial from schedule_start through month-end."""
        first_month_end = self._declining_nbv_last_day_of_month(schedule_start)
        if global_index == 0:
            return schedule_start, first_month_end
        month_after_partial = first_month_end + timedelta(days=1)
        cursor = month_after_partial + relativedelta(months=global_index - 1)
        p_start = date(cursor.year, cursor.month, 1)
        p_end = self._declining_nbv_last_day_of_month(p_start)
        return p_start, p_end

    def _declining_nbv_year_fraction(self, period_start, period_end):
        """Fraction of a 1-year declining charge (rate is annual), by calendar days."""
        self.ensure_one()
        if period_end < period_start:
            return 0.0
        total = 0.0
        cur = period_start
        while cur <= period_end:
            diy = 366 if calendar.isleap(cur.year) else 365
            total += 1.0 / float(diy)
            cur += timedelta(days=1)
        return total

    def _declining_nbv_rate(self):
        self.ensure_one()
        f = float(self.method_progress_factor or 0.0)
        if f > 1.0:
            f = f / 100.0
        return f

    def _asset_original_value(self):
        self.ensure_one()
        for fname in ('original_value', 'value', 'purchase_value'):
            if fname in self._fields:
                return float(getattr(self, fname) or 0.0)
        return 0.0

    def _asset_salvage_value(self):
        self.ensure_one()
        if 'salvage_value' in self._fields:
            return float(self.salvage_value or 0.0)
        return 0.0

    def _asset_depreciation_lines_rel(self):
        self.ensure_one()
        _Model, fname = self._declining_nbv_board_spec()
        if fname not in self._fields:
            raise UserError(_('Depreciation lines field %s not found on this asset.') % fname)
        return getattr(self, fname)

    @api.model
    def _declining_nbv_board_spec(self):
        """Resolve board line model: Odoo 18e often uses account.asset.depreciation.line, not account.asset.line."""
        icp = self.env['ir.config_parameter'].sudo()
        forced_model = icp.get_param('declining_depreciation_method.board_line_model')
        forced_field = icp.get_param('declining_depreciation_method.board_lines_field')
        if forced_model and forced_field:
            if forced_model not in self.env.registry:
                raise UserError(_('System parameter board_line_model=%r is not a valid model.') % forced_model)
            if forced_field not in self.env['account.asset']._fields:
                raise UserError(_('System parameter board_lines_field=%r is not on account.asset.') % forced_field)
            f = self.env['account.asset']._fields[forced_field]
            if f.type != 'one2many' or f.comodel_name != forced_model:
                raise UserError(_('Field %r must be One2many(%r).') % (forced_field, forced_model))
            return self.env[forced_model], forced_field

        Asset = self.env['account.asset']
        pair = self._declining_nbv_board_spec_known_pairs(Asset)
        if pair:
            return pair

        candidates = []
        for fname, field in Asset._fields.items():
            if field.type != 'one2many':
                continue
            comodel = field.comodel_name
            if not comodel or comodel not in self.env.registry:
                continue
            if comodel in (
                'account.move',
                'account.bank.statement.line',
                'mail.message',
                'account.asset',
            ):
                continue
            Line = self.env[comodel]
            if not self._declining_nbv_line_model_links_asset(Line):
                continue
            if not self._declining_nbv_line_model_has_date(Line):
                continue
            if not self._declining_nbv_line_model_has_amount(Line):
                continue
            score = 0
            low = fname.lower()
            if 'deprec' in low:
                score += 20
            if 'board' in low:
                score += 15
            if 'line' in low:
                score += 5
            if 'value' in low:
                score += 3
            candidates.append((score, fname, comodel))

        if not candidates:
            o2m = []
            for fn, fld in sorted(Asset._fields.items()):
                if fld.type == 'one2many' and fld.comodel_name:
                    o2m.append('%s → %s' % (fn, fld.comodel_name))
            hint = _('One2many fields on account.asset: %s') % ('; '.join(o2m) if o2m else _('(none)'))
            raise UserError(
                _(
                    'Could not auto-detect depreciation board lines.\n\n'
                    'Set Technical → Parameters → System Parameters:\n'
                    '• declining_depreciation_method.board_line_model = technical model name\n'
                    '• declining_depreciation_method.board_lines_field = account.asset field name\n\n'
                    '%s'
                )
                % hint
            )

        candidates.sort(key=lambda x: (-x[0], x[1]))
        _score, lines_fname, comodel = candidates[0]
        return self.env[comodel], lines_fname

    @api.model
    def _declining_nbv_board_spec_known_pairs(self, Asset):
        pairs = [
            ('depreciation_move_ids', 'account.move'),
            ('depreciation_line_ids', 'account.asset.depreciation.line'),
            ('depreciation_line_ids', 'account.asset.line'),
            ('asset_depreciation_line_ids', 'account.asset.depreciation.line'),
            ('depreciation_ids', 'account.asset.depreciation.line'),
            ('depreciation_line_ids', 'account.asset.value.line'),
        ]
        for fname, comodel in pairs:
            if comodel not in self.env.registry or fname not in Asset._fields:
                continue
            f = Asset._fields[fname]
            if f.type == 'one2many' and f.comodel_name == comodel:
                return self.env[comodel], fname
        return None

    @api.model
    def _declining_nbv_line_model_links_asset(self, Line):
        skip_m2o = {'parent_id', 'root_asset_id', 'asset_parent_id', 'parent_asset_id'}
        for lfname, lfield in Line._fields.items():
            if lfield.type == 'many2one' and lfield.comodel_name == 'account.asset':
                if lfname in skip_m2o or 'parent' in lfname.lower():
                    continue
                return True
            if lfield.type == 'many2many' and lfield.comodel_name == 'account.asset':
                return True
        return False

    @api.model
    def _declining_nbv_line_model_has_date(self, Line):
        for n in (
            'depreciation_date',
            'date',
            'line_date',
            'accounting_date',
            'invoice_date',
        ):
            if n in Line._fields and Line._fields[n].type in ('date', 'datetime'):
                return True
        return False

    @api.model
    def _declining_nbv_line_model_has_amount(self, Line):
        for n in (
            'depreciation_amount',
            'amount',
            'depreciation_value',
            'accumulated_value',
            'depreciation',
            'value',
        ):
            if n not in Line._fields:
                continue
            if Line._fields[n].type in ('monetary', 'float', 'integer'):
                return True
        for lfname, lfield in Line._fields.items():
            if lfield.type not in ('monetary', 'float', 'integer'):
                continue
            low = lfname.lower()
            if any(k in low for k in ('deprec', 'amount', 'expense', 'value', 'credit', 'debit')):
                return True
        return False

    def _declining_nbv_line_is_posted(self, line):
        self.ensure_one()
        if getattr(line, 'move_id', False) or getattr(line, 'parent_move_id', False):
            return True
        state = getattr(line, 'state', None)
        if state == 'posted':
            return True
        if getattr(line, 'posted', False):
            return True
        return False

    @api.model
    def _asset_line_amount_field(self, Line):
        for fname in (
            'depreciation_amount',
            'amount',
            'depreciation_value',
            'accumulated_value',
            'depreciation',
        ):
            if fname in Line._fields:
                return fname
        raise UserError(_('Could not find amount field on board line model %s.') % Line._name)

    @api.model
    def _asset_line_date_field(self, Line):
        for fname in ('depreciation_date', 'date', 'line_date', 'accounting_date', 'invoice_date'):
            if fname in Line._fields:
                return fname
        raise UserError(_('Could not find date field on board line model %s.') % Line._name)
