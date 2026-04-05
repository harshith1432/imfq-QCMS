/**
 * QCMS Enterprise - Shared UI Components
 * v1.0 - Handle sidebars, navbars, and role-based UI logic.
 */

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
        'Admin': { canCreate: true, canValidate: true, canApprove: true, isAdmin: true },
        'Team Leader': { canCreate: true, canValidate: false, canApprove: false, isAdmin: false },
        'Facilitator': { canCreate: false, canValidate: true, canApprove: false, isAdmin: false },
        'Reviewer': { canCreate: false, canValidate: false, canApprove: true, isAdmin: false },
        'Team Member': { canCreate: false, canValidate: false, canApprove: false, isAdmin: false }
    },

    init() {
        const userStr = localStorage.getItem('user');
        if (userStr) {
            try {
                this.user = JSON.parse(userStr);
            } catch (e) {
                console.error("Failed to parse user session:", e);
                this.logout();
                return;
            }
        }

        // Centralized Lucide config for premium look
        if (window.lucide) {
            window.lucide.createIcons({
                attrs: {
                    'stroke-width': 2.2,
                    'class': 'ds-icon'
                }
            });
        }

        // Initialize UI components
        if (this.user) {
            this.renderSidebar();
            this.renderNavbar();
            this.setActiveLink();
        }

        // Listen for theme changes to re-render
        window.addEventListener('qcms-theme-change', () => {
            if (this.user) this.renderNavbar();
        });
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
        if (!dateStr || dateStr === '—') return '—';
        let normalized = dateStr;
        if (typeof dateStr === 'string' && !dateStr.endsWith('Z') && !dateStr.includes('+')) normalized += 'Z';
        const date = new Date(normalized);
        if (isNaN(date.getTime())) return '—';
        return date.toLocaleDateString('en-US', { 
            month: 'short', 
            day: 'numeric', 
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
        if (!dateStr || dateStr === '—') return '—';
        let normalized = dateStr;
        if (typeof dateStr === 'string' && !dateStr.endsWith('Z') && !dateStr.includes('+')) normalized += 'Z';
        const date = new Date(normalized);
        if (isNaN(date.getTime())) return '—';
        const diff = (new Date() - date) / 1000;
        if (diff < 60) return 'Just now';
        if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
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
        const roles = ['Team Member', 'Team Leader', 'Facilitator', 'Reviewer', 'Admin'];
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
            <div class="container-fluid d-flex align-items-center h-100 px-4">
                <!-- Breadcrumb Placeholder -->
                <div id="nav-breadcrumb-container" class="d-none d-lg-flex align-items-center px-3" style="min-width: 200px;"></div>

                <div class="h-stack gap-3 ms-auto align-items-center pe-3">
                    <!-- Global Search -->
                    <div class="nav-search-wrapper d-none d-md-flex align-items-center">
                        <div class="ds-search-inline glass-panel" style="width: 320px; background: rgba(var(--ds-primary-rgb), 0.03); border-radius: 12px; height: 40px; border: 1px solid var(--ds-border-color); display: flex; align-items: center; padding: 0 12px;">
                            <i data-lucide="search" style="width:18px; height:18px; opacity: 0.5; margin-right: 10px;"></i>
                            <input type="text" class="ds-input border-0 bg-transparent p-0" placeholder="Search projects or users..." id="globalSearchInput" 
                                   style="height: 100%; font-size: 14px; font-weight: 500; flex: 1; outline: none; color: var(--ds-text-main);">
                            <kbd class="ds-kbd d-none d-lg-inline-block" style="background: var(--ds-bg-card); border: 1px solid var(--ds-border-color); color: var(--ds-text-secondary); padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 700;">/</kbd>
                        </div>
                    </div>

                    <!-- Theme Toggle -->
                    <div class="theme-switcher-wrapper glass-panel p-1 d-flex gap-1" style="border-radius: 12px; background: rgba(var(--ds-primary-rgb), 0.03); border: 1px solid var(--ds-border-color);">
                        <button class="ds-btn ds-btn-icon ${!isDark ? 'ds-btn-primary' : 'ds-btn-ghost text-muted'}" 
                                style="width:32px; height:32px; border-radius: 8px; padding:0;" title="Light Mode"
                                onclick="window.themeManager.applyTheme('light'); localStorage.setItem('qcms-theme', 'light');">
                            <i data-lucide="sun" style="width:15px; height:15px;"></i>
                        </button>
                        <button class="ds-btn ds-btn-icon ${isDark ? 'ds-btn-primary' : 'ds-btn-ghost text-muted'}" 
                                style="width:32px; height:32px; border-radius: 8px; padding:0;" title="Dark Mode"
                                onclick="window.themeManager.applyTheme('dark'); localStorage.setItem('qcms-theme', 'dark');">
                            <i data-lucide="moon" style="width:15px; height:15px;"></i>
                        </button>
                    </div>

                    <!-- Notification Bell -->
                    <button id="notif-bell-btn" class="ds-btn ds-btn-ghost position-relative"
                            style="width:42px; height:42px; border-radius:12px; padding:0; display:flex; align-items:center; justify-content:center; color:var(--ds-text-main); border: 1px solid transparent;"
                            title="Notifications" onclick="showNotificationsPanel()">
                        <i data-lucide="bell" style="width:22px; height:22px;"></i>
                        <span id="notif-badge" style="position:absolute; top:8px; right:8px; width:11px; height:11px; background:#ef4444; border-radius:50%; border:2px solid var(--ds-bg-surface); display:block;"></span>
                    </button>

                    <div class="v-divider" style="height: 24px; width: 1px; background: var(--ds-border-color); opacity: 0.5;"></div>

                    <!-- User Badge -->
                    <div class="user-pill d-flex align-items-center gap-2 ps-1 pe-3 py-1 clickable glass-panel hover-shadow" 
                         style="border-radius: 14px; background: rgba(var(--ds-primary-rgb), 0.04); border: 1px solid var(--ds-border-color); transition: all 0.2s;" 
                         onclick="window.location.href='profile.html'">
                        <div class="user-avatar-sm d-flex align-items-center justify-content-center text-white" 
                             style="width:38px; height:38px; border-radius:12px; font-weight:700; font-size:15px; background: var(--ds-accent); overflow: hidden; border: 1px solid rgba(255,255,255,0.1);"
                             id="nav-user-avatar">
                            ${this.renderAvatar(user, 38)}
                        </div>
                        <div class="user-meta d-none d-sm-block text-start" style="line-height: 1.2;">
                            <div class="fw-bold" style="font-size: 14px; color: var(--ds-text-main);">${user.full_name || user.username || 'User'}</div>
                            <div class="text-secondary" style="font-size: 10px; font-weight: 700; text-transform: uppercase; opacity: 0.6; letter-spacing: 0.05em;">${user.role || 'Member'}</div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Initialize global search listener
        setTimeout(() => {
            const searchInput = document.getElementById('globalSearchInput');
            if (searchInput) {
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

        if (window.lucide) lucide.createIcons();
        if (window.Breadcrumbs) window.Breadcrumbs.init('nav-breadcrumb-container');
    },

    /**
     * Standardized Sidebar Rendering
     */
    renderSidebar() {
        const user = this.user;
        if (!user) return;

        const sidebar = document.getElementById('app-sidebar');
        if (!sidebar) return;

        sidebar.className = 'glass-sidebar';
        const roleName = user.role || 'Team Member';
        const roleSlug = this.roleToSlug(roleName);

        let content = `
            <div class="sidebar-brand">
                <div class="brand-icon" style="background: var(--ds-accent);">
                    <i data-lucide="shield-check" style="color:white;"></i>
                </div>
                <div class="brand-text">
                    QCMS <small style="color:var(--ds-accent); opacity:1;">Enterprise OS</small>
                </div>
            </div>

            <div class="sidebar-section">
                <div class="sidebar-section-label">Main</div>
                <nav class="sidebar-nav">
                    <a href="dashboard-${roleSlug}.html" class="sidebar-link">
                        <i class="link-icon" data-lucide="layout-dashboard"></i>
                        <span>Overview</span>
                    </a>
                    <a href="projects-repository.html" class="sidebar-link">
                        <i class="link-icon" data-lucide="layers"></i>
                        <span>Project Repo</span>
                    </a>
                    <a href="analytics.html" class="sidebar-link">
                        <i class="link-icon" data-lucide="bar-chart-3"></i>
                        <span>Analytics</span>
                    </a>
                </nav>
            </div>
        `;

        if (roleName === 'Admin') {
            content += `
                <div class="sidebar-section">
                    <div class="sidebar-section-label">Administration</div>
                    <nav class="sidebar-nav">
                        <a href="users.html" class="sidebar-link">
                            <i class="link-icon" data-lucide="users"></i>
                            <span>User Management</span>
                        </a>
                        <a href="departments.html" class="sidebar-link">
                            <i class="link-icon" data-lucide="building-2"></i>
                            <span>Departments</span>
                        </a>
                        <a href="audit-logs.html" class="sidebar-link">
                            <i class="link-icon" data-lucide="scroll-text"></i>
                            <span>Audit logs</span>
                        </a>
                    </nav>
                </div>
            `;
        }

        content += `
            <div class="sidebar-section">
                <div class="sidebar-section-label">Resources</div>
                <nav class="sidebar-nav">
                    <a href="repository.html" class="sidebar-link">
                        <i class="link-icon" data-lucide="database"></i>
                        <span>Knowledge Base</span>
                    </a>
                    <a href="standards.html" class="sidebar-link">
                        <i class="link-icon" data-lucide="file-check-2"></i>
                        <span>Standards & SOPs</span>
                    </a>
                </nav>
            </div>

            <div class="sidebar-footer">
                <nav class="sidebar-nav">
                    ${roleName === 'Admin' ? `
                    <a href="settings.html" class="sidebar-link">
                        <i class="link-icon" data-lucide="settings"></i>
                        <span>Settings</span>
                    </a>
                    ` : ''}
                    <a href="#" class="sidebar-link text-danger" onclick="QCMS.logout()">
                        <i class="link-icon" data-lucide="log-out"></i>
                        <span>Logout</span>
                    </a>
                </nav>
            </div>
        `;

        sidebar.innerHTML = content;
        if (window.lucide) lucide.createIcons();
    },

    roleToSlug(role) {
        return role.toLowerCase().replace(/ /g, '-');
    },

    setActiveLink() {
        const path = window.location.pathname;
        const page = path.split("/").pop() || 'index.html';
        const cleanPage = page.split('?')[0].split('#')[0];

        document.querySelectorAll('.sidebar-link').forEach(link => {
            const href = link.getAttribute('href');
            if (!href || href === '#') return;
            const cleanHref = href.split('?')[0].split('#')[0];
            link.classList.toggle('active', cleanHref === cleanPage);
            
            // Default to dashboard match if on root
            if (cleanPage === 'index.html' && cleanHref.includes('dashboard')) {
                link.classList.add('active');
            }
        });
    },

    logout() {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = '/login.html';
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

    kpiCard(label, value, icon, color = 'blue', trend = null, link = null) {
        const trendIcon = trend > 0 ? 'trending-up' : 'trending-down';
        const trendClass = trend > 0 ? 'ds-badge green' : 'ds-badge red';
        const colorVar = `var(--ds-${color})`;
        const rgbVar = `var(--ds-${color}-rgb)`;

        const cardContent = `
            <div class="glass-card fade-in h-100 ${link ? 'hover-shadow clickable' : ''}" style="${link ? 'transition: all 0.2s ease;' : ''}">
                <div class="ds-card-body p-4" style="position: relative; z-index: 1;">
                    <div class="kpi-icon-row mb-3">
                        <div class="kpi-icon-box" style="background: rgba(${rgbVar}, 0.15); color: ${colorVar}; border-color: rgba(${rgbVar}, 0.2)">
                            <i data-lucide="${icon}"></i>
                        </div>
                        ${trend !== null ? `
                            <div class="${trendClass}">
                                <i data-lucide="${trendIcon}" style="width:12px;height:12px;"></i>
                                ${trend}%
                            </div>
                        ` : ''}
                    </div>
                    <div class="kpi-label mb-1" style="font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--ds-text-tertiary); opacity: 0.8;">
                        ${label}
                    </div>
                    <div class="kpi-value fw-bold" style="font-size: 1.875rem; letter-spacing: -0.025em; color: var(--ds-text-main);">
                        ${value}
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
        if (!status) return `<span class="ds-badge gray">N/A</span>`;
        const s = String(status).toLowerCase();
        let color = 'gray';
        if (s.includes('active') || s.includes('in_progress') || s.includes('approved') || s.includes('open')) color = 'blue';
        if (s.includes('completed') || s.includes('closed') || s.includes('success') || s.includes('done')) color = 'green';
        if (s.includes('pending') || s.includes('review') || s.includes('warning') || s.includes('stalled')) color = 'orange';
        if (s.includes('rejected') || s.includes('failed') || s.includes('danger') || s.includes('inactive')) color = 'red';
        return `<span class="ds-badge ${color}">${status}</span>`;
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
        if (!dateStr) return '—';
        let normalized = dateStr;
        if (typeof dateStr === 'string' && !dateStr.endsWith('Z') && !dateStr.includes('+')) normalized += 'Z';
        const date = new Date(normalized);
        const diff = (new Date() - date) / 1000;
        if (diff < 60) return 'Just now';
        if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    },

    formatDate(dateStr) {
        if (!dateStr) return '—';
        let normalized = dateStr;
        if (typeof dateStr === 'string' && !dateStr.endsWith('Z') && !dateStr.includes('+')) normalized += 'Z';
        const date = new Date(normalized);
        return date.toLocaleDateString('en-US', { 
            month: 'short', 
            day: 'numeric', 
            year: 'numeric' 
        });
    },

    formatTime(dateStr) {
        if (!dateStr) return '—';
        const date = new Date(dateStr);
        return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    },

    stageStepper(currentStage) {
        const stages = ['ID', 'SEL', 'ANA', 'CAU', 'RCA', 'DATA', 'DEV', 'IMP'];
        return `
            <div class="ds-stepper">
                ${stages.map((s, i) => {
            const status = i + 1 < currentStage ? 'completed' : (i + 1 === currentStage ? 'active' : 'pending');
            return `<div class="step ${status}"><div class="step-circle">${i + 1}</div><div class="step-label">${s}</div></div>`;
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
        const pct = Math.round((currentStage / totalStages) * 100);
        return `
            <div class="ds-progress-container mt-3">
                <div class="ds-progress-label"><span>Stage ${currentStage}/${totalStages}</span><span>${pct}%</span></div>
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
    }
};

// Global helper for notifications
function showNotificationsPanel() {
    const existing = document.getElementById('notif-panel-overlay');
    if (existing) { existing.remove(); return; }

    const notifs = window.QCMS.notifications || [];
    const hasNotifs = notifs.length > 0;

    const notifItems = hasNotifs ? notifs.map(n => `
        <div class="notif-item p-3 mb-2 rounded-2" style="background:rgba(255,255,255,0.5); border:1px solid rgba(0,0,0,0.05);">
            <div class="fw-bold text-sm">${n.title || 'Notification'}</div>
            <div class="text-xs text-secondary">${n.message || ''}</div>
        </div>
    `).join('') : '<div class="p-5 text-center opacity-50">No new alerts</div>';

    const overlay = document.createElement('div');
    overlay.id = 'notif-panel-overlay';
    overlay.style.cssText = 'position:fixed; inset:0; z-index:19999;';
    overlay.onclick = (e) => { if (e.target === overlay) overlay.remove(); };
    overlay.innerHTML = `
        <div id="notif-panel" style="position:fixed; top:64px; right:16px; width:360px; background:white; border-radius:18px; box-shadow:0 20px 60px rgba(0,0,0,0.1); z-index:20000; overflow:hidden;">
            <div class="p-3 border-bottom d-flex justify-content-between align-items-center">
                <span class="fw-bold">Notifications</span>
                <button class="btn btn-sm btn-link" onclick="QCMS.notifications=[]; document.getElementById('notif-badge').style.display='none'; document.getElementById('notif-panel-overlay').remove()">Clear All</button>
            </div>
            <div class="p-2" style="max-height:400px; overflow-y:auto;">${notifItems}</div>
        </div>
    `;
    document.body.appendChild(overlay);
}

// Expose QCMS globally
window.QCMS = QCMS;
QCMS.init();

