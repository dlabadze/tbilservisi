/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";
import { onMounted, onWillUnmount } from "@odoo/owl";

patch(ListRenderer.prototype, {
    setup() {
        super.setup(...arguments);
        
        onMounted(() => {
            setTimeout(() => {
                this.setupScrollArrows();
            }, 200);
        });
        
        onWillUnmount(() => {
            this.cleanupScrollArrows();
        });
    },

    setupScrollArrows() {
        let tableContainer = null;
        
        if (this.rootRef?.el) {
            tableContainer = this.rootRef.el.querySelector('.o_list_table_wrapper') ||
                           this.rootRef.el.querySelector('.o_list_view') ||
                           this.rootRef.el.closest('.o_list_renderer') ||
                           this.rootRef.el;
        } else {
            return;
        }
        
        if (!tableContainer) {
            return;
        }

        // Check if already has arrows
        if (document.querySelector('.inventory-scroll-arrow')) {
            return;
        }

        // Create left arrow
        const leftArrow = document.createElement('div');
        leftArrow.className = 'inventory-scroll-arrow inventory-scroll-arrow-left visible';
        leftArrow.innerHTML = '<i class="fa fa-chevron-left"></i>';
        leftArrow.style.cssText = `
            position: fixed;
            left: 20px;
            top: 50%;
            transform: translateY(-50%);
            width: 50px;
            height: 50px;
            background: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            z-index: 9999;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
        `;
        leftArrow.addEventListener('click', (e) => {
            e.stopPropagation();
            tableContainer.scrollBy({ left: -300, behavior: 'smooth' });
        });
        
        // Create right arrow
        const rightArrow = document.createElement('div');
        rightArrow.className = 'inventory-scroll-arrow inventory-scroll-arrow-right visible';
        rightArrow.innerHTML = '<i class="fa fa-chevron-right"></i>';
        rightArrow.style.cssText = `
            position: fixed;
            right: 20px;
            top: 50%;
            transform: translateY(-50%);
            width: 50px;
            height: 50px;
            background: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            z-index: 9999;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
        `;
        rightArrow.addEventListener('click', (e) => {
            e.stopPropagation();
            tableContainer.scrollBy({ left: 300, behavior: 'smooth' });
        });

        // Append to body for visibility
        document.body.appendChild(leftArrow);
        document.body.appendChild(rightArrow);

        // Store references
        this.leftArrow = leftArrow;
        this.rightArrow = rightArrow;
        this.tableContainer = tableContainer;
    },

    cleanupScrollArrows() {
        if (this.leftArrow) this.leftArrow.remove();
        if (this.rightArrow) this.rightArrow.remove();
    }
});

console.log("📦 Inventory Line Scroll Arrows module loaded");