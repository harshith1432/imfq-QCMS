/**
 * OctaQube Enterprise - Shared UI Components
 * v1.0 - Handle sidebars, navbars, and role-based UI logic.
 */

// Auto-load FeatureEngine client and module map if not already present
(function loadFeatureEngine() {
    if (!window.OctaQube_MODULE_MAP && !window.QCMS_MODULE_MAP) {
        const s1 = document.createElement('script');
        s1.src = '/assets/js/module-map.js';
        document.head.appendChild(s1);
    }
    if (!window.FeatureEngine) {
        const s2 = document.createElement('script');
        s2.src = '/assets/js/feature-engine.js';
        document.head.appendChild(s2);
    }
})();

// Global Helper: Format mandatory labels with bright red asterisk (<span class="text-danger">*</span>)
window.ensureRedAsterisksOnLabels = function(targetContainer) {
    try {
        const scope = targetContainer || document;
        scope.querySelectorAll('label, .ds-label, .form-label').forEach(label => {
            const cardParent = label.closest('[data-required="false"], [data-applicable="false"]');
            if (cardParent) {
                // Inside an optional or not-applicable section - strip asterisks
                label.querySelectorAll('.text-danger, .required-star').forEach(s => s.remove());
                return;
            }
            if (label.querySelector('.text-danger') || label.querySelector('.required-star')) return;
            let html = label.innerHTML;
            if (/\s*\*\s*$/.test(html)) {
                label.innerHTML = html.replace(/\s*\*\s*$/, ' <span class="text-danger" style="color: #ef4444 !important; font-weight: bold; margin-left: 2px;">*</span>');
            } else {
                const inputId = label.getAttribute('for');
                let input = inputId ? scope.querySelector('#' + inputId) : null;
                if (!input) {
                    const parentField = label.closest('.ds-field, .col-md-12, .col-md-6, .col-md-4, .col-md-3, .col-12, div');
                    if (parentField) {
                        input = parentField.querySelector('input:not([type="hidden"]), select, textarea');
                    }
                }
                if (input && input.hasAttribute('required') && input.type !== 'file') {
                    label.innerHTML = html.trim() + ' <span class="text-danger" style="color: #ef4444 !important; font-weight: bold; margin-left: 2px;">*</span>';
                }
            }
        });
    } catch (e) {
        console.warn('Asterisk label formatting error:', e);
    }
};

// Global Helper: Annotate table cells with data-label for responsive stacked mobile cards
window.ensureTableDataLabels = function(targetContainer) {
    try {
        const scope = targetContainer || document;
        const tables = scope.querySelectorAll('table.ds-table, table.table, .table-responsive table, .ds-table-container table');
        tables.forEach(table => {
            if (table.classList.contains('keep-table-layout')) return;
            const headers = Array.from(table.querySelectorAll('thead th, thead td')).map(th => th.textContent.trim());
            if (!headers.length) return;
            table.querySelectorAll('tbody tr').forEach(tr => {
                const cells = tr.querySelectorAll('td');
                cells.forEach((td, idx) => {
                    if (!td.hasAttribute('data-label') && headers[idx]) {
                        td.setAttribute('data-label', headers[idx]);
                    }
                });
            });
        });
    } catch (e) {
        console.debug('Table data-label formatting warning:', e);
    }
};

document.addEventListener('DOMContentLoaded', () => {
    window.ensureRedAsterisksOnLabels();
    window.ensureTableDataLabels();
    if (window.OctaQube && typeof window.OctaQube.setActiveLink === 'function') {
        window.OctaQube.setActiveLink();
    }
    setInterval(() => {
        window.ensureRedAsterisksOnLabels();
        window.ensureTableDataLabels();
        if (window.OctaQube && typeof window.OctaQube.setActiveLink === 'function') {
            window.OctaQube.setActiveLink();
        }
    }, 1500);
});

/**
 * Theme Manager Integration
 */
const DEFAULT_PALETTES = {
    light: {
        primary_color: '#002347',
        secondary_color: '#476585',
        accent_color: '#C4A25A',
        gold_hover: '#AC8839',
        violet_color: '#4809BD',
        success_color: '#10B981',
        warning_color: '#C4A25A',
        danger_color: '#ef4444'
    },
    dark: {
        primary_color: '#C4A25A',
        secondary_color: '#DAE0E7',
        accent_color: '#C4A25A',
        gold_hover: '#AC8839',
        violet_color: '#4809BD',
        success_color: '#10B981',
        warning_color: '#C4A25A',
        danger_color: '#ef4444'
    }
};

class ThemeManager {
    constructor() {
        this.theme = this.getSavedTheme();
        this.init();
    }

    getStorageKey() {
        try {
            const userStr = sessionStorage.getItem('user') || localStorage.getItem('user');
            if (userStr) {
                const u = JSON.parse(userStr);
                const uid = u.id || u.user_id;
                if (uid) return `octaqube-theme-user-${uid}`;
                const role = (u.role && typeof u.role === 'object') ? u.role.name : u.role;
                if (role) return `octaqube-theme-role-${String(role).toLowerCase().replace(/\s+/g, '_')}`;
            }
        } catch(e) {}
        return 'octaqube-theme';
    }

    getSavedTheme() {
        const userKey = this.getStorageKey();
        const userSaved = localStorage.getItem(userKey) || localStorage.getItem(userKey.replace('octaqube-', 'qcms-'));
        if (userSaved) return userSaved;
        return localStorage.getItem('octaqube-theme') || localStorage.getItem('qcms-theme') || 'light';
    }

    init() {
        this.applyTheme(this.theme);

        // Match system preference if not set for this user
        const userKey = this.getStorageKey();
        if (!localStorage.getItem(userKey)) {
            const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)');
            if (systemPrefersDark.matches) {
                this.applyTheme('dark');
            }
            systemPrefersDark.addEventListener('change', e => {
                if (!localStorage.getItem(this.getStorageKey())) {
                    this.applyTheme(e.matches ? 'dark' : 'light');
                }
            });
        }
    }

    _hexToRgb(hex) {
        if (!hex) return null;
        let c = hex.replace('#', '').trim();
        if (c.length === 3) c = c.split('').map(x => x + x).join('');
        const num = parseInt(c, 16);
        return isNaN(num) ? null : `${(num >> 16) & 255}, ${(num >> 8) & 255}, ${num & 255}`;
    }

    applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        const userKey = this.getStorageKey();
        localStorage.setItem(userKey, theme);
        localStorage.setItem('theme', theme);
        this.theme = theme;

        // Apply mode-isolated palette colors
        this.applyModePalette(theme);

        // Broadcast theme change to all child iframes (e.g. Global Stage Templates)
        document.querySelectorAll('iframe').forEach(iframe => {
            try {
                if (iframe.contentWindow) {
                    iframe.contentWindow.postMessage({ type: 'THEME_CHANGED', theme: theme }, '*');
                }
                if (iframe.contentDocument && iframe.contentDocument.documentElement) {
                    iframe.contentDocument.documentElement.setAttribute('data-theme', theme);
                }
            } catch (e) {}
        });

        // Dispatch event
        window.dispatchEvent(new CustomEvent('octaqube-theme-change', { detail: { theme } }));
        window.dispatchEvent(new CustomEvent('qcms-theme-change', { detail: { theme } }));

        // Dynamic favicon or meta updates could go here
        if (window.lucide) lucide.createIcons();
    }

    applyModePalette(theme) {
        const root = document.documentElement;
        // Cleanly reset inline color overrides so default stylesheets don't get polluted across modes
        const colorVars = [
            '--ds-primary', '--ds-accent', '--primary', '--bs-primary',
            '--ds-primary-rgb', '--ds-accent-rgb', '--primary-rgb',
            '--ds-text-secondary', '--ds-gray-rgb',
            '--ds-accent-highlight', '--accent',
            '--ds-green-rgb', '--ds-orange-rgb', '--ds-red-rgb'
        ];
        colorVars.forEach(v => root.style.removeProperty(v));

        let brandConfig = {};
        try {
            brandConfig = JSON.parse(localStorage.getItem('octaqube_branding_config') || '{}');
        } catch (e) {}

        const activeMode = theme || this.theme || 'light';
        let modePalette = null;
        if (brandConfig[activeMode] && typeof brandConfig[activeMode] === 'object') {
            modePalette = brandConfig[activeMode];
        } else if (brandConfig.primary_color && !brandConfig.light && !brandConfig.dark) {
            // Backward compatibility for flat legacy configs
            modePalette = brandConfig;
        }

        if (modePalette) {
            if (modePalette.primary_color) {
                const rgb = this._hexToRgb(modePalette.primary_color);
                root.style.setProperty('--ds-primary', modePalette.primary_color);
                root.style.setProperty('--ds-accent', modePalette.primary_color);
                root.style.setProperty('--primary', modePalette.primary_color);
                root.style.setProperty('--bs-primary', modePalette.primary_color);
                if (rgb) {
                    root.style.setProperty('--ds-primary-rgb', rgb);
                    root.style.setProperty('--ds-accent-rgb', rgb);
                    root.style.setProperty('--primary-rgb', rgb);
                }
            }
            if (modePalette.secondary_color) {
                root.style.setProperty('--ds-text-secondary', modePalette.secondary_color);
                const rgb = this._hexToRgb(modePalette.secondary_color);
                if (rgb) root.style.setProperty('--ds-gray-rgb', rgb);
            }
            if (modePalette.accent_color) {
                root.style.setProperty('--ds-accent-highlight', modePalette.accent_color);
                root.style.setProperty('--accent', modePalette.accent_color);
            }
            if (modePalette.success_color) {
                const rgb = this._hexToRgb(modePalette.success_color);
                if (rgb) root.style.setProperty('--ds-green-rgb', rgb);
            }
            if (modePalette.warning_color) {
                const rgb = this._hexToRgb(modePalette.warning_color);
                if (rgb) root.style.setProperty('--ds-orange-rgb', rgb);
            }
            if (modePalette.danger_color) {
                const rgb = this._hexToRgb(modePalette.danger_color);
                if (rgb) root.style.setProperty('--ds-red-rgb', rgb);
            }
        }

        // Global font and border radius
        const globalBrand = brandConfig.global || brandConfig;
        if (globalBrand.font_family) {
            const fontStack = globalBrand.font_family === 'Roboto'
                ? `'Roboto', system-ui, sans-serif`
                : globalBrand.font_family === 'Outfit'
                ? `'Outfit', 'Inter', system-ui, sans-serif`
                : `'Inter', system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`;
            root.style.setProperty('--ds-font-body', fontStack);
            root.style.setProperty('--ds-font-heading', fontStack);
            root.style.setProperty('--ds-font-title', fontStack);
        }
        if (globalBrand.border_radius) {
            root.style.setProperty('--ds-radius-lg', globalBrand.border_radius);
            const num = parseInt(globalBrand.border_radius);
            if (!isNaN(num)) {
                root.style.setProperty('--ds-radius-md', `${Math.max(6, num - 4)}px`);
                root.style.setProperty('--ds-radius-sm', `${Math.max(4, num - 8)}px`);
            }
        }
    }

    toggle() {
        const newTheme = this.theme === 'light' ? 'dark' : 'light';
        this.applyTheme(newTheme);
        return newTheme;
    }
}
window.DEFAULT_PALETTES = DEFAULT_PALETTES;
window.themeManager = new ThemeManager();

/**
 * UI Utilities & Core Logic
 */
