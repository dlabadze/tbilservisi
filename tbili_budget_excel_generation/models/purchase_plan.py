import base64
import io

from odoo import fields, models, _
from odoo.exceptions import UserError


class PurchasePlan(models.Model):
    _inherit = 'purchase.plan'

    def action_generate_excel(self):
        self.ensure_one()

        try:
            import xlsxwriter
        except ImportError:
            raise UserError(_('xlsxwriter ბიბლიოთეკა საჭიროა Excel-ის გენერაციისთვის.'))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('შესყიდვების გეგმა')

        # ── Formats ──────────────────────────────────────────────────────────
        header_fmt = workbook.add_format({
            'bold': True,
            'bg_color': '#4472C4',
            'font_color': '#FFFFFF',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': True,
        })
        cell_fmt = workbook.add_format({
            'border': 1,
            'valign': 'vcenter',
        })
        money_fmt = workbook.add_format({
            'border': 1,
            'valign': 'vcenter',
            'num_format': '#,##0.00',
        })
        num_fmt = workbook.add_format({
            'border': 1,
            'valign': 'vcenter',
            'align': 'center',
        })
        bool_fmt = workbook.add_format({
            'border': 1,
            'valign': 'vcenter',
            'align': 'center',
        })

        # ── Selection-field decode maps ───────────────────────────────────────
        FUNDING_SOURCE = {
            '1': 'სახელმწიფო ბიუჯეტი',
            '2': 'ავტ. რეს. ბიუჯეტი',
            '3': 'ადგილობრივი ბიუჯეტი',
            '4': 'საკუთარი სახსრები',
            '5': 'გრანტი/კრედიტი',
        }
        VADEBI = {
            '1': 'ერთწლიანი',
            '2': 'ორწლიანი',
            '3': 'სამწლიანი',
            '4': 'ოთხწლიანი',
        }
        PRICEKURANT = {'1': 'კი', '2': 'არა'}
        PLAN_TYPE = {'1': 'ერთწლიანი', '2': 'მრავალწლიანი'}

        # ── Column definitions: (label, width, fmt) ───────────────────────────
        # Order mirrors the list view exactly.
        COLUMNS = [
            ('N',                               5,  num_fmt),
            ('CPV კოდი',                        14, cell_fmt),
            ('CPV დასახელება',                  35, cell_fmt),
            ('ბიუჯეტის CPV',                    16, cell_fmt),
            ('ცვლილებები',                      16, cell_fmt),
            ('დაფინანსების წყარო',              22, cell_fmt),
            ('შესყიდვის საშუალება',             22, cell_fmt),
            ('შესყიდვის საფუძველი',             22, cell_fmt),
            ('შესყიდვის ვადები',                16, cell_fmt),
            ('Quarter Tags',               22, cell_fmt),
            ('შესყიდვის ტიპი',             18, cell_fmt),   # purchase_plan_type
            ('Code',                  14, cell_fmt),
            ('პრეისკურანტი',                   14, cell_fmt),
            ('პრეისკურანტით?',                 16, bool_fmt),   # with_preiskuranti
            ('პირვანდელი ღირებულება',           20, money_fmt),
            ('ცვლილებების ჯამი',                18, money_fmt),
            ('მიმდინარე ღირებულება',            20, money_fmt),
            ('სხვაობა',                         14, money_fmt),
            ('ტენდერის თანხა',                  18, money_fmt),  # tender_amount
            ('ხელშეკრულების თანხა',             20, money_fmt),
            ('დარჩ. რეს. ხელშეკრულებით',        22, money_fmt),
            ('გადახდილი თანხა',                 18, money_fmt),
            ('დარჩენილი რესურსი',               18, money_fmt),
            ('ვალუტა',                          10, cell_fmt),
            ('Budget Lines Allocated',             20, money_fmt),
            ('Remaining To Allocate',                  20, money_fmt),
        ]

        # ── Header row ───────────────────────────────────────────────────────
        sheet.set_row(0, 35)
        for col_idx, col_def in enumerate(COLUMNS):
            sheet.write(0, col_idx, col_def[0], header_fmt)
            sheet.set_column(col_idx, col_idx, col_def[1])

        sheet.freeze_panes(1, 0)

        # ── Data rows ────────────────────────────────────────────────────────
        for row_idx, line in enumerate(self.line_ids, start=1):

            # Fields that come from the `tenderi` module — use getattr so the
            # Excel export still works even if tenderi is not installed.
            with_preiskuranti  = getattr(line, 'with_preiskuranti', False)
            tender_amount       = getattr(line, 'tender_amount', 0.0) or 0.0

            plan_type           = getattr(line, 'purchase_plan_type', False)

            values = [
                row_idx,                                                        # N
                line.cpv_id.code if line.cpv_id else '',                        # CPV კოდი
                line.cpv_name or '',                                            # CPV დასახელება
                line.budget_cpv_id.cpv_code if line.budget_cpv_id else '',     # ბიუჯეტის CPV
                line.change_id.cpv_code if line.change_id else '',             # ცვლილებები
                FUNDING_SOURCE.get(line.funding_source or '', ''),             # დაფინანსების წყარო
                line.purchase_method_id.name if line.purchase_method_id else '', # შეს. საშ.
                line.purchase_reason_id.name if line.purchase_reason_id else '', # შეს. საფ.
                VADEBI.get(line.vadebi or '', ''),                             # შეს. ვადები
                ', '.join(line.tag_ids.mapped('name')),                        # კვ. ტეგები
                PLAN_TYPE.get(plan_type or '', ''),                            # შეს. ტიპი
                line.purchase_method_code or '',                               # შეს. საშ. კოდი
                PRICEKURANT.get(line.pricekurant or '', ''),                   # პრეისკურანტი
                'კი' if with_preiskuranti else 'არა',                          # პრეისკურანტით?
                line.pu_st_am or 0.0,                                          # პირვ. ღირ.
                line.total_changes or 0.0,                                     # ცვლ. ჯამი
                line.pu_ac_am or 0.0,                                          # მიმდ. ღირ.
                line.pu_diff or 0.0,                                           # სხვაობა
                tender_amount,                                                  # ტენდ. თანხა
                line.pcon_am or 0.0,                                           # ხელშ. თანხა
                line.pc_re_am or 0.0,                                          # დარჩ. ხელშ.
                line.paim_am or 0.0,                                           # გადახდ. თ.
                line.pa_re_am or 0.0,                                          # დარჩ. რეს.
                line.currency_id.name if line.currency_id else '',             # ვალუტა
                line.budget_lines_allocated or 0.0,                            # გამოყ. ბიუჯ.
                line.remaining_to_allocate or 0.0,                             # დარჩ. გამ.
            ]

            for col_idx, value in enumerate(values):
                sheet.write(row_idx, col_idx, value, COLUMNS[col_idx][2])

        # ── Close & encode ────────────────────────────────────────────────────
        workbook.close()
        output.seek(0)
        excel_data = base64.b64encode(output.read())

        filename = 'purchase_plan_{}_{}.xlsx'.format(
            (self.name or 'export').replace('/', '-'),
            fields.Date.today(),
        )

        attachment = self.env['ir.attachment'].create({
            'name': filename,
            'type': 'binary',
            'datas': excel_data,
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': (
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            ),
        })

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/{}?download=true'.format(attachment.id),
            'target': 'new',
        }
