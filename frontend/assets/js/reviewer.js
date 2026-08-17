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

        // Check if user is Admin, and update UI accordingly
        try {
            const currentUser = JSON.parse(sessionStorage.getItem('user') || '{}');
            if (currentUser.role === 'Admin') {
                const badgeEl = document.querySelector('.ds-badge.orange.text-xs');
                if (badgeEl) {
                    badgeEl.textContent = 'Stage 8 Closure Review';
                    badgeEl.className = 'ds-badge green text-xs';
                }
                const subtitleEl = document.querySelector('.ds-text-secondary');
                if (subtitleEl) {
                    subtitleEl.textContent = 'Review completed projects and authorize final administrative closure.';
                }
            }
        } catch (e) {
            console.error("Failed to parse user role for UI updates", e);
        }
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

    async openReview(id, showStageNum = null) {
        this.selectedProposalId = id;
        const project = this.pendingAudits.find(a => a.project_id === id);
        
        const modalEl = document.getElementById('reviewModal');
        if (!modalEl) {
            console.error("Review modal not found in DOM");
            return;
        }

        const modal = new bootstrap.Modal(modalEl);
        
        // Show loading state if it is the first load
        if (!project.all_workflows) {
            document.getElementById('proposalDetailView').innerHTML = `
                <div class="text-center p-5">
                    <div class="spinner-grow text-primary" role="status"></div>
                    <p class="mt-3 text-secondary">Fetching context...</p>
                </div>
            `;
            try {
                const projectDetails = await api.get('/projects/' + id);
                project.all_workflows = projectDetails.workflows || [];
            } catch (e) {
                console.error("Failed to load project details for review history", e);
                project.all_workflows = [];
            }
        }

        const activeStage = showStageNum || project.pending_stage;

        api.get(`/reviewer/pending`).then(allPending => {
            const data = allPending.find(p => p.project_id === id);
            if (!data) throw new Error("Project not found in pending list");

            // Extract the active stage's data
            let d = {};
            if (activeStage === data.pending_stage) {
                d = data.stage_data || {};
            } else {
                const wf = project.all_workflows.find(w => w.stage_id === activeStage);
                d = wf ? { data: wf.data } : {};
            }

            // Build the stage tabs navigation
            let stageTabs = '';
            if (project.all_workflows && project.all_workflows.length > 0) {
                stageTabs = `
                    <div class="mb-4">
                        <div class="text-xs text-muted fw-bold mb-2 uppercase tracking-wider">Project Stage History</div>
                        <div class="d-flex flex-wrap gap-1.5 p-1.5 rounded-3" style="border: 1px solid rgba(0,0,0,0.08); background: rgba(0,0,0,0.03);">
                            ${[1, 2, 3, 4, 5, 6, 7, 8].map(sNum => {
                                const isCurrentPending = (sNum === data.pending_stage);
                                const isActive = (sNum === activeStage);
                                const hasData = project.all_workflows.some(w => w.stage_id === sNum) || sNum === data.pending_stage;
                                
                                let btnClass = 'ds-btn ds-btn-sm ';
                                if (isActive) {
                                    btnClass += 'ds-btn-primary';
                                } else if (isCurrentPending) {
                                    btnClass += 'ds-btn-outline border-warning text-warning';
                                } else if (hasData) {
                                    btnClass += 'ds-btn-outline border-secondary text-secondary';
                                } else {
                                    btnClass += 'ds-btn-ghost text-muted opacity-50';
                                }
                                
                                let label = `Stage ${sNum}`;
                                if (isCurrentPending) {
                                    label += ' ⚠️';
                                }
                                
                                return `<button type="button" class="${btnClass} py-1 px-2.5" ${hasData ? `onclick="reviewer.openReview(${data.project_id}, ${sNum})"` : 'disabled'} style="font-size: 0.72rem; border-radius: 6px;">
                                    ${label}
                                </button>`;
                            }).join('')}
                        </div>
                    </div>
                `;
            }

            let detailHtml = '';
            
            let headerHtml = `
                <header class="reviewer-header p-3 glass-panel rounded-3 mb-2" style="background: rgba(var(--ds-primary-rgb), 0.05);">
                    <h5 class="fw-bold mb-1">${data.title}</h5>
                    <div class="text-secondary text-sm">${data.department} | Viewing Stage ${activeStage}</div>
                </header>
                ${stageTabs}
            `;

            if (activeStage === 8) {
                detailHtml = `
                    <div class="v-stack gap-4">
                        ${headerHtml}
                        <section class="review-context-section">
                            <h6 class="ds-text-tertiary text-xs fw-bold text-uppercase mb-3">Lessons Learned</h6>
                            <div class="p-3 border rounded-3 bg-light text-sm">${d.lessons_learned || (d.data && d.data.lessons_learned) || 'No lessons learned recorded.'}</div>
                        </section>

                        <section class="review-context-section">
                            <h6 class="ds-text-tertiary text-xs fw-bold text-uppercase mb-3">Preventive Actions</h6>
                            <div class="p-3 border rounded-3 bg-light text-sm">${d.preventive_actions || (d.data && d.data.preventive_actions) || 'No preventive actions recorded.'}</div>
                        </section>

                        <section class="review-context-section">
                            <div class="h-stack gap-4">
                                <div class="kpi-stat">
                                    <div class="text-xs text-muted mb-1">Target Action</div>
                                    <div class="fw-bold text-success">Project Closure & Archiving</div>
                                </div>
                            </div>
                        </section>
                    </div>
                `;
            } else if (activeStage === 2) {
                const s2 = d.data || {};
                const po = s2.process_observation || {};
                const cs = s2.current_state || {};
                const files = cs.media_files || [];
                
                let filesHtml = '';
                if (files.length === 0) {
                    filesHtml = '<div class="text-xs text-muted">No files uploaded.</div>';
                } else {
                    filesHtml = files.map(f => {
                        const isImage = /\.(jpg|jpeg|png|gif)$/i.test(f.url);
                        const isVideo = /\.(mp4|webm|mov|avi|mkv)$/i.test(f.url);
                        let icon = 'file-text';
                        if (isImage) icon = 'image';
                        else if (isVideo) icon = 'video';
                        
                        return `
                            <div class="h-stack justify-content-between p-2 rounded border bg-light mb-1" style="font-size:0.78rem;">
                                <div class="d-flex align-items-center gap-2">
                                    <i data-lucide="${icon}" style="width:14px;height:14px;color:var(--ds-primary);"></i>
                                    <span class="fw-medium">${f.name}</span>
                                </div>
                                <a href="${f.url}" target="_blank" class="ds-btn ds-btn-sm py-1 px-2 text-xs" style="background:var(--ds-primary);color:#fff;border-radius:6px;height:26px;display:inline-flex;align-items:center;">
                                    <i data-lucide="external-link" style="width:11px;height:11px;margin-right:3px;"></i>View
                                </a>
                            </div>
                        `;
                    }).join('');
                }

                let linksHtml = '';
                if (cs.video_link || cs.drive_link) {
                    linksHtml = `
                        <div class="row g-2 mt-2">
                            ${cs.video_link ? `
                                <div class="col-6">
                                    <a href="${cs.video_link}" target="_blank" class="ds-btn ds-btn-outline w-100 py-2 text-xs text-center justify-content-center" style="border-radius:8px;height:34px;display:inline-flex;align-items:center;">
                                        <i data-lucide="video" class="me-1" style="width:13px;height:13px;"></i> Open Video Link
                                    </a>
                                </div>
                            ` : ''}
                            ${cs.drive_link ? `
                                <div class="col-6">
                                    <a href="${cs.drive_link}" target="_blank" class="ds-btn ds-btn-outline w-100 py-2 text-xs text-center justify-content-center" style="border-radius:8px;height:34px;display:inline-flex;align-items:center;">
                                        <i data-lucide="external-link" class="me-1" style="width:13px;height:13px;"></i> Open Google Drive
                                    </a>
                                </div>
                            ` : ''}
                        </div>
                    `;
                }

                detailHtml = `
                    <div class="v-stack gap-4">
                        ${headerHtml}
                        <section class="review-context-section">
                            <h6 class="ds-text-tertiary text-xs fw-bold text-uppercase mb-2">Process Observation &amp; Findings</h6>
                            <div class="p-3 border rounded-3 bg-light text-xs">
                                <div><strong>Observer:</strong> ${po.observer || 'N/A'} | <strong>Area:</strong> ${po.area || 'N/A'}</div>
                                <div class="mt-1"><strong>Finding:</strong> <span class="badge bg-warning text-dark text-xxs" style="font-size:0.6rem;padding:3px 6px;">${po.finding_type || 'N/A'}</span> (${po.finding_severity || 'N/A'})</div>
                                <div class="mt-2 border-top pt-2" style="white-space:pre-line;">${po.finding_desc || 'No details provided.'}</div>
                            </div>
                        </section>

                        <section class="review-context-section">
                            <h6 class="ds-text-tertiary text-xs fw-bold text-uppercase mb-2">Current State Metrics</h6>
                            <div class="p-3 border rounded-3 bg-light text-xs" style="white-space:pre-line;">${cs.metrics || 'No baseline metrics provided.'}</div>
                        </section>

                        <section class="review-context-section">
                            <h6 class="ds-text-tertiary text-xs fw-bold text-uppercase mb-2">Current State Evidence (Files &amp; Links)</h6>
                            <div class="p-3 border rounded-3 bg-white">
                                ${filesHtml}
                                ${linksHtml}
                            </div>
                        </section>
                    </div>
                `;
            } else {
                detailHtml = `
                    <div class="v-stack gap-4">
                        ${headerHtml}
                        <section class="review-context-section">
                            <h6 class="ds-text-tertiary text-xs fw-bold text-uppercase mb-3">Goal & Problem Statement</h6>
                            <div class="p-3 border rounded-3 bg-light text-sm">${d.problem_statement || (d.data && d.data.problem_statement) || 'No problem statement provided.'}</div>
                        </section>

                        <section class="review-context-section">
                            <h6 class="ds-text-tertiary text-xs fw-bold text-uppercase mb-3">Root Cause Analysis</h6>
                            <div class="p-3 border rounded-3 bg-light text-sm">${d.root_cause_summary || (d.data && d.data.root_cause_summary) || 'No root cause summary provided.'}</div>
                        </section>

                        <section class="review-context-section">
                            <h6 class="ds-text-tertiary text-xs fw-bold text-uppercase mb-3">Proposed Solution & ROI</h6>
                            <div class="p-3 border rounded-3 bg-light text-sm mb-3">${d.solution || (d.data && d.data.solution) || 'No solution details provided.'}</div>
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
            }
            document.getElementById('proposalDetailView').innerHTML = detailHtml;

            // Update button label
            const btnApprove = document.getElementById('btn-approve');
            const btnSendCeo = document.getElementById('btn-send-ceo');
            if (btnApprove) {
                if (data.pending_stage === 8) {
                    btnApprove.innerHTML = `<i data-lucide="check-circle" class="me-2 text-sm"></i> Sign Off & Close Directly`;
                    if (btnSendCeo) btnSendCeo.classList.remove('d-none');
                } else {
                    btnApprove.innerHTML = `<i data-lucide="check-circle" class="me-2 text-sm"></i> Approve Transition`;
                    if (btnSendCeo) btnSendCeo.classList.add('d-none');
                }
                if (window.lucide) lucide.createIcons();
            }
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
        const comments = providedComments || document.getElementById('reviewerComments')?.value || '';
        if (!comments && (decision === 'Rejected' || decision === 'Revision')) {
            QCMS.toast("Please provide comments for rejection or revision.", "warning");
            return;
        }

        const audit = this.pendingAudits?.find(a => a.project_id === this.selectedProposalId);
        const pendingStage = audit ? audit.pending_stage : 1;
        const projectTitle = audit ? (audit.title || `Project #${this.selectedProposalId}`) : `Project #${this.selectedProposalId}`;

        QCMS.showDecisionConfirmationDialog({
            decision,
            projectTitle,
            stageNumber: pendingStage,
            comments,
            onConfirm: async () => {
                try {
                    QCMS.setLoading('btn-approve', true);

                    if (decision === 'SendToCEO') {
                        const res = await api.post(`/reviewer/closure/${this.selectedProposalId}/complete`, {
                            send_to_ceo: true,
                            reviewer_notes: comments || "Forwarded to CEO for review.",
                            lessons_learned: comments || "Stage 8 lessons recorded.",
                            preventive_actions: "Stage 8 preventive actions recorded."
                        });
                        QCMS.toast(res.msg || "Project forwarded to CEO for review successfully.", 'success');
                    } else {
                        const result = await api.post(`/reviewer/decision`, {
                            project_id: this.selectedProposalId,
                            decision: decision,
                            comments: comments || "Approved",
                            pending_stage: pendingStage
                        });
                        QCMS.toast(`Project ${decision} successfully.`, 'success');
                    }
                    
                    // Close modal if open
                    const modalEl = document.getElementById('reviewModal');
                    if (modalEl) {
                        const modal = bootstrap.Modal.getInstance(modalEl);
                        if (modal) modal.hide();
                    }

                    // Clear inputs
                    const commEl = document.getElementById('reviewerComments');
                    if (commEl) commEl.value = '';

                    // Reload reviewer queues
                    if (typeof Reviewer !== 'undefined' && Reviewer.loadInitialData) {
                        Reviewer.loadInitialData();
                    }
                } catch (err) {
                    QCMS.toast(err.message || "Failed to submit decision", 'error');
                } finally {
                    QCMS.setLoading('btn-approve', false);
                }
            }
        });
    }
};

// Initialize the reviewer module
document.addEventListener('DOMContentLoaded', () => {
    reviewer.init();
});

