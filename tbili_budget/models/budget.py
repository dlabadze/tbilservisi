from odoo import models, fields, api
from odoo.exceptions import ValidationError
import requests
import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = 'stock.move'

    request_number = fields.Char(string='Request Number')

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create to copy custom fields from purchase order line to stock move
        when the move is created from a purchase order.
        """
        for vals in vals_list:
            purchase_line_id = vals.get('purchase_line_id')
            if purchase_line_id and 'request_number' not in vals:
                purchase_line = self.env['purchase.order.line'].browse(purchase_line_id)

                # Copy x_studio_ from purchase.order.line to request_number in stock.move
                if hasattr(purchase_line, 'x_studio_') and purchase_line.x_studio_:
                    vals['request_number'] = purchase_line.x_studio_
                    _logger.info(f'Copied x_studio_ to request_number from purchase line {purchase_line_id}: {purchase_line.x_studio_}')

        return super().create(vals_list)

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    # Add budget tracking fields
    purchase_plan_id = fields.Many2one('purchase.plan', string='Purchase Plan')
    purchase_plan_line_id = fields.Many2one(
        'purchase.plan.line',
        string='Purchase Plan Line',
        domain="[('plan_id', '=', purchase_plan_id)]"
    )
    budget_analytic_id = fields.Many2one(
        'budget.analytic',
        string='Budget',
        domain="[('date_to', '>=', context_today().strftime('%Y-%m-%d'))]"
    )
    available_budget_line_ids = fields.Many2many(
        'budget.line',
        compute='_compute_available_budget_lines',
        store=False
    )
    budget_line_id = fields.Many2one(
        'budget.line',
        string='Budget Line',
        domain="[('id', 'in', available_budget_line_ids)]"
    )
    budget_line_account_id = fields.Many2one(
        'account.analytic.account',
        string='Account',
        related='budget_line_id.account_id',
        readonly=True,
        store=False
    )

    @api.depends('budget_analytic_id')
    def _compute_available_budget_lines(self):
        """Compute available budget lines based on selected budget analytic"""
        for record in self:
            if record.budget_analytic_id:
                budget_lines = self.env['budget.line'].search([
                    ('budget_analytic_id', '=', record.budget_analytic_id.id)
                ])
                record.available_budget_line_ids = budget_lines
            else:
                record.available_budget_line_ids = False

    def _prepare_stock_move_vals(self, picking, price_unit, product_uom_qty, product_uom):
        """
        Override to add custom fields from purchase order line to stock move.
        This ensures that custom fields are copied from RFQ lines to receipt lines.
        """
        vals = super()._prepare_stock_move_vals(picking, price_unit, product_uom_qty, product_uom)

        # Copy x_studio_ from purchase.order.line to request_number in stock.move
        if hasattr(self, 'x_studio_') and self.x_studio_:
            vals['request_number'] = self.x_studio_
            _logger.info(f'Copying x_studio_ to request_number: {self.x_studio_}')

        return vals

class CPVCode(models.Model):
    _name = 'cpv.code'
    _description = 'Common Procurement Vocabulary Codes'
    _rec_name = 'code'

    code = fields.Char('CPV Code', required=True, index=True)
    name = fields.Char('CPV Name', required=True)
    budget_line_ids = fields.Many2many(
        'budget.line',
        'cpv_budget_rel',
        'cpv_id',
        'budget_line_id',
        string='ბიუჯეტის ხაზები'
    )

    _sql_constraints = [
        ('cpv_code_unique', 'unique(code)', 'CPV Code must be unique!')
    ]


class BudgetLine(models.Model):
    _inherit = 'budget.line'
    purchase_plan_id = fields.Many2one('purchase.plan', string='შესყიდვების გეგმა')
    cpv_line_ids = fields.One2many('budget.cpv.line', 'budget_line_id', string='CPV Lines')
    pur_plan_am = fields.Monetary(string='შესყიდვების გეგმა', currency_field='currency_id')
    pu_re_am = fields.Monetary(string='გეგმის რესურსი სავარუდო შესყიდვით', currency_field='currency_id')
    cont_am = fields.Monetary(string='ხელშეკრულების თანხა', currency_field='currency_id')
    co_re_am = fields.Monetary(string='გეგმის რესურსი ხელშეკრულებით', currency_field='currency_id')
    paim_am = fields.Monetary(string='გადახდილი თანხა', currency_field='currency_id')
    pa_re_am = fields.Monetary(string='დარჩენილი რესურსი', compute='_compute_pa_re_am', currency_field='currency_id',
                               store=True)

    write_off_resource = fields.Monetary(
        string='ჩამოწერის რესურსი',
        compute='_compute_write_off_resource',
        store=True,
        currency_field='currency_id',
        help='Budget Amount minus x_studio_ field'
    )

    request_resource = fields.Monetary(
        string='მოთხოვნის მიხედვით რესურსი',
        compute='_compute_request_resource',
        store=True,
        currency_field='currency_id',
        help='Budget Amount minus x_studio_reserved field'
    )

    @api.depends('budget_amount')
    def _compute_write_off_resource(self):
        """Compute write off resource: budget_amount - x_studio_"""
        for record in self:
            # Safely get x_studio_ value, handle if field doesn't exist
            x_studio_value = 0
            if hasattr(record, 'x_studio_') and record.x_studio_:
                x_studio_value = record.x_studio_
            record.write_off_resource = record.budget_amount - x_studio_value

    @api.depends('budget_amount')
    def _compute_request_resource(self):
        """Compute request resource: budget_amount - x_studio_reserved"""
        for record in self:
            # Safely get x_studio_reserved value, handle if field doesn't exist
            x_studio_reserved_value = 0
            if hasattr(record, 'x_studio_reserved') and record.x_studio_reserved:
                x_studio_reserved_value = record.x_studio_reserved
            record.request_resource = record.budget_amount - x_studio_reserved_value

    purchase_order_ids = fields.Many2many(
        'purchase.order',
        compute='_compute_purchase_orders',
        string='Purchase Orders',
        store=False
    )

    purchase_requisition_ids = fields.Many2many(
        'purchase.requisition',
        compute='_compute_purchase_requisitions',
        string='Purchase Agreements',
        store=False
    )

    requisition_line_ids = fields.One2many(
        'purchase.requisition.line',
        'budget_line_id',
        string='Purchase Requisition Lines'
    )

    @api.depends('requisition_line_ids', 'requisition_line_ids.requisition_id')
    def _compute_purchase_orders(self):
        """Compute purchase orders related to this budget line through requisition lines"""
        for record in self:
            # Get all requisitions linked to this budget line
            requisitions = record.requisition_line_ids.mapped('requisition_id')

            # Get all purchase orders linked to those requisitions
            purchase_orders = self.env['purchase.order'].search([
                ('requisition_id', 'in', requisitions.ids)
            ])

            record.purchase_order_ids = purchase_orders

    @api.depends('requisition_line_ids')
    def _compute_purchase_requisitions(self):
        """Compute purchase requisitions related to this budget line"""
        for record in self:
            # Get unique requisitions from requisition lines
            requisitions = record.requisition_line_ids.mapped('requisition_id')

            record.purchase_requisition_ids = requisitions

    @api.depends('budget_amount', 'paim_am')
    def _compute_pa_re_am(self):
        for record in self:
            record.pa_re_am = record.budget_amount - record.paim_am

    def write(self, vals):
        res = super().write(vals)
        if 'cont_am' in vals:
            for record in self:
                record.co_re_am = record.budget_amount - record.cont_am

        # Update x_plan fields in CPV lines
        x_plan_fields = [field for field in vals if field.startswith('x_plan')]
        if x_plan_fields:
            for record in self:
                if record.cpv_line_ids:
                    # Force recomputation of selected_plan_name
                    record.cpv_line_ids._compute_selected_plan_name()

        return res

    @api.onchange('budget_amount', 'cont_am')
    def _onchange_co_re_am(self):
        for record in self:
            if record.budget_amount and record.cont_am:
                record.co_re_am = record.budget_amount - record.cont_am

    @api.onchange('budget_amount')
    def _onchange_budget_amount(self):
        for record in self:
            record.pu_re_am = record.budget_amount
            record.co_re_am = record.budget_amount

    @api.depends('cpv_line_ids.amount')
    def _onchange_cpv_lines(self):
        for record in self:
            record.write({
                'pur_plan_am': sum(record.cpv_line_ids.mapped('amount')),
                'pu_re_am': record.budget_amount - record.pur_plan_am,
                'co_re_am': record.budget_amount - record.cont_am,
                'pa_re_am': record.budget_amount - record.paim_am
            })

    @api.onchange('purchase_plan_id')
    def _onchange_purchase_plan(self):
        if self.purchase_plan_id and self.purchase_plan_id.currency_id != self.currency_id:
            self.purchase_plan_id.currency_id = self.currency_id


class PurchasePlan(models.Model):
    _name = 'purchase.plan'
    _description = 'Purchase Plan'

    start_date = fields.Date(string='პერიოდის დასაწყისი', required=True)
    end_date = fields.Date(string='პერიოდის დასასრული', required=True)
    currency_id = fields.Many2one('res.currency', required=True, default=lambda self: self.env.company.currency_id)
    line_ids = fields.One2many('purchase.plan.line', 'plan_id', string='Purchase Plan Lines')
    name = fields.Char(string='დასახელება', required=True)
    pu_ac_am_total = fields.Monetary(
        string='მიმდინარე ღირებულების ჯამი',
        store=True,
        compute='_compute_pu_ac_am_total'
    )

    @api.depends('line_ids.pu_ac_am', 'line_ids')
    def _compute_pu_ac_am_total(self):
        for rec in self:
            rec.pu_ac_am_total = sum(rec.line_ids.mapped('pu_ac_am'))

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for record in self:
            if record.start_date and record.end_date and record.start_date > record.end_date:
                raise ValidationError('პერიოდის დასაწყისი თარიღი ვერ იქნება დასასრულ თარიღზე მეტი')

    def unlink(self):
        # Store references to related records
        purchase_plan_lines = self.mapped('line_ids')
        budget_cpvs = purchase_plan_lines.mapped('budget_cpv_id')

        # Store original values for reversal
        original_budget_cpv_amounts = {cpv.id: cpv.amount for cpv in budget_cpvs}

        # First delete purchase plan lines to trigger their unlink methods
        purchase_plan_lines.unlink()

        # Then delete the purchase plan
        res = super(PurchasePlan, self).unlink()

        # Cleanup any remaining related records
        if budget_cpvs:
            for cpv in budget_cpvs:
                # Attempt to reset or delete orphaned budget CPV records
                if not cpv.line_ids:
                    cpv.unlink()

        return res

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class PurchaseMethod(models.Model):
    _name = 'purchase.method'
    _description = 'Purchase Method'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True)


class PurchaseReason(models.Model):
    _name = 'purchase.reason'
    _description = 'Purchase Reason'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True)


class PurchasePlanTag(models.Model):
    _name = 'purchase.plan.tag'
    _description = 'Purchase Plan Tag'
    _order = 'sequence, name'

    name = fields.Char(string='Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    color = fields.Integer(string='Color Index', default=0)


class PurchasePlanVariant(models.Model):
    _name = 'purchase.plan.variant'
    _description = 'Purchase Plan Variant'
    _rec_name = 'name'

    name = fields.Char(
        string='Variant Name',
        required=True
    )


import logging
from odoo import models, fields, api
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)


class PurchasePlanLine(models.Model):
    _name = 'purchase.plan.line'
    _description = 'Purchase Plan Line'
    _rec_name = 'name'

    change_id = fields.Many2one('purchase.plan.changes', string='ცვლილებები')
    plan_id = fields.Many2one('purchase.plan', string='Purchase Plan', required=True, ondelete='cascade')
    budget_cpv_id = fields.Many2one('budget.cpv', string='ბიუჯეტის CPV')
    # Add a field to track if the record is saved and has a budget_cpv_id
    budget_cpv_readonly = fields.Boolean(compute='_compute_budget_cpv_readonly', store=True)
    cpv_id = fields.Many2one('cpv.code', string='CPV კოდი', required=True)
    cpv_name = fields.Char(related='cpv_id.name', string='CPV კოდის დასახელება', readonly=True)
    pu_st_am = fields.Monetary(string='პირვანდელი ღირებულება', currency_field='currency_id', tracking=True)
    pu_diff = fields.Monetary(string='სხვაობა', compute='_compute_pu_diff', currency_field='currency_id', store=True,
                              help='პირვანდელი ღირებულება - მიმდინარე ღირებულება')
    pcon_am = fields.Monetary(string='ხელშეკრულების თანხა', currency_field='currency_id', tracking=True)
    pc_re_am = fields.Monetary(string='დარჩენილი რესურსი ხელშეკრულებით', compute='_compute_pc_re_am',
                               currency_field='currency_id', store=True,
                               help='მიმდინარე ღირებულება - ხელშეკრულების თანხა')
    currency_id = fields.Many2one(related='plan_id.currency_id', store=True)
    paim_am = fields.Monetary(string='გადახდილი თანხა', currency_field='currency_id')
    pu_ac_am = fields.Monetary(string='მიმდინარე ღირებულება', currency_field='currency_id', tracking=True)
    name = fields.Char(compute='_compute_name', store=True)
    pa_re_am = fields.Monetary(string='დარჩენილი რესურსი', compute='_compute_pu_re_am', currency_field='currency_id',
                               store=True)
    currency_id = fields.Many2one('res.currency', required=True, default=lambda self: self.env.company.currency_id)
    budget_lines_total = fields.Monetary(string='Budget Lines Total', compute='_compute_budget_lines_totals',
                                         currency_field='currency_id', store=True)
    budget_lines_available = fields.Monetary(string='Budget Lines Available', compute='_compute_budget_lines_totals',
                                             currency_field='currency_id', store=True)
    budget_lines_allocated = fields.Monetary(string='Budget Lines Allocated', compute='_compute_budget_lines_totals',
                                             currency_field='currency_id', store=True)
    remaining_to_allocate = fields.Monetary(string='Remaining to Allocate', compute='_compute_remaining_to_allocate',
                                            currency_field='currency_id', store=True)
    total_changes = fields.Monetary(related='change_id.total_changes', string='ცვლილებების ჯამი', readonly=True,
                                    store=True, currency_field='currency_id')

    # Tags field for quarterly planning
    tag_ids = fields.Many2many(
        'purchase.plan.tag',
        'purchase_plan_line_tag_rel',
        'line_id',
        'tag_id',
        string='Quarter Tags'
    )

    purchase_order_ids = fields.Many2many(
        'purchase.order',
        compute='_compute_purchase_orders',
        string='Purchase Orders',
        store=False
    )

    # Computed field to show count of purchase orders
    purchase_orders_count = fields.Integer(
        string='Purchase Orders Count',
        compute='_compute_purchase_orders',
        store=True
    )

    @api.depends('requisition_line_ids', 'requisition_line_ids.requisition_id')
    def _compute_purchase_orders(self):
        for record in self:
            # Get all requisitions linked to this plan line
            requisitions = record.requisition_line_ids.mapped('requisition_id')

            # Get all purchase orders linked to those requisitions
            purchase_orders = self.env['purchase.order'].search([
                ('requisition_id', 'in', requisitions.ids)
            ])

            record.purchase_order_ids = purchase_orders
            record.purchase_orders_count = len(purchase_orders)

    # Multiple selection field using Many2many
    variant_ids = fields.Many2many(
        'purchase.plan.variant',
        'purchase_plan_line_variant_rel',
        'line_id',
        'variant_id',
        string='Variants',
        help='Select one or more variants'
    )

    # One2many field to show all purchase requisition lines linked to this purchase plan line
    requisition_line_ids = fields.One2many(
        'purchase.requisition.line',
        'purchase_plan_line_id',
        string='Purchase Requisition Lines'
    )

    # Computed field to show count of requisition lines
    requisition_lines_count = fields.Integer(
        string='Requisition Lines Count',
        compute='_compute_requisition_lines_count',
        store=True
    )

    # One2many field to show all payment purchase plan lines linked to this purchase plan line
    payment_plan_line_ids = fields.One2many(
        'account.payment.purchase.plan.line',
        'purchase_plan_line_id',
        string='Payment Plan Lines'
    )

    # Computed field to show count of payment plan lines
    payment_plan_lines_count = fields.Integer(
        string='Payment Plan Lines Count',
        compute='_compute_payment_plan_lines_count',
        store=True
    )

    # ADD THESE COMPUTED METHODS:

    @api.onchange('pu_ac_am', 'x_studio_reserved')
    def _onchange_remaining_resource(self):
        """Calculate remaining resource when current value or reserved amount changes"""
        for record in self:
            # Safely get x_studio_reserved value, handle if field doesn't exist
            reserved_value = 0.0
            if hasattr(record, 'x_studio_reserved'):
                reserved_value = record.x_studio_reserved or 0.0

            # Safely set x_studio_remaining_resource if it exists
            if hasattr(record, 'x_studio_remaining_resource'):
                record.x_studio_remaining_resource = (record.pu_ac_am or 0.0) - reserved_value

    @api.depends('requisition_line_ids')
    def _compute_requisition_lines_count(self):
        for record in self:
            record.requisition_lines_count = len(record.requisition_line_ids)

    @api.depends('payment_plan_line_ids')
    def _compute_payment_plan_lines_count(self):
        for record in self:
            record.payment_plan_lines_count = len(record.payment_plan_line_ids)

    # New selection fields
    funding_source = fields.Selection([
        ('1', 'სახელმწიფო ბიუჯეტი'),
        ('2', 'ავტ. რეს, ბიუჯეტი'),
        ('3', 'ადგილობრივი ბიუჯეტი'),
        ('4', 'საკუთარი სახსრები'),
        ('5', 'გრანტი/კრედიტი'),
    ], string='დაფინანსების წყარო')

    purchase_method_id = fields.Many2one('purchase.method', string='შესყიდვის საშუალებები')
    purchase_reason_id = fields.Many2one('purchase.reason', string='შესყიდვის საფუძველი')

    purchase_method_code = fields.Char(related='purchase_method_id.code', store=True)


    # Helper field to store allowed reason IDs for domain
    allowed_reason_ids = fields.Many2many('purchase.reason', compute='_compute_allowed_reason_ids')

    @api.depends('purchase_method_id')
    def _compute_allowed_reason_ids(self):
        for record in self:
            if record.purchase_method_id and record.purchase_method_id.code == '6':
                # გამარტივებული ელექტრონული ტენდერი - only 9, 10
                allowed_reasons = self.env['purchase.reason'].search([('code', 'in', ['9', '10'])])
                record.allowed_reason_ids = allowed_reasons
            elif record.purchase_method_id and record.purchase_method_id.code == '5':
                # გამარტივებული შესყიდვა - all except 9, 10
                allowed_reasons = self.env['purchase.reason'].search([('code', 'not in', ['10'])])
                record.allowed_reason_ids = allowed_reasons
            else:
                # All other methods - show all reasons
                allowed_reasons = self.env['purchase.reason'].search([])
                record.allowed_reason_ids = allowed_reasons

    @api.onchange('purchase_method_id')
    def _onchange_purchase_method(self):
        # Clear purchase_reason when method changes
        self.purchase_reason_id = False

    vadebi = fields.Selection([
        ('1', 'ერთწლიანი'),
        ('2', 'ორწლიანი'),
        ('3', 'სამწლიანი'),
        ('4', 'ოთხწლიანი'),
    ], string='შესყიდვის ვადები')

    pricekurant = fields.Selection([
        ('1', 'კი'),
        ('2', 'არა'),
    ], string='პრეისკურანტი')

    @api.depends('budget_cpv_id')
    def _compute_budget_cpv_readonly(self):
        for record in self:
            if not record._origin.id:
                record.budget_cpv_readonly = False
            else:
                record.budget_cpv_readonly = bool(record.budget_cpv_id)

    @api.depends('budget_cpv_id.line_ids.budget_amount',
                 'budget_cpv_id.line_ids.pu_re_am',
                 'budget_cpv_id.line_ids.amount')
    def _compute_budget_lines_totals(self):
        for record in self:
            if record.budget_cpv_id:
                lines = record.budget_cpv_id.line_ids
                record.budget_lines_total = sum(lines.mapped('budget_amount'))
                record.budget_lines_available = sum(lines.mapped('pu_re_am'))
                record.budget_lines_allocated = sum(lines.mapped('amount'))
            else:
                record.budget_lines_total = 0
                record.budget_lines_available = 0
                record.budget_lines_allocated = 0

    @api.depends('pu_ac_am', 'budget_lines_allocated')
    def _compute_remaining_to_allocate(self):
        for record in self:
            record.remaining_to_allocate = record.pu_ac_am - record.budget_lines_allocated

    @api.depends('pu_ac_am', 'paim_am')
    def _compute_pu_re_am(self):
        for record in self:
            record.pa_re_am = record.pu_ac_am - record.paim_am

    @api.depends('cpv_id.code', 'cpv_name')
    def _compute_name(self):
        for record in self:
            record.name = f"{record.cpv_id.code} - {record.cpv_name}" if record.cpv_id else ''

    @api.depends('pu_st_am', 'pu_ac_am')
    def _compute_pu_diff(self):
        for record in self:
            record.pu_diff = record.pu_st_am - record.pu_ac_am

    @api.depends('pu_ac_am', 'pcon_am')
    def _compute_pc_re_am(self):
        for record in self:
            record.pc_re_am = record.pu_ac_am - record.pcon_am

    @api.onchange('pu_st_am')
    def _onchange_pu_st_am(self):
        """When initial amount changes, update current amount if no changes exist"""
        for record in self:
            if not record.change_id or not record.change_id.line_ids:
                record.pu_ac_am = record.pu_st_am
            else:
                # If changes exist, recalculate based on changes
                record.pu_ac_am = record.pu_st_am + record.change_id.total_changes

    @api.onchange('cpv_id')
    def create_budget_cpv(self):
        if self.cpv_id and not self.budget_cpv_id:
            max_id = self.env['budget.cpv'].search([], order='custom_id desc', limit=1).custom_id or 0
            vals = {
                'custom_id': max_id + 1,
                'name': self.cpv_id.id,
                'cpv_name': self.cpv_id.name,
                'cpv_code': self.cpv_id.code,
                'amount': self.pu_ac_am or 0,
                'currency_id': self.currency_id.id,
            }
            new_budget_cpv = self.env['budget.cpv'].create(vals)
            self.budget_cpv_id = new_budget_cpv.id

    # @api.onchange('cpv_id')
    # def create_plan_changes(self):
    #     # For new records (NewId), don't create change records here
    #     # Let the create() method handle it after the plan is properly saved
    #     if self.cpv_id and self.plan_id and self.plan_id.id:
    #         # Only handle this for existing, saved plans
    #         _logger.info(
    #             f"[ONCHANGE] Creating/finding change record for CPV {self.cpv_id.id} in plan {self.plan_id.id}")
    #
    #         existing_change = self.env['purchase.plan.changes'].search([
    #             ('name', '=', self.cpv_id.id),
    #             ('plan_id', '=', self.plan_id.id),
    #             ('currency_id', '=', self.currency_id.id)
    #         ], limit=1)
    #
    #         if existing_change:
    #             _logger.info(f"[ONCHANGE] Found existing change record {existing_change.id}")
    #             self.change_id = existing_change.id
    #         else:
    #             _logger.info(f"[ONCHANGE] No existing change record found, will create in create() method")
    #     else:
    #         _logger.info(f"[ONCHANGE] Skipping change record creation - plan not saved yet or missing data")

    @api.model
    def create(self, vals):
        _logger.info(f"[CREATE] Creating purchase plan line with vals: {vals}")

        # Create the record first
        res = super(PurchasePlanLine, self).create(vals)
        _logger.info(f"[CREATE] Created purchase plan line {res.id} in plan {res.plan_id.id}")

        # Set initial default values if not provided
        if 'pu_st_am' in vals and not 'pu_ac_am' in vals:
            res.pu_ac_am = vals['pu_st_am']
        elif 'pu_ac_am' in vals and not 'pu_st_am' in vals:
            res.pu_st_am = vals['pu_ac_am']

        # ALWAYS create a NEW unique change record for this plan line
        if res.cpv_id and not res.change_id:
            _logger.info(f"[CREATE] Creating unique change record for plan line {res.id}")

            max_id = self.env['purchase.plan.changes'].search([], order='custom_id desc', limit=1).custom_id or 0
            change_vals = {
                'custom_id': max_id + 1,
                'name': res.cpv_id.id,
                'plan_id': res.plan_id.id,
                'plan_line_id': res.id,  # ADD THIS - link to specific plan line
                'currency_id': res.currency_id.id,
                'amount': 0
            }
            _logger.info(f"[CREATE] Creating new change record with vals: {change_vals}")
            new_change = self.env['purchase.plan.changes'].create(change_vals)
            _logger.info(f"[CREATE] Created new change record {new_change.id} for plan line {res.id}")
            res.write({'change_id': new_change.id})

        # Update budget CPV amount
        res._update_budget_cpv_amount()

        # Update change amount
        res._update_change_amount()

        return res

    def write(self, vals):
        if 'budget_cpv_id' in vals:
            for record in self:
                if record.budget_cpv_id:
                    # Remove this field from vals to prevent the change
                    vals.pop('budget_cpv_id')

        if 'change_id' in vals:
            for record in self:
                if record.change_id:
                    # Remove this field from vals to prevent the change
                    vals.pop('change_id')

        if 'cpv_name' in vals:
            for record in self:
                if record.cpv_name:
                    # Remove this field from vals to prevent the change
                    vals.pop('cpv_name')

        # If changing pu_st_am but not pu_ac_am and no changes exist
        if 'pu_st_am' in vals and not 'pu_ac_am' in vals:
            for record in self:
                if not record.change_id or not record.change_id.line_ids:
                    vals['pu_ac_am'] = vals['pu_st_am']
                else:
                    # If changes exist, recalculate based on changes
                    vals['pu_ac_am'] = vals['pu_st_am'] + record.change_id.total_changes

        # If changing pu_ac_am but not through changes, we should update pu_st_am
        # and create a change record to track the difference
        if 'pu_ac_am' in vals and not self.env.context.get('from_change_update'):
            for record in self:
                old_ac_am = record.pu_ac_am
                new_ac_am = vals['pu_ac_am']

                # If there's a change and no pu_st_am change specified
                if old_ac_am != new_ac_am and not 'pu_st_am' in vals:
                    # If no change_id or no changes yet, just update pu_st_am
                    if not record.change_id or not record.change_id.line_ids:
                        vals['pu_st_am'] = new_ac_am
                    else:
                        # There are existing changes, so we need to add a new change
                        # to account for the difference
                        difference = new_ac_am - (record.pu_st_am + record.change_id.total_changes)

                        if abs(difference) > 0.01:  # Small threshold to avoid rounding errors
                            # Create a new change line
                            self.env['purchase.plan.changes.line'].create({
                                'change_id': record.change_id.id,
                                'date': fields.Date.context_today(self),
                                'amount': difference,
                                'comment': 'Manual adjustment'
                            })
                            # Mark that we're handling this through changes
                            vals['pu_ac_am'] = record.pu_st_am + record.change_id.total_changes + difference

        res = super(PurchasePlanLine, self).write(vals)

        # Update amounts when relevant fields change
        if 'pu_ac_am' in vals or 'budget_cpv_id' in vals:
            self._update_budget_cpv_amount()

        if 'pu_ac_am' in vals or 'change_id' in vals:
            self._update_change_amount()

        return res

    def _update_budget_cpv_amount(self):
        """Update budget CPV amount based on sum of all related purchase plan lines"""
        for line in self:
            if line.budget_cpv_id:
                total_amount = sum(self.search([
                    ('budget_cpv_id', '=', line.budget_cpv_id.id)
                ]).mapped('pu_ac_am'))
                line.budget_cpv_id.write({'amount': total_amount})

    def _update_change_amount(self):
        """Update change amount based on this specific purchase plan line"""
        for line in self:
            if line.change_id:
                # Update the change record amount to match THIS line's amount
                line.change_id.write({'amount': line.pu_ac_am})
                _logger.info(f"[UPDATE_CHANGE] Updated change {line.change_id.id} amount to {line.pu_ac_am}")

    def unlink(self):
        # Store changes that need to be updated after deletion
        changes_to_update = set()

        for record in self:
            try:
                # Store all necessary data before any deletions
                restore_data = []

                if record.budget_cpv_id:
                    dependent_records = self.env['budget.cpv.line'].search([
                        ('budget_cpv_id', '=', record.budget_cpv_id.id)
                    ])

                    # Store the data we'll need after deletion
                    for cpv_line in dependent_records:
                        restore_data.append({
                            'budget_line_id': cpv_line.budget_line_id.id,
                            'amount': cpv_line.amount
                        })

                    # First delete budget CPV lines
                    if dependent_records:
                        dependent_records.with_context(skip_budget_line_update=True).unlink()

                    # Then delete the budget CPV
                    record.budget_cpv_id.unlink()

                # Handle change records
                if record.change_id:
                    other_lines = self.search([
                        ('change_id', '=', record.change_id.id),
                        ('id', '!=', record.id)
                    ])

                    if not other_lines:
                        # No other lines use this change, delete it
                        record.change_id.unlink()
                    else:
                        # Other lines use this change, update the amount after deletion
                        changes_to_update.add(record.change_id.id)

                # Now restore the budget line amounts using stored data
                processed_budget_lines = set()
                for data in restore_data:
                    budget_line_id = data['budget_line_id']
                    if budget_line_id not in processed_budget_lines:
                        budget_line = self.env['budget.line'].browse(budget_line_id)
                        if budget_line.exists():
                            # Sum up all amounts for this budget line
                            total_amount = sum(
                                d['amount'] for d in restore_data
                                if d['budget_line_id'] == budget_line_id
                            )

                            # Calculate new amounts
                            new_pur_plan_am = budget_line.pur_plan_am - total_amount
                            new_pu_re_am = budget_line.budget_amount - new_pur_plan_am

                            budget_line.write({
                                'pur_plan_am': new_pur_plan_am,
                                'pu_re_am': new_pu_re_am
                            })
                            processed_budget_lines.add(budget_line_id)

            except Exception as e:
                raise ValidationError(f"Cannot delete the record: {str(e)}")

        # Finally delete the purchase plan line itself
        result = super(PurchasePlanLine, self).unlink()

        # Update change amounts if needed (after deletion)
        if changes_to_update:
            for change_id in changes_to_update:
                change = self.env['purchase.plan.changes'].browse(change_id)
                if change.exists():
                    remaining_lines = self.search([('change_id', '=', change_id)])
                    total_amount = sum(remaining_lines.mapped('pu_ac_am'))
                    change.write({'amount': total_amount})
                    _logger.info(f"[UNLINK] Updated change {change_id} amount to {total_amount} after deletion")

        return result

    def action_view_purchase_plan_line_new(self):
        """Open the purchase plan line in form view"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Purchase Plan Line: {self.name}',
            'res_model': 'purchase.plan.line',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',  # Opens in popup
            'context': self.env.context,
        }

class BudgetCPVLine(models.Model):
    _name = 'budget.cpv.line'
    _description = 'Budget CPV Line'

    budget_cpv_id = fields.Many2one('budget.cpv', string='Budget CPV', required=True, ondelete='cascade')
    budget_line_id = fields.Many2one('budget.line', string='Budget Line', required=True,
                                     domain="[('budget_analytic_id.date_to', '>=', context_today().strftime('%Y-%m-%d'))]")
    amount = fields.Monetary(string='თანხა', currency_field='currency_id')
    currency_id = fields.Many2one(related='budget_cpv_id.currency_id', store=True)
    plan2_display = fields.Char(string='ბიუჯეტის ხაზები', compute='_compute_plan2_display', store=True)

    pu_re_am = fields.Monetary(related='budget_line_id.pu_re_am', string='Available Amount', store=True)
    budget_amount = fields.Monetary(related='budget_line_id.budget_amount', string='Budget Amount', store=True)

    selected_plan_name = fields.Char(string='Selected Plan Name', compute='_compute_selected_plan_name', store=True)

    @api.depends('budget_line_id')
    def _compute_selected_plan_name(self):
        for record in self:
            plan_name = ''
            budget_line = record.budget_line_id

            if budget_line:
                # First check if account_id exists and use its value
                if hasattr(budget_line, 'account_id') and budget_line.account_id and hasattr(budget_line.account_id,
                                                                                             'code'):
                    code = budget_line.account_id.code or ''
                    name = budget_line.account_id.name if hasattr(budget_line.account_id, 'name') else ''
                    plan_name = f"{code} {name}".strip()
                else:
                    # Then check for x_plan fields if account_id isn't available
                    for field_name in budget_line._fields:
                        if field_name.startswith('x_plan'):
                            plan = getattr(budget_line, field_name, False)
                            if plan and hasattr(plan, 'code'):
                                code = plan.code or ''
                                name = plan.name if hasattr(plan, 'name') else ''
                                plan_name = f"{code} {name}".strip()
                                break

            record.selected_plan_name = plan_name

    @api.constrains('amount')
    def _check_cpv_total_amount(self):
        for record in self:
            if record.budget_cpv_id:
                all_cpv_lines = self.search([
                    ('budget_cpv_id', '=', record.budget_cpv_id.id),
                    ('id', '!=', record.id)  # Exclude current record
                ])
                total = sum(line.amount for line in all_cpv_lines) + (record.amount or 0)
                if total > record.budget_cpv_id.amount:
                    raise ValidationError("Total amount of CPV lines cannot exceed the budget CPV amount.")

    @api.constrains('amount')
    def _check_amount(self):
        for record in self:
            if record.budget_line_id:
                all_cpv_lines = self.search([('budget_line_id', '=', record.budget_line_id.id)])
                total = sum(line.amount for line in all_cpv_lines if line.id != record.id) + (record.amount or 0)
                _logger.info(f"total: {total}")
                _logger.info(f"pu re am: {record.budget_line_id.pu_re_am + (record._origin.amount or 0)}")
                if total > record.budget_line_id.budget_amount + (record._origin.amount or 0):
                    raise ValidationError("The total amount exceeds the available budget (pu_re_am).")

    def write(self, vals):
        res = super().write(vals)
        if 'amount' in vals:
            for record in self:
                if record.budget_line_id:
                    all_cpv_lines = self.search([('budget_line_id', '=', record.budget_line_id.id)])
                    total = sum(line.amount for line in all_cpv_lines)
                    record.budget_line_id.write({
                        'pur_plan_am': total,
                        'pu_re_am': record.budget_line_id.budget_amount - total
                    })
        return res

    @api.model
    def create(self, vals):
        record = super().create(vals)
        if record.budget_line_id:
            all_cpv_lines = self.search([('budget_line_id', '=', record.budget_line_id.id)])
            total = sum(line.amount for line in all_cpv_lines)
            if total > record.budget_line_id.budget_amount:
                raise ValidationError("The total amount exceeds the available budget (pu_re_am).")
            record.budget_line_id.write({
                'pur_plan_am': total,
                'pu_re_am': record.budget_line_id.budget_amount - total
            })
        return record

    def unlink(self):
        # Store references to related budget lines and budget CPVs
        budget_lines = self.mapped('budget_line_id')

        # Perform standard deletion
        res = super(BudgetCPVLine, self).unlink()

        # Skip budget line updates if context indicates we're in a cascade delete
        if not self.env.context.get('skip_budget_line_update'):
            # Recompute budget line amounts
            for budget_line_id in set(budget_lines.ids):
                budget_line = self.env['budget.line'].browse(budget_line_id)
                if budget_line.exists():
                    remaining_cpv_lines = self.env['budget.cpv.line'].search([('budget_line_id', '=', budget_line_id)])
                    total = sum(line.amount for line in remaining_cpv_lines)

                    budget_line.write({
                        'pur_plan_am': total,
                        'pu_re_am': budget_line.budget_amount - total
                    })

            # We remove the code that updates the budget_cpv amounts
            # This prevents the amount field from being changed when budget_cpv_line is unlinked

        return res


class BudgetCPV(models.Model):
    _name = 'budget.cpv'
    _description = 'Budget CPV Selection'
    _rec_name = 'cpv_name'

    custom_id = fields.Integer(string='ID', required=True, index=True)
    name = fields.Many2one('cpv.code', string='CPV კოდი')
    amount = fields.Monetary(string='თანხა', currency_field='currency_id')
    cpv_name = fields.Char(string='CPV დასახელება')
    cpv_code = fields.Char(string='CPV კოდი')
    currency_id = fields.Many2one('res.currency', string='ვალუტა')
    budget_line_ids = fields.Many2many('budget.line', 'budget_cpv_line_rel', 'budget_cpv_id', 'budget_line_id',
                                       string='ბიუჯეტის ხაზები')
    line_ids = fields.One2many('budget.cpv.line', 'budget_cpv_id', string='CPV ხაზები')

    # New fields
    total_line_amounts = fields.Monetary(
        string='ხაზების ჯამი',
        compute='_compute_total_line_amounts',
        store=True,
        currency_field='currency_id'
    )
    remaining_amount = fields.Monetary(
        string='დარჩენილი თანხა',
        compute='_compute_total_line_amounts',
        store=True,
        currency_field='currency_id'
    )

    @api.depends('amount', 'line_ids.amount')
    def _compute_total_line_amounts(self):
        for record in self:
            record.total_line_amounts = sum(record.line_ids.mapped('amount'))
            record.remaining_amount = record.amount - record.total_line_amounts

    _sql_constraints = [('custom_id_unique', 'unique(custom_id)', 'ID must be unique!')]


