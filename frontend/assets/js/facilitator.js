/**
 * Facilitator Module Logic — Real API integration
 */

const facilitator = {
    init() {
        console.log("Facilitator Module Initialized");
        this.bindEvents();
        this.bindTabs();
        this.loadStats();
        this.loadAssistanceRequests();
        this.loadActiveProjects();
        this.renderCharts();
        
        if (window.lucide) {
            window.lucide.createIcons();
        }
    },

    bindEvents() {
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const section = item.getAttribute('data-section');
                if (section === 'logout') return;
                this.showSection(section);
            });
        });

        // Wire logout button
        document.getElementById('logoutBtn')?.addEventListener('click', () => {
            logout();
        });
    },

    showSection(sectionId) {
        document.querySelectorAll('.dashboard-section').forEach(s => s.classList.remove('active'));
        document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

        const targetSection = document.getElementById(`${sectionId}Section`);
        if (targetSection) {
            targetSection.classList.add('active');
            document.querySelector(`[data-section="${sectionId}"]`)?.classList.add('active');
            
            const titles = {
                overview: { main: "Facilitator Console", sub: "Guide, Analyze, and Validate Quality Projects" },
                projects: { main: "All Projects", sub: "Cross-department Project Visibility" },
                rca: { main: "RCA Workspace", sub: "Stage 5: Root Cause Analysis Tools" },
                impact: { main: "Impact Measurement", sub: "Stage 8: Validating KPI Improvements" },
                closure: { main: "Project Closure", sub: "Stage 8: Implementation & Lessons Learned" },
                analytics: { main: "KPI Analytics", sub: "Strategic Performance Insights" }
            };

            if (titles[sectionId]) {
                document.getElementById('pageTitle').textContent = titles[sectionId].main;
                document.getElementById('pageSubtitle').textContent = titles[sectionId].sub;
            }

            // Load section-specific data
            if (sectionId === 'rca') this.loadRcaProjects();
            if (sectionId === 'impact') this.loadImpactProjects();
            if (sectionId === 'closure') this.loadClosureProjects();
        }
    },

    async loadStats() {
        try {
            const stats = await api.get('/facilitator/stats');

            document.getElementById('pendingRcaCount').textContent = stats.pending_rca || 0;
            document.getElementById('pendingImpactCount').textContent = stats.pending_impact || 0;
            document.getElementById('avgImprovement').textContent = stats.avg_improvement || '0%';
            document.getElementById('totalSavings').textContent = typeof stats.total_savings === 'number' ? `₹${stats.total_savings.toLocaleString()}` : '₹0';
        } catch (err) {
            console.error("Failed to load stats", err);
        }
    },

    async loadActiveProjects() {
        const table = document.getElementById('activeProjectsTable');
        if (!table) return;

        try {
            const projects = await api.get('/facilitator/projects');

            if (projects.length === 0) {
                table.innerHTML = '<tr><td colspan="4" class="text-center text-muted">No active projects.</td></tr>';
                return;
            }

            table.innerHTML = projects.map(p => {
                let action = 'View';
                if (p.stage === 5) action = 'Review RCA';
                else if (p.stage === 8) action = 'Validate Impact';
                else if (p.stage === 8 && p.status === 'Pending Closure') action = 'Closure Review';

                return `
                    <tr>
                        <td><strong>${p.title}</strong><br><small class="text-muted">${p.uid || ''}</small></td>
                        <td><span class="badge bg-primary">Stage ${p.stage}</span></td>
                        <td>${p.team_leader || 'Unknown'}</td>
                        <td><button class="btn btn-sm btn-outline-primary" onclick="window.location.href='/projects/project-details.html?id=${p.id}'">${action}</button></td>
                    </tr>
                `;
            }).join('');
        } catch (err) {
            console.error("Failed to load projects", err);
            table.innerHTML = '<tr><td colspan="4" class="text-center text-danger">Failed to load project data.</td></tr>';
        }
    },

    renderCharts() {
        const ctx = document.getElementById('kpiTrendChart');
        if (!ctx) return;

        new Chart(ctx, {
            type: 'line',
            data: {
                labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
                datasets: [{
                    label: 'Cost Savings (₹)',
                    data: [12000, 19000, 15000, 25000, 22000, 30000],
                    borderColor: '#4f46e5',
                    tension: 0.4,
                    fill: true,
                    backgroundColor: 'rgba(79, 70, 229, 0.1)'
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true } }
            }
        });
    },

    async loadRcaProjects() {
        const table = document.getElementById('rcaTableBody');
        if (!table) return;

        try {
            const projects = await api.get('/facilitator/rca-projects');
            
            if (projects.length === 0) {
                table.innerHTML = `<tr><td colspan="5" class="text-center text-muted">No projects currently in RCA stage</td></tr>`;
                return;
            }

            table.innerHTML = projects.map(p => `
                <tr>
                    <td><strong>${p.title}</strong></td>
                    <td>${p.dept || 'Unknown'}</td>
                    <td>${p.tools_used.length > 0 ? p.tools_used.join(', ') : 'None'}</td>
                    <td><span class="badge ${p.has_rca ? 'bg-success' : 'bg-warning'}">${p.has_rca ? 'In Progress' : 'Not Started'}</span></td>
                    <td><button class="btn btn-sm btn-primary" onclick="window.location.href='/projects/project-details.html?id=${p.id}'">Open RCA</button></td>
                </tr>
            `).join('');
        } catch (err) {
            console.error("Failed to load RCA projects", err);
            table.innerHTML = `<tr><td colspan="5" class="text-center text-danger">Failed to load RCA data</td></tr>`;
        }
    },

    async loadImpactProjects() {
        const table = document.getElementById('impactTableBody');
        if (!table) return;

        try {
            const projects = await api.get('/facilitator/impact-projects');

            if (projects.length === 0) {
                table.innerHTML = `<tr><td colspan="5" class="text-center text-muted">No projects currently awaiting impact validation</td></tr>`;
                return;
            }

            table.innerHTML = projects.map(p => `
                <tr>
                    <td><strong>${p.title}</strong></td>
                    <td>${p.baseline ? JSON.stringify(p.baseline) : 'N/A'}</td>
                    <td>${p.final ? JSON.stringify(p.final) : 'N/A'}</td>
                    <td><span class="fw-bold text-success">${p.improvement_pct || 0}%</span></td>
                    <td><button class="btn btn-sm btn-success" onclick="window.location.href='/projects/project-details.html?id=${p.id}'">Validate</button></td>
                </tr>
            `).join('');
        } catch (err) {
            console.error("Failed to load impact projects", err);
            table.innerHTML = `<tr><td colspan="5" class="text-center text-danger">Failed to load impact data</td></tr>`;
        }
    },

    async loadClosureProjects() {
        const table = document.getElementById('closureTableBody');
        if (!table) return;

        try {
            const projects = await api.get('/facilitator/closure-projects?t=' + Date.now());

            if (projects.length === 0) {
                table.innerHTML = `<tr><td colspan="5" class="text-center text-muted">No projects currently awaiting closure</td></tr>`;
                return;
            }

            table.innerHTML = projects.map(p => `
                <tr>
                    <td><strong>${p.title}</strong></td>
                    <td><span class="badge ${['Uploaded', 'Active', 'Approved'].includes(p.sop_status) ? 'bg-success' : (p.sop_status === 'Under Review' ? 'bg-info' : 'bg-warning')}">${p.sop_status}</span></td>
                    <td>${p.lessons}</td>
                    <td><span class="badge ${p.facilitator_signoff ? 'bg-success' : 'bg-secondary'}">${p.facilitator_signoff ? 'Signed Off' : 'Pending'}</span></td>
                    <td><button class="btn btn-sm btn-primary" onclick="window.location.href='/projects/project-details.html?id=${p.id}'">Review</button></td>
                </tr>
            `).join('');
        } catch (err) {
            console.error("Failed to load closure projects", err);
            table.innerHTML = `<tr><td colspan="5" class="text-center text-danger">Failed to load closure data</td></tr>`;
        }
    },

    bindTabs() {
        const tabBtns = document.querySelectorAll('#facTabs .ds-btn-tab');
        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const targetTab = btn.getAttribute('data-tab');
                tabBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                document.querySelectorAll('.tab-content-panel').forEach(panel => panel.classList.add('d-none'));
                const targetPanel = document.getElementById(`tab-${targetTab}`);
                if (targetPanel) targetPanel.classList.remove('d-none');

                if (targetTab === 'assistance') this.loadAssistanceRequests();
                if (targetTab === 'rca') this.loadRcaProjects();
                if (targetTab === 'pipeline') this.loadPipelineProjects();
                if (targetTab === 'completed') this.loadCompletedProjects();
            });
        });
    },

    async loadAssistanceRequests() {
        const body = document.getElementById('assistanceBody');
        const countEl = document.getElementById('assistanceCount');
        if (!body) return;

        try {
            const requests = await api.get('/facilitator/assistance-requests');
            if (countEl) countEl.textContent = `${requests.length} Request${requests.length === 1 ? '' : 's'}`;

            if (!requests || requests.length === 0) {
                body.innerHTML = `<tr><td colspan="7" class="p-4 text-center text-muted">No assistance requests received.</td></tr>`;
                return;
            }

            body.innerHTML = requests.map(r => `
                <tr>
                    <td>
                        <strong>${r.project_title}</strong><br>
                        <small class="text-muted" style="font-family:monospace;">${r.project_uid}</small>
                    </td>
                    <td><span class="ds-badge blue">Stage ${r.stage_id}</span></td>
                    <td>
                        <strong>${r.user_name}</strong><br>
                        <small class="text-muted">${r.user_email || '—'}</small>
                    </td>
                    <td>
                        <div class="text-sm text-main" style="max-width: 250px; white-space: normal;">${r.message}</div>
                        ${r.response ? `<div class="text-xxs text-success mt-1"><strong>Response:</strong> ${r.response}</div>` : ''}
                    </td>
                    <td class="text-xs text-muted">${r.created_at ? new Date(r.created_at).toLocaleDateString() : '—'}</td>
                    <td>
                        <span class="ds-badge ${r.status === 'Pending' ? 'orange' : 'green'}">${r.status}</span>
                    </td>
                    <td class="text-end">
                        <button class="ds-btn ds-btn-sm ds-btn-outline" onclick="window.location.href='/projects/project-details.html?id=${r.project_id}&stage=${r.stage_id}'">
                            Open Project
                        </button>
                    </td>
                </tr>
            `).join('');
        } catch (err) {
            console.error("Failed to load assistance requests", err);
            body.innerHTML = `<tr><td colspan="7" class="p-4 text-center text-danger">Failed to load assistance requests.</td></tr>`;
        }
    },

    async loadPipelineProjects() {
        const body = document.getElementById('pipelineBody');
        const countEl = document.getElementById('pipelineCount');
        if (!body) return;
        try {
            const projects = await api.get('/facilitator/projects');
            if (countEl) countEl.textContent = `${projects.length} Project${projects.length === 1 ? '' : 's'}`;
            if (!projects || projects.length === 0) {
                body.innerHTML = `<tr><td colspan="5" class="p-4 text-center text-muted">No pipeline projects found.</td></tr>`;
                return;
            }
            body.innerHTML = projects.map(p => `
                <tr>
                    <td><strong>${p.title}</strong><br><small class="text-muted">${p.uid || ''}</small></td>
                    <td>${p.dept || 'N/A'}</td>
                    <td><span class="ds-badge blue">Stage ${p.stage}</span></td>
                    <td><span class="ds-badge orange">${p.status}</span></td>
                    <td class="text-end"><button class="ds-btn ds-btn-sm ds-btn-outline" onclick="window.location.href='/projects/project-details.html?id=${p.id}'">View</button></td>
                </tr>
            `).join('');
        } catch (err) {
            body.innerHTML = `<tr><td colspan="5" class="p-4 text-center text-danger">Failed to load pipeline projects.</td></tr>`;
        }
    },

    async loadCompletedProjects() {
        const body = document.getElementById('completedBody');
        const countEl = document.getElementById('completedCount');
        if (!body) return;
        try {
            const projects = await api.get('/facilitator/completed-projects');
            if (countEl) countEl.textContent = `${projects.length} Project${projects.length === 1 ? '' : 's'}`;
            if (!projects || projects.length === 0) {
                body.innerHTML = `<tr><td colspan="5" class="p-4 text-center text-muted">No completed projects found.</td></tr>`;
                return;
            }
            body.innerHTML = projects.map(p => `
                <tr>
                    <td><strong>${p.title}</strong><br><small class="text-muted">${p.uid || ''}</small></td>
                    <td>${p.dept || 'N/A'}</td>
                    <td><span class="ds-badge green">Stage 8</span></td>
                    <td><span class="ds-badge green">Closed</span></td>
                    <td class="text-end"><button class="ds-btn ds-btn-sm ds-btn-outline" onclick="window.location.href='/projects/project-details.html?id=${p.id}'">View</button></td>
                </tr>
            `).join('');
        } catch (err) {
            body.innerHTML = `<tr><td colspan="5" class="p-4 text-center text-danger">Failed to load completed projects.</td></tr>`;
        }
    }
};

document.addEventListener('DOMContentLoaded', () => {
    if (window.location.pathname.includes('dashboard-facilitator.html')) {
        facilitator.init();
    }
});
