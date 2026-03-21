/**
 * Reviewer Module Logic — Real API integration
 */

const reviewer = {
    selectedProposalId: null,

    init() {
        console.log("Reviewer Module Initialized");
        this.bindEvents();
        this.loadStats();
        this.loadQueue();
        this.renderStrategicChart();
        
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
                overview: { main: "Reviewer Console", sub: "Strategic Project Authorization & Governance" },
                approvals: { main: "Approval Queue", sub: "High-Priority Strategic Decisions" },
                analytics: { main: "Strategic Analytics", sub: "Organization-wide Quality Impact" },
                projects: { main: "Project History", sub: "Audit Trail of Past Decisions" }
            };

            if (titles[sectionId]) {
                document.getElementById('pageTitle').textContent = titles[sectionId].main;
                document.getElementById('pageSubtitle').textContent = titles[sectionId].sub;
            }
        }
    },

    async loadStats() {
        try {
            const stats = await api.get('/reviewer/stats');

            document.getElementById('queueCount').textContent = stats.queue || 0;
            document.getElementById('pendingBadge').textContent = stats.queue || 0;
            document.getElementById('approvedCount').textContent = stats.approved || 0;
            document.getElementById('totalSavings').textContent = typeof stats.savings === 'number' ? `$${stats.savings.toLocaleString()}` : stats.savings || '$0';
            document.getElementById('avgRoi').textContent = stats.roi || '0%';
        } catch (err) {
            console.error("Failed to load stats", err);
        }
    },

    async loadQueue() {
        const priorityContainer = document.getElementById('priorityQueueList');
        const fullTable = document.getElementById('fullQueueTable');

        try {
            const proposals = await api.get('/reviewer/queue');

            if (proposals.length > 0) {
                if (priorityContainer) {
                    priorityContainer.innerHTML = proposals.map(p => `
                        <div class="p-3 mb-3 border rounded-3 bg-white d-flex justify-content-between align-items-center">
                            <div>
                                <h6 class="mb-1">${p.title}</h6>
                                <small class="text-muted">${p.dept} | ROI: ${p.roi || 0}% | Budget: $${(p.budget || 0).toLocaleString()}</small>
                            </div>
                            <button class="btn btn-sm btn-primary" onclick="reviewer.openReview(${p.id})">Review</button>
                        </div>
                    `).join('');
                }

                if (fullTable) {
                    fullTable.innerHTML = proposals.map(p => `
                        <tr>
                            <td><strong>${p.title}</strong></td>
                            <td>${p.dept}</td>
                            <td>${p.team_leader}</td>
                            <td><span class="text-success fw-bold">${p.roi || 0}%</span></td>
                            <td><button class="btn btn-sm btn-primary" onclick="reviewer.openReview(${p.id})">Review</button></td>
                        </tr>
                    `).join('');
                }
            } else {
                if (priorityContainer) {
                    priorityContainer.innerHTML = '<div class="text-center text-muted p-4">No proposals awaiting review.</div>';
                }
            }
        } catch (err) {
            console.error("Failed to load queue", err);
            if (priorityContainer) {
                priorityContainer.innerHTML = '<div class="text-center text-danger p-4">Failed to load approval queue.</div>';
            }
        }
    },

    openReview(id) {
        this.selectedProposalId = id;
        const modal = new bootstrap.Modal(document.getElementById('reviewModal'));
        
        // Load proposal details from API
        api.get(`/team-leader/projects/${id}`).then(data => {
            document.getElementById('proposalDetailView').innerHTML = `
                <div class="row">
                    <div class="col-md-8">
                        <h4>${data.title}</h4>
                        <p class="text-muted">${data.description || 'No description provided'}</p>
                        <hr>
                        ${data.proposal ? `
                        <div class="mb-3">
                            <h6>Budget Required</h6>
                            <p class="fw-bold text-primary">$${(data.proposal.budget || 0).toLocaleString()}</p>
                        </div>
                        <div class="mb-3">
                            <h6>Estimated ROI</h6>
                            <p class="fw-bold text-success">${data.proposal.roi || 0}%</p>
                        </div>
                        <div class="mb-3">
                            <h6>Resource Plan</h6>
                            <p>${data.proposal.resources || 'Not specified'}</p>
                        </div>
                        ` : '<p class="text-muted">No proposal data available</p>'}
                    </div>
                    <div class="col-md-4">
                        <div class="card bg-light border-0">
                            <div class="card-body">
                                <h6>Project Info</h6>
                                <p class="mb-1"><strong>Stage:</strong> ${data.stage}</p>
                                <p class="mb-1"><strong>Status:</strong> ${data.status}</p>
                                <p class="mb-1"><strong>Team:</strong> ${data.members ? data.members.map(m => m.name).join(', ') : 'None'}</p>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }).catch(err => {
            document.getElementById('proposalDetailView').innerHTML = '<p class="text-danger">Failed to load proposal details.</p>';
        });
        
        modal.show();
    },

    async submitDecision(decision) {
        const comments = document.getElementById('reviewerComments').value;
        if (!comments && (decision === 'Rejected' || decision === 'Revision')) {
            alert("Please provide comments for rejection or revision.");
            return;
        }

        try {
            const result = await api.post(`/reviewer/approve/${this.selectedProposalId}`, {
                decision: decision,
                comments: comments
            });
            
            alert(result.msg || `Project ${decision} successfully.`);
            const modal = bootstrap.Modal.getInstance(document.getElementById('reviewModal'));
            modal.hide();
            this.loadQueue();
            this.loadStats();
        } catch (err) {
            alert("Failed to submit decision: " + (err.message || 'Unknown error'));
        }
    },

    renderStrategicChart() {
        const ctx = document.getElementById('strategicChart');
        if (!ctx) return;

        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Prod', 'Quality', 'Safety', 'Cost'],
                datasets: [{
                    data: [40, 30, 15, 15],
                    backgroundColor: ['#4f46e5', '#34d399', '#f87171', '#fbbf24']
                }]
            },
            options: { cutout: '70%', plugins: { legend: { position: 'bottom' } } }
        });
    }
};

document.addEventListener('DOMContentLoaded', () => {
    if (window.location.pathname.includes('dashboard-reviewer.html')) {
        reviewer.init();
    }
});
