/**
 * QCMS Enterprise - Shared UI Components
 * v1.0 - Handle sidebars, navbars, and role-based UI logic.
 */

// Auto-load FeatureEngine client and module map if not already present
(function loadFeatureEngine() {
    if (!window.QCMS_MODULE_MAP) {
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
                if (input && input.hasAttribute('required')) {
                    label.innerHTML = html.trim() + ' <span class="text-danger" style="color: #ef4444 !important; font-weight: bold; margin-left: 2px;">*</span>';
                }
            }
        });
    } catch (e) {
        console.warn('Asterisk label formatting error:', e);
    }
};

document.addEventListener('DOMContentLoaded', () => {
    window.ensureRedAsterisksOnLabels();
    if (window.QCMS && typeof window.QCMS.setActiveLink === 'function') {
        window.QCMS.setActiveLink();
    }
    setInterval(() => {
        window.ensureRedAsterisksOnLabels();
        if (window.QCMS && typeof window.QCMS.setActiveLink === 'function') {
            window.QCMS.setActiveLink();
        }
    }, 1500);
});

/**
 * Theme Manager Integration
 */
class ThemeManager {
    constructor() {
        this.theme = localStorage.getItem('qcms-theme') || 'light';
        this.init();
    }

    init() {
        this.applyTheme(this.theme);

        // Match system preference if not set
        if (!localStorage.getItem('qcms-theme')) {
            const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)');
            this.applyTheme(systemPrefersDark.matches ? 'dark' : 'light');
            systemPrefersDark.addEventListener('change', e => {
                if (!localStorage.getItem('qcms-theme')) {
                    this.applyTheme(e.matches ? 'dark' : 'light');
                }
            });
        }
    }

    applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        this.theme = theme;

        // Dispatch event
        window.dispatchEvent(new CustomEvent('qcms-theme-change', { detail: { theme } }));

        // Dynamic favicon or meta updates could go here
        if (window.lucide) lucide.createIcons();
    }

    toggle() {
        const newTheme = this.theme === 'light' ? 'dark' : 'light';
        localStorage.setItem('qcms-theme', newTheme);
        this.applyTheme(newTheme);
        return newTheme;
    }
}
window.themeManager = new ThemeManager();

/**
 * UI Utilities & Core Logic
 */