const OctaQube = {
    user: null,
    perms: {
        'SuperAdmin': { canCreate: true, canValidate: true, canApprove: true, isAdmin: true, isSuperAdmin: true },
        'Admin': { canCreate: true, canValidate: true, canApprove: true, isAdmin: true },
        'Team Leader': { canCreate: true, canValidate: false, canApprove: false, isAdmin: false },
        'Facilitator': { canCreate: false, canValidate: true, canApprove: false, isAdmin: false },
        'Reviewer': { canCreate: false, canValidate: false, canApprove: true, isAdmin: false },
        'Team Member': { canCreate: false, canValidate: false, canApprove: false, isAdmin: false },
        'CEO': { canCreate: false, canValidate: false, canApprove: false, isAdmin: false, isCEO: true }
    },

    renderPagination(page, totalPages, onClickFnName = 'Users.loadUsers') {
        if (totalPages <= 1) return '';
        let pages = [];
        if (totalPages <= 5) {
            for (let i = 1; i <= totalPages; i++) pages.push(i);
        } else {
            pages.push(1);
            let start = Math.max(2, page - 1);
            let end = Math.min(totalPages - 1, page + 1);

            if (page <= 3) {
                start = 2;
                end = 4;
            } else if (page >= totalPages - 2) {
                start = totalPages - 3;
                end = totalPages - 1;
            }

            if (start > 2) {
                pages.push('...');
            }

            for (let i = start; i <= end; i++) {
                pages.push(i);
            }

            if (end < totalPages - 1) {
                pages.push('...');
            }

            pages.push(totalPages);
        }

        return pages.map(p => {
            if (p === '...') {
                return `<span class="px-1 text-xs text-muted fw-bold d-inline-flex align-items-center" style="user-select: none;">...</span>`;
            }
            return `
                <button class="ds-btn ds-btn-sm ${p === page ? 'ds-btn-primary' : 'ds-btn-ghost'}" style="min-width: 32px; height: 32px; padding: 0;" onclick="${onClickFnName}(${p})">
                    ${p}
                </button>
            `;
        }).join('');
    },

    normalizeRole(role) {
        if (!role) return 'Team Member';
        let roleStr = role;
        if (typeof role === 'object') {
            roleStr = role.name || role.role_name || role.role || '';
        }
        if (!roleStr || typeof roleStr !== 'string') return 'Team Member';
        const r = roleStr.trim().toLowerCase();
        if (r === 'superadmin' || r === 'super admin' || r === 'super_admin') return 'SuperAdmin';
        if (r === 'admin') return 'Admin';
        if (r === 'team leader' || r === 'teamleader' || r === 'team_leader') return 'Team Leader';
        if (r === 'team member' || r === 'teammember' || r === 'team_member') return 'Team Member';
        if (r === 'facilitator') return 'Facilitator';
        if (r === 'reviewer') return 'Reviewer';
        if (r === 'ceo') return 'CEO';
        return roleStr;
    },

    getDashboardUrl(role) {
        const norm = this.normalizeRole(role || (this.user && this.user.role));
        if (norm === 'SuperAdmin') return '/admin/super-admin.html';
        if (norm === 'Admin' || norm === 'CEO') return '/dashboard/dashboard-admin.html';
        if (norm === 'Facilitator') return '/dashboard/dashboard-facilitator.html';
        if (norm === 'Reviewer') return '/dashboard/dashboard-reviewer.html';
        if (norm === 'Team Leader') return '/dashboard/dashboard-team-member.html';
        if (norm === 'Team Member') return '/dashboard/dashboard-team-member.html';
        return '/dashboard/dashboard-team-member.html';
    },

    isModuleAllowed(roleName, moduleKey) {
        try {
            const userStr = sessionStorage.getItem('user') || localStorage.getItem('user');
            const user = userStr ? JSON.parse(userStr) : {};
            const perms = user.role_permissions || JSON.parse(sessionStorage.getItem('role_permissions') || localStorage.getItem('role_permissions') || 'null');
            
            let normRole = roleName || user.role;
            if (typeof normRole === 'object') normRole = normRole.name || '';
            
            normRole = (normRole === 'Team Leader' || normRole === 'teamleader' || normRole === 'team_leader') ? 'Team Member' :
                       (normRole === 'Facilitator' || normRole === 'facilitator') ? 'Facilitator' :
                       (normRole === 'Reviewer' || normRole === 'reviewer') ? 'Reviewer' :
                       (normRole === 'CEO' || normRole === 'ceo') ? 'CEO' :
                       (normRole === 'Admin' || normRole === 'admin' || normRole === 'SuperAdmin') ? 'Admin' :
                       'Team Member';

            // Immutable safeguard: Admin and SuperAdmin must always have access to settings
            if ((normRole === 'Admin' || normRole === 'SuperAdmin') && moduleKey === 'settings') {
                return true;
            }
                       
            if (perms && perms[normRole] && typeof perms[normRole][moduleKey] === 'boolean') {
                return perms[normRole][moduleKey];
            }

            // Default rules: Project Repository is hidden by default for CEO, Facilitator, and Reviewer
            if (moduleKey === 'project_repo' && ['CEO', 'Facilitator', 'Reviewer'].includes(normRole)) {
                return false;
            }
        } catch (e) {
            console.warn('RBAC check error:', e);
        }
        return true;
    },

    isPublicOrAuthPage() {
        const path = (window.location.pathname || '').toLowerCase();
        const rawPage = path.split('/').pop() || 'index.html';
        const page = rawPage.split('?')[0].split('#')[0].toLowerCase();
        const publicPages = [
            'login.html',
            'login',
            'register.html',
            'register',
            'register-org.html',
            'register-org',
            'forgot-password.html',
            'forgot-password',
            'reset-password.html',
            'reset-password',
            'verify-email.html',
            'verify-email',
            'accept-invite.html',
            'accept-invite',
            'maintenance.html',
            'maintenance'
        ];
        return (
            path === '/' ||
            path === '' ||
            page === 'index.html' ||
            page === '' ||
            publicPages.includes(page)
        );
    },

    init() {
        if (typeof document !== 'undefined' && document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.init());
            return;
        }

        // If this is a public landing or auth page, never render authenticated shell elements
        if (this.isPublicOrAuthPage()) {
            const nav = document.getElementById('octaqube-mobile-bottom-nav');
            if (nav) nav.remove();
            const sidebar = document.getElementById('app-sidebar');
            if (sidebar) sidebar.remove();
            const navbar = document.getElementById('app-navbar');
            if (navbar) navbar.remove();
            const aiW = document.getElementById('ai-chat-widget');
            if (aiW) aiW.remove();
            const hdW = document.getElementById('helpdesk-widget');
            if (hdW) hdW.remove();
            const backdrop = document.getElementById('sidebar-backdrop');
            if (backdrop) backdrop.remove();
            document.body.classList.remove('sidebar-mobile-open');

            this.refreshIcons();
            this.applyBranding();
            return;
        }

        const userStr = sessionStorage.getItem('user') || localStorage.getItem('user');
        if (userStr) {
            try {
                this.user = JSON.parse(userStr);
                if (this.user && this.user.role) {
                    this.user.role = this.normalizeRole(this.user.role);
                }
                const synched = JSON.stringify(this.user);
                sessionStorage.setItem('user', synched);
                localStorage.setItem('user', synched);
            } catch (e) {
                console.error("Failed to parse user session:", e);
                this.logout();
                return;
            }
        }

        if (!this.user && !this.isPublicOrAuthPage()) {
            const path = window.location.pathname.toLowerCase();
            const fallbackRole = path.includes('super-admin') ? 'SuperAdmin' :
                                 (path.includes('/admin/') ? 'Admin' : 'Team Member');
            this.user = {
                id: 'active_session',
                full_name: 'Enterprise User',
                role: fallbackRole,
                org_name: 'OctaQube Enterprise',
                email: 'user@octaqube.io'
            };
        }

        // Centralized Lucide config for premium look
        this.refreshIcons();

        // Apply white labeling / custom branding globally (from cached session)
        this.applyBranding();

        // Detect layout mode (Mobile vs Desktop) and render bottom nav
        this.updateLayoutMode();
        if (!this._resizeBound) {
            this._resizeBound = true;
            window.addEventListener('resize', () => {
                clearTimeout(this._resizeDebounce);
                this._resizeDebounce = setTimeout(() => {
                    this.updateLayoutMode();
                }, 100);
            });
        }

        // Global Top-Layer Dropdown Stacking Handler for Tables & Cards
        if (!this._dropdownTopLayerBound) {
            this._dropdownTopLayerBound = true;
            document.addEventListener('show.bs.dropdown', (e) => {
                const toggle = e.target;
                const tr = toggle.closest('tr');
                if (tr) {
                    tr.classList.add('dropdown-open');
                    tr.style.setProperty('z-index', '1050', 'important');
                    tr.style.setProperty('position', 'relative', 'important');
                }
                const td = toggle.closest('td');
                if (td) {
                    td.classList.add('dropdown-open');
                    td.style.setProperty('z-index', '1050', 'important');
                    td.style.setProperty('position', 'relative', 'important');
                }
                const menu = toggle.nextElementSibling || (toggle.parentElement ? toggle.parentElement.querySelector('.dropdown-menu') : null);
                if (menu) {
                    menu.style.setProperty('z-index', '100050', 'important');
                    menu.style.setProperty('opacity', '1', 'important');
                }
            });

            document.addEventListener('hidden.bs.dropdown', (e) => {
                const toggle = e.target;
                const tr = toggle.closest('tr');
                if (tr) {
                    tr.classList.remove('dropdown-open');
                    tr.style.removeProperty('z-index');
                    tr.style.removeProperty('position');
                }
                const td = toggle.closest('td');
                if (td) {
                    td.classList.remove('dropdown-open');
                    td.style.removeProperty('z-index');
                    td.style.removeProperty('position');
                }
            });
        }

        // Initialize UI components
        if (this.user) {
            this.renderSidebar();
            this.renderNavbar();
            this.renderMobileBottomNav();
            const isSuperAdminPage = window.location.pathname.includes('super-admin.html') || window.location.href.includes('super-admin.html');
            if (!isSuperAdminPage) {
                this.renderAIChatWidget();
                this.renderHelpdeskWidget();
            } else {
                const aiW = document.getElementById('ai-chat-widget');
                if (aiW) aiW.remove();
                const hdW = document.getElementById('helpdesk-widget');
                if (hdW) hdW.remove();
            }
            this.setupMobileSidebar();
            this.loadUpcomingMeetingsFeed();
            this.loadNotifications();
            if (window.GlobalAnnouncementBanner) {
                window.GlobalAnnouncementBanner.init();
            }
 
            // Check Corporate Profile completion for Organisation Admins
            this.checkProfileCompletion();

            // Async: Fetch fresh branding from server to keep org theme in sync
            // This ensures all org users always see the latest admin-configured colors/logos
            this.syncBrandingFromServer();
        }

        // Listen for theme changes to re-render
        window.addEventListener('octaqube-theme-change', () => {
            if (this.user) {
                this.renderNavbar();
                this.renderMobileBottomNav();
            }
        });

        // Listen for language changes to re-render
        window.addEventListener('octaqube-language-change', () => {
            if (this.user) {
                this.renderSidebar();
                this.renderNavbar();
            }
        });

        // Impersonation banner check
        if (sessionStorage.getItem('super_admin_backup_token')) {
            this.renderImpersonationBanner();
        }
    },

    renderImpersonationBanner() {
        if (document.getElementById('impersonationBanner')) return;
        const banner = document.createElement('div');
        banner.id = 'impersonationBanner';
        banner.style.position = 'fixed';
        banner.style.top = '0';
        banner.style.left = '0';
        banner.style.width = '100%';
        banner.style.height = '40px';
        banner.style.background = 'rgb(var(--ds-orange-rgb))';
        banner.style.color = '#fff';
        banner.style.zIndex = '999999';
        banner.style.display = 'flex';
        banner.style.alignItems = 'center';
        banner.style.justifyContent = 'center';
        banner.style.fontSize = '13px';
        banner.style.fontWeight = 'bold';
        banner.style.boxShadow = '0 2px 10px rgba(0,0,0,0.2)';
        banner.innerHTML = `
            <div class="d-flex align-items-center gap-2">
                <span>⚠️ Impersonating Administrator Context (${this.user ? this.user.org_name : 'Tenant'})</span>
                <button onclick="OctaQube.exitImpersonation()" class="btn btn-sm btn-light py-0 px-2 fw-bold text-xs" style="color:rgb(var(--ds-orange-rgb)); border-radius: 4px; border:none; height:24px; line-height:1;">
                    Return to Super Admin
                </button>
            </div>
        `;
        document.body.appendChild(banner);
        document.body.style.paddingTop = '40px';
    },

    exitImpersonation() {
        sessionStorage.removeItem('super_admin_backup_token');
        sessionStorage.removeItem('user');
        window.location.href = '/admin/super-admin.html';
    },

    async checkProfileCompletion() {
        try {
            if (!this.user) return;
            const roleName = this.normalizeRole(this.user.role?.name || this.user.role || this.user.role_name);
            // Strictly only Organization Administrators should see and act on organization profile completion
            const isOrgAdmin = (roleName === 'Admin') && !this.user.is_super_admin;
            if (!isOrgAdmin) {
                const existing = document.getElementById('org-profile-completion-banner');
                if (existing) existing.remove();
                return;
            }

            // Skip on login page or super-admin portal
            if (window.location.pathname.includes('login.html') || window.location.pathname.includes('super-admin.html')) {
                const existing = document.getElementById('org-profile-completion-banner');
                if (existing) existing.remove();
                return;
            }

            const res = await api.get('/admin/org-settings');
            if (!res) return;

            let comp = res.profile_completion;
            if (!comp) {
                const fields = [
                    { k: 'name', l: 'Legal Entity Name' },
                    { k: 'industry', l: 'Industry Sector' },
                    { k: 'admin_name', l: 'Primary Admin Name' },
                    { k: 'website', l: 'Website URL' },
                    { k: 'email', l: 'Business Email' },
                    { k: 'phone', l: 'Phone Number' },
                    { k: 'gst_number', l: 'GST Number' },
                    { k: 'pan_number', l: 'PAN Number' },
                    { k: 'address', l: 'HQ Address' },
                    { k: 'city', l: 'City' },
                    { k: 'state', l: 'State / Province' },
                    { k: 'country', l: 'Country' },
                    { k: 'zip_code', l: 'ZIP Code' }
                ];
                let filled = 0;
                let missing = [];
                fields.forEach(f => {
                    const v = res[f.k];
                    if (v && String(v).trim() !== '' && String(v).trim() !== 'None' && String(v).trim() !== 'null') {
                        filled++;
                    } else {
                        missing.push(f.l);
                    }
                });
                const total = fields.length;
                const completed_pct = Math.round((filled / total) * 100);
                comp = {
                    completed_pct,
                    pending_pct: 100 - completed_pct,
                    filled_count: filled,
                    total_count: total,
                    is_complete: (completed_pct === 100),
                    missing_fields: missing
                };
            }

            // If Corporate Profile is 100% complete, remove banner if present & do nothing!
            if (comp.is_complete || comp.completed_pct >= 100) {
                const existing = document.getElementById('org-profile-completion-banner');
                if (existing) existing.remove();
                return;
            }

            // Render notification banner
            this.renderProfileCompletionBanner(comp);
        } catch (e) {
            console.warn('Profile completion check warning:', e);
        }
    },

    renderProfileCompletionBanner(comp) {
        if (!this.user) return;
        const roleName = this.normalizeRole(this.user.role?.name || this.user.role || this.user.role_name);
        const isOrgAdmin = (roleName === 'Admin') && !this.user.is_super_admin;
        if (!isOrgAdmin) {
            const existing = document.getElementById('org-profile-completion-banner');
            if (existing) existing.remove();
            return;
        }

        if (document.getElementById('org-profile-completion-banner')) {
            const pctEl = document.getElementById('opc-completed-pct');
            if (pctEl) pctEl.innerText = `${comp.completed_pct}%`;
            const pendEl = document.getElementById('opc-pending-pct');
            if (pendEl) pendEl.innerText = `${comp.pending_pct}% Pending`;
            return;
        }

        const banner = document.createElement('div');
        banner.id = 'org-profile-completion-banner';
        banner.className = 'container-fluid px-2 px-sm-4 pt-2 pb-1';
        banner.innerHTML = `
            <div class="d-flex align-items-center justify-content-between flex-wrap gap-2 px-2.5 px-sm-3 py-1.5 rounded-3 fade-in" style="background: rgba(99,102,241,0.08); border: 1px solid rgba(99,102,241,0.22); font-size: 12px; min-height: 36px;">
                <div class="d-flex align-items-center gap-1.5 gap-sm-2 overflow-hidden flex-grow-1" style="min-width: 0;">
                    <i data-lucide="alert-circle" class="text-warning flex-shrink-0" style="width:14px;height:14px;"></i>
                    <span class="fw-semibold text-main text-truncate" style="font-size:11.5px;">
                        <span class="d-none d-sm-inline">Corporate </span>Profile Incomplete
                    </span>
                    <span class="badge py-0.5 px-1.5 px-sm-2 text-xxs flex-shrink-0" style="background: rgba(245, 158, 11, 0.15); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 12px; font-weight: 600;">
                        <span id="opc-completed-pct">${comp.completed_pct}%</span><span class="d-none d-md-inline"> Complete</span>
                    </span>
                    <span class="text-secondary text-truncate d-none d-lg-inline" style="max-width: 280px; font-size: 11px;">
                        Missing: ${comp.missing_fields.slice(0, 2).join(', ')}${comp.missing_fields.length > 2 ? '...' : ''}
                    </span>
                </div>
                <div class="d-flex align-items-center flex-shrink-0 ms-auto">
                    <a href="/admin/settings.html?tab=profile" class="btn btn-sm btn-primary py-0.5 px-2 px-sm-2.5 text-xs fw-bold d-inline-flex align-items-center gap-1 opc-complete-btn" style="border-radius:6px; font-size:11px; height: 26px; line-height: 1; white-space: nowrap;">
                        <i data-lucide="edit-3" style="width:11px;height:11px;"></i>
                        <span class="d-inline d-sm-none">Complete (${comp.pending_pct}%)</span>
                        <span class="d-none d-sm-inline">Complete Profile (${comp.pending_pct}% Left)</span>
                    </a>
                </div>
            </div>
        `;

        const target = document.querySelector('main') || document.querySelector('.ds-main-content') || document.querySelector('.main-wrapper') || document.querySelector('#app-content');
        if (target) {
            target.insertBefore(banner, target.firstChild);
        } else {
            document.body.insertBefore(banner, document.body.firstChild);
        }

        const completeBtn = banner.querySelector('.opc-complete-btn');
        if (completeBtn) {
            completeBtn.addEventListener('click', (e) => {
                if (window.location.pathname.includes('settings.html')) {
                    e.preventDefault();
                    if (window.settingsManager && typeof window.settingsManager.switchTab === 'function') {
                        window.settingsManager.switchTab('profile');
                    } else {
                        const link = document.querySelector('.sidebar-link[data-target="profile"]');
                        if (link) link.click();
                    }
                    window.scrollTo({ top: 0, behavior: 'smooth' });
                }
            });
        }

        if (window.lucide) lucide.createIcons();
    },

    /**
     * Fetch fresh branding data from /auth/me and update sessionStorage.
     * Called on every page load so org-wide changes are reflected in real time.
     */
    async syncBrandingFromServer() {
        try {
            const currentToken = sessionStorage.getItem('token') || localStorage.getItem('token') || '';
            const headers = {};
            if (currentToken) headers['Authorization'] = `Bearer ${currentToken}`;
            const response = await fetch('/api/auth/me', {
                headers,
                credentials: 'same-origin'
            });
            if (!response.ok) return;

            const profile = await response.json();

            // Update session with latest org branding from server
            const userStr = sessionStorage.getItem('user');
            if (!userStr) return;
            const user = JSON.parse(userStr);
            if (user.username && profile.username && user.username !== profile.username) return;

            let changed = false;
            const brandingFields = [
                'org_primary_color', 'org_logo_url', 'org_favicon_url', 'org_name'
            ];
            for (const field of brandingFields) {
                if (profile[field] !== undefined && user[field] !== profile[field]) {
                    user[field] = profile[field];
                    changed = true;
                }
            }

            if (changed) {
                sessionStorage.setItem('user', JSON.stringify(user));
                this.user = user;
                // Re-apply branding with new values
                this.applyBranding();
                // Re-render sidebar for logo changes
                this.renderSidebar();
            }
        } catch (e) {
            // Silently fail — branding sync is best-effort
            console.debug('[OctaQube] Branding sync skipped:', e.message);
        }
    },

    /**
     * Apply organization's custom branding globally (Colors, Favicon, Logo)
     */
    applyBranding() {
        if (!this.user) return;
        const color = this.user.org_primary_color;
        const faviconUrl = this.user.org_favicon_url;
        const logoUrl = this.user.org_logo_url;

        if (color) {
            // Apply primary color to CSS variables
            document.documentElement.style.setProperty('--ds-primary', color);
            document.documentElement.style.setProperty('--ds-accent', color);

            // Derive a slightly darker shade for hover state
            const hexToRgb = hex => {
                let r=0, g=0, b=0;
                if (hex.length === 4) {
                    r = parseInt(hex[1]+hex[1],16);
                    g = parseInt(hex[2]+hex[2],16);
                    b = parseInt(hex[3]+hex[3],16);
                } else if (hex.length === 7) {
                    r = parseInt(hex.substring(1,3),16);
                    g = parseInt(hex.substring(3,5),16);
                    b = parseInt(hex.substring(5,7),16);
                }
                return { r, g, b, str: `${r}, ${g}, ${b}` };
            };

            if (color.startsWith('#')) {
                const rgb = hexToRgb(color);
                document.documentElement.style.setProperty('--ds-primary-rgb', rgb.str);
                document.documentElement.style.setProperty('--ds-accent-rgb', rgb.str);

                // Derive a slightly darker accent-hover
                const darken = v => Math.max(0, Math.floor(v * 0.8));
                const hoverHex = `#${darken(rgb.r).toString(16).padStart(2,'0')}${darken(rgb.g).toString(16).padStart(2,'0')}${darken(rgb.b).toString(16).padStart(2,'0')}`;
                document.documentElement.style.setProperty('--ds-accent-hover', hoverHex);
            }
        }

        let link = document.querySelector("link[rel~='icon']");
        if (!link) {
            link = document.createElement('link');
            link.rel = 'icon';
            document.getElementsByTagName('head')[0].appendChild(link);
        }
        
        if (faviconUrl) {
            link.href = faviconUrl;
        } else {
            // Default OctaQube Shield Favicon
            link.href = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="%230f172a" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path><path d="m9 12 2 2 4-4"></path></svg>';
        }

        // Update sidebar logo if it's already rendered
        const sidebarBrand = document.querySelector('.sidebar-brand');
        const orgName = (this.user && this.user.org_name) ? this.user.org_name : 'OctaQube';
        if (sidebarBrand) {
            if (logoUrl && logoUrl !== 'null' && logoUrl !== 'None') {
                let img = sidebarBrand.querySelector('img');
                if (!img) {
                    sidebarBrand.innerHTML = `<img src="${logoUrl}" alt="Logo" style="width: 32px; height: 32px; object-fit: contain; border-radius: 8px;">
                                              <div class="brand-text">${OctaQube.escapeHtml(orgName)} <small style="color:var(--ds-accent); opacity:1;">Workspace</small></div>`;
                } else {
                    img.src = logoUrl;
                    const bt = sidebarBrand.querySelector('.brand-text');
                    if (bt) bt.innerHTML = `${OctaQube.escapeHtml(orgName)} <small style="color:var(--ds-accent); opacity:1;">Workspace</small>`;
                }
            } else {
                sidebarBrand.innerHTML = `<div class="brand-icon" style="background: var(--ds-accent);">
                                            <i data-lucide="shield-check" style="color:white;"></i>
                                          </div>
                                          <div class="brand-text">${OctaQube.escapeHtml(orgName)} <small style="color:var(--ds-accent); opacity:1;">Enterprise OS</small></div>`;
                if (window.lucide) lucide.createIcons();
            }
        }

        // Update breadcrumb root text dynamically
        if (window.Breadcrumbs && typeof window.Breadcrumbs.updateOrgName === 'function') {
            window.Breadcrumbs.updateOrgName(orgName);
        } else {
            const rootBreadcrumbs = document.querySelectorAll('.glass-breadcrumb .breadcrumb-item:first-child a, .org-breadcrumb-root');
            if (rootBreadcrumbs.length > 0 && orgName) {
                rootBreadcrumbs.forEach(el => {
                    el.textContent = orgName;
                });
            }
        }
    },

    updateLayoutMode() {
        const isMobile = window.innerWidth <= 768;
        if (isMobile) {
            document.body.classList.add('is-mobile-layout');
            document.body.classList.remove('is-desktop-layout');
        } else {
            document.body.classList.remove('is-mobile-layout');
            document.body.classList.add('is-desktop-layout');
            // Auto close mobile drawer if resized to desktop
            const sidebar = document.getElementById('app-sidebar');
            const backdrop = document.getElementById('sidebar-backdrop');
            if (sidebar) sidebar.classList.remove('show');
            if (backdrop) backdrop.classList.remove('show');
            document.body.classList.remove('sidebar-mobile-open');
        }
        if (this.user && !this.isPublicOrAuthPage()) {
            this.renderMobileBottomNav();
        } else {
            const nav = document.getElementById('octaqube-mobile-bottom-nav');
            if (nav) nav.remove();
        }
        if (window.ensureTableDataLabels) {
            window.ensureTableDataLabels();
        }
    },

    renderMobileBottomNav() {
        if (!this.user || this.isPublicOrAuthPage()) {
            const existingNav = document.getElementById('octaqube-mobile-bottom-nav');
            if (existingNav) existingNav.remove();
            return;
        }

        let nav = document.getElementById('octaqube-mobile-bottom-nav');
        if (window.innerWidth > 768) {
            if (nav) nav.remove();
            return;
        }

        const roleName = this.normalizeRole(this.user.role);
        const currentPath = (window.location.pathname || '').toLowerCase();
        const currentSearch = (window.location.search || '').toLowerCase();
        const urlParams = new URLSearchParams(window.location.search);
        const currentView = (urlParams.get('view') || 'overview').toLowerCase();

        // Unambiguous route matchers to prevent multiple tab highlights
        const isKnowledgeActive = currentPath.includes('repository.html') && !currentPath.includes('projects-repository');
        const isNewProjectActive = currentPath.includes('new-project.html');
        const isProjectsActive = !isKnowledgeActive && !isNewProjectActive && (
            currentPath.includes('projects-repository') ||
            currentPath.includes('workspace') ||
            currentPath.includes('sop-deviation') ||
            currentPath.includes('additional-sources') ||
            (currentPath.includes('/projects/') && !currentPath.includes('repository.html'))
        );
        const isLeaderboardActive = currentPath.includes('leaderboard.html') || currentPath.includes('/rewards/');
        const isProfileActive = currentPath.includes('profile.html') || currentPath.includes('user-profile.html') || currentPath.includes('/auth/profile') || currentPath.includes('/auth/user-profile');
        const isUsersActive = currentPath.includes('users.html') || currentPath.includes('user-management.html') || currentPath.includes('departments.html') || currentPath.includes('plants.html');
        const isAuditLogsActive = currentPath.includes('audit-logs.html') || currentPath.includes('audit_logs');
        const isAnalyticsActive = currentPath.includes('analytics.html') || currentPath.includes('/reports/');
        const isTemplatesActive = currentPath.includes('stage-template.html');
        const isSettingsActive = currentPath.includes('/admin/settings') || currentPath.includes('settings.html');

        let navItems = [];

        if (roleName === 'SuperAdmin') {
            // ── SuperAdmin Platform Owner Bottom Navigation ──
            const isOverviewActive = currentPath.includes('super-admin.html') && (currentView === 'overview' || !window.location.search);
            const isOrgsActive = currentPath.includes('super-admin.html') && currentView === 'organizations';
            const isPlansActive = currentPath.includes('super-admin.html') && (currentView === 'plans' || currentView === 'billing');
            const isLogsActive = currentPath.includes('super-admin.html') && currentView === 'logs';
            const isSASettingsActive = currentPath.includes('super-admin.html') && ['settings', 'doc-identity', 'integrations', 'storage', 'stage-templates', 'stage-weightage', 'recycle-bin'].includes(currentView);

            navItems = [
                {
                    label: 'Dashboard',
                    url: '/admin/super-admin.html',
                    icon: 'layout-dashboard',
                    isActive: isOverviewActive
                },
                {
                    label: 'Orgs',
                    url: '/admin/super-admin.html?view=organizations',
                    icon: 'building-2',
                    isActive: isOrgsActive
                },
                {
                    label: 'Plans',
                    url: '/admin/super-admin.html?view=plans',
                    icon: 'layers',
                    isActive: isPlansActive
                },
                {
                    label: 'Logs',
                    url: '/admin/super-admin.html?view=logs',
                    icon: 'scroll-text',
                    isActive: isLogsActive
                },
                {
                    label: 'Settings',
                    url: '/admin/super-admin.html?view=settings',
                    icon: 'settings-2',
                    isActive: isSASettingsActive
                }
            ];
        } else if (roleName === 'Admin') {
            // ── Organization Administrator ──
            const canProj = this.isModuleAllowed(roleName, 'project_repo');
            const canUsers = this.isModuleAllowed(roleName, 'user_management');
            const canAudits = this.isModuleAllowed(roleName, 'audit_logs');
            const canReports = this.isModuleAllowed(roleName, 'analytics');

            navItems = [
                {
                    label: 'Dashboard',
                    url: '/dashboard/dashboard-admin.html',
                    icon: 'layout-dashboard',
                    isActive: currentPath.includes('dashboard-admin.html') || (currentPath.endsWith('/dashboard/') && !currentPath.includes('reviewer') && !currentPath.includes('facilitator') && !currentPath.includes('team-member'))
                }
            ];
            if (canProj) {
                navItems.push({
                    label: 'Projects',
                    url: '/projects/projects-repository.html',
                    icon: 'folder-kanban',
                    isActive: isProjectsActive
                });
            }
            if (canUsers) {
                navItems.push({
                    label: 'Directory',
                    url: '/admin/users.html',
                    icon: 'users',
                    isActive: isUsersActive
                });
            }
            if (canAudits) {
                navItems.push({
                    label: 'Audit Logs',
                    url: '/admin/audit-logs.html',
                    icon: 'scroll-text',
                    isActive: isAuditLogsActive
                });
            } else if (canReports) {
                navItems.push({
                    label: 'Analytics',
                    url: '/reports/analytics.html',
                    icon: 'bar-chart-3',
                    isActive: isAnalyticsActive
                });
            }
            navItems.push({
                label: 'Settings',
                url: '/admin/settings.html',
                icon: 'settings',
                isActive: isSettingsActive
            });
        } else if (roleName === 'CEO') {
            // ── CEO / Executive ──
            const canReports = this.isModuleAllowed(roleName, 'analytics');
            const canRewards = this.isModuleAllowed(roleName, 'leaderboard');
            const canUsers = this.isModuleAllowed(roleName, 'user_management');

            navItems = [
                {
                    label: 'Executive',
                    url: '/dashboard/dashboard-admin.html',
                    icon: 'layout-dashboard',
                    isActive: currentPath.includes('dashboard-admin.html') || currentPath.includes('dashboard-ceo.html')
                }
            ];
            if (canReports) {
                navItems.push({
                    label: 'Analytics',
                    url: '/reports/analytics.html',
                    icon: 'bar-chart-3',
                    isActive: isAnalyticsActive
                });
            }
            if (canRewards) {
                navItems.push({
                    label: 'Leaderboard',
                    url: '/rewards/leaderboard.html',
                    icon: 'trophy',
                    isActive: isLeaderboardActive
                });
            }
            if (canUsers) {
                navItems.push({
                    label: 'Directory',
                    url: '/admin/users.html',
                    icon: 'users',
                    isActive: isUsersActive
                });
            }
            navItems.push({
                label: 'Profile',
                url: '/auth/profile.html',
                icon: 'user',
                isActive: isProfileActive
            });
        } else if (roleName === 'Reviewer') {
            // ── Stage Reviewer / Approver ──
            const canProj = this.isModuleAllowed(roleName, 'project_repo');
            const canReports = this.isModuleAllowed(roleName, 'analytics');

            navItems = [
                {
                    label: 'Dashboard',
                    url: '/dashboard/dashboard-reviewer.html',
                    icon: 'layout-dashboard',
                    isActive: currentPath.includes('dashboard-reviewer.html')
                }
            ];
            if (canProj) {
                navItems.push({
                    label: 'Projects',
                    url: '/projects/projects-repository.html',
                    icon: 'folder-kanban',
                    isActive: isProjectsActive
                });
            }
            if (canReports) {
                navItems.push({
                    label: 'Analytics',
                    url: '/reports/analytics.html',
                    icon: 'bar-chart-3',
                    isActive: isAnalyticsActive
                });
            }
            navItems.push({
                label: 'Profile',
                url: '/auth/profile.html',
                icon: 'user',
                isActive: isProfileActive
            });
        } else if (roleName === 'Facilitator') {
            // ── Gate Facilitator ──
            const canProj = this.isModuleAllowed(roleName, 'project_repo');
            const canTpl = this.isModuleAllowed(roleName, 'stage_template');

            navItems = [
                {
                    label: 'Dashboard',
                    url: '/dashboard/dashboard-facilitator.html',
                    icon: 'layout-dashboard',
                    isActive: currentPath.includes('dashboard-facilitator.html')
                }
            ];
            if (canProj) {
                navItems.push({
                    label: 'Projects',
                    url: '/projects/projects-repository.html',
                    icon: 'folder-kanban',
                    isActive: isProjectsActive
                });
            }
            if (canTpl) {
                navItems.push({
                    label: 'Templates',
                    url: '/admin/stage-template.html',
                    icon: 'layers',
                    isActive: isTemplatesActive
                });
            }
            navItems.push({
                label: 'Profile',
                url: '/auth/profile.html',
                icon: 'user',
                isActive: isProfileActive
            });
        } else if (roleName === 'Team Leader') {
            // ── Team Leader ──
            const canProj = this.isModuleAllowed(roleName, 'project_repo');
            const canRewards = this.isModuleAllowed(roleName, 'leaderboard');

            navItems = [
                {
                    label: 'Dashboard',
                    url: '/dashboard/dashboard-team-member.html',
                    icon: 'layout-dashboard',
                    isActive: currentPath.includes('dashboard-team-member.html')
                }
            ];
            if (canProj) {
                navItems.push({
                    label: 'Projects',
                    url: '/projects/projects-repository.html',
                    icon: 'folder-kanban',
                    isActive: isProjectsActive
                });
                navItems.push({
                    label: 'Create',
                    url: '/projects/new-project.html',
                    icon: 'plus-circle',
                    isActive: isNewProjectActive
                });
            }
            if (canRewards) {
                navItems.push({
                    label: 'Rewards',
                    url: '/rewards/leaderboard.html',
                    icon: 'trophy',
                    isActive: isLeaderboardActive
                });
            }
            navItems.push({
                label: 'Profile',
                url: '/auth/profile.html',
                icon: 'user',
                isActive: isProfileActive
            });
        } else {
            // ── Team Member (Default Contributor) ──
            const canProj = this.isModuleAllowed(roleName, 'project_repo');
            const canKB = this.isModuleAllowed(roleName, 'knowledge_base');
            const canRewards = this.isModuleAllowed(roleName, 'leaderboard');

            navItems = [
                {
                    label: 'Dashboard',
                    url: '/dashboard/dashboard-team-member.html',
                    icon: 'layout-dashboard',
                    isActive: currentPath.includes('dashboard-team-member.html')
                }
            ];
            if (canProj) {
                navItems.push({
                    label: 'Projects',
                    url: '/projects/projects-repository.html',
                    icon: 'folder-kanban',
                    isActive: isProjectsActive
                });
            }
            if (canKB) {
                navItems.push({
                    label: 'Knowledge',
                    url: '/projects/repository.html',
                    icon: 'book-open',
                    isActive: isKnowledgeActive
                });
            }
            if (canRewards) {
                navItems.push({
                    label: 'Leaderboard',
                    url: '/rewards/leaderboard.html',
                    icon: 'trophy',
                    isActive: isLeaderboardActive
                });
            }
            navItems.push({
                label: 'Profile',
                url: '/auth/profile.html',
                icon: 'user',
                isActive: isProfileActive
            });
        }

        const navHtml = navItems.map(item => `
            <a href="${item.url}" class="app-bottom-nav-item ${item.isActive ? 'active' : ''}">
                <div class="app-bottom-nav-icon">
                    <i data-lucide="${item.icon}"></i>
                </div>
                <span class="app-bottom-nav-label">${item.label}</span>
            </a>
        `).join('');

        if (!nav) {
            nav = document.createElement('nav');
            nav.id = 'octaqube-mobile-bottom-nav';
            nav.className = 'app-bottom-nav';
            document.body.appendChild(nav);
        }
        nav.innerHTML = navHtml;
        this.refreshIcons();
    },

    setupMobileSidebar() {
        let backdrop = document.getElementById('sidebar-backdrop');
        if (!backdrop) {
            backdrop = document.createElement('div');
            backdrop.id = 'sidebar-backdrop';
            backdrop.className = 'sidebar-backdrop';
            document.body.appendChild(backdrop);
        }

        // Check saved desktop state
        if (localStorage.getItem('octaqube-sidebar-collapsed') === 'true') {
            document.body.classList.add('sidebar-collapsed');
        }

        // Auto-retreat mobile sidebar when choosing any navigation option
        if (!this._sidebarNavClickBound) {
            this._sidebarNavClickBound = true;
            document.addEventListener('click', (e) => {
                const sidebarLink = e.target.closest('#app-sidebar a, #app-sidebar .sidebar-link, #app-sidebar button');
                if (sidebarLink && window.innerWidth <= 1024) {
                    const sidebar = document.getElementById('app-sidebar');
                    const bd = document.getElementById('sidebar-backdrop');
                    if (sidebar) sidebar.classList.remove('show');
                    if (bd) bd.classList.remove('show');
                    document.body.classList.remove('sidebar-mobile-open');
                }
            });
        }

        if (backdrop) {
            const closeDrawer = (e) => {
                if (e && e.cancelable) e.preventDefault();
                const sidebar = document.getElementById('app-sidebar');
                if (sidebar) sidebar.classList.remove('show');
                backdrop.classList.remove('show');
                document.body.classList.remove('sidebar-mobile-open');
            };
            backdrop.onclick = closeDrawer;
            backdrop.ontouchstart = closeDrawer;
        }

        // Native Swipe-to-close Touch Gesture on Drawer
        const sidebar = document.getElementById('app-sidebar');
        if (sidebar && !this._sidebarSwipeBound) {
            this._sidebarSwipeBound = true;
            let touchStartX = 0;
            let touchStartY = 0;
            let isSwiping = false;

            sidebar.addEventListener('touchstart', (e) => {
                if (e.touches.length === 1) {
                    touchStartX = e.touches[0].clientX;
                    touchStartY = e.touches[0].clientY;
                    isSwiping = true;
                }
            }, { passive: true });

            sidebar.addEventListener('touchmove', (e) => {
                if (!isSwiping || e.touches.length !== 1) return;
                const currentX = e.touches[0].clientX;
                const currentY = e.touches[0].clientY;
                const deltaX = currentX - touchStartX;
                const deltaY = Math.abs(currentY - touchStartY);

                // If swipe to the left by > 50px with low vertical movement
                if (deltaX < -50 && deltaY < 50) {
                    sidebar.classList.remove('show');
                    if (backdrop) backdrop.classList.remove('show');
                    document.body.classList.remove('sidebar-mobile-open');
                    isSwiping = false;
                }
            }, { passive: true });

            sidebar.addEventListener('touchend', () => {
                isSwiping = false;
            }, { passive: true });
        }
    },

    toggleSidebar(event) {
        if (event) {
            if (typeof event.stopPropagation === 'function') event.stopPropagation();
            if (typeof event.preventDefault === 'function') event.preventDefault();
        }
        let backdrop = document.getElementById('sidebar-backdrop');
        if (!backdrop) {
            backdrop = document.createElement('div');
            backdrop.id = 'sidebar-backdrop';
            backdrop.className = 'sidebar-backdrop';
            document.body.appendChild(backdrop);
            const closeDrawer = (e) => {
                if (e && e.cancelable) e.preventDefault();
                const sb = document.getElementById('app-sidebar');
                if (sb) sb.classList.remove('show');
                backdrop.classList.remove('show');
                document.body.classList.remove('sidebar-mobile-open');
            };
            backdrop.onclick = closeDrawer;
            backdrop.ontouchstart = closeDrawer;
        }

        const sidebar = document.getElementById('app-sidebar');

        if (window.innerWidth <= 1024) {
            const isCurrentlyOpen = sidebar ? sidebar.classList.contains('show') : false;
            const willOpen = !isCurrentlyOpen;
            if (sidebar) sidebar.classList.toggle('show', willOpen);
            backdrop.classList.toggle('show', willOpen);
            document.body.classList.toggle('sidebar-mobile-open', willOpen);
        } else {
            document.body.classList.toggle('sidebar-collapsed');
            localStorage.setItem('octaqube-sidebar-collapsed', document.body.classList.contains('sidebar-collapsed'));
            setTimeout(() => window.dispatchEvent(new Event('resize')), 350);
        }
    },

    async loadUpcomingMeetingsFeed() {
        const container = document.getElementById('upcomingMeetingsFeed');
        if (!container) return;

        // Render card structure (premium, clean styling)
        container.innerHTML = `
            <div class="ds-card-header d-flex justify-content-between align-items-center">
                <h5 class="card-title">
                    <i data-lucide="calendar" class="me-2" style="width:18px;height:18px;vertical-align:text-bottom;color:var(--ds-primary);"></i>
                    Upcoming Meetings
                </h5>
                <span class="ds-badge gray" id="meetingCountDisplay">0 Scheduled</span>
            </div>
            <div class="ds-card-body p-0">
                <div class="activity-feed p-4" id="meetingsListBody" style="max-height:400px; overflow-y:auto;">
                    <div class="text-center py-4 text-muted">
                        <div class="spinner-border spinner-border-sm text-primary opacity-25" role="status"></div>
                        <p class="text-xs mt-2">Fetching upcoming meetings...</p>
                    </div>
                </div>
            </div>
        `;
        if (window.lucide) lucide.createIcons();

        try {
            const meetings = await api.get('/dashboard/meetings');
            const listBody = document.getElementById('meetingsListBody');
            const countDisplay = document.getElementById('meetingCountDisplay');
            
            countDisplay.textContent = `${meetings.length} Scheduled`;
            
            if (!meetings || !meetings.length) {
                listBody.innerHTML = `
                    <div class="text-center py-4 text-muted">
                        <i data-lucide="calendar-x" class="mb-2 opacity-50" style="width:24px;height:24px;"></i>
                        <p class="text-xs mb-0">No meetings scheduled for your projects.</p>
                    </div>
                `;
                if (window.lucide) lucide.createIcons();
                return;
            }

            listBody.innerHTML = meetings.map(m => {
                const dateStr = new Date(m.scheduled_at).toLocaleDateString(undefined, {
                    weekday: 'short', month: 'short', day: 'numeric', year: 'numeric'
                });
                const timeStr = new Date(m.scheduled_at).toLocaleTimeString(undefined, {
                    hour: '2-digit', minute: '2-digit'
                });
                const duration = m.duration;
                
                const isOnline = m.meeting_type === 'online';
                const actionBtn = isOnline && m.url ? `
                    <a href="${m.url}" target="_blank" class="ds-btn ds-btn-primary ds-btn-sm mt-2">
                        <i data-lucide="video" class="me-1" style="width:12px;height:12px;"></i> Join Meeting
                    </a>
                ` : `
                    <span class="ds-badge ds-badge-sm mt-2" style="background:rgba(var(--ds-info-rgb),0.12);color:var(--ds-info);width:fit-content;display:inline-block;">
                        <i data-lucide="map-pin" class="me-1" style="width:10px;height:10px;vertical-align:middle;"></i> Offline (No URL)
                    </span>
                `;

                return `
                    <div class="activity-item pb-3 mb-3 border-bottom fade-in">
                        <div class="activity-dot bg-primary"></div>
                        <div class="activity-content d-flex flex-wrap flex-sm-nowrap justify-content-between align-items-start gap-3">
                            <div class="v-stack">
                                <span class="text-xs text-muted mb-1">
                                    Project: <strong>${m.project_title}</strong> (Stage ${m.stage_id})
                                </span>
                                <h6 class="fw-bold mb-1" style="color:var(--ds-text-main);">${m.title}</h6>
                                <span class="text-xs ds-text-secondary">
                                    <i data-lucide="clock" class="me-1" style="width:12px;height:12px;vertical-align:text-top;"></i>
                                    ${dateStr} @ ${timeStr} (${duration} mins)
                                </span>
                                ${actionBtn}
                            </div>
                            <span class="ds-badge ds-badge-sm ${isOnline ? 'blue' : 'gray'}">
                                ${isOnline ? 'Online' : 'Offline'}
                            </span>
                        </div>
                    </div>
                `;
            }).join('');
            if (window.lucide) lucide.createIcons();
        } catch (e) {
            console.error('Meetings load failed', e);
            document.getElementById('meetingsListBody').innerHTML = `
                <div class="text-center py-4 text-danger text-xs">
                    <i data-lucide="alert-triangle" class="mb-1" style="width:18px;height:18px;"></i>
                    Failed to load meetings feed.
                </div>
            `;
            if (window.lucide) lucide.createIcons();
        }
    },

    /**
     * Standardized Avatar Rendering
     */
    renderAvatar(user, size = 32) {
        if (!user) {
            return `<div class="avatar-fallback" style="width:${size}px; height:${size}px; min-width:${size}px; min-height:${size}px; max-width:${size}px; max-height:${size}px; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; background:rgba(var(--ds-primary-rgb), 0.1); color:var(--ds-text-secondary); font-size:${Math.round(size/2.5)}px; flex-shrink:0;">?</div>`;
        }
        
        const name = user.full_name || user.username || 'User';
        const parts = name.trim().split(/\s+/);
        const initials = parts.length > 1 
            ? (parts[0][0] + parts[parts.length - 1][0]).toUpperCase() 
            : name.substring(0, 2).toUpperCase() || 'U';
        
        const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ec4899', '#8b5cf6', '#06b6d4', '#6366f1', '#14b8a6'];
        let colorIdx = 0;
        for (let i = 0; i < name.length; i++) {
            colorIdx = (colorIdx + name.charCodeAt(i)) % colors.length;
        }
        const bgColor = colors[colorIdx];

        if (user.profile_picture) {
            let src = user.profile_picture;
            if (!src.startsWith('http') && !src.startsWith('data:')) {
                src = src.startsWith('/') ? src : '/' + src;
            }
            return `<div class="avatar-container" style="width:${size}px; height:${size}px; min-width:${size}px; min-height:${size}px; max-width:${size}px; max-height:${size}px; border-radius:50%; overflow:hidden; display:inline-flex; align-items:center; justify-content:center; background:${bgColor}; flex-shrink:0; position:relative;">
                <img src="${src}" alt="${OctaQube.escapeHtml(name)}" style="width:100%; height:100%; object-fit:cover; display:block; border-radius:50%;" onerror="this.style.display='none'; if(this.nextElementSibling) this.nextElementSibling.style.display='flex';">
                <div class="avatar-initials" style="width:100%; height:100%; display:none; align-items:center; justify-content:center; background:${bgColor}; color:#ffffff; font-weight:700; font-size:${Math.round(size/2.4)}px; border-radius:50%;">
                    ${initials}
                </div>
            </div>`;
        }
        
        return `<div class="avatar-initials" style="width:${size}px; height:${size}px; min-width:${size}px; min-height:${size}px; max-width:${size}px; max-height:${size}px; border-radius:50%; display:inline-flex; align-items:center; justify-content:center; background:${bgColor}; color:#ffffff; font-weight:700; font-size:${Math.round(size/2.4)}px; flex-shrink:0;">
            ${initials}
        </div>`;
    },



    /**
     * KPI Card Component with interactive calculation tooltip
     */
    kpiCardWithTooltip(label, value, icon, color, calculation, description, extraAttrs = '') {
        const hexMap = {
            blue: '#2563eb', green: '#10b981', red: '#ef4444',
            orange: '#f59e0b', purple: '#8b5cf6', cyan: '#06b6d4', gray: '#64748b',
            slate: '#64748b', amber: '#f59e0b'
        };
        const c = hexMap[color] || hexMap.blue;
        const escCal = (calculation || '').replace(/"/g, '&quot;');
        const escDesc = (description || '').replace(/"/g, '&quot;');
        const timestamp = new Date().toLocaleTimeString();
        
        return `<div class="glass-card position-relative clickable hover-shadow" style="padding: var(--ds-space-5); text-align: center; min-height: 140px; cursor: pointer;" data-bs-toggle="tooltip" data-bs-html="true" data-bs-placement="top" title="<div class='text-start p-1' style='font-size:11px;line-height:1.4;'><div class='fw-bold text-white mb-1'>📊 ${label}</div><div class='text-white-50 mb-1'><strong>Data:</strong> ${escDesc || 'Real-time aggregated tenant metrics'}</div><div class='text-white-50 mb-1'><strong>Formula:</strong> ${escCal || 'Direct aggregation'}</div><div style='color:#93c5fd;'>👉 Click to filter records</div></div>" ${extraAttrs}>
            <div class="position-absolute" style="top: 10px; right: 10px; z-index: 10;" onclick="event.stopPropagation()">
                <i data-lucide="info" class="text-muted" style="width: 14px; height: 14px; opacity:0.6;"></i>
            </div>
            <div style="width:40px;height:40px;border-radius:12px;background:${c}1f;display:flex;align-items:center;justify-content:center;margin:0 auto var(--ds-space-3);">
                <i data-lucide="${icon || 'hash'}" style="width:20px;height:20px;color:${c};"></i>
            </div>
            <div class="text-2xl fw-bold" style="color:var(--ds-text-main);">${value ?? '—'}</div>
            <div class="text-xs text-muted mt-1" style="text-transform: uppercase; font-weight: 600; letter-spacing: 0.03em;">${label}</div>
        </div>`;
    },

    /**
     * Cleans up lingering, orphaned, or stuck tooltips from the DOM
     */
    cleanTooltips(container = document) {
        if (typeof bootstrap !== 'undefined' && bootstrap && bootstrap.Tooltip) {
            try {
                container.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
                    try {
                        const inst = bootstrap.Tooltip.getInstance(el);
                        if (inst) {
                            inst.hide();
                            inst.dispose();
                        }
                    } catch (_) {}
                });
            } catch (_) {}
        }
        document.querySelectorAll('.tooltip').forEach(t => t.remove());
    },

    /**
     * Initializes Bootstrap tooltips with hover-only trigger and auto-dismiss on click
     */
    initTooltips(container = document) {
        this.cleanTooltips(container);
        if (typeof bootstrap !== 'undefined' && bootstrap && bootstrap.Tooltip) {
            const list = container.querySelectorAll('[data-bs-toggle="tooltip"]');
            [...list].forEach(el => {
                try {
                    const tip = new bootstrap.Tooltip(el, {
                        boundary: 'window',
                        trigger: 'hover',
                        delay: { show: 150, hide: 80 }
                    });
                    // Auto-hide tooltip on click so it doesn't get stuck at (0,0) during async re-renders
                    el.addEventListener('click', () => {
                        try {
                            tip.hide();
                            setTimeout(() => {
                                document.querySelectorAll('.tooltip').forEach(t => t.remove());
                            }, 50);
                        } catch (_) {}
                    }, { passive: true });
                } catch (e) {
                    try { new bootstrap.Tooltip(el); } catch (_) {}
                }
            });
        }
    },


    getPermissions() {
        if (!this.user) return this.perms['Team Member'];
        return this.perms[this.user.role] || this.perms['Team Member'];
    },

    /**
     * Check if current user has a specific role or higher
     * Levels: Team Member (0) < Team Leader (1) < Facilitator (2) < Reviewer (3) < Admin (4)
     */
    checkRoleAccess(requiredRole) {
        if (!this.user) return false;
        const roles = ['Team Member', 'Team Leader', 'Facilitator', 'Reviewer', 'Admin', 'CEO', 'SuperAdmin'];
        const userLevel = roles.indexOf(this.user.role || 'Team Member');
        const requiredLevel = roles.indexOf(requiredRole);
        return userLevel >= requiredLevel;
    },

    /**
     * Standardized Navbar Rendering
     */
    renderNavbar(userData = null) {
        const user = userData || this.user;
        if (!user) return;

        const navbar = document.getElementById('app-navbar');
        if (!navbar) return;

        navbar.className = 'glass-navbar';
        const isDark = document.documentElement.getAttribute('data-theme') === 'dark';

        navbar.innerHTML = `
            <div class="container-fluid d-flex align-items-center justify-content-between h-100 px-2 px-md-4">
                <div class="d-flex align-items-center">
                    <!-- Sidebar Toggle -->
                    <button class="ds-btn ds-btn-ghost p-1 me-2" id="sidebar-toggle-btn" onclick="OctaQube.toggleSidebar(event)" style="width: 38px; height: 38px; display: flex; align-items: center; justify-content: center; color: #FFFFFF !important;" title="Toggle Navigation Sidebar">
                        <i data-lucide="menu" style="width: 22px; height: 22px; color: #FFFFFF !important;"></i>
                    </button>

                    <!-- Breadcrumb Placeholder -->
                    <div id="nav-breadcrumb-container" class="d-none d-lg-flex align-items-center px-2" style="min-width: 200px;"></div>
                </div>

                <div class="d-flex gap-2 gap-md-3 align-items-center">

                    <!-- Theme Toggle -->
                    <div class="theme-switcher-wrapper">
                        <button class="theme-toggle-btn ${!isDark ? 'theme-active-gold' : 'theme-inactive-ghost'}" 
                                title="Light Mode"
                                data-i18n-title="navbar.light_mode"
                                onclick="window.themeManager.applyTheme('light');">
                            <i data-lucide="sun"></i>
                        </button>
                        <button class="theme-toggle-btn ${isDark ? 'theme-active-gold' : 'theme-inactive-ghost'}" 
                                title="Dark Mode"
                                data-i18n-title="navbar.dark_mode"
                                onclick="window.themeManager.applyTheme('dark');">
                            <i data-lucide="moon"></i>
                        </button>
                    </div>

                    <!-- Language Selector -->
                    <div class="dropdown" id="lang-selector-dropdown">
                        <button class="ds-btn ds-btn-ghost" 
                                style="width:38px; height:38px; border-radius:10px; padding:0; display:flex; align-items:center; justify-content:center; color:#FFFFFFCC; border: 1px solid rgba(255, 255, 255, 0.15); background: rgba(255, 255, 255, 0.08);" 
                                data-bs-toggle="dropdown" aria-expanded="false" title="Change Language" data-i18n-title="navbar.change_language">
                            <i data-lucide="languages" style="width:18px; height:18px;"></i>
                        </button>
                        <ul class="dropdown-menu dropdown-menu-end glass-dropdown" style="border-radius:12px; background:#002347; border: 1px solid rgba(196, 162, 90, 0.3); padding: 6px; box-shadow: var(--ds-shadow-lg);">
                            <li><a class="dropdown-item d-flex align-items-center gap-2 clickable ${window.i18n && window.i18n.getLanguage() === 'en' ? 'active' : ''}" onclick="window.i18n.setLanguage('en')" style="border-radius: 8px; font-weight: 500; font-size:14px; color:#FFFFFF;"><span style="width: 20px; font-size:11px; opacity:0.6; color:#C4A25A;">EN</span>English</a></li>
                            <li><a class="dropdown-item d-flex align-items-center gap-2 clickable ${window.i18n && window.i18n.getLanguage() === 'hi' ? 'active' : ''}" onclick="window.i18n.setLanguage('hi')" style="border-radius: 8px; font-weight: 500; font-size:14px; color:#FFFFFF;"><span style="width: 20px; font-size:11px; opacity:0.6; color:#C4A25A;">HI</span>हिन्दी (Hindi)</a></li>
                            <li><a class="dropdown-item d-flex align-items-center gap-2 clickable ${window.i18n && window.i18n.getLanguage() === 'mr' ? 'active' : ''}" onclick="window.i18n.setLanguage('mr')" style="border-radius: 8px; font-weight: 500; font-size:14px; color:#FFFFFF;"><span style="width: 20px; font-size:11px; opacity:0.6; color:#C4A25A;">MR</span>मराठी (Marathi)</a></li>
                            <li><a class="dropdown-item d-flex align-items-center gap-2 clickable ${window.i18n && window.i18n.getLanguage() === 'kn' ? 'active' : ''}" onclick="window.i18n.setLanguage('kn')" style="border-radius: 8px; font-weight: 500; font-size:14px; color:#FFFFFF;"><span style="width: 20px; font-size:11px; opacity:0.6; color:#C4A25A;">KN</span>ಕನ್ನಡ (Kannada)</a></li>
                            <li><a class="dropdown-item d-flex align-items-center gap-2 clickable ${window.i18n && window.i18n.getLanguage() === 'te' ? 'active' : ''}" onclick="window.i18n.setLanguage('te')" style="border-radius: 8px; font-weight: 500; font-size:14px; color:#FFFFFF;"><span style="width: 20px; font-size:11px; opacity:0.6; color:#C4A25A;">TE</span>తెలుగు (Telugu)</a></li>
                            <li><a class="dropdown-item d-flex align-items-center gap-2 clickable ${window.i18n && window.i18n.getLanguage() === 'ta' ? 'active' : ''}" onclick="window.i18n.setLanguage('ta')" style="border-radius: 8px; font-weight: 500; font-size:14px; color:#FFFFFF;"><span style="width: 20px; font-size:11px; opacity:0.6; color:#C4A25A;">TA</span>தமிழ் (Tamil)</a></li>
                            <li><a class="dropdown-item d-flex align-items-center gap-2 clickable ${window.i18n && window.i18n.getLanguage() === 'ml' ? 'active' : ''}" onclick="window.i18n.setLanguage('ml')" style="border-radius: 8px; font-weight: 500; font-size:14px; color:#FFFFFF;"><span style="width: 20px; font-size:11px; opacity:0.6; color:#C4A25A;">ML</span>മലയാളം (Malayalam)</a></li>
                        </ul>
                    </div>

                    <!-- Notification Bell -->
                    <button id="notif-bell-btn" class="ds-btn ds-btn-ghost position-relative"
                            style="width:38px; height:38px; border-radius:10px; padding:0; display:flex; align-items:center; justify-content:center; color:#FFFFFFCC; border: 1px solid rgba(255, 255, 255, 0.15); background: rgba(255, 255, 255, 0.08);"
                            title="Notifications" data-i18n-title="navbar.notifications" onclick="showNotificationsPanel()">
                        <i data-lucide="bell" style="width:18px; height:18px;"></i>
                        <span id="notif-badge" style="position:absolute; top:6px; right:6px; width:9px; height:9px; background:#C4A25A; border-radius:50%; border:2px solid #002347; display:block;"></span>
                    </button>

                    <div class="v-divider" style="height: 24px; width: 1px; background: rgba(255, 255, 255, 0.15);"></div>

                    <!-- User Auth/Profile Pill: Translucent pill button (background: rgba(255,255,255,0.1), border-radius: 10px, padding: 8px 16px) -->
                    <div class="user-pill d-flex align-items-center gap-2 px-3 py-2 clickable" 
                         style="border-radius: 10px; background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.15); transition: all 0.2s;" 
                         onclick="if (window.SuperAdmin && typeof SuperAdmin.switchView === 'function') { SuperAdmin.switchView('settings'); setTimeout(() => window.PlatformSettings && PlatformSettings.switchTab('admin-logins'), 50); } else { window.location.href='${(user.role === 'SuperAdmin' || user.role === 'Super Admin') ? '/admin/super-admin.html?view=settings&tab=admin-logins' : '/admin/settings.html?tab=personal'}'; }">
                        <div class="user-avatar-sm d-flex align-items-center justify-content-center" 
                             style="width:28px; height:28px; border-radius:8px; font-weight:700; font-size:13px; background: #C4A25A; color: #002347; overflow: hidden;"
                             id="nav-user-avatar">
                            ${this.renderAvatar(user, 28)}
                        </div>
                        <div class="user-meta d-none d-sm-block text-start" style="line-height: 1.2;">
                            <div class="fw-bold" style="font-size: 13px; color: #FFFFFF;">${user.full_name || user.username || 'User'}</div>
                            <div style="font-size: 10px; font-weight: 600; text-transform: uppercase; color: #C4A25A; letter-spacing: 0.05em;" data-i18n="roles.${(user.role || 'Team Member').toLowerCase().replace(' ', '_')}">${user.role || 'Member'}</div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Initialize global search listener
        setTimeout(() => {
            const searchInput = document.getElementById('globalSearchInput');
            if (searchInput) {
                searchInput.value = ''; // Force clear browser autofill
                setTimeout(() => { searchInput.value = ''; }, 500); // Clear again for slower autofills
                searchInput.addEventListener('input', (e) => {
                    window.dispatchEvent(new CustomEvent('octaqube-global-search', { detail: { query: e.target.value } }));
                });
                document.addEventListener('keydown', (e) => {
                    if (e.key === '/' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
                        e.preventDefault();
                        searchInput.focus();
                    }
                });
            }
        }, 100);

        OctaQube.refreshIcons();
        if (window.Breadcrumbs) {
            window.Breadcrumbs.init('nav-breadcrumb-container');
        } else {
            const script = document.createElement('script');
            script.src = '/assets/dist/breadcrumbs.58281b52.min.js';
            script.onload = () => {
                if (window.Breadcrumbs) window.Breadcrumbs.init('nav-breadcrumb-container');
            };
            document.head.appendChild(script);
        }
        if (window.i18n) window.i18n.translatePage();
    },

    /**
     * Standardized Sidebar Rendering â€” Strict RBAC per role
     * Each role gets a completely separate sidebar. No shared sections leak across roles.
     */
    renderSidebar() {
        const user = this.user;
        if (!user) return;

        const sidebar = document.getElementById('app-sidebar');
        if (!sidebar) return;

        sidebar.className = 'app-sidebar glass-sidebar';
        const roleName = user.role || 'Team Member';
        const roleSlug = this.roleToSlug(roleName);

        // Brand header — shared across all roles
        // SuperAdmin: show platform logo & platform name
        // Org users: show org logo (if set) & org name — NEVER the platform logo
        const isSuperAdmin = (user.role === 'SuperAdmin' || user.role === 'Super Admin');

        const shortName = isSuperAdmin
            ? (user.platform_short_name || user.software_name || user.software_display_name || 'OctaQube')
            : (user.org_name || user.platform_short_name || 'OctaQube');

        const displaySub = isSuperAdmin
            ? (user.platform_subtitle || 'ENTERPRISE OS')
            : 'WORKSPACE';

        // Strictly separate: SuperAdmin → platform logo, Org users → org logo only
        const logoUrl = isSuperAdmin
            ? (user.platform_logo_url)
            : (user.org_logo_url);

        let logoIconHtml = `
            <div class="brand-icon" style="background: var(--ds-accent);">
                <i data-lucide="${isSuperAdmin ? 'shield-check' : 'building-2'}" style="color:white;"></i>
            </div>
        `;
        let brandNameHtml = `${OctaQube.escapeHtml(shortName)} <small style="color:var(--ds-accent); opacity:1;">${OctaQube.escapeHtml(displaySub)}</small>`;

        if (logoUrl && logoUrl !== 'null' && logoUrl !== 'None' && !logoUrl.includes('/assets/img/logo.png')) {
            logoIconHtml = `<img src="${logoUrl}" alt="Logo" style="width: 32px; height: 32px; object-fit: contain; border-radius: 8px;">`;
        }

        const brandHtml = `
            <a href="${this.getDashboardUrl(roleName)}" class="sidebar-brand" style="text-decoration: none; color: inherit; display: flex; align-items: center; cursor: pointer;">
                ${logoIconHtml}
                <div class="brand-text">
                    ${brandNameHtml}
                </div>
            </a>
        `;

        let sectionsHtml = '';
        let footerHtml = '';

        // ── SUPER ADMIN – Platform owner only ──────────────────────────
        if (roleName === 'SuperAdmin') {
            sectionsHtml = `
                <div class="sidebar-section" style="margin-bottom: 0;">
                    <nav class="sidebar-nav" style="gap: 1px;">
                        <a href="/admin/super-admin.html" class="sidebar-link sa-compact-link" title="Dashboard">
                            <i class="link-icon" data-lucide="layout-dashboard"></i>
                            <span>Dashboard</span>
                        </a>
                        <a href="/admin/super-admin.html?view=organizations" class="sidebar-link sa-compact-link" title="Organizations">
                            <i class="link-icon" data-lucide="building-2"></i>
                            <span>Organizations</span>
                        </a>
                        <a href="/admin/super-admin.html?view=plans" class="sidebar-link sa-compact-link" title="Plans">
                            <i class="link-icon" data-lucide="layers"></i>
                            <span>Plans</span>
                        </a>
                        <a href="/admin/super-admin.html?view=analytics" class="sidebar-link sa-compact-link" title="Analytics">
                            <i class="link-icon" data-lucide="bar-chart-2"></i>
                            <span>Analytics</span>
                        </a>
                        <a href="/admin/super-admin.html?view=support" class="sidebar-link sa-compact-link" title="Support Tickets">
                            <i class="link-icon" data-lucide="life-buoy"></i>
                            <span>Support Tickets</span>
                        </a>
                        <a href="/admin/super-admin.html?view=billing" class="sidebar-link sa-compact-link" title="Billing">
                            <i class="link-icon" data-lucide="receipt"></i>
                            <span>Billing</span>
                        </a>
                        <a href="/admin/super-admin.html?view=announcements" class="sidebar-link sa-compact-link" title="Announcements">
                            <i class="link-icon" data-lucide="megaphone"></i>
                            <span>Announcements</span>
                        </a>
                        <a href="/admin/super-admin.html?view=logs" class="sidebar-link sa-compact-link" title="Audit Logs">
                            <i class="link-icon" data-lucide="scroll-text"></i>
                            <span>Audit Logs</span>
                        </a>
                        <a href="/admin/super-admin.html?view=integrations" class="sidebar-link sa-compact-link" title="Integrations">
                            <i class="link-icon" data-lucide="blocks"></i>
                            <span>Integrations</span>
                        </a>
                        <a href="/admin/super-admin.html?view=doc-identity" class="sidebar-link sa-compact-link" title="Document Identity & Branding">
                            <i class="link-icon" data-lucide="file-badge"></i>
                            <span>Doc Identity & Branding</span>
                        </a>
                        <a href="/admin/super-admin.html?view=storage" class="sidebar-link sa-compact-link" title="Storage Analytics">
                            <i class="link-icon" data-lucide="hard-drive"></i>
                            <span>Storage Analytics</span>
                        </a>
                        <a href="/admin/super-admin.html?view=stage-templates" class="sidebar-link sa-compact-link" title="Global Stage Templates">
                            <i class="link-icon" data-lucide="layers"></i>
                            <span>Global Stage Templates</span>
                        </a>
                        <a href="/admin/super-admin.html?view=stage-weightage" class="sidebar-link sa-compact-link" title="Stage Weightage">
                            <i class="link-icon" data-lucide="percent"></i>
                            <span>Stage Weightage</span>
                        </a>
                        <a href="/admin/super-admin.html?view=recycle-bin" class="sidebar-link sa-compact-link" title="Recycle Bin">
                            <i class="link-icon" data-lucide="trash-2"></i>
                            <span>Recycle Bin</span>
                        </a>
                        <a href="/resources/user-manual.html" class="sidebar-link sa-compact-link" title="User Manual">
                            <i class="link-icon" data-lucide="book-open"></i>
                            <span>User Manual</span>
                        </a>
                        <a href="/admin/super-admin.html?view=settings" class="sidebar-link sa-compact-link" title="Settings">
                            <i class="link-icon" data-lucide="settings-2"></i>
                            <span>Settings</span>
                        </a>
                    </nav>
                </div>
            `;
            footerHtml = `
                <div class="sidebar-footer">
                    <nav class="sidebar-nav">
                        <a href="#" class="sidebar-link sa-compact-link text-danger" onclick="OctaQube.logout()">
                            <i class="link-icon" data-lucide="log-out"></i>
                            <span data-i18n="sidebar.links.logout">Logout</span>
                        </a>
                    </nav>
                </div>
            `;

        // ── ALL ORGANIZATION ROLES (Admin, CEO, Facilitator, Reviewer, Team Leader, Team Member) ──
        // Permissions are dynamically determined by the Organization's Role Access Control matrix
        } else {
            const canOverview = this.isModuleAllowed(roleName, 'overview');
            const canProjRepo = this.isModuleAllowed(roleName, 'project_repo');
            const canAnalytics = this.isModuleAllowed(roleName, 'analytics');
            const canKB = this.isModuleAllowed(roleName, 'knowledge_base');
            const canRewards = this.isModuleAllowed(roleName, 'leaderboard');
            const canSources = this.isModuleAllowed(roleName, 'additional_sources');
            const canUserMgmt = this.isModuleAllowed(roleName, 'user_management');
            const canPlants = this.isModuleAllowed(roleName, 'plants');
            const canDepts = this.isModuleAllowed(roleName, 'departments');
            const canAudit = this.isModuleAllowed(roleName, 'audit_logs');
            const canTemplate = this.isModuleAllowed(roleName, 'stage_template');
            const canSettings = this.isModuleAllowed(roleName, 'settings');

            const dashboardUrl = this.getDashboardUrl(roleName);

            // Main section: Overview, Projects Repository, Analytics
            let mainNav = '';
            if (canOverview) {
                if (roleName === 'CEO') {
                    mainNav += `<a href="/dashboard/dashboard-ceo.html?view=strategic-overview" class="sidebar-link"><i class="link-icon" data-lucide="line-chart"></i><span data-i18n="sidebar.links.overview">Overview</span></a>`;
                    mainNav += `<a href="/dashboard/dashboard-ceo.html?view=executive-approvals" class="sidebar-link"><i class="link-icon" data-lucide="check-circle-2"></i><span>Project Closures</span><span class="badge bg-warning-subtle text-warning ms-auto d-none" id="ceoPendingApprovalsBadge">0</span></a>`;
                    mainNav += `<a href="/dashboard/dashboard-ceo.html?view=org-health" class="sidebar-link"><i class="link-icon" data-lucide="activity"></i><span data-i18n="sidebar.links.org_health">Organization Health</span></a>`;
                    mainNav += `<a href="/dashboard/dashboard-ceo.html?view=roi-analytics" class="sidebar-link"><i class="link-icon" data-lucide="trending-up"></i><span>Business Analytics</span></a>`;
                } else {
                    mainNav += `<a href="${dashboardUrl}" class="sidebar-link"><i class="link-icon" data-lucide="layout-dashboard"></i><span data-i18n="sidebar.links.overview">Overview</span></a>`;
                }
            }
            if (canProjRepo) {
                mainNav += `<a href="/projects/projects-repository.html" class="sidebar-link"><i class="link-icon" data-lucide="layers"></i><span data-i18n="sidebar.links.projects_repo">Project Repository</span></a>`;
            }
            if (canAnalytics) {
                mainNav += `<a href="/analytics/analytics.html" class="sidebar-link"><i class="link-icon" data-lucide="bar-chart-3"></i><span data-i18n="sidebar.links.analytics">Analytics</span></a>`;
            }

            // Administration section: User Management, Plant Locations, Departments, Audit Logs, 8 Stage Template
            let adminNav = '';
            if (canUserMgmt) {
                adminNav += `<a href="/admin/users.html" class="sidebar-link"><i class="link-icon" data-lucide="users"></i><span data-i18n="sidebar.links.user_management">User Management</span></a>`;
            }
            if (canPlants) {
                adminNav += `<a href="/admin/plants.html" class="sidebar-link"><i class="link-icon" data-lucide="factory"></i><span>Plant Locations</span></a>`;
            }
            if (canDepts) {
                adminNav += `<a href="/admin/departments.html" class="sidebar-link"><i class="link-icon" data-lucide="building-2"></i><span data-i18n="sidebar.links.departments">Departments</span></a>`;
            }
            if (canAudit) {
                adminNav += `<a href="/admin/audit-logs.html" class="sidebar-link"><i class="link-icon" data-lucide="scroll-text"></i><span data-i18n="sidebar.links.audit_logs">Audit Logs</span></a>`;
            }
            if (canTemplate) {
                adminNav += `<a href="/admin/stage-template.html" class="sidebar-link"><i class="link-icon" data-lucide="layout-list"></i><span>8 Stage Template</span></a>`;
            }
            if (canTemplate || canUserMgmt) {
                adminNav += `<a href="/admin/sop-masters.html" class="sidebar-link"><i class="link-icon" data-lucide="file-text"></i><span>Categories & Types</span></a>`;
            }

            // Resources section: Knowledge Base, Leaderboard & Rewards, Additional Sources, User Manual
            let resNav = '';
            if (canKB) {
                resNav += `<a href="/projects/repository.html" class="sidebar-link"><i class="link-icon" data-lucide="database"></i><span data-i18n="sidebar.links.knowledge_base">Knowledge Base</span></a>`;
            }
            if (canRewards) {
                resNav += `<a href="/rewards/leaderboard.html" class="sidebar-link"><i class="link-icon" data-lucide="award"></i><span>Leaderboard & Rewards</span></a>`;
            }
            if (canSources) {
                resNav += `<a href="/projects/additional-sources.html" class="sidebar-link"><i class="link-icon" data-lucide="sparkles"></i><span>Additional Sources</span></a>`;
            }
            resNav += `<a href="/resources/user-manual.html" class="sidebar-link"><i class="link-icon" data-lucide="book-open"></i><span data-i18n="sidebar.links.user_manual">User Manual</span></a>`;

            sectionsHtml = `
                ${mainNav ? `
                <div class="sidebar-section">
                    <div class="sidebar-section-label" data-i18n="sidebar.labels.main">Main</div>
                    <nav class="sidebar-nav">
                        ${mainNav}
                    </nav>
                </div>` : ''}

                ${adminNav ? `
                <div class="sidebar-section">
                    <div class="sidebar-section-label" data-i18n="sidebar.labels.administration">Administration</div>
                    <nav class="sidebar-nav">
                        ${adminNav}
                    </nav>
                </div>` : ''}

                ${resNav ? `
                <div class="sidebar-section">
                    <div class="sidebar-section-label" data-i18n="sidebar.labels.resources">Resources</div>
                    <nav class="sidebar-nav">
                        ${resNav}
                    </nav>
                </div>` : ''}
            `;

            footerHtml = `
                <div class="sidebar-footer">
                    <nav class="sidebar-nav">
                        ${canSettings ? `<a href="/admin/settings.html" class="sidebar-link"><i class="link-icon" data-lucide="settings"></i><span data-i18n="sidebar.links.settings">Settings</span></a>` : ''}
                        <a href="#" class="sidebar-link text-danger" onclick="OctaQube.logout()">
                            <i class="link-icon" data-lucide="log-out"></i>
                            <span data-i18n="sidebar.links.logout">Logout</span>
                        </a>
                    </nav>
                </div>
            `;
        }

        sidebar.innerHTML = `${brandHtml}<div class="sidebar-body">${sectionsHtml}</div>${footerHtml}`;
        OctaQube.refreshIcons();
        this.setActiveLink();
        if (window.i18n) window.i18n.translatePage();
        if (window.FeatureEngine) {
            window.FeatureEngine.applyAll();
        }
    },

    roleToSlug(role) {
        return role.toLowerCase().replace(/ /g, '-');
    },

    setActiveLink() {
        const path = window.location.pathname.toLowerCase();
        const fullUrl = window.location.href.toLowerCase();
        const page = (path.split("/").pop() || 'index.html').toLowerCase();
        const cleanPage = page.split('?')[0].split('#')[0];
        const search = window.location.search.toLowerCase();

        const links = document.querySelectorAll('.sidebar-link');
        if (!links || links.length === 0) return;

        let bestMatch = null;
        let bestMatchScore = -1;

        links.forEach(link => {
            link.classList.remove('active');
            const href = link.getAttribute('href');
            if (!href || href === '#') return;

            const cleanHref = href.split('?')[0].split('#')[0].toLowerCase();
            const hrefPage = cleanHref.split("/").pop();
            const hrefSearch = href.includes('?') ? '?' + href.split('?')[1].toLowerCase() : '';

            let score = -1;

            // 1. Query param match for tabbed/view dashboards (e.g. dashboard-ceo.html?view=org-health)
            if (hrefSearch && search.includes(hrefSearch)) {
                score = 100;
            }
            // 2. Exact file path match (e.g. /projects/repository.html)
            else if (cleanHref === path || (path.endsWith(cleanHref) && cleanHref !== '/')) {
                score = 80;
            }
            // 3. Exact filename match (e.g. repository.html === repository.html)
            else if (hrefPage && hrefPage === cleanPage && hrefPage !== 'index.html') {
                score = 60;
            }
            // 4. Default dashboard fallback on root / index.html
            else if ((cleanPage === 'index.html' || cleanPage === '') && cleanHref.includes('dashboard')) {
                score = 10;
            }

            if (score > bestMatchScore) {
                bestMatchScore = score;
                bestMatch = link;
            }
        });

        if (bestMatch && bestMatchScore > 0) {
            bestMatch.classList.add('active');
        }
    },

    async logout() {
        try {
            await fetch('/api/auth/logout', { method: 'POST', credentials: 'same-origin' }).catch(() => {});
        } catch (_) {}
        try {
            sessionStorage.clear();
            localStorage.removeItem('octaqube_authenticated');
            localStorage.removeItem('token');
            localStorage.removeItem('access_token');
            localStorage.removeItem('user');
            localStorage.removeItem('role_permissions');
            sessionStorage.removeItem('role_permissions');
        } catch (_) {}
        window.location.replace('/auth/login.html?logout=true');
    },

    setLoading(btnId, isLoading) {
        const btn = document.getElementById(btnId);
        if (!btn) return;
        if (isLoading) {
            btn.setAttribute('data-original-html', btn.innerHTML);
            btn.disabled = true;
            btn.innerHTML = `<span class="spinner-border spinner-border-sm"></span> Loading...`;
        } else {
            const originalHtml = btn.getAttribute('data-original-html');
            if (originalHtml) btn.innerHTML = originalHtml;
            btn.disabled = false;
        }
    },

    kpiCard(label, value, icon, color = 'blue', trend = null, link = null, labelKey = null, valueKey = null) {
        const trendIcon = trend > 0 ? 'trending-up' : 'trending-down';
        const trendClass = trend > 0 ? 'ds-badge green' : 'ds-badge red';
        
        const hexMap = {
            blue: '#2563eb', green: '#10b981', red: '#ef4444',
            orange: '#f59e0b', purple: '#8b5cf6', cyan: '#06b6d4', gray: '#64748b'
        };
        const hexColor = hexMap[color] || '#2563eb';
        const rgbVar = `var(--ds-${color}-rgb, 37, 99, 235)`;

        const cardContent = `
            <div class="glass-card fade-in h-100 ${link ? 'hover-shadow clickable' : ''}" style="${link ? 'transition: all 0.2s ease; cursor: pointer;' : ''}; border-radius: 12px; min-width: 0;">
                <div class="ds-card-body p-3 kpi-card-body" style="position: relative; z-index: 1;">
                    <div class="kpi-icon-row mb-2" style="display:flex; align-items:center; justify-content:space-between;">
                        <div class="kpi-icon-box" style="width:34px; height:34px; border-radius:10px; display:flex; align-items:center; justify-content:center; background: rgba(${rgbVar}, 0.12); color: ${hexColor}; border: 1px solid rgba(${rgbVar}, 0.2)">
                            <i data-lucide="${icon || 'hash'}" style="width:16px; height:16px;"></i>
                        </div>
                        ${trend !== null ? `
                            <div class="${trendClass}">
                                <i data-lucide="${trendIcon}" style="width:12px;height:12px;"></i>
                                ${trend}%
                            </div>
                        ` : ''}
                    </div>
                    <div class="kpi-label mb-1" style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; color: var(--ds-text-secondary);"
                         ${labelKey ? `data-i18n="${labelKey}"` : ''}>
                        ${label}
                    </div>
                    <div class="kpi-value fw-bold" style="font-size: 1.4rem; letter-spacing: -0.02em; color: var(--ds-text-main);"
                         ${valueKey ? `data-i18n-number="${valueKey}"` : (typeof value === 'number' ? `data-i18n-number="${value}"` : '')}>
                        ${value ?? '0'}
                    </div>
                </div>
            </div>
        `;

        return link ? `<a href="${link}" style="text-decoration: none; color: inherit; display: block; height: 100%;">${cardContent}</a>` : cardContent;
    },

    badge(text, color = 'blue') {
        return `<span class="ds-badge ${color}">${text}</span>`;
    },

    roleBadge(role) {
        if (!role) return `<span class="ds-badge blue">Team Member</span>`;
        const r = String(role).trim();
        const lower = r.toLowerCase();
        let color = 'blue';

        if (lower.includes('superadmin') || lower.includes('super admin') || lower.includes('super_admin')) {
            color = 'purple';
        } else if (lower.includes('admin') || lower.includes('administrator')) {
            color = 'red';
        } else if (lower === 'ceo' || lower.includes('executive') || lower.includes('director')) {
            color = 'gold';
        } else if (lower.includes('facilitator')) {
            color = 'orange';
        } else if (lower.includes('reviewer') || lower.includes('auditor')) {
            color = 'cyan';
        } else if (lower.includes('leader') || lower.includes('lead') || lower.includes('manager')) {
            color = 'green';
        } else if (lower.includes('member') || lower.includes('user') || lower.includes('viewer')) {
            color = 'blue';
        } else {
            color = 'gray';
        }

        const safeText = OctaQube.escapeHtml ? OctaQube.escapeHtml(r) : r;
        return `<span class="ds-badge ${color}">${safeText}</span>`;
    },

    statusBadge(status) {
        if (!status) return `<span class="ds-badge gray" data-i18n="common.no_data">N/A</span>`;
        const s = String(status).toLowerCase();
        let color = 'gray';
        if (s.includes('active') || s.includes('in_progress') || s.includes('approved') || s.includes('open')) color = 'blue';
        if (s.includes('completed') || s.includes('closed') || s.includes('success') || s.includes('done') || s.includes('resolved')) color = 'green';
        if (s.includes('pending') || s.includes('review') || s.includes('warning') || s.includes('stalled')) color = 'orange';
        if (s.includes('rejected') || s.includes('failed') || s.includes('danger') || s.includes('inactive')) color = 'red';
        
        // Map common status text to i18n keys
        const i18nKey = `common.status_list.${s.replace(/ /g, '_')}`;
        return `<span class="ds-badge ${color}" data-i18n="${i18nKey}">${status}</span>`;
    },

    categoryBadge(cat) {
        if (!cat) return `<span class="ds-badge gray">Uncategorized</span>`;
        const categoryStr = String(cat);
        const hash = Array.from(categoryStr).reduce((acc, char) => char.charCodeAt(0) + ((acc << 5) - acc), 0);
        const colors = ['blue', 'green', 'orange', 'red', 'purple', 'gray', 'cyan'];
        const color = colors[Math.abs(hash) % colors.length];
        return `<span class="ds-badge ${color}">${categoryStr}</span>`;
    },

    formatRelative(dateStr) {
        if (!dateStr) return 'â€”';
        let normalized = dateStr;
        if (typeof dateStr === 'string' && !dateStr.endsWith('Z') && !dateStr.includes('+')) normalized += 'Z';
        const date = new Date(normalized);
        const diff = (new Date() - date) / 1000;
        if (diff < 60) return 'Just now';
        if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
        return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
    },

    formatDate(dateStr) {
        if (!dateStr) return 'â€”';
        let normalized = dateStr;
        if (typeof dateStr === 'string' && !dateStr.endsWith('Z') && !dateStr.includes('+')) normalized += 'Z';
        const date = new Date(normalized);
        return date.toLocaleDateString('en-IN', { 
            day: '2-digit',
            month: 'short', 
            year: 'numeric' 
        });
    },

    formatTime(dateStr) {
        if (!dateStr) return 'â€”';
        const date = new Date(dateStr);
        return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    },

    stageStepper(currentStage) {
        const stages = ['S0/S1', 'S2', 'S3', 'S4', 'S5', 'S6', 'S7', 'S8'];
        const stageIcons = ['users', 'search', 'shield', 'git-branch', 'sliders', 'wrench', 'shield-check', 'award'];
        const stageTitles = [
            'S0/S1 Plan & Establish Team',
            'S2 Define Problem',
            'S3 Interim Containment',
            'S4 Determine Root Causes',
            'S5 Choose Permanent Corrections',
            'S6 Implement Corrective Actions',
            'S7 Take Preventive Measures',
            'S8 Congratulate Team & Closure'
        ];
        return `
            <div class="ds-stepper">
                ${stages.map((s, i) => {
            const status = i + 1 < currentStage ? 'completed' : (i + 1 === currentStage ? 'active' : 'pending');
            const iconName = stageIcons[i];
            const title = stageTitles[i];
            return `
                <div class="step ${status}" title="${title}">
                    <div class="step-circle" style="display: flex; align-items: center; justify-content: center;">
                        <i data-lucide="${iconName}" style="width: 16px; height: 16px;"></i>
                    </div>
                    <div class="step-label">${s}</div>
                </div>
            `;
        }).join('<div class="step-line"></div>')}
            </div>
        `;
    },

    tableSkeleton(rows = 5) {
        let content = '';
        for (let i = 0; i < rows; i++) {
            content += `
                <tr>
                    <td><div class="skeleton-text skeleton" style="width:180px;"></div></td>
                    <td><div class="skeleton-text skeleton" style="width:120px;"></div></td>
                    <td><div class="skeleton-text skeleton" style="width:150px;"></div></td>
                    <td class="text-end"><div class="skeleton-badge skeleton ml-auto" style="width:60px;"></div></td>
                </tr>
            `;
        }
        return content;
    },

    projectProgress(currentStage, totalStages = 8, customPct = null) {
        let pct = (customPct !== null && customPct !== undefined) ? Number(customPct) : ((currentStage / totalStages) * 100);
        if (isNaN(pct)) pct = 0;
        if (pct > 100) pct = 100;
        if (pct < 0) pct = 0;
        const pctStr = (pct % 1 === 0) ? pct.toFixed(0) : pct.toFixed(1);
        return `
            <div class="ds-progress-container mt-3">
                <div class="ds-progress-label"><span>Stage ${currentStage} of ${totalStages} = ${pctStr}%</span></div>
                <div class="ds-progress-bar"><div class="ds-progress-fill" style="width: ${pct}%"></div></div>
            </div>
        `;
    },

    emptyState(param1 = 'No Data Found', param2 = 'Try refining your search or adding new items.', param3 = 'search') {
        let icon = 'search';
        let title = 'No Data Found';
        let message = 'Try refining your search or adding new items.';

        if (arguments.length >= 3) {
            // Check if param1 is an icon name (e.g. 'inbox', 'alert-circle', 'users', 'folder-kanban')
            if (typeof param1 === 'string' && !param1.includes(' ') && /^[a-z0-9-]+$/.test(param1)) {
                icon = param1;
                title = param2;
                message = param3;
            } else {
                title = param1;
                message = param2;
                icon = param3;
            }
        } else if (arguments.length === 2) {
            title = param1;
            message = param2;
        } else if (arguments.length === 1) {
            title = param1;
        }

        return `
            <div class="empty-state-container py-5 px-4 text-center fade-in bg-white/50 rounded-xl border border-dashed border-slate-200">
                <div class="empty-state-icon-box mb-4 mx-auto glass-panel" style="width: 80px; height: 80px; display: flex; align-items: center; justify-content: center; border-radius: 20px;">
                    <i data-lucide="${icon || 'search'}" style="width: 32px; height: 32px; color: var(--ds-accent);"></i>
                </div>
                <h3 class="ds-text-main fw-bold mb-2">${title}</h3>
                <p class="ds-text-secondary mb-0 mx-auto" style="max-width: 400px;">${message}</p>
            </div>
        `;
    },

    chartPlaceholder(label = 'Chart') {
        return `
            <div class="d-flex flex-column align-items-center justify-content-center h-100 py-5 text-center" style="min-height:220px;">
                <div style="width:56px;height:56px;background:var(--ds-bg-subtle);border-radius:16px;display:flex;align-items:center;justify-content:center;margin-bottom:16px;">
                    <i data-lucide="bar-chart-2" style="width:28px;height:28px;color:var(--ds-text-placeholder);"></i>
                </div>
                <p class="ds-text-secondary ds-text-sm mb-0">No data yet for <strong>${label}</strong></p>
                <p class="ds-text-tertiary ds-text-xs mt-1">Data will appear once projects are created.</p>
            </div>
        `;
    },


    toast(message, type = 'info', duration = 3000) {
        let container = document.querySelector('.toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container';
            document.body.appendChild(container);
        }
        const toast = document.createElement('div');
        toast.className = `ds-toast ${type}`;
        toast.innerHTML = `
            <i data-lucide="${type === 'success' ? 'check-circle' : type === 'error' ? 'alert-circle' : 'info'}"></i>
            <span style="flex-grow:1;">${message}</span>
            <button type="button" class="btn-close ms-2" style="font-size:0.65rem;opacity:0.6;cursor:pointer;" onclick="const t=this.closest('.ds-toast'); if(t){ t.classList.add('dismissing'); setTimeout(()=>t.remove(),300); }"></button>
        `;
        container.appendChild(toast);
        if (window.lucide) lucide.createIcons();

        const dismiss = () => {
            if (!toast || !toast.parentNode) return;
            toast.classList.add('dismissing');
            setTimeout(() => {
                if (toast.parentNode) toast.remove();
            }, 300);
        };

        setTimeout(dismiss, duration);
    },

    /**
     * AI Chat Assistant Widget
     */
    renderAIChatWidget() {
        if (window.location.pathname.includes('super-admin.html') || window.location.href.includes('super-admin.html')) return;
        if (document.getElementById('ai-chat-widget')) return;

        const widget = document.createElement('div');
        widget.id = 'ai-chat-widget';
        widget.innerHTML = `
            <button id="chat-toggle" class="chat-toggle-btn shadow-lg">
                <i data-lucide="sparkles"></i>
            </button>
            <div id="chat-window" class="chat-window hidden glass-panel shadow-2xl">
                <div class="chat-header">
                    <div class="d-flex align-items-center gap-2">
                        <div class="ai-avatar"><i data-lucide="bot"></i></div>
                        <div>
                            <div class="fw-bold text-white">Quality AI Assistant</div>
                            <div class="text-xs text-blue-200">Organization &amp; Quality Intelligence</div>
                        </div>
                    </div>
                    <button id="close-chat" class="btn-close-chat"><i data-lucide="x"></i></button>
                </div>
                <div id="chat-messages" class="chat-messages p-4">
                    <div class="message system">
                        <div class="mb-1">👋 Hello! I'm your <strong>Quality AI Assistant</strong>.</div>
                        <div class="text-xs text-muted">Ask me anything about your organization's employees, project growth &amp; status, how-to step guides, 8-stage quality tools, or past root causes.</div>
                    </div>
                    <div class="quick-questions-container" id="quickQuestionsContainer">
                        <div class="text-xs fw-bold text-muted mb-2 d-flex align-items-center gap-1">
                            <i data-lucide="sparkles" style="width:12px;height:12px;color:var(--ds-primary, #6366f1);"></i> Quick Questions:
                        </div>
                        <div class="d-flex flex-column gap-1.5" id="quickQuestionsList">
                            <button type="button" class="quick-question-btn p-2 rounded-2" data-prompt="What is the overall progress and completion status of our quality projects?">
                                📊 Overall project status &amp; completion progress
                            </button>
                            <button type="button" class="quick-question-btn p-2 rounded-2" data-prompt="How do I start and execute an 8-Stage OctaQube project?">
                                🛠️ How to start an 8-Stage OctaQube project
                            </button>
                            <button type="button" class="quick-question-btn p-2 rounded-2" data-prompt="Which plant location has the highest quality performance and savings?">
                                🏭 Plant quality performance &amp; top savings
                            </button>
                            <button type="button" class="quick-question-btn p-2 rounded-2" data-prompt="How many active employees, stakeholders, and departments are registered?">
                                👥 Organization headcount &amp; registered stakeholders
                            </button>
                            <button type="button" class="quick-question-btn p-2 rounded-2" data-prompt="What are the most common root causes and corrective actions identified?">
                                🔍 Common root causes &amp; corrective actions
                            </button>
                        </div>
                    </div>
                </div>
                <form id="chat-form" class="chat-input-area p-3 border-top">
                    <div class="input-group">
                        <input type="text" id="chat-input" class="form-control" placeholder="Ask about employees, project growth, how-to..." autocomplete="off">
                        <button type="submit" class="btn btn-primary"><i data-lucide="send"></i></button>
                    </div>
                </form>
            </div>
        `;
        document.body.appendChild(widget);

        // Logic
        const toggle = document.getElementById('chat-toggle');
        const chatWindow = document.getElementById('chat-window');
        const close = document.getElementById('close-chat');
        const form = document.getElementById('chat-form');
        const input = document.getElementById('chat-input');
        const messages = document.getElementById('chat-messages');

        toggle.onclick = () => {
            const isOpening = chatWindow.classList.contains('hidden');
            chatWindow.classList.toggle('hidden');
            if (isOpening) {
                // Automatically close Helpdesk Support widget if open
                const helpdeskWindow = document.getElementById('helpdesk-window');
                if (helpdeskWindow) {
                    helpdeskWindow.classList.add('hidden');
                }
            }
        };
        close.onclick = () => chatWindow.classList.add('hidden');

        function formatAIMarkdown(text) {
            if (!text) return '';
            let formatted = String(text);
            
            // Convert code blocks
            formatted = formatted.replace(/```([\s\S]*?)```/g, '<pre class="p-2 rounded bg-dark text-light font-mono my-2" style="font-size:11px; overflow-x:auto;"><code>$1</code></pre>');
            // Convert inline code
            formatted = formatted.replace(/`([^`]+)`/g, '<code class="px-1 py-0.5 rounded bg-light border text-primary font-mono text-xs">$1</code>');
            
            // Headers
            formatted = formatted.replace(/^### (.*$)/gim, '<h6 class="fw-bold text-primary mt-2 mb-1">$1</h6>');
            formatted = formatted.replace(/^## (.*$)/gim, '<h6 class="fw-bold text-main mt-2 mb-1">$1</h6>');
            formatted = formatted.replace(/^# (.*$)/gim, '<h5 class="fw-bold text-main mt-2 mb-1">$1</h5>');
            
            // Bold: **text** or __text__
            formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
            formatted = formatted.replace(/__(.*?)__/g, '<strong>$1</strong>');
            
            // Italic: *text* or _text_
            formatted = formatted.replace(/\*([^*\n]+)\*/g, '<em>$1</em>');
            formatted = formatted.replace(/_([^_\n]+)_/g, '<em>$1</em>');
            
            // Clean up any remaining stray double asterisks
            formatted = formatted.replace(/\*\*/g, '');
            
            // Unordered lists: lines starting with * or -
            formatted = formatted.replace(/^\s*[\*\-]\s+(.*$)/gim, '<li class="ms-3 mb-1">$1</li>');
            
            // Numbered lists: lines starting with 1. 2. etc.
            formatted = formatted.replace(/^\s*(\d+)\.\s+(.*$)/gim, '<li class="ms-3 mb-1" style="list-style-type:decimal;">$2</li>');
            
            // Newlines to br
            formatted = formatted.replace(/\n/g, '<br>');
            formatted = formatted.replace(/(<\/h[56]>)<br>/g, '$1');
            formatted = formatted.replace(/(<\/li>)<br>/g, '$1');
            formatted = formatted.replace(/(<\/pre>)<br>/g, '$1');

            return formatted;
        }

        const sendQuery = async (queryText) => {
            const query = (queryText || '').trim();
            if (!query) return;

            // Add user message
            const userMsg = document.createElement('div');
            userMsg.className = 'message user';
            userMsg.textContent = query;
            messages.appendChild(userMsg);
            input.value = '';
            messages.scrollTop = messages.scrollHeight;

            // Add typing indicator
            const typing = document.createElement('div');
            typing.className = 'message system typing';
            typing.textContent = 'Thinking...';
            messages.appendChild(typing);
            messages.scrollTop = messages.scrollHeight;

            try {
                const response = await fetch('/api/rag/chat', {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json'
                    },
                    credentials: 'same-origin',
                    body: JSON.stringify({ query })
                });

                const data = await response.json();
                typing.remove();

                const aiMsg = document.createElement('div');
                aiMsg.className = 'message system';
                
                if (data.answer) {
                    const formatted = formatAIMarkdown(data.answer);
                    aiMsg.innerHTML = `<div class="answer text-sm">${formatted}</div>`;
                    if (data.sources && data.sources.length > 0) {
                        const sourcesHtml = data.sources.map(s => `<li class="mt-1"><a href="/project-details.html?id=${s.project_id}" target="_blank" class="source-link fw-semibold">${s.title}</a> <span class="text-xs text-muted">(${s.category || 'Quality'})</span></li>`).join('');
                        aiMsg.innerHTML += `<div class="sources mt-3 pt-2 border-top text-xs"><strong>Knowledge Sources (${data.sources.length}):</strong><ul class="ps-3 mb-0">${sourcesHtml}</ul></div>`;
                    }
                } else {
                    aiMsg.textContent = data.error || "Sorry, I encountered an error querying your Quality AI Assistant.";
                }

                messages.appendChild(aiMsg);
            } catch (err) {
                typing.remove();
                const errorMsg = document.createElement('div');
                errorMsg.className = 'message system error';
                errorMsg.textContent = "Failed to connect to the AI service.";
                messages.appendChild(errorMsg);
            }
            messages.scrollTop = messages.scrollHeight;
        };

        // Attach quick question click handlers
        widget.querySelectorAll('.quick-question-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const prompt = btn.getAttribute('data-prompt');
                sendQuery(prompt);
            });
        });

        form.onsubmit = (e) => {
            e.preventDefault();
            sendQuery(input.value);
        };

        if (window.lucide) lucide.createIcons();
    },

    /**
     * Floating Helpdesk Support Ticket Widget
     */
    renderHelpdeskWidget() {
        if (window.location.pathname.includes('super-admin.html') || window.location.href.includes('super-admin.html')) return;
        if (document.getElementById('helpdesk-widget')) return;

        const widget = document.createElement('div');
        widget.id = 'helpdesk-widget';
        widget.innerHTML = `
            <button id="helpdesk-toggle" class="helpdesk-toggle-btn shadow-lg">
                <i data-lucide="message-square"></i>
            </button>
            <div id="helpdesk-window" class="helpdesk-window hidden glass-panel shadow-2xl">
                <div class="helpdesk-header">
                    <div class="d-flex align-items-center gap-2">
                        <div class="ai-avatar" style="background: rgba(79, 70, 229, 0.1); color: #4f46e5;"><i data-lucide="help-circle"></i></div>
                        <div>
                            <div class="fw-bold text-white">Helpdesk Support</div>
                            <div class="text-xs text-blue-200">Submit a support ticket</div>
                        </div>
                    </div>
                    <button id="close-helpdesk" class="btn-close-helpdesk"><i data-lucide="x"></i></button>
                </div>
                <div class="helpdesk-tabs">
                    <button id="helpdesk-tab-new" class="helpdesk-tab-btn active">New Ticket</button>
                    <button id="helpdesk-tab-history" class="helpdesk-tab-btn">History</button>
                </div>
                <div id="helpdesk-content-area" class="helpdesk-content">
                    <!-- Dynamic Content -->
                </div>
            </div>
        `;
        document.body.appendChild(widget);

        const toggleBtn = document.getElementById('helpdesk-toggle');
        const helpdeskWindow = document.getElementById('helpdesk-window');
        const closeBtn = document.getElementById('close-helpdesk');
        const tabNew = document.getElementById('helpdesk-tab-new');
        const tabHistory = document.getElementById('helpdesk-tab-history');
        const contentArea = document.getElementById('helpdesk-content-area');

        // Toggle window visibility
        toggleBtn.onclick = () => {
            const isOpening = helpdeskWindow.classList.contains('hidden');
            helpdeskWindow.classList.toggle('hidden');
            if (isOpening) {
                // Automatically close Quality AI Assistant widget if open
                const chatWindow = document.getElementById('chat-window');
                if (chatWindow) {
                    chatWindow.classList.add('hidden');
                }
                // Default to showing form when opened
                switchTab('new');
            }
        };
        closeBtn.onclick = () => helpdeskWindow.classList.add('hidden');

        // Tab selection logic
        const switchTab = (tabName) => {
            if (tabName === 'new') {
                tabNew.classList.add('active');
                tabHistory.classList.remove('active');
                renderForm();
            } else {
                tabNew.classList.remove('active');
                tabHistory.classList.add('active');
                renderHistory();
            }
        };

        tabNew.onclick = () => switchTab('new');
        tabHistory.onclick = () => switchTab('history');

        // Render ticket creation form
        const renderForm = () => {
            contentArea.innerHTML = `
                <form id="helpdesk-form" class="v-stack gap-3">
                    <div class="ds-field">
                        <label class="ds-label text-white">Subject <span class="text-danger">*</span></label>
                        <input type="text" id="helpdesk-subject" class="ds-input form-control" placeholder="Brief summary of the issue..." required>
                    </div>
                    <div class="row g-2">
                        <div class="col-6">
                            <div class="ds-field">
                                <label class="ds-label text-white">Category <span class="text-danger">*</span></label>
                                <select id="helpdesk-category" class="ds-input form-control" style="background:#0f172a;color:#f8fafc;border-color:rgba(255,255,255,0.1);">
                                    <option value="Technical">Technical</option>
                                    <option value="Billing">Billing</option>
                                    <option value="Feature Request">Feature Request</option>
                                    <option value="Other">Other</option>
                                </select>
                            </div>
                        </div>
                        <div class="col-6">
                            <div class="ds-field">
                                <label class="ds-label text-white">Priority <span class="text-danger">*</span></label>
                                <select id="helpdesk-priority" class="ds-input form-control" style="background:#0f172a;color:#f8fafc;border-color:rgba(255,255,255,0.1);">
                                    <option value="Low">Low</option>
                                    <option value="Medium" selected>Medium</option>
                                    <option value="High">High</option>
                                    <option value="Urgent">Urgent</option>
                                </select>
                            </div>
                        </div>
                    </div>
                    <div class="ds-field">
                        <label class="ds-label text-white">Description / Message <span class="text-danger">*</span></label>
                        <textarea id="helpdesk-message" class="ds-input form-control" rows="4" placeholder="Explain the problem in detail..." required></textarea>
                    </div>
                    <button type="submit" id="helpdesk-submit-btn" class="ds-btn ds-btn-primary w-100 mt-2">
                        <i data-lucide="send" class="me-2" style="width:16px;height:16px;vertical-align:middle;display:inline-block;"></i>Submit Ticket
                    </button>
                </form>
            `;
            if (window.lucide) lucide.createIcons();

            const form = document.getElementById('helpdesk-form');
            form.onsubmit = async (e) => {
                e.preventDefault();
                const subject = document.getElementById('helpdesk-subject').value.trim();
                const category = document.getElementById('helpdesk-category').value;
                const priority = document.getElementById('helpdesk-priority').value;
                const message = document.getElementById('helpdesk-message').value.trim();
                const submitBtn = document.getElementById('helpdesk-submit-btn');

                if (!subject || !message) return;

                // Disable submit button during load
                submitBtn.disabled = true;
                submitBtn.innerHTML = `Submitting...`;

                try {
                    const response = await fetch('/api/auth/support/tickets', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        credentials: 'same-origin',
                        body: JSON.stringify({ subject, category, priority, message })
                    });
                    const data = await response.json();

                    if (response.ok && data.status === 'success') {
                        // Success screen
                        contentArea.innerHTML = `
                            <div class="helpdesk-success-screen">
                                <div class="helpdesk-success-icon"><i data-lucide="check-circle" style="width:36px;height:36px;"></i></div>
                                <h5 class="text-white fw-bold mb-2">Ticket Submitted!</h5>
                                <p class="text-sm text-secondary mb-4">Your requested tokens id is <span class="text-white fw-bold font-monospace">#TKT-${data.ticket_id}</span></p>
                                <button id="helpdesk-success-back" class="ds-btn ds-btn-outline ds-btn-sm">Create Another</button>
                            </div>
                        `;
                        if (window.lucide) lucide.createIcons();
                        document.getElementById('helpdesk-success-back').onclick = () => renderForm();
                    } else {
                        alert(data.msg || "Failed to submit ticket.");
                        submitBtn.disabled = false;
                        submitBtn.innerHTML = `<i data-lucide="send" class="me-2" style="width:16px;height:16px;vertical-align:middle;display:inline-block;"></i>Submit Ticket`;
                        if (window.lucide) lucide.createIcons();
                    }
                } catch (err) {
                    alert("An error occurred. Please try again.");
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = `<i data-lucide="send" class="me-2" style="width:16px;height:16px;vertical-align:middle;display:inline-block;"></i>Submit Ticket`;
                    if (window.lucide) lucide.createIcons();
                }
            };
        };

        // Render ticket history (4 tickets per page)
        let currentHistoryPage = 1;
        const perPage = 4;

        const renderHistory = async (page = 1) => {
            contentArea.scrollTop = 0;
            contentArea.innerHTML = `<div class="text-center text-secondary py-4"><span class="spinner-border spinner-border-sm me-2"></span>Loading history...</div>`;

            try {
                const response = await fetch('/api/auth/support/tickets', {
                    credentials: 'same-origin'
                });
                const data = await response.json();

                if (response.ok && data.status === 'success') {
                    const allTickets = data.data || [];
                    if (!allTickets || allTickets.length === 0) {
                        contentArea.innerHTML = `<div class="text-center text-secondary py-5">No support tickets submitted yet.</div>`;
                        return;
                    }

                    const totalItems = allTickets.length;
                    const totalPages = Math.ceil(totalItems / perPage) || 1;
                    const validPage = Math.min(Math.max(1, page), totalPages);
                    currentHistoryPage = validPage;

                    const startIndex = (validPage - 1) * perPage;
                    const pageTickets = allTickets.slice(startIndex, startIndex + perPage);

                    let paginationHtml = '';
                    if (totalPages > 1) {
                        let pageBtns = '';
                        for (let p = 1; p <= totalPages; p++) {
                            const activeClass = p === validPage ? 'btn-primary' : 'btn-outline-secondary text-white';
                            pageBtns += `<button type="button" class="btn btn-sm ${activeClass} py-0 px-2 text-xs fw-bold hd-page-btn" data-page="${p}" style="min-width:24px;height:24px;padding:0 6px;">${p}</button>`;
                        }
                        paginationHtml = `
                            <div class="d-flex align-items-center justify-content-between pt-2.5 mt-3 border-top" style="border-color: rgba(255,255,255,0.08)!important;">
                                <span class="text-xxs text-secondary">
                                    Showing ${startIndex + 1}–${Math.min(startIndex + perPage, totalItems)} of ${totalItems}
                                </span>
                                <div class="d-flex align-items-center gap-1">
                                    <button type="button" class="btn btn-sm btn-outline-secondary text-white py-0 px-2 text-xs d-inline-flex align-items-center gap-1" style="height:24px;padding:0 6px;" ${validPage <= 1 ? 'disabled' : ''} id="hd-prev-btn">
                                        <i data-lucide="chevron-left" style="width:12px;height:12px;"></i> Prev
                                    </button>
                                    ${pageBtns}
                                    <button type="button" class="btn btn-sm btn-outline-secondary text-white py-0 px-2 text-xs d-inline-flex align-items-center gap-1" style="height:24px;padding:0 6px;" ${validPage >= totalPages ? 'disabled' : ''} id="hd-next-btn">
                                        Next <i data-lucide="chevron-right" style="width:12px;height:12px;"></i>
                                    </button>
                                </div>
                            </div>
                        `;
                    }

                    contentArea.innerHTML = `
                        <div class="helpdesk-history-list">
                            ${pageTickets.map(t => {
                                const createdDate = new Date(t.created_at).toLocaleDateString();
                                const badgeHtml = this.statusBadge(t.status);
                                const comments = t.comments || [];
                                const hasComments = comments.length > 0;
                                const isClosedOrResolved = ['closed', 'resolved', 'cancelled'].includes((t.status || '').toLowerCase());

                                // Build comments / replies timeline
                                let repliesHtml = '';
                                if (hasComments) {
                                    repliesHtml = `
                                        <div class="mt-2.5 pt-2 border-top" style="border-color: rgba(255,255,255,0.08)!important;">
                                            <div class="text-xxs fw-bold text-primary mb-2 d-flex align-items-center gap-1">
                                                <i data-lucide="messages-square" style="width:12px;height:12px;"></i>
                                                <span>Support Replies & Updates (${comments.length}):</span>
                                            </div>
                                            <div class="d-flex flex-column gap-2">
                                                ${comments.map(c => {
                                                    const isSupport = c.is_support || (c.user && !c.user.toLowerCase().includes('customer'));
                                                    const badgeBg = isSupport 
                                                        ? 'background: rgba(79, 142, 247, 0.15); color: #4f8ef7; border: 1px solid rgba(79, 142, 247, 0.3);' 
                                                        : 'background: rgba(255, 255, 255, 0.08); color: #94a3b8; border: 1px solid rgba(255, 255, 255, 0.12);';
                                                    const attHtml = (c.attachments && c.attachments.length > 0) ? `
                                                        <div class="d-flex flex-wrap gap-1 mt-1.5 pt-1.5 border-top" style="border-color: rgba(255,255,255,0.06)!important;">
                                                            ${c.attachments.map(a => `
                                                                <a href="${a.file_path}" target="_blank" download class="badge text-decoration-none d-inline-flex align-items-center gap-1" style="background: rgba(255,255,255,0.08); color: #e2e8f0; border: 1px solid rgba(255,255,255,0.15); padding: 3px 6px; font-size: 10px;">
                                                                    <i data-lucide="paperclip" style="width:10px;height:10px;"></i>
                                                                    <span class="text-truncate" style="max-width: 130px;">${OctaQube.escapeHtml(a.file_name)}</span>
                                                                </a>
                                                            `).join('')}
                                                        </div>
                                                    ` : '';

                                                    return `
                                                        <div class="p-2 rounded" style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.07); border-left: 3px solid ${isSupport ? '#4f8ef7' : '#94a3b8'};">
                                                            <div class="d-flex justify-content-between align-items-center mb-1">
                                                                <div class="d-flex align-items-center gap-1">
                                                                    <span class="text-xs fw-bold text-white">${OctaQube.escapeHtml(c.user)}</span>
                                                                    <span class="badge py-0 px-1 text-xxs" style="${badgeBg}">${isSupport ? 'Support' : 'You'}</span>
                                                                </div>
                                                                <span class="text-xxs text-secondary">${c.created_at ? new Date(c.created_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' }) : ''}</span>
                                                            </div>
                                                            <div class="text-xs" style="white-space: pre-wrap; word-break: break-word; color: #cbd5e1!important;">${OctaQube.escapeHtml(c.content)}</div>
                                                            ${attHtml}
                                                        </div>
                                                    `;
                                                }).join('')}
                                            </div>
                                        </div>
                                    `;
                                }

                                // Build resolution section
                                let resolutionHtml = '';
                                const hasDistinctRes = t.resolution && t.resolution.trim() && t.resolution !== 'No resolution notes provided.' && (!hasComments || !comments.some(c => c.content === t.resolution));
                                if (hasDistinctRes) {
                                    resolutionHtml = `
                                        <div class="helpdesk-resolution-box ${t.status.toLowerCase() === 'rejected' ? 'rejected' : ''} mt-2.5">
                                            <div class="d-flex align-items-center gap-1.5 fw-bold mb-1" style="font-size: 11px;">
                                                <i data-lucide="${t.status.toLowerCase() === 'rejected' ? 'x-circle' : 'check-circle'}" style="width:13px;height:13px;"></i>
                                                <span>Resolution Summary:</span>
                                            </div>
                                            <div class="text-xs" style="white-space: pre-wrap; word-break: break-word;">${OctaQube.escapeHtml(t.resolution)}</div>
                                        </div>
                                    `;
                                } else if (isClosedOrResolved && !hasComments) {
                                    resolutionHtml = `
                                        <div class="helpdesk-resolution-box mt-2.5">
                                            <div class="d-flex align-items-center gap-1.5 fw-bold mb-1" style="font-size: 11px;">
                                                <i data-lucide="check-circle" style="width:13px;height:13px;"></i>
                                                <span>Status:</span>
                                            </div>
                                            <div class="text-xs">This ticket has been marked as <strong>${t.status}</strong>.</div>
                                        </div>
                                    `;
                                }

                                return `
                                    <div class="helpdesk-history-item">
                                        <div class="d-flex justify-content-between align-items-start mb-2">
                                            <span class="text-xs font-monospace text-secondary">#TKT-${t.id}</span>
                                            ${badgeHtml}
                                        </div>
                                        <div class="fw-bold text-white text-sm mb-1">${OctaQube.escapeHtml(t.subject)}</div>
                                        <div class="text-xs text-secondary mb-2">${createdDate} &bull; ${OctaQube.escapeHtml(t.category)} &bull; ${OctaQube.escapeHtml(t.priority)} Priority</div>
                                        <div class="p-2 rounded mb-2" style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05);">
                                            <div class="text-xxs text-secondary mb-1 text-uppercase fw-bold" style="letter-spacing:.04em;">Your Message:</div>
                                            <div class="text-xs text-muted" style="white-space: pre-wrap; word-break: break-word;">${OctaQube.escapeHtml(t.message)}</div>
                                        </div>
                                        ${repliesHtml}
                                        ${resolutionHtml}
                                    </div>
                                `;
                            }).join('')}
                            ${paginationHtml}
                        </div>
                    `;
                    if (window.lucide) lucide.createIcons();

                    // Bind pagination handlers
                    const prevBtn = document.getElementById('hd-prev-btn');
                    if (prevBtn) prevBtn.onclick = () => renderHistory(validPage - 1);

                    const nextBtn = document.getElementById('hd-next-btn');
                    if (nextBtn) nextBtn.onclick = () => renderHistory(validPage + 1);

                    document.querySelectorAll('.hd-page-btn').forEach(btn => {
                        btn.onclick = () => {
                            const p = parseInt(btn.getAttribute('data-page'), 10);
                            if (p) renderHistory(p);
                        };
                    });
                } else {
                    contentArea.innerHTML = `<div class="text-center text-danger py-4">Failed to load history.</div>`;
                }
            } catch (err) {
                contentArea.innerHTML = `<div class="text-center text-danger py-4">Error loading history.</div>`;
            }
        };

        // Render form by default
        renderForm();

        if (window.lucide) lucide.createIcons();
    },

    /**
     * Indian Number System Formatter (Lakh/Crore)
     */
    formatINR(num) {
        if (num === null || num === undefined || isNaN(num)) return '₹0';
        const val = Math.abs(Number(num));
        const sign = Number(num) < 0 ? '-' : '';
        const CR = 10000000;   // 1 Crore  = 1,00,00,000
        const L  = 100000;     // 1 Lakh   = 1,00,000
        const K  = 1000;       // 1 Thousand

        if (val >= CR) {
            // Show in Crores, up to 2 decimal places
            const cr = val / CR;
            const formatted = cr % 1 === 0 ? cr.toFixed(0) : cr.toFixed(2).replace(/\.?0+$/, '');
            return `${sign}₹${formatted} Cr`;
        } else if (val >= L) {
            // Show in Lakhs, up to 2 decimal places
            const lakh = val / L;
            const formatted = lakh % 1 === 0 ? lakh.toFixed(0) : lakh.toFixed(2).replace(/\.?0+$/, '');
            return `${sign}₹${formatted} L`;
        } else if (val >= K) {
            // Show in thousands with Indian comma formatting
            return `${sign}₹${val.toLocaleString('en-IN')}`;
        } else {
            return `${sign}₹${val.toLocaleString('en-IN')}`;
        }
    },

    notifications: [],

    async loadNotifications() {
        try {
            const notifs = await api.get('/notifications').catch(() => null);
            // Guard: backend returns a raw array; treat any non-array response as empty
            this.notifications = Array.isArray(notifs) ? notifs : [];
            const badge = document.getElementById('notif-badge');
            if (badge) {
                const unread = this.notifications.some(n => !n.is_read);
                badge.style.display = unread ? 'block' : 'none';
            }
        } catch (e) {
            // Silently fail — no notifications is not an error state
            this.notifications = [];
            const badge = document.getElementById('notif-badge');
            if (badge) badge.style.display = 'none';
        }
    },

    async markNotificationsAsRead() {
        try {
            await api.post('/notifications/read');
            const badge = document.getElementById('notif-badge');
            if (badge) badge.style.display = 'none';
            if (this.notifications) {
                this.notifications.forEach(n => n.is_read = true);
            }
        } catch (e) {
            console.error('Failed to mark notifications as read', e);
        }
    },

    async clearNotifications() {
        try {
            await api.post('/notifications/clear');
            this.notifications = [];
            const badge = document.getElementById('notif-badge');
            if (badge) badge.style.display = 'none';
        } catch (e) {
            console.error('Failed to clear notifications', e);
        }
    },

    handleNotificationClick(link) {
        if (!link) return;
        if (link.includes('/reports/export/pdf/')) {
            const endpoint = link.startsWith('/api') ? link.substring(4) : link;
            const match = link.match(/\/reports\/export\/pdf\/(\d+)/);
            const projectId = match ? match[1] : 'Project';
            api.downloadFile(endpoint, `QC_Project_Report_${projectId}.pdf`);
        } else {
            window.location.href = link;
        }
    },

    openNotificationDetail(target) {
        let notif = null;
        if (typeof target === 'object' && target !== null) {
            notif = target;
        } else {
            notif = (this.notifications || []).find(n => n.id == target) || (this.notifications || [])[target];
        }
        if (!notif) {
            notif = { title: 'Notification Alert', message: 'No detailed content available.' };
        }

        // Mark as read locally & sync backend
        notif.is_read = true;
        if (notif.id) {
            api.post(`/notifications/${notif.id}/read`).catch(() => {});
        }

        const badge = document.getElementById('notif-badge');
        if (badge) {
            const hasUnread = (this.notifications || []).some(n => !n.is_read);
            badge.style.display = hasUnread ? 'block' : 'none';
        }

        // Auto-disappear unstarred read notification from list
        switchNotifTab(currentNotifFilterTab || 'all', currentNotifPage);

        // Close notification dropdown panel if open
        const existingOverlay = document.getElementById('notif-panel-overlay');
        if (existingOverlay) existingOverlay.remove();

        // Remove old detail modal if present
        const oldModal = document.getElementById('notif-detail-modal-container');
        if (oldModal) oldModal.remove();

        const modalEl = document.createElement('div');
        modalEl.id = 'notif-detail-modal-container';
        modalEl.className = 'modal fade show';
        modalEl.style.cssText = 'display:block; background:rgba(0,0,0,0.55); z-index:20500; backdrop-filter:blur(4px);';

        const createdDateStr = notif.created_at ? `${new Date(notif.created_at).toLocaleString()} (${OctaQube.formatRelative(notif.created_at)})` : 'Just now';

        const titleLower = (notif.title || '').toLowerCase();
        const msgLower = (notif.message || '').toLowerCase();
        const isOfflinePaymentNotif = titleLower.includes('offline payment') || msgLower.includes('payment proof') || titleLower.includes('payment verification') || titleLower.includes('payment approved') || msgLower.includes('utr:');
        const isPaygBillNotif = titleLower.includes('pay-as-you-go') || msgLower.includes('metered invoice') || msgLower.includes('pay-as-you-go bill') || titleLower.includes('monthly pay-as-you-go') || (titleLower.includes('bill') && msgLower.includes('generated'));

        let utrMatch = null;
        if (notif.message) {
            const m = notif.message.match(/UTR[:\s]+([A-Za-z0-9_\-]+)/i);
            if (m) utrMatch = m[1];
        }

        let actionButtonHtml = '';
        if (isPaygBillNotif) {
            actionButtonHtml = `
                <div class="p-3 bg-primary bg-opacity-10 border border-primary border-opacity-25 rounded-3 mb-3">
                    <div class="text-xs text-secondary mb-2 fw-bold"><i data-lucide="receipt" class="me-1"></i> Outstanding Pay-As-You-Go Bill Action</div>
                    <button type="button" class="ds-btn ds-btn-primary ds-btn-sm w-100 py-2 fw-bold text-white shadow-sm" onclick="OctaQube.handlePaygBillNotifClick()">
                        <i data-lucide="credit-card" class="me-1.5"></i> Pay Invoice Now & View Usage Breakdown
                    </button>
                </div>
            `;
        } else if (isOfflinePaymentNotif) {
            if (window.location.pathname.includes('super-admin.html')) {
                actionButtonHtml = `
                    <div class="p-3 bg-primary bg-opacity-10 border border-primary border-opacity-25 rounded-3 mb-3">
                        <div class="text-xs text-secondary mb-2 fw-bold">Offline Payment Review Action</div>
                        <button type="button" class="ds-btn ds-btn-primary ds-btn-sm w-100 py-2" onclick="OctaQube.handleOfflinePaymentNotifClick('${utrMatch || ''}')">
                            <i data-lucide="shield-check" class="me-1"></i> View Receipt Image, UTR & Activate Plan
                        </button>
                    </div>
                `;
            } else {
                actionButtonHtml = `
                    <div class="p-3 bg-primary bg-opacity-10 border border-primary border-opacity-25 rounded-3 mb-3">
                        <div class="text-xs text-secondary mb-2 fw-bold">Billing & Subscription Status</div>
                        <button type="button" class="ds-btn ds-btn-primary ds-btn-sm w-100 py-2" onclick="document.getElementById('notif-detail-modal-container').remove(); window.location.href='/admin/settings.html#billing';">
                            <i data-lucide="credit-card" class="me-1"></i> Open Billing Settings & Resubmit Proof
                        </button>
                    </div>
                `;
            }
        }

        modalEl.innerHTML = `
            <div class="modal-dialog modal-dialog-centered" style="max-width:540px;">
                <div class="modal-content glass-card border-0" style="background:var(--ds-bg-surface); border:1px solid var(--ds-border-color)!important; border-radius:16px; box-shadow:0 25px 50px -12px rgba(0,0,0,0.25);">
                    <div class="modal-header border-bottom p-3" style="border-color:var(--ds-border-color)!important;">
                        <div class="d-flex align-items-center gap-2">
                            <div class="p-2 rounded-circle" style="background:${notif.is_announcement ? 'rgba(59,130,246,0.15)' : 'rgba(var(--ds-primary-rgb), 0.1)'}; color:${notif.is_announcement ? '#3b82f6' : 'var(--ds-primary)'};">
                                <i data-lucide="${notif.is_announcement ? 'megaphone' : 'bell'}" style="width:20px;height:20px;"></i>
                            </div>
                            <div>
                                <h6 class="modal-title fw-bold mb-0" style="color:var(--ds-text-main); font-size:16px;">${OctaQube.escapeHtml(notif.title || (notif.is_announcement ? 'Announcement' : 'Notification Details'))}</h6>
                                <span class="text-xxs text-secondary">${createdDateStr}</span>
                            </div>
                        </div>
                        <button type="button" class="btn-close" style="filter:var(--ds-icon-filter, none);" onclick="document.getElementById('notif-detail-modal-container').remove()"></button>
                    </div>
                    <div class="modal-body p-4" style="max-height:60vh; overflow-y:auto;">
                        <div class="mb-3 d-flex align-items-center gap-2">
                            ${notif.is_announcement ? `
                                <span class="badge bg-primary bg-opacity-15 text-primary border border-primary border-opacity-25" style="font-size:11px;">
                                    📢 Platform Announcement
                                </span>
                            ` : `
                                <span class="badge bg-primary bg-opacity-10 text-primary border border-primary border-opacity-25" style="font-size:11px;">
                                    System Notification
                                </span>
                                <span class="badge bg-success bg-opacity-10 text-success border border-success border-opacity-25" style="font-size:11px;">
                                    Verified Alert
                                </span>
                            `}
                            ${notif.is_starred ? `<span class="badge bg-warning bg-opacity-15 text-warning border border-warning border-opacity-25" style="font-size:11px;">★ Saved</span>` : ''}
                        </div>
                        <div class="p-3 rounded-3 mb-3" style="background:rgba(255,255,255,0.03); border:1px solid var(--ds-border-color); font-size:14px; line-height:1.6; color:var(--ds-text-main); white-space:pre-wrap; word-break:break-word;">
${OctaQube.escapeHtml(notif.message || 'No detailed description available.')}
                        </div>
                        ${actionButtonHtml}
                    </div>
                    <div class="modal-footer border-top p-3 d-flex justify-content-between align-items-center" style="border-color:var(--ds-border-color)!important;">
                        ${notif.is_announcement ? `
                            <button type="button" class="btn btn-sm btn-link text-primary text-decoration-none fw-bold text-xs p-0" onclick="document.getElementById('notif-detail-modal-container').remove(); UserAnnouncementsModal.open();">
                                📢 View All Announcements
                            </button>
                        ` : '<div></div>'}
                        <button type="button" class="ds-btn ds-btn-secondary ds-btn-sm" onclick="document.getElementById('notif-detail-modal-container').remove()">Close</button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modalEl);
        if (OctaQube.refreshIcons) OctaQube.refreshIcons();
    },

    handleNotifClick(index) {
        const notifs = window.OctaQube.notifications || this.notifications || [];
        const notif = notifs[index];
        if (!notif) return;

        const overlay = document.getElementById('notif-panel-overlay');
        if (overlay) overlay.remove();

        this.openNotificationDetail(notif);
    },

    handleOfflinePaymentNotifClick(utr) {
        const detailModal = document.getElementById('notif-detail-modal-container');
        if (detailModal) detailModal.remove();

        if (window.location.pathname.includes('super-admin.html')) {
            if (typeof showView === 'function') showView('subscriptions');
            if (window.SuperAdmin && typeof window.SuperAdmin.openVerificationFromNotification === 'function') {
                window.SuperAdmin.openVerificationFromNotification(utr);
            }
        } else {
            window.location.href = `/admin/super-admin.html?view=subscriptions&utr=${encodeURIComponent(utr)}`;
        }
    },

    handlePaygBillNotifClick() {
        const detailModal = document.getElementById('notif-detail-modal-container');
        if (detailModal) detailModal.remove();

        if (window.location.pathname.includes('settings.html')) {
            const billingTab = document.querySelector('[data-i18n="settings.nav.billing"]') || document.querySelector('button[onclick*="billing"]');
            if (billingTab) billingTab.click();
            if (typeof settingsManager !== 'undefined' && typeof settingsManager.loadBillingHistory === 'function') {
                settingsManager.loadBillingHistory();
            }
            if (typeof openCheckoutModal === 'function') {
                openCheckoutModal();
            }
        } else {
            window.location.href = '/admin/settings.html#billing';
        }
    }
};

// Global helper for notifications with dedicated Announcement & Alerts tabs
let currentNotifFilterTab = 'all';
let currentNotifPage = 1;
const NOTIFS_PER_PAGE = 10;

OctaQube.toggleStarNotification = async function(notifId, e) {
    if (e) e.stopPropagation();
    const notifs = window.OctaQube.notifications || [];
    const notif = notifs.find(n => n.id == notifId);
    if (!notif) return;

    notif.is_starred = !notif.is_starred;
    switchNotifTab(currentNotifFilterTab || 'all', currentNotifPage);

    try {
        await api.post(`/notifications/${notifId}/star`);
    } catch (err) {
        console.error('Failed to toggle star status:', err);
    }
};

OctaQube.changeNotifPage = function(delta) {
    currentNotifPage += delta;
    if (currentNotifPage < 1) currentNotifPage = 1;
    switchNotifTab(currentNotifFilterTab || 'all', currentNotifPage);
};

function switchNotifTab(tab, page) {
    currentNotifFilterTab = tab;
    currentNotifPage = page || currentNotifPage || 1;
    const bodyEl = document.getElementById('notif-items-container');
    const footerPaginationEl = document.getElementById('notif-pagination-container');
    if (!bodyEl) return;
    
    // Update tab pills active styling
    document.querySelectorAll('.notif-tab-btn').forEach(btn => {
        const isActive = btn.getAttribute('data-tab') === tab;
        btn.style.background = isActive ? 'rgba(var(--ds-primary-rgb), 0.15)' : 'transparent';
        btn.style.color = isActive ? 'var(--ds-primary)' : 'var(--ds-text-muted, #94a3b8)';
        btn.style.borderColor = isActive ? 'rgba(var(--ds-primary-rgb), 0.3)' : 'transparent';
        btn.style.fontWeight = isActive ? '700' : '500';
    });

    const notifs = window.OctaQube.notifications || [];
    
    // Active notifications: Only show items that are UNREAD or STARRED!
    // Unstarred seen/read notifications automatically disappear!
    const activeNotifs = notifs.filter(n => !n.is_read || n.is_starred);

    let filtered = activeNotifs;
    if (tab === 'announcements') {
        filtered = activeNotifs.filter(n => n.is_announcement || (n.title && n.title.startsWith('📢')));
    } else if (tab === 'alerts') {
        filtered = activeNotifs.filter(n => !n.is_announcement && !(n.title && n.title.startsWith('📢')));
    }

    const totalFiltered = filtered.length;
    const totalPages = Math.max(1, Math.ceil(totalFiltered / NOTIFS_PER_PAGE));
    if (currentNotifPage > totalPages) currentNotifPage = totalPages;

    const startIdx = (currentNotifPage - 1) * NOTIFS_PER_PAGE;
    const pageItems = filtered.slice(startIdx, startIdx + NOTIFS_PER_PAGE);

    if (totalFiltered === 0) {
        let emptyMsg = 'No new notifications';
        let emptyIcon = 'bell-off';
        if (tab === 'announcements') {
            emptyMsg = 'No platform announcements yet';
            emptyIcon = 'megaphone';
        } else if (tab === 'alerts') {
            emptyMsg = 'No system alerts';
            emptyIcon = 'shield-check';
        }
        bodyEl.innerHTML = `
            <div class="p-5 text-center opacity-60">
                <i data-lucide="${emptyIcon}" class="mb-2" style="width:28px;height:28px;"></i>
                <div class="text-xs text-secondary">${emptyMsg}</div>
            </div>
        `;
        if (footerPaginationEl) footerPaginationEl.style.display = 'none';
    } else {
        bodyEl.innerHTML = pageItems.map((n) => {
            const originalIdx = notifs.indexOf(n);
            const isAnn = n.is_announcement || (n.title && n.title.startsWith('📢'));
            const isStarred = Boolean(n.is_starred);
            return `
                <div class="notif-item p-3 mb-2 rounded-2 clickable hover-bg" 
                     style="background:${isStarred ? 'rgba(234, 179, 8, 0.06)' : 'rgba(255,255,255,0.03)'}; border:1px solid ${isStarred ? 'rgba(234, 179, 8, 0.35)' : 'var(--ds-border-color)'}; cursor:pointer; transition:all 0.15s ease;"
                     onclick="OctaQube.handleNotifClick(${originalIdx})">
                    <div class="d-flex align-items-center justify-content-between mb-1">
                        <div class="d-flex align-items-center gap-1.5 overflow-hidden">
                            ${isAnn ? '<span class="badge bg-primary bg-opacity-15 text-primary text-xxs font-monospace px-1.5 py-0.5">📢 Announcement</span>' : ''}
                            <div class="fw-bold text-sm text-truncate" style="color: var(--ds-text-main);">${OctaQube.escapeHtml(n.title || (isAnn ? 'Announcement' : 'Notification'))}</div>
                        </div>
                        <div class="d-flex align-items-center gap-1.5 flex-shrink-0">
                            <button type="button" class="btn btn-sm p-0 border-0 ${isStarred ? 'text-warning' : 'text-secondary opacity-60'}" 
                                    title="${isStarred ? 'Unstar notification' : 'Star & Save notification'}"
                                    onclick="OctaQube.toggleStarNotification(${n.id}, event)" 
                                    style="font-size:16px; line-height:1; background:transparent; cursor:pointer;">
                                ${isStarred ? '★' : '☆'}
                            </button>
                            ${!n.is_read ? '<span class="badge bg-primary" style="font-size:9px; padding:2px 5px; flex-shrink:0;">New</span>' : ''}
                        </div>
                    </div>
                    <div class="text-xs text-secondary text-truncate">${OctaQube.escapeHtml(n.message || '')}</div>
                    <div class="text-xxs text-muted mt-1.5 d-flex align-items-center justify-content-between">
                        <span>${OctaQube.formatRelative(n.created_at)}</span>
                        ${isStarred ? '<span class="text-warning fw-semibold text-xxs">★ Saved</span>' : (isAnn ? '<span class="text-primary fw-semibold">Read Details &rarr;</span>' : '')}
                    </div>
                </div>
            `;
        }).join('');

        if (footerPaginationEl) {
            footerPaginationEl.style.display = totalPages > 1 ? 'flex' : 'none';
            const startItem = totalFiltered > 0 ? startIdx + 1 : 0;
            const endItem = Math.min(startIdx + NOTIFS_PER_PAGE, totalFiltered);
            footerPaginationEl.innerHTML = `
                <span class="text-xxs text-muted">Showing ${startItem}–${endItem} of ${totalFiltered}</span>
                <div class="d-flex align-items-center gap-1">
                    <button class="btn btn-xs ds-btn-ghost px-2 py-0.5 text-xxs" ${currentNotifPage <= 1 ? 'disabled' : ''} onclick="OctaQube.changeNotifPage(-1)">&larr; Prev</button>
                    <span class="text-xxs fw-bold px-1" style="color:var(--ds-text-main);">Page ${currentNotifPage}/${totalPages}</span>
                    <button class="btn btn-xs ds-btn-ghost px-2 py-0.5 text-xxs" ${currentNotifPage >= totalPages ? 'disabled' : ''} onclick="OctaQube.changeNotifPage(1)">Next &rarr;</button>
                </div>
            `;
        }
    }

    if (window.lucide) lucide.createIcons();
}

function showNotificationsPanel() {
    const existing = document.getElementById('notif-panel-overlay');
    if (existing) { existing.remove(); return; }

    currentNotifPage = 1;
    const notifs = window.OctaQube.notifications || [];
    const activeNotifs = notifs.filter(n => !n.is_read || n.is_starred);

    const annCount = activeNotifs.filter(n => n.is_announcement || (n.title && n.title.startsWith('📢'))).length;
    const alertCount = activeNotifs.filter(n => !n.is_announcement && !(n.title && n.title.startsWith('📢'))).length;

    const overlay = document.createElement('div');
    overlay.id = 'notif-panel-overlay';
    overlay.style.cssText = 'position:fixed; inset:0; z-index:19999;';
    overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };
    overlay.innerHTML = `
        <div id="notif-panel" style="position:fixed; top:64px; right:16px; width:380px; background:var(--ds-bg-surface); border-radius:18px; box-shadow:0 20px 60px rgba(0,0,0,0.25); border: 1px solid var(--ds-glass-border); z-index:20000; overflow:hidden;">
            <div class="p-3 border-bottom d-flex justify-content-between align-items-center" style="border-color: var(--ds-border-color) !important;">
                <div class="d-flex align-items-center gap-2">
                    <span class="fw-bold" style="color: var(--ds-text-main); font-size:15px;">Notifications</span>
                    <span class="badge rounded-pill bg-primary bg-opacity-15 text-primary text-xxs font-monospace">${activeNotifs.length}</span>
                </div>
                <div class="d-flex align-items-center gap-2">
                    <button class="btn btn-sm btn-link text-decoration-none text-xs p-0 text-muted" onclick="OctaQube.markNotificationsAsRead()">Mark Read</button>
                    <span class="text-muted opacity-50">&bull;</span>
                    <button class="btn btn-sm btn-link text-decoration-none text-xs p-0 text-danger" onclick="OctaQube.clearNotifications(); switchNotifTab(currentNotifFilterTab, 1);">Clear All</button>
                </div>
            </div>

            <!-- Category Tabs: All / Announcements / System Alerts -->
            <div class="d-flex gap-1 p-2 border-bottom" style="border-color: var(--ds-border-color) !important; background:rgba(255,255,255,0.02);">
                <button type="button" class="notif-tab-btn btn btn-sm py-1 px-2.5 text-xs rounded-pill border" data-tab="all" onclick="switchNotifTab('all', 1)">
                    All <span class="opacity-75">(${activeNotifs.length})</span>
                </button>
                <button type="button" class="notif-tab-btn btn btn-sm py-1 px-2.5 text-xs rounded-pill border" data-tab="announcements" onclick="switchNotifTab('announcements', 1)">
                    📢 Announcements <span class="opacity-75">(${annCount})</span>
                </button>
                <button type="button" class="notif-tab-btn btn btn-sm py-1 px-2.5 text-xs rounded-pill border" data-tab="alerts" onclick="switchNotifTab('alerts', 1)">
                    🔔 Alerts <span class="opacity-75">(${alertCount})</span>
                </button>
            </div>

            <div id="notif-items-container" class="p-2" style="max-height:360px; overflow-y:auto; background: var(--ds-bg-surface);">
                <!-- Loaded dynamically by switchNotifTab -->
            </div>

            <!-- 10-Item Pagination Controls -->
            <div id="notif-pagination-container" class="p-2 px-3 border-top d-flex justify-content-between align-items-center" style="border-color: var(--ds-border-color) !important; background:rgba(0,0,0,0.03);">
            </div>

            <div class="p-2.5 border-top text-center" style="border-color: var(--ds-border-color) !important; background:rgba(0,0,0,0.05);">
                <button class="btn btn-sm btn-link text-primary text-decoration-none fw-bold text-xs" onclick="document.getElementById('notif-panel-overlay').remove(); UserAnnouncementsModal.open();">
                    📢 View All Platform Announcements &rarr;
                </button>
            </div>
        </div>
    `;
    document.body.appendChild(overlay);
    switchNotifTab(currentNotifFilterTab || 'all', 1);
}

// Expose OctaQube globally (with backwards compatibility alias)
window.OctaQube = OctaQube;
window.QCMS = OctaQube;
var QCMS = OctaQube;

OctaQube.escapeHtml = function(str) {
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
};

// Dynamic Organization Category Manager
OctaQube._cachedCategories = null;
OctaQube._categoryFetchPromise = null;

OctaQube.loadCategories = async function(forceRefresh = false) {
    if (OctaQube._cachedCategories && !forceRefresh) {
        return OctaQube._cachedCategories;
    }
    if (OctaQube._categoryFetchPromise && !forceRefresh) {
        return OctaQube._categoryFetchPromise;
    }

    const defaultCategories = ['Quality', 'Cost', 'Delivery', 'Safety', 'Morale', 'Environment', 'Productivity'];

    OctaQube._categoryFetchPromise = (async () => {
        try {
            if (typeof api !== 'undefined' && typeof api.get === 'function') {
                const res = await api.get('/sop/masters');
                if (res && Array.isArray(res.categories) && res.categories.length > 0) {
                    const loaded = res.categories.map(c => typeof c === 'string' ? c : (c.name || '')).filter(Boolean);
                    if (loaded.length > 0) {
                        OctaQube._cachedCategories = loaded;
                        return loaded;
                    }
                }
            }
        } catch (e) {
            console.warn('Could not fetch categories from server, using defaults:', e);
        }
        OctaQube._cachedCategories = defaultCategories;
        return defaultCategories;
    })();

    return OctaQube._categoryFetchPromise;
};

OctaQube.populateCategorySelects = async function(targetContainer) {
    try {
        const categories = await OctaQube.loadCategories();
        const root = targetContainer || document;
        
        const selects = root.querySelectorAll(`
            select#categoryFilter,
            select#filterCategory,
            select#initCategory,
            select#projCategory,
            select#projectCategory,
            select#s8_sop_category,
            select#s1_init_category,
            select[name="category"],
            select[name="project_category"],
            select[data-source="categories"],
            select[data-source="sop_categories"]
        `);

        selects.forEach(select => {
            const currentVal = select.value;
            const isFilter = select.id.toLowerCase().includes('filter') || select.classList.contains('filter-select') || (select.name && select.name.includes('filter'));
            const placeholderText = isFilter ? 'All Categories' : '-- Select Category --';
            
            let optionsHtml = `<option value="">${placeholderText}</option>`;
            categories.forEach(cat => {
                const isSelected = (currentVal === cat) ? ' selected' : '';
                optionsHtml += `<option value="${OctaQube.escapeHtml(cat)}"${isSelected}>${OctaQube.escapeHtml(cat)}</option>`;
            });

            select.innerHTML = optionsHtml;
            if (currentVal && categories.includes(currentVal)) {
                select.value = currentVal;
            }
        });
    } catch (err) {
        console.warn('Error in populateCategorySelects:', err);
    }
};

// Standardized Icon Refresh
OctaQube.refreshIcons = function() {
    if (window.lucide) {
        window.lucide.createIcons({
            attrs: {
                'stroke-width': 2.2,
                'class': 'ds-icon'
            }
        });
    }
};

// Auto-populate Category dropdowns on page load and modal open
document.addEventListener('DOMContentLoaded', () => {
    OctaQube.populateCategorySelects();
});

OctaQube.showDecisionConfirmationDialog = function({
    decision,
    projectTitle = '',
    stageNumber = null,
    comments = '',
    onConfirm = () => {},
    onCancel = () => {}
}) {
    const existing = document.getElementById('octaqube-decision-confirm-modal');
    if (existing) existing.remove();

    const normalized = (decision === 'SendToCEO' || decision === 'send_to_ceo' || decision === 'Send to CEO') ? 'SendToCEO' :
                       (decision === 'Approved' || decision === 'approved' || decision === 'Approve') ? 'Approved' :
                       (decision === 'Rejected' || decision === 'rejected' || decision === 'Reject') ? 'Rejected' :
                       'Revision';

    const configs = {
        'Approved': {
            title: 'Confirm Project Stage Approval',
            badge: stageNumber === 8 ? 'Final Closure Sign-Off' : `Stage ${stageNumber || ''} Approval`,
            badgeClass: 'bg-success text-white',
            borderColor: '#10b981',
            icon: 'check-circle-2',
            iconColor: '#10b981',
            btnClass: 'ds-btn ds-btn-primary',
            btnStyle: 'background:#10b981; border-color:#10b981; color:#fff;',
            confirmText: 'Yes, Approve & Advance',
            impacts: [
                { icon: 'arrow-right-circle', text: stageNumber === 8 ? '<strong>Project Closure:</strong> Formally marks this project as Completed & archives it in the Knowledge Repository.' : `<strong>Stage Progression:</strong> Automatically advances the project to <strong>Stage ${(stageNumber || 0) + 1}</strong> and unlocks next deliverables.` },
                { icon: 'award', text: '<strong>Recognition & Points:</strong> Officially credits nominated team awards and leaderboard rewards to all participating members.' },
                { icon: 'shield-check', text: '<strong>Quality Gate Pass:</strong> Permanently locks review sign-off in the enterprise immutable audit trail.' }
            ]
        },
        'Revision': {
            title: 'Confirm Revision Request',
            badge: `Stage ${stageNumber || ''} Revision`,
            badgeClass: 'bg-warning text-dark',
            borderColor: '#f59e0b',
            icon: 'rotate-ccw',
            iconColor: '#f59e0b',
            btnClass: 'ds-btn ds-btn-secondary',
            btnStyle: 'background:#f59e0b; border-color:#f59e0b; color:#fff;',
            confirmText: 'Send Revision Request',
            impacts: [
                { icon: 'unlock', text: '<strong>Stage Reopened:</strong> Unlocks editing permissions for the Team Leader and members to update their inputs.' },
                { icon: 'bell', text: '<strong>Team Notification:</strong> Dispatches high-priority notification with your reviewer feedback comments.' },
                { icon: 'clock', text: '<strong>Pending Re-submission:</strong> Project remains in Revision Required state until the team submits updated deliverables.' }
            ]
        },
        'Rejected': {
            title: 'Confirm Project Rejection',
            badge: 'Irreversible Action',
            badgeClass: 'bg-danger text-white',
            borderColor: '#ef4444',
            icon: 'alert-octagon',
            iconColor: '#ef4444',
            btnClass: 'ds-btn ds-btn-danger',
            btnStyle: 'background:#ef4444; border-color:#ef4444; color:#fff;',
            confirmText: 'Yes, Reject Project',
            impacts: [
                { icon: 'alert-triangle', text: '<strong>Workflow Terminated:</strong> Project progress is halted and locked across all 8 stages.' },
                { icon: 'lock', text: '<strong>Read-Only Lock:</strong> Team members will no longer be permitted to edit or advance this project.' },
                { icon: 'file-x', text: '<strong>Stakeholder Notification:</strong> Detailed rejection rationale is recorded in audit logs and sent to project sponsor.' }
            ]
        },
        'SendToCEO': {
            title: 'Forward Project to CEO for Executive Review',
            badge: 'Executive Escalation',
            badgeClass: 'bg-primary text-white',
            borderColor: '#6366f1',
            icon: 'send',
            iconColor: '#6366f1',
            btnClass: 'ds-btn ds-btn-primary',
            btnStyle: 'background:#6366f1; border-color:#6366f1; color:#fff;',
            confirmText: 'Forward to CEO Dashboard',
            impacts: [
                { icon: 'crown', text: '<strong>Executive Dossier:</strong> Sends the complete 8-stage project dossier directly to the CEO Dashboard.' },
                { icon: 'sparkles', text: '<strong>Strategic Recognition:</strong> Flags this project for executive review, corporate awards, and multi-plant scaling.' },
                { icon: 'check-square', text: '<strong>Executive Closure:</strong> Final project closure and executive sign-off will be performed by the CEO.' }
            ]
        }
    };

    const cfg = configs[normalized] || configs['Revision'];

    const modalHtml = `
        <div class="modal fade" id="octaqube-decision-confirm-modal" tabindex="-1" style="z-index: 10050;">
            <div class="modal-dialog modal-dialog-centered" style="max-width: 520px;">
                <div class="modal-content" style="border-radius: 16px; border: 1px solid ${cfg.borderColor}40; box-shadow: 0 25px 60px rgba(0,0,0,0.3); background: var(--ds-bg-card, #ffffff); overflow: hidden;">
                    
                    <!-- Header -->
                    <div class="p-4 d-flex align-items-start gap-3 border-bottom" style="background: var(--ds-bg-elevated, #f8fafc);">
                        <div style="width: 44px; height: 44px; border-radius: 12px; background: ${cfg.iconColor}15; display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                            <i data-lucide="${cfg.icon}" style="width: 24px; height: 24px; color: ${cfg.iconColor};"></i>
                        </div>
                        <div style="flex: 1;">
                            <div class="d-flex align-items-center gap-2 mb-1">
                                <span class="badge ${cfg.badgeClass}" style="font-size: 0.7rem; padding: 3px 8px; border-radius: 6px;">${cfg.badge}</span>
                                ${stageNumber ? `<span class="text-xs text-muted fw-bold">Stage ${stageNumber}</span>` : ''}
                            </div>
                            <h5 class="modal-title fw-bold text-dark mb-0" style="font-size: 1.1rem;">${cfg.title}</h5>
                            ${projectTitle ? `<div class="text-xs text-secondary text-truncate mt-1" style="max-width: 380px;">Project: <strong>${OctaQube.escapeHtml(projectTitle)}</strong></div>` : ''}
                        </div>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>

                    <!-- Body / Impact Explanation -->
                    <div class="p-4">
                        <div class="text-xs text-uppercase fw-bold text-muted mb-2 letter-spacing-1">
                            <i data-lucide="info" style="width: 13px; height: 13px; margin-right: 4px;"></i> Action Impact & Next Steps:
                        </div>
                        
                        <div class="d-flex flex-column gap-3 p-3 rounded-3 mb-3 border" style="background: var(--ds-bg-surface, #f8fafc);">
                            ${cfg.impacts.map(imp => `
                                <div class="d-flex align-items-start gap-2 text-xs" style="line-height: 1.5; color: var(--ds-text-main, #1e293b);">
                                    <i data-lucide="${imp.icon}" style="width: 16px; height: 16px; color: ${cfg.iconColor}; flex-shrink: 0; margin-top: 2px;"></i>
                                    <div>${imp.text}</div>
                                </div>
                            `).join('')}
                        </div>

                        ${comments ? `
                            <div class="p-2 px-3 rounded-2 text-xs border" style="background: rgba(0,0,0,0.02);">
                                <span class="text-muted fw-bold">Reviewer Feedback:</span>
                                <div class="text-secondary italic text-truncate" style="max-height: 40px; overflow-y: auto;">"${OctaQube.escapeHtml(comments)}"</div>
                            </div>
                        ` : ''}
                    </div>

                    <!-- Footer Buttons -->
                    <div class="p-3 px-4 border-top d-flex justify-content-end gap-2" style="background: var(--ds-bg-elevated, #f8fafc);">
                        <button type="button" class="ds-btn ds-btn-ghost ds-btn-sm" data-bs-dismiss="modal" id="octaqube-btn-cancel-decision">
                            Cancel
                        </button>
                        <button type="button" class="${cfg.btnClass} ds-btn-sm fw-bold" style="${cfg.btnStyle}" id="octaqube-btn-confirm-decision">
                            ${cfg.confirmText}
                        </button>
                    </div>

                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHtml);
    const modalEl = document.getElementById('octaqube-decision-confirm-modal');
    const bsModal = new bootstrap.Modal(modalEl, { backdrop: 'static' });

    if (window.lucide) lucide.createIcons({ root: modalEl });

    document.getElementById('octaqube-btn-confirm-decision').onclick = () => {
        bsModal.hide();
        setTimeout(() => {
            modalEl.remove();
            onConfirm();
        }, 200);
    };

    document.getElementById('octaqube-btn-cancel-decision').onclick = () => {
        onCancel();
    };

    modalEl.addEventListener('hidden.bs.modal', () => {
        modalEl.remove();
    });

    bsModal.show();
};

