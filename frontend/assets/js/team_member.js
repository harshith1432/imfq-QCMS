/**
 * Team Member Module Logic
 */

const teamMember = {
    projects: [],

    init() {
        console.log("Team Member Module Initialized");
        this.bindEvents();
        this.loadProjects();
        
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
    },

    showSection(sectionId) {
        document.querySelectorAll('.dashboard-section').forEach(s => s.classList.remove('active', 'd-none'));
        // Hide all, then show target
        document.querySelectorAll('.dashboard-section').forEach(s => {
            if (s.id !== `${sectionId}Section`) s.classList.add('d-none');
            else s.classList.add('active');
        });
        
        document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
        document.querySelector(`[data-section="${sectionId}"]`)?.classList.add('active');
    },

    async loadProjects() {
        try {
            this.projects = await api.get('/team-member/projects');
            this.renderDashboard();
            this.renderProjectTable();
        } catch (err) {
            console.error("Failed to load projects", err);
        }
    },

    renderDashboard() {
        // Stats
        const activeProjects = this.projects.filter(p => p.status !== 'Closed');
        const completedProjects = this.projects.filter(p => p.status === 'Closed' || p.stage === 8);
        
        // Members act on stages 1,2,3,6,7,8. Stages 4,5 are TL/Reviewer.
        const actionItems = this.projects.filter(p => [1,2,3,6,7,8].includes(p.stage) && p.status !== 'Closed');

        document.getElementById('statActive').textContent = activeProjects.length;
        document.getElementById('statActionItems').textContent = actionItems.length;
        document.getElementById('statCompleted').textContent = completedProjects.length;
        document.getElementById('actionCountBadge').textContent = actionItems.length;

        // Action Items List
        const listEl = document.getElementById('actionItemsList');
        if (actionItems.length === 0) {
            listEl.innerHTML = '<li class="list-group-item p-4 text-center text-muted">No pending action items.</li>';
        } else {
            listEl.innerHTML = actionItems.map(p => `
                <li class="list-group-item d-flex justify-content-between align-items-center p-3">
                    <div>
                        <h6 class="mb-0">${p.title}</h6>
                        <small class="text-muted">Awaiting Input - Stage ${p.stage}</small>
                    </div>
                    <button class="btn btn-sm btn-outline-success" onclick="window.location.href='workspace.html?id=${p.id}'">Open Workspace</button>
                </li>
            `).join('');
        }

        // Kanban Pipeline
        const board = document.getElementById('kanbanBoard');
        const stages = [
            "1. ID", "2. Data", "3. RCA", "4. Prop",
            "5. Review", "6. Impl", "7. Impact", "8. Close"
        ];

        board.innerHTML = stages.map((s, idx) => {
            const stageProjects = this.projects.filter(p => p.stage === (idx + 1));
            return `
                <div class="kanban-col border rounded-3 p-2 bg-light shadow-sm" style="min-width: 200px;">
                    <p class="fw-bold small mb-2 text-uppercase text-muted">${s}</p>
                    <div class="kanban-cards d-flex flex-column gap-2">
                        ${stageProjects.map(p => `
                            <div class="card shadow-sm border-0 p-2 cursor-pointer border-start border-3 ${[1,2,3,6,7,8].includes(p.stage) ? 'border-success' : 'border-secondary'}" 
                                 onclick="window.location.href='workspace.html?id=${p.id}'">
                                <div class="small fw-bold text-truncate" title="${p.title}">${p.title}</div>
                                <div class="text-muted" style="font-size:0.7rem;">${p.uid}</div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
        }).join('');
    },

    renderProjectTable() {
        const tbody = document.getElementById('projectTableBody');
        if (this.projects.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center py-4">No projects assigned yet.</td></tr>';
            return;
        }

        tbody.innerHTML = this.projects.map(p => `
            <tr>
                <td><span class="text-muted fw-bold">${p.uid}</span></td>
                <td>${p.title}</td>
                <td><span class="badge bg-success bg-opacity-10 text-success">Stage ${p.stage}</span></td>
                <td>${p.status}</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="window.location.href='workspace.html?id=${p.id}'">
                        Workspace
                    </button>
                </td>
            </tr>
        `).join('');
    }
};

document.addEventListener('DOMContentLoaded', () => {
    if (window.location.pathname.includes('dashboard-team-member.html')) {
        teamMember.init();
    }
});
