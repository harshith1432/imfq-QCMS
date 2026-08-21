/**
 * QCMS Action Locking & Single-Execution Engine
 * ============================================
 * Prevents double-clicks, rapid clicks, keyboard spam, touch spam, and duplicate API requests.
 */

(function () {
    'use strict';

    class ActionLockEngine {
        constructor() {
            this.activeLocks = new Set();
            this.inFlightEndpoints = new Map(); // endpoint -> Promise
            this.initGlobalInterceptors();
        }

        /**
         * Global capture-phase event listeners to block redundant clicks/submits on locked elements.
         */
        initGlobalInterceptors() {
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', () => this.bindDocumentEvents());
            } else {
                this.bindDocumentEvents();
            }
        }

        bindDocumentEvents() {
            // Capture phase click interceptor
            document.addEventListener('click', (e) => {
                const target = e.target.closest('button, a, input[type="submit"], input[type="button"], [data-action]');
                if (!target) return;

                if (this.isLocked(target)) {
                    e.preventDefault();
                    e.stopPropagation();
                    e.stopImmediatePropagation();
                    return false;
                }
            }, true);

            // Capture phase form submit interceptor
            document.addEventListener('submit', (e) => {
                const form = e.target;
                if (!form) return;

                if (this.isLocked(form)) {
                    e.preventDefault();
                    e.stopPropagation();
                    e.stopImmediatePropagation();
                    return false;
                }

                // Lock form submit button automatically
                const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
                if (submitBtn) {
                    this.lockButton(submitBtn);

                    const initialCount = (window.api && window.api.inFlightRequests) ? window.api.inFlightRequests.size : 0;

                    // Check periodically and unlock submit button when request finishes or fails
                    const checkInterval = setInterval(() => {
                        const inFlight = (window.api && window.api.inFlightRequests) ? window.api.inFlightRequests.size : 0;
                        if (inFlight === 0) {
                            clearInterval(checkInterval);
                            if (this.isLocked(submitBtn)) {
                                this.unlockButton(submitBtn);
                            }
                        }
                    }, 100);

                    // Safety timeout after 1.5 seconds maximum
                    setTimeout(() => {
                        clearInterval(checkInterval);
                        if (this.isLocked(submitBtn)) {
                            this.unlockButton(submitBtn);
                        }
                    }, 1500);
                }
            }, true);

            // Prevent Enter key spam on focused inputs when processing
            document.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    const target = e.target.closest('button, input[type="submit"], [data-action]');
                    if (target && this.isLocked(target)) {
                        e.preventDefault();
                        e.stopPropagation();
                        e.stopImmediatePropagation();
                        return false;
                    }
                }
            }, true);
        }

        /**
         * Checks if an element or form is currently locked.
         */
        isLocked(el) {
            if (!el) return false;
            return el.classList.contains('is-locked') ||
                   el.dataset.loading === 'true' ||
                   el.disabled === true ||
                   el.getAttribute('aria-busy') === 'true' ||
                   this.activeLocks.has(el);
        }

        /**
         * Converts a button into a Loading state and locks interaction.
         */
        lockButton(btn, customText = '') {
            if (!btn || this.isLocked(btn)) return false;

            // Preserve original HTML content and styles
            if (!btn.dataset.originalHtml) {
                btn.dataset.originalHtml = btn.innerHTML;
            }

            const currentText = btn.innerText ? btn.innerText.trim() : 'Processing';
            let loadingText = customText;

            if (!loadingText) {
                if (currentText.startsWith('Create') || currentText.startsWith('Add')) {
                    loadingText = currentText.replace(/^(Create|Add)/, '$1ing') + '...';
                } else if (currentText.startsWith('Save') || currentText.startsWith('Submit')) {
                    loadingText = currentText.replace(/^(Save|Submit)/, '$1ting') + '...';
                } else if (currentText.startsWith('Delete') || currentText.startsWith('Remove')) {
                    loadingText = currentText.replace(/^(Delete|Remove)/, '$1ting') + '...';
                } else if (currentText.startsWith('Update')) {
                    loadingText = 'Updating...';
                } else if (currentText.startsWith('Upload')) {
                    loadingText = 'Uploading...';
                } else if (currentText.startsWith('Export') || currentText.startsWith('Download')) {
                    loadingText = 'Generating...';
                } else {
                    loadingText = 'Processing...';
                }
            }

            btn.classList.add('is-locked', 'btn-loading', 'disabled');
            btn.dataset.loading = 'true';
            btn.dataset.locked = 'true';
            btn.setAttribute('disabled', 'true');
            btn.setAttribute('aria-busy', 'true');
            btn.style.pointerEvents = 'none';
            btn.style.cursor = 'not-allowed';

            // Set loading spinner and text
            btn.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span><span>${loadingText}</span>`;

            this.activeLocks.add(btn);

            // Safety fallback timeout after 5 seconds to prevent permanent locking
            if (btn._lockSafetyTimer) clearTimeout(btn._lockSafetyTimer);
            btn._lockSafetyTimer = setTimeout(() => {
                this.unlockButton(btn);
            }, 5000);

            return true;
        }

        /**
         * Restores button to Idle state.
         */
        unlockButton(btn) {
            if (!btn) return;

            if (btn._lockSafetyTimer) {
                clearTimeout(btn._lockSafetyTimer);
                btn._lockSafetyTimer = null;
            }

            btn.classList.remove('is-locked', 'btn-loading', 'disabled');
            btn.dataset.loading = 'false';
            btn.dataset.locked = 'false';
            btn.removeAttribute('disabled');
            btn.removeAttribute('aria-busy');
            btn.style.pointerEvents = '';
            btn.style.cursor = '';

            if (btn.dataset.originalHtml) {
                btn.innerHTML = btn.dataset.originalHtml;
                delete btn.dataset.originalHtml;
            }

            this.activeLocks.delete(btn);

            if (window.lucide && typeof window.lucide.createIcons === 'function') {
                try { window.lucide.createIcons(); } catch (_) {}
            }
        }

        /**
         * Wraps an async function call with automatic button locking and unlocking.
         */
        async execute(btn, asyncFn, customText = '') {
            if (btn && this.isLocked(btn)) {
                console.warn('[ActionLock] Duplicate execution blocked for button:', btn);
                return;
            }

            if (btn) this.lockButton(btn, customText);

            try {
                const result = await asyncFn();
                return result;
            } finally {
                if (btn) this.unlockButton(btn);
            }
        }
    }

    window.ActionLock = new ActionLockEngine();
})();
