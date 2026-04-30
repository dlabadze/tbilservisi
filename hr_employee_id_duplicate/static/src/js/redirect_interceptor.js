/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { actionService } from "@web/webclient/actions/action_service";

/**
 * Patch ActionService to support skipCheckIsDirty in Odoo 18.
 */
patch(actionService, {
    start(env) {
        const am = super.start(...arguments);
        const originalDoAction = am.doAction;

        am.doAction = async function (actionRequest, options = {}) {
            const isDuplicateWizard =
                actionRequest === "hr_employee_id_duplicate.action_hr_employee_duplicate_wizard" ||
                (typeof actionRequest === "object" && actionRequest.res_model === "hr.employee.duplicate.wizard");

            if (isDuplicateWizard || options.skipCheckIsDirty) {
                const originalTrigger = env.bus.trigger;
                env.bus.trigger = (name, ...args) => {
                    if (name === "CLEAR-UNCOMMITTED-CHANGES") return;
                    return originalTrigger.apply(env.bus, [name, ...args]);
                };
                try {
                    return await originalDoAction.apply(this, arguments);
                } finally {
                    env.bus.trigger = originalTrigger;
                }
            }
            return originalDoAction.apply(this, arguments);
        };
        return am;
    },
});

/**
 * Patch FormController to bypass the standard Save Error dialog
 * specifically for the Duplicate Employee RedirectWarning.
 * This removes the "Oh snap!", "Stay here", and "Discard changes" buttons.
 */
patch(FormController.prototype, {
    async onSaveError(error, { discard }) {
        if (error && error.data && error.data.name === "odoo.exceptions.RedirectWarning") {
            const args = error.data.arguments;
            if (args && args.length >= 2) {
                const [message, actionId, buttonText, additionalContext] = args;

                // If it relates to our duplicate employee check
                if (message && message.includes("ყოფილი თანამშრომელი")) {
                    // Bypass the standard dialog entirely
                    this.allowLeavingWithoutSaving = true;
                    try {
                        await this.actionService.doAction(actionId, {
                            additionalContext,
                            skipCheckIsDirty: true
                        });
                        // Return false to signify the error was handled and no further dialog is needed
                        return false;
                    } finally {
                        this.allowLeavingWithoutSaving = false;
                    }
                }
            }
        }
        // For other errors, use standard Odoo behavior
        return super.onSaveError(...arguments);
    }
});
