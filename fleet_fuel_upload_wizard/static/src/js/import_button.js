/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";

export class FleetFuelUploadListController extends ListController {
	setup() {
		super.setup();
	}

	onOpenImportWizard() {
		this.actionService.doAction('fleet_fuel_upload_wizard.action_fleet_fuel_upload_wizard');
	}
}

registry.category("views").add("fleet_fuel_upload_list", {
	...listView,
	Controller: FleetFuelUploadListController,
	buttonTemplate: "fleet_fuel_upload_wizard.ListView.Buttons",
});
