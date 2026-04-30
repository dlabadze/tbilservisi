from odoo import api, fields, models
from odoo.exceptions import UserError


class AssetSplit(models.Model):
    _name = "asset.split"
    _description = "Asset Split"

    name = fields.Char(string="Reference", required=True, default="New", readonly=True)
    asset_id = fields.Many2one('account.asset', string="Asset", required=True)
    raod = fields.Float(string="Raod", readonly=True, compute='_compute_raod', store=True)
    raod_new = fields.Float(string="Raod New", required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed')
    ], string='Status', default='draft', required=True, tracking=True)
    
    # ინფორმაციული ველები
    original_value_current = fields.Float(string="Current Original Value", readonly=True, compute='_compute_current_values', store=True)
    already_depreciated_current = fields.Float(string="Current Depreciated Amount", readonly=True, compute='_compute_current_values', store=True)
    
    # გამოთვლილი ახალი მნიშვნელობები
    new_asset_original_value = fields.Float(string="New Asset Original Value", readonly=True, compute='_compute_split_values', store=True)
    new_asset_depreciated = fields.Float(string="New Asset Depreciated", readonly=True, compute='_compute_split_values', store=True)
    old_asset_original_value = fields.Float(string="Old Asset Original Value", readonly=True, compute='_compute_split_values', store=True)
    old_asset_depreciated = fields.Float(string="Old Asset Depreciated", readonly=True, compute='_compute_split_values', store=True)
    
    new_asset_id = fields.Many2one('account.asset', string="Created Asset", readonly=True)

    @api.depends('asset_id')
    def _compute_raod(self):
        for record in self:
            if record.asset_id:
                record.raod = record.asset_id.x_studio_ or 0.0
            else:
                record.raod = 0.0

    @api.depends('asset_id')
    def _compute_current_values(self):
        for record in self:
            if record.asset_id:
                record.original_value_current = record.asset_id.original_value_new or 0.0
                record.already_depreciated_current = record.asset_id.already_depreciated_amount_import_new or 0.0
            else:
                record.original_value_current = 0.0
                record.already_depreciated_current = 0.0

    @api.depends('asset_id', 'raod', 'raod_new')
    def _compute_split_values(self):
        for record in self:
            if record.asset_id and record.raod > 0:
                # ახალი asset-ისთვის
                record.new_asset_original_value = (record.original_value_current / record.raod) * record.raod_new
                record.new_asset_depreciated = (record.already_depreciated_current / record.raod) * record.raod_new
                
                # ძველი asset-ისთვის
                record.old_asset_original_value = (record.original_value_current / record.raod) * (record.raod - record.raod_new)
                record.old_asset_depreciated = (record.already_depreciated_current / record.raod) * (record.raod - record.raod_new)
            else:
                record.new_asset_original_value = 0.0
                record.new_asset_depreciated = 0.0
                record.old_asset_original_value = 0.0
                record.old_asset_depreciated = 0.0

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('asset.split') or 'New'
        return super(AssetSplit, self).create(vals)

    def action_confirm(self):
        """დაადასტურე და დაყავი აქტივი"""
        self.ensure_one()
        
        if not self.asset_id:
            raise UserError("გთხოვთ აირჩიოთ ძირითადი საშუალება!")
        
        if self.raod <= 0:
            raise UserError("Raod უნდა იყოს 0-ზე მეტი!")
        
        if self.raod_new <= 0 or self.raod_new >= self.raod:
            raise UserError("Raod New უნდა იყოს 0-ზე მეტი და Raod-ზე ნაკლები!")
        
        # გამოთვლილი original_value-ები
        new_original_value = (self.asset_id.original_value / self.raod) * self.raod_new if self.asset_id.original_value else 0.0
        old_original_value = (self.asset_id.original_value / self.raod) * (self.raod - self.raod_new) if self.asset_id.original_value else 0.0
        
        # ახალი asset-ის შექმნა (კოპირება copy() მეთოდით)
        new_asset = self.asset_id.copy(default={
            'name': f"{self.asset_id.name} - Split",
            'original_value': new_original_value,
            'original_value_new': self.new_asset_original_value,
            'already_depreciated_amount_import_new': self.new_asset_depreciated,
            'x_studio_': self.raod_new,
        })
        
        # ძველი asset-ის განახლება
        self.asset_id.write({
            'original_value': old_original_value,
            'original_value_new': self.old_asset_original_value,
            'already_depreciated_amount_import_new': self.old_asset_depreciated,
            'x_studio_': self.raod - self.raod_new,
        })
        
        # სტატუსის განახლება
        self.write({
            'state': 'confirmed',
            'new_asset_id': new_asset.id
        })
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Created Asset',
            'res_model': 'account.asset',
            'res_id': new_asset.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_draft(self):
        """დაბრუნება Draft-ში"""
        self.write({'state': 'draft'})

