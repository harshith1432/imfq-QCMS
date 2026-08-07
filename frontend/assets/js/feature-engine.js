/**
 * QCMS Feature Engine Client Library
 * ===================================
 * Centralized feature flag evaluation and DOM control for the frontend application.
 * Features:
 *  - Cached flag evaluation via /api/feature-engine/flags
 *  - Real-time live hot-reload via SSE stream (/api/feature-engine/stream)
 *  - Automatic DOM toggling for elements with data-feature="module.code"
 *  - Async and Sync feature checks
 *  - Usage tracking
 */

class FeatureEngineClient {
    constructor() {
        this.flags = {};
        this.moduleDetails = {};
        this.initialized = false;
        this.sse = null;
        this.listeners = [];
    }

    /**
     * Initializes the FeatureEngine by fetching flags and starting SSE listener.
     */
    async init() {
        if (this.initialized) return;
        await this.loadFlags();
        this.startSSE();
        this.applyAll();
        this.initialized = true;
        console.log('[FeatureEngine] Initialized with', Object.keys(this.flags).length, 'modules.');
    }

    /**
     * Fetches current feature flags from server.
     */
    async loadFlags() {
        try {
            const token = sessionStorage.getItem('token') || localStorage.getItem('token') || localStorage.getItem('access_token');
            const headers = {};
            if (token) headers['Authorization'] = `Bearer ${token}`;

            const res = await fetch('/api/feature-engine/flags', { headers });
            const data = await res.json();

            if (data.status === 'success' && data.flags) {
                this.flags = data.flags;
                this.moduleDetails = data.details || {};
            }
        } catch (err) {
            console.warn('[FeatureEngine] Failed to load flags:', err);
        }
    }

    getModuleDetails(moduleCode) {
        if (!moduleCode) return {};
        if (this.moduleDetails[moduleCode]) return this.moduleDetails[moduleCode];

        const lowerCode = moduleCode.trim().toLowerCase();
        for (const [k, d] of Object.entries(this.moduleDetails)) {
            if (k.toLowerCase() === lowerCode || (d.name && d.name.toLowerCase() === lowerCode)) {
                return d;
            }
        }

        if (window.QCMS_MODULE_MAP && window.QCMS_MODULE_MAP.findByName) {
            const resolvedCode = window.QCMS_MODULE_MAP.findByName(moduleCode);
            if (resolvedCode && this.moduleDetails[resolvedCode]) {
                return this.moduleDetails[resolvedCode];
            }
        }
        return {};
    }

    /**
     * Checks if a module is enabled (Synchronous, uses cached flags).
     * @param {string} moduleCode 
     * @returns {boolean}
     */
    isEnabled(moduleCode) {
        if (!moduleCode) return true;
        if (Object.keys(this.flags).length === 0) return true; // Fallback before init

        if (this.flags[moduleCode] !== undefined) {
            return this.flags[moduleCode] !== false;
        }

        const lowerCode = moduleCode.trim().toLowerCase();
        for (const k of Object.keys(this.flags)) {
            if (k.toLowerCase() === lowerCode) {
                return this.flags[k] !== false;
            }
        }

        if (window.QCMS_MODULE_MAP && window.QCMS_MODULE_MAP.findByName) {
            const resolvedCode = window.QCMS_MODULE_MAP.findByName(moduleCode);
            if (resolvedCode && this.flags[resolvedCode] !== undefined) {
                return this.flags[resolvedCode] !== false;
            }
        }

        return true; // Allow by default if not explicitly disabled
    }

    /**
     * Checks if a module is enabled (Async, re-fetches if not loaded).
     * @param {string} moduleCode 
     * @returns {Promise<boolean>}
     */
    async isEnabledAsync(moduleCode) {
        if (!this.initialized) await this.init();
        return this.isEnabled(moduleCode);
    }

