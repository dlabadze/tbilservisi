/** @odoo-module **/

import { ListController } from "@web/views/list/list_controller";
import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";

export class FuelListControllerWithDateFilter extends ListController {
	setup() {
		super.setup();
	}

	openFuelDateWizard() {
		this.actionService.doAction("fuel_management.action_fuel_date_wizard");
	}

	openFuelRecalcWizard() {
		this.actionService.doAction("fuel_management.action_fuel_recalc_wizard");
	}
}

registry.category("views").add("fuel_management_list_with_date_filter", {
	...listView,
	Controller: FuelListControllerWithDateFilter,
	buttonTemplate: "fuel_management.ListView.Buttons",
});


