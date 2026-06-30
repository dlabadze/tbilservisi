/** @odoo-module */

import { localization } from "@web/core/l10n/localization";

const langCode = (localization.code || "").toLowerCase();
if (langCode.startsWith("ka")) {
    luxon.Settings.defaultLocale = "ka";
}
