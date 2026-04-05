/**
 * Reviewer Module Logic — Real API integration
 */

const reviewer = {
    selectedProposalId: null,
    pendingAudits: [],

    init() {
        console.log("Reviewer Module Initialized");
        this.bindEvents();
        
        // Determine which page we're on for targeted logic
        const path = window.location.pathname;
        if (path.includes('audit-queue.html')) {
            this.initAuditQueue();
        } else if (path.includes('dashboard-reviewer.html')) {
            this.initDashboard();
        }

        if (window.lucide) {
            window.lucide.createIcons();
        }
    },

    bindEvents() {
        // Generic dashboard events
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
            QCMS.logout();
        });
    },

    /**
     * DASHBOARD LOGIC
     */
    initDashboard() {
        this.loadStats();
        this.loadQueue();
        this.renderStrategicChart();
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
            // Support both dashboard and audit-queue structures
            const pendingCountEl = document.getElementById('queueCount') || document.getElementById('kpi-pending-audits');
            const approvedCountEl = document.getElementById('approvedCount');
            
            if (document.getElementById('queueCount')) document.getElementById('queueCount').textContent = stats.pending_count || 0;
            if (document.getElementById('pendingBadge')) document.getElementById('pendingBadge').textContent = stats.pending_count || 0;
            if (document.getElementById('approvedCount')) document.getElementById('approvedCount').textContent = stats.approved_count || 0;
            if (document.getElementById('totalSavings')) document.getElementById('totalSavings').textContent = stats.avg_turnaround_time || '0h';
        } catch (err) {
            console.error("Failed to load stats", err);
        }
    },

    async loadQueue() {
        const priorityContainer = document.getElementById('priorityQueueList');
        try {
            const proposals = await api.get('/reviewer/pending');
            if (priorityContainer) {
                if (proposals.length > 0) {
                    priorityContainer.innerHTML = proposals.map(p => `
                        <div class="p-3 mb-3 border rounded-3 bg-white d-flex justify-content-between align-items-center">
                            <div>
                                <h6 class="mb-1">${p.title}</h6>
                                <small class="text-muted">${p.department} | Submitted: ${QCMS.formatRelative(p.submitted_at)}</small>
                            </div>
                            <button class="btn btn-sm btn-primary" onclick="reviewer.openReview(${p.project_id})">Review</button>
                        </div>
                    `).join('');
                } else {
                    priorityContainer.innerHTML = '<div class="text-center text-muted p-4">No proposals awaiting review.</div>';
                }
            }
        } catch (err) {
            console.error("Failed to load queue", err);
        }
    },

    /**
     * AUDIT QUEUE PAGE LOGIC
     */
    async initAuditQueue() {
        this.fetchAuditStats();
        this.fetchAuditQueue();

        // Listen for global search
        window.addEventListener('qcms-global-search', (e) => {
            this.filterAuditQueue(e.detail.query);
        });
    },

    async fetchAuditStats() {
        try {
            const stats = await api.get('/reviewer/stats');
            const pendingContainer = document.getElementById('kpi-pending-audits');
            const avgContainer = document.getElementById('kpi-avg-review');

            if (pendingContainer) {
                pendingContainer.innerHTML = QCMS.kpiCard('Pending Audits', stats.pending_count || 0, 'clock', 'orange');
            }
            if (avgContainer) {
                avgContainer.innerHTML = QCMS.kpiCard('Avg. Review Time', stats.avg_turnaround_time || '—', 'timer', 'blue');
            }
            if (window.lucide) lucide.createIcons();
        } catch (err) {
            console.error("Failed to fetch audit stats", err);
        }
    },

    async fetchAuditQueue() {
        const container = document.getElementById('auditQueueList');
        if (!container) return;

        try {
            container.innerHTML = `<div class="p-5 text-center"><div class="spinner-border text-primary"></div><p class="mt-2 text-secondary">Loading audits...</p></div>`;
            const audits = await api.get('/reviewer/pending');
            this.pendingAudits = audits;
            this.renderAuditQueue(audits);
        } catch (err) {
            console.error("Failed to fetch audit queue", err);
            container.innerHTML = QCMS.emptyState('Connection Error', 'Unable to reach the server. Please try again later.', 'wifi-off');
        }
    },

    renderAuditQueue(audits) {
        const container = document.getElementById('auditQueueList');
        if (!container) return;

        if (audits.length === 0) {
            container.innerHTML = QCMS.emptyState('Queue is Empty', 'All projects have been reviewed and validated. Good job!', 'check-circle');
            return;
        }

        container.innerHTML = audits.map(audit => `
            <div class="glass-card ds-card p-4 mb-3 fade-in audit-item" data-id="${audit.project_id}">
                <div class="h-stack justify-content-between align-items-center">
                    <div class="h-stack gap-4 align-items-center">
                        <div class="kpi-icon-box" style="background: rgba(var(--ds-orange-rgb), 0.1); color: var(--ds-orange); border-color: rgba(var(--ds-orange-rgb), 0.15); width: 48px; height: 48px;">
                            <i data-lucide="file-warning"></i>
                        </div>
                        <div class="v-stack">
                            <h4 class="ds-text-main fw-bold mb-1" style="font-size: 1.1rem;">${audit.title}</h4>
                            <div class="h-stack gap-2 flex-wrap">
                                <span class="ds-badge gray text-xs">${audit.department}</span>
                                <span class="text-xs text-muted opacity-50">•</span>
                                <span class="ds-text-tertiary text-xs">Submitted ${QCMS.formatRelative(audit.submitted_at)}</span>
                                <span class="text-xs text-muted opacity-50">•</span>
                                <span class="ds-text-secondary text-xs">Est. Cost: ₹${(audit.estimated_cost || 0).toLocaleString()}</span>
                            </div>
                        </div>
                    </div>
                    <div class="h-stack gap-2">
                        <button class="ds-btn ds-btn-ghost text-sm py-2 px-3" onclick="reviewer.openReview(${audit.project_id})">
                            <i data-lucide="eye" style="width:14px; height:14px; margin-right:6px;"></i> Review
                        </button>
                        <button class="ds-btn ds-btn-primary text-sm py-2 px-3" onclick="reviewer.quickApprove(${audit.project_id})">
                            <i data-lucide="check" style="width:14px; height:14px; margin-right:6px;"></i> Approve
                        </button>
                    </div>
                </div>
            </div>
        `).join('');

        if (window.lucide) lucide.createIcons();
    },

    filterAuditQueue(query) {
        const q = (query || '').toLowerCase();
        const items = document.querySelectorAll('.audit-item');
        let hasVisible = false;

        items.forEach(item => {
            const text = item.innerText.toLowerCase();
            const visible = text.includes(q);
            item.style.display = visible ? '' : 'none';
            if (visible) hasVisible = true;
        });

        const empty = document.getElementById('searchEmptyState');
        if (!hasVisible && items.length > 0) {
            if (!empty) {
                const el = document.createElement('div');
                el.id = 'searchEmptyState';
                el.innerHTML = QCMS.emptyState('No results found', `No audits match "${q}"`, 'search-x');
                document.getElementById('auditQueueList').appendChild(el);
            } else {
                empty.style.display = 'block';
            }
        } else if (empty) {
            empty.style.display = 'none';
        }
    },

    openReview(id) {
        this.selectedProposalId = id;
        const project = this.pendingAudits.find(a => a.project_id === id);
        
        const modalEl = document.getElementById('reviewModal');
        if (!modalEl) {
            console.error("Review modal not found in DOM");
            return;
        }

        const modal = new bootstrap.Modal(modalEl);
        
        // Show loading state
        document.getElementById('proposalDetailView').innerHTML = `
            <div class="text-center p-5">
                <div class="spinner-grow text-primary" role="status"></div>
                <p class="mt-3 text-secondary">Fetching context...</p>
            </div>
        `;
        
        // Fetch detailed project context
        api.get(`/reviewer/pending`).then(allPending => {
            const data = allPending.find(p => p.project_id === id);
            if (!data) throw new Error("Project not found in pending list");

            document.getElementById('proposalDetailView').innerHTML = `
                <div class="v-stack gap-4">
                    <header class="reviewer-header p-3 glass-panel rounded-3 mb-2" style="background: rgba(var(--ds-primary-rgb), 0.05);">
                        <h5 class="fw-bold mb-1">${data.title}</h5>
                        <div class="text-secondary text-sm">${data.department} | Submitted ${QCMS.formatRelative(data.submitted_at)}</div>
                    </header>

                    <section class="review-context-section">
                        <h6 class="ds-text-tertiary text-xs fw-bold text-uppercase mb-3">Goal & Problem Statement</h6>
                        <div class="p-3 border rounded-3 bg-light text-sm">${data.problem_statement || 'No problem statement provided.'}</div>
                    </section>

                    <section class="review-context-section">
                        <h6 class="ds-text-tertiary text-xs fw-bold text-uppercase mb-3">Root Cause Analysis</h6>
                        <div class="p-3 border rounded-3 bg-light text-sm">${data.root_cause_summary || 'No root cause summary provided.'}</div>
                    </section>

                    <section class="review-context-section">
                        <h6 class="ds-text-tertiary text-xs fw-bold text-uppercase mb-3">Proposed Solution & ROI</h6>
                        <div class="p-3 border rounded-3 bg-light text-sm mb-3">${data.solution || 'No solution details provided.'}</div>
                        <div class="h-stack gap-4">
                            <div class="kpi-stat">
                                <div class="text-xs text-muted mb-1">Est. Cost</div>
                                <div class="fw-bold text-primary">₹${(data.estimated_cost || 0).toLocaleString()}</div>
                            </div>
                            <div class="kpi-stat">
                                <div class="text-xs text-muted mb-1">Target Action</div>
                                <div class="fw-bold text-success">Stage 8 Transition</div>
                            </div>
                        </div>
                    </section>
                </div>
            `;
        }).catch(err => {
            console.error(err);
            document.getElementById('proposalDetailView').innerHTML = '<p class="text-danger p-4">Failed to load detailed context. Please try again.</p>';
        });
        
        modal.show();
    },

    quickApprove(id) {
        this.selectedProposalId = id;
        if (confirm("Are you sure you want to approve this project immediately?")) {
            this.submitDecision('Approved', "Quick approval via queue list.");
        }
    },

    async submitDecision(decision, providedComments = null) {
        const comments = providedComments || document.getElementById('reviewerComments')?.value;
        if (!comments && (decision === 'Rejected' || decision === 'Revision')) {
            alert("Please provide comments for rejection or revision.");
            return;
        }

        try {
            QCMS.setLoading('btn-approve', true);
            const result = await api.post(`/reviewer/decision`, {
                project_id: this.selectedProposalId,
                decision: decision,
                comments: comments || "Approved"
            });
            
            QCMS.toast(`Project ${decision} successfully.`, 'success');
            
            // Close modal if open
            const modalEl = document.getElementById('reviewModal');
            if (modalEl) {
                const modal = bootstrap.Modal.getInstance(modalEl);
                if (modal) modal.hide();
            }

            // Clear inputs
            if (document.getElementById('reviewerComments')) document.getElementById('reviewerComments').value = '';

            // Reload data
            this.fetchAuditQueue();
            this.fetchAuditStats();
            this.loadQueue(); // If on dashboard
        } catch (err) {
            QCMS.toast("Failed to submit decision: " + (err.message || 'Unknown error'), 'error');
        } finally {
            QCMS.setLoading('btn-approve', false);
        }
    }
};

// Initialize the reviewer module
document.addEventListener('DOMContentLoaded', () => {
    reviewer.init();
});

