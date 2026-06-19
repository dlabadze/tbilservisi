/** @odoo-module **/
/**
 * For any list table marked with "o_sticky_cols_2", column 1 and column 2
 * are frozen via CSS `position: sticky` (see list_view_custom.scss).
 * Column 1's width isn't fixed, so column 2's `left` offset is measured
 * here at runtime and stored on the table as --o-sticky-col1-w.
 */

import { registry } from "@web/core/registry";

const MARKER_CLASS = "o_sticky_cols_2";
const OBSERVED_ATTR = "data-sticky-cols-observed";

function updateOffset(table) {
    const firstCell = table.querySelector("tbody tr td:first-child") || table.querySelector("thead tr th:first-child");
    if (!firstCell) return;
    table.style.setProperty("--o-sticky-col1-w", `${firstCell.getBoundingClientRect().width}px`);
}

function observeTable(table) {
    if (table.getAttribute(OBSERVED_ATTR)) return;
    table.setAttribute(OBSERVED_ATTR, "1");

    updateOffset(table);

    if (window.ResizeObserver) {
        const ro = new ResizeObserver(() => updateOffset(table));
        ro.observe(table);
    }
}

const stickyColumnsService = {
    start() {
        let debounceTimer = null;

        const scan = () => {
            document.querySelectorAll(`.${MARKER_CLASS} table.o_list_table`).forEach(observeTable);
        };

        const scheduleScan = () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(scan, 300);
        };

        const mo = new MutationObserver(scheduleScan);
        mo.observe(document.body, { childList: true, subtree: true });

        setTimeout(scan, 500);
        return {};
    },
};

registry.category("services").add("fmg_sticky_columns", stickyColumnsService);
