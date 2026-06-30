/** @odoo-module */

// Do not read @web localization parameters during early boot, as this can
// crash module loading before parameters are initialized.
const sessionLang =
    (window.odoo && window.odoo.__session_info__ && window.odoo.__session_info__.user_context
        ? window.odoo.__session_info__.user_context.lang
        : "") || "";
const htmlLang = (document.documentElement && document.documentElement.lang) || "";
const langCode = (sessionLang || htmlLang).toLowerCase();

if (langCode.startsWith("ka") && typeof luxon !== "undefined" && luxon.Settings) {
    luxon.Settings.defaultLocale = "ka";
}