from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class PurchasePlanChanges(models.Model):
    _name = 'purchase.plan.changes'
    _description = 'Purchase Plan Changes'
    _rec_name = 'cpv_name'

    plan_id = fields.Many2one('purchase.plan', string='Purchase Plan', required=True)
    plan_line_id = fields.Many2one('purchase.plan.line', string='Purchase Plan Line', required=True)  # ADD THIS

    custom_id = fields.Integer(string='ID', required=True, index=True)
    name = fields.Many2one('cpv.code', string='CPV კოდი', required=True)
    cpv_name = fields.Char(related='name.name', string='CPV დასახელება', store=True)
    cpv_code = fields.Char(related='name.code', string='CPV კოდი', store=True)
    amount = fields.Monetary(string='თანხა', currency_field='currency_id')
    comment = fields.Text(string='კომენტარი')
    currency_id = fields.Many2one('res.currency', string='ვალუტა')
    line_ids = fields.One2many('purchase.plan.changes.line', 'change_id', string='ცვლილებების ხაზები')
    total_changes = fields.Monetary(
        string='ცვლილებების ჯამი',
        compute='_compute_total_changes',
        store=True,
        currency_field='currency_id'
    )

    # ADD THESE RELATED FIELDS
    purchase_method_id = fields.Many2one(
        related='plan_line_id.purchase_method_id',
        string='შესყიდვის საშუალებები',
        readonly=True,
        store=True
    )
    purchase_reason_id = fields.Many2one(
        related='plan_line_id.purchase_reason_id',
        string='შესყიდვის საფუძველი',
        readonly=True,
        store=True
    )

    @api.depends('line_ids.amount')
    def _compute_total_changes(self):
        for record in self:
            record.total_changes = sum(record.line_ids.mapped('amount'))

    @api.model
    def create(self, vals):
        res = super(PurchasePlanChanges, self).create(vals)
        return res

    def write(self, vals):
        res = super(PurchasePlanChanges, self).write(vals)
        # If name (CPV code) is changed, update related plan line
        if 'name' in vals:
            for record in self:
                if record.plan_line_id and record.plan_line_id.cpv_id.id != vals['name']:
                    record.plan_line_id.cpv_id = vals['name']
        return res

    def unlink(self):
        # Find the specific plan line linked to this change record
        plan_line = self.plan_line_id

        # Perform standard deletion
        res = super(PurchasePlanChanges, self).unlink()

        # Update the plan line after changes are removed
        if plan_line and plan_line.exists():
            plan_line.write({
                'pu_ac_am': plan_line.pu_st_am,
                'change_id': False
            })

            # Update related budget CPV if it exists
            if plan_line.budget_cpv_id:
                plan_line._update_budget_cpv_amount()

        return res

    _sql_constraints = [
        ('custom_id_unique', 'unique(custom_id)', 'ID must be unique!'),
        ('plan_line_unique', 'unique(plan_line_id)', 'Each purchase plan line must have only one changes record!')  # UPDATED CONSTRAINT
    ]