// Global calendar picker activator: opening calendar on click for date/datetime inputs
document.addEventListener('click', (e) => {
    const target = e.target;
    if (target && target.tagName === 'INPUT' && ['date', 'datetime-local', 'time', 'month'].includes(target.type)) {
        if (typeof target.showPicker === 'function') {
            try {
                target.showPicker();
            } catch (err) {
                // Ignore if already open or disallowed
            }
        }
    }
});

OctaQube.init();

function updateChartTheme(theme) {
    if (typeof Chart === 'undefined') return;
    const isDark = theme === 'dark';
    const textColor = isDark ? '#e2e8f0' : '#475569';
    const gridColor = isDark ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';
    const borderColor = isDark ? 'rgba(255, 255, 255, 0.2)' : 'rgba(0, 0, 0, 0.1)';
    
    if (Chart.defaults) {
        // Chart.js v3/v4 defaults
        Chart.defaults.color = textColor;
        Chart.defaults.borderColor = borderColor;
        
        // Scale grid defaults
        if (Chart.defaults.scale && Chart.defaults.scale.grid) {
            Chart.defaults.scale.grid.color = gridColor;
        }
        if (Chart.defaults.scales) {
            Object.values(Chart.defaults.scales).forEach(scale => {
                if (scale.grid) scale.grid.color = gridColor;
                if (scale.ticks) scale.ticks.color = textColor;
            });
        }
        
        // Update all active instances
        if (Chart.instances) {
            Object.values(Chart.instances).forEach(chart => {
                // Update scales
                if (chart.options.scales) {
                    Object.values(chart.options.scales).forEach(scale => {
                        if (scale.ticks) scale.ticks.color = textColor;
                        if (scale.grid) scale.grid.color = gridColor;
                        if (scale.title) scale.title.color = textColor;
                    });
                }
                
                // Update legend/title plugins
                if (chart.options.plugins) {
                    if (chart.options.plugins.legend && chart.options.plugins.legend.labels) {
                        chart.options.plugins.legend.labels.color = textColor;
                    }
                    if (chart.options.plugins.title) {
                        chart.options.plugins.title.color = textColor;
                    }
                }
                
                // Dynamic dataset styling for dark mode/light mode
                if (chart.data && chart.data.datasets) {
                    chart.data.datasets.forEach(dataset => {
                        // Swap white border in dark mode to dark border
                        if (dataset.borderColor === '#ffffff') {
                            dataset.borderColor = isDark ? '#1e293b' : '#ffffff';
                        } else if (dataset.borderColor === '#1e293b') {
                            dataset.borderColor = isDark ? '#1e293b' : '#ffffff';
                        }
                        
                        // Pie/Doughnut charts slate color array replacement
                        if (chart.config.type === 'doughnut' || chart.config.type === 'pie') {
                            const isSlateArray = Array.isArray(dataset.backgroundColor) && dataset.backgroundColor.includes('#334155');
                            const isHighContrastDarkPalette = Array.isArray(dataset.backgroundColor) && dataset.backgroundColor.includes('#60a5fa');
                            
                            if (isDark && (isSlateArray || !isHighContrastDarkPalette)) {
                                if (!dataset._originalBg) dataset._originalBg = dataset.backgroundColor;
                                dataset.backgroundColor = ['#60a5fa', '#2dd4bf', '#818cf8', '#a78bfa', '#f472b6', '#34d399'];
                            } else if (!isDark && dataset._originalBg) {
                                dataset.backgroundColor = dataset._originalBg;
                            }
                        }
                    });
                }
                
                chart.update();
            });
        }
    }
}

