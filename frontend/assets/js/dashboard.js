const dashboard = {
    init: async function() {
        const userJson = localStorage.getItem('user');
        if (!userJson) {
            window.location.href = 'login.html';
            return;
        }
        const user = JSON.parse(userJson);
        const role = user.role;

        // Set Profile Info (if elements exist)
        const nameDisplay = document.getElementById('userNameDisplay');
        const roleDisplay = document.getElementById('userRoleDisplay');
        if (nameDisplay) nameDisplay.textContent = user.username;
        if (roleDisplay) roleDisplay.textContent = role;

        // Initialize Icons
        if (window.lucide) lucide.createIcons();

        // Load Data
        await this.loadStats(role);
        await this.loadProjects();
    },

    loadStats: async function(role) {
        try {
            const stats = await api.get('/analytics/dashboard');
            const summary = stats.summary || {};
            
            // Map data to UI elements if they exist
            const mappings = {
                'totalProjects': summary.total_projects || 0,
                'totalSavings': `$${(summary.total_savings || 0).toLocaleString()}`,
                'successRate': `${summary.success_rate || 0}%`,
                'adminUserCount': summary.user_count || 0,
                'qhOrgSavings': `$${(summary.org_savings || 0).toLocaleString()}`,
                'laPendingAudits': summary.pending_audits || 0,
                'laComplianceScore': `${summary.compliance_score || 0}%`,
                'pmResourceUtil': '94%', // Mocked for now
                'pmDelays': '2 Projects', // Mocked for now
                'tmTasks': summary.pending_tasks || 0,
                'tmContributions': '12' // Mocked for now
            };

            for (const [id, value] of Object.entries(mappings)) {
                const el = document.getElementById(id);
                if (el) el.textContent = value;
            }

            // Render Charts if canvas exists
            if (document.getElementById('savingsChart')) {
                this.renderTrendsChart(stats.trends || []);
            }
            if (document.getElementById('statusChart')) {
                this.renderStatusChart(stats.status_distribution || {});
            }

        } catch (err) {
            console.error('Error loading dashboard stats:', err);
        }
    },

    loadProjects: async function() {
        const projectsTable = document.getElementById('projectsTable');
        if (!projectsTable) return;

        try {
            const projects = await api.get('/projects');
            projectsTable.innerHTML = '';

            projects.slice(0, 5).forEach(p => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td><span class="uid-pill">${p.uid}</span></td>
                    <td class="font-medium">${p.title}</td>
                    <td><span class="stage-pill">Stage ${p.current_stage}</span></td>
                    <td><span class="status-pill ${p.status.toLowerCase().replace(' ', '-')}">${p.status}</span></td>
                    <td class="font-mono text-success">$${(p.financial_impact || 0).toLocaleString()}</td>
                    <td class="text-right">
                        <button class="btn btn-secondary btn-sm" onclick="window.location.href='workspace.html?id=${p.id}'">
                            <i data-lucide="external-link"></i> Open
                        </button>
                    </td>
                `;
                projectsTable.appendChild(tr);
            });
            if (window.lucide) lucide.createIcons();
        } catch (err) {
            console.error('Error loading projects:', err);
        }
    },

    renderTrendsChart: function(data) {
        const el = document.getElementById('savingsChart');
        if (!el) return;
        const ctx = el.getContext('2d');
        
        const gradient = ctx.createLinearGradient(0, 0, 0, 300);
        gradient.addColorStop(0, 'rgba(99, 102, 241, 0.2)');
        gradient.addColorStop(1, 'rgba(99, 102, 241, 0)');

        new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.length ? data.map(d => d.month) : ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                datasets: [{
                    label: 'Impact ($)',
                    data: data.length ? data.map(d => d.amount) : [12000, 19000, 15000, 25000, 22000, 30000],
                    borderColor: '#6366f1',
                    borderWidth: 3,
                    pointBackgroundColor: '#fff',
                    pointBorderColor: '#6366f1',
                    tension: 0.4,
                    fill: true,
                    backgroundColor: gradient
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { 
                    y: { beginAtZero: true, grid: { color: '#f1f5f9' } },
                    x: { grid: { display: false } }
                }
            }
        });
    },

    renderStatusChart: function(data) {
        const el = document.getElementById('statusChart');
        if (!el) return;
        const ctx = el.getContext('2d');
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: Object.keys(data).length ? Object.keys(data) : ['Active', 'Completed', 'On Hold'],
                datasets: [{
                    data: Object.values(data).length ? Object.values(data) : [12, 5, 3],
                    backgroundColor: ['#6366f1', '#10b981', '#f59e0b'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'bottom' } },
                cutout: '70%'
            }
        });
    },

    refresh: function() {
        this.init();
    }
};

document.addEventListener('DOMContentLoaded', () => dashboard.init());
// Export to window for global access (like refresh buttons)
window.dashboard = dashboard;