class PurchasePlanChangesLine(models.Model):
    _name = 'purchase.plan.changes.line'
    _description = 'Purchase Plan Changes Line'
    _order = 'date desc, id desc'

    change_id = fields.Many2one('purchase.plan.changes', string='ცვლილება', required=True, ondelete='cascade')
    date = fields.Date(string='თარიღი', required=True, default=fields.Date.context_today)
    amount = fields.Monetary(string='თანხა', currency_field='currency_id')
    comment = fields.Text(string='კომენტარი')
    currency_id = fields.Many2one(related='change_id.currency_id', store=True)

    def _update_plan_line_amount(self):
        """Update the related purchase plan line's amounts"""
        for line in self:
            _logger.info(f"Processing change line ID: {line.id}")

            # Get the SPECIFIC plan line linked to this change record
            if line.change_id and line.change_id.plan_line_id:
                plan_line = line.change_id.plan_line_id

                # Get all changes for this specific change record
                all_changes = self.search([
                    ('change_id', '=', line.change_id.id)
                ])
                total_changes = sum(change.amount for change in all_changes)

                # Update ONLY this specific plan line
                new_amount = plan_line.pu_st_am + total_changes
                plan_line.with_context(from_change_update=True).write({
                    'pu_ac_am': new_amount
                })

                # Update related budget CPV if it exists
                if plan_line.budget_cpv_id:
                    plan_line._update_budget_cpv_amount()

    @api.model
    def create(self, vals):
        record = super(PurchasePlanChangesLine, self).create(vals)
        record._update_plan_line_amount()

        # Update the total changes amount on the parent change record
        if record.change_id:
            record.change_id._compute_total_changes()

        return record

    def write(self, vals):
        res = super(PurchasePlanChangesLine, self).write(vals)
        if 'amount' in vals or 'change_id' in vals:
            self._update_plan_line_amount()

            # If change_id changed, update both old and new parent change records
            if 'change_id' in vals:
                old_change_ids = set(self.mapped('change_id').ids)
                new_changes = self.env['purchase.plan.changes'].browse(vals.get('change_id'))
                if new_changes:
                    old_change_ids.add(new_changes.id)

                for change_id in old_change_ids:
                    change = self.env['purchase.plan.changes'].browse(change_id)
                    if change.exists():
                        change._compute_total_changes()
            # Otherwise just update the current parent change record
            else:
                self.mapped('change_id')._compute_total_changes()

        return res

    def unlink(self):
        # Store the changes and plan lines before deletion
        change_ids = self.mapped('change_id').ids
        plan_lines = self.env['purchase.plan.line'].search([
            ('change_id', 'in', change_ids)
        ])

        # Perform standard deletion
        res = super(PurchasePlanChangesLine, self).unlink()

        # Update parent change records
        changes = self.env['purchase.plan.changes'].browse(change_ids)
        changes._compute_total_changes()

        # Update amounts for affected plan lines
        for plan_line in plan_lines:
            if plan_line.change_id:
                remaining_changes = self.search([
                    ('change_id', '=', plan_line.change_id.id)
                ])
                total_changes = sum(change.amount for change in remaining_changes)
                new_amount = plan_line.pu_st_am + total_changes
                plan_line.write({
                    'pu_ac_am': new_amount
                })

                # Update related budget CPV if it exists
                if plan_line.budget_cpv_id:
                    plan_line._update_budget_cpv_amount()

        return res


