from odoo import _, fields, models
from odoo.exceptions import ValidationError


class StockMove(models.Model):
    _inherit = "stock.move"

    def _dv_clear_move_sequence_if_date_mismatch(self, account_move):
        """Clear sequence fields when move name doesn't match its date.

        In Odoo 18, date-based sequences are enforced. If an `account.move` already has an
        inconsistent (date, name/sequence) pair, *any* write on that move (or some related writes)
        can raise a ValidationError. Clearing the sequence first makes the move editable again.
        """
        if not account_move:
            return
        if not account_move.name or account_move.name == "/":
            return
        # If the sequence doesn't match the current date, clear it.
        if hasattr(account_move, "_sequence_matches_date") and not account_move._sequence_matches_date():
            clear_vals = {"name": "/"}
            # Odoo 18 stores the sequence in dedicated fields; clear them if present.
            if "sequence_prefix" in account_move._fields:
                clear_vals["sequence_prefix"] = False
            if "sequence_number" in account_move._fields:
                clear_vals["sequence_number"] = False
            if "sequence_override_regex" in account_move._fields:
                clear_vals["sequence_override_regex"] = False
            account_move.with_context(
                check_move_validity=False,
                skip_account_move_synchronization=True,
            ).write(clear_vals)

    def _dv_fix_valuation_to_standard_price(self):
        """
        Adjust (in-place) stock valuation and related accounting entries so that valuation equals
        product Standard Price × quantity.

        This method edits the existing valuation-linked journal entries by:
        - moving them to draft
        - updating the valuation-linked lines (debit/credit) while keeping balance = 0
        - re-posting the move

        Notes:
        - Only applies to real-time valuation products.
        - Requires that related journal entries can be reset to draft (no lock dates / restrictions).
        """
        AccountMove = self.env["account.move"].sudo()
        AccountMoveLine = self.env["account.move.line"].sudo()

        for move in self:
            move = move.with_company(move.company_id)
            if not move.product_id.is_storable:
                continue
            if move.product_id.valuation != "real_time":
                continue

            # -----------------------------------------------------------------
            # 1) Ensure SVL exists and fix SVL values first (even if no JE exists).
            # -----------------------------------------------------------------
            if not move.stock_valuation_layer_ids and (move._is_out() or move.scrapped):
                move._create_out_svl()

            svls_all = move.stock_valuation_layer_ids.sudo()
            for svl in svls_all:
                desired_value = move.product_id.standard_price * svl.quantity
                if not svl.currency_id.is_zero(desired_value - svl.value):
                    svl.write({"value": desired_value})

            # -----------------------------------------------------------------
            # 2) If there was no JE because valuation was 0 at the time, generate it now
            #    using the standard stock_account mechanism, while tracking created dates.
            # -----------------------------------------------------------------
            svls_missing_je = svls_all.filtered(
                lambda l: not l.account_move_id and not l.currency_id.is_zero(l.value)
            )
            svls_missing_je_ids = set(svls_missing_je.ids)
            created_account_move_dates = {}
            if svls_missing_je:
                for date, svls_group in svls_missing_je.grouped(
                    lambda l: (
                        fields.Datetime.context_timestamp(l, l.create_date).date()
                        if l.create_date
                        else fields.Date.context_today(l)
                    )
                ).items():
                    try:
                        # `sequence_date` is used by Odoo sequences; without it, a move can be
                        # created with a date different from the sequence it gets assigned.
                        svls_group.with_context(
                            force_period_date=date,
                            sequence_date=date,
                            dv_skip_date_sequence_constraint=True,
                        )._validate_accounting_entries()
                        svls_group._validate_analytic_accounting_entries()
                    except ValidationError as e:
                        raise
                    created_moves = svls_group.mapped("account_move_id").sudo().exists()
                    for am in created_moves:
                        created_account_move_dates[am.id] = date

            # Stock valuation journal entries are linked to the move through account.move.stock_move_id.
            account_moves = (move.account_move_ids | svls_all.mapped("account_move_id")).sudo().exists()
            for account_move in account_moves:
                if not account_move:
                    continue

                company_currency = account_move.company_id.currency_id

                # If the move is already inconsistent (date vs sequence), clear sequence *first*
                # so drafting / AML writes won't crash with the date-sequence constraint.
                account_move = account_move.with_context(dv_skip_date_sequence_constraint=True)
                self._dv_clear_move_sequence_if_date_mismatch(account_move)

                # Reset to draft to allow editing.
                if account_move.state == "posted":
                    (account_move.line_ids.filtered("reconciled")).remove_move_reconcile()
                    account_move.with_context(skip_readonly_check=True).button_draft()

                # Get SVLs linked to this journal entry (usually 1 per move, but keep it generic).
                svls = svls_all.filtered(lambda l: l.account_move_id.id == account_move.id)
                if not svls:
                    continue

                # Update AMLs (in-place) by account ids, like Odoo tests do.
                _journal_id, acc_src, acc_dest, acc_valuation = move._get_accounting_data_for_valuation()
                valuation_lines = account_move.line_ids.filtered(
                    lambda l: l.account_id.id == acc_valuation
                )
                counterpart_lines = account_move.line_ids.filtered(
                    lambda l: l.account_id.id in (acc_src, acc_dest)
                    and l.account_id.id != acc_valuation
                )

                valuation_line = valuation_lines[:1]
                counterpart_line = counterpart_lines[:1]
                if not valuation_line or not counterpart_line:
                    # Fallback: take one non-display line with nonzero balance besides valuation.
                    valuation_line = valuation_line or account_move.line_ids.filtered(
                        lambda l: l.account_id.id == acc_valuation
                    )[:1]
                    counterpart_line = counterpart_line or (
                        account_move.line_ids.filtered(
                            lambda l: not l.display_type
                            and l.account_id.id != acc_valuation
                            and not company_currency.is_zero(l.balance)
                        )[:1]
                    )
                if not valuation_line or not counterpart_line:
                    continue

                new_total = company_currency.round(sum(svls.mapped("value")))

                ctx = dict(
                    self.env.context,
                    check_move_validity=False,
                    skip_account_move_synchronization=True,
                )
                AccountMoveLine.with_context(ctx).browse(valuation_line.id).write(
                    {
                        "balance": new_total,
                        "amount_currency": new_total
                        if (
                            not valuation_line.currency_id
                            or valuation_line.currency_id == company_currency
                        )
                        else valuation_line.amount_currency,
                    }
                )
                AccountMoveLine.with_context(ctx).browse(counterpart_line.id).write(
                    {
                        "balance": -new_total,
                        "amount_currency": -new_total
                        if (
                            not counterpart_line.currency_id
                            or counterpart_line.currency_id == company_currency
                        )
                        else counterpart_line.amount_currency,
                    }
                )

                # Re-post, aligning date (and sequence when needed) to the valuation date.
                if account_move.state == "draft":
                    is_missing_je_move = (
                        svls_missing_je_ids
                        and any(
                            svl.id in svls_missing_je_ids
                            for svl in account_move.stock_valuation_layer_ids
                        )
                    )
                    target_date = False
                    if is_missing_je_move and created_account_move_dates.get(account_move.id):
                        target_date = created_account_move_dates[account_move.id]
                    elif svls:
                        svl_with_date = svls.filtered(lambda l: l.create_date)[:1]
                        if svl_with_date:
                            target_date = fields.Datetime.context_timestamp(
                                svl_with_date, svl_with_date.create_date
                            ).date()

                    if target_date:
                        # If we're changing the date of an already-numbered move, we MUST clear the
                        # name first, otherwise Odoo will raise:
                        # "Date (...) isn't aligned with the existing sequence number (...)".
                        if (
                            account_move.name
                            and account_move.name != "/"
                            and account_move.date
                            and account_move.date != target_date
                        ):
                            # Odoo 18 enforces date-based sequences. For already-numbered moves we
                            # avoid changing the date (and thus the sequence), otherwise we'd need
                            # a dedicated resequencing flow.
                            target_date = False

                        # Then update the date. If a ValidationError still occurs, clear the name
                        # and retry once (defensive).
                        if target_date and account_move.date != target_date:
                            try:
                                account_move.with_context(
                                    check_move_validity=False,
                                    skip_account_move_synchronization=True,
                                ).write({"date": target_date})
                            except ValidationError as e:
                                # If date change is blocked by sequence constraints, keep the original date.
                                pass

                    try:
                        AccountMove.browse(account_move.id).with_context(
                            dv_skip_date_sequence_constraint=True,
                            skip_readonly_check=True,
                        )._post()
                    except ValidationError:
                        if (
                            account_move.name
                            and account_move.name != "/"
                            and not account_move._sequence_matches_date()
                        ):
                            write_vals = {"name": "/"}
                            if target_date:
                                write_vals["date"] = target_date
                            account_move.with_context(
                                check_move_validity=False,
                                skip_account_move_synchronization=True,
                                skip_readonly_check=True,
                            ).write(write_vals)
                            AccountMove.browse(account_move.id).with_context(
                                dv_skip_date_sequence_constraint=True,
                                skip_readonly_check=True,
                            )._post()
                        else:
                            raise

    def _action_done(self, cancel_backorder=False):
        res = super()._action_done(cancel_backorder=cancel_backorder)
        moves = (self | res).exists()
        moves_to_fix = moves.filtered(
            lambda m: m.state == "done"
            and (
                (
                    m.scrapped
                    and m.scrap_id
                    and m.scrap_id.dv_fix_valuation_to_standard_price
                )
                or (
                    m.picking_id
                    and (
                        m.picking_id.picking_type_code == "outgoing"
                        or m.picking_id.location_dest_id.scrap_location
                    )
                    and m.picking_id.dv_fix_valuation_to_standard_price
                )
            )
        )
        if moves_to_fix:
            moves_to_fix._dv_fix_valuation_to_standard_price()
        return res