    /**
     * Applies visibility state across the entire document for all elements tagged with [data-feature].
     */
    applyAll() {
        // Super Admin control panel must NOT hide or disable Super Admin interface elements!
        if (window.location.pathname.includes('/admin/super-admin.html')) return;

        // 0. Check current page route access
        this.checkCurrentPageAccess();

        // 1. Tagged elements with [data-feature]
        const elements = document.querySelectorAll('[data-feature]');
        elements.forEach(el => {
            const code = el.getAttribute('data-feature');
            if (code) {
                const enabled = this.isEnabled(code);
                this.toggleElement(el, enabled, code);
            }
        });

        // 2. Sidebar Navigation Links mapped via QCMS_MODULE_MAP or href
        const sidebarLinks = document.querySelectorAll('.sidebar-link');
        sidebarLinks.forEach(link => {
            const href = link.getAttribute('href');
            if (!href || href === '#' || href.includes('logout')) return;

            let moduleCode = link.getAttribute('data-feature');
            if (!moduleCode && window.QCMS_MODULE_MAP) {
                moduleCode = window.QCMS_MODULE_MAP.findByRoute(href);
            }

            if (moduleCode && this.flags[moduleCode] === false) {
                const details = this.moduleDetails[moduleCode] || {};
                const isUpgrade = details.reason === 'upgrade_required';
                
                link.classList.add(isUpgrade ? 'feature-upgrade-required' : 'feature-under-maintenance');
                link.style.opacity = '0.55';
                link.title = isUpgrade 
                    ? `Upgrade your plan to continue with this module.`
                    : 'This module is temporarily disabled. Please contact the Support team to enable this.';
                
                if (!link.getAttribute('data-maintenance-bound')) {
                    link.setAttribute('data-maintenance-bound', 'true');
                    link.addEventListener('click', (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        this.showDisabledModuleNotice(moduleCode);
                    });
                }
            }
        });

        // 3. Elements mapped via QCMS_MODULE_MAP
        if (window.QCMS_MODULE_MAP && this.flags) {
            Object.keys(this.flags).forEach(code => {
                if (this.flags[code] === false) {
                    const mod = window.QCMS_MODULE_MAP[code];
                    if (mod && mod.selectors) {
                        mod.selectors.forEach(sel => {
                            try {
                                document.querySelectorAll(sel).forEach(el => {
                                    this.toggleElement(el, false, code);
                                });
                            } catch(e) {}
                        });
                    }
                }
            });
        }
    }

    /**
     * Toggles a single DOM element's visibility and accessibility.
     */
    toggleElement(el, enabled, moduleCode = '') {
        if (enabled) {
            el.style.display = '';
            el.removeAttribute('disabled');
            el.classList.remove('feature-disabled', 'd-none-feature');
            if (el.tagName === 'A' || el.tagName === 'BUTTON') {
                el.style.pointerEvents = '';
                el.style.opacity = '';
            }
        } else {
            el.setAttribute('disabled', 'true');
            el.classList.add('feature-disabled');
            el.style.opacity = '0.45';
            el.style.pointerEvents = 'auto'; // allow click to show notice modal
            el.style.cursor = 'not-allowed';
            if (el.tagName === 'A' || el.tagName === 'BUTTON' || el.classList.contains('clickable')) {
                if (!el.getAttribute('data-maintenance-bound')) {
                    el.setAttribute('data-maintenance-bound', 'true');
                    el.addEventListener('click', (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        const code = moduleCode || el.getAttribute('data-feature') || '';
                        this.showDisabledModuleNotice(code);
                    });
                }
            }
        }
    }

    /**
     * Displays warning modal when user attempts to access a disabled module or one requiring a plan upgrade.
     */
    showDisabledModuleNotice(moduleCode) {
        const details = this.getModuleDetails(moduleCode);
        const modName = details.name || ((window.QCMS_MODULE_MAP && window.QCMS_MODULE_MAP[moduleCode]) 
            ? window.QCMS_MODULE_MAP[moduleCode].name 
            : (moduleCode || 'This module'));
        const reason = details.reason || 'disabled';
        const requiredPlan = details.required_plan || 'Professional';
        const isUpgrade = reason === 'upgrade_required';

        let modal = document.getElementById('qcmsDisabledModuleModal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'qcmsDisabledModuleModal';
            modal.className = 'modal fade';
            modal.tabIndex = -1;
            modal.setAttribute('aria-hidden', 'true');
            document.body.appendChild(modal);
        }

        const iconName = isUpgrade ? 'sparkles' : 'lock';
        const iconColor = isUpgrade ? '#6366f1' : '#d97706';
        const iconBg = isUpgrade ? 'rgba(99, 102, 241, 0.12)' : 'rgba(245, 158, 11, 0.12)';
        const iconBorder = isUpgrade ? 'rgba(99, 102, 241, 0.3)' : 'rgba(245, 158, 11, 0.3)';
        const alertBg = isUpgrade ? 'rgba(99, 102, 241, 0.08)' : 'rgba(245, 158, 11, 0.08)';

        const titleText = isUpgrade ? `Upgrade Plan to Access ${modName}` : `${modName} Disabled`;
        const bodyText = isUpgrade 
            ? `Upgrade your plan to continue with this module. To use this feature, please upgrade to the <strong>${requiredPlan}</strong> plan.`
            : `This module is under maintenance. Please contact the Support team to enable this.`;
        const actionBtn = isUpgrade 
            ? `<a href="/admin/subscriptions.html" class="ds-btn ds-btn-primary btn-sm px-4">Upgrade Plan</a>`
            : `<a href="/admin/settings.html?tab=support" class="ds-btn ds-btn-primary btn-sm px-4">Contact Support Team</a>`;

        modal.innerHTML = `
            <div class="modal-dialog modal-dialog-centered" style="max-width: 460px;">
                <div class="modal-content border-0 shadow-lg" style="border-radius: 16px; overflow: hidden; background: var(--ds-surface, #ffffff);">
                    <div class="modal-body p-4 text-center">
                        <div class="rounded-circle d-inline-flex align-items-center justify-content-center mb-3" style="width: 64px; height: 64px; background: ${iconBg}; border: 1.5px solid ${iconBorder};">
                            <i data-lucide="${iconName}" style="width: 32px; height: 32px; color: ${iconColor}; stroke-width: 2.2;"></i>
                        </div>
                        <h5 class="fw-bold text-main mb-2">${titleText}</h5>
                        <div class="alert border-0 p-3 mb-3 text-start" style="background: ${alertBg}; border-radius: 10px;">
                            <div class="d-flex gap-2 align-items-start">
                                <i data-lucide="${isUpgrade ? 'info' : 'alert-triangle'}" style="width: 18px; height: 18px; color: ${iconColor}; flex-shrink: 0;" class="mt-0.5"></i>
                                <span class="text-xs text-secondary fw-semibold">
                                    ${bodyText}
                                </span>
                            </div>
                        </div>
                        <div class="d-flex justify-content-center gap-2">
                            <button type="button" class="ds-btn ds-btn-secondary btn-sm px-4" data-bs-dismiss="modal">Close</button>
                            ${actionBtn}
                        </div>
                    </div>
                </div>
            </div>
        `;

        if (window.lucide) lucide.createIcons();

        if (window.bootstrap && window.bootstrap.Modal) {
            const bsModal = window.bootstrap.Modal.getOrCreateInstance(modal);
            bsModal.show();
        } else {
            alert(bodyText.replace(/<[^>]*>?/gm, ''));
        }
    }

    /**
     * Checks if current page route belongs to a disabled module.
     */
    checkCurrentPageAccess() {
        if (window.location.pathname.includes('/admin/super-admin.html')) return;

        const path = window.location.pathname;
        if (!window.QCMS_MODULE_MAP) return;

        const moduleCode = window.QCMS_MODULE_MAP.findByRoute(path);
        if (moduleCode && this.isEnabled(moduleCode) === false) {
            this.renderPageDisabledOverlay(moduleCode);
        }
    }

    /**
     * Renders full page warning overlay if user directly navigates to a disabled module page.
     */
    renderPageDisabledOverlay(moduleCode) {
        const details = this.getModuleDetails(moduleCode);
        const modName = details.name || ((window.QCMS_MODULE_MAP && window.QCMS_MODULE_MAP[moduleCode])
            ? window.QCMS_MODULE_MAP[moduleCode].name
            : 'This module');
        const reason = details.reason || 'disabled';
        const requiredPlan = details.required_plan || 'Professional';
        const isUpgrade = reason === 'upgrade_required';

        let overlay = document.getElementById('qcmsPageDisabledOverlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'qcmsPageDisabledOverlay';
            overlay.style.cssText = 'position: fixed; inset: 0; background: var(--ds-surface, #ffffff); z-index: 99999; display: flex; align-items: center; justify-content: center; padding: 2rem;';

            const title = isUpgrade ? `Upgrade Plan Required for ${modName}` : `${modName} Temporarily Disabled`;
            const msg = isUpgrade 
                ? `Upgrade your plan to continue with this module. To use this feature, please upgrade to the ${requiredPlan} plan.`
                : `This module is under maintenance. Please contact the Support team to enable this.`;
            const actionBtn = isUpgrade 
                ? `<a href="/admin/subscriptions.html" class="ds-btn ds-btn-primary">Upgrade Plan</a>`
                : `<a href="/admin/settings.html?tab=support" class="ds-btn ds-btn-primary">Contact Support Team</a>`;

            overlay.innerHTML = `
                <div class="text-center p-5 rounded-4 shadow-lg border" style="max-width: 520px; background: var(--ds-surface-raised, #ffffff); border-color: ${isUpgrade ? 'rgba(99, 102, 241, 0.3)' : 'rgba(245, 158, 11, 0.3)'} !important;">
                    <div class="rounded-circle d-inline-flex align-items-center justify-content-center mb-4" style="width: 72px; height: 72px; background: ${isUpgrade ? 'rgba(99, 102, 241, 0.12)' : 'rgba(245, 158, 11, 0.12)'}; border: 1.5px solid ${isUpgrade ? 'rgba(99, 102, 241, 0.3)' : 'rgba(245, 158, 11, 0.3)'};">
                        <i data-lucide="${isUpgrade ? 'sparkles' : 'shield-alert'}" style="width: 38px; height: 38px; color: ${isUpgrade ? '#6366f1' : '#d97706'}; stroke-width: 2.2;"></i>
                    </div>
                    <h4 class="fw-bold text-main mb-2">${title}</h4>
                    <p class="text-secondary text-sm mb-4">
                        ${msg}
                    </p>
                    <div class="d-flex justify-content-center gap-3">
                        <button type="button" class="ds-btn ds-btn-secondary" onclick="window.history.back()">Go Back</button>
                        ${actionBtn}
                    </div>
                </div>
            `;
            document.body.appendChild(overlay);
            if (window.lucide) lucide.createIcons();
        }
    }

    /**
     * Connects to SSE endpoint for instantaneous hot-reloading when Super Admin changes a module status.
     */
    startSSE() {
        if (this.sse) return;
        try {
            this.sse = new EventSource('/api/feature-engine/stream');

            this.sse.addEventListener('module_changed', (e) => {
                try {
                    const data = JSON.parse(e.data);
                    if (data.code) {
                        this.flags[data.code] = data.enabled;
                        console.log(`[FeatureEngine] Hot reload event: '${data.code}' is now ${data.enabled ? 'ENABLED' : 'DISABLED'}`);
                        this.applyAll();
                        this.notifyListeners(data.code, data.enabled);
                    }
                } catch (err) {
                    console.error('[FeatureEngine] SSE parse error:', err);
                }
            });

            this.sse.onerror = () => {
                // EventSource auto-reconnects
            };
        } catch (err) {
            console.warn('[FeatureEngine] SSE initialization failed:', err);
        }
    }

    /**
     * Registers a callback for module state changes.
     */
    onChange(callback) {
        this.listeners.push(callback);
    }

    notifyListeners(code, enabled) {
        this.listeners.forEach(cb => {
            try { cb(code, enabled); } catch (e) {}
        });
    }

    /**
     * Tracks frontend user actions or page views.
     */
    trackUsage(moduleCode, eventType = 'action') {
        if (!moduleCode) return;
        try {
            const token = sessionStorage.getItem('token') || localStorage.getItem('token');
            fetch('/api/feature-engine/track-usage', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': token ? `Bearer ${token}` : ''
                },
                body: JSON.stringify({ module_code: moduleCode, event_type: eventType })
            }).catch(() => {});
        } catch (e) {}
    }
}

// Global Singleton
window.FeatureEngine = new FeatureEngineClient();

// Auto-initialize on DOMReady
document.addEventListener('DOMContentLoaded', () => {
    window.FeatureEngine.init();
});