window.addEventListener('octaqube-theme-change', e => {
    updateChartTheme(e.detail.theme);
});

window.addEventListener('load', () => {
    const theme = localStorage.getItem('octaqube-theme') || 'light';
    updateChartTheme(theme);
});

// Global JS Error Boundary for Production Hardening
window.addEventListener('error', function(event) {
    console.error('[OctaQube Error Boundary]', event.error || event.message);
    // Only log — individual components handle their own errors via try/catch
});

window.addEventListener('unhandledrejection', function(event) {
    const reason = event.reason;
    console.error('[OctaQube Unhandled Rejection]', reason);
    
    // Only show toast for actual network/fetch failures, not JS TypeErrors
    const isNetworkError = reason instanceof TypeError && 
        (String(reason.message).includes('fetch') || String(reason.message).includes('network') || String(reason.message).includes('Failed to fetch'));
    
    if (isNetworkError && typeof OctaQube !== 'undefined' && typeof OctaQube.toast === 'function') {
        OctaQube.toast('Network connection error. Please check your connection.', 'error');
    }
    
    // Prevent browser from logging the unhandled rejection in console (we already logged it)
    event.preventDefault();
});


// ─── Global Announcement Banner & User Modal Components ────────────────────────

const GlobalAnnouncementBanner = {
    activeAnnouncements: [],
    currentIndex: 0,

    async init() {
        // Sticky header banner removed per UX requirement — all announcements are routed under the Notifications Tab
        const existing = document.getElementById('global-announcement-banner-container');
        if (existing) existing.remove();

        await this.fetchActiveAnnouncements();

        window.addEventListener('octaqube:announcement-published', () => {
            this.fetchActiveAnnouncements();
            if (window.OctaQube && typeof OctaQube.loadNotifications === 'function') {
                OctaQube.loadNotifications();
            }
        });
    },

    async fetchActiveAnnouncements() {
        try {
            const res = await api.get('/announcements/user-active');
            if (res && res.status === 'success' && Array.isArray(res.data)) {
                this.activeAnnouncements = res.data.filter(a => !a.is_dismissed);
                if (window.OctaQube && typeof OctaQube.loadNotifications === 'function') {
                    OctaQube.loadNotifications();
                }
            }
        } catch (e) {
            // Silently ignore if announcements cannot be loaded
        }
    },

    render() {
        // Top header banner is completely disabled
        const container = document.getElementById('global-announcement-banner-container');
        if (container) container.remove();
    },

    openDetailModal(annId) {
        const ann = this.activeAnnouncements.find(a => a.id === annId);
        if (!ann) return;
        
        api.post(`/announcements/${annId}/mark-read`).catch(() => {});

        const oldModal = document.getElementById('user-ann-reader-modal');
        if (oldModal) oldModal.remove();

        const modalEl = document.createElement('div');
        modalEl.id = 'user-ann-reader-modal';
        modalEl.className = 'modal fade show';
        modalEl.style.cssText = 'display:block; background:rgba(0,0,0,0.65); z-index:20600; backdrop-filter:blur(4px);';

        modalEl.innerHTML = `
            <div class="modal-dialog modal-dialog-centered modal-lg">
                <div class="modal-content glass-card border-0" style="background:var(--ds-bg-surface); border:1px solid var(--ds-border-color)!important; border-radius:16px;">
                    <div class="modal-header border-bottom p-3" style="border-color:var(--ds-border-color)!important;">
                        <div class="d-flex align-items-center gap-2">
                            <span class="badge bg-primary bg-opacity-10 text-primary border border-primary border-opacity-25 text-xs">${ann.category}</span>
                            <span class="badge ${ann.priority === 'Critical' ? 'bg-danger' : ann.priority === 'High' ? 'bg-warning text-dark' : 'bg-info'} text-xs">${ann.priority}</span>
                            <h6 class="modal-title fw-bold mb-0 text-main ms-2">${OctaQube.escapeHtml(ann.title)}</h6>
                        </div>
                        <button type="button" class="btn-close" style="filter:var(--ds-icon-filter, none);" onclick="document.getElementById('user-ann-reader-modal').remove()"></button>
                    </div>
                    <div class="modal-body p-4" style="max-height:65vh; overflow-y:auto;">
                        <div class="text-xxs text-secondary mb-3">
                            Published by <strong>${OctaQube.escapeHtml(ann.created_by)}</strong> on ${ann.published_at ? new Date(ann.published_at).toLocaleString() : 'Recently'}
                        </div>
                        ${ann.summary ? `<div class="p-3 bg-body-tertiary rounded-3 mb-3 text-xs text-secondary border" style="border-color:var(--ds-border-color)!important;"><strong>Summary:</strong> ${OctaQube.escapeHtml(ann.summary)}</div>` : ''}
                        <div class="text-sm text-main leading-relaxed" style="white-space:pre-wrap;">
                            ${ann.body || 'No detailed message provided.'}
                        </div>
                    </div>
                    <div class="modal-footer border-top p-3 d-flex justify-content-between align-items-center" style="border-color:var(--ds-border-color)!important;">
                        <button class="btn btn-sm btn-outline-secondary" onclick="GlobalAnnouncementBanner.dismiss(${ann.id}); document.getElementById('user-ann-reader-modal').remove();">
                            Dismiss Banner
                        </button>
                        <button class="ds-btn ds-btn-primary ds-btn-sm" onclick="document.getElementById('user-ann-reader-modal').remove();">
                            Close
                        </button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modalEl);
        if (window.lucide) lucide.createIcons();
    }
};


const UserAnnouncementsModal = {
    async open() {
        const oldModal = document.getElementById('user-announcements-modal-container');
        if (oldModal) oldModal.remove();

        const modalEl = document.createElement('div');
        modalEl.id = 'user-announcements-modal-container';
        modalEl.className = 'modal fade show';
        modalEl.style.cssText = 'display:block; background:rgba(0,0,0,0.65); z-index:20550; backdrop-filter:blur(4px);';

        modalEl.innerHTML = `
            <div class="modal-dialog modal-xl modal-dialog-centered modal-dialog-scrollable">
                <div class="modal-content glass-card border-0" style="background:var(--ds-bg-surface); border:1px solid var(--ds-border-color)!important; border-radius:16px;">
                    <div class="modal-header border-bottom p-3" style="border-color:var(--ds-border-color)!important;">
                        <div class="d-flex align-items-center gap-2">
                            <div class="p-2 rounded-circle bg-primary bg-opacity-10 text-primary">
                                <i data-lucide="megaphone" style="width:20px;height:20px;"></i>
                            </div>
                            <div>
                                <h5 class="modal-title fw-bold text-main mb-0">Platform Announcements & Broadcasts</h5>
                                <span class="text-xxs text-secondary">Official messages and alerts targeted to your organization</span>
                            </div>
                        </div>
                        <button type="button" class="btn-close" style="filter:var(--ds-icon-filter, none);" onclick="document.getElementById('user-announcements-modal-container').remove()"></button>
                    </div>
                    
                    <div class="p-3 border-bottom d-flex flex-wrap align-items-center justify-content-between gap-3" style="border-color:var(--ds-border-color)!important; background:rgba(255,255,255,0.01);">
                        <div class="d-flex align-items-center gap-2">
                            <input type="text" class="ds-input py-1 px-3 text-xs" style="width:220px;" placeholder="Search announcements..." id="userAnnSearch" oninput="UserAnnouncementsModal.loadData()">
                            <select class="ds-input ds-select py-1 px-2 text-xs" id="userAnnCategory" onchange="UserAnnouncementsModal.loadData()">
                                <option value="">All Categories</option>
                                <option value="General">General</option>
                                <option value="Maintenance">Maintenance</option>
                                <option value="Security">Security Alert</option>
                                <option value="Feature Release">Feature Release</option>
                            </select>
                        </div>
                        <div class="form-check form-switch text-xs mb-0">
                            <input class="form-check-input" type="checkbox" id="userAnnUnreadOnly" onchange="UserAnnouncementsModal.loadData()">
                            <label class="form-check-input-label text-secondary fw-semibold" for="userAnnUnreadOnly">Unread Only</label>
                        </div>
                    </div>

                    <div class="modal-body p-4" id="userAnnModalBody" style="min-height:350px;">
                        <div class="text-center py-5"><div class="spinner-border text-primary"></div></div>
                    </div>

                    <div class="modal-footer border-top p-3" style="border-color:var(--ds-border-color)!important;">
                        <button class="ds-btn ds-btn-secondary ds-btn-sm" onclick="document.getElementById('user-announcements-modal-container').remove()">Close</button>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modalEl);
        if (window.lucide) lucide.createIcons();
        await this.loadData();
    },

    async loadData() {
        const body = document.getElementById('userAnnModalBody');
        if (!body) return;

        const q = (document.getElementById('userAnnSearch')?.value || '').trim();
        const cat = document.getElementById('userAnnCategory')?.value || '';
        const unread = document.getElementById('userAnnUnreadOnly')?.checked || false;

        let params = new URLSearchParams();
        if (q) params.append('q', q);
        if (cat) params.append('category', cat);
        if (unread) params.append('unread_only', 'true');

        try {
            const res = await api.get(`/announcements/my-announcements?${params.toString()}`);
            if (res.status !== 'success') throw new Error('Load failed');

            const list = res.data || [];
            if (list.length === 0) {
                body.innerHTML = `
                    <div class="text-center py-5 text-secondary">
                        <i data-lucide="inbox" class="mb-2 opacity-50" style="width:40px;height:40px;"></i>
                        <p class="mb-0 text-sm">No announcements found matching criteria.</p>
                    </div>
                `;
                if (window.lucide) lucide.createIcons();
                return;
            }

            body.innerHTML = `
                <div class="table-responsive">
                    <table class="ds-table align-middle mb-0" style="width:100%;">
                        <thead>
                            <tr class="text-uppercase text-xxs text-secondary border-bottom">
                                <th style="width:110px; padding:12px 14px;">Priority</th>
                                <th style="width:130px; padding:12px 14px;">Category</th>
                                <th style="padding:12px 14px;">Announcement Details</th>
                                <th style="width:180px; padding:12px 14px;">Author & Date</th>
                                <th style="width:140px; padding:12px 14px; text-align:right;">Status / Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${list.map(a => {
                                let priorityStyle = 'background:#2563eb; color:#ffffff;';
                                const pUpper = (a.priority || '').toUpperCase();
                                if (pUpper.includes('CRITICAL')) priorityStyle = 'background:#dc2626; color:#ffffff;';
                                else if (pUpper.includes('HIGH')) priorityStyle = 'background:#ea580c; color:#ffffff;';
                                else if (pUpper.includes('MEDIUM')) priorityStyle = 'background:#2563eb; color:#ffffff;';
                                else if (pUpper.includes('LOW')) priorityStyle = 'background:#64748b; color:#ffffff;';

                                const catLabel = OctaQube.escapeHtml(a.category || 'General');
                                const isUnread = !a.is_read;

                                return `
                                    <tr class="border-bottom hover-bg" style="transition:background 0.15s ease;">
                                        <td style="padding:12px 14px;">
                                            <span class="badge rounded-pill px-2.5 py-1 text-xxs font-monospace fw-bold" style="${priorityStyle} display:inline-block; letter-spacing:0.5px; box-shadow:0 1px 2px rgba(0,0,0,0.1);">
                                                ${OctaQube.escapeHtml(a.priority || 'Medium')}
                                            </span>
                                        </td>
                                        <td style="padding:12px 14px;">
                                            <span class="badge rounded-pill px-2.5 py-1 text-xxs fw-semibold" style="background:rgba(148,163,184,0.12); color:var(--ds-text-main, #334155); border:1px solid rgba(148,163,184,0.3); display:inline-block;">
                                                ${catLabel}
                                            </span>
                                        </td>
                                        <td style="padding:12px 14px; max-width:340px;">
                                            <div class="fw-bold text-sm text-main mb-1" style="color:var(--ds-text-main); font-size:13.5px;">${OctaQube.escapeHtml(a.title)}</div>
                                            <div class="text-xs text-secondary text-truncate-2" style="line-height:1.45; color:var(--ds-text-muted, #64748b); font-size:12px;">${OctaQube.escapeHtml(a.summary || a.body || '')}</div>
                                        </td>
                                        <td style="padding:12px 14px;">
                                            <div class="text-xs fw-semibold text-main" style="color:var(--ds-text-main);">${OctaQube.escapeHtml(a.created_by || 'System Admin')}</div>
                                            <div class="text-xxs text-muted mt-0.5" style="font-size:11px;">${a.published_at ? new Date(a.published_at).toLocaleDateString() : 'Recently'}</div>
                                        </td>
                                        <td style="padding:12px 14px;" class="text-end">
                                            ${isUnread ? `
                                                <div class="d-flex flex-column align-items-end gap-1">
                                                    <span class="badge bg-success bg-opacity-15 text-success border border-success border-opacity-25 px-2 py-0.5 text-xxs font-monospace fw-bold">UNREAD</span>
                                                    <button class="btn btn-sm btn-link text-primary p-0 text-xxs fw-bold text-decoration-none" onclick="UserAnnouncementsModal.markRead(${a.id})">
                                                        Mark as Read &check;
                                                    </button>
                                                </div>
                                            ` : `
                                                <span class="badge bg-secondary bg-opacity-10 text-secondary border border-secondary border-opacity-25 px-2 py-0.5 text-xxs font-monospace">READ</span>
                                            `}
                                        </td>
                                    </tr>
                                `;
                            }).join('')}
                        </tbody>
                    </table>
                </div>
            `;
            if (window.lucide) lucide.createIcons();

        } catch (e) {
            body.innerHTML = `<div class="alert alert-danger">Error loading announcements.</div>`;
        }
    },

    async markRead(id) {
        try {
            await api.post(`/announcements/${id}/mark-read`);
            await this.loadData();
            if (window.GlobalAnnouncementBanner) {
                GlobalAnnouncementBanner.fetchActiveAnnouncements();
            }
        } catch (e) {}
    }
};

window.GlobalAnnouncementBanner = GlobalAnnouncementBanner;
window.UserAnnouncementsModal = UserAnnouncementsModal;



