/** @odoo-module **/

/**
 * Barcode Quantity Input - რაოდენობის შეყვანის ფუნქციონალი
 */

(function() {
    'use strict';
    
    async function jsonrpc(url, params) {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                jsonrpc: '2.0',
                method: 'call',
                params: params,
                id: Math.floor(Math.random() * 1000000000),
            }),
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        
        if (data.error) {
            throw new Error(data.error.data?.message || data.error.message || JSON.stringify(data.error));
        }
        return data.result;
    }
    
    window.barcodeQuantityHandler = {
        initialized: false,
        enhancedLines: new Set(),
        
        init: function() {
            if (this.initialized) return;
            this.initialized = true;
            this.observeBarcodeInterface();
        },
        
        observeBarcodeInterface: function() {
            const self = this;
            
            setTimeout(() => self.enhanceAllExistingLines(), 100);
            setTimeout(() => self.enhanceAllExistingLines(), 200);
            setTimeout(() => self.enhanceAllExistingLines(), 300);
            setTimeout(() => self.enhanceAllExistingLines(), 500);
            setTimeout(() => self.enhanceAllExistingLines(), 1000);
            setTimeout(() => self.enhanceAllExistingLines(), 2000);
            
            setInterval(() => {
                self.enhanceAllExistingLines();
            }, 200);
            
            const observer = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    mutation.addedNodes.forEach(function(node) {
                        if (node.nodeType === 1) {
                            self.enhanceBarcodeLines(node);
                        }
                    });
                });
            });
            
            const startObserving = function() {
                const targetNode = document.body;
                if (targetNode) {
                    observer.observe(targetNode, {
                        childList: true,
                        subtree: true
                    });
                }
            };
            
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', startObserving);
            } else {
                startObserving();
            }
        },
        
        enhanceAllExistingLines: function() {
            const lines = document.querySelectorAll('.o_barcode_line');
            lines.forEach(line => {
                this.enhanceBarcodeLines(line);
            });
        },
        
        enhanceBarcodeLines: function(element) {
            if (!element || !element.querySelectorAll) return;
            
            const lines = element.classList && element.classList.contains('o_barcode_line') 
                ? [element] 
                : element.querySelectorAll('.o_barcode_line');
            
            lines.forEach(line => {
                const virtualId = line.dataset.virtualId;
                
                const existingInput = line.querySelector('.o_barcode_qty_input_group');
                if (existingInput) {
                    return;
                }
                
                if (this.enhancedLines.has(virtualId)) {
                    this.enhancedLines.delete(virtualId);
                }
                
                const qtyContainer = line.querySelector('div[name="quantity"]');
                
                if (qtyContainer && virtualId) {
                    this.injectQuantityInput(line, qtyContainer, virtualId);
                    this.enhancedLines.add(virtualId);
                }
            });
        },
        
        parseNumber: function(value) {
            if (typeof value === 'number') return value;
            if (!value) return 0;
            const str = String(value).trim();
            const normalized = str.replace(',', '.');
            const num = parseFloat(normalized);
            return isNaN(num) ? 0 : num;
        },
        
        injectQuantityInput: function(line, qtyContainer, virtualId) {
            const lineId = 'line_' + virtualId;
            line.dataset.lineId = lineId;
            line.dataset.virtualId = virtualId;
            
            const qtyDoneSpan = line.querySelector('.qty-done');
            const currentQty = qtyDoneSpan ? this.parseNumber(qtyDoneSpan.textContent) : 0;
            
            const inputGroup = document.createElement('div');
            inputGroup.className = 'o_barcode_qty_input_group d-flex align-items-center gap-2 mt-2';
            inputGroup.dataset.lineId = lineId;
            inputGroup.innerHTML = `
                <input type="number" 
                       class="form-control form-control-sm o_barcode_quantity_input" 
                       value="${currentQty}"
                       step="0.01" 
                       min="0" 
                       placeholder="შეიყვანეთ რაოდენობა"
                       style="width: 150px; font-weight: bold; text-align: center; font-size: 1.1em;">
                <button class="btn btn-success btn-sm o_save_qty" type="button" title="შენახვა">
                    <i class="fa fa-check me-1"></i> შენახვა
                </button>
            `;
            
            const input = inputGroup.querySelector('input');
            const saveBtn = inputGroup.querySelector('.o_save_qty');
            
            input.onkeydown = (ev) => {
                this.handleKeydown(ev, lineId, virtualId);
            };
            saveBtn.onclick = () => {
                this.saveQuantity(lineId, input, virtualId);
            };
            
            qtyContainer.appendChild(inputGroup);
        },
        
        async saveQuantity(lineId, inputElement, virtualId) {
            const newQty = this.parseNumber(inputElement.value);
            
            if (newQty < 0) {
                alert('რაოდენობა არ შეიძლება იყოს უარყოფითი');
                return;
            }
            
            const line = document.querySelector(`[data-line-id="${lineId}"]`);
            if (!line) return;
            
            const qtyDoneSpan = line.querySelector('.qty-done');
            if (!qtyDoneSpan) return;
            
            const currentQty = this.parseNumber(qtyDoneSpan.textContent);
            
            qtyDoneSpan.textContent = newQty;
            
            try {
                const pickingName = this.getCurrentPickingName();
                
                if (!pickingName) {
                    this.showNotification('⚠️ შეცდომა: picking არ მოიძებნა', 'warning');
                    return;
                }
                
                const moveLines = await jsonrpc('/web/dataset/call_kw', {
                    model: 'stock.picking',
                    method: 'get_move_lines_by_picking_name',
                    args: [pickingName],
                    kwargs: {}
                });
                
                const moveLine = moveLines.find(ml => ml.virtual_id === parseInt(virtualId));
                
                if (moveLine) {
                    const result = await jsonrpc('/web/dataset/call_kw', {
                        model: 'stock.picking',
                        method: 'update_move_line_quantity',
                        args: [moveLine.id, newQty],
                        kwargs: {}
                    });
                    
                    if (!result || !result.success) {
                        throw new Error(result?.error || 'Failed to update quantity');
                    }
                    
                    this.showNotification('✅ რაოდენობა შენახულია', 'success');
                    
                    qtyDoneSpan.textContent = result.quantity || newQty;
                    inputElement.value = result.quantity || newQty;
                    
                    setTimeout(() => {
                        const refreshEvent = new CustomEvent('barcode-line-updated', {
                            detail: { lineId: moveLine.id, quantity: result.quantity },
                            bubbles: true
                        });
                        document.dispatchEvent(refreshEvent);
                    }, 100);
                } else {
                    this.showNotification('⚠️ შეცდომა: ხაზი არ მოიძებნა', 'warning');
                }
                
            } catch (error) {
                this.showNotification('❌ შეცდომა: ' + error.message, 'danger');
                qtyDoneSpan.textContent = currentQty;
            }
        },
        
        getCurrentPickingName: function() {
            const titleButton = document.querySelector('.o_barcode_header .o_title div');
            if (titleButton) {
                return titleButton.textContent.trim();
            }
            return null;
        },
        
        showNotification: function(message, type = 'info') {
            if (window.odoo && window.odoo.notification) {
                window.odoo.notification.add(message, { type });
            }
        },
        
        handleKeydown: function(event, lineId, virtualId) {
            if (event.key === 'Enter') {
                event.preventDefault();
                const line = document.querySelector(`[data-line-id="${lineId}"]`);
                const input = line?.querySelector('.o_barcode_quantity_input');
                if (input) {
                    this.saveQuantity(lineId, input, virtualId);
                }
            }
        }
    };
    
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            window.barcodeQuantityHandler.init();
        });
    } else {
        window.barcodeQuantityHandler.init();
    }
    
})();
