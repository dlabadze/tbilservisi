/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";
import { onMounted, onWillUnmount, onPatched } from "@odoo/owl";

patch(ListRenderer.prototype, {
    setup() {
        super.setup(...arguments);

        this.scrollAmount = 300;

        onMounted(() => {
            // Wait slightly for DOM to settle and calculate correct widths
            this.setupScrollTimeout = setTimeout(() => {
                this.setupScrollArrows();
            }, 250);
        });

        onPatched(() => {
            this.updateArrowVisibility();
        });

        onWillUnmount(() => {
            clearTimeout(this.setupScrollTimeout);
            this.cleanupScrollArrows();
        });
    },

    setupScrollArrows() {
        if (!this.rootRef?.el) {
            return;
        }

        // Find the wrapper container that has overflow-x: auto
        const tableContainer = this.rootRef.el.querySelector('.o_list_table_wrapper') || 
                               this.rootRef.el.querySelector('.o_list_renderer') || 
                               this.rootRef.el;

        if (!tableContainer) {
            return;
        }

        // Remove any existing scroll arrows inside this renderer to avoid duplicates
        this.cleanupScrollArrows();

        // Create left arrow element
        const leftArrow = document.createElement('div');
        leftArrow.className = 'inventory-scroll-arrow inventory-scroll-arrow-left';
        leftArrow.innerHTML = '<i class="fa fa-chevron-left"></i>';
        
        // Create right arrow element
        const rightArrow = document.createElement('div');
        rightArrow.className = 'inventory-scroll-arrow inventory-scroll-arrow-right';
        rightArrow.innerHTML = '<i class="fa fa-chevron-right"></i>';

        // Add event listeners for click to scroll smoothly
        leftArrow.addEventListener('click', (e) => {
            e.stopPropagation();
            tableContainer.scrollBy({ left: -this.scrollAmount, behavior: 'smooth' });
        });

        rightArrow.addEventListener('click', (e) => {
            e.stopPropagation();
            tableContainer.scrollBy({ left: this.scrollAmount, behavior: 'smooth' });
        });

        // Append arrows to this.rootRef.el (must have relative positioning in CSS)
        this.rootRef.el.appendChild(leftArrow);
        this.rootRef.el.appendChild(rightArrow);

        this.leftArrow = leftArrow;
        this.rightArrow = rightArrow;
        this.tableContainer = tableContainer;

        // Listen for scroll events on the container to dynamically toggle visibility of the arrows
        this.onTableScroll = () => {
            this.updateArrowVisibility();
        };
        this.tableContainer.addEventListener('scroll', this.onTableScroll);

        // Also watch for size changes using ResizeObserver
        if (window.ResizeObserver) {
            this.resizeObserver = new ResizeObserver(() => {
                this.updateArrowVisibility();
            });
            this.resizeObserver.observe(this.tableContainer);
        }

        // Initial check
        this.updateArrowVisibility();
    },

    updateArrowVisibility() {
        if (!this.tableContainer || !this.leftArrow || !this.rightArrow) {
            return;
        }

        const { scrollLeft, scrollWidth, clientWidth } = this.tableContainer;
        
        // If the table is not scrollable (or barely scrollable), hide both arrows
        const isScrollable = scrollWidth > clientWidth + 3;
        
        if (!isScrollable) {
            this.leftArrow.classList.remove('visible');
            this.rightArrow.classList.remove('visible');
            return;
        }

        // Show/hide left arrow based on scroll position
        if (scrollLeft <= 5) {
            this.leftArrow.classList.remove('visible');
        } else {
            this.leftArrow.classList.add('visible');
        }

        // Show/hide right arrow based on scroll position
        if (scrollLeft + clientWidth >= scrollWidth - 5) {
            this.rightArrow.classList.remove('visible');
        } else {
            this.rightArrow.classList.add('visible');
        }
    },

    cleanupScrollArrows() {
        if (this.tableContainer && this.onTableScroll) {
            this.tableContainer.removeEventListener('scroll', this.onTableScroll);
        }
        if (this.resizeObserver) {
            this.resizeObserver.disconnect();
        }
        if (this.leftArrow) {
            this.leftArrow.remove();
            this.leftArrow = null;
        }
        if (this.rightArrow) {
            this.rightArrow.remove();
            this.rightArrow = null;
        }
    }
});

console.log("📦 Inventory Line Scroll Arrows module loaded");