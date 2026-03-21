/**
 * QCMS Enterprise - Shared UI Components
 * v1.0 - Handle sidebars, navbars, and role-based UI logic.
 */

document.addEventListener('DOMContentLoaded', () => {
    initUI();
});

function initUI() {
    const userStr = localStorage.getItem('user');
    if (!userStr) return;

    const user = JSON.parse(userStr);
    const roleName = user.role || 'Member'; // Unified to 'role'

    renderSidebar(roleName);
    renderNavbar(user);
    setActiveLink();
    if (window.lucide) lucide.createIcons();
}

/**
 * Render standard Navbar for all roles
 */
function renderNavbar(user) {
    const navbar = document.getElementById('app-navbar');
    if (!navbar) return;

    navbar.innerHTML = `
        <div class="navbar-left">
            <div class="page-breadcrumb d-none d-md-flex align-items-center">
                <span class="text-muted text-xs">QCMS</span>
                <i data-lucide="chevron-right" class="mx-2 text-muted" style="width:12px;"></i>
                <span class="text-primary fw-medium">${document.title.split('|')[0].trim()}</span>
            </div>
        </div>
        <div class="navbar-right">
            <div class="d-flex align-items-center gap-2">
                <button class="nav-icon-btn position-relative" title="Notifications" onclick="QCMS.showNotifications()">
                    <i data-lucide="bell"></i>
                    <span class="notification-dot"></span>
                </button>
                <div class="v-divider mx-2"></div>
                <div class="user-pill d-flex align-items-center gap-2 px-2 py-1 clickable" onclick="window.location.href='profile.html'">
                    <div class="user-avatar-sm">${(user.username || 'U').charAt(0).toUpperCase()}</div>
                    <div class="user-meta d-none d-sm-block">
                        <div class="user-name-sm">${user.username || 'User'}</div>
                        <div class="user-role-sm">${user.role || 'Member'}</div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    if (window.lucide) lucide.createIcons();
}

/**
 * Render Role-Specific Sidebar
 */
function renderSidebar(roleName) {
    const sidebar = document.getElementById('app-sidebar');
    if (!sidebar) return;

    let navItems = '';

    const commonItems = `
        <div class="sidebar-section">
            <div class="sidebar-section-label">Main</div>
            <nav class="sidebar-nav">
                <a href="dashboard-${roleToSlug(roleName)}.html" class="sidebar-link active">
                    <i class="link-icon" data-lucide="layout-dashboard"></i>
                    <span>Overview</span>
                </a>
                <a href="projects.html" class="sidebar-link">
                    <i class="link-icon" data-lucide="folder-kanban"></i>
                    <span>My Projects</span>
                </a>
                <a href="projects-repository.html" class="sidebar-link">
                    <i class="link-icon" data-lucide="layers"></i>
                    <span>Project Repository</span>
                </a>
                <a href="analytics.html" class="sidebar-link">
                    <i class="link-icon" data-lucide="bar-chart-3"></i>
                    <span>Analytics</span>
                </a>
            </nav>
        </div>
    `;

    const adminExtra = `
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

    const knowledgeBase = `
        <div class="sidebar-section">
            <div class="sidebar-section-label">Resources</div>
            <nav class="sidebar-nav">
                <a href="repository.html" class="sidebar-link">
                    <i class="link-icon" data-lucide="database"></i>
                    <span>Knowledge Repo</span>
                </a>
                <a href="standards.html" class="sidebar-link">
                    <i class="link-icon" data-lucide="file-check-2"></i>
                    <span>Standards & SOPs</span>
                </a>
            </nav>
        </div>
    `;

    const footerItems = `
        <div class="sidebar-footer">
            <nav class="sidebar-nav">
                <a href="settings.html" class="sidebar-link">
                    <i class="link-icon" data-lucide="settings"></i>
                    <span>Settings</span>
                </a>
                <a href="#" class="sidebar-link text-danger" id="logout-btn">
                    <i class="link-icon" data-lucide="log-out"></i>
                    <span>Logout</span>
                </a>
            </nav>
        </div>
    `;

    let content = `
        <div class="sidebar-brand">
            <div class="brand-icon">
                <i data-lucide="shield-check"></i>
            </div>
            <div class="brand-text">
                QCMS <small>Enterprise Edition</small>
            </div>
        </div>
    `;

    content += commonItems;
    if (roleName === 'Admin') content += adminExtra;
    content += knowledgeBase;
    content += footerItems;

    sidebar.innerHTML = content;

    // Add logout listener
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', (e) => {
            e.preventDefault();
            logout();
        });
    }

    if (window.lucide) lucide.createIcons();
}

/**
 * UI Utilities
 */
