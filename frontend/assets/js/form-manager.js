/**
 * QCMS Centralized Form State & Transactional Form Manager
 * Ensures zero auto-save / zero automatic DB updates while typing or editing.
 * DB updates occur strictly when the user clicks 'Save Changes'.
 */

class FormManager {
    constructor(config = {}) {
        this.containerSelector = config.container;
        this.containerEl = typeof config.container === 'string' 
            ? document.querySelector(config.container) 
            : config.container;
        
        this.saveBtn = config.saveBtn ? (typeof config.saveBtn === 'string' ? document.querySelector(config.saveBtn) : config.saveBtn) : null;
        this.cancelBtn = config.cancelBtn ? (typeof config.cancelBtn === 'string' ? document.querySelector(config.cancelBtn) : config.cancelBtn) : null;
        this.badgeEl = config.badge ? (typeof config.badge === 'string' ? document.querySelector(config.badge) : config.badge) : null;
        
        this.onSaveCallback = config.onSave || null;
        this.onCancelCallback = config.onCancel || null;
        this.validateFn = config.validate || null;

        this.originalData = {};
        this.editableData = {};
        this.dirtyFields = new Set();
        this.isDirty = false;
        this.validationErrors = {};
        this.pendingFiles = {};

        if (this.containerEl) {
            this.bindEvents();
        }
    }

    /**
     * Initializes or re-seeds form data from current DOM values or explicit JSON
     */
    initData(dataObject = null) {
        this.originalData = dataObject ? JSON.parse(JSON.stringify(dataObject)) : this.extractFormDataFromDOM();
        this.editableData = JSON.parse(JSON.stringify(this.originalData));
        this.dirtyFields.clear();
        this.isDirty = false;
        this.pendingFiles = {};
        this.validationErrors = {};
        this.syncDOMFromEditableData();
        this.updateUIState();
    }

    /**
     * Extracts values of input, select, textarea elements within container
     */
    extractFormDataFromDOM() {
        if (!this.containerEl) return {};
        const data = {};
        const inputs = this.containerEl.querySelectorAll('input, select, textarea');
        
        inputs.forEach(input => {
            const key = input.name || input.id;
            if (!key || input.type === 'file' || input.type === 'button' || input.type === 'submit') return;

            if (input.type === 'checkbox') {
                data[key] = input.checked;
            } else if (input.type === 'radio') {
                if (input.checked) {
                    data[input.name] = input.value;
                }
            } else {
                data[key] = input.value;
            }
        });
        return data;
    }

    /**
     * Syncs DOM inputs to match editableData
     */
    syncDOMFromEditableData() {
        if (!this.containerEl) return;
        const inputs = this.containerEl.querySelectorAll('input, select, textarea');

        inputs.forEach(input => {
            const key = input.name || input.id;
            if (!key || input.type === 'file' || input.type === 'button' || input.type === 'submit') return;

            if (input.type === 'checkbox') {
                if (key in this.editableData) input.checked = Boolean(this.editableData[key]);
            } else if (input.type === 'radio') {
                if (input.name in this.editableData) {
                    input.checked = (input.value === String(this.editableData[input.name]));
                }
            } else {
                if (key in this.editableData && this.editableData[key] !== null && this.editableData[key] !== undefined) {
                    input.value = this.editableData[key];
                }
            }
        });
    }

    /**
     * Binds input/change event listeners strictly to update LOCAL UI STATE only (NO API Calls!)
     */
    bindEvents() {
        if (!this.containerEl) return;

        // Input event for text, textarea, number, email, phone, etc.
        this.containerEl.addEventListener('input', (e) => {
            const target = e.target;
            if (!target.matches('input, select, textarea')) return;
            if (target.type === 'file') return;

            this.handleFieldChange(target);
        });

        // Change event for checkbox, radio, select, date, file
        this.containerEl.addEventListener('change', (e) => {
            const target = e.target;
            if (!target.matches('input, select, textarea')) return;

            if (target.type === 'file') {
                const key = target.name || target.id;
                if (key && target.files.length > 0) {
                    this.pendingFiles[key] = target.files[0];
                    this.dirtyFields.add(key);
                    this.isDirty = true;
                    this.updateUIState();
                }
                return;
            }

            this.handleFieldChange(target);
        });

        // Wire Save Button
        if (this.saveBtn) {
            this.saveBtn.addEventListener('click', async (e) => {
                e.preventDefault();
                await this.save();
            });
        }

        // Wire Cancel Button
        if (this.cancelBtn) {
            this.cancelBtn.addEventListener('click', (e) => {
                e.preventDefault();
                this.cancel();
            });
        }
    }

