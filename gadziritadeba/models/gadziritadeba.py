from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class AccountAsset(models.Model):
    _inherit = ['account.asset']  # ✅ combine inherits

    gadziritadeba_line_id = fields.Many2one(
        'gadziritadeba_det',
        string='Gadziritadeba Line',
        help='Link to the gadziritadeba detail line that created this asset'
    )

    gadziritadeba_id = fields.Many2one(
        'gadziritadeba',
        string='Gadziritadeba',
        related='gadziritadeba_line_id.gadziritadeba_id',
        store=True,
        help='Link to the main gadziritadeba record'
    )

    paspiri = fields.Many2one(
        'hr.employee',
        string='პასუხისმგებელი პირი'
    )

    mcirefasiani = fields.Boolean(string='მცირე ფასიანი', default=False)
    aqtnumbos = fields.Text(string="აქტის ნომერი")
    maragiskodi = fields.Text(string="მარაგის კოდი")


class Gadziritadeba(models.Model):
    _name = 'gadziritadeba'
    _description = 'საწყობის მოდულიდან ექსპლუატაცია'
    _order = 'date desc, id desc'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    state = fields.Selection([
        ('draft', 'Draft'),
        ('seen', 'Seen'),
        ('validated', 'Validated')
    ], default='draft', string='Status')

    picking_id = fields.Many2one(
        'stock.picking',
        string='აირჩიეთ ჩამოწერა',
        domain="[('picking_type_id.code', '=', 'internal'), ('state', '=', 'done')]",
        required=True
    )
    date = fields.Date(
        string="ექსპლუატაციაში გაშვების თარიღი",
        default=fields.Date.context_today,
        required=True
    )
    gamcsaw = fields.Text(string="გამცემი საწყობი")
    mimpiri = fields.Text(string="მიმღები პირი")
    aqtnumb = fields.Text(string="აქტის ნომერი")
    comment = fields.Text(string="საფუძველი")
    requestnum = fields.Text(string="მოთხოვნის ნომერი")
    dzkodandnam = fields.Text(string="ძირითადი საშუალება")
    gadziritadeba_line_ids = fields.One2many(
        'gadziritadeba_det', 'gadziritadeba_id', string='Transferred Products'
    )

    @api.constrains('gadziritadeba_line_ids')
    def _check_lines_exist(self):
        """Ensure at least one line exists before validation"""
        for record in self:
            if record.state == 'validated' and not record.gadziritadeba_line_ids:
                raise ValidationError("At least one product line is required for validation.")

    def assets(self):
        self.ensure_one()
        return {
            'name': 'Linked Assets',
            'type': 'ir.actions.act_window',
            'res_model': 'account.asset',
            'view_mode': 'list,form',
            'domain': [
                ('gadziritadeba_id', '=', self.id),
            ],
        }

    def action_validate(self):
        """Validate record and create assets with grouped dziritad logic and per-unit split"""
        self.ensure_one()

        if self.state != 'draft':
            raise UserError("Only draft records can be validated.")
        if not self.gadziritadeba_line_ids:
            raise UserError("Cannot validate without product lines.")

        Move = self.env['account.move']
        Asset = self.env['account.asset']
        Assetmovv = self.env['asset.movement']
        AssetMovLine = self.env['asset.movement.line']

        journal = self.env['account.journal'].search([('type', '=', 'general')], limit=1)
        if not journal:
            raise UserError("No general journal found. Please create a general journal first.")

        expense_account = self.env['account.account'].search([('code', '=', '7455')], limit=1)
        if not expense_account:
            raise UserError("Depreciation expense account (7455) not found.")

        partner_id = self.env.company.partner_id.id or False

        # --- GROUPING (dziritad + attached lines) ---
        grouped_lines = {}
        dziritad_lines = self.gadziritadeba_line_ids.filtered('dziritad')

        # Collect all dziritad groups first
        for dz_line in dziritad_lines:
            group_name = (dz_line.group_asset_name or dz_line.product_id.name or '').strip()
            refkodd = dz_line.product_id.default_code or ''
            grouped_lines[group_name] = {
                'dz_line': dz_line,
                'lines': [dz_line],
                'ref_code': refkodd,
            }

        # Add extra lines belonging to those groups
        extra_lines = self.gadziritadeba_line_ids.filtered(
            lambda l: not l.dziritad and l.group_asset_name
        )
        for line in extra_lines:
            group_name = line.group_asset_name.strip()
            if group_name in grouped_lines:
                grouped_lines[group_name]['lines'].append(line)

        # --- PROCESS GROUPED / DZIRITAD ASSETS ---
        for group_name, data in grouped_lines.items():
            dziritad_line = data['dz_line']
            lines = data['lines']
            refkodd = data['ref_code']

            dz_qty = dziritad_line.quantity or 1.0
            total_value = sum(l.sumofdzs for l in lines)
            per_unit = dziritad_line.per_unit

            asset_account = dziritad_line.account_id.id
            source_account = dziritad_line.product_id.categ_id.property_stock_account_output_categ_id.id
            if not asset_account or not source_account:
                raise UserError(f"Missing account configuration for asset group '{group_name}'.")

            # --- Increase existing asset if set ---
            if dziritad_line.asset_idd:
                modify_wizard = self.env['asset.modify'].create({
                    'asset_id': dziritad_line.asset_idd.id,
                    'modify_action': 'modify',
                    'date': self.date,
                    'value_residual': total_value,
                    'salvage_value': 0.0,
                    'account_asset_id': dziritad_line.asset_idd.account_asset_id.id,
                    'account_asset_counterpart_id': source_account,
                    'account_depreciation_id': dziritad_line.asset_idd.account_depreciation_id.id,
                    'account_depreciation_expense_id': expense_account.id,
                    'name': f'Asset increase from gadziritadeba: {self.comment or ""}',
                })
                modify_wizard.modify()
                dziritad_line.asset_idd.write({'gadziritadeba_line_id': dziritad_line.id})
                continue

            # --- Otherwise create new asset(s) ---
            # 1) PER UNIT
            if per_unit:
                unit_value = total_value / dz_qty if dz_qty else 0.0

                for i in range(int(dz_qty)):
                    # Create capitalization move
                    move = Move.create({
                        'date': self.date,
                        'journal_id': journal.id,
                        'ref': f'ექსპლუატაცია {group_name} #{i + 1}',
                        'line_ids': [
                            (0, 0, {
                                'account_id': asset_account,
                                'debit': unit_value,
                                'credit': 0.0,
                                'name': f'{group_name} #{i + 1}',
                                'partner_id': partner_id,
                            }),
                            (0, 0, {
                                'account_id': source_account,
                                'debit': 0.0,
                                'credit': unit_value,
                                'name': f'{group_name} #{i + 1}',
                            }),
                        ]
                    })
                    move.action_post()

                    # Reconcile 1613 vs capitalization if possible
                    valuation_move = dziritad_line.accountmov
                    if valuation_move and valuation_move.state == 'posted':
                        stock_line = valuation_move.line_ids.filtered(
                            lambda l: l.account_id.code == '1613' and l.debit > 0
                        )[:1]
                        gadziri_line = move.line_ids.filtered(
                            lambda l: l.account_id.code == '1613' and l.credit > 0
                        )[:1]
                        if stock_line and gadziri_line:
                            (stock_line + gadziri_line).reconcile()

                    # Create asset
                    asset_line = move.line_ids.filtered(
                        lambda l: l.debit > 0 and l.account_id.id == asset_account
                    )
                    asset = Asset.create({
                        'name': group_name,  # f'{group_name} #{i + 1}',
                        'original_value': unit_value,
                        'acquisition_date': self.date,
                        'account_asset_id': asset_account,
                        'account_depreciation_id': dziritad_line.account_depr_id.id,
                        'account_depreciation_expense_id': expense_account.id,
                        'original_move_line_ids': [(6, 0, asset_line.ids)],
                        'method_number': dziritad_line.depreciation_duration_months or 5,
                        'method_period': '12',
                        'gadziritadeba_line_id': dziritad_line.id,
                        'maragiskodi': refkodd,
                        'aqtnumbos': self.aqtnumb,
                        'x_studio_': 1.0,
                    })

                    if hasattr(asset, 'validate'):
                        asset.with_context(asset_validate=True).validate()

                                        # Asset movement record
                    # Asset movement + line
                    movement = Assetmovv.create({
                        'operation_type_id': 1,     # Many2one ID (e.g. 1 = "გაძირითადება")
                        'date': self.date,
                        'employee_id': 1,       # set real employee if you have it
                        #'department_id': False,     # optional
                        #'location': False,          # set location many2one if you want
                        # let state default (e.g. 'draft' / 'confirmed')
                    })

                    AssetMovLine.create({
                        'movement_id': movement.id,  # or the real field name if different
                        'asset_id': asset.id,
                    })
                    # 🔔 create activity for user 1
                    self._create_movement_activity(movement)                    

            # 2) SINGLE ASSET FOR TOTAL
            else:
                move = Move.create({
                    'date': self.date,
                    'journal_id': journal.id,
                    'ref': f'ექსპლუატაცია {group_name}',
                    'line_ids': [
                        (0, 0, {
                            'account_id': asset_account,
                            'debit': total_value,
                            'credit': 0.0,
                            'name': group_name,
                            'partner_id': partner_id,
                        }),
                        (0, 0, {
                            'account_id': source_account,
                            'debit': 0.0,
                            'credit': total_value,
                            'name': group_name,
                        }),
                    ]
                })
                move.action_post()

                valuation_move = dziritad_line.accountmov
                if valuation_move and valuation_move.state == 'posted':
                    stock_line = valuation_move.line_ids.filtered(
                        lambda l: l.account_id.code == '1613' and l.debit > 0
                    )[:1]
                    gadziri_line = move.line_ids.filtered(
                        lambda l: l.account_id.code == '1613' and l.credit > 0
                    )[:1]
                    if stock_line and gadziri_line and abs(stock_line.debit - gadziri_line.credit) < 0.01:
                        (stock_line + gadziri_line).reconcile()

                asset_line = move.line_ids.filtered(
                    lambda l: l.debit > 0 and l.account_id.id == asset_account
                )
                asset = Asset.create({
                    'name': group_name,
                    'original_value': total_value,     # ✅ was unit_value (undefined) before
                    'acquisition_date': self.date,
                    'account_asset_id': asset_account,
                    'account_depreciation_id': dziritad_line.account_depr_id.id,
                    'account_depreciation_expense_id': expense_account.id,
                    'original_move_line_ids': [(6, 0, asset_line.ids)],
                    'method_number': dziritad_line.depreciation_duration_months or 5,
                    'method_period': '12',
                    'gadziritadeba_line_id': dziritad_line.id,
                    'maragiskodi': refkodd,
                    'aqtnumbos': self.aqtnumb,
                    'x_studio_': dziritad_line.quantity,
                })

                if hasattr(asset, 'validate'):
                    asset.with_context(asset_validate=True).validate()


                # Asset movement + line
                movement = Assetmovv.create({
                    'operation_type_id': 1,     # Many2one ID (e.g. 1 = "გაძირითადება")
                    'date': self.date,
                    'employee_id': 1,       # set real employee if you have it
                    #'department_id': False,     # optional
                    #'location': False,          # set location many2one if you want
                    # let state default (e.g. 'draft' / 'confirmed')
                })

                AssetMovLine.create({
                    'movement_id': movement.id,  # or the real field name if different
                    'asset_id': asset.id,
                })
                # 🔔 create activity for user 1
                self._create_movement_activity(movement)
        # --- მცირე ფასიანი (mcirefas) ---
        mcirefas_lines = self.gadziritadeba_line_ids.filtered(
            lambda l: not l.dziritad and not l.group_asset_name and l.mcirefas
        )

        if mcirefas_lines:
            journal = self.env['account.journal'].search([('type', '=', 'general')], limit=1)
            expense_7460 = self.env['account.account'].search([('code', '=', '7460')], limit=1)
            stock_1613 = self.env['account.account'].search([('code', '=', '1613')], limit=1)

            if not journal or not expense_7460 or not stock_1613:
                raise UserError("Accounts 7460 or 1613 or general journal not found.")

            for line in mcirefas_lines:
                amount = line.sumofdzs or 0.0

                # Accounting move: expense 7460 vs stock 1613
                move = Move.create({
                    'date': self.date,
                    'journal_id': journal.id,
                    'ref': f'მცირე ფასიანი {line.product_id.display_name}',
                    'line_ids': [
                        (0, 0, {
                            'account_id': expense_7460.id,
                            'debit': amount,
                            'credit': 0.0,
                            'name': line.product_id.display_name,
                            'partner_id': partner_id,
                        }),
                        (0, 0, {
                            'account_id': stock_1613.id,
                            'debit': 0.0,
                            'credit': amount,
                            'name': line.product_id.display_name,
                        }),
                    ],
                })
                move.action_post()

                # Reconcile 1613 with valuation move if exists
                valuation_move = line.accountmov
                if valuation_move and valuation_move.state == 'posted':
                    stock_line = valuation_move.line_ids.filtered(
                        lambda l: l.account_id.code == '1613' and l.debit > 0
                    )[:1]
                    gadziri_line = move.line_ids.filtered(
                        lambda l: l.account_id.code == '1613' and l.credit > 0
                    )[:1]
                    if stock_line and gadziri_line and abs(stock_line.debit - gadziri_line.credit) < 0.01:
                        (stock_line + gadziri_line).reconcile()

                # Create zero-valued asset (mark as მცირე ფასიანი)
                mc_asset_account = line.account_id.id or expense_7460.id
                mc_depr_account = line.account_depr_id.id if getattr(line, 'account_depr_id', False) else expense_7460.id

                asset = Asset.create({
                    'name': line.product_id.display_name,
                    'original_value': 0.0,
                    'acquisition_date': self.date,
                    'account_asset_id': mc_asset_account,
                    'account_depreciation_id': mc_depr_account,
                    'account_depreciation_expense_id': expense_7460.id,
                    'method_number': getattr(line, 'depreciation_duration_months', 1) or 1,
                    'method_period': '12',
                    'gadziritadeba_line_id': line.id,
                    'maragiskodi': line.product_id.default_code or '',
                    'aqtnumbos': self.aqtnumb,
                    'mcirefasiani': True,
                })

                if hasattr(asset, 'validate'):
                    asset.with_context(asset_validate=True).validate()

        self.write({'state': 'validated'})


    def _create_movement_activity(self, movement):
        """Create an activity on asset.movement for user 1 after capitalization."""
        # standard TODO activity type
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        if not activity_type or not movement:
            return

        model_id = self.env['ir.model']._get_id('asset.movement')

        self.env['mail.activity'].create({
            'res_model_id': model_id,
            'res_id': movement.id,
            'activity_type_id': activity_type.id,
            'user_id': 1,  # user with id 1 (usually Administrator)
            'summary': 'გაძირითადება',
            'note': 'მოხდა გაძირითადება, შეამოწმეთ',
            'date_deadline': fields.Date.context_today(self),
        })    

    def action_reset_draft(self):
        """Reset record back to draft state"""
        self.ensure_one()
        self.write({'state': 'draft'})

    def action_seen_draft(self):
        """Record has been checked"""
        self.ensure_one()

        if self.state != 'draft':
            raise UserError("Only draft records can be checked.")

        self.write({'state': 'seen'})
