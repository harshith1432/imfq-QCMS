/**
 * QCMS Breadcrumbs Utility
 * Dynamically generates breadcrumbs based on URL path and mapping.
 */
const Breadcrumbs = {
    mapping: {
        'dashboard-admin.html': 'Admin Dashboard',
        'dashboard-facilitator.html': 'Facilitator Dashboard',
        'dashboard-reviewer.html': 'Reviewer Dashboard',
        'dashboard-team-leader.html': 'Team Leader Dashboard',
        'dashboard-team-member.html': 'Team Member Dashboard',
        'workspace.html': 'Project Workspace',
        'repository.html': 'Knowledge Repository',
        'projects.html': 'Project Gallery',
        'projects-repository.html': 'Project Repository',
        'project-details.html': 'Project Details',
        'standards.html': 'Standards & SOPs',
        'audit-logs.html': 'System Audit Logs',
        'settings.html': 'Platform Settings',
        'user-management.html': 'User Management',
        'users.html': 'Directory',
        'departments.html': 'Department Registry',
        'profile.html': 'My Profile',
        'audit-queue.html': 'Audit Queue',
        'analytics.html': 'Performance Analytics',
        'login.html': 'Portal Access',
        'register.html': 'Account Creation',
        'super-admin.html': 'Super Admin'
    },

    getOrgName() {
        if (window.QCMS && window.QCMS.user && window.QCMS.user.platform_short_name) {
            const short = window.QCMS.user.platform_short_name.trim();
            if (short) return short;
        }
        try {
            const userStr = sessionStorage.getItem('user') || localStorage.getItem('user');
            if (userStr) {
                const u = JSON.parse(userStr);
                if (u && u.platform_short_name) {
                    const short = u.platform_short_name.trim();
                    if (short) return short;
                }
                if (u && u.org_name) return u.org_name;
            }
        } catch(e) {}
        if (window.QCMS && window.QCMS.user && window.QCMS.user.org_name) {
            return window.QCMS.user.org_name;
        }
        return 'QCMS';
    },

    escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    },

    init(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;

        const fullPath = window.location.pathname.split('/').pop() || 'index.html';
        // Sanitize path: remove query params, hashes, and any trailing characters like %
        const path = fullPath.split('?')[0].split('#')[0].replace(/%$/, '');
        const currentPageName = this.mapping[path] || 'Resource';
        const rootName = this.getOrgName();
        
        let html = `
            <nav aria-label="breadcrumb">
                <ol class="breadcrumb glass-breadcrumb m-0">
                    <li class="breadcrumb-item"><a href="index.html" class="org-breadcrumb-root">${this.escapeHtml(rootName)}</a></li>
        `;

        // Logic for nested levels could go here if URLs were nested, 
        // but for this flat structure, we'll show Home > Current
        if (path && path !== 'index.html') {
            html += `<li class="breadcrumb-item active" aria-current="page">${this.escapeHtml(currentPageName)}</li>`;
        }

        html += `
                </ol>
            </nav>
        `;

        container.innerHTML = html;
        this.applyStyles();
    },

    updateOrgName(name) {
        const targetName = name || this.getOrgName();
        const elems = document.querySelectorAll('.org-breadcrumb-root, .glass-breadcrumb .breadcrumb-item:first-child a');
        elems.forEach(el => {
            el.textContent = targetName;
        });
    },

    applyStyles() {
        if (!document.getElementById('breadcrumb-styles')) {
            const style = document.createElement('style');
            style.id = 'breadcrumb-styles';
            style.textContent = `
                .glass-breadcrumb .breadcrumb-item {
                    font-size: 0.85rem;
                    font-weight: 500;
                    color: var(--ds-text-tertiary);
                }
                .glass-breadcrumb .breadcrumb-item a {
                    color: var(--ds-text-secondary);
                    text-decoration: none;
                    transition: color 0.2s;
                }
                .glass-breadcrumb .breadcrumb-item a:hover {
                    color: var(--ds-primary);
                }
                .glass-breadcrumb .breadcrumb-item.active {
                    color: var(--ds-text-main);
                }
                .glass-breadcrumb .breadcrumb-item + .breadcrumb-item::before {
                    color: var(--ds-text-tertiary);
                    content: "/";
                    padding: 0 10px;
                }
            `;
            document.head.appendChild(style);
        }
    }
};

window.Breadcrumbs = Breadcrumbs;