    /**
     * Updates local editableData and calculates dirty fields without triggering network requests
     */
    handleFieldChange(target) {
        const key = target.name || target.id;
        if (!key) return;

        let val;
        if (target.type === 'checkbox') {
            val = target.checked;
        } else if (target.type === 'radio') {
            val = target.value;
        } else {
            val = target.value;
        }

        this.editableData[key] = val;

        // Compare with originalData
        const origVal = this.originalData[key];
        if (String(val) !== String(origVal !== undefined ? origVal : '')) {
            this.dirtyFields.add(key);
        } else {
            this.dirtyFields.delete(key);
        }

        this.isDirty = this.dirtyFields.size > 0 || Object.keys(this.pendingFiles).length > 0;
        this.updateUIState();
    }

    /**
     * Updates button states and dirty badge
     */
    updateUIState() {
        if (this.saveBtn) {
            this.saveBtn.disabled = !this.isDirty;
            if (this.isDirty) {
                this.saveBtn.classList.remove('disabled', 'btn-secondary', 'ds-btn-disabled');
                this.saveBtn.classList.add('ds-btn-primary', 'btn-primary');
            } else {
                this.saveBtn.classList.add('disabled', 'ds-btn-disabled');
            }
        }

        if (this.cancelBtn) {
            this.cancelBtn.disabled = !this.isDirty;
            if (this.isDirty) {
                this.cancelBtn.classList.remove('disabled', 'd-none');
            } else {
                this.cancelBtn.classList.add('disabled');
            }
        }

        if (this.badgeEl) {
            if (this.isDirty) {
                this.badgeEl.classList.remove('d-none');
                this.badgeEl.style.display = 'inline-flex';
            } else {
                this.badgeEl.classList.add('d-none');
                this.badgeEl.style.display = 'none';
            }
        }
    }

    /**
     * Returns JSON object containing ONLY modified fields
     */
    getDiffPayload() {
        const payload = {};
        this.dirtyFields.forEach(key => {
            if (key in this.editableData) {
                payload[key] = this.editableData[key];
            }
        });
        return payload;
    }