class PurchaseRequisitionInherit(models.Model):
    _inherit = 'purchase.requisition'

    # Date fields
    registration_year = fields.Char(string='გაფორმების წელი')
    contract_registration_date = fields.Date(string='ხელშეკრულების გაფორმების თარიღი')
    effective_date = fields.Date(string='ძალაში შესვლის თარიღი')
    delivery_date = fields.Date(string='მოწოდების თარიღი')
    contract_end_date = fields.Date(string='ხელშეკრულების დასრულების თარიღი')
    payment_due_date = fields.Char(string='გადახდის ვადა')

    # String fields
    purchase_method = fields.Char(string='შესყიდვის საშუალება')
    purchase_basis = fields.Char(string='შესყიდვის საფუძველი')
    basis = fields.Char(string='საფუძველი')
    contract_number = fields.Char(string='ხელშეკრულების N')
    contract_number_iur = fields.Char(string='ხელშეკრულების N (იურისტი)')
    spa_number = fields.Char(string='SPA ნომერი')
    cmr_number = fields.Char(string='CMR ნომერი')
    notes = fields.Text(string='შენიშვნა')
    supplier = fields.Char(string='მომწოდებელი')
    supplier_id_code = fields.Char(string='მომწოდებლის საიდ. კოდი')
    cpv_code = fields.Char(string='CPV კოდი')
    budget_article = fields.Char(string='ბიუჯეტის მუხლი')

    currency_rate = fields.Float(string='Currency Rate', digits=(16, 4), default=1.0)

    # Number fields
    exchange_rate = fields.Float(string='კურსი', digits=(16, 4))
    percentage = fields.Float(string='პირგასამტეხლო %', digits=(5, 2))

    # Float fields
    contract_amount = fields.Float(string='ხელშეკრულების თანხა', digits=(16, 2))
    requested_amount = fields.Float(string='მოთხოვნილი თანხა', digits=(16, 2))
    receipt_delivery_amount = fields.Float(string='მიღება-ჩაბარების თანხა', digits=(16, 2))
    paid_amount = fields.Float(string='გადახდილი თანხა', digits=(16, 2))
    penalty_amount = fields.Float(string='ჯარიმის თანხა', digits=(16, 2))
    remaining_amount = fields.Float(string='დარჩენილი თანხა', digits=(16, 2))

    # Selection fields
    delivery_type = fields.Selection([
        ('მოკლევადიანი', 'მოკლევადიანი'),
        ('გრძელვადიანი', 'გრძელვადიანი'),
    ], string='მოწოდების ტიპი')

    vat_included = fields.Selection([
        ('კი', 'კი'),
        ('არა', 'არა'),
    ], string='დღგს ჩათვლით?')

    currency_type = fields.Selection([
        ('GEL', 'GEL'),
        ('USD', 'USD'),
        ('EUR', 'EUR'),
    ], string='ვალუტა')

    contract_status = fields.Selection([
        ('მიმდინარე', 'მიმდინარე'),
        ('გაუქმებული', 'გაუქმებული'),
        ('შესრულებული', 'შესრულებული'),
        ('შეუსრულებელი', 'შეუსრულებელი'),
        ('მიმდინარე ხელშეკრულება საგარანტიო პერიოდი', 'მიმდინარე ხელშეკრულება საგარანტიო პერიოდი'),
    ], string='ხელშეკრულების სტატუსი')

    @api.onchange('contract_registration_date', 'currency_type')
    def _onchange_currency_rate(self):
        """Fetch currency rate from NBG API when contract_registration_date or currency_type changes"""
        if self.contract_registration_date and self.currency_type:
            # If currency is GEL, rate is always 1.0
            if self.currency_type == 'GEL':
                self.currency_rate = 1.0
                return

            # Fetch rate from API for USD or EUR
            self._fetch_currency_rate_from_api()

    def _fetch_currency_rate_from_api(self):
        """Fetch currency rate from National Bank of Georgia API"""
        if not self.contract_registration_date or not self.currency_type:
            return

        # Format date as YYYY-MM-DD
        date_str = self.contract_registration_date.strftime('%Y-%m-%d')
        api_url = f'https://nbg.gov.ge/gw/api/ct/monetarypolicy/currencies/en/json/?date={date_str}'

        try:
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            data = response.json()

            # The response is a list, get the first element
            if not data or not isinstance(data, list):
                _logger.warning('Invalid API response format for date %s', date_str)
                return

            data = data[0]
            currencies = data.get('currencies', [])

            # Find the matching currency
            for currency_data in currencies:
                if currency_data.get('code') == self.currency_type:
                    rate = currency_data.get('rate')
                    if rate:
                        self.currency_rate = float(rate)
                        _logger.info('Currency rate updated: %s = %s GEL on %s',
                                     self.currency_type, rate, date_str)
                        return

            _logger.warning('Currency %s not found in API response for date %s',
                            self.currency_type, date_str)

        except requests.exceptions.Timeout:
            _logger.error('API request timeout for date %s', date_str)
            raise UserError('Currency rate API request timed out. Please try again.')
        except requests.exceptions.RequestException as e:
            _logger.error('Error fetching currency rate from API: %s', str(e))
            raise UserError(f'Error fetching currency rate: {str(e)}')
        except (ValueError, KeyError) as e:
            _logger.error('Error parsing API response: %s', str(e))
            raise UserError('Error processing currency rate data from API.')

