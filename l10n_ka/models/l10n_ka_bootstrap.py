import logging

from odoo import SUPERUSER_ID, api, models


_logger = logging.getLogger(__name__)


class L10nKaBootstrap(models.AbstractModel):
    _name = "l10n.ka.bootstrap"
    _description = "Georgian UI bootstrap adjustments"

    def _register_hook(self):
        result = super()._register_hook()
        env = api.Environment(self._cr, SUPERUSER_ID, {})

        # Never block registry load because of a localization patch.
        bootstrap_steps = [
            self._rename_server_actions,
            self._translate_module_names,
            self._translate_app_menu_names,
            self._translate_attendance_field_labels,
            self._translate_attendance_selection_labels,
            self._translate_attendance_menu_names,
            self._translate_attendance_view_strings,
            self._translate_accounting_menu_names,
            self._translate_planned_activities_string,
            self._force_field_labels_and_selections,
            self._translate_existing_onboarding_messages,
        ]
        for step in bootstrap_steps:
            try:
                step(env)
            except Exception:
                _logger.exception("l10n_ka bootstrap step failed: %s", step.__name__)

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
    def _translate_attendance_field_labels(env):
        fields_model = env["ir.model.fields"].sudo()
        field_labels = {
            ("hr.attendance", "employee_id"): "თანამშრომელი",
            ("hr.attendance", "department_id"): "დეპარტამენტი",
            ("hr.attendance", "manager_id"): "მენეჯერი",
            ("hr.attendance", "check_in"): "შემოსვლა",
            ("hr.attendance", "check_out"): "გასვლა",
            ("hr.attendance", "worked_hours"): "ნამუშევარი საათები",
            ("hr.attendance", "overtime_status"): "ზეგანაკვეთური სტატუსი",
            ("hr.attendance", "in_mode"): "შემოსვლის რეჟიმი",
            ("hr.attendance", "out_mode"): "გასვლის რეჟიმი",
            ("hr.attendance", "in_latitude"): "შესვლის განედი",
            ("hr.attendance", "in_longitude"): "შესვლის გრძედი",
            ("hr.attendance", "out_latitude"): "გასვლის განედი",
            ("hr.attendance", "out_longitude"): "გასვლის გრძედი",
            ("hr.attendance", "in_city"): "შესვლის ქალაქი",
            ("hr.attendance", "out_city"): "გასვლის ქალაქი",
            ("hr.attendance", "in_country_name"): "შესვლის ქვეყანა",
            ("hr.attendance", "out_country_name"): "გასვლის ქვეყანა",
            ("hr.attendance", "attendance_status"): "დასწრების სტატუსი",
            ("hr.attendance", "type"): "ტიპი",
            ("hr.attendance", "mode"): "რეჟიმი",
            ("hr.attendance", "x_studio_identification_no"): "საიდენტიფიკაციო კოდი",
            ("hr.attendance", "x_studio_selection_field_99n_1j76jab36"): "ტიპი",
        }

        updated = 0
        for (model_name, field_name), label in field_labels.items():
            field_rec = fields_model.search([
                ("model", "=", model_name),
                ("name", "=", field_name),
            ], limit=1)
            if field_rec and field_rec.field_description != label:
                field_rec.field_description = label
                updated += 1

        if updated:
            _logger.info("l10n_ka: translated %s attendance field labels", updated)

    @staticmethod
    def _translate_attendance_selection_labels(env):
        fields_model = env["ir.model.fields"].sudo()
        selection_model = env["ir.model.fields.selection"].sudo()

        selection_field_names = {
            "state",
            "status",
            "attendance_status",
            "check_in_state",
            "check_out_state",
        }

        selection_map = {
            "approved": "დამტკიცებული",
            "refused": "უარყოფილი",
            "to_approve": "დასამტკიცებელი",
            "draft": "დრაფტი",
            "confirmed": "დადასტურებული",
            "done": "დასრულებული",
        }

        updated = 0
        selection_fields = fields_model.search([
            ("model", "=", "hr.attendance"),
            ("ttype", "=", "selection"),
        ])
        for field_rec in selection_fields:
            if field_rec.name not in selection_field_names:
                continue

            selections = selection_model.search([("field_id", "=", field_rec.id)])
            for selection in selections:
                new_label = selection_map.get(selection.value)
                if new_label and selection.name != new_label:
                    selection.name = new_label
                    updated += 1

        if updated:
            _logger.info("l10n_ka: translated %s attendance selection labels", updated)

    @staticmethod
    def _translate_attendance_menu_names(env):
        menu_name_map = {
            "Overview": "მიმოხილვა",
            "Management": "მართვა",
            "Kiosk Mode": "კიოსკის რეჟიმი",
            "Reporting": "რეპორტინგი",
            "Configuration": "კონფიგურაცია",
            "Attendances Import": "დასწრების იმპორტი",
        }

        root_menu = env.ref("hr_attendance.menu_hr_attendance_root", raise_if_not_found=False)
        if not root_menu:
            return

        menus = env["ir.ui.menu"].sudo().search([("id", "child_of", root_menu.id)])
        updated = 0
        for menu in menus:
            ge_name = menu_name_map.get(menu.name)
            if not ge_name:
                continue
            if menu.with_context(lang="ka_GE").name == ge_name:
                continue
            menu.with_context(lang="ka_GE").write({"name": ge_name})
            updated += 1

        if updated:
            env["ir.ui.menu"].clear_caches()
            _logger.info("l10n_ka: translated %s attendance menu labels", updated)

    @staticmethod
    def _translate_attendance_view_strings(env):
        replace_map = {
            "My Attendances": "ჩემი დასწრება",
            "My Team": "ჩემი გუნდი",
            "At Work": "სამსახურში",
            "Errors": "შეცდომები",
            "Automatically Checked-Out": "ავტომატურად გასული",
            "Active Employees": "აქტიური თანამშრომლები",
            "Archived Employees": "არქივირებული თანამშრომლები",
            "To Approve": "დასამტკიცებელი",
            "Approved": "დამტკიცებული",
            "Refused": "უარყოფილი",
            "Employee": "თანამშრომელი",
            "Department": "დეპარტამენტი",
            "Manager": "მენეჯერი",
            "Method": "მეთოდი",
            "Date": "თარიღი",
            "Identification No": "საიდენტიფიკაციო კოდი",
            "Type": "ტიპი",
            "type": "ტიპი",
        }

        views = env["ir.ui.view"].sudo().search([
            ("model", "in", ["hr.attendance", "hr.employee"]),
            ("type", "in", ["search", "list", "tree"]),
        ])

        updated = 0
        for view in views:
            arch = view.arch_db or ""
            translated = arch
            for old, new in replace_map.items():
                translated = translated.replace(f'string="{old}"', f'string="{new}"')
                translated = translated.replace(f"string='{old}'", f"string='{new}'")
            if translated != arch:
                view.write({"arch_db": translated})
                updated += 1

        if updated:
            env["ir.ui.view"].clear_caches()
            _logger.info("l10n_ka: translated %s attendance views", updated)

    @staticmethod
    def _translate_accounting_menu_names(env):
        menu_name_map = {
            "Purchase Plans": "შესყიდვების გეგმები",
            "CPV Codes": "CPV კოდები",
            "Budget CPV": "ბიუჯეტის CPV",
            "Purchase Plan Changes": "შესყიდვების გეგმის ცვლილებები",
            "Journal Reports": "ჟურნალის რეპორტები",
            "Audit Reports": "აუდიტის რეპორტები",
            "Consolidated Reports": "კონსოლიდირებული რეპორტები",
            "Management": "მენეჯმენტი",
            "Balance Sheet": "ბალანსი",
            "Profit and Loss": "მოგება და ზარალი",
            "Cash Flow Statement": "ფულადი ნაკადების ანგარიში",
            "Executive Summary": "აღმასრულებელი შეჯამება",
            "Tax Return": "საგადასახადო დეკლარაცია",
            "General Ledger": "მთავარი წიგნი",
            "Trial Balance": "საცდელი ბალანსი",
            "Journal Audit": "ჟურნალის აუდიტი",
            "Partner Ledger": "პარტნიორის ბრუნვის რეპორტი",
            "Aged Receivable": "მოთხოვნების ვადაგადაცილება",
            "Aged Payable": "ვალდებულებების ვადაგადაცილება",
            "Unrealized Currency Gains/Losses": "არარეალიზებული საკურსო მოგება/ზარალი",
            "Deferred Expense": "გადავადებული ხარჯი",
            "Deferred Revenue": "გადავადებული შემოსავალი",
            "Depreciation Schedule": "ამორტიზაციის გეგმა",
            "Disallowed Expenses": "არაღიარებული ხარჯები",
            "Loans Analysis": "სესხების ანალიზი",
            "Budget Report": "ბიუჯეტის ანგარიში",
            "Journal Item Report Wizard": "ჟურნალის ჩანაწერების რეპორტი",
            "Partner Currency Movement Report": "პარტნიორის ვალუტური მოძრაობის რეპორტი",
            "Invoicing": "ინვოისინგი",
            "Follow-up Levels": "მიმდევრობის დონეები",
            "Online Synchronization": "ონლაინ სინქრონიზაცია",
            "Tax Units": "საგადასახადო ერთეულები",
            "Horizontal Groups": "ჰორიზონტალური ჯგუფები",
            "Import Country Codes": "ქვეყნის კოდების იმპორტი",
            "Financial Budgets": "ფინანსური ბიუჯეტები",
            "Payment Providers": "გადახდის პროვაიდერები",
            "Payment Methods": "გადახდის მეთოდები",
            "Payment Tokens": "გადახდის ტოკენები",
            "Payment Transactions": "გადახდის ტრანზაქციები",
            "Asset Models": "აქტივების მოდელები",
            "Accounting Reports": "საბუღალტრო რეპორტები",
            "Disallowed Expenses Categories": "არაღიარებული ხარჯების კატეგორიები",
        }

        accounting_root = env.ref("account.menu_finance", raise_if_not_found=False)
        if not accounting_root:
            return

        menus = env["ir.ui.menu"].sudo().search([("id", "child_of", accounting_root.id)])
        updated = 0
        for menu in menus:
            ge_name = menu_name_map.get(menu.name)
            if not ge_name:
                continue
            if menu.with_context(lang="ka_GE").name == ge_name:
                continue
            menu.with_context(lang="ka_GE").write({"name": ge_name})
            updated += 1

        if updated:
            env["ir.ui.menu"].clear_caches()
            _logger.info("l10n_ka: translated %s accounting menu labels", updated)

    @staticmethod
    def _translate_planned_activities_string(env):
        views = env["ir.ui.view"].sudo().search([
            ("arch_db", "ilike", "Planned Activities"),
        ])

        updated = 0
        for view in views:
            arch = view.arch_db or ""
            translated = arch.replace("Planned Activities", "დაგეგმილი აქტივობები")
            if translated != arch:
                view.write({"arch_db": translated})
                updated += 1

        if updated:
            env["ir.ui.view"].clear_caches()
            _logger.info("l10n_ka: translated Planned Activities in %s views", updated)

    @staticmethod
    def _translate_module_names(env):
        module_names = {
            "account": "ბუღალტერია",
            "approvals": "დამტკიცებები",
            "base_import": "მონაცემთა იმპორტი",
            "calendar": "კალენდარი",
            "contacts": "კონტაქტები",
            "documents": "დოკუმენტები",
            "documents_spreadsheet": "დოკუმენტები - ცხრილები",
            "hr_attendance": "დასწრება",
            "hr_contract": "კონტრაქტები",
            "hr_contract_sign": "კონტრაქტის ხელმოწერა",
            "hr_holidays": "შვებულებები",
            "hr_maintenance": "თანამშრომელთა აღჭურვილობა",
            "hr_payroll": "ხელფასები",
            "hr_payroll_holidays": "სახელფასო შვებულებები",
            "hr_recruitment": "რეკრუტმენტი",
            "hr_skills": "უნარები",
            "hr_work_entry": "სამუშაო ჩანაწერები",
            "hr_work_entry_contract": "კონტრაქტებიდან სამუშაო ჩანაწერები",
            "hr_work_entry_contract_enterprise": "კონტრაქტებიდან სამუშაო ჩანაწერები (Enterprise)",
            "l10n_ka": "საქართველო - თარგმანები",
            "mail": "დისკუსია",
            "sign": "ხელმოწერა",
            "spreadsheet_edition": "ცხრილები",
            "web": "ვებ კლიენტი",
            "web_gantt": "განტის ხედი",
        }

        modules = env["ir.module.module"].sudo().search([
            ("name", "in", list(module_names.keys())),
        ])

        updated = 0
        for module in modules:
            ge_name = module_names.get(module.name)
            if not ge_name:
                continue

            values = {}
            if module.shortdesc != ge_name:
                values["shortdesc"] = ge_name
            if module.summary and module.summary != ge_name:
                values["summary"] = ge_name

            if values:
                module.write(values)
                updated += 1

        if updated:
            _logger.info("l10n_ka: translated %s module names", updated)

    @staticmethod
    def _translate_app_menu_names(env):
        app_menu_names = {
            "Accounting": "ბუღალტერია",
            "Approvals": "ბრძანებები",
            "Apps": "აპლიკაციები",
            "Attendances": "დასწრება",
            "Barcode": "შტრიხკოდი",
            "Calendar": "კალენდარი",
            "Contacts": "კონტაქტები",
            "Dashboards": "დაშბორდები",
            "Discuss": "დისკუსია",
            "Documents": "დოკუმენტები",
            "Employees": "თანამშრომლები",
            "Expenses": "ხარჯები",
            "File Editor Passwords": "ფაილ ედიტორის პაროლები",
            "Fleet": "ავტოპარკი",
            "Inventory": "საწყობი",
            "Link Tracker": "ბმულების ტრეკერი",
            "Maintenance": "მომსახურება",
            "Manufacturing": "წარმოება",
            "operations": "ოპერაციები",
            "Planning": "გეგმვა",
            "Project": "პროექტი",
            "Purchase": "შესყიდვები",
            "Recruitment": "რეკრუტმენტი",
            "Sales": "გაყიდვები",
            "Salary Management": "ხელფასების მართვა",
            "Settings": "პარამეტრები",
            "Shop Floor": "საწარმოო იატაკი",
            "Sign": "ხელმოწერა",
            "Time Off": "შვებულებები",
            "Timesheets": "ტაბელი",
            "To-do": "საქმეები",
            "Docx Report": "დოკუმენტის რეპორტი",
        }

        module_app_names = {
            "alnas_docx": "დოკუმენტის რეპორტი",
            "external_file_editor": "ფაილ ედიტორის პაროლები",
            "operations": "ოპერაციები",
            "salary_management": "ხელფასების მართვა",
        }

        root_menu = env.ref("base.menu_root", raise_if_not_found=False)
        domain = []
        if root_menu:
            domain.append(("parent_id", "=", root_menu.id))

        menus = env["ir.ui.menu"].sudo().search(domain)

        updated = 0
        for menu in menus:
            ge_name = app_menu_names.get(menu.name)
            if not ge_name and menu.web_icon:
                technical_module = menu.web_icon.split(",", 1)[0].strip()
                ge_name = module_app_names.get(technical_module)
            if not ge_name:
                continue
            if menu.with_context(lang="ka_GE").name == ge_name:
                continue

            # Writing with lang context stores a translation without changing the base source label.
            menu.with_context(lang="ka_GE").write({"name": ge_name})
            updated += 1

        if updated:
            env["ir.ui.menu"].clear_caches()
            _logger.info("l10n_ka: translated %s app menu names for ka_GE", updated)

    @staticmethod
    def _translate_existing_onboarding_messages(env):
        messages = env["mail.message"].sudo().search([
            "|",
            ("body", "ilike", "May I recommend you to setup an"),
            ("body", "ilike", "Attendance created"),
        ])
        if not messages:
            return

        old_prefix = '<b>Congratulations!</b> May I recommend you to setup an <a href="'
        old_prefix_plain = 'Congratulations! May I recommend you to setup an <a href="'
        new_prefix = '<b>გილოცავთ!</b> გირჩევთ, შექმნათ <a href="'
        old_suffix = '">onboarding plan?</a>'
        new_suffix = '">ადაპტაციის გეგმა</a>'
        attendance_old = 'Attendance created'
        attendance_new = 'დასწრება შეიქმნა'

        updated = 0
        for message in messages:
            body = message.body or ""
            translated = (
                body
                .replace(old_prefix, new_prefix)
                .replace(old_prefix_plain, new_prefix)
                .replace(old_suffix, new_suffix)
                .replace(attendance_old, attendance_new)
            )
            if translated != body:
                message.body = translated
                updated += 1

        if updated:
            _logger.info("l10n_ka: translated %s onboarding chatter messages", updated)
