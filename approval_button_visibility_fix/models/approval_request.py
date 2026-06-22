from lxml import etree

from odoo import api, models


class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    def _get_target_category_ids(self):
        category_model = self.env['approval.category'].sudo()

        temporary = category_model.search([
            ('name', 'in', ['დანიშვნა დროებით', 'დანიშვნა დროებითი'])
        ], limit=1)
        if not temporary:
            temporary = category_model.search([
                '|',
                ('name', 'ilike', 'დროებით'),
                ('name', 'ilike', 'დროებითი'),
            ], limit=1)

        appointment = category_model.search([
            ('name', '=', 'დანიშვნა'),
        ], limit=1)
        if not appointment:
            appointment = category_model.search([
                ('name', 'ilike', 'დანიშვნა'),
                ('id', '!=', temporary.id if temporary else 0),
            ], limit=1)

        return appointment.id if appointment else False, temporary.id if temporary else False

    def _patch_button_visibility_arch(self, arch_text):
        appointment_id, temporary_id = self._get_target_category_ids()
        if not appointment_id or not temporary_id:
            return arch_text

        try:
            doc = etree.fromstring(arch_text)
        except Exception:
            return arch_text

        changed = False
        for button in doc.xpath("//button[@type='action']"):
            button_name = (button.get('name') or '').strip()
            if button_name == '1194':
                new_expr = f"category_id != {appointment_id}"
                if button.get('invisible') != new_expr:
                    button.set('invisible', new_expr)
                    changed = True
                if button.get('string') != 'დანიშვნა':
                    button.set('string', 'დანიშვნა')
                    changed = True
            elif button_name == '1403':
                new_expr = f"category_id != {temporary_id}"
                if button.get('invisible') != new_expr:
                    button.set('invisible', new_expr)
                    changed = True

        if not changed:
            return arch_text

        return etree.tostring(doc, encoding='unicode')

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super().fields_view_get(
            view_id=view_id,
            view_type=view_type,
            toolbar=toolbar,
            submenu=submenu,
        )

        if view_type != 'form' or not res.get('arch'):
            return res

        res['arch'] = self._patch_button_visibility_arch(res['arch'])

        return res

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        res = super().get_view(view_id=view_id, view_type=view_type, **options)
        if view_type != 'form' or not res.get('arch'):
            return res

        res['arch'] = self._patch_button_visibility_arch(res['arch'])

        return res
