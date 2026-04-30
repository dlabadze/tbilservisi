from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class RepairOrder(models.Model):
    _inherit = 'repair.order'

    has_attachment = fields.Boolean(string='Has Attachment', compute='_compute_has_attachment')

    def _compute_has_attachment(self):
        for rec in self:
            attachments = self.env['ir.attachment'].search([
                ('res_model', '=', 'repair.order'),
                ('res_id', '=', rec.id)
            ])
            tags = self.env["repair.tags"].search([
                ('name', '=', 'ნაწილები')
            ], limit=1)
            if tags:
                if tags.id in rec.tag_ids.ids and not attachments:
                    rec.has_attachment = False
                else:
                    rec.has_attachment = True
            else:
                rec.has_attachment = True
    
    def action_validate(self):
        for rec in self:
            if not rec.has_attachment:
                raise ValidationError(_("ფაილი არ არის მიბმული ჩანაწერზე"))
        
        return super(RepairOrder, self).action_validate()

