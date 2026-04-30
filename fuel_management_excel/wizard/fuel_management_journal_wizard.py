# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class FuelManagementJournalWizard(models.TransientModel):
    _name = 'fuel.management.journal.wizard'
    _description = 'Fuel Management Journal Entry Wizard'

    date = fields.Date(
        string='Journal Entry Date',
        required=True,
        default=fields.Date.context_today,
        help='This date will be used as the account.move date for the created journal entries.',
    )

    def action_confirm(self):
        self.ensure_one()
        active_ids = self.env.context.get('active_ids', [])
        if not active_ids:
            return
        fuel_records = self.env['fuel.management'].browse(active_ids)
        return fuel_records.with_context(journal_entry_date=self.date).action_generate_journal_entry()