const QCMS = {
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

    init() {
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

        // Centralized Lucide config for premium look
        this.refreshIcons();

        // Apply white labeling / custom branding globally (from cached session)
        this.applyBranding();

        // Initialize UI components
        if (this.user) {
            this.renderSidebar();
            this.renderNavbar();
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
 
            // Async: Fetch fresh branding from server to keep org theme in sync
            // This ensures all org users always see the latest admin-configured colors/logos
            this.syncBrandingFromServer();
        }

        // Listen for theme changes to re-render
        window.addEventListener('qcms-theme-change', () => {
            if (this.user) this.renderNavbar();
        });

        // Listen for language changes to re-render
        window.addEventListener('qcms-language-change', () => {
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
                <button onclick="QCMS.exitImpersonation()" class="btn btn-sm btn-light py-0 px-2 fw-bold text-xs" style="color:rgb(var(--ds-orange-rgb)); border-radius: 4px; border:none; height:24px; line-height:1;">
                    Return to Super Admin
                </button>
            </div>
        `;
        document.body.appendChild(banner);
        document.body.style.paddingTop = '40px';
    },

    exitImpersonation() {
        const superToken = sessionStorage.getItem('super_admin_backup_token');
        if (superToken) {
            sessionStorage.setItem('token', superToken);
            sessionStorage.removeItem('super_admin_backup_token');
            sessionStorage.removeItem('user');
            window.location.href = '/admin/super-admin.html';
        }
    },

    /**
     * Fetch fresh branding data from /auth/me and update sessionStorage.
     * Called on every page load so org-wide changes are reflected in real time.
     */
    async syncBrandingFromServer() {
        try {
            const token = sessionStorage.getItem('token');
            if (!token) return;

            const response = await fetch('/api/auth/me', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!response.ok) return;

            const profile = await response.json();

            // Update session with latest org branding from server
            const userStr = sessionStorage.getItem('user');
            if (!userStr) return;
            const user = JSON.parse(userStr);

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
            console.debug('[QCMS] Branding sync skipped:', e.message);
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
            // Default QCMS Shield Favicon
            link.href = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="%230f172a" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path><path d="m9 12 2 2 4-4"></path></svg>';
        }

        // Update sidebar logo if it's already rendered
        const sidebarBrand = document.querySelector('.sidebar-brand');
        const orgName = (this.user && this.user.org_name) ? this.user.org_name : 'QCMS';
        if (sidebarBrand) {
            if (logoUrl && logoUrl !== 'null' && logoUrl !== 'None') {
                let img = sidebarBrand.querySelector('img');
                if (!img) {
                    sidebarBrand.innerHTML = `<img src="${logoUrl}" alt="Logo" style="width: 32px; height: 32px; object-fit: contain; border-radius: 8px;">
                                              <div class="brand-text">${QCMS.escapeHtml(orgName)} <small style="color:var(--ds-accent); opacity:1;">Workspace</small></div>`;
                } else {
                    img.src = logoUrl;
                    const bt = sidebarBrand.querySelector('.brand-text');
                    if (bt) bt.innerHTML = `${QCMS.escapeHtml(orgName)} <small style="color:var(--ds-accent); opacity:1;">Workspace</small>`;
                }
            } else {
                sidebarBrand.innerHTML = `<div class="brand-icon" style="background: var(--ds-accent);">
                                            <i data-lucide="shield-check" style="color:white;"></i>
                                          </div>
                                          <div class="brand-text">${QCMS.escapeHtml(orgName)} <small style="color:var(--ds-accent); opacity:1;">Enterprise OS</small></div>`;
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

    setupMobileSidebar() {
        let backdrop = document.getElementById('sidebar-backdrop');
        if (!backdrop) {
            backdrop = document.createElement('div');
            backdrop.id = 'sidebar-backdrop';
            backdrop.className = 'sidebar-backdrop';
            document.body.appendChild(backdrop);
        }

        const sidebar = document.getElementById('app-sidebar');
        const toggleBtn = document.getElementById('sidebar-toggle-btn');

        // Check saved desktop state
        if (localStorage.getItem('qcms-sidebar-collapsed') === 'true') {
            document.body.classList.add('sidebar-collapsed');
        }

        if (toggleBtn && sidebar && backdrop) {
            toggleBtn.onclick = (e) => {
                e.stopPropagation();
                if (window.innerWidth <= 1024) {
                    sidebar.classList.toggle('show');
                    backdrop.classList.toggle('show');
                } else {
                    document.body.classList.toggle('sidebar-collapsed');
                    localStorage.setItem('qcms-sidebar-collapsed', document.body.classList.contains('sidebar-collapsed'));
                    setTimeout(() => window.dispatchEvent(new Event('resize')), 350);
                }
            };

            backdrop.onclick = () => {
                sidebar.classList.remove('show');
                backdrop.classList.remove('show');
            };

            sidebar.querySelectorAll('.sidebar-link').forEach(link => {
                link.addEventListener('click', () => {
                    if (window.innerWidth <= 1024) {
                        sidebar.classList.remove('show');
                        backdrop.classList.remove('show');
                    }
                });
            });
        }
    },

    toggleSidebar() {
        if (window.innerWidth <= 1024) {
            const sidebar = document.getElementById('app-sidebar');
            const backdrop = document.getElementById('sidebar-backdrop');
            if (sidebar) sidebar.classList.toggle('show');
            if (backdrop) backdrop.classList.toggle('show');
        } else {
            document.body.classList.toggle('sidebar-collapsed');
            localStorage.setItem('qcms-sidebar-collapsed', document.body.classList.contains('sidebar-collapsed'));
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
        if (!user) return `<div class="avatar-fallback" style="width:${size}px;height:${size}px;">?</div>`;
        
        const name = user.full_name || user.username || 'User';
        const initials = name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase();
        
        if (user.profile_picture) {
            // Check if it's already a full URL
            let src = user.profile_picture;
            if (!src.startsWith('http')) {
                // Assume backend is on port 5000 if frontend is on different port, 
                // but usually the proxy handles /api and /uploads.
                // We fallback to relative path which is safest for most deployments.
                src = src.startsWith('/') ? src : '/' + src;
            }
            return `<img src="${src}" alt="${name}" style="width:${size}px; height:${size}px; object-fit:cover;" onerror="this.outerHTML='<div class=\'avatar-initials\' style=\'width:${size}px;height:${size}px;display:flex;align-items:center;justify-content:center;background:var(--ds-accent);color:white;font-weight:700;font-size:${size/2.5}px;\'>${initials}</div>';">`;
        }
        
        return `<div class="avatar-initials" style="width:${size}px;height:${size}px;display:flex;align-items:center;justify-content:center;background:var(--ds-accent);color:white;font-weight:700;font-size:${size/2.5}px;">${initials}</div>`;
    },

    /**
     * Premium Date Formatting
     */
    formatDate(dateStr) {
        if (!dateStr || dateStr === 'â€”') return 'â€”';
        let normalized = dateStr;
        if (typeof dateStr === 'string' && !dateStr.endsWith('Z') && !dateStr.includes('+')) normalized += 'Z';
        const date = new Date(normalized);
        if (isNaN(date.getTime())) return 'â€”';
        return date.toLocaleDateString('en-IN', { 
            day: '2-digit',
            month: 'short', 
            year: 'numeric' 
        });
    },

    /**
     * Premium Time Formatting
     */
    formatTime(dateStr) {
        if (!dateStr) return '';
        const d = new Date(dateStr);
        if (isNaN(d.getTime())) return '';
        return d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true });
    },

    /**
     * Relative Time (e.g. 2 hours ago)
     */
    formatRelative(dateStr) {
        if (!dateStr || dateStr === 'â€”') return 'â€”';
        let normalized = dateStr;
        if (typeof dateStr === 'string' && !dateStr.endsWith('Z') && !dateStr.includes('+')) normalized += 'Z';
        const date = new Date(normalized);
        if (isNaN(date.getTime())) return 'â€”';
        const diff = (new Date() - date) / 1000;
        if (diff < 60) return 'Just now';
        if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
        return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
    },

    /**
     * KPI Card Component â€” for dashboard grids
     */
    kpiCard(label, value, icon, color) {
        const hexMap = {
            blue: '#2563eb', green: '#10b981', red: '#ef4444',
            orange: '#f59e0b', purple: '#8b5cf6', cyan: '#06b6d4', gray: '#64748b'
        };
        const c = hexMap[color] || hexMap.blue;
        return `<div class="glass-card" style="padding: var(--ds-space-5); text-align: center;">
            <div style="width:40px;height:40px;border-radius:12px;background:${c}1f;display:flex;align-items:center;justify-content:center;margin:0 auto var(--ds-space-3);">
                <i data-lucide="${icon || 'hash'}" style="width:20px;height:20px;color:${c};"></i>
            </div>
            <div class="text-2xl fw-bold" style="color:var(--ds-text-main);">${value ?? '—'}</div>
            <div class="text-xs text-muted mt-1">${label}</div>
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
        
        return `<div class="glass-card position-relative clickable hover-shadow" style="padding: var(--ds-space-5); text-align: center; min-height: 140px; cursor: pointer;" ${extraAttrs}>
            <div class="position-absolute" style="top: 10px; right: 10px; z-index: 10;" onclick="event.stopPropagation()">
                <i data-lucide="info" class="text-muted" style="width: 14px; height: 14px; cursor: help;"
                   data-bs-toggle="tooltip" data-bs-html="true"
                   title="<strong>Formula:</strong> ${escCal}<br/><small class='text-muted'>${escDesc}<br/>As of: ${timestamp} (polls every 15m)</small>"></i>
            </div>
            <div style="width:40px;height:40px;border-radius:12px;background:${c}1f;display:flex;align-items:center;justify-content:center;margin:0 auto var(--ds-space-3);">
                <i data-lucide="${icon || 'hash'}" style="width:20px;height:20px;color:${c};"></i>
            </div>
            <div class="text-2xl fw-bold" style="color:var(--ds-text-main);">${value ?? '—'}</div>
            <div class="text-xs text-muted mt-1">${label}</div>
        </div>`;
    },

    /**
     * Status Badge Component
     */
    statusBadge(status) {
        const map = { 'Active': 'green', 'Trialing': 'orange', 'Suspended': 'red', 'Expired': 'gray', 'Pending': 'orange' };
        return `<span class="ds-badge ${map[status] || 'gray'}">${status}</span>`;
    },

    /**
     * Empty State Component
     */
    emptyState(title, message, icon) {
        return `<div style="text-align:center; padding: var(--ds-space-8) var(--ds-space-4);">
            <div style="width:56px;height:56px;border-radius:16px;background:rgba(var(--ds-primary-rgb),0.08);display:flex;align-items:center;justify-content:center;margin:0 auto var(--ds-space-4);">
                <i data-lucide="${icon || 'inbox'}" style="width:24px;height:24px;opacity:0.4;"></i>
            </div>
            <h6 class="fw-bold mb-1">${title}</h6>
            <p class="text-sm text-muted mb-0">${message}</p>
        </div>`;
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
                    <button class="ds-btn ds-btn-ghost p-1 me-2" id="sidebar-toggle-btn" style="width: 38px; height: 38px; display: flex; align-items: center; justify-content: center;">
                        <i data-lucide="menu" style="width: 22px; height: 22px;"></i>
                    </button>

                    <!-- Breadcrumb Placeholder -->
                    <div id="nav-breadcrumb-container" class="d-none d-lg-flex align-items-center px-3" style="min-width: 200px;"></div>
                </div>

                <div class="d-flex gap-2 gap-md-3 align-items-center">


                    <!-- Theme Toggle -->
                    <div class="theme-switcher-wrapper glass-panel p-1 d-flex gap-1" style="border-radius: 12px; background: rgba(var(--ds-primary-rgb), 0.03); border: 1px solid var(--ds-border-color);">
                        <button class="ds-btn ds-btn-icon ${!isDark ? 'ds-btn-primary' : 'ds-btn-ghost text-muted'}" 
                                style="width:32px; height:32px; border-radius: 8px; padding:0;" title="Light Mode"
                                data-i18n-title="navbar.light_mode"
                                onclick="window.themeManager.applyTheme('light'); localStorage.setItem('qcms-theme', 'light');">
                            <i data-lucide="sun" style="width:15px; height:15px;"></i>
                        </button>
                        <button class="ds-btn ds-btn-icon ${isDark ? 'ds-btn-primary' : 'ds-btn-ghost text-muted'}" 
                                style="width:32px; height:32px; border-radius: 8px; padding:0;" title="Dark Mode"
                                data-i18n-title="navbar.dark_mode"
                                onclick="window.themeManager.applyTheme('dark'); localStorage.setItem('qcms-theme', 'dark');">
                            <i data-lucide="moon" style="width:15px; height:15px;"></i>
                        </button>
                    </div>

                    <!-- Language Selector -->
                    <div class="dropdown" id="lang-selector-dropdown">
                        <button class="ds-btn ds-btn-ghost" 
                                style="width:42px; height:42px; border-radius:12px; padding:0; display:flex; align-items:center; justify-content:center; color:var(--ds-text-main); border: 1px solid transparent;" 
                                data-bs-toggle="dropdown" aria-expanded="false" title="Change Language" data-i18n-title="navbar.change_language">
                            <i data-lucide="languages" style="width:20px; height:20px;"></i>
                        </button>
                        <ul class="dropdown-menu dropdown-menu-end glass-dropdown" style="border-radius:12px; background:var(--ds-bg-surface); border: 1px solid var(--ds-glass-border); padding: 6px; box-shadow: var(--ds-shadow-lg);">
                            <li><a class="dropdown-item d-flex align-items-center gap-2 clickable ${window.i18n && window.i18n.getLanguage() === 'en' ? 'active' : ''}" onclick="window.i18n.setLanguage('en')" style="border-radius: 8px; font-weight: 500; font-size:14px; color:var(--ds-text-main);"><span style="width: 20px; font-size:11px; opacity:0.6;">EN</span>English</a></li>
                            <li><a class="dropdown-item d-flex align-items-center gap-2 clickable ${window.i18n && window.i18n.getLanguage() === 'hi' ? 'active' : ''}" onclick="window.i18n.setLanguage('hi')" style="border-radius: 8px; font-weight: 500; font-size:14px; color:var(--ds-text-main);"><span style="width: 20px; font-size:11px; opacity:0.6;">HI</span>हिन्दी (Hindi)</a></li>
                            <li><a class="dropdown-item d-flex align-items-center gap-2 clickable ${window.i18n && window.i18n.getLanguage() === 'kn' ? 'active' : ''}" onclick="window.i18n.setLanguage('kn')" style="border-radius: 8px; font-weight: 500; font-size:14px; color:var(--ds-text-main);"><span style="width: 20px; font-size:11px; opacity:0.6;">KN</span>ಕನ್ನಡ (Kannada)</a></li>
                            <li><a class="dropdown-item d-flex align-items-center gap-2 clickable ${window.i18n && window.i18n.getLanguage() === 'te' ? 'active' : ''}" onclick="window.i18n.setLanguage('te')" style="border-radius: 8px; font-weight: 500; font-size:14px; color:var(--ds-text-main);"><span style="width: 20px; font-size:11px; opacity:0.6;">TE</span>తెలుగు (Telugu)</a></li>
                            <li><a class="dropdown-item d-flex align-items-center gap-2 clickable ${window.i18n && window.i18n.getLanguage() === 'ta' ? 'active' : ''}" onclick="window.i18n.setLanguage('ta')" style="border-radius: 8px; font-weight: 500; font-size:14px; color:var(--ds-text-main);"><span style="width: 20px; font-size:11px; opacity:0.6;">TA</span>தமிழ் (Tamil)</a></li>
                            <li><a class="dropdown-item d-flex align-items-center gap-2 clickable ${window.i18n && window.i18n.getLanguage() === 'ml' ? 'active' : ''}" onclick="window.i18n.setLanguage('ml')" style="border-radius: 8px; font-weight: 500; font-size:14px; color:var(--ds-text-main);"><span style="width: 20px; font-size:11px; opacity:0.6;">ML</span>മലയാളം (Malayalam)</a></li>
                        </ul>
                    </div>

                    <!-- Notification Bell -->
                    <button id="notif-bell-btn" class="ds-btn ds-btn-ghost position-relative"
                            style="width:42px; height:42px; border-radius:12px; padding:0; display:flex; align-items:center; justify-content:center; color:var(--ds-text-main); border: 1px solid transparent;"
                            title="Notifications" data-i18n-title="navbar.notifications" onclick="showNotificationsPanel()">
                        <i data-lucide="bell" style="width:22px; height:22px;"></i>
                        <span id="notif-badge" style="position:absolute; top:8px; right:8px; width:11px; height:11px; background:#ef4444; border-radius:50%; border:2px solid var(--ds-bg-surface); display:block;"></span>
                    </button>

                    <div class="v-divider" style="height: 24px; width: 1px; background: var(--ds-border-color); opacity: 0.5;"></div>

                    <!-- User Badge -->
                    <div class="user-pill d-flex align-items-center gap-2 ps-1 pe-3 py-1 clickable glass-panel hover-shadow" 
                         style="border-radius: 14px; background: rgba(var(--ds-primary-rgb), 0.04); border: 1px solid var(--ds-border-color); transition: all 0.2s;" 
                         onclick="window.location.href='${user.role === 'SuperAdmin' ? '/admin/super-admin.html?view=settings' : '/admin/settings.html'}'">
                        <div class="user-avatar-sm d-flex align-items-center justify-content-center text-white" 
                             style="width:38px; height:38px; border-radius:12px; font-weight:700; font-size:15px; background: var(--ds-accent); overflow: hidden; border: 1px solid rgba(255,255,255,0.1);"
                             id="nav-user-avatar">
                            ${this.renderAvatar(user, 38)}
                        </div>
                        <div class="user-meta d-none d-sm-block text-start" style="line-height: 1.2;">
                            <div class="fw-bold" style="font-size: 14px; color: var(--ds-text-main);">${user.full_name || user.username || 'User'}</div>
                            <div class="text-secondary" style="font-size: 10px; font-weight: 700; text-transform: uppercase; opacity: 0.6; letter-spacing: 0.05em;" data-i18n="roles.${(user.role || 'Team Member').toLowerCase().replace(' ', '_')}">${user.role || 'Member'}</div>
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
                    window.dispatchEvent(new CustomEvent('qcms-global-search', { detail: { query: e.target.value } }));
                });
                document.addEventListener('keydown', (e) => {
                    if (e.key === '/' && document.activeElement.tagName !== 'INPUT' && document.activeElement.tagName !== 'TEXTAREA') {
                        e.preventDefault();
                        searchInput.focus();
                    }
                });
            }
        }, 100);

        QCMS.refreshIcons();
        if (window.Breadcrumbs) window.Breadcrumbs.init('nav-breadcrumb-container');
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
            ? (user.platform_short_name || user.software_name || user.software_display_name || 'QCMS')
            : (user.org_name || user.platform_short_name || 'QCMS');

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
        let brandNameHtml = `${QCMS.escapeHtml(shortName)} <small style="color:var(--ds-accent); opacity:1;">${QCMS.escapeHtml(displaySub)}</small>`;

        if (logoUrl && logoUrl !== 'null' && logoUrl !== 'None' && !logoUrl.includes('/assets/img/logo.png')) {
            logoIconHtml = `<img src="${logoUrl}" alt="Logo" style="width: 32px; height: 32px; object-fit: contain; border-radius: 8px;">`;
        }

        const brandHtml = `
            <div class="sidebar-brand">
                ${logoIconHtml}
                <div class="brand-text">
                    ${brandNameHtml}
                </div>
            </div>
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
                        <a href="/admin/super-admin.html?view=subscriptions" class="sidebar-link sa-compact-link" title="Subscriptions">
                            <i class="link-icon" data-lucide="repeat"></i>
                            <span>Subscriptions</span>
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
                        <a href="/admin/super-admin.html?view=recycle-bin" class="sidebar-link sa-compact-link" title="Recycle Bin">
                            <i class="link-icon" data-lucide="trash-2"></i>
                            <span>Recycle Bin</span>
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
                        <a href="#" class="sidebar-link sa-compact-link text-danger" onclick="QCMS.logout()">
                            <i class="link-icon" data-lucide="log-out"></i>
                            <span data-i18n="sidebar.links.logout">Logout</span>
                        </a>
                    </nav>
                </div>
            `;

        // â”€â”€ COMPANY ADMIN â€” Organization management â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        } else if (roleName === 'Admin') {
            sectionsHtml = `
                <div class="sidebar-section">
                    <div class="sidebar-section-label" data-i18n="sidebar.labels.main">Main</div>
                    <nav class="sidebar-nav">
                        <a href="/dashboard/dashboard-admin.html" class="sidebar-link">
                            <i class="link-icon" data-lucide="layout-dashboard"></i>
                            <span data-i18n="sidebar.links.overview">Overview</span>
                        </a>
                        <a href="/projects/projects-repository.html" class="sidebar-link">
                            <i class="link-icon" data-lucide="layers"></i>
                            <span data-i18n="sidebar.links.projects_repo">Project Repository</span>
                        </a>
                    </nav>
                </div>
                <div class="sidebar-section">
                    <div class="sidebar-section-label" data-i18n="sidebar.labels.administration">Administration</div>
                    <nav class="sidebar-nav">
                        <a href="/admin/users.html" class="sidebar-link">
                            <i class="link-icon" data-lucide="users"></i>
                            <span data-i18n="sidebar.links.user_management">User Management</span>
                        </a>
                        <a href="/admin/plants.html" class="sidebar-link">
                            <i class="link-icon" data-lucide="factory"></i>
                            <span>Plant Locations</span>
                        </a>
                        <a href="/admin/departments.html" class="sidebar-link">
                            <i class="link-icon" data-lucide="building-2"></i>
                            <span data-i18n="sidebar.links.departments">Departments</span>
                        </a>
                        <a href="/admin/audit-logs.html" class="sidebar-link">
                            <i class="link-icon" data-lucide="scroll-text"></i>
                            <span data-i18n="sidebar.links.audit_logs">Audit Logs</span>
                        </a>
                        <a href="/admin/stage-template.html" class="sidebar-link">
                            <i class="link-icon" data-lucide="layout-list"></i>
                            <span>8 Stage Template</span>
                        </a>
                    </nav>
                </div>
                <div class="sidebar-section">
                    <div class="sidebar-section-label" data-i18n="sidebar.labels.resources">Resources</div>
                    <nav class="sidebar-nav">
                        <a href="/projects/repository.html" class="sidebar-link">
                            <i class="link-icon" data-lucide="database"></i>
                            <span data-i18n="sidebar.links.knowledge_base">Knowledge Base</span>
                        </a>
                        <a href="/rewards/leaderboard.html" class="sidebar-link">
                            <i class="link-icon" data-lucide="award"></i>
                            <span>Leaderboard & Rewards</span>
                        </a>
                        <a href="/projects/additional-sources.html" class="sidebar-link">
                            <i class="link-icon" data-lucide="sparkles"></i>
                            <span>Additional Sources</span>
                        </a>
                    </nav>
                </div>
            `;
            footerHtml = `
                <div class="sidebar-footer">
                    <nav class="sidebar-nav">
                        <a href="/admin/settings.html" class="sidebar-link">
                            <i class="link-icon" data-lucide="settings"></i>
                            <span data-i18n="sidebar.links.settings">Settings</span>
                        </a>
                        <a href="#" class="sidebar-link text-danger" onclick="QCMS.logout()">
                            <i class="link-icon" data-lucide="log-out"></i>
                            <span data-i18n="sidebar.links.logout">Logout</span>
                        </a>
                    </nav>
                </div>
            `;

        // â”€â”€ TEAM LEADER â€” Project oversight â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        } else if (roleName === 'Team Leader') {
            sectionsHtml = `
                <div class="sidebar-section">
                    <div class="sidebar-section-label" data-i18n="sidebar.labels.main">Main</div>
                    <nav class="sidebar-nav">
                        <a href="/dashboard/dashboard-team-member.html" class="sidebar-link">
                            <i class="link-icon" data-lucide="layout-dashboard"></i>
                            <span data-i18n="sidebar.links.overview">Overview</span>
                        </a>
                        <a href="/projects/projects-repository.html" class="sidebar-link">
                            <i class="link-icon" data-lucide="layers"></i>
                            <span data-i18n="sidebar.links.projects_repo">Project Repository</span>
                        </a>
                        <a href="/analytics/analytics.html" class="sidebar-link">
                            <i class="link-icon" data-lucide="bar-chart-3"></i>
                            <span data-i18n="sidebar.links.analytics">Analytics</span>
                        </a>
                    </nav>
                </div>
                <div class="sidebar-section">
                    <div class="sidebar-section-label" data-i18n="sidebar.labels.resources">Resources</div>
                    <nav class="sidebar-nav">
                        <a href="/projects/repository.html" class="sidebar-link">
                            <i class="link-icon" data-lucide="database"></i>
                            <span data-i18n="sidebar.links.knowledge_base">Knowledge Base</span>
                        </a>
                    </nav>
                </div>
            `;
            footerHtml = `
                <div class="sidebar-footer">
                    <nav class="sidebar-nav">
                        <a href="/admin/settings.html" class="sidebar-link">
                            <i class="link-icon" data-lucide="settings"></i>
                            <span data-i18n="sidebar.links.settings">Settings</span>
                        </a>
                        <a href="#" class="sidebar-link text-danger" onclick="QCMS.logout()">
                            <i class="link-icon" data-lucide="log-out"></i>
                            <span data-i18n="sidebar.links.logout">Logout</span>
                        </a>
                    </nav>
                </div>
            `;

        // ─── FACILITATOR — Validation support ───────────────────────
        } else if (roleName === 'Facilitator') {
            const isNA = user.department === 'N/A';
            const resourcesSection = isNA ? '' : `
                <div class="sidebar-section">
                    <div class="sidebar-section-label" data-i18n="sidebar.labels.resources">Resources</div>
                    <nav class="sidebar-nav">
                        <a href="/projects/repository.html" class="sidebar-link">
                            <i class="link-icon" data-lucide="database"></i>
                            <span data-i18n="sidebar.links.knowledge_base">Knowledge Base</span>
                        </a>
                    </nav>
                </div>
            `;

            sectionsHtml = `
                <div class="sidebar-section">
                    <div class="sidebar-section-label" data-i18n="sidebar.labels.main">Main</div>
                    <nav class="sidebar-nav">
                        <a href="/dashboard/dashboard-facilitator.html" class="sidebar-link">
                            <i class="link-icon" data-lucide="layout-dashboard"></i>
                            <span data-i18n="sidebar.links.overview">Overview</span>
                        </a>
                        <a href="/analytics/analytics.html" class="sidebar-link">
                            <i class="link-icon" data-lucide="bar-chart-3"></i>
                            <span data-i18n="sidebar.links.analytics">Analytics</span>
                        </a>
                    </nav>
                </div>
                ${resourcesSection}
            `;
            footerHtml = `
                <div class="sidebar-footer">
                    <nav class="sidebar-nav">
                        <a href="/admin/settings.html" class="sidebar-link">
                            <i class="link-icon" data-lucide="settings"></i>
                            <span data-i18n="sidebar.links.settings">Settings</span>
                        </a>
                        <a href="#" class="sidebar-link text-danger" onclick="QCMS.logout()">
                            <i class="link-icon" data-lucide="log-out"></i>
                            <span data-i18n="sidebar.links.logout">Logout</span>
                        </a>
                    </nav>
                </div>
            `;

        // ─── REVIEWER — Approval flow ──────────────────────────────
        } else if (roleName === 'Reviewer') {
            const isNA = user.department === 'N/A';
            const resourcesSection = isNA ? '' : `
                <div class="sidebar-section">
                    <div class="sidebar-section-label" data-i18n="sidebar.labels.resources">Resources</div>
                    <nav class="sidebar-nav">
                        <a href="/projects/repository.html" class="sidebar-link">
                            <i class="link-icon" data-lucide="database"></i>
                            <span data-i18n="sidebar.links.knowledge_base">Knowledge Base</span>
                        </a>
                    </nav>
                </div>
            `;

            sectionsHtml = `
                <div class="sidebar-section">
                    <div class="sidebar-section-label" data-i18n="sidebar.labels.main">Main</div>
                    <nav class="sidebar-nav">
                        <a href="/dashboard/dashboard-reviewer.html" class="sidebar-link">
                            <i class="link-icon" data-lucide="layout-dashboard"></i>
                            <span data-i18n="sidebar.links.overview">Overview</span>
                        </a>
                        <a href="/analytics/analytics.html" class="sidebar-link">
                            <i class="link-icon" data-lucide="bar-chart-3"></i>
                            <span data-i18n="sidebar.links.analytics">Analytics</span>
                        </a>
                    </nav>
                </div>
                ${resourcesSection}
            `;
            footerHtml = `
                <div class="sidebar-footer">
                    <nav class="sidebar-nav">
                        <a href="/admin/settings.html" class="sidebar-link">
                            <i class="link-icon" data-lucide="settings"></i>
                            <span data-i18n="sidebar.links.settings">Settings</span>
                        </a>
                        <a href="#" class="sidebar-link text-danger" onclick="QCMS.logout()">
                            <i class="link-icon" data-lucide="log-out"></i>
                            <span data-i18n="sidebar.links.logout">Logout</span>
                        </a>
                    </nav>
                </div>
            `;
        
        // â”€â”€ CEO â€” Executive Strategic Oversight â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        } else if (roleName === 'CEO') {
            sectionsHtml = `
                <div class="sidebar-section">
                    <div class="sidebar-section-label" data-i18n="sidebar.labels.executive">Executive Oversight</div>
                    <nav class="sidebar-nav">
                        <a href="/dashboard/dashboard-ceo.html?view=strategic-overview" class="sidebar-link">
                            <i class="link-icon" data-lucide="line-chart"></i>
                            <span data-i18n="sidebar.links.overview">Overview</span>
                        </a>
                        <a href="/dashboard/dashboard-ceo.html?view=org-health" class="sidebar-link">
                            <i class="link-icon" data-lucide="activity"></i>
                            <span data-i18n="sidebar.links.org_health">Organization Health</span>
                        </a>
                        <a href="/dashboard/dashboard-ceo.html?view=roi-analytics" class="sidebar-link">
                            <i class="link-icon" data-lucide="trending-up"></i>
                            <span data-i18n="sidebar.links.roi_analytics">ROI Analytics</span>
                        </a>
                        <a href="/analytics/analytics.html" class="sidebar-link">
                            <i class="link-icon" data-lucide="bar-chart-2"></i>
                            <span data-i18n="sidebar.links.analytics">Analytics</span>
                        </a>
                    </nav>
                </div>
                <div class="sidebar-section">
                    <div class="sidebar-section-label" data-i18n="sidebar.labels.operations">Operational Intelligence</div>
                    <nav class="sidebar-nav">
                        <a href="/projects/projects-repository.html" class="sidebar-link">
                            <i class="link-icon" data-lucide="layers"></i>
                            <span data-i18n="sidebar.links.projects_repo">Project Repository</span>
                        </a>
                        <a href="/rewards/leaderboard.html" class="sidebar-link">
                            <i class="link-icon" data-lucide="award"></i>
                            <span>Leaderboard & Rewards</span>
                        </a>
                        <a href="/projects/repository.html" class="sidebar-link">
                            <i class="link-icon" data-lucide="database"></i>
                            <span data-i18n="sidebar.links.knowledge_base">Knowledge Base</span>
                        </a>
                    </nav>
                </div>
            `;
            footerHtml = `
                <div class="sidebar-footer">
                    <nav class="sidebar-nav">
                        <a href="/admin/settings.html" class="sidebar-link">
                            <i class="link-icon" data-lucide="settings"></i>
                            <span data-i18n="sidebar.links.settings">Settings</span>
                        </a>
                        <a href="#" class="sidebar-link text-danger" onclick="QCMS.logout()">
                            <i class="link-icon" data-lucide="log-out"></i>
                            <span data-i18n="sidebar.links.logout">Logout</span>
                        </a>
                    </nav>
                </div>
            `;

        // â”€â”€ TEAM MEMBER â€” Limited access â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        } else {
            sectionsHtml = `
                <div class="sidebar-section">
                    <div class="sidebar-section-label" data-i18n="sidebar.labels.main">Main</div>
                    <nav class="sidebar-nav">
                        <a href="/dashboard/dashboard-team-member.html" class="sidebar-link">
                            <i class="link-icon" data-lucide="layout-dashboard"></i>
                            <span data-i18n="sidebar.links.overview">Overview</span>
                        </a>
                        <a href="/projects/projects-repository.html" class="sidebar-link">
                            <i class="link-icon" data-lucide="layers"></i>
                            <span data-i18n="sidebar.links.projects_repo">Project Repository</span>
                        </a>
                    </nav>
                </div>
                <div class="sidebar-section">
                    <div class="sidebar-section-label" data-i18n="sidebar.labels.resources">Resources</div>
                    <nav class="sidebar-nav">
                        <a href="/projects/repository.html" class="sidebar-link">
                            <i class="link-icon" data-lucide="database"></i>
                            <span data-i18n="sidebar.links.knowledge_base">Knowledge Base</span>
                        </a>
                    </nav>
                </div>
            `;
            footerHtml = `
                <div class="sidebar-footer">
                    <nav class="sidebar-nav">
                        <a href="/admin/settings.html" class="sidebar-link">
                            <i class="link-icon" data-lucide="settings"></i>
                            <span data-i18n="sidebar.links.settings">Settings</span>
                        </a>
                        <a href="#" class="sidebar-link text-danger" onclick="QCMS.logout()">
                            <i class="link-icon" data-lucide="log-out"></i>
                            <span data-i18n="sidebar.links.logout">Logout</span>
                        </a>
                    </nav>
                </div>
            `;
        }

        sidebar.innerHTML = brandHtml + sectionsHtml + footerHtml;
        QCMS.refreshIcons();
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

    logout() {
        sessionStorage.removeItem('token');
        sessionStorage.removeItem('user');
        window.location.href = '/auth/login.html';
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
            <div class="glass-card fade-in h-100 ${link ? 'hover-shadow clickable' : ''}" style="${link ? 'transition: all 0.2s ease; cursor: pointer;' : ''}">
                <div class="ds-card-body p-4" style="position: relative; z-index: 1;">
                    <div class="kpi-icon-row mb-3" style="display:flex; align-items:center; justify-content:space-between;">
                        <div class="kpi-icon-box" style="width:42px; height:42px; border-radius:12px; display:flex; align-items:center; justify-content:center; background: rgba(${rgbVar}, 0.12); color: ${hexColor}; border: 1px solid rgba(${rgbVar}, 0.2)">
                            <i data-lucide="${icon || 'hash'}" style="width:20px; height:20px;"></i>
                        </div>
                        ${trend !== null ? `
                            <div class="${trendClass}">
                                <i data-lucide="${trendIcon}" style="width:12px;height:12px;"></i>
                                ${trend}%
                            </div>
                        ` : ''}
                    </div>
                    <div class="kpi-label mb-1" style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--ds-text-secondary);"
                         ${labelKey ? `data-i18n="${labelKey}"` : ''}>
                        ${label}
                    </div>
                    <div class="kpi-value fw-bold" style="font-size: 1.75rem; letter-spacing: -0.025em; color: var(--ds-text-main);"
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

    projectProgress(currentStage, totalStages = 8) {
        let pct = (currentStage / totalStages) * 100;
        if (pct > 100) pct = 100;
        if (pct < 0) pct = 0;
        const pctStr = pct.toFixed(2);
        return `
            <div class="ds-progress-container mt-3">
                <div class="ds-progress-label"><span>Stage ${currentStage} of ${totalStages} = ${pctStr}%</span></div>
                <div class="ds-progress-bar"><div class="ds-progress-fill" style="width: ${pct}%"></div></div>
            </div>
        `;
    },

    emptyState(title = 'No Data Found', message = 'Try refining your search or adding new items.', icon = 'search') {
        return `
            <div class="empty-state-container py-5 px-4 text-center fade-in bg-white/50 rounded-xl border border-dashed border-slate-200">
                <div class="empty-state-icon-box mb-4 mx-auto glass-panel" style="width: 80px; height: 80px; display: flex; align-items: center; justify-content: center; border-radius: 20px;">
                    <i data-lucide="${icon}" style="width: 32px; height: 32px; color: var(--ds-accent);"></i>
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


    toast(message, type = 'info') {
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
            <span>${message}</span>
        `;
        container.appendChild(toast);
        if (window.lucide) lucide.createIcons();
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateX(100%)';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
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
                            <div class="text-xs text-blue-200">Retrieval Augmented Generation</div>
                        </div>
                    </div>
                    <button id="close-chat" class="btn-close-chat"><i data-lucide="x"></i></button>
                </div>
                <div id="chat-messages" class="chat-messages p-4">
                    <div class="message system">Hello! I'm your Quality Assistant. Ask me anything about archived projects.</div>
                </div>
                <form id="chat-form" class="chat-input-area p-3 border-top">
                    <div class="input-group">
                        <input type="text" id="chat-input" class="form-control" placeholder="Ask about past root causes..." autocomplete="off">
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

        toggle.onclick = () => chatWindow.classList.toggle('hidden');
        close.onclick = () => chatWindow.classList.add('hidden');

        form.onsubmit = async (e) => {
            e.preventDefault();
            const query = input.value.trim();
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
                const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token') || localStorage.getItem('token') || sessionStorage.getItem('token');
                const response = await fetch('/api/rag/chat', {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${token}`
                    },
                    body: JSON.stringify({ query })
                });

                const data = await response.json();
                typing.remove();

                const aiMsg = document.createElement('div');
                aiMsg.className = 'message system';
                
                if (data.answer) {
                    let formatted = data.answer
                        .replace(/### (.*?)\n/g, '<h6 class="fw-bold text-primary mt-2 mb-1">$1</h6>')
                        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                        .replace(/`([^`]+)`/g, '<code class="px-1 py-0.5 rounded bg-light">$1</code>')
                        .replace(/\n/g, '<br>');
                    aiMsg.innerHTML = `<div class="answer text-sm">${formatted}</div>`;
                    if (data.sources && data.sources.length > 0) {
                        const sourcesHtml = data.sources.map(s => `<li class="mt-1"><a href="project-details.html?id=${s.project_id}" target="_blank" class="source-link fw-semibold">${s.title}</a> <span class="text-xs text-muted">(${s.category || 'Quality'})</span></li>`).join('');
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
            helpdeskWindow.classList.toggle('hidden');
            if (!helpdeskWindow.classList.contains('hidden')) {
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
                        <label class="ds-label text-white">Subject</label>
                        <input type="text" id="helpdesk-subject" class="ds-input form-control" placeholder="Brief summary of the issue..." required>
                    </div>
                    <div class="row g-2">
                        <div class="col-6">
                            <div class="ds-field">
                                <label class="ds-label text-white">Category</label>
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
                                <label class="ds-label text-white">Priority</label>
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
                        <label class="ds-label text-white">Description / Message</label>
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
                    const token = sessionStorage.getItem('token');
                    const response = await fetch('/api/auth/support/tickets', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${token}`
                        },
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

        // Render ticket history
        const renderHistory = async () => {
            contentArea.innerHTML = `<div class="text-center text-secondary py-4"><span class="spinner-border spinner-border-sm me-2"></span>Loading history...</div>`;

            try {
                const token = sessionStorage.getItem('token');
                const response = await fetch('/api/auth/support/tickets', {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                const data = await response.json();

                if (response.ok && data.status === 'success') {
                    const tickets = data.data;
                    if (!tickets || tickets.length === 0) {
                        contentArea.innerHTML = `<div class="text-center text-secondary py-5">No support tickets submitted yet.</div>`;
                        return;
                    }

                    contentArea.innerHTML = `
                        <div class="helpdesk-history-list">
                            ${tickets.map(t => {
                                const createdDate = new Date(t.created_at).toLocaleDateString();
                                const badgeHtml = this.statusBadge(t.status);
                                return `
                                    <div class="helpdesk-history-item">
                                        <div class="d-flex justify-content-between align-items-start mb-2">
                                            <span class="text-xs font-monospace text-secondary">#TKT-${t.id}</span>
                                            ${badgeHtml}
                                        </div>
                                        <div class="fw-bold text-white text-sm mb-1">${t.subject}</div>
                                        <div class="text-xs text-secondary mb-2">${createdDate} &bull; ${t.category} &bull; ${t.priority} Priority</div>
                                        <div class="text-xs text-muted" style="white-space: pre-wrap; word-break: break-word;">${t.message}</div>
                                        ${t.resolution ? `
                                            <div class="helpdesk-resolution-box ${t.status.toLowerCase() === 'rejected' ? 'rejected' : ''}">
                                                <strong>Resolution Summary:</strong>
                                                <div class="mt-1">${t.resolution}</div>
                                            </div>
                                        ` : ''}
                                    </div>
                                `;
                            }).join('')}
                        </div>
                    `;
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
            const notifs = await api.get('/notifications');
            this.notifications = notifs || [];
            const badge = document.getElementById('notif-badge');
            if (badge) {
                const unread = this.notifications.some(n => !n.is_read);
                badge.style.display = unread ? 'block' : 'none';
            }
        } catch (e) {
            console.error('Failed to load notifications', e);
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
        const badge = document.getElementById('notif-badge');
        if (badge) {
            const hasUnread = (this.notifications || []).some(n => !n.is_read);
            badge.style.display = hasUnread ? 'block' : 'none';
        }
        api.post('/notifications/read').catch(() => {});

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

        const createdDateStr = notif.created_at ? `${new Date(notif.created_at).toLocaleString()} (${QCMS.formatRelative(notif.created_at)})` : 'Just now';

        const titleLower = (notif.title || '').toLowerCase();
        const msgLower = (notif.message || '').toLowerCase();
        const isOfflinePaymentNotif = titleLower.includes('offline payment') || msgLower.includes('payment proof') || titleLower.includes('payment verification') || titleLower.includes('payment approved') || msgLower.includes('utr:');

        let utrMatch = null;
        if (notif.message) {
            const m = notif.message.match(/UTR[:\s]+([A-Za-z0-9_\-]+)/i);
            if (m) utrMatch = m[1];
        }

        let actionButtonHtml = '';
        if (isOfflinePaymentNotif) {
            if (window.location.pathname.includes('super-admin.html')) {
                actionButtonHtml = `
                    <div class="p-3 bg-primary bg-opacity-10 border border-primary border-opacity-25 rounded-3 mb-3">
                        <div class="text-xs text-secondary mb-2 fw-bold">Offline Payment Review Action</div>
                        <button type="button" class="ds-btn ds-btn-primary ds-btn-sm w-100 py-2" onclick="QCMS.handleOfflinePaymentNotifClick('${utrMatch || ''}')">
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
                            <div class="p-2 rounded-circle" style="background:rgba(var(--ds-primary-rgb), 0.1); color:var(--ds-primary);">
                                <i data-lucide="bell" style="width:20px;height:20px;"></i>
                            </div>
                            <div>
                                <h6 class="modal-title fw-bold mb-0" style="color:var(--ds-text-main); font-size:16px;">${QCMS.escapeHtml(notif.title || 'Notification Details')}</h6>
                                <span class="text-xxs text-secondary">${createdDateStr}</span>
                            </div>
                        </div>
                        <button type="button" class="btn-close" style="filter:var(--ds-icon-filter, none);" onclick="document.getElementById('notif-detail-modal-container').remove()"></button>
                    </div>
                    <div class="modal-body p-4" style="max-height:60vh; overflow-y:auto;">
                        <div class="mb-3 d-flex align-items-center gap-2">
                            <span class="badge bg-primary bg-opacity-10 text-primary border border-primary border-opacity-25" style="font-size:11px;">
                                System Notification
                            </span>
                            <span class="badge bg-success bg-opacity-10 text-success border border-success border-opacity-25" style="font-size:11px;">
                                Verified Alert
                            </span>
                        </div>
                        <div class="p-3 rounded-3 mb-3" style="background:rgba(255,255,255,0.03); border:1px solid var(--ds-border-color); font-size:14px; line-height:1.6; color:var(--ds-text-main); white-space:pre-wrap; word-break:break-word;">
${QCMS.escapeHtml(notif.message || 'No detailed description available.')}
                        </div>
                        ${actionButtonHtml}
                    </div>
                    <div class="modal-footer border-top p-3 d-flex justify-content-end" style="border-color:var(--ds-border-color)!important;">
                        <button type="button" class="ds-btn ds-btn-secondary ds-btn-sm" onclick="document.getElementById('notif-detail-modal-container').remove()">Close</button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(modalEl);
        if (QCMS.refreshIcons) QCMS.refreshIcons();
    },

    handleNotifClick(index) {
        const notifs = window.QCMS.notifications || this.notifications || [];
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
    }
};

// Global helper for notifications
function showNotificationsPanel() {
    const existing = document.getElementById('notif-panel-overlay');
    if (existing) { existing.remove(); return; }

    const notifs = window.QCMS.notifications || [];
    const hasNotifs = notifs.length > 0;

    const notifItems = hasNotifs ? notifs.map((n, idx) => `
        <div class="notif-item p-3 mb-2 rounded-2 clickable hover-bg" 
             style="background:rgba(255,255,255,0.03); border:1px solid var(--ds-border-color); cursor:pointer;"
             onclick="QCMS.handleNotifClick(${idx})">
            <div class="d-flex align-items-center justify-content-between mb-1">
                <div class="fw-bold text-sm" style="color: var(--ds-text-main);">${n.title || 'Notification'}</div>
                ${!n.is_read ? '<span class="badge bg-primary" style="font-size:9px; padding:2px 5px;">New</span>' : ''}
            </div>
            <div class="text-xs text-secondary text-truncate">${n.message || ''}</div>
            <div class="text-xxs text-muted mt-1">${QCMS.formatRelative(n.created_at)}</div>
        </div>
    `).join('') : '<div class="p-5 text-center opacity-50">No new alerts</div>';

    const overlay = document.createElement('div');
    overlay.id = 'notif-panel-overlay';
    overlay.style.cssText = 'position:fixed; inset:0; z-index:19999;';
    overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };
    overlay.innerHTML = `
        <div id="notif-panel" style="position:fixed; top:64px; right:16px; width:360px; background:var(--ds-bg-surface); border-radius:18px; box-shadow:0 20px 60px rgba(0,0,0,0.1); border: 1px solid var(--ds-glass-border); z-index:20000; overflow:hidden;">
            <div class="p-3 border-bottom d-flex justify-content-between align-items-center" style="border-color: var(--ds-border-color) !important;">
                <span class="fw-bold" style="color: var(--ds-text-main);">Notifications</span>
                <button class="btn btn-sm btn-link text-decoration-none" onclick="QCMS.clearNotifications(); document.getElementById('notif-panel-overlay').remove()">Clear All</button>
            </div>
            <div class="p-2" style="max-height:360px; overflow-y:auto; background: var(--ds-bg-surface);">${notifItems}</div>
            <div class="p-2 border-top text-center" style="border-color: var(--ds-border-color) !important; background:rgba(0,0,0,0.05);">
                <button class="btn btn-sm btn-link text-primary text-decoration-none fw-bold text-xs" onclick="document.getElementById('notif-panel-overlay').remove(); UserAnnouncementsModal.open();">
                    📢 View All Announcements
                </button>
            </div>
        </div>
    `;
    document.body.appendChild(overlay);
}

// Expose QCMS globally
window.QCMS = QCMS;

QCMS.escapeHtml = function(str) {
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
};

// Standardized Icon Refresh
QCMS.refreshIcons = function() {
    if (window.lucide) {
        window.lucide.createIcons({
            attrs: {
                'stroke-width': 2.2,
                'class': 'ds-icon'
            }
        });
    }
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

QCMS.init();

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

window.addEventListener('qcms-theme-change', e => {
    updateChartTheme(e.detail.theme);
});

window.addEventListener('load', () => {
    const theme = localStorage.getItem('qcms-theme') || 'light';
    updateChartTheme(theme);
});

// Global JS Error Boundary for Production Hardening
window.addEventListener('error', function(event) {
    console.error('[QCMS Error Boundary]', event.error || event.message);
    // Only log — individual components handle their own errors via try/catch
});

window.addEventListener('unhandledrejection', function(event) {
    const reason = event.reason;
    console.error('[QCMS Unhandled Rejection]', reason);
    
    // Only show toast for actual network/fetch failures, not JS TypeErrors
    const isNetworkError = reason instanceof TypeError && 
        (String(reason.message).includes('fetch') || String(reason.message).includes('network') || String(reason.message).includes('Failed to fetch'));
    
    if (isNetworkError && typeof QCMS !== 'undefined' && typeof QCMS.toast === 'function') {
        QCMS.toast('Network connection error. Please check your connection.', 'error');
    }
    
    // Prevent browser from logging the unhandled rejection in console (we already logged it)
    event.preventDefault();
});


// ─── Global Announcement Banner & User Modal Components ────────────────────────

const GlobalAnnouncementBanner = {
    activeAnnouncements: [],
    currentIndex: 0,

    async init() {
        if (!document.getElementById('global-announcement-banner-container')) {
            const container = document.createElement('div');
            container.id = 'global-announcement-banner-container';
            container.style.cssText = 'position: relative; z-index: 1040; width: 100%;';
            document.body.prepend(container);
        }
        await this.fetchActiveAnnouncements();

        window.addEventListener('qcms:announcement-published', () => {
            this.fetchActiveAnnouncements();
        });
    },

    async fetchActiveAnnouncements() {
        try {
            const res = await api.get('/announcements/user-active');
            if (res && res.status === 'success' && Array.isArray(res.data)) {
                this.activeAnnouncements = res.data.filter(a => !a.is_dismissed);
                this.render();
            }
        } catch (e) {
            console.error('Error loading active announcements', e);
        }
    },

    render() {
        const container = document.getElementById('global-announcement-banner-container');
        if (!container) return;

        if (!this.activeAnnouncements || this.activeAnnouncements.length === 0) {
            container.innerHTML = '';
            return;
        }

        if (this.currentIndex >= this.activeAnnouncements.length) {
            this.currentIndex = 0;
        }

        const ann = this.activeAnnouncements[this.currentIndex];

        const priorityStyles = {
            'Critical': 'background: linear-gradient(90deg, #450a0a, #7f1d1d); border-bottom: 2px solid #ef4444; color: #fecdd3;',
            'High': 'background: linear-gradient(90deg, #451a03, #78350f); border-bottom: 2px solid #f97316; color: #ffedd5;',
            'Medium': 'background: linear-gradient(90deg, #0c4a6e, #0369a1); border-bottom: 2px solid #38bdf8; color: #e0f2fe;',
            'Low': 'background: linear-gradient(90deg, #064e3b, #047857); border-bottom: 2px solid #34d399; color: #d1fae5;'
        };
        const priorityIcons = {
            'Critical': 'alert-octagon',
            'High': 'alert-triangle',
            'Medium': 'info',
            'Low': 'megaphone'
        };

        const style = priorityStyles[ann.priority] || priorityStyles['Medium'];
        const icon = priorityIcons[ann.priority] || 'megaphone';

        const cleanSummary = ann.summary || (ann.body ? ann.body.replace(/<[^>]*>?/gm, '').substring(0, 100) : '');

        container.innerHTML = `
            <div class="global-ann-banner p-2.5 px-4 d-flex align-items-center justify-content-between gap-3 shadow-sm fade-in" style="${style}">
                <div class="d-flex align-items-center gap-2.5 flex-grow-1 overflow-hidden">
                    <span class="badge rounded-pill bg-black bg-opacity-25 px-2.5 py-1 text-uppercase font-monospace text-xxs fw-bold d-inline-flex align-items-center gap-1" style="border: 1px solid rgba(255,255,255,0.2);">
                        <i data-lucide="${icon}" style="width:13px;height:13px;"></i> ${ann.priority} Notice
                    </span>
                    <strong class="text-xs text-truncate font-semibold">${QCMS.escapeHtml(ann.title)}:</strong>
                    <span class="text-xs opacity-90 text-truncate d-none d-md-inline">${QCMS.escapeHtml(cleanSummary)}</span>
                </div>
                <div class="d-flex align-items-center gap-2 flex-shrink-0">
                    <button class="btn btn-sm btn-light py-0.5 px-2.5 text-xxs fw-bold rounded-pill text-dark shadow-sm" onclick="GlobalAnnouncementBanner.openDetailModal(${ann.id})">
                        View Notice
                    </button>
                    ${this.activeAnnouncements.length > 1 ? `
                        <span class="text-xxs opacity-75 font-monospace">${this.currentIndex + 1}/${this.activeAnnouncements.length}</span>
                        <button class="btn btn-sm btn-link text-white p-0 m-0" onclick="GlobalAnnouncementBanner.nextAnn()" title="Next Announcement">
                            <i data-lucide="chevron-right" style="width:14px;height:14px;"></i>
                        </button>
                    ` : ''}
                    <button class="btn btn-sm btn-link text-white p-0 m-0 opacity-75 hover-opacity-100" onclick="GlobalAnnouncementBanner.dismiss(${ann.id})" title="Dismiss Banner">
                        <i data-lucide="x" style="width:16px;height:16px;"></i>
                    </button>
                </div>
            </div>
        `;

        if (window.lucide) lucide.createIcons();
    },

    nextAnn() {
        this.currentIndex = (this.currentIndex + 1) % this.activeAnnouncements.length;
        this.render();
    },

    async dismiss(annId) {
        try {
            await api.post(`/announcements/${annId}/dismiss`);
        } catch (e) {}
        this.activeAnnouncements = this.activeAnnouncements.filter(a => a.id !== annId);
        this.render();
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
                            <h6 class="modal-title fw-bold mb-0 text-main ms-2">${QCMS.escapeHtml(ann.title)}</h6>
                        </div>
                        <button type="button" class="btn-close" style="filter:var(--ds-icon-filter, none);" onclick="document.getElementById('user-ann-reader-modal').remove()"></button>
                    </div>
                    <div class="modal-body p-4" style="max-height:65vh; overflow-y:auto;">
                        <div class="text-xxs text-secondary mb-3">
                            Published by <strong>${QCMS.escapeHtml(ann.created_by)}</strong> on ${ann.published_at ? new Date(ann.published_at).toLocaleString() : 'Recently'}
                        </div>
                        ${ann.summary ? `<div class="p-3 bg-body-tertiary rounded-3 mb-3 text-xs text-secondary border" style="border-color:var(--ds-border-color)!important;"><strong>Summary:</strong> ${QCMS.escapeHtml(ann.summary)}</div>` : ''}
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
                <div class="d-flex flex-column gap-3">
                    ${list.map(a => `
                        <div class="p-3.5 rounded-3 border transition hover-card" style="background:rgba(255,255,255,0.02); border-color:var(--ds-border-color)!important;">
                            <div class="d-flex align-items-center justify-content-between mb-2">
                                <div class="d-flex align-items-center gap-2">
                                    <span class="badge ${a.priority === 'Critical' ? 'bg-danger' : a.priority === 'High' ? 'bg-warning text-dark' : 'bg-primary bg-opacity-15 text-primary'} text-xxs px-2 py-0.5">
                                        ${a.priority}
                                    </span>
                                    <span class="badge bg-secondary-subtle text-secondary text-xxs px-2 py-0.5">${a.category}</span>
                                    ${!a.is_read ? '<span class="badge bg-success text-xxs px-2 py-0.5">UNREAD</span>' : ''}
                                </div>
                                <span class="text-xxs text-secondary">${a.published_at ? new Date(a.published_at).toLocaleDateString() : 'Recently'}</span>
                            </div>
                            <h6 class="fw-bold text-main mb-1.5">${QCMS.escapeHtml(a.title)}</h6>
                            <p class="text-xs text-secondary mb-3">${QCMS.escapeHtml(a.summary || a.body || '')}</p>
                            <div class="d-flex align-items-center justify-content-between text-xxs border-top pt-2" style="border-color:var(--ds-border-color)!important;">
                                <span class="text-muted">By: ${QCMS.escapeHtml(a.created_by)}</span>
                                ${!a.is_read ? `
                                    <button class="btn btn-sm btn-link text-primary p-0 text-xxs fw-bold text-decoration-none" onclick="UserAnnouncementsModal.markRead(${a.id})">
                                        Mark as Read
                                    </button>
                                ` : '<span class="text-success"><i data-lucide="check-check" style="width:12px;height:12px;"></i> Read</span>'}
                            </div>
                        </div>
                    `).join('')}
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



