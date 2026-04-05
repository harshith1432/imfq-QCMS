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
        'project_workspace.html': 'Active Workspace',
        'repository.html': 'Knowledge Repository',
        'projects.html': 'Project Gallery',
        'projects-repository.html': 'Projects Archive',
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
        'register.html': 'Account Creation'
    },

    init(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;

        const fullPath = window.location.pathname.split('/').pop() || 'index.html';
        // Sanitize path: remove query params, hashes, and any trailing characters like %
        const path = fullPath.split('?')[0].split('#')[0].replace(/%$/, '');
        const currentPageName = this.mapping[path] || 'Resource';
        
        let html = `
            <nav aria-label="breadcrumb">
                <ol class="breadcrumb glass-breadcrumb m-0">
                    <li class="breadcrumb-item"><a href="index.html">QCMS</a></li>
        `;

        // Logic for nested levels could go here if URLs were nested, 
        // but for this flat structure, we'll show Home > Current
        if (path && path !== 'index.html') {
            html += `<li class="breadcrumb-item active" aria-current="page">${currentPageName}</li>`;
        }

        html += `
                </ol>
            </nav>
        `;

        container.innerHTML = html;
        this.applyStyles();
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
