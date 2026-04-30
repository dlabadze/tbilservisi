from odoo import models, fields, api

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    combined_invoice_id = fields.Many2one('combined.invoice.model', string='Combined Invoice Model')
    invoice_number = fields.Char(related='combined_invoice_id.invoice_number', string='ზედნადების ნომერი')
    invoice_id = fields.Char(related='combined_invoice_id.invoice_id', string='ზედნადების ID')
    factura_num = fields.Char(related='combined_invoice_id.factura_num', string='ფაქტურის id')
    get_invoice_id = fields.Char(related='combined_invoice_id.get_invoice_id', string='ფაქტურის ნომერი')
    start_location = fields.Char('ტრანსპორტირების დაწყების ადგილი')
    end_location = fields.Char('ტრანსპორტირების დასრულების ადგილი')
    editable_end_location = fields.Char('ტრანსპორტირების დასრულების ადგილი')
    
    delivery = fields.Selection([
        ('2', 'მიწოდება ტრანსპორტირებით'),
        ('3', 'ტრანსპორტირების გარეშე'),
    ], 'მიწოდების სახე', default='2')
    
    trans_id = fields.Selection([
        ('1', 'საავტომობილო'),
        ('2', 'სარკინიგზო'),
        ('3', 'საავიაციო'),
        ('4', 'სხვა'),
        ('6', 'საავტომობილო - უცხო ქვეყნის'),
        ('7', 'გადამზიდავი'),
        ('8', 'მოპედი/მოტოციკლი'),
    ], string='ტრანსპორტირების სახე', default='1')

    trans_txt = fields.Char('ტრანსპორტირების ტექსტი')
    buyer_type = fields.Selection([
        ('1', 'საქართველოს მოქალაქე'),
        ('0', 'უცხოეთის მოქალაქე'),
    ], string='მყიდველი', default='1')

    driver_type = fields.Selection([
        ('1', 'საქართველოს მოქალაქე'),
        ('0', 'უცხოეთის მოქალაქე'),
    ], string='მძღოლის ტიპი', default='1')
    
    car_number = fields.Char('მანქანის ნომერი')
    driver_id = fields.Char('მძღოლის პირადი ნომერი')
    driver_name = fields.Char('მძღოლის სახელი')
    transport_cost = fields.Float('ტრანსპორტირების ღირებულება')
    transport_cost_payer = fields.Selection([
        ('1', 'მყიდველი'),
        ('2', 'გამყიდველი'),
    ], string='ტრანსპორტირების ღირებულების გადამხდელი', default='1')
    
    comment = fields.Text('კომენტარი')
    begin_date = fields.Datetime(string='დაწყების დრო', default=fields.Datetime.now)
    
    status = fields.Char('Status')
    error_field = fields.Char('error_field')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse')
    warehouse_address = fields.Char(related='warehouse_id.partner_id.name', string='Warehouse Address', readonly=True)
    formatted_begin_date = fields.Char(compute='_compute_formatted_begin_date', string='Formatted Begin Date')
    show_all_fields = fields.Boolean(string='რს-ის ველები')
    is_start_location_required = fields.Boolean(string="Is Start Location Required", compute="_compute_is_start_location_required")
    is_editable_end_location_required = fields.Boolean(string="Is Editable End Location Required", compute="_compute_is_editable_end_location_required")
    is_trans_id_4 = fields.Boolean(compute='_compute_is_trans_id_4')
    rs_acc = fields.Char(compute='_compute_rs_acc', string='rs.ge ექაუნთი', readonly=True)
    rs_pass = fields.Char(compute='_compute_rs_pass', string='rs.ge პაროლი', readonly=True)
    partner_vat = fields.Char(related='partner_id.vat', string='Customer VAT', readonly=True, store=True)
    completed_soap = fields.Char(string='გაგზავნილია')
    is_soap_completed = fields.Boolean(compute='_compute_is_soap_completed')

    @api.depends('begin_date')
    def _compute_formatted_begin_date(self):
        for record in self:
            if record.begin_date:
                begin_date_datetime = fields.Datetime.from_string(record.begin_date)
                record.formatted_begin_date = begin_date_datetime.strftime("%Y-%m-%dT%H:%M:%S")
            else:
                record.formatted_begin_date = False

    @api.depends('delivery')
    def _compute_is_start_location_required(self):
        for record in self:
            record.is_start_location_required = record.delivery == '2'

    @api.depends('delivery')
    def _compute_is_editable_end_location_required(self):
        for record in self:
            record.is_editable_end_location_required = record.delivery == '2'

    @api.depends('trans_id')
    def _compute_is_trans_id_4(self):
        for record in self:
            record.is_trans_id_4 = record.trans_id == '4'

    @api.depends('user_id.rs_acc')
    def _compute_rs_acc(self):
        for record in self:
            user = self.env.user
            record.rs_acc = user.rs_acc

    @api.depends('user_id.rs_pass')
    def _compute_rs_pass(self):
        for record in self:
            user = self.env.user
            record.rs_pass = user.rs_pass

    @api.depends('completed_soap')
    def _compute_is_soap_completed(self):
        for record in self:
            record.is_soap_completed = record.completed_soap == '1'

    has_landed_costs = fields.Boolean(string='Has Landed Costs')
    landed_cost_count = fields.Integer(string='Landed Cost Count', compute='_compute_landed_cost_count')

    def _compute_landed_cost_count(self):
        for record in self:
            record.landed_cost_count = 0 

    def action_view_landed_costs(self):
        pass
