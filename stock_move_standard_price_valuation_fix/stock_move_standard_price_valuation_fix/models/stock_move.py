from odoo import _, fields, models
from odoo.exceptions import ValidationError


class StockMove(models.Model):
    _inherit = "stock.move"

    def _dv_clear_move_sequence_if_date_mismatch(self, account_move):
        if not account_move or not account_move.name or account_move.name == "/":
            return
        if hasattr(account_move, "_sequence_matches_date") and not account_move._sequence_matches_date():
            clear_vals = {"name": "/"}
            if "sequence_prefix" in account_move._fields:
                clear_vals["sequence_prefix"] = False
            if "sequence_number" in account_move._fields:
                clear_vals["sequence_number"] = False
            if "sequence_override_regex" in account_move._fields:
                clear_vals["sequence_override_regex"] = False
            account_move.with_context(
                check_move_validity=False,
                skip_account_move_synchronization=True,
                skip_readonly_check=True,
                dv_skip_date_sequence_constraint=True,
            ).write(clear_vals)

    dv_fix_valuation_to_standard_price = fields.Boolean(
        string="Fix valuation to Standard Price",
        help="When enabled on this move, its stock valuation and accounting entries can be "
        "re-aligned so that valuation equals product Standard Price × quantity.",
        copy=False,
    )

    def _dv_fix_writeoff_valuation_to_standard_price(self):
        """
        Adjust (in-place) stock valuation and related accounting entries so that valuation equals
        product Standard Price × quantity for selected moves.

        This helper is private to this module to avoid conflicts with other dv_* valuation fixes.

        Notes:
        - Only applies to real-time valuation products.
        - Requires that related journal entries can be reset to draft (no lock dates / restrictions).
        """
        AccountMove = self.env["account.move"].sudo()
        AccountMoveLine = self.env["account.move.line"].sudo()

        for move in self:
            move = move.with_company(move.company_id)
            product = move.product_id
            if not product or not product.is_storable:
                continue
            if product.valuation != "real_time":
                continue

            # Ensure at least one SVL exists; for outgoing / write-off moves this may be missing.
            if not move.stock_valuation_layer_ids and (move._is_out() or move.scrapped):
                move._create_out_svl()

            svls_all = move.stock_valuation_layer_ids.sudo()
            for svl in svls_all:
                desired_value = product.standard_price * svl.quantity
                if not svl.currency_id.is_zero(desired_value - svl.value):
                    svl.write({"value": desired_value})

            # If there was no JE because valuation was 0 at the time, generate it now.
            svls_missing_je = svls_all.filtered(
                lambda l: not l.account_move_id and not l.currency_id.is_zero(l.value)
            )
            if svls_missing_je:
                # Create the JE with the correct period/sequence context.
                for date, svls_group in svls_missing_je.grouped(
                    lambda l: (
                        fields.Datetime.context_timestamp(l, l.create_date).date()
                        if l.create_date
                        else fields.Date.context_today(l)
                    )
                ).items():
                    svls_group.with_context(
                        force_period_date=date,
                        sequence_date=date,
                        dv_skip_date_sequence_constraint=True,
                    )._validate_accounting_entries()
                svls_missing_je._validate_analytic_accounting_entries()

            # Stock valuation journal entries are linked to the move through account.move.stock_move_id.
            account_moves = (move.account_move_ids | svls_all.mapped("account_move_id")).sudo().exists()
            for account_move in account_moves:
                if not account_move:
                    continue

                company_currency = account_move.company_id.currency_id

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

                # Re-post.
                if account_move.state == "draft":
                    AccountMove.browse(account_move.id).with_context(
                        dv_skip_date_sequence_constraint=True,
                        skip_readonly_check=True,
                    )._post()

    def action_dv_apply_standard_price_valuation_fix(self):
        """Manual action from stock moves list/form to fix valuation on selected moves.

        Only moves where:
        - source location usage == 'internal' (real warehouse)
        - destination location usage in ('inventory', 'customer', 'production')
        will be adjusted.
        """
        moves = self.filtered(
            lambda m: m.state == "done"
            and m.location_id.usage == "internal"
            and m.location_dest_id.usage in ("inventory", "customer", "production")
        )
        if not moves:
            return True

        moves.write({"dv_fix_valuation_to_standard_price": True})
        moves._dv_fix_writeoff_valuation_to_standard_price()
        return True