    /**
     * Validates form and performs explicit Save Changes API call
     */
    async save() {
        if (!this.isDirty && Object.keys(this.pendingFiles).length === 0) return false;

        // Run validation if provided
        if (typeof this.validateFn === 'function') {
            const isValid = this.validateFn(this.editableData);
            if (!isValid) {
                if (typeof showToast === 'function') showToast('Please fix validation errors before saving.', 'danger');
                return false;
            }
        }

        const payload = this.getDiffPayload();

        try {
            if (this.saveBtn) {
                this.saveBtn.disabled = true;
                this.saveBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span> Saving...`;
            }

            let success = false;
            if (typeof this.onSaveCallback === 'function') {
                success = await this.onSaveCallback(payload, this.pendingFiles, this.editableData);
            }

            if (success !== false) {
                // Update originalData snapshot on success
                this.originalData = JSON.parse(JSON.stringify(this.editableData));
                this.dirtyFields.clear();
                this.pendingFiles = {};
                this.isDirty = false;
                this.updateUIState();

                if (typeof showToast === 'function') {
                    showToast('Changes saved successfully!', 'success');
                } else if (window.Components && typeof window.Components.showToast === 'function') {
                    window.Components.showToast('Changes saved successfully!', 'success');
                }
                return true;
            } else {
                throw new Error('Save callback returned failure');
            }
        } catch (err) {
            console.error('[FormManager] Save failed:', err);
            if (typeof showToast === 'function') {
                showToast('Save failed. Please try again.', 'danger');
            } else if (window.Components && typeof window.Components.showToast === 'function') {
                window.Components.showToast('Save failed. Please try again.', 'danger');
            }
            return false;
        } finally {
            if (this.saveBtn) {
                this.saveBtn.disabled = !this.isDirty;
                this.saveBtn.innerHTML = `Save Changes`;
            }
        }
    }

    /**
     * Cancels all unsaved changes and restores original values
     */
    cancel() {
        if (!this.isDirty) return;

        this.editableData = JSON.parse(JSON.stringify(this.originalData));
        this.dirtyFields.clear();
        this.pendingFiles = {};
        this.isDirty = false;
        this.syncDOMFromEditableData();
        this.updateUIState();

        if (typeof this.onCancelCallback === 'function') {
            this.onCancelCallback();
        }

        if (typeof showToast === 'function') {
            showToast('Unsaved changes discarded.', 'info');
        }
    }
}

/**
 * Navigation Protection Guard (NavigationGuard)
 * Intercepts tab closing, browser reload, and in-app route changes when unsaved changes exist.
 */
const NavigationGuard = {
    _activeFormManagers: new Set(),
    _initialized: false,

    register(formManager) {
        this._activeFormManagers.add(formManager);
        if (!this._initialized) {
            this.initGlobalListeners();
            this._initialized = true;
        }
    },

    unregister(formManager) {
        this._activeFormManagers.delete(formManager);
    },

    hasUnsavedChanges() {
        for (const fm of this._activeFormManagers) {
            if (fm.isDirty) return true;
        }
        return false;
    },

    getDirtyManager() {
        for (const fm of this._activeFormManagers) {
            if (fm.isDirty) return fm;
        }
        return null;
    },

    initGlobalListeners() {
        // Browser tab reload / close alert
        window.addEventListener('beforeunload', (e) => {
            if (this.hasUnsavedChanges()) {
                e.preventDefault();
                e.returnValue = 'You have unsaved changes. Save before leaving?';
                return e.returnValue;
            }
        });

        // Intercept internal navigation clicks
        document.addEventListener('click', async (e) => {
            const link = e.target.closest('a, button[data-nav-target], .sidebar-link, .ps-nav-item');
            if (!link) return;

            // Ignore save/cancel button clicks
            if (link.closest('#saveChangesBtn, #cancelBtn, .fm-save-btn, .fm-cancel-btn')) return;

            if (this.hasUnsavedChanges()) {
                const targetHref = link.getAttribute('href') || link.getAttribute('data-href');
                if (targetHref && targetHref !== '#' && !targetHref.startsWith('javascript:')) {
                    e.preventDefault();
                    e.stopPropagation();

                    const fm = this.getDirtyManager();
                    const choice = await this.showConfirmationModal();

                    if (choice === 'save') {
                        const saved = await fm.save();
                        if (saved) {
                            window.location.href = targetHref;
                        }
                    } else if (choice === 'discard') {
                        fm.cancel();
                        window.location.href = targetHref;
                    }
                    // Choice === 'cancel' does nothing, stays on page
                }
            }
        }, true);
    },

    showConfirmationModal() {
        return new Promise((resolve) => {
            // Remove existing modal if any
            const oldModal = document.getElementById('unsavedChangesModal');
            if (oldModal) oldModal.remove();

            const modalHtml = `
                <div class="modal fade show" id="unsavedChangesModal" tabindex="-1" style="display: block; background: rgba(0,0,0,0.5); z-index: 10000;" aria-modal="true" role="dialog">
                    <div class="modal-dialog modal-dialog-centered">
                        <div class="modal-content shadow-lg border-0 rounded-3">
                            <div class="modal-header bg-warning text-dark py-3">
                                <h5 class="modal-title font-semibold fs-6">
                                    <i class="bi bi-exclamation-triangle-fill me-2"></i> Unsaved Changes
                                </h5>
                                <button type="button" class="btn-close" id="ucmCloseBtn"></button>
                            </div>
                            <div class="modal-content p-4 text-center">
                                <p class="mb-3 text-secondary">You have unsaved changes. Save before leaving?</p>
                                <div class="d-flex justify-content-center gap-2 mt-2">
                                    <button class="btn btn-success px-4" id="ucmSaveBtn">Save</button>
                                    <button class="btn btn-outline-danger px-4" id="ucmDiscardBtn">Discard</button>
                                    <button class="btn btn-secondary px-4" id="ucmCancelBtn">Cancel</button>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;

            document.body.insertAdjacentHTML('beforeend', modalHtml);

            const modalEl = document.getElementById('unsavedChangesModal');
            const cleanUp = (result) => {
                modalEl.remove();
                resolve(result);
            };

            document.getElementById('ucmSaveBtn').onclick = () => cleanUp('save');
            document.getElementById('ucmDiscardBtn').onclick = () => cleanUp('discard');
            document.getElementById('ucmCancelBtn').onclick = () => cleanUp('cancel');
            document.getElementById('ucmCloseBtn').onclick = () => cleanUp('cancel');
        });
    }
};

window.FormManager = FormManager;
window.NavigationGuard = NavigationGuard;
