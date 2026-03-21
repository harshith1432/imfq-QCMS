/**
 * Team Leader Module — Full API integration with centralized api.js helper
 */

const teamLeader = {
    init() {
        console.log("Team Leader Module Initialized");
        this.bindEvents();
        this.loadStats();
        this.loadQueue();
        this.renderKanban();
        this.loadMembers();
        
        // Set username in header
        const user = JSON.parse(localStorage.getItem('user'));
        if (user) {
            document.getElementById('userName').textContent = user.username;
        }
        
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

        // Wire logout
        document.getElementById('logoutBtn')?.addEventListener('click', () => {
            logout();
        });

        // Wire project init form
        document.getElementById('initProjectForm')?.addEventListener('submit', (e) => this.handleInitialization(e));
    },

    showSection(sectionId) {
        document.querySelectorAll('.dashboard-section').forEach(s => s.classList.remove('active'));
        document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

        const targetSection = document.getElementById(`${sectionId}Section`);
        if (targetSection) {
            targetSection.classList.add('active');
            document.querySelector(`[data-section="${sectionId}"]`)?.classList.add('active');
            
            if (sectionId === 'projects') this.loadProjectTable();
        }
    },

    async loadStats() {
        try {
            const data = await api.get('/team-leader/dashboard-stats');
            
            document.getElementById('deptSavings').textContent = `$${(data.total_savings || 0).toLocaleString()}`;
            document.getElementById('activeCount').textContent = data.total_projects || 0;
            document.getElementById('queueCount').textContent = data.queue_count || 0;
        } catch (err) {
            console.error("Stats failed", err);
        }
    },

    async loadQueue() {
        const container = document.getElementById('validationQueueList');
        try {
            const queue = await api.get('/team-leader/queue');
            
            if (queue.length > 0) {
                container.innerHTML = queue.map(item => `
                    <div class="queue-item d-flex justify-content-between align-items-center p-3 border rounded-3 mb-2 bg-white shadow-sm">
                        <div>
                            <span class="badge bg-soft-primary text-primary mb-1">Stage ${item.stage}</span>
                            <h6 class="mb-0">${item.title}</h6>
                            <small class="text-muted">${item.type || ''}</small>
                        </div>
                        <div class="d-flex gap-2">
                            <button class="btn btn-sm btn-outline-primary" onclick="window.location.href='workspace.html?id=${item.id}'">Review</button>
                            <button class="btn btn-sm btn-primary" onclick="teamLeader.confirmAction(${item.id}, 'proceed')">Validate & Proceed</button>
                        </div>
                    </div>
                `).join('');
            } else {
                container.innerHTML = '<p class="text-center text-muted m-0">No pending validations.</p>';
            }
        } catch (err) {
            console.error("Queue failed", err);
        }
    },

    async renderKanban() {
        const board = document.getElementById('kanbanBoard');
        if (!board) return;
        
        const stages = [
            "1. Identification", "2. Data Collection", "3. Root Cause", "4. Proposal",
            "5. Approval", "6. Implementation", "7. Impact", "8. Standardization"
        ];

        try {
            const projects = await api.get('/team-leader/projects');
            
            board.innerHTML = stages.map((s, idx) => {
                const stageProjects = projects.filter(p => p.stage === (idx + 1));
                return `
                    <div class="kanban-col border rounded-3 p-2 bg-light" style="min-width: 220px;">
                        <p class="fw-bold small mb-2 text-uppercase text-muted">${s}</p>
                        <div class="kanban-cards d-flex flex-column gap-2">
                            ${stageProjects.length > 0 ? stageProjects.map(p => `
                                <div class="card shadow-sm border-0 p-2 cursor-pointer" onclick="window.location.href='workspace.html?id=${p.id}'" style="cursor:pointer;">
                                    <div class="small fw-bold text-truncate">${p.title}</div>
                                    <div class="text-muted" style="font-size:0.7rem;">${p.uid || ''}</div>
                                    ${p.category ? `<span class="badge bg-soft-primary text-primary mt-1" style="font-size:0.65rem;">${p.category}</span>` : ''}
                                </div>
                            `).join('') : '<p class="text-muted small text-center m-0">—</p>'}
                        </div>
                    </div>
                `;
            }).join('');
        } catch (err) {
            console.error("Kanban failed", err);
            board.innerHTML = '<p class="text-danger">Failed to load project pipeline.</p>';
        }
    },

    async loadMembers() {
        const target = document.getElementById('memberChecklist');
        if (!target) return;
        
        try {
            // Use dept-filtered TL members endpoint (not admin/users)
            const users = await api.get('/team-leader/members');
            
            if (users.length === 0) {
                target.innerHTML = '<p class="text-muted small m-0">No department members found.</p>';
                return;
            }
            
            target.innerHTML = users.map(u => `
                <div class="form-check">
                    <input class="form-check-input" type="checkbox" value="${u.id}" name="members" id="m${u.id}">
                    <label class="form-check-label small" for="m${u.id}">${u.username} <span class="text-muted">(${u.role})</span></label>
                </div>
            `).join('');
        } catch (err) {
            console.error("Members load failed", err);
            target.innerHTML = '<p class="text-danger small m-0">Failed to load members.</p>';
        }
    },

    async handleInitialization(e) {
        e.preventDefault();
        const fd = new FormData(e.target);
        const memberIds = Array.from(e.target.querySelectorAll('input[name="members"]:checked')).map(cb => parseInt(cb.value));
        
        const payload = {
            title: fd.get('title'),
            description: fd.get('description'),
            category: fd.get('category'),
            deadline: fd.get('deadline') || null,
            member_ids: memberIds
        };

        const submitBtn = e.target.querySelector('button[type="submit"]');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Creating...';

        try {
            const result = await api.post('/team-leader/initialize', payload);
            
            alert("Project initialized successfully!");
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('initProjectModal'));
            if (modal) modal.hide();
            
            // Redirect to workspace
            if (result.project_id) {
                window.location.href = `workspace.html?id=${result.project_id}`;
            } else {
                window.location.reload();
            }
        } catch (err) {
            alert(err.message || "Initialization failed. Please try again.");
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Create & Start Stage 1';
        }
    },

    async confirmAction(id, action) {
        if (!confirm(`Are you sure you want to validate and proceed this project to the next stage?`)) return;
        
        try {
            await api.post(`/team-leader/action/${id}/proceed`);
            this.loadQueue();
            this.renderKanban();
            this.loadStats();
        } catch (err) {
            alert("Action failed: " + (err.message || ''));
        }
    },

    async loadProjectTable() {
        const tbody = document.getElementById('projectsTableBody');
        if (!tbody) return;

        try {
            const projects = await api.get('/team-leader/projects');
            
            tbody.innerHTML = projects.map(p => `
                <tr>
                    <td><code>${p.uid || p.id}</code></td>
                    <td><strong>${p.title}</strong></td>
                    <td><span class="badge bg-primary">Stage ${p.stage}</span></td>
                    <td><span class="badge ${p.status === 'In Progress' ? 'bg-success' : p.status === 'Closed' ? 'bg-secondary' : 'bg-warning'}">${p.status}</span></td>
                    <td>${p.members ? p.members.map(m => m.name).join(', ') : '—'}</td>
                    <td><button class="btn btn-sm btn-outline-primary" onclick="window.location.href='workspace.html?id=${p.id}'">Open</button></td>
                </tr>
            `).join('');

            if (projects.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No projects found.</td></tr>';
            }
        } catch (err) {
            console.error("Project table load failed", err);
        }
    }
};

document.addEventListener('DOMContentLoaded', () => {
    if (window.location.pathname.includes('dashboard-team-leader.html')) {
        teamLeader.init();
    }
});
