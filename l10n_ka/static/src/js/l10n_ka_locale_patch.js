/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { TimeOffCalendarYearRenderer } from "@hr_holidays/views/calendar/year/calendar_year_renderer";

function getLangCode() {
    const sessionLang =
        (window.odoo && window.odoo.__session_info__ && window.odoo.__session_info__.user_context
            ? window.odoo.__session_info__.user_context.lang
            : "") || "";
    const htmlLang = (document.documentElement && document.documentElement.lang) || "";
    return (sessionLang || htmlLang).toLowerCase();
}

const superOptionsGetter = Object.getOwnPropertyDescriptor(
    TimeOffCalendarYearRenderer.prototype,
    "options"
).get;

patch(TimeOffCalendarYearRenderer.prototype, {
    get options() {
        const options = superOptionsGetter.call(this);
        if (!getLangCode().startsWith("ka")) {
            return options;
        }

        return {
            ...options,
            // Force Georgian month titles for Time Off yearly dashboard calendar.
            titleFormat: (arg) =>
                new Intl.DateTimeFormat("ka-GE", {
                    month: "long",
                    year: "numeric",
                }).format(arg.date),
        };
    },
});
