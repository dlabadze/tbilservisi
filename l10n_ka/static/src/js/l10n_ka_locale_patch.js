/** @odoo-module */

function getLangCode() {
    const sessionLang =
        (window.odoo && window.odoo.__session_info__ && window.odoo.__session_info__.user_context
            ? window.odoo.__session_info__.user_context.lang
            : "") || "";
    const htmlLang = (document.documentElement && document.documentElement.lang) || "";
    return (sessionLang || htmlLang).toLowerCase();
}

if (getLangCode().startsWith("ka")) {
    const monthMap = {
        January: "იანვარი",
        February: "თებერვალი",
        March: "მარტი",
        April: "აპრილი",
        May: "მაისი",
        June: "ივნისი",
        July: "ივლისი",
        August: "აგვისტო",
        September: "სექტემბერი",
        October: "ოქტომბერი",
        November: "ნოემბერი",
        December: "დეკემბერი",
    };

    const dayAriaMap = {
        Monday: "ორშაბათი",
        Tuesday: "სამშაბათი",
        Wednesday: "ოთხშაბათი",
        Thursday: "ხუთშაბათი",
        Friday: "პარასკევი",
        Saturday: "შაბათი",
        Sunday: "კვირა",
    };

    const dayShortMap = {
        Monday: "ორ",
        Tuesday: "სამ",
        Wednesday: "ოთხ",
        Thursday: "ხუთ",
        Friday: "პარ",
        Saturday: "შაბ",
        Sunday: "კვ",
    };

    function toGeorgianDateLabel(label) {
        const match = /^([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})$/.exec(label);
        if (!match) {
            return null;
        }
        const [, monthEn, day, year] = match;
        if (!monthMap[monthEn]) {
            return null;
        }
        const monthIndex = [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ].indexOf(monthEn);
        if (monthIndex < 0) {
            return null;
        }

        const date = new Date(Number(year), monthIndex, Number(day));
        if (Number.isNaN(date.getTime())) {
            return null;
        }
        return new Intl.DateTimeFormat("ka-GE", {
            month: "long",
            day: "numeric",
            year: "numeric",
        }).format(date);
    }

    function localizeYearCalendar(root) {
        const yearViews = root.querySelectorAll(".fc.fc-dayGridYear-view");
        for (const yearView of yearViews) {
            const titles = yearView.querySelectorAll(".fc-toolbar-title");
            for (const title of titles) {
                const text = (title.textContent || "").trim();
                const monthYear = /^([A-Za-z]+)\s+(\d{4})$/.exec(text);
                if (!monthYear) {
                    continue;
                }
                const [, monthEn, year] = monthYear;
                if (monthMap[monthEn]) {
                    title.textContent = `${monthMap[monthEn]} ${year}`;
                }
            }

            const ariaNodes = yearView.querySelectorAll("[aria-label]");
            for (const node of ariaNodes) {
                const aria = node.getAttribute("aria-label") || "";

                if (dayAriaMap[aria]) {
                    node.setAttribute("aria-label", dayAriaMap[aria]);
                    if (node.classList.contains("fc-col-header-cell-cushion")) {
                        node.textContent = dayShortMap[aria] || node.textContent;
                    }
                    continue;
                }

                const weekMatch = /^Week\s+(\d+)$/.exec(aria);
                if (weekMatch) {
                    node.setAttribute("aria-label", `კვირა ${weekMatch[1]}`);
                    continue;
                }

                const geDate = toGeorgianDateLabel(aria);
                if (geDate) {
                    node.setAttribute("aria-label", geDate);
                }
            }
        }
    }

    let queued = false;
    const scheduleLocalization = () => {
        if (queued) {
            return;
        }
        queued = true;
        requestAnimationFrame(() => {
            queued = false;
            localizeYearCalendar(document);
        });
    };

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", scheduleLocalization, { once: true });
    } else {
        scheduleLocalization();
    }

    const observer = new MutationObserver(scheduleLocalization);
    observer.observe(document.documentElement, {
        childList: true,
        subtree: true,
    });
}
