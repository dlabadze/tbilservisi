import logging

from odoo import SUPERUSER_ID, api, models


_logger = logging.getLogger(__name__)


class L10nKaBootstrap(models.AbstractModel):
    _name = "l10n.ka.bootstrap"
    _description = "Georgian UI bootstrap adjustments"

    def _register_hook(self):
        result = super()._register_hook()
        env = api.Environment(self._cr, SUPERUSER_ID, {})

        self._rename_server_actions(env)
        self._force_field_labels_and_selections(env)
        self._translate_existing_onboarding_messages(env)

        return result

    @staticmethod
    def _rename_server_actions(env):
        label_map = {
            "Delete": "წაშლა",
            "Sync Emp and Contact": "თანამშრომლისა და კონტაქტის სინქრონიზაცია",
            "Send HR Documents Access Link": "HR დოკუმენტებზე წვდომის ბმულის გაგზავნა",
        }

        actions = env["ir.actions.server"].sudo().search([
            ("name", "in", list(label_map.keys())),
        ])
        for action in actions:
            new_name = label_map.get(action.name)
            if new_name and action.name != new_name:
                action.name = new_name

    @staticmethod
    def _force_field_labels_and_selections(env):
        fields_model = env["ir.model.fields"].sudo()

        # Force wizard labels shown in "აქტივობის დაგეგმვა" popup.
        field_labels = {
            ("mail.activity.schedule", "plan_id"): "გეგმა",
            ("mail.activity.schedule", "date_deadline"): "ვადა",
        }
        for (model_name, field_name), label in field_labels.items():
            field_rec = fields_model.search([
                ("model", "=", model_name),
                ("name", "=", field_name),
            ], limit=1)
            if field_rec and field_rec.field_description != label:
                field_rec.field_description = label

        # Force hr.leave.allocation selection labels.
        selection_model = env["ir.model.fields.selection"].sudo()
        allocation_field = fields_model.search([
            ("model", "=", "hr.leave.allocation"),
            ("name", "=", "allocation_type"),
        ], limit=1)
        if allocation_field:
            selection_map = {
                "regular": "ჩვეულებრივი განაწილება",
                "accrual": "დაგროვებითი განაწილება",
            }
            selections = selection_model.search([("field_id", "=", allocation_field.id)])
            for selection in selections:
                new_label = selection_map.get(selection.value)
                if new_label and selection.name != new_label:
                    selection.name = new_label

    @staticmethod
    def _translate_existing_onboarding_messages(env):
        messages = env["mail.message"].sudo().search([
            ("body", "ilike", "May I recommend you to setup an"),
        ])
        if not messages:
            return

        old_prefix = '<b>Congratulations!</b> May I recommend you to setup an <a href="'
        old_prefix_plain = 'Congratulations! May I recommend you to setup an <a href="'
        new_prefix = '<b>გილოცავთ!</b> გირჩევთ, შექმნათ <a href="'
        old_suffix = '">onboarding plan?</a>'
        new_suffix = '">ადაპტაციის გეგმა</a>'

        updated = 0
        for message in messages:
            body = message.body or ""
            translated = (
                body
                .replace(old_prefix, new_prefix)
                .replace(old_prefix_plain, new_prefix)
                .replace(old_suffix, new_suffix)
            )
            if translated != body:
                message.body = translated
                updated += 1

        if updated:
            _logger.info("l10n_ka: translated %s onboarding chatter messages", updated)