class PurchaseRequisition(models.Model):
    _inherit = 'purchase.requisition.line'

    contract_number = fields.Char(
        related='requisition_id.contract_number',
        string='ხელშეკრულების N',
        readonly=True,
        store=True
    )

    purchase_plan_id = fields.Many2one('purchase.plan', string='Purchase Plan')
    purchase_plan_line_id = fields.Many2one(
        'purchase.plan.line',
        string='Purchase Plan Line',
        domain="[('plan_id', '=', purchase_plan_id)]"
    )
    budget_analytic_id = fields.Many2one('budget.analytic', string='Budget',
                                         domain="[('date_to', '>=', context_today().strftime('%Y-%m-%d'))]")

    line_total = fields.Float(compute='_compute_line_total', store=True)
    available_budget_line_ids = fields.Many2many(
        'budget.line',
        compute='_compute_available_budget_lines',
        store=True
    )
    budget_line_id = fields.Many2one(
        'budget.line',
        string='Budget Line',
        domain="[('id', 'in', available_budget_line_ids)]"
    )

    total_amount = fields.Float(
        string='სულ თანხა',
        digits=(16, 2),
        tracking=True
    )

    supplied_amount = fields.Float(
        string='მოწოდებული თანხა',
        digits=(16, 2),
        tracking=True
    )

    remaining_quantity = fields.Float(
        string='დარჩენილი რაოდენობა',
        digits=(16, 2),
        tracking=True
    )

    remaining_amount = fields.Float(
        string='დარჩენილი თანხა',
        digits=(16, 2),
        tracking=True
    )

    currency = fields.Selection([
        ('GEL', 'GEL'),
        ('USD', 'USD'),
        ('EUR', 'EUR'),
    ], string='Currency', related='requisition_id.currency_type', store=True, readonly=True)

    value_in_currency = fields.Float(
        string='Value in Currency',
        digits=(16, 2),
        compute='_compute_value_in_currency',
        store=True
    )

    selected_plan_name = fields.Char(string='Selected Plan Name', compute='_compute_selected_plan_name', store=True)

    @api.depends('total_amount', 'requisition_id.currency_rate', 'currency')
    def _compute_value_in_currency(self):
        for record in self:
            # If currency is GEL, value_in_currency should be 0
            if record.currency == 'GEL':
                record.value_in_currency = 0.0
            elif record.total_amount and record.requisition_id.currency_rate:
                record.value_in_currency = record.total_amount * record.requisition_id.currency_rate
            else:
                record.value_in_currency = 0.0

    @api.depends('budget_line_id')
    def _compute_selected_plan_name(self):
        for record in self:
            plan_name = ''
            budget_line = record.budget_line_id

            if budget_line:
                # First check if account_id exists and use its value
                if hasattr(budget_line, 'account_id') and budget_line.account_id and hasattr(budget_line.account_id,
                                                                                             'code'):
                    code = budget_line.account_id.code or ''
                    name = budget_line.account_id.name if hasattr(budget_line.account_id, 'name') else ''
                    plan_name = f"{code} {name}".strip()
                else:
                    # Then check for x_plan fields if account_id isn't available
                    for field_name in budget_line._fields:
                        if field_name.startswith('x_plan'):
                            plan = getattr(budget_line, field_name, False)
                            if plan and hasattr(plan, 'code'):
                                code = plan.code or ''
                                name = plan.name if hasattr(plan, 'name') else ''
                                plan_name = f"{code} {name}".strip()
                                break

            record.selected_plan_name = plan_name

    @api.depends('purchase_plan_line_id', 'purchase_plan_line_id.budget_cpv_id',
                 'purchase_plan_line_id.budget_cpv_id.line_ids')
    def _compute_available_budget_lines(self):
        for record in self:
            if record.purchase_plan_line_id and record.purchase_plan_line_id.budget_cpv_id:
                budget_lines = self.env['budget.cpv.line'].search([
                    ('budget_cpv_id', '=', record.purchase_plan_line_id.budget_cpv_id.id)
                ])
                record.available_budget_line_ids = budget_lines.mapped('budget_line_id').ids
            else:
                record.available_budget_line_ids = [(5, 0, 0)]

    @api.depends('product_qty', 'price_unit')
    def _compute_line_total(self):
        for line in self:
            line.line_total = line.product_qty * line.price_unit
            # Trigger update when line_total changes
            if line.id and not self.env.context.get('skip_amount_update'):
                line.with_context(skip_amount_update=True)._trigger_amount_updates()

    def _trigger_amount_updates(self):
        """Trigger updates to budget and plan amounts when line_total changes"""
        for line in self:
            if line.budget_line_id:
                line._force_update_budget_amounts()
            if line.purchase_plan_line_id:
                line._force_update_plan_amounts()

    def _force_update_budget_amounts(self):
        """Force update of budget amounts"""
        for line in self:
            if line.budget_line_id:
                # Calculate total contracted amount for this budget line
                total_contracted = sum(self.search([
                    ('budget_line_id', '=', line.budget_line_id.id),
                    ('id', '!=', line.id)
                ]).mapped('line_total'))

                # Add current line's amount if it exists
                if line.line_total:
                    total_contracted += line.line_total

                # Force update the budget line
                self.env.cr.execute("""
                    UPDATE budget_line 
                    SET cont_am = %s,
                        co_re_am = budget_amount - %s
                    WHERE id = %s
                """, (total_contracted, total_contracted, line.budget_line_id.id))

    def _force_update_plan_amounts(self):
        """Force update of purchase plan amounts"""
        for line in self:
            if line.purchase_plan_line_id:
                # Calculate total contracted amount for this plan line
                total_contracted = sum(self.search([
                    ('purchase_plan_line_id', '=', line.purchase_plan_line_id.id),
                    ('id', '!=', line.id)
                ]).mapped('line_total'))

                # Add current line's amount if it exists
                if line.line_total:
                    total_contracted += line.line_total

                # Force update the plan line
                tender_amount = getattr(line.purchase_plan_line_id, 'tender_amount', 0.0) or 0.0
                self.env.cr.execute("""
                    UPDATE purchase_plan_line
                    SET pcon_am = %s,
                        pc_re_am = pu_ac_am - %s - %s
                    WHERE id = %s
                """, (total_contracted, total_contracted, tender_amount, line.purchase_plan_line_id.id))

    @api.model
    def create(self, vals):
        res = super(PurchaseRequisition, self).create(vals)
        res._force_update_budget_amounts()
        res._force_update_plan_amounts()
        return res

    def write(self, vals):
        # Store old records for recomputation
        old_budget_lines = self.mapped('budget_line_id')
        old_plan_lines = self.mapped('purchase_plan_line_id')

        res = super(PurchaseRequisition, self).write(vals)

        if any(field in vals for field in ['product_qty', 'price_unit', 'total_amount', 'purchase_plan_line_id', 'budget_line_id']):
            # Update current records
            self._force_update_budget_amounts()
            self._force_update_plan_amounts()

            # Update old records if relationships changed
            if 'budget_line_id' in vals:
                for old_line in old_budget_lines:
                    if old_line:
                        self.env.cr.execute("""
                            UPDATE budget_line 
                            SET cont_am = COALESCE((
                                SELECT SUM(line_total)
                                FROM purchase_requisition_line
                                WHERE budget_line_id = %s
                            ), 0)
                            WHERE id = %s
                        """, (old_line.id, old_line.id))

                        # Update co_re_am
                        self.env.cr.execute("""
                            UPDATE budget_line 
                            SET co_re_am = budget_amount - cont_am
                            WHERE id = %s
                        """, (old_line.id,))

            if 'purchase_plan_line_id' in vals:
                for old_line in old_plan_lines:
                    if old_line:
                        self.env.cr.execute("""
                            UPDATE purchase_plan_line 
                            SET pcon_am = COALESCE((
                                SELECT SUM(line_total)
                                FROM purchase_requisition_line
                                WHERE purchase_plan_line_id = %s
                            ), 0)
                            WHERE id = %s
                        """, (old_line.id, old_line.id))

                        # Update pc_re_am
                        tender_amount = getattr(old_line, 'tender_amount', 0.0) or 0.0
                        self.env.cr.execute("""
                            UPDATE purchase_plan_line
                            SET pc_re_am = pu_ac_am - pcon_am - %s
                            WHERE id = %s
                        """, (tender_amount, old_line.id))

        return res

    def unlink(self):
        # Store references before deletion
        budget_lines = self.mapped('budget_line_id')
        plan_lines = self.mapped('purchase_plan_line_id')

        res = super(PurchaseRequisition, self).unlink()

        # Force update all affected budget lines
        for budget_line in budget_lines:
            if budget_line:
                self.env.cr.execute("""
                    UPDATE budget_line 
                    SET cont_am = COALESCE((
                        SELECT SUM(line_total)
                        FROM purchase_requisition_line
                        WHERE budget_line_id = %s
                    ), 0)
                    WHERE id = %s
                """, (budget_line.id, budget_line.id))

                # Update co_re_am
                self.env.cr.execute("""
                    UPDATE budget_line 
                    SET co_re_am = budget_amount - cont_am
                    WHERE id = %s
                """, (budget_line.id,))

        # Force update all affected plan lines
        for plan_line in plan_lines:
            if plan_line:
                self.env.cr.execute("""
                    UPDATE purchase_plan_line 
                    SET pcon_am = COALESCE((
                        SELECT SUM(line_total)
                        FROM purchase_requisition_line
                        WHERE purchase_plan_line_id = %s
                    ), 0)
                    WHERE id = %s
                """, (plan_line.id, plan_line.id))

                # Update pc_re_am
                tender_amount = getattr(plan_line, 'tender_amount', 0.0) or 0.0
                self.env.cr.execute("""
                    UPDATE purchase_plan_line
                    SET pc_re_am = pu_ac_am - pcon_am - %s
                    WHERE id = %s
                """, (tender_amount, plan_line.id))

        return res


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    line_ids = fields.One2many(
        'account.payment.line',
        'payment_id',
        string='Payment Lines'
    )
    budget_analytic_id = fields.Many2one(
        'budget.analytic',
        string='Budget',
        domain="[('date_to', '>=', context_today().strftime('%Y-%m-%d'))]"
    )
    budget_line_ids = fields.Many2many(
        'budget.line',
        'account_payment_budget_line_rel',
        'payment_id',
        'budget_line_id',
        string='Budget Lines'
    )
    purchase_plan_line_ids = fields.One2many(
        'account.payment.purchase.plan.line',
        'payment_id',
        string='Purchase Plan Lines'
    )
    remaining_budget_amount = fields.Monetary(
        string='Remaining Budget Amount',
        compute='_compute_remaining_amounts',
        store=True
    )
    remaining_purchase_amount = fields.Monetary(
        string='Remaining Purchase Amount',
        compute='_compute_remaining_amounts',
        store=True
    )

    @api.depends('amount', 'line_ids.amount', 'purchase_plan_line_ids.amount')
    def _compute_remaining_amounts(self):
        for payment in self:
            budget_used = sum(payment.line_ids.mapped('amount'))
            purchase_used = sum(payment.purchase_plan_line_ids.mapped('amount'))
            payment.remaining_budget_amount = payment.amount - budget_used
            payment.remaining_purchase_amount = payment.amount - purchase_used