const QCMS = {
    user: null,
    init() {
        const userStr = localStorage.getItem('user');
        if (userStr) this.user = JSON.parse(userStr);
        initUI();
    },

    setLoading(btnId, isLoading) {
        const btn = document.getElementById(btnId);
        if (!btn) return;

        if (isLoading) {
            btn.setAttribute('data-original-html', btn.innerHTML);
            btn.disabled = true;
            btn.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Loading...`;
        } else {
            const originalHtml = btn.getAttribute('data-original-html');
            if (originalHtml) {
                btn.innerHTML = originalHtml;
            }
            btn.disabled = false;
        }
    },

    showNotifications() {
        this.toast('System Check: All modules operating normally. No pending alerts.', 'success');
        const dot = document.querySelector('.notification-dot');
        if (dot) dot.style.display = 'none';
    },

    kpiCard(label, value, icon, color = 'blue', trend = null) {
        const trendIcon = trend > 0 ? 'trending-up' : 'trending-down';
        const trendColor = trend > 0 ? 'text-green' : 'text-red';
        return `
            <div class="kpi-card ds-card p-4 h-100 kpi-premium">
                <div class="d-flex justify-content-between align-items-start mb-3">
                    <div class="kpi-icon-box bg-${color}-subtle text-${color}">
                        <i data-lucide="${icon}"></i>
                    </div>
                    ${trend !== null ? `
                        <div class="trend-badge ${trendColor}">
                            <i data-lucide="${trendIcon}" style="width:12px; height:12px;"></i>
                            <span>${Math.abs(trend)}%</span>
                        </div>
                    ` : ''}
                </div>
                <div class="kpi-label">${label}</div>
                <div class="kpi-value">${value}</div>
            </div>
        `;
    },

    badge(text, color = 'blue') {
        return `<span class="ds-badge ${color}">${text}</span>`;
    },

    statusBadge(status) {
        const s = (status || '').toLowerCase();
        let color = 'gray';
        if (s.includes('active') || s.includes('in_progress') || s.includes('approved') || s.includes('open')) color = 'blue';
        if (s.includes('completed') || s.includes('closed') || s.includes('success') || s.includes('done')) color = 'green';
        if (s.includes('pending') || s.includes('review') || s.includes('warning') || s.includes('stalled')) color = 'orange';
        if (s.includes('rejected') || s.includes('failed') || s.includes('danger') || s.includes('inactive')) color = 'red';
        return `<span class="ds-badge ${color}">${status}</span>`;
    },

    categoryBadge(cat) {
        const hash = Array.from(cat).reduce((acc, char) => char.charCodeAt(0) + ((acc << 5) - acc), 0);
        const colors = ['blue', 'green', 'orange', 'red', 'cyan', 'gray'];
        const color = colors[Math.abs(hash) % colors.length];
        return `<span class="ds-badge ${color}">${cat}</span>`;
    },

    emptyState(icon, title, message) {
        return `
            <div class="empty-state">
                <i class="empty-icon" data-lucide="${icon}"></i>
                <h5>${title}</h5>
                <p>${message}</p>
            </div>
        `;
    },

    formatRelative(dateStr) {
        if (!dateStr) return '—';
        let normalized = dateStr;
        if (typeof dateStr === 'string' && !dateStr.endsWith('Z') && !dateStr.includes('+')) {
            normalized += 'Z';
        }
        const date = new Date(normalized);
        const now = new Date();
        const diff = (now - date) / 1000;
        if (diff < 60) return 'Just now';
        if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
        return date.toLocaleDateString();
    },

    stageStepper(currentStage) {
        const stages = ['ID', 'Data', 'RCA', 'Plan', 'Appr', 'Exec', 'Impact', 'Close'];
        return `
            <div class="ds-stepper">
                ${stages.map((s, i) => {
                    const status = i + 1 < currentStage ? 'completed' : (i + 1 === currentStage ? 'active' : 'pending');
                    return `
                        <div class="step ${status}">
                            <div class="step-circle">${i + 1 < currentStage ? '<i data-lucide="check" style="width:12px;height:12px;"></i>' : i + 1}</div>
                            <div class="step-label">${s}</div>
                        </div>
                    `;
                }).join('<div class="step-line"></div>')}
            </div>
        `;
    },

    chartPlaceholder(title = "No Data Available") {
        return `
            <div class="d-flex flex-column align-items-center justify-content-center p-5 text-center fade-in">
                <div class="mb-3 opacity-20">
                    <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/>
                    </svg>
                </div>
                <h6 class="fw-bold mb-1">${title}</h6>
                <p class="text-xs text-muted">Awaiting synchronization with server...</p>
            </div>
        `;
    },

    tableSkeleton(rows = 5) {
        let content = '';
        for(let i=0; i<rows; i++) {
            content += `
                <tr>
                    <td><div class="skeleton-text skeleton" style="width:180px;"></div></td>
                    <td><div class="skeleton-text skeleton" style="width:120px;"></div></td>
                    <td><div class="skeleton-text skeleton" style="width:150px;"></div></td>
                    <td><div class="skeleton-text skeleton" style="width:100px;"></div></td>
                    <td><div class="skeleton-text skeleton" style="width:120px;"></div></td>
                    <td class="text-end"><div class="skeleton-badge skeleton ml-auto" style="width:60px;"></div></td>
                </tr>
            `;
        }
        return content;
    },

    projectProgress(currentStage, totalStages = 8) {
        const pct = Math.round((currentStage / totalStages) * 100);
        return `
            <div class="ds-progress-container">
                <div class="ds-progress-label">
                    <span>Stage ${currentStage}/${totalStages}</span>
                    <span>${pct}%</span>
                </div>
                <div class="ds-progress-bar">
                    <div class="ds-progress-fill" style="width: ${pct}%"></div>
                </div>
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

function roleToSlug(role) {
    return role.toLowerCase().replace(' ', '-');
}

function getInitials(name) {
    return name.split(' ').map(n => n[0]).join('').toUpperCase().substring(0, 2);
}

function setActiveLink() {
    const currentPath = window.location.pathname.split('/').pop();
    const links = document.querySelectorAll('.sidebar-link');
    links.forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });
}

function logout() {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = '/login.html';
}

function initTooltips() {
    // Basic tooltip logic if needed
}
