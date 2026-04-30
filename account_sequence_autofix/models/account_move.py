from odoo import api, models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _must_check_constrains_date_sequence(self):
        return False

    def _dv_has_date_sequence_mismatch(self):
        self.ensure_one()
        return bool(
            self.name
            and self.name != "/"
            and hasattr(self, "_sequence_matches_date")
            and not self._sequence_matches_date()
        )

    def _dv_get_sequence_reset_vals(self):
        self.ensure_one()
        vals = {"name": "/"}
        for field_name in (
            "sequence_prefix",
            "sequence_number",
            "sequence_override_regex",
        ):
            if field_name in self._fields:
                vals[field_name] = False
        if "made_sequence_gap" in self._fields:
            vals["made_sequence_gap"] = False
        return vals

    def _dv_assign_sequence_from_date(self):
        for move in self:
            if not move.date or not hasattr(move, "_set_next_sequence"):
                continue
            move.with_context(
                sequence_date=move.date,
                ir_sequence_date=move.date,
                dv_skip_date_sequence_constraint=True,
                check_move_validity=False,
                skip_account_move_synchronization=True,
                skip_readonly_check=True,
            )._set_next_sequence()
        return True

    def _dv_autofix_date_sequence(self):
        for move in self:
            if not move._dv_has_date_sequence_mismatch():
                continue
            if not hasattr(move, "_set_next_sequence"):
                continue
            move.with_context(
                dv_skip_sequence_autofix=True,
                dv_skip_sequence_autofix_constraint=True,
                dv_skip_date_sequence_constraint=True,
                check_move_validity=False,
                skip_account_move_synchronization=True,
                skip_readonly_check=True,
            ).write(move._dv_get_sequence_reset_vals())
            move.with_context(
                dv_skip_sequence_autofix=True,
                dv_skip_sequence_autofix_constraint=True,
            )._dv_assign_sequence_from_date()
        return True

    @api.constrains("name", "date")
    def _constrains_date_sequence(self):
        if not self.env.context.get("dv_skip_sequence_autofix_constraint"):
            self.filtered(lambda move: move.name and move.name != "/")._dv_autofix_date_sequence()
        return super()._constrains_date_sequence()

    def write(self, vals):
        if self.env.context.get("dv_skip_sequence_autofix"):
            return super().write(vals)

        if "date" not in vals or "name" in vals:
            return super().write(vals)

        result = True
        for move in self:
            move_vals = dict(vals)
            if (
                move.state == "posted"
                and move.name
                and move.name != "/"
                and move_vals.get("date")
                and move_vals["date"] != move.date
            ):
                move_vals.update(move._dv_get_sequence_reset_vals())
                result = (
                    super(
                        AccountMove,
                        move.with_context(
                            dv_skip_sequence_autofix=True,
                            dv_skip_date_sequence_constraint=True,
                            check_move_validity=False,
                            skip_account_move_synchronization=True,
                            skip_readonly_check=True,
                        ),
                    ).write(move_vals)
                    and result
                )
                move.with_context(
                    dv_skip_sequence_autofix=True,
                    dv_skip_date_sequence_constraint=True,
                    check_move_validity=False,
                    skip_account_move_synchronization=True,
                    skip_readonly_check=True,
                )._dv_assign_sequence_from_date()
            else:
                result = super(AccountMove, move).write(move_vals) and result
        return result

    def _post(self, soft=True):
        for move in self.filtered(lambda m: m.state == "draft" and m._dv_has_date_sequence_mismatch()):
            move.with_context(
                dv_skip_sequence_autofix=True,
                dv_skip_date_sequence_constraint=True,
                check_move_validity=False,
                skip_account_move_synchronization=True,
                skip_readonly_check=True,
            ).write(move._dv_get_sequence_reset_vals())
        return super()._post(soft=soft)