class AccountPaymentLine(models.Model):
    _name = 'account.payment.line'
    _description = 'Account Payment Line'

    payment_id = fields.Many2one(
        'account.payment',
        string='Payment',
        required=True,
        ondelete='cascade'
    )
    budget_analytic_id = fields.Many2one(
        'budget.analytic',
        string='Budget',
        domain="[('date_to', '>=', context_today().strftime('%Y-%m-%d'))]"
    )
    budget_line_id = fields.Many2one(
        'budget.line',
        string='Budget Line'
    )
    amount = fields.Float(string="თანხა")
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency'
    )

    paim_am = fields.Monetary(
        string='Paid Amount',
        compute='_compute_paim_am',
        store=True,
        currency_field='currency_id'
    )

    @api.depends('amount', 'budget_line_id')
    def _compute_paim_am(self):
        for record in self:
            record.paim_am = record.amount if record.budget_line_id else 0

    @api.constrains('budget_line_id', 'amount')
    def _check_budget_line_amount(self):
        for line in self:
            if line.budget_line_id and line.amount:
                # Get all payment lines for this budget line except current one
                other_lines = self.search([
                    ('budget_line_id', '=', line.budget_line_id.id),
                    ('id', '!=', line.id)
                ])
                total_amount = sum(other_lines.mapped('amount')) + line.amount

                if total_amount > line.budget_line_id.budget_amount:
                    raise ValidationError("Total amount exceeds the budget amount.")

    def _update_budget_line_amounts(self):
        # Group updates by budget line for efficiency
        budget_lines_to_update = {}

        for line in self:
            if line.budget_line_id:
                if line.budget_line_id.id not in budget_lines_to_update:
                    all_payment_lines = self.search([
                        ('budget_line_id', '=', line.budget_line_id.id)
                    ])
                    total_paid = sum(all_payment_lines.mapped('amount'))
                    budget_lines_to_update[line.budget_line_id.id] = {
                        'line': line.budget_line_id,
                        'total_paid': total_paid
                    }

        # Update all budget lines at once
        for data in budget_lines_to_update.values():
            budget_line = data['line']
            total_paid = data['total_paid']

            try:
                budget_line.write({
                    'paim_am': total_paid,
                    'pa_re_am': budget_line.budget_amount - total_paid
                })
            except Exception as e:
                _logger.error(f"Error updating budget line amounts: {str(e)}")

    @api.model
    def create(self, vals):
        res = super(AccountPaymentLine, self).create(vals)
        res._update_budget_line_amounts()
        return res

    def write(self, vals):
        old_budget_lines = self.mapped('budget_line_id')
        res = super(AccountPaymentLine, self).write(vals)

        if 'amount' in vals or 'budget_line_id' in vals:
            self._update_budget_line_amounts()
            # Update old budget lines if budget_line_id changed
            if 'budget_line_id' in vals:
                for old_budget_line in old_budget_lines:
                    all_payment_lines = self.search([
                        ('budget_line_id', '=', old_budget_line.id)
                    ])
                    total_paid = sum(all_payment_lines.mapped('amount'))
                    try:
                        old_budget_line.write({
                            'paim_am': total_paid,
                            'pa_re_am': old_budget_line.budget_amount - total_paid
                        })
                    except Exception as e:
                        _logger.error(f"Error updating old budget line: {str(e)}")
        return res

    def unlink(self):
        budget_lines = self.mapped('budget_line_id')
        res = super(AccountPaymentLine, self).unlink()

        for budget_line in budget_lines:
            if budget_line.exists():
                remaining_lines = self.search([
                    ('budget_line_id', '=', budget_line.id)
                ])
                total_paid = sum(remaining_lines.mapped('amount'))
                try:
                    budget_line.write({
                        'paim_am': total_paid,
                        'pa_re_am': budget_line.budget_amount - total_paid
                    })
                except Exception as e:
                    _logger.error(f"Error updating budget line during unlink: {str(e)}")
        return res

    @api.constrains('amount')
    def _check_amount(self):
        for line in self:
            if line.amount > line.payment_id.remaining_budget_amount + line.amount:
                raise ValidationError("Amount exceeds the remaining budget amount for this payment.")


class AccountPaymentPurchasePlanLine(models.Model):
    _name = 'account.payment.purchase.plan.line'
    _description = 'Account Payment Purchase Plan Line'

    payment_id = fields.Many2one(
        'account.payment',
        string='Payment',
        required=True,
        ondelete='cascade'
    )
    purchase_plan_id = fields.Many2one(
        'purchase.plan',
        string='Purchase Plan',
        required=True
    )
    purchase_plan_line_id = fields.Many2one(
        'purchase.plan.line',
        string='Purchase Plan Line',
        required=True,
        domain="[('plan_id', '=', purchase_plan_id)]"
    )
    cpv_id = fields.Many2one(
        related='purchase_plan_line_id.cpv_id',
        readonly=True
    )
    cpv_name = fields.Char(
        related='purchase_plan_line_id.cpv_name',
        readonly=True
    )
    pu_ac_am = fields.Monetary(
        related='purchase_plan_line_id.pu_ac_am',
        readonly=True,
        currency_field='currency_id'
    )
    pcon_am = fields.Monetary(
        related='purchase_plan_line_id.pcon_am',
        readonly=True,
        currency_field='currency_id'
    )
    pa_re_am = fields.Monetary(
        related='purchase_plan_line_id.pa_re_am',
        readonly=True,
        currency_field='currency_id'
    )
    currency_id = fields.Many2one(
        related='purchase_plan_line_id.currency_id',
        readonly=True
    )
    amount = fields.Float(string="თანხა")

    @api.constrains('purchase_plan_line_id', 'amount')
    def _check_purchase_plan_line_amount(self):
        for line in self:
            if line.purchase_plan_line_id and line.amount:
                other_lines = self.search([
                    ('purchase_plan_line_id', '=', line.purchase_plan_line_id.id),
                    ('id', '!=', line.id)
                ])
                total_amount = sum(other_lines.mapped('amount')) + line.amount

                if total_amount > line.purchase_plan_line_id.pu_ac_am:
                    raise ValidationError("Total amount exceeds the purchase plan line amount.")

    def _update_purchase_plan_line_amounts(self):
        # Group updates by purchase plan line for efficiency
        plan_lines_to_update = {}

        for line in self:
            if line.purchase_plan_line_id:
                if line.purchase_plan_line_id.id not in plan_lines_to_update:
                    all_payment_lines = self.search([
                        ('purchase_plan_line_id', '=', line.purchase_plan_line_id.id)
                    ])
                    total_paid = sum(all_payment_lines.mapped('amount'))
                    plan_lines_to_update[line.purchase_plan_line_id.id] = {
                        'line': line.purchase_plan_line_id,
                        'total_paid': total_paid
                    }

        # Update all purchase plan lines at once
        for data in plan_lines_to_update.values():
            plan_line = data['line']
            total_paid = data['total_paid']

            try:
                plan_line.write({
                    'paim_am': total_paid,
                    'pa_re_am': plan_line.pu_ac_am - total_paid
                })
            except Exception as e:
                _logger.error(f"Error updating purchase plan line amounts: {str(e)}")

    @api.model
    def create(self, vals):
        res = super(AccountPaymentPurchasePlanLine, self).create(vals)
        res._update_purchase_plan_line_amounts()
        return res

    def write(self, vals):
        old_plan_lines = self.mapped('purchase_plan_line_id')
        res = super(AccountPaymentPurchasePlanLine, self).write(vals)

        if 'amount' in vals or 'purchase_plan_line_id' in vals:
            self._update_purchase_plan_line_amounts()
            # Update old plan lines if purchase_plan_line_id changed
            if 'purchase_plan_line_id' in vals:
                for old_plan_line in old_plan_lines:
                    all_payment_lines = self.search([
                        ('purchase_plan_line_id', '=', old_plan_line.id)
                    ])
                    total_paid = sum(all_payment_lines.mapped('amount'))
                    try:
                        old_plan_line.write({
                            'paim_am': total_paid,
                            'pa_re_am': old_plan_line.pu_ac_am - total_paid
                        })
                    except Exception as e:
                        _logger.error(f"Error updating old purchase plan line: {str(e)}")
        return res

    def unlink(self):
        plan_lines = self.mapped('purchase_plan_line_id')
        res = super(AccountPaymentPurchasePlanLine, self).unlink()

        for plan_line in plan_lines:
            if plan_line.exists():
                remaining_lines = self.search([
                    ('purchase_plan_line_id', '=', plan_line.id)
                ])
                total_paid = sum(remaining_lines.mapped('amount'))
                try:
                    plan_line.write({
                        'paim_am': total_paid,
                        'pa_re_am': plan_line.pu_ac_am - total_paid
                    })
                except Exception as e:
                    _logger.error(f"Error updating purchase plan line during unlink: {str(e)}")
        return res

    @api.constrains('amount')
    def _check_amount(self):
        for line in self:
            if line.amount > line.payment_id.remaining_purchase_amount + line.amount:
                raise ValidationError("Amount exceeds the remaining purchase plan amount for this payment.")


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    budget_analytic_id = fields.Many2one(
        'budget.analytic',
        string='Budget',
        domain="[('state', '=', 'confirmed')]"
    )
    budget_line_id = fields.Many2one(
        'budget.line',
        string='Budget Line',
        domain="[('budget_analytic_id', '=', budget_analytic_id), ('budget_analytic_id.state', '=', 'confirmed')]"
    )
    paim_am = fields.Monetary(
        string='Paid Amount',
        currency_field='currency_id'
    )
    amount = fields.Float(string="amount")
