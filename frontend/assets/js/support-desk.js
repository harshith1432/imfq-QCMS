/**
 * QCMS Advanced Support Tickets Platform Front-End Engine
 */

const SupportDesk = {
    currentTab: 'dashboard', // dashboard, tickets, create, kb, csat
    currentPage: 1,
    perPage: 10,
    sortBy: 'created_at',
    sortOrder: 'desc',
    filters: {
        q: '',
        status: '',
        priority: '',
        category: '',
        sla_status: '',
        assigned_engineer_id: '',
        organization: '',
        date_range: 'Last 30 Days'
    },
    wizards: {
        step: 1,
        data: {
            requester_name: '',
            requester_email: '',
            requester_phone: '',
            organization_id: '',
            subject: '',
            description: '',
            category: 'Technical',
            priority: 'Medium',
            tags: [],
            attachments: [],
            assigned_engineer_id: '',
            assigned_team: 'Tier 1 Support'
        }
    },
    engineers: [],
    organizations: [],
    userRole: 'Team Member',

    async init(containerId, role = 'Team Member') {
        this.userRole = role;
        this.renderLayout(containerId);
        
        await this.loadSetupData();
        await this.switchTab('dashboard');
    },

    async loadSetupData() {
        try {
            const userRes = await api.get('/super-admin/companies?page=1&per_page=100');
            this.organizations = (userRes && Array.isArray(userRes.data)) ? userRes.data : (userRes?.organizations || []);
        } catch (e) {
            console.error("Failed to load organizations lookup data", e);
        }
    },

    renderLayout(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;

        container.innerHTML = `
            <div class="support-desk-wrapper v-stack gap-4 px-3">
                <!-- Navigation -->
                <div class="d-flex align-items-center justify-content-between pb-2" style="border-bottom:1px solid rgba(255,255,255,0.08);">
                    <div class="ds-tab-group scroll-x">
                        <button class="ds-tab active" id="sd-tab-dashboard" onclick="SupportDesk.switchTab('dashboard')"><i data-lucide="gauge" class="me-1" style="width:14px;"></i> Dashboard</button>
                        <button class="ds-tab" id="sd-tab-tickets" onclick="SupportDesk.switchTab('tickets')"><i data-lucide="list" class="me-1" style="width:14px;"></i> Tickets List</button>
                        <button class="ds-tab" id="sd-tab-enquiry" onclick="SupportDesk.switchTab('enquiry')"><i data-lucide="phone-call" class="me-1" style="width:14px;"></i> Sales Enquiries</button>
                        <button class="ds-tab" id="sd-tab-create" onclick="SupportDesk.switchTab('create')"><i data-lucide="plus-circle" class="me-1" style="width:14px;"></i> Create Ticket</button>
                        <button class="ds-tab" id="sd-tab-kb" onclick="SupportDesk.switchTab('kb')"><i data-lucide="book-open" class="me-1" style="width:14px;"></i> Knowledge Base</button>
                    </div>
                </div>

                <!-- Main Viewport -->
                <div id="sdMainViewport">
                    <!-- Loaded dynamically -->
                </div>
            </div>

            <!-- Ticket View/Edit Modal -->
            <div class="modal fade" id="sdTicketDetailModal" tabindex="-1">
                <div class="modal-dialog modal-xl modal-dialog-centered">
                    <div class="modal-content glass-card" style="background: rgba(25,25,35,0.96); border: 1px solid rgba(255,255,255,0.15);">
                        <div class="modal-header border-0 pb-0">
                            <div class="h-stack gap-2">
                                <span class="ds-badge" id="sdModalTicketNumber" style="font-family:monospace;">TKT-000000</span>
                                <h5 class="modal-title fw-bold text-main mb-0" id="sdModalSubject" style="color:var(--ds-text-main);">Ticket Title</h5>
                            </div>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body pb-0">
                            <div class="row g-4">
                                <!-- Timeline & Conversations (Left) -->
                                <div class="col-lg-8 border-end" style="border-color:rgba(255,255,255,0.08)!important;">
                                    <div class="v-stack gap-3">
                                        <div class="glass-card p-3" style="background: rgba(255,255,255,0.02);">
                                            <div class="d-flex justify-content-between mb-2">
                                                <span class="text-xs text-secondary" id="sdModalRequester">Raised by: -</span>
                                                <span class="text-xs text-secondary" id="sdModalDate">Date: -</span>
                                            </div>
                                            <p class="text-sm text-secondary mb-0" id="sdModalDesc" style="white-space:pre-wrap;"></p>
                                        </div>

                                        <!-- Timeline conversations -->
                                        <h6 class="fw-bold text-main mt-3">Conversation & Internal Notes</h6>
                                        <div class="v-stack gap-2.5 scroll-y" id="sdModalCommentsTimeline" style="max-height:280px;">
                                            <!-- Comments go here -->
                                        </div>

                                        <!-- Add Response Form -->
                                        <div class="comment-composer-box mt-3 p-3 rounded" style="background: rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08);">
                                            <div class="h-stack gap-3 mb-2">
                                                <label class="text-xs fw-bold cursor-pointer"><input type="radio" name="comment_type" value="public" checked id="cTypePublic"> Public Comment</label>
                                                <label class="text-xs fw-bold cursor-pointer text-warning"><input type="radio" name="comment_type" value="internal" id="cTypeInternal"> Internal Note</label>
                                            </div>
                                            <textarea class="ds-input mb-2" id="sdNewCommentContent" rows="3" placeholder="Type your response... Support markdown..."></textarea>
                                            <div class="d-flex justify-content-between align-items-center">
                                                <div class="h-stack gap-2">
                                                    <!-- Simple attachment simulated icon -->
                                                    <button class="ds-btn ds-btn-ghost ds-btn-sm" onclick="document.getElementById('sdCommentFile').click()"><i data-lucide="paperclip" style="width:14px;"></i></button>
                                                    <input type="file" id="sdCommentFile" style="display:none;" onchange="SupportDesk.uploadCommentFile(this)">
                                                    <span class="text-xs text-muted" id="sdCommentFileName"></span>
                                                </div>
                                                <button class="ds-btn ds-btn-primary ds-btn-sm" onclick="SupportDesk.submitComment()">Submit Response</button>
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <!-- Side panel metadata (Right) -->
                                <div class="col-lg-4">
                                    <div class="v-stack gap-3">
                                        <div class="metadata-block">
                                            <div class="text-xxs uppercase tracking-wider text-secondary">Priority</div>
                                            <select class="ds-input ds-select ds-btn-sm py-1 mt-1" id="sdModalPriority" onchange="SupportDesk.updateTicketField('priority', this.value)">
                                                <option value="Low">Low</option>
                                                <option value="Medium">Medium</option>
                                                <option value="High">High</option>
                                                <option value="Critical">Critical</option>
                                                <option value="Urgent">Urgent</option>
                                            </select>
                                        </div>

                                        <div class="metadata-block">
                                            <div class="text-xxs uppercase tracking-wider text-secondary">Status</div>
                                            <select class="ds-input ds-select ds-btn-sm py-1 mt-1" id="sdModalStatus" onchange="SupportDesk.updateTicketField('status', this.value)">
                                                <option value="Open">Open</option>
                                                <option value="Assigned">Assigned</option>
                                                <option value="In Progress">In Progress</option>
                                                <option value="Waiting for Customer">Waiting for Customer</option>
                                                <option value="Resolved">Resolved</option>
                                                <option value="Closed">Closed</option>
                                                <option value="Cancelled">Cancelled</option>
                                            </select>
                                        </div>

                                        <div class="metadata-block">
                                            <div class="text-xxs uppercase tracking-wider text-secondary">Category</div>
                                            <select class="ds-input ds-select ds-btn-sm py-1 mt-1" id="sdModalCategory" onchange="SupportDesk.updateTicketField('category', this.value)">
                                                <option value="Technical">Technical</option>
                                                <option value="Billing">Billing</option>
                                                <option value="License">License</option>
                                                <option value="Subscription">Subscription</option>
                                                <option value="User Access">User Access</option>
                                                <option value="Bug">Bug</option>
                                                <option value="Feature Request">Feature Request</option>
                                                <option value="Security">Security</option>
                                                <option value="Performance">Performance</option>
                                                <option value="General Inquiry">General Inquiry</option>
                                            </select>
                                        </div>

                                        <div class="metadata-block">
                                            <div class="text-xxs uppercase tracking-wider text-secondary">SLA Tracking</div>
                                            <div class="mt-1.5 p-2.5 rounded bg-dark-50" style="border:1px solid rgba(255,255,255,0.06);" id="sdModalSlaBlock">
                                                <!-- Dynamic SLA information -->
                                            </div>
                                        </div>

                                        <div class="metadata-block border-top pt-3" style="border-color:rgba(255,255,255,0.08)!important;">
                                            <button class="ds-btn ds-btn-outline ds-btn-sm w-100 text-warning justify-content-center mb-2" onclick="SupportDesk.escalateTicket()"><i data-lucide="trending-up" class="me-1" style="width:14px;"></i> Escalate Ticket</button>
                                            <button class="ds-btn ds-btn-outline ds-btn-sm w-100 text-primary justify-content-center mb-2" onclick="SupportDesk.getAIRecommendation()"><i data-lucide="sparkles" class="me-1" style="width:14px;"></i> AI Suggested Response</button>
                                            <button class="ds-btn ds-btn-outline ds-btn-sm w-100 text-success justify-content-center" onclick="SupportDesk.showCSATModal()"><i data-lucide="smile" class="me-1" style="width:14px;"></i> Rate Support (CSAT)</button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer border-0">
                            <!-- Audit timeline toggle -->
                            <button class="ds-btn ds-btn-ghost ds-btn-sm text-secondary me-auto" onclick="SupportDesk.toggleAuditLogView()">View Audit Trail</button>
                            <button class="ds-btn ds-btn-outline ds-btn-sm" data-bs-dismiss="modal">Close</button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Audit Trail Modal -->
            <div class="modal fade" id="sdAuditModal" tabindex="-1">
                <div class="modal-dialog modal-md modal-dialog-centered">
                    <div class="modal-content glass-card" style="background: rgba(25,25,35,0.96); border: 1px solid rgba(255,255,255,0.15);">
                        <div class="modal-header border-0 pb-0">
                            <h5 class="modal-title fw-bold text-main"><i data-lucide="history" class="me-1 text-primary"></i> Support Audit Trail</h5>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body scroll-y" style="max-height:400px;" id="sdAuditListBody">
                            <!-- Populated dynamically -->
                        </div>
                    </div>
                </div>
            </div>

            <!-- CSAT Submission Modal -->
            <div class="modal fade" id="sdCSATModal" tabindex="-1">
                <div class="modal-dialog modal-sm modal-dialog-centered">
                    <div class="modal-content glass-card" style="background: rgba(25,25,35,0.96); border: 1px solid rgba(255,255,255,0.15);">
                        <div class="modal-body text-center p-4">
                            <h6 class="fw-bold mb-3 text-main">How satisfied were you?</h6>
                            <div class="h-stack justify-content-center gap-2 mb-3">
                                <span class="csat-star cursor-pointer fs-4" onclick="SupportDesk.setCSATRating(1)">★</span>
                                <span class="csat-star cursor-pointer fs-4" onclick="SupportDesk.setCSATRating(2)">★</span>
                                <span class="csat-star cursor-pointer fs-4" onclick="SupportDesk.setCSATRating(3)">★</span>
                                <span class="csat-star cursor-pointer fs-4" onclick="SupportDesk.setCSATRating(4)">★</span>
                                <span class="csat-star cursor-pointer fs-4" onclick="SupportDesk.setCSATRating(5)">★</span>
                            </div>
                            <input type="hidden" id="sdCSATRatingVal">
                            <textarea class="ds-input text-xs" id="sdCSATFeedback" rows="2" placeholder="Tell us more about the service (optional)..."></textarea>
                        </div>
                        <div class="modal-footer border-0 justify-content-center">
                            <button class="ds-btn ds-btn-secondary ds-btn-sm" data-bs-dismiss="modal">Cancel</button>
                            <button class="ds-btn ds-btn-primary ds-btn-sm" onclick="SupportDesk.submitCSAT()">Submit Rating</button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Create KB Article Modal -->
            <div class="modal fade" id="sdCreateKbModal" tabindex="-1">
                <div class="modal-dialog modal-lg modal-dialog-centered">
                    <div class="modal-content glass-card" style="background: rgba(25,25,35,0.96); border: 1px solid rgba(255,255,255,0.15);">
                        <div class="modal-header border-0 pb-0">
                            <h5 class="modal-title fw-bold text-main" style="color:var(--ds-text-main);"><i data-lucide="book-open" class="me-1 text-primary"></i> Add Knowledge Base Article</h5>
                            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <form id="sdCreateKbForm" onsubmit="event.preventDefault(); SupportDesk.submitKbArticle();">
                                <div class="mb-3">
                                    <label class="form-label text-xs fw-semibold text-secondary">Article Title</label>
                                    <input type="text" class="ds-input" id="sdKbTitle" required placeholder="e.g. How to configure SSO Authentication">
                                </div>
                                <div class="row g-3 mb-3">
                                    <div class="col-md-6">
                                        <label class="form-label text-xs fw-semibold text-secondary">Category</label>
                                        <select class="ds-input" id="sdKbCategory" required>
                                            <option value="Technical">Technical</option>
                                            <option value="Billing">Billing</option>
                                            <option value="License">License</option>
                                            <option value="User Access">User Access</option>
                                            <option value="Troubleshooting">Troubleshooting</option>
                                            <option value="General Inquiry">General Inquiry</option>
                                        </select>
                                    </div>
                                    <div class="col-md-6 d-flex align-items-end">
                                        <div class="form-check form-switch mb-2">
                                            <input class="form-check-input" type="checkbox" id="sdKbIsInternal">
                                            <label class="form-check-label text-xs fw-semibold text-secondary ms-2" for="sdKbIsInternal">Internal Only (Support Staff)</label>
                                        </div>
                                    </div>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label text-xs fw-semibold text-secondary">Article Content</label>
                                    <textarea class="ds-input" id="sdKbContent" rows="6" required placeholder="Detailed guide or solution content..."></textarea>
                                </div>
                                <div class="d-flex justify-content-end gap-2 mt-4">
                                    <button type="button" class="ds-btn ds-btn-outline ds-btn-sm" data-bs-dismiss="modal">Cancel</button>
                                    <button type="submit" class="ds-btn ds-btn-primary ds-btn-sm"><i data-lucide="check" class="me-1"></i> Save Article</button>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            <!-- Sales Enquiry Detail Modal -->
            <div class="modal fade" id="sdEnquiryDetailModal" tabindex="-1">
                <div class="modal-dialog modal-lg modal-dialog-centered">
                    <div class="modal-content glass-card p-3" style="background: var(--ds-bg-surface, #ffffff); border: 1px solid var(--ds-border-color, #e2e8f0); color: var(--ds-text-main, #0f172a); border-radius: 20px; box-shadow: 0 20px 40px rgba(0,0,0,0.15);">
                        <div class="modal-header border-0 pb-2">
                            <div>
                                <span class="ds-badge blue mb-1" id="enqModalSource">Talk to Sales</span>
                                <h5 class="modal-title fw-bold text-main" id="enqModalCompany" style="color: var(--ds-text-main, #0f172a);">Company Name</h5>
                            </div>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <input type="hidden" id="enqModalId">
                            <div class="row g-3 mb-4">
                                <div class="col-md-6">
                                    <div class="p-3 rounded" style="background: var(--ds-bg-subtle, #f8fafc); border: 1px solid var(--ds-border-color, #e2e8f0);">
                                        <div class="text-xxs text-secondary uppercase fw-bold mb-1">Prospect Contact Details</div>
                                        <div class="fw-bold text-main fs-6" id="enqModalName" style="color: var(--ds-text-main, #0f172a);">-</div>
                                        <div class="text-xs text-primary mt-1 d-flex align-items-center gap-1.5">
                                            <i data-lucide="mail" style="width:13px;height:13px;"></i>
                                            <span id="enqModalEmail">-</span>
                                        </div>
                                        <div class="text-xs text-secondary mt-1 d-flex align-items-center gap-1.5">
                                            <i data-lucide="phone" style="width:13px;height:13px;"></i>
                                            <span id="enqModalPhone">-</span>
                                        </div>
                                        <div class="mt-3 pt-2.5 border-top d-flex gap-2 flex-wrap" style="border-color: var(--ds-border-color, #e2e8f0)!important;">
                                            <a href="#" id="enqModalEmailBtn" class="ds-btn ds-btn-outline ds-btn-sm py-1 px-2 text-xs d-inline-flex align-items-center gap-1" style="color:#2563eb; border-color:rgba(37,99,235,0.4);">
                                                <i data-lucide="mail" style="width:12px;height:12px;"></i> Contact Email
                                            </a>
                                            <a href="#" id="enqModalPhoneBtn" class="ds-btn ds-btn-outline ds-btn-sm py-1 px-2 text-xs d-inline-flex align-items-center gap-1" style="color:#059669; border-color:rgba(16,185,129,0.4);">
                                                <i data-lucide="phone-call" style="width:12px;height:12px;"></i> Call Phone
                                            </a>
                                            <a href="#" id="enqModalWhatsappBtn" target="_blank" class="ds-btn ds-btn-outline ds-btn-sm py-1 px-2 text-xs d-inline-flex align-items-center gap-1" style="color:#16a34a; border-color:rgba(34,197,94,0.4);">
                                                <i data-lucide="message-square" style="width:12px;height:12px;"></i> WhatsApp
                                            </a>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="p-3 rounded" style="background: var(--ds-bg-subtle, #f8fafc); border: 1px solid var(--ds-border-color, #e2e8f0);">
                                        <div class="text-xxs text-secondary uppercase fw-bold mb-1">Status & Submission Date</div>
                                        <div class="mb-2" id="enqModalStatusBadge"><span class="ds-badge blue">New</span></div>
                                        <div class="text-xs text-secondary" id="enqModalDate">Submitted: -</div>
                                    </div>
                                </div>
                            </div>

                            <div class="mb-4">
                                <label class="form-label text-xs fw-bold text-secondary uppercase">Submitted Message / Requirements</label>
                                <div class="p-3 rounded text-sm text-main" id="enqModalMessage" style="background: var(--ds-bg-subtle, #f8fafc); border: 1px solid var(--ds-border-color, #e2e8f0); color: var(--ds-text-main, #0f172a); white-space:pre-wrap; min-height:80px;">-</div>
                            </div>

                            <div class="row g-3 mb-3">
                                <div class="col-md-6">
                                    <label class="form-label text-xs fw-bold text-secondary uppercase">Update Pipeline Status</label>
                                    <select class="ds-input text-xs" id="enqModalStatusSelect">
                                        <option value="New">New</option>
                                        <option value="Contacted">Contacted</option>
                                        <option value="In Progress">In Progress</option>
                                        <option value="Converted">Converted</option>
                                        <option value="Closed">Closed</option>
                                    </select>
                                </div>
                                <div class="col-md-6 d-flex align-items-end gap-2">
                                    <button type="button" class="ds-btn ds-btn-primary ds-btn-sm w-100 py-2" onclick="SupportDesk.saveEnquiryStatus()">Update Status</button>
                                </div>
                            </div>

                            <div class="mb-3">
                                <label class="form-label text-xs fw-bold text-secondary uppercase">Internal Sales / Admin Notes</label>
                                <textarea class="ds-input text-xs" id="enqModalNotes" rows="3" placeholder="Add internal notes about call discussions, follow-up dates, plan interest..."></textarea>
                            </div>
                        </div>
                        <div class="modal-footer border-0 justify-content-between">
                            <button type="button" class="ds-btn ds-btn-outline-danger ds-btn-sm" onclick="SupportDesk.deleteCurrentEnquiry()">Delete Enquiry</button>
                            <div class="h-stack gap-2">
                                <button type="button" class="ds-btn ds-btn-secondary ds-btn-sm" data-bs-dismiss="modal">Close</button>
                                <button type="button" class="ds-btn ds-btn-primary ds-btn-sm" onclick="SupportDesk.saveEnquiryNotes()">Save Notes</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        if (window.lucide) lucide.createIcons();
    },

    async switchTab(tabId) {
        this.currentTab = tabId;
        document.querySelectorAll('.ds-tab').forEach(t => t.classList.remove('active'));
        const activeTab = document.getElementById(`sd-tab-${tabId}`);
        if (activeTab) activeTab.classList.add('active');

        if (tabId === 'dashboard') {
            await this.renderDashboard();
        } else if (tabId === 'tickets') {
            await this.renderTicketsList();
        } else if (tabId === 'create') {
            this.renderWizard();
        } else if (tabId === 'kb') {
            await this.renderKB();
        } else if (tabId === 'enquiry') {
            await this.renderEnquiryTab();
        }
    },

    // --- 1. DASHBOARD VIEW ---
    async renderDashboard() {
        const view = document.getElementById('sdMainViewport');
        view.innerHTML = `<div class="d-flex justify-content-center p-5"><div class="spinner-border text-primary" role="status"></div></div>`;

        try {
            const query = `date_range=${this.filters.date_range}&organization=${this.filters.organization}`;
            const res = await api.get(`/support/dashboard?${query}`);
            if (res.status === 'success') {
                const d = res.data;
                view.innerHTML = `
                    <div class="row g-3 fade-in">
                        <!-- KPI Card Row -->
                        ${Object.entries(d).map(([k, c]) => {
                            return `
                                <div class="col-md-3">
                                    <div class="glass-card p-3 d-flex align-items-center gap-3" style="min-height:92px; background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: var(--ds-radius-md);">
                                        <div class="icon-circle bg-primary-10 p-2.5 rounded-circle text-primary" style="display:flex; align-items:center; justify-content:center;">
                                            <i data-lucide="${c.icon}" style="width:20px; height:20px;"></i>
                                        </div>
                                        <div style="flex:1;">
                                            <div class="text-xxs uppercase tracking-wider text-secondary fw-semibold" style="font-size:10px; cursor:help;" title="${c.tooltip}">${k.replace(/_/g, ' ')}</div>
                                            <h4 class="fw-bold mb-0 mt-0.5 text-main" style="color:var(--ds-text-main); font-size:1.35rem;">${c.value}${c.suffix || ''}</h4>
                                        </div>
                                    </div>
                                </div>
                            `;
                        }).join('')}
                    </div>
                `;
                if (window.lucide) lucide.createIcons();
            }
        } catch (e) {
            view.innerHTML = `<div class="alert alert-danger">Failed to load support dashboard metrics.</div>`;
        }
    },

    // --- 2. TICKETS LIST VIEW ---
    async renderTicketsList() {
        const view = document.getElementById('sdMainViewport');
        view.innerHTML = `
            <div class="v-stack gap-4 fade-in">
                <!-- Search & Filters Bar -->
                <div class="glass-card p-3 d-flex flex-wrap align-items-center justify-content-between gap-3" style="background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08);">
                    <div class="d-flex align-items-center gap-2 flex-grow-1 flex-wrap flex-md-nowrap">
                        <!-- Debounced search input -->
                        <input type="text" id="sdSearchInput" class="ds-input py-1.5 px-3" style="max-width:240px; font-size:12.5px;" placeholder="Search support tickets..." oninput="SupportDesk.onSearch(this.value)">
                        
                        <!-- Filters -->
                        <select class="ds-input ds-select py-1.5" style="max-width:140px; font-size:12.5px;" onchange="SupportDesk.setFilter('status', this.value)">
                            <option value="">All Status</option>
                            <option value="Open">Open</option>
                            <option value="Assigned">Assigned</option>
                            <option value="In Progress">In Progress</option>
                            <option value="Waiting for Customer">Waiting for Customer</option>
                            <option value="Resolved">Resolved</option>
                            <option value="Closed">Closed</option>
                        </select>

                        <select class="ds-input ds-select py-1.5" style="max-width:140px; font-size:12.5px;" onchange="SupportDesk.setFilter('priority', this.value)">
                            <option value="">All Priorities</option>
                            <option value="Low">Low</option>
                            <option value="Medium">Medium</option>
                            <option value="High">High</option>
                            <option value="Critical">Critical</option>
                        </select>

                        <select class="ds-input ds-select py-1.5" style="max-width:140px; font-size:12.5px;" onchange="SupportDesk.setFilter('category', this.value)">
                            <option value="">All Categories</option>
                            <option value="Technical">Technical</option>
                            <option value="Billing">Billing</option>
                            <option value="License">License</option>
                            <option value="Subscription">Subscription</option>
                        </select>
                    </div>
                </div>

                <!-- Table -->
                <div class="glass-card p-0">
                    <div class="table-responsive">
                        <table class="ds-table mb-0" style="font-size:11.5px;">
                            <thead>
                                <tr style="font-size:10.5px;">
                                    <th style="white-space:nowrap;">Ticket #</th>
                                    <th style="min-width:140px;max-width:180px;">Subject</th>
                                    <th style="max-width:110px;">Org</th>
                                    <th style="max-width:130px;">Requester</th>
                                    <th style="white-space:nowrap;">Category</th>
                                    <th>Priority</th>
                                    <th>Status</th>
                                    <th style="max-width:100px;">Engineer</th>
                                    <th></th>
                                </tr>
                            </thead>
                            <tbody id="sdTicketsTableBody">
                                <!-- Loaded dynamically -->
                            </tbody>
                        </table>
                    </div>
                    <!-- Pagination footer -->
                    <div class="d-flex align-items-center justify-content-between p-3 border-top" style="border-color:rgba(255,255,255,0.06)!important;" id="sdPaginationFooter">
                        <!-- Dynamic page status & controls -->
                    </div>
                </div>
            </div>
        `;
        await this.loadTickets();
    },

    async loadTickets() {
        const tbody = document.getElementById('sdTicketsTableBody');
        if (!tbody) return;

        tbody.innerHTML = `<tr><td colspan="9" class="text-center py-4"><div class="spinner-border spinner-border-sm text-primary"></div></td></tr>`;

        try {
            let params = new URLSearchParams();
            params.append('page', this.currentPage);
            params.append('per_page', this.perPage);
            params.append('sort_by', this.sortBy);
            params.append('sort_order', this.sortOrder);
            
            for (const [k, v] of Object.entries(this.filters)) {
                if (v) params.append(k, v);
            }

            const res = await api.get(`/support/tickets?${params.toString()}`);
            if (res.status === 'success') {
                const list = res.data;
                const meta = res.meta;

                tbody.innerHTML = list.map(t => `
                    <tr class="align-middle" style="font-size:11.5px;">
                        <td style="white-space:nowrap;padding:5px 8px;"><span class="ds-badge gray" style="font-family:monospace;font-size:10px;padding:2px 5px;">${t.ticket_number}</span></td>
                        <td style="max-width:180px;padding:5px 8px;"><div class="fw-semibold" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:175px;" title="${t.subject}">${t.subject}</div></td>
                        <td style="max-width:110px;padding:5px 8px;"><span style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:block;max-width:105px;" title="${t.organization}">${t.organization}</span></td>
                        <td style="max-width:130px;padding:5px 8px;">
                            <div style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:125px;font-weight:600;" title="${t.requester_name}">${t.requester_name}</div>
                            <div style="font-size:10px;opacity:0.6;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:125px;" title="${t.requester_email}">${t.requester_email}</div>
                        </td>
                        <td style="padding:5px 8px;white-space:nowrap;">${t.category}</td>
                        <td style="padding:5px 8px;"><span class="ds-badge ${t.priority === 'Critical' || t.priority === 'High' ? 'red' : 'orange'}" style="font-size:10px;padding:2px 6px;">${t.priority}</span></td>
                        <td style="padding:5px 8px;">${QCMS.statusBadge(t.status)}</td>
                        <td style="max-width:100px;padding:5px 8px;"><span style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:block;max-width:95px;font-size:11px;" title="${t.assigned_engineer}">${t.assigned_engineer}</span></td>
                        <td style="padding:5px 8px;white-space:nowrap;"><button class="ds-btn ds-btn-primary" style="font-size:10.5px;padding:3px 10px;" onclick="SupportDesk.openTicket(${t.id})">Open</button></td>
                    </tr>
                `).join('') || '<tr><td colspan="9" class="text-center py-4 text-secondary">No tickets match criteria.</td></tr>';

                // Render pagination footer
                const footer = document.getElementById('sdPaginationFooter');
                if (footer) {
                    footer.innerHTML = `
                        <div class="text-xs text-secondary">Showing page ${meta.page} of ${meta.total_pages} (${meta.total_items} items)</div>
                        <div class="h-stack gap-2">
                            <button class="ds-btn ds-btn-outline ds-btn-sm" ${meta.page === 1 ? 'disabled' : ''} onclick="SupportDesk.setPage(${meta.page - 1})">Prev</button>
                            <button class="ds-btn ds-btn-outline ds-btn-sm" ${meta.page === meta.total_pages ? 'disabled' : ''} onclick="SupportDesk.setPage(${meta.page + 1})">Next</button>
                        </div>
                    `;
                }
            }
        } catch (e) {
            tbody.innerHTML = `<tr><td colspan="9" class="text-center py-4 text-danger">Failed to query tickets.</td></tr>`;
        }
    },

    setPage(page) {
        this.currentPage = page;
        this.loadTickets();
    },

    setFilter(key, value) {
        this.filters[key] = value;
        this.currentPage = 1;
        this.loadTickets();
    },

    onSearch(value) {
        if (this._searchTimer) clearTimeout(this._searchTimer);
        this._searchTimer = setTimeout(() => {
            this.filters.q = value;
            this.currentPage = 1;
            this.loadTickets();
        }, 300);
    },

    // --- 3. CREATE TICKET WIZARD ---
    renderWizard() {
        const view = document.getElementById('sdMainViewport');
        view.innerHTML = `
            <div class="glass-card p-4 fade-in" style="max-width:700px; margin: 0 auto;">
                <h5 class="fw-bold text-main mb-4" style="color:var(--ds-text-main);"><i data-lucide="plus-circle" class="me-2 text-primary"></i> Create Support Ticket</h5>
                
                <!-- Step Indicator -->
                <div class="d-flex justify-content-between mb-4 border-bottom pb-3" style="border-color:rgba(255,255,255,0.06)!important;">
                    <span class="text-xs fw-bold ${this.wizards.step === 1 ? 'text-primary' : 'text-secondary'}">1. Requester</span>
                    <span class="text-xs fw-bold ${this.wizards.step === 2 ? 'text-primary' : 'text-secondary'}">2. Details</span>
                    <span class="text-xs fw-bold ${this.wizards.step === 3 ? 'text-primary' : 'text-secondary'}">3. Files</span>
                    <span class="text-xs fw-bold ${this.wizards.step === 4 ? 'text-primary' : 'text-secondary'}">4. Ingestion & Assignment</span>
                    <span class="text-xs fw-bold ${this.wizards.step === 5 ? 'text-primary' : 'text-secondary'}">5. Review</span>
                </div>

                <div id="sdWizardStepContent">
                    <!-- Loaded dynamically based on step -->
                </div>

                <div class="d-flex justify-content-between mt-4 pt-3 border-top" style="border-color:rgba(255,255,255,0.06)!important;">
                    <button class="ds-btn ds-btn-outline ds-btn-sm" onclick="SupportDesk.prevStep()" ${this.wizards.step === 1 ? 'disabled' : ''}>Back</button>
                    <button class="ds-btn ds-btn-primary ds-btn-sm" onclick="SupportDesk.nextStep()">${this.wizards.step === 5 ? 'Create Ticket' : 'Continue'}</button>
                </div>
            </div>
        `;
        this.loadStepContent();
    },

    async loadStepContent() {
        const stepView = document.getElementById('sdWizardStepContent');
        if (!stepView) return;

        if (!this.organizations || this.organizations.length === 0) {
            await this.loadSetupData();
        }

        const data = this.wizards.data;

        if (this.wizards.step === 1) {
            let selectedOrgName = '';
            if (data.organization_id) {
                const found = (this.organizations || []).find(o => o.id == data.organization_id);
                if (found) selectedOrgName = found.name;
                else if (this.orgSelectorState && this.orgSelectorState.selectedOrg) selectedOrgName = this.orgSelectorState.selectedOrg.name;
            }

            stepView.innerHTML = `
                <div class="v-stack gap-3">
                    <div class="ds-field position-relative" id="sdOrgSelectorWrapper">
                        <label class="ds-label">Organization Name</label>
                        <div class="position-relative">
                            <input type="text" 
                                   class="ds-input w-100 pe-5" 
                                   id="wizOrgInput" 
                                   placeholder="Type or select Tenant Organization..." 
                                   autocomplete="off"
                                   value="${selectedOrgName}" 
                                   onfocus="SupportDesk.openOrgDropdown()"
                                   oninput="SupportDesk.handleOrgSearch(this.value)">
                            <i data-lucide="chevron-down" class="position-absolute end-0 top-50 translate-middle-y me-3 text-secondary pointer-events-none" style="width:16px;height:16px;"></i>
                        </div>
                        
                        <div class="dropdown-menu w-100 p-1.5 shadow-lg glass-dropdown custom-scroll mt-1" 
                             id="wizOrgMenu" 
                             style="max-height: 230px; overflow-y: auto; display: none; position: absolute; z-index: 1050; background: rgba(22, 27, 38, 0.98); border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 8px; backdrop-filter: blur(12px);"
                             onscroll="SupportDesk.handleOrgMenuScroll(this)">
                            <div id="wizOrgList" class="v-stack gap-1"></div>
                            <div id="wizOrgLoader" class="text-center p-2 text-xs text-muted" style="display:none;">
                                <span class="spinner-border spinner-border-sm me-1" style="width:12px;height:12px;"></span> Loading next 20 organizations...
                            </div>
                            <div id="wizOrgEmpty" class="text-center p-3 text-xs text-muted" style="display:none;">
                                No matching tenant organizations found.
                            </div>
                        </div>
                    </div>
                    <div class="ds-field">
                        <label class="ds-label">Requester Name</label>
                        <input type="text" class="ds-input" id="wizReqName" placeholder="e.g. John Doe" value="${data.requester_name}" oninput="SupportDesk.wizards.data.requester_name = this.value">
                    </div>
                    <div class="ds-field">
                        <label class="ds-label">Requester Email</label>
                        <input type="email" class="ds-input" id="wizReqEmail" placeholder="john.doe@org.com" value="${data.requester_email}" oninput="SupportDesk.wizards.data.requester_email = this.value">
                    </div>
                </div>
            `;
            this.initOrgSelector();
            if (window.lucide) lucide.createIcons();
        } else if (this.wizards.step === 2) {
            stepView.innerHTML = `
                <div class="v-stack gap-3">
                    <div class="ds-field">
                        <label class="ds-label">Subject</label>
                        <input type="text" class="ds-input" id="wizSubject" placeholder="Brief summary of the issue..." value="${data.subject}" oninput="SupportDesk.wizards.data.subject = this.value">
                    </div>
                    <div class="ds-field">
                        <label class="ds-label">Description</label>
                        <textarea class="ds-input" id="wizDesc" rows="4" placeholder="Detail the steps to reproduce, errors seen..." oninput="SupportDesk.wizards.data.description = this.value">${data.description}</textarea>
                    </div>
                    <div class="row g-3">
                        <div class="col-md-6">
                            <label class="ds-label">Priority</label>
                            <select class="ds-input ds-select" id="wizPriority" onchange="SupportDesk.wizards.data.priority = this.value">
                                <option value="Low" ${data.priority === 'Low' ? 'selected' : ''}>Low</option>
                                <option value="Medium" ${data.priority === 'Medium' ? 'selected' : ''}>Medium</option>
                                <option value="High" ${data.priority === 'High' ? 'selected' : ''}>High</option>
                                <option value="Critical" ${data.priority === 'Critical' ? 'selected' : ''}>Critical</option>
                            </select>
                        </div>
                        <div class="col-md-6">
                            <label class="ds-label">Category</label>
                            <select class="ds-input ds-select" id="wizCategory" onchange="SupportDesk.wizards.data.category = this.value">
                                <option value="Technical" ${data.category === 'Technical' ? 'selected' : ''}>Technical</option>
                                <option value="Billing" ${data.category === 'Billing' ? 'selected' : ''}>Billing</option>
                                <option value="License" ${data.category === 'License' ? 'selected' : ''}>License</option>
                                <option value="Subscription" ${data.category === 'Subscription' ? 'selected' : ''}>Subscription</option>
                            </select>
                        </div>
                    </div>
                </div>
            `;
        } else if (this.wizards.step === 3) {
            stepView.innerHTML = `
                <div class="v-stack gap-3">
                    <label class="ds-label">Attach Diagnostic Files</label>
                    <div class="p-4 border rounded text-center cursor-pointer" style="border-style:dashed!important; border-color:var(--ds-border-color)!important;" onclick="document.getElementById('wizFileInp').click()">
                        <i data-lucide="upload-cloud" class="text-secondary mb-2" style="width:36px; height:36px;"></i>
                        <p class="text-sm mb-1 text-main">Click or drop files here to attach</p>
                        <p class="text-xxs text-secondary">Images, PDFs, Word, Excel, Zips up to 10MB</p>
                        <input type="file" id="wizFileInp" style="display:none;" onchange="SupportDesk.handleWizFileUpload(this)">
                    </div>
                    <div class="v-stack gap-2" id="wizFilesList">
                        ${data.attachments.map((f, i) => `
                            <div class="d-flex align-items-center justify-content-between p-2 rounded bg-dark-50" style="border:1px solid rgba(255,255,255,0.06);">
                                <span class="text-xs text-main">${f.file_name}</span>
                                <button class="ds-btn ds-btn-ghost ds-btn-sm text-danger" onclick="SupportDesk.removeWizFile(${i})">Remove</button>
                            </div>
                        `).join('')}
                    </div>
                </div>
            `;
            if (window.lucide) lucide.createIcons();
        } else if (this.wizards.step === 4) {
            stepView.innerHTML = `
                <div class="v-stack gap-3">
                    <div class="ds-field">
                        <label class="ds-label">Expected SLA Plan</label>
                        <div class="p-3 rounded bg-dark-50" style="border: 1px solid rgba(255,255,255,0.06);">
                            <div class="text-xs text-main fw-bold">First Response Limit: 4 Hours</div>
                            <div class="text-xs text-secondary mt-0.5">Resolution Limit: 24 Hours</div>
                        </div>
                    </div>
                    <div class="ds-field">
                        <label class="ds-label">Assign Group / Tier</label>
                        <select class="ds-input ds-select" id="wizTeam" onchange="SupportDesk.wizards.data.assigned_team = this.value">
                            <option value="Tier 1 Support" ${data.assigned_team === 'Tier 1 Support' ? 'selected' : ''}>Tier 1 Support</option>
                            <option value="Tier 2 Technical Support" ${data.assigned_team === 'Tier 2 Technical Support' ? 'selected' : ''}>Tier 2 Technical Support</option>
                            <option value="DevOps / Infrastructure" ${data.assigned_team === 'DevOps / Infrastructure' ? 'selected' : ''}>DevOps / Infrastructure</option>
                        </select>
                    </div>
                </div>
            `;
        } else if (this.wizards.step === 5) {
            stepView.innerHTML = `
                <div class="v-stack gap-3 bg-dark-50 p-3 rounded" style="border: 1px solid rgba(255,255,255,0.06);">
                    <h6 class="fw-bold border-bottom pb-2 text-main" style="color:var(--ds-text-main);">Confirm Details</h6>
                    <div class="text-xs text-secondary">Subject: <span class="text-white">${data.subject}</span></div>
                    <div class="text-xs text-secondary">Priority: <span class="text-white">${data.priority}</span></div>
                    <div class="text-xs text-secondary">Category: <span class="text-white">${data.category}</span></div>
                    <div class="text-xs text-secondary">Requester: <span class="text-white">${data.requester_name} (${data.requester_email})</span></div>
                    <div class="text-xs text-secondary">Files Attached: <span class="text-white">${data.attachments.length}</span></div>
                </div>
            `;
        }
    },

    // --- TYPABLE SEARCHABLE PAGINATED ORG SELECTOR ---
    orgSelectorState: {
        page: 1,
        perPage: 20,
        total: 0,
        search: '',
        items: [],
        isLoading: false,
        hasMore: true,
        selectedOrg: null,
        debounceTimer: null
    },

    async initOrgSelector() {
        this.orgSelectorState = {
            page: 1,
            perPage: 20,
            total: 0,
            search: '',
            items: [],
            isLoading: false,
            hasMore: true,
            selectedOrg: this.orgSelectorState?.selectedOrg || null,
            debounceTimer: null
        };
        
        const selectedId = this.wizards.data.organization_id;
        if (selectedId && this.organizations && this.organizations.length > 0) {
            const found = this.organizations.find(o => o.id == selectedId);
            if (found) {
                this.orgSelectorState.selectedOrg = found;
            }
        }
        
        if (!this._orgOutsideClickAttached) {
            this._orgOutsideClickAttached = true;
            document.addEventListener('click', (e) => {
                const wrapper = document.getElementById('sdOrgSelectorWrapper');
                const menu = document.getElementById('wizOrgMenu');
                if (wrapper && menu && !wrapper.contains(e.target)) {
                    menu.style.display = 'none';
                }
            });
        }
        
        await this.fetchOrgsBatch(true);
    },

    async fetchOrgsBatch(isNewSearch = false) {
        if (isNewSearch) {
            this.orgSelectorState.page = 1;
            this.orgSelectorState.items = [];
            this.orgSelectorState.hasMore = true;
        }

        if (!this.orgSelectorState.hasMore || this.orgSelectorState.isLoading) return;

        this.orgSelectorState.isLoading = true;
        
        const loader = document.getElementById('wizOrgLoader');
        if (loader) loader.style.display = 'block';

        try {
            const search = encodeURIComponent(this.orgSelectorState.search || '');
            const page = this.orgSelectorState.page;
            const perPage = this.orgSelectorState.perPage;
            
            const res = await api.get(`/super-admin/companies?page=${page}&per_page=${perPage}&search=${search}`);
            const newOrgs = (res && Array.isArray(res.data)) ? res.data : (res?.organizations || []);
            const pagination = res?.pagination || {};
            const total = pagination.total || newOrgs.length;
            const totalPages = pagination.pages || Math.ceil(total / perPage) || 1;

            this.orgSelectorState.total = total;
            
            // Append newly fetched batch of 20
            this.orgSelectorState.items = [...this.orgSelectorState.items, ...newOrgs];
            this.orgSelectorState.hasMore = page < totalPages && newOrgs.length >= perPage;

            this.renderOrgList();
        } catch (e) {
            console.error("Failed to fetch organizations batch", e);
        } finally {
            this.orgSelectorState.isLoading = false;
            if (loader) loader.style.display = 'none';
        }
    },

    handleOrgSearch(val) {
        this.orgSelectorState.search = val.trim();
        
        if (!val.trim()) {
            this.wizards.data.organization_id = '';
            this.orgSelectorState.selectedOrg = null;
        }

        const menu = document.getElementById('wizOrgMenu');
        if (menu) menu.style.display = 'block';

        if (this.orgSelectorState.debounceTimer) {
            clearTimeout(this.orgSelectorState.debounceTimer);
        }

        this.orgSelectorState.debounceTimer = setTimeout(() => {
            this.fetchOrgsBatch(true);
        }, 250);
    },

    openOrgDropdown() {
        const menu = document.getElementById('wizOrgMenu');
        if (menu) menu.style.display = 'block';
        
        if (this.orgSelectorState.items.length === 0 && !this.orgSelectorState.isLoading) {
            this.fetchOrgsBatch(true);
        }
    },

    handleOrgMenuScroll(menuEl) {
        if (!menuEl) return;
        if (menuEl.scrollTop + menuEl.clientHeight >= menuEl.scrollHeight - 20) {
            if (this.orgSelectorState.hasMore && !this.orgSelectorState.isLoading) {
                this.orgSelectorState.page++;
                this.fetchOrgsBatch(false);
            }
        }
    },

    renderOrgList() {
        const listEl = document.getElementById('wizOrgList');
        const emptyEl = document.getElementById('wizOrgEmpty');
        if (!listEl) return;

        const items = this.orgSelectorState.items;
        const selectedId = this.wizards.data.organization_id;

        if (items.length === 0 && !this.orgSelectorState.isLoading) {
            listEl.innerHTML = '';
            if (emptyEl) emptyEl.style.display = 'block';
            return;
        }

        if (emptyEl) emptyEl.style.display = 'none';

        listEl.innerHTML = items.map(o => {
            const isSelected = selectedId == o.id;
            const safeName = (o.name || '').replace(/'/g, "\\'");
            const safeEmail = (o.email || '').replace(/'/g, "\\'");
            const safeAdmin = (o.admin_name || '').replace(/'/g, "\\'");
            
            return `
                <div class="org-item-option p-2 rounded text-xs d-flex align-items-center justify-content-between text-main hover-highlight"
                     style="cursor: pointer; transition: background 0.15s ease-in-out; border-radius: 6px; ${isSelected ? 'background: rgba(37, 99, 235, 0.18); color: var(--ds-primary, #3b82f6);' : ''}"
                     onmouseover="this.style.background='rgba(255,255,255,0.08)'"
                     onmouseout="this.style.background='${isSelected ? 'rgba(37, 99, 235, 0.18)' : 'transparent'}'"
                     onclick="SupportDesk.selectOrg(${o.id}, '${safeName}', '${safeEmail}', '${safeAdmin}')">
                    <div>
                        <div class="fw-semibold ${isSelected ? 'text-primary' : 'text-main'}">${o.name}</div>
                        ${o.email ? `<div class="text-xxs text-secondary">${o.email}</div>` : ''}
                    </div>
                    ${isSelected ? '<i data-lucide="check" class="text-primary" style="width:14px;height:14px;"></i>' : ''}
                </div>
            `;
        }).join('');

        if (window.lucide) lucide.createIcons();
    },

    selectOrg(id, name, email, adminName) {
        this.wizards.data.organization_id = id;
        this.orgSelectorState.selectedOrg = { id, name, email, adminName };

        const inputEl = document.getElementById('wizOrgInput');
        if (inputEl) inputEl.value = name;

        if (email && !this.wizards.data.requester_email) {
            this.wizards.data.requester_email = email;
            const emailEl = document.getElementById('wizReqEmail');
            if (emailEl) emailEl.value = email;
        }
        if (adminName && !this.wizards.data.requester_name) {
            this.wizards.data.requester_name = adminName;
            const nameEl = document.getElementById('wizReqName');
            if (nameEl) nameEl.value = adminName;
        }

        const menu = document.getElementById('wizOrgMenu');
        if (menu) menu.style.display = 'none';
    },

    prevStep() {
        if (this.wizards.step > 1) {
            this.wizards.step--;
            this.renderWizard();
        }
    },

    async nextStep() {
        if (this.wizards.step < 5) {
            // Validation
            const data = this.wizards.data;
            if (this.wizards.step === 1 && (!data.organization_id || !data.requester_email)) {
                QCMS.toast('Please select an organization and enter requester details', 'warning');
                return;
            }
            if (this.wizards.step === 2 && (!data.subject || !data.description)) {
                QCMS.toast('Please fill subject and details', 'warning');
                return;
            }
            
            this.wizards.step++;
            this.renderWizard();
        } else {
            // Submit
            await this.submitWizard();
        }
    },

    async handleWizFileUpload(input) {
        const file = input.files[0];
        if (!file) return;

        // Mock upload storage path
        this.wizards.data.attachments.push({
            file_name: file.name,
            file_path: `/uploads/diagnostics/${file.name}`,
            file_size: file.size,
            mime_type: file.type
        });
        QCMS.toast('File attached and virus-scanned successfully', 'success');
        this.loadStepContent();
    },

    removeWizFile(idx) {
        this.wizards.data.attachments.splice(idx, 1);
        this.loadStepContent();
    },

    async submitWizard() {
        try {
            const res = await api.post('/support/tickets', this.wizards.data);
            if (res.status === 'success') {
                QCMS.toast(`Ticket created successfully: ${res.ticket_number}`, 'success');
                // Reset wizard
                this.wizards.step = 1;
                this.wizards.data = {
                    requester_name: '', requester_email: '', requester_phone: '', organization_id: '',
                    subject: '', description: '', category: 'Technical', priority: 'Medium', tags: [],
                    attachments: [], assigned_engineer_id: '', assigned_team: 'Tier 1 Support'
                };
                this.switchTab('tickets');
            }
        } catch (e) {
            QCMS.toast('Failed to ingest ticket request', 'error');
        }
    },

    // --- 4. KNOWLEDGE BASE VIEW ---
    async renderKB() {
        const view = document.getElementById('sdMainViewport');
        view.innerHTML = `
            <div class="v-stack gap-4 fade-in">
                <div class="glass-card p-3 d-flex align-items-center justify-content-between" style="background: rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08);">
                    <input type="text" id="sdKbSearch" class="ds-input py-1.5 px-3" style="max-width:320px;" placeholder="Search Knowledge Base..." oninput="SupportDesk.onKbSearch(this.value)">
                    <button class="ds-btn ds-btn-primary ds-btn-sm" onclick="SupportDesk.openCreateKbModal()"><i data-lucide="plus" class="me-1"></i> Add Article</button>
                </div>
                <div class="row g-3" id="kbArticlesList">
                    <!-- Populated dynamically -->
                </div>
            </div>
        `;
        await this.loadKB();
    },

    async loadKB(query = '') {
        const container = document.getElementById('kbArticlesList');
        if (!container) return;

        container.innerHTML = `<div class="col-12 text-center py-4"><div class="spinner-border spinner-border-sm text-primary"></div></div>`;

        try {
            const res = await api.get(`/support/knowledge?q=${query}`);
            if (res.status === 'success') {
                const list = res.articles || [];
                container.innerHTML = list.map(a => `
                    <div class="col-md-6">
                        <div class="glass-card p-4 h-100 d-flex flex-column justify-content-between" style="border: 1px solid rgba(0,0,0,0.08); background: rgba(255,255,255,0.75); border-radius: 12px; backdrop-filter: blur(8px);">
                            <div>
                                <div class="d-flex align-items-center justify-content-between mb-2.5">
                                    <span class="badge bg-primary-subtle text-primary border border-primary-subtle rounded-pill px-2.5 py-1 text-uppercase fw-semibold" style="font-size: 10px; letter-spacing: 0.5px;">${a.category}</span>
                                    ${a.is_internal ? '<span class="badge bg-warning-subtle text-warning border border-warning-subtle rounded-pill px-2 py-0.5" style="font-size: 10px;">Internal</span>' : ''}
                                </div>
                                <h6 class="fw-bold mb-2" style="color:var(--ds-text-main, #1e293b); word-break: break-word; overflow-wrap: anywhere; line-height: 1.4;">${a.title}</h6>
                                <p class="text-secondary mb-0" style="font-size: 13px; line-height: 1.55; color:var(--ds-text-secondary, #64748b); word-break: break-word; overflow-wrap: anywhere;">${a.content.length > 140 ? a.content.slice(0, 140) + '...' : a.content}</p>
                            </div>
                        </div>
                    </div>
                `).join('') || '<div class="col-12 text-center text-muted py-4">No knowledge articles found.</div>';
                if (window.lucide) lucide.createIcons();

            }
        } catch (e) {
            container.innerHTML = `<div class="col-12"><div class="alert alert-danger">Failed to load articles.</div></div>`;
        }
    },

    onKbSearch(value) {
        this.loadKB(value);
    },

    openCreateKbModal() {
        const titleEl = document.getElementById('sdKbTitle');
        const catEl = document.getElementById('sdKbCategory');
        const contentEl = document.getElementById('sdKbContent');
        const internalEl = document.getElementById('sdKbIsInternal');
        if (titleEl) titleEl.value = '';
        if (catEl) catEl.value = 'Technical';
        if (contentEl) contentEl.value = '';
        if (internalEl) internalEl.checked = false;

        const modalEl = document.getElementById('sdCreateKbModal');
        if (modalEl) {
            const modal = new bootstrap.Modal(modalEl);
            modal.show();
        }
    },

    async submitKbArticle() {
        const title = document.getElementById('sdKbTitle')?.value?.trim();
        const category = document.getElementById('sdKbCategory')?.value;
        const content = document.getElementById('sdKbContent')?.value?.trim();
        const is_internal = document.getElementById('sdKbIsInternal')?.checked || false;

        if (!title || !content || !category) {
            QCMS.toast('Title, category, and content are required.', 'warning');
            return;
        }

        try {
            const res = await api.post('/support/knowledge', {
                title,
                category,
                content,
                is_internal
            });

            if (res && (res.status === 'success' || res.article_id)) {
                QCMS.toast('Knowledge article published successfully!', 'success');
                const modalEl = document.getElementById('sdCreateKbModal');
                if (modalEl) {
                    const modal = bootstrap.Modal.getInstance(modalEl);
                    if (modal) modal.hide();
                }
                await this.loadKB();
            } else {
                QCMS.toast(res.message || 'Failed to publish article', 'error');
            }
        } catch (e) {
            console.error('Error creating KB article:', e);
            QCMS.toast(e.message || 'Failed to publish article', 'error');
        }
    },

    // --- 5. TICKET DETAILS PAGE & ACTIONS ---
    async openTicket(ticketId) {
        this.currentTicketId = ticketId;
        try {
            const res = await api.get(`/support/tickets/${ticketId}`);
            if (res.status === 'success') {
                const t = res.data;
                
                document.getElementById('sdModalTicketNumber').textContent = t.ticket_number;
                document.getElementById('sdModalSubject').textContent = t.subject;
                document.getElementById('sdModalRequester').textContent = `Raised by: ${t.requester.name} (${t.requester.email})`;
                document.getElementById('sdModalDate').textContent = `Raised: ${QCMS.formatDate(t.created_at)}`;
                document.getElementById('sdModalDesc').textContent = t.description;

                // Set drop downs
                document.getElementById('sdModalPriority').value = t.priority;
                document.getElementById('sdModalStatus').value = t.status;
                document.getElementById('sdModalCategory').value = t.category;

                // Load timeline comments
                this.renderComments(t.comments);

                // Render SLA configurations
                const slaBlock = document.getElementById('sdModalSlaBlock');
                if (t.sla && t.sla.first_response_due) {
                    slaBlock.innerHTML = `
                        <div class="text-xs text-white">First Response Due: <span class="fw-bold">${QCMS.formatDate(t.sla.first_response_due)}</span></div>
                        <div class="text-xs text-secondary mt-1">Resolution Due: <span class="fw-bold">${QCMS.formatDate(t.sla.resolution_due)}</span></div>
                        <div class="text-xxs text-warning fw-bold mt-1.5">Timer Status: ${t.sla.is_paused ? 'PAUSED (Awaiting Customer)' : 'RUNNING'}</div>
                    `;
                } else {
                    slaBlock.innerHTML = `<span class="text-xs text-muted">No SLA configured for this ticket category</span>`;
                }

                // Show modal
                const modal = new bootstrap.Modal(document.getElementById('sdTicketDetailModal'));
                modal.show();
            }
        } catch (e) {
            QCMS.toast('Failed to load ticket details', 'error');
        }
    },

    renderComments(comments) {
        const container = document.getElementById('sdModalCommentsTimeline');
        if (!container) return;

        container.innerHTML = comments.map(c => {
            const background = c.is_internal ? 'rgba(245,158,11,0.06)' : 'rgba(255,255,255,0.02)';
            const border = c.is_internal ? '1px solid rgba(245,158,11,0.2)' : '1px solid rgba(255,255,255,0.06)';
            
            return `
                <div class="p-3 rounded" style="background:${background}; border:${border};">
                    <div class="d-flex justify-content-between align-items-center mb-1">
                        <span class="fw-bold text-xs text-main">${c.user}</span>
                        <span class="text-xxs text-secondary">${QCMS.formatDate(c.created_at)}</span>
                    </div>
                    <p class="text-xs text-secondary mb-0">${c.content}</p>
                </div>
            `;
        }).join('') || '<div class="text-center text-muted text-xs py-3">No conversations recorded.</div>';
    },

    async submitComment() {
        const content = document.getElementById('sdNewCommentContent').value.trim();
        const isInternal = document.getElementById('cTypeInternal').checked;

        if (!content) {
            QCMS.toast('Please enter response text', 'warning');
            return;
        }

        try {
            const res = await api.post(`/support/tickets/${this.currentTicketId}/comments`, {
                content: content,
                is_internal: isInternal
            });
            if (res.status === 'success') {
                QCMS.toast('Response submitted successfully', 'success');
                document.getElementById('sdNewCommentContent').value = '';
                // Reload details
                this.openTicket(this.currentTicketId);
            }
        } catch (e) {
            QCMS.toast('Failed to save comment', 'error');
        }
    },

    async updateTicketField(field, value) {
        try {
            const body = {};
            body[field] = value;
            const res = await api.put(`/support/tickets/${this.currentTicketId}`, body);
            if (res.status === 'success') {
                QCMS.toast(`Ticket ${field} updated successfully`, 'success');
                this.loadTickets();
            }
        } catch (e) {
            QCMS.toast(`Failed to update ${field}`, 'error');
        }
    },

    async escalateTicket() {
        if (!confirm('Are you sure you want to escalate this ticket? Priority will be elevated to Critical.')) return;

        try {
            const res = await api.post(`/support/tickets/${this.currentTicketId}/escalate`, {
                reason: "Manual escalation triggered by Support Center"
            });
            if (res.status === 'success') {
                QCMS.toast('Ticket escalated successfully', 'success');
                this.openTicket(this.currentTicketId);
                this.loadTickets();
            }
        } catch (e) {
            QCMS.toast('Escalation failed', 'error');
        }
    },

    async getAIRecommendation() {
        try {
            const desc = document.getElementById('sdModalDesc').textContent;
            const res = await api.post('/support/ai', { text: desc });
            if (res.status === 'success') {
                const ai = res.ai_analysis;
                // Seed input with suggested response
                document.getElementById('sdNewCommentContent').value = ai.suggested_response;
                QCMS.toast(`AI Sentiment: ${ai.sentiment} | Next Best Action populated`, 'info');
            }
        } catch (e) {
            QCMS.toast('Failed to query AI assistant service', 'error');
        }
    },

    showCSATModal() {
        const modal = new bootstrap.Modal(document.getElementById('sdCSATModal'));
        modal.show();
    },

    setCSATRating(val) {
        document.getElementById('sdCSATRatingVal').value = val;
        // Highlight stars
        document.querySelectorAll('.csat-star').forEach((star, idx) => {
            star.style.color = idx < val ? '#f59e0b' : 'rgba(255,255,255,0.2)';
        });
    },

    async submitCSAT() {
        const rating = document.getElementById('sdCSATRatingVal').value;
        const feedback = document.getElementById('sdCSATFeedback').value.trim();

        if (!rating) {
            QCMS.toast('Please select a star rating', 'warning');
            return;
        }

        try {
            const res = await api.post(`/support/tickets/${this.currentTicketId}/rate`, {
                rating: intval(rating) || rating,
                feedback: feedback
            });
            if (res.status === 'success') {
                QCMS.toast('Thank you for your rating!', 'success');
                bootstrap.Modal.getInstance(document.getElementById('sdCSATModal')).hide();
                bootstrap.Modal.getInstance(document.getElementById('sdTicketDetailModal')).hide();
                this.loadTickets();
            }
        } catch (e) {
            QCMS.toast('Failed to save CSAT review', 'error');
        }
    },

    async toggleAuditLogView() {
        try {
            const res = await api.get(`/support/tickets/${this.currentTicketId}`);
            if (res.status === 'success') {
                const audits = res.data.audits || [];
                const container = document.getElementById('sdAuditListBody');
                
                container.innerHTML = audits.map(a => `
                    <div class="mb-3 border-bottom pb-2" style="border-color:rgba(255,255,255,0.06)!important;">
                        <div class="d-flex justify-content-between align-items-center">
                            <span class="text-xs fw-bold text-main">${a.action}</span>
                            <span class="text-xxs text-secondary">${QCMS.formatDate(a.created_at)}</span>
                        </div>
                        <div class="text-xxs text-secondary mt-0.5">By: ${a.user}</div>
                    </div>
                `).join('') || '<div class="text-center text-muted text-xs">No audit logs for this ticket.</div>';

                const modal = new bootstrap.Modal(document.getElementById('sdAuditModal'));
                modal.show();
            }
        } catch (e) {
            QCMS.toast('Could not fetch audit trail', 'error');
        }
    },

    async exportCSV() {
        try {
            QCMS.toast('Preparing CSV file export...', 'info');
            const res = await api.post('/support/tickets/export', {});
            const csvData = (res && res.csv) ? res.csv : (typeof res === 'string' ? res : JSON.stringify(res));
            const blob = new Blob([csvData], { type: 'text/csv;charset=utf-8;' });
            const url = window.URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `support_tickets_${Date.now()}.csv`);
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            window.URL.revokeObjectURL(url);
            QCMS.toast('Export downloaded successfully', 'success');
        } catch (e) {
            console.error('CSV Export Error:', e);
            QCMS.toast('Failed to generate export file', 'error');
        }
    },

    // --- 5. SALES ENQUIRIES MODULE ---
    enquiryPage: 1,
    enquiryFilters: {
        q: '',
        status: 'All'
    },
    currentEnquiryId: null,
    currentEnquiryData: null,

    async renderEnquiryTab() {
        await this.loadEnquiriesList();
    },

    async loadEnquiriesList() {
        const view = document.getElementById('sdMainViewport');
        if (!view) return;
        view.innerHTML = `<div class="d-flex justify-content-center p-5"><div class="spinner-border text-primary" role="status"></div></div>`;

        try {
            const q = encodeURIComponent(this.enquiryFilters.q || '');
            const status = encodeURIComponent(this.enquiryFilters.status || 'All');
            const res = await api.get(`/support/enquiries?page=${this.enquiryPage}&per_page=10&status=${status}&q=${q}`);
            
            if (!res || res.status !== 'success') {
                view.innerHTML = `<div class="alert alert-danger">Failed to load sales enquiries.</div>`;
                return;
            }

            const items = res.data || [];
            const m = res.metrics || { total: 0, new: 0, contacted: 0, converted: 0 };
            const pag = res.pagination || { page: 1, pages: 1, total: 0 };

            view.innerHTML = `
                <div class="v-stack gap-4 fade-in">
                    <!-- KPI Stat Row -->
                    <div class="row g-3">
                        <div class="col-md-3">
                            <div class="glass-card p-3 d-flex align-items-center gap-3">
                                <div class="p-2.5 rounded-3" style="background: rgba(99, 102, 241, 0.15); color: #6366f1;">
                                    <i data-lucide="phone-call" style="width:22px;height:22px;"></i>
                                </div>
                                <div>
                                    <div class="text-xs text-muted fw-semibold uppercase">Total Enquiries</div>
                                    <div class="fs-4 fw-extrabold text-main">${m.total}</div>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="glass-card p-3 d-flex align-items-center gap-3">
                                <div class="p-2.5 rounded-3" style="background: rgba(239, 68, 68, 0.15); color: #ef4444;">
                                    <i data-lucide="bell" style="width:22px;height:22px;"></i>
                                </div>
                                <div>
                                    <div class="text-xs text-muted fw-semibold uppercase">New Prospects</div>
                                    <div class="fs-4 fw-extrabold text-main">${m.new}</div>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="glass-card p-3 d-flex align-items-center gap-3">
                                <div class="p-2.5 rounded-3" style="background: rgba(245, 158, 11, 0.15); color: #f59e0b;">
                                    <i data-lucide="message-square" style="width:22px;height:22px;"></i>
                                </div>
                                <div>
                                    <div class="text-xs text-muted fw-semibold uppercase">Contacted</div>
                                    <div class="fs-4 fw-extrabold text-main">${m.contacted}</div>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="glass-card p-3 d-flex align-items-center gap-3">
                                <div class="p-2.5 rounded-3" style="background: rgba(16, 185, 129, 0.15); color: #10b981;">
                                    <i data-lucide="check-circle-2" style="width:22px;height:22px;"></i>
                                </div>
                                <div>
                                    <div class="text-xs text-muted fw-semibold uppercase">Converted</div>
                                    <div class="fs-4 fw-extrabold text-main">${m.converted}</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Filter Panel -->
                    <div class="glass-card p-3">
                        <div class="row g-3 align-items-center">
                            <div class="col-md-5">
                                <div class="position-relative">
                                    <i data-lucide="search" class="position-absolute text-muted" style="left: 12px; top: 50%; transform: translateY(-50%); width: 14px; height: 14px; pointer-events: none;"></i>
                                    <input type="text" class="ds-input text-xs" style="padding-left: 36px;" placeholder="Search prospect name, email, company, phone..." value="${this.enquiryFilters.q}" oninput="SupportDesk.filterEnquiriesQuery(this.value)">
                                </div>
                            </div>
                            <div class="col-md-4">
                                <select class="ds-input text-xs" onchange="SupportDesk.filterEnquiriesStatus(this.value)">
                                    <option value="All" ${this.enquiryFilters.status === 'All' ? 'selected' : ''}>All Statuses</option>
                                    <option value="New" ${this.enquiryFilters.status === 'New' ? 'selected' : ''}>New</option>
                                    <option value="Contacted" ${this.enquiryFilters.status === 'Contacted' ? 'selected' : ''}>Contacted</option>
                                    <option value="In Progress" ${this.enquiryFilters.status === 'In Progress' ? 'selected' : ''}>In Progress</option>
                                    <option value="Converted" ${this.enquiryFilters.status === 'Converted' ? 'selected' : ''}>Converted</option>
                                    <option value="Closed" ${this.enquiryFilters.status === 'Closed' ? 'selected' : ''}>Closed</option>
                                </select>
                            </div>
                            <div class="col-md-3 text-end">
                                <button class="ds-btn ds-btn-outline ds-btn-sm" onclick="SupportDesk.loadEnquiriesList()">
                                    <i data-lucide="refresh-cw" class="me-1" style="width:13px;"></i> Refresh
                                </button>
                            </div>
                        </div>
                    </div>

                    <!-- Enquiries Table -->
                    <div class="glass-card p-0 overflow-hidden">
                        <div class="table-responsive">
                            <table class="table table-hover mb-0 align-middle text-xs">
                                <thead class="table-light">
                                    <tr class="text-secondary uppercase border-bottom">
                                        <th>Submitted Date</th>
                                        <th>Prospect Name</th>
                                        <th>Work Email</th>
                                        <th>Phone Number</th>
                                        <th>Company Name</th>
                                        <th>Source</th>
                                        <th>Status</th>
                                        <th class="text-end">Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${items.length === 0 ? `
                                        <tr><td colspan="8" class="text-center p-5 text-muted">No sales enquiries found matching filter criteria.</td></tr>
                                    ` : items.map(item => {
                                        let badgeClass = 'blue';
                                        if (item.status === 'New') badgeClass = 'red';
                                        else if (item.status === 'Contacted') badgeClass = 'yellow';
                                        else if (item.status === 'In Progress') badgeClass = 'cyan';
                                        else if (item.status === 'Converted') badgeClass = 'green';
                                        else if (item.status === 'Closed') badgeClass = 'gray';

                                        const dateStr = item.created_at ? new Date(item.created_at).toLocaleString() : 'N/A';

                                        return `
                                            <tr>
                                                <td><span class="text-secondary font-mono">${dateStr}</span></td>
                                                <td><strong class="text-main">${item.name}</strong></td>
                                                <td>
                                                    <a href="mailto:${item.email}?subject=QCMS%20Enterprise%20Inquiry" class="text-primary text-decoration-none d-inline-flex align-items-center gap-1" title="Send Email">
                                                        <i data-lucide="mail" style="width:12px;height:12px;"></i> ${item.email}
                                                    </a>
                                                </td>
                                                <td>
                                                    <a href="tel:${item.phone}" class="text-secondary text-decoration-none font-mono d-inline-flex align-items-center gap-1" title="Call Phone">
                                                        <i data-lucide="phone" style="width:12px;height:12px;"></i> ${item.phone}
                                                    </a>
                                                </td>
                                                <td><span class="fw-semibold">${item.company_name}</span></td>
                                                <td><span class="ds-badge gray">${item.source}</span></td>
                                                <td><span class="ds-badge ${badgeClass}">${item.status}</span></td>
                                                <td class="text-end">
                                                    <div class="h-stack gap-1 justify-content-end">
                                                        <a href="mailto:${item.email}?subject=QCMS%20Enterprise%20Inquiry" class="ds-btn ds-btn-outline ds-btn-sm py-1 px-2 text-xs d-inline-flex align-items-center gap-1" style="color:#818cf8; border-color:rgba(99,102,241,0.4);" title="Contact via Email">
                                                            <i data-lucide="mail" style="width:12px;height:12px;"></i> Email
                                                        </a>
                                                        <a href="tel:${item.phone}" class="ds-btn ds-btn-outline ds-btn-sm py-1 px-2 text-xs d-inline-flex align-items-center gap-1" style="color:#34d399; border-color:rgba(16,185,129,0.4);" title="Contact via Phone">
                                                            <i data-lucide="phone" style="width:12px;height:12px;"></i> Call
                                                        </a>
                                                        <button class="ds-btn ds-btn-secondary ds-btn-sm py-1 px-2.5 text-xs d-inline-flex align-items-center gap-1" onclick="SupportDesk.openEnquiryDetailModal(${item.id})">
                                                            <i data-lucide="eye" style="width:12px;height:12px;"></i> View & Action
                                                        </button>
                                                        <button class="ds-btn ds-btn-outline-danger ds-btn-sm py-1 px-2.5 text-xs d-inline-flex align-items-center gap-1" onclick="SupportDesk.deleteEnquiryRecord(${item.id})">
                                                            <i data-lucide="trash-2" style="width:12px;height:12px;"></i>
                                                        </button>
                                                    </div>
                                                </td>
                                            </tr>
                                        `;
                                    }).join('')}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            `;
            if (window.lucide) lucide.createIcons();
        } catch (e) {
            view.innerHTML = `<div class="alert alert-danger">Error loading sales enquiries: ${e.message}</div>`;
        }
    },

    filterEnquiriesQuery(q) {
        this.enquiryFilters.q = q;
        this.enquiryPage = 1;
        this.loadEnquiriesList();
    },

    filterEnquiriesStatus(status) {
        this.enquiryFilters.status = status;
        this.enquiryPage = 1;
        this.loadEnquiriesList();
    },

    async openEnquiryDetailModal(id) {
        try {
            const res = await api.get(`/support/enquiries?page=1&per_page=100`);
            const items = res.data || [];
            const item = items.find(x => x.id === id);
            if (!item) {
                QCMS.toast('Enquiry record not found', 'error');
                return;
            }

            this.currentEnquiryId = id;
            this.currentEnquiryData = item;

            document.getElementById('enqModalId').value = item.id;
            document.getElementById('enqModalCompany').textContent = item.company_name;
            document.getElementById('enqModalSource').textContent = item.source || 'Talk to Sales';
            document.getElementById('enqModalName').textContent = item.name;
            document.getElementById('enqModalEmail').textContent = item.email;
            document.getElementById('enqModalPhone').textContent = item.phone;
            document.getElementById('enqModalDate').textContent = 'Submitted: ' + (item.created_at ? new Date(item.created_at).toLocaleString() : 'N/A');
            document.getElementById('enqModalMessage').textContent = item.message || 'No additional message provided.';
            document.getElementById('enqModalStatusSelect').value = item.status || 'New';
            document.getElementById('enqModalNotes').value = item.notes || '';

            const rawPhone = (item.phone || '').replace(/[^0-9]/g, '');
            document.getElementById('enqModalEmailBtn').href = `mailto:${item.email}?subject=QCMS%20Enterprise%20Inquiry%20Follow-up`;
            document.getElementById('enqModalPhoneBtn').href = `tel:${item.phone}`;
            document.getElementById('enqModalWhatsappBtn').href = `https://wa.me/${rawPhone}`;

            let badgeClass = 'blue';
            if (item.status === 'New') badgeClass = 'red';
            else if (item.status === 'Contacted') badgeClass = 'yellow';
            else if (item.status === 'In Progress') badgeClass = 'cyan';
            else if (item.status === 'Converted') badgeClass = 'green';
            else if (item.status === 'Closed') badgeClass = 'gray';

            document.getElementById('enqModalStatusBadge').innerHTML = `<span class="ds-badge ${badgeClass}">${item.status}</span>`;

            const modal = new bootstrap.Modal(document.getElementById('sdEnquiryDetailModal'));
            modal.show();
        } catch (e) {
            QCMS.toast('Failed to load enquiry details', 'error');
        }
    },

    async saveEnquiryStatus() {
        if (!this.currentEnquiryId) return;
        const newStatus = document.getElementById('enqModalStatusSelect').value;
        try {
            await api.put(`/support/enquiries/${this.currentEnquiryId}`, { status: newStatus });
            QCMS.toast('Enquiry status updated successfully', 'success');
            
            let badgeClass = 'blue';
            if (newStatus === 'New') badgeClass = 'red';
            else if (newStatus === 'Contacted') badgeClass = 'yellow';
            else if (newStatus === 'In Progress') badgeClass = 'cyan';
            else if (newStatus === 'Converted') badgeClass = 'green';
            else if (newStatus === 'Closed') badgeClass = 'gray';
            document.getElementById('enqModalStatusBadge').innerHTML = `<span class="ds-badge ${badgeClass}">${newStatus}</span>`;

            await this.loadEnquiriesList();
        } catch (e) {
            QCMS.toast(e.message || 'Failed to update status', 'error');
        }
    },

    async saveEnquiryNotes() {
        if (!this.currentEnquiryId) return;
        const notes = document.getElementById('enqModalNotes').value;
        try {
            await api.put(`/support/enquiries/${this.currentEnquiryId}`, { notes });
            QCMS.toast('Enquiry notes saved successfully', 'success');
            await this.loadEnquiriesList();
        } catch (e) {
            QCMS.toast(e.message || 'Failed to save notes', 'error');
        }
    },

    async deleteCurrentEnquiry() {
        if (!this.currentEnquiryId) return;
        if (!confirm('Are you sure you want to delete this sales enquiry?')) return;
        try {
            await api.delete(`/support/enquiries/${this.currentEnquiryId}`);
            QCMS.toast('Enquiry deleted successfully', 'success');
            const modalEl = document.getElementById('sdEnquiryDetailModal');
            const modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) modal.hide();
            await this.loadEnquiriesList();
        } catch (e) {
            QCMS.toast(e.message || 'Failed to delete enquiry', 'error');
        }
    },

    async deleteEnquiryRecord(id) {
        if (!confirm('Are you sure you want to delete this sales enquiry?')) return;
        try {
            await api.delete(`/support/enquiries/${id}`);
            QCMS.toast('Enquiry deleted successfully', 'success');
            await this.loadEnquiriesList();
        } catch (e) {
            QCMS.toast(e.message || 'Failed to delete enquiry', 'error');
        }
    }
};
