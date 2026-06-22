from lxml import etree

from odoo import api, models


class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

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

        appointment_category = self.env['approval.category'].sudo().search([
            ('name', '=', 'დანიშვნა')
        ], limit=1)
        temporary_category = self.env['approval.category'].sudo().search([
            ('name', 'in', ['დანიშვნა დროებით', 'დანიშვნა დროებითი'])
        ], limit=1)

        if not appointment_category or not temporary_category:
            return res

        try:
            doc = etree.fromstring(res['arch'])
        except Exception:
            return res

        changed = False
        for button in doc.xpath("//button[@type='action']"):
            button_name = (button.get('name') or '').strip()
            label = (button.get('string') or '').strip()

            is_temporary = (
                button_name == '1403'
                or 'დროებით' in label
                or 'დროებითი' in label
            )
            is_appointment = (
                button_name == '1194'
                or ('დანიშვნა' in label and not is_temporary)
            )

            if is_appointment:
                new_expr = f"category_id != {appointment_category.id}"
                if button.get('invisible') != new_expr:
                    button.set('invisible', new_expr)
                    changed = True

            if is_temporary:
                new_expr = f"category_id != {temporary_category.id}"
                if button.get('invisible') != new_expr:
                    button.set('invisible', new_expr)
                    changed = True

        if changed:
            res['arch'] = etree.tostring(doc, encoding='unicode')

        return res
