/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";

export class DakavebaImportListController extends ListController {
    setup() {
        super.setup();
    }

    onOpenDakavebaImportWizard() {
        this.actionService.doAction(
            "biuleteni.action_dakaveba_import_wizard"   // <-- your wizard action
        );
    }
}

registry.category("views").add("dakaveba_import_list", {
    ...listView,
    Controller: DakavebaImportListController,
    buttonTemplate: "dakaveba_import.ListView.Buttons",
});
