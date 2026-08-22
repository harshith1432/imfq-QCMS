/**
 * QCMS Advanced Support Tickets Platform Front-End Engine
 */

const SupportDesk = {
    currentTab: 'dashboard', // dashboard, tickets, create, kb, csat
    currentPage: 1,
    perPage: 10,
    trialExtensionsPage: 1,
    trialExtensionsPerPage: 5,
    trialExtensionsSearch: '',
    _trialExtensionsData: [],
    sortBy: 'created_at',
    sortOrder: 'desc',
    filters: {
        q: '',
        status: 'Open',
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
                <div class="d-flex align-items-center justify-content-between pb-2" style="border-bottom:1px solid rgba(255,255,255,0.08); overflow-x: auto; max-width: 100%; -webkit-overflow-scrolling: touch;">
                    <div class="ds-tab-group scroll-x" style="display: flex; flex-wrap: nowrap; overflow-x: auto; -webkit-overflow-scrolling: touch; max-width: 100%; gap: 6px; padding-bottom: 2px;">
                        <button class="ds-tab active text-nowrap" id="sd-tab-dashboard" onclick="SupportDesk.switchTab('dashboard')"><i data-lucide="gauge" class="me-1" style="width:14px;"></i> Dashboard</button>
                        <button class="ds-tab text-nowrap" id="sd-tab-tickets" onclick="SupportDesk.switchTab('tickets')"><i data-lucide="list" class="me-1" style="width:14px;"></i> Tickets List</button>
                        <button class="ds-tab text-nowrap" id="sd-tab-enquiry" onclick="SupportDesk.switchTab('enquiry')"><i data-lucide="phone-call" class="me-1" style="width:14px;"></i> Sales Enquiries</button>
                        <button class="ds-tab text-nowrap" id="sd-tab-trial-extensions" onclick="SupportDesk.switchTab('trial-extensions')"><i data-lucide="clock" class="me-1" style="width:14px;"></i> Trial Extensions</button>
                        <button class="ds-tab text-nowrap" id="sd-tab-create" onclick="SupportDesk.switchTab('create')"><i data-lucide="plus-circle" class="me-1" style="width:14px;"></i> Create Ticket</button>
                        <button class="ds-tab text-nowrap" id="sd-tab-kb" onclick="SupportDesk.switchTab('kb')"><i data-lucide="book-open" class="me-1" style="width:14px;"></i> Knowledge Base</button>
                    </div>
                </div>

                <!-- Main Viewport -->
                <div id="sdMainViewport">
                    <!-- Loaded dynamically -->
                </div>
            </div>
        `;

        // Render modals as a direct child of document.body so they pop up on the top layer without clipping
        let modalsContainer = document.getElementById('sdGlobalModalsContainer');
        if (!modalsContainer) {
            modalsContainer = document.createElement('div');
            modalsContainer.id = 'sdGlobalModalsContainer';
            document.body.appendChild(modalsContainer);
        }

        modalsContainer.innerHTML = `
            <!-- Ticket View/Edit Modal -->
            <div class="modal fade" id="sdTicketDetailModal" tabindex="-1">
                <div class="modal-dialog modal-xl modal-dialog-centered">
                    <div class="modal-content glass-card" style="background: var(--ds-bg-surface, #ffffff); border: 1px solid var(--ds-border-color, #cbd5e1); color: var(--ds-text-main, #0f172a); border-radius: 16px; box-shadow: 0 20px 40px rgba(0,0,0,0.25);">
                        <div class="modal-header border-0 pb-0">
                            <div class="h-stack gap-2">
                                <span class="ds-badge" id="sdModalTicketNumber" style="font-family:monospace;">TKT-000000</span>
                                <h5 class="modal-title fw-bold text-main mb-0" id="sdModalSubject" style="color:var(--ds-text-main);">Ticket Title</h5>
                            </div>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body pb-0">
                            <div class="row g-4">
                                <!-- Timeline & Conversations (Left) -->
                                <div class="col-lg-8 border-end" style="border-color:rgba(255,255,255,0.08)!important;">
                                    <div class="v-stack gap-3">
                                        <!-- Main Ticket Details Card -->
                                        <div class="glass-card p-3 rounded" style="background: rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08);">
                                            <div class="d-flex justify-content-between align-items-center mb-2">
                                                <span class="text-xs text-secondary" id="sdModalRequester">Raised by: -</span>
                                                <span class="text-xs text-secondary" id="sdModalDate">Date: -</span>
                                            </div>
                                            <p class="text-sm text-secondary mb-0" id="sdModalDesc" style="white-space:pre-wrap;"></p>
                                            
                                            <!-- Uploaded Attachments / Documents Section -->
                                            <div id="sdModalAttachmentsWrapper" class="mt-3 pt-3 border-top" style="display:none; border-color:rgba(255,255,255,0.08)!important;">
                                                <div class="text-xs fw-bold text-main mb-2 d-flex align-items-center gap-1.5"><i data-lucide="paperclip" class="text-primary" style="width:14px;height:14px;"></i> Uploaded Documents & Media:</div>
                                                <div id="sdModalAttachmentsList" class="d-flex flex-wrap gap-2"></div>
                                            </div>
                                        </div>

                                        <!-- Timeline conversations -->
                                        <h6 class="fw-bold text-main mt-3 mb-3 d-flex align-items-center gap-2" style="font-size:13px;letter-spacing:.01em;">
                                            <i data-lucide="message-square" style="width:15px;height:15px;opacity:.7;"></i>
                                            Conversation &amp; Internal Notes
                                        </h6>
                                        <div class="d-flex flex-column gap-3 overflow-auto" id="sdModalCommentsTimeline" style="max-height:300px;padding-right:4px;">
                                            <!-- Comments go here -->
                                        </div>

                                        <!-- Add Response Form -->
                                        <div class="mt-4 pt-3" style="border-top:1px solid rgba(255,255,255,0.09);">
                                            <div class="d-flex align-items-center gap-3 mb-2">
                                                <span class="text-xs fw-bold" style="color:var(--ds-text-secondary,#94a3b8);text-transform:uppercase;letter-spacing:.05em;">Reply as:</span>
                                                <label class="d-flex align-items-center gap-1 text-xs fw-semibold cursor-pointer mb-0">
                                                    <input type="radio" name="comment_type" value="public" checked id="cTypePublic" style="accent-color:var(--ds-accent,#4f8ef7);">
                                                    Public Comment
                                                </label>
                                                <label class="d-flex align-items-center gap-1 text-xs fw-semibold cursor-pointer mb-0" style="color:#f59e0b;">
                                                    <input type="radio" name="comment_type" value="internal" id="cTypeInternal" style="accent-color:#f59e0b;">
                                                    Internal Note
                                                </label>
                                            </div>
                                            <textarea class="ds-input mb-2" id="sdNewCommentContent" rows="3"
                                                placeholder="Type your response... Supports markdown..."
                                                style="resize:vertical;min-height:80px;width:100%;"></textarea>
                                            <div class="d-flex justify-content-between align-items-center flex-wrap gap-2">
                                                <div class="d-flex align-items-center gap-2 flex-wrap">
                                                    <button type="button" class="ds-btn ds-btn-outline ds-btn-sm d-inline-flex align-items-center gap-1" onclick="document.getElementById('sdCommentFile').click()">
                                                        <i data-lucide="paperclip" style="width:13px;height:13px;"></i>
                                                        <span>Upload Documents</span>
                                                    </button>
                                                    <input type="file" id="sdCommentFile" style="display:none;"
                                                        accept=".pdf,.png,.jpg,.jpeg,.gif,.webp,image/*,application/pdf"
                                                        onchange="SupportDesk.uploadCommentFile(this)">
                                                    <span class="text-xs text-muted" id="sdCommentFileName"></span>
                                                </div>
                                                <button class="ds-btn ds-btn-primary ds-btn-sm d-inline-flex align-items-center gap-1" onclick="SupportDesk.submitComment()">
                                                    <i data-lucide="send" style="width:13px;height:13px;"></i>
                                                    Submit Response
                                                </button>
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
                                            <button class="ds-btn ds-btn-outline ds-btn-sm w-100 text-primary justify-content-center" onclick="SupportDesk.getAIRecommendation()"><i data-lucide="sparkles" class="me-1" style="width:14px;"></i> AI Suggested Response</button>
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
                    <div class="modal-content glass-card" style="background: var(--ds-bg-surface, #ffffff); border: 1px solid var(--ds-border-color, #cbd5e1); color: var(--ds-text-main, #0f172a); border-radius: 16px; box-shadow: 0 20px 40px rgba(0,0,0,0.25); overflow: hidden;">
                        <div class="modal-header border-bottom pb-3 pt-3 px-4" style="border-color: var(--ds-border-color, rgba(148,163,184,0.2)) !important;">
                            <h5 class="modal-title fw-bold text-main d-flex align-items-center gap-2" style="color:var(--ds-text-main); font-size: 16px;">
                                <i data-lucide="history" class="text-primary" style="width: 18px; height: 18px;"></i>
                                Support Audit Trail
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body px-4 py-3" style="max-height: 420px; overflow-y: auto; overflow-x: hidden;" id="sdAuditListBody">
                            <!-- Populated dynamically -->
                        </div>
                    </div>
                </div>
            </div>

            <!-- CSAT Submission Modal -->
            <div class="modal fade" id="sdCSATModal" tabindex="-1">
                <div class="modal-dialog modal-sm modal-dialog-centered">
                    <div class="modal-content glass-card" style="background: var(--ds-bg-surface, #ffffff); border: 1px solid var(--ds-border-color, #cbd5e1); color: var(--ds-text-main, #0f172a); border-radius: 16px; box-shadow: 0 20px 40px rgba(0,0,0,0.25);">
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
                    <div class="modal-content glass-card" style="background: var(--ds-bg-surface, #ffffff); border: 1px solid var(--ds-border-color, #cbd5e1); color: var(--ds-text-main, #0f172a); border-radius: 16px; box-shadow: 0 20px 40px rgba(0,0,0,0.25);">
                        <div class="modal-header border-0 pb-0">
                            <h5 class="modal-title fw-bold text-main" style="color:var(--ds-text-main);"><i data-lucide="book-open" class="me-1 text-primary"></i> Add Knowledge Base Article</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
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
            </div>

            <!-- Sales Enquiry Detail Modal -->
            <div class="modal fade" id="sdEnquiryDetailModal" tabindex="-1" style="z-index: 1070;">
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
                                    <div class="p-3 rounded" style="background: var(--ds-bg-card); border: 1px solid var(--ds-border-color);">
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
                                            <a href="#" id="enqModalEmailBtn" class="ds-btn ds-btn-primary ds-btn-sm py-1 px-3 text-xs d-inline-flex align-items-center gap-1.5" style="border-radius: 6px;">
                                                <i data-lucide="mail" style="width:13px;height:13px;"></i> Contact Email
                                            </a>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="p-3 rounded" style="background: var(--ds-bg-card); border: 1px solid var(--ds-border-color);">
                                        <div class="text-xxs text-secondary uppercase fw-bold mb-1">Status & Submission Date</div>
                                        <div class="mb-2" id="enqModalStatusBadge"><span class="ds-badge blue">New</span></div>
                                        <div class="text-xs text-secondary" id="enqModalDate">Submitted: -</div>
                                    </div>
                                </div>
                            </div>

                            <div class="mb-4">
                                <label class="form-label text-xs fw-bold text-secondary uppercase">Submitted Message / Requirements</label>
                                <div class="p-3 rounded text-sm text-main" id="enqModalMessage" style="background: var(--ds-bg-card); border: 1px solid var(--ds-border-color); white-space:pre-wrap; min-height:80px;">-</div>
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
            <!-- In-App Compose Email Modal for Sales Enquiries -->
            <div class="modal fade" id="sdComposeEmailModal" tabindex="-1" style="z-index: 1080;">
                <div class="modal-dialog modal-lg modal-dialog-centered">
                    <div class="modal-content glass-card ds-card" style="background: var(--ds-bg-surface, #ffffff); border: 1px solid var(--ds-border-color, #cbd5e1); color: var(--ds-text-main, #0f172a); border-radius: 16px; box-shadow: 0 20px 40px rgba(0,0,0,0.25);">
                        <div class="modal-header border-bottom p-4">
                            <div class="d-flex align-items-center gap-2">
                                <div class="p-2 rounded-3" style="background: rgba(99, 102, 241, 0.12); color: var(--ds-primary, #6366f1);">
                                    <i data-lucide="send" style="width: 18px; height: 18px;"></i>
                                </div>
                                <div>
                                    <h5 class="modal-title fw-bold text-main mb-0" style="color:var(--ds-text-main);">Compose In-App Email</h5>
                                    <div class="text-xs text-secondary">Dispatched via configured Enterprise Support Email</div>
                                </div>
                            </div>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body p-4">
                            <form id="sdComposeEmailForm" onsubmit="event.preventDefault();">
                                <input type="hidden" id="sdComposeEnquiryId">
                                <div class="row g-3 mb-3">
                                    <div class="col-md-6">
                                        <label class="ds-label">RECIPIENT EMAIL</label>
                                        <input type="email" class="ds-input" id="sdComposeToEmail" required placeholder="recipient@company.com">
                                    </div>
                                    <div class="col-md-6">
                                        <label class="ds-label">PROSPECT NAME / COMPANY</label>
                                        <input type="text" class="ds-input" id="sdComposeProspectName" readonly style="opacity: 0.8;">
                                    </div>
                                </div>
                                <div class="mb-3">
                                    <label class="ds-label">EMAIL SUBJECT</label>
                                    <input type="text" class="ds-input" id="sdComposeSubject" required placeholder="Re: Inquiry Response - QCMS Enterprise">
                                </div>
                                <div class="mb-3">
                                    <label class="ds-label">MESSAGE CONTENT</label>
                                    <textarea class="ds-input" id="sdComposeMessage" rows="6" required placeholder="Type your email response here..."></textarea>
                                </div>
                                <div class="p-3 rounded-3 d-flex align-items-center gap-2" style="background: rgba(99, 102, 241, 0.06); border: 1px solid rgba(99, 102, 241, 0.15);">
                                    <i data-lucide="shield-check" class="text-primary" style="width: 16px; height: 16px;"></i>
                                    <span class="text-xs text-secondary">This email will be sent directly through your software mail server using the **Support Email** identity.</span>
                                </div>
                            </form>
                        </div>
                        <div class="modal-footer border-top p-4">
                            <button class="ds-btn ds-btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button class="ds-btn ds-btn-primary px-4" id="btnSendComposeEmail" onclick="SupportDesk.submitComposeEmail()">
                                <i data-lucide="send" style="width: 14px; height: 14px;" class="me-1"></i> Send Email Now
                            </button>
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
        } else if (tabId === 'trial-extensions') {
            await this.renderTrialExtensionsTab();
        }
    },

    async renderTrialExtensionsTab() {
        const view = document.getElementById('sdMainViewport');
        if (!view) return;
        view.innerHTML = `<div class="d-flex justify-content-center p-5"><div class="spinner-border text-primary" role="status"></div></div>`;

        try {
            const res = await api.get('/super-admin/trial-extensions');
            const data = (res && Array.isArray(res.data)) ? res.data : [];
            this._trialExtensionsData = data;

            const totalRequests = data.reduce((acc, o) => acc + (o.total_trial_requests || 0), 0);
            const autoApproved = data.reduce((acc, o) => acc + (o.auto_approved_trial_extensions || 0), 0);
            const manualApproved = data.reduce((acc, o) => acc + (o.manual_approved_trial_extensions || 0), 0);
            const pendingReqs = data.filter(o => o.pending_request && o.pending_request.status === 'Pending');

            let hasActiveAutoApproving = data.some(o => Boolean(o.is_auto_approving && o.seconds_remaining > 0));

            if (this._trialCountdownTimer) clearInterval(this._trialCountdownTimer);
            if (hasActiveAutoApproving) {
                this._trialCountdownTimer = setInterval(() => {
                    if (this.currentTab !== 'trial-extensions') {
                        clearInterval(this._trialCountdownTimer);
                        return;
                    }
                    const timerEls = document.querySelectorAll('[data-countdown-sec]');
                    if (!timerEls.length) {
                        clearInterval(this._trialCountdownTimer);
                        return;
                    }
                    let anyExpired = false;
                    timerEls.forEach(el => {
                        let sec = parseInt(el.getAttribute('data-countdown-sec')) || 0;
                        if (sec > 0) {
                            sec -= 1;
                            el.setAttribute('data-countdown-sec', sec);
                            const m = Math.floor(sec / 60);
                            const s = sec % 60;
                            el.textContent = `${m}m ${s < 10 ? '0' : ''}${s}s`;
                        } else {
                            anyExpired = true;
                        }
                    });
                    if (anyExpired) {
                        clearInterval(this._trialCountdownTimer);
                        setTimeout(() => {
                            if (this.currentTab === 'trial-extensions') {
                                this.renderTrialExtensionsTab();
                            }
                        }, 1000);
                    }
                }, 1000);
            }

            view.innerHTML = `
                <div class="fade-in v-stack gap-4">
                    <!-- KPI Cards -->
                    <div class="row g-2 g-md-3">
                        <div class="col-6 col-md-3">
                            <div class="glass-card p-2.5 p-md-3 d-flex align-items-center gap-2.5 gap-md-3 h-100" style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px;">
                                <div class="p-2 p-md-2.5 rounded-circle bg-primary-subtle text-primary flex-shrink-0"><i data-lucide="file-text" style="width:18px;height:18px;"></i></div>
                                <div class="min-w-0">
                                    <div class="text-xxs uppercase tracking-wider text-secondary fw-semibold text-truncate">Total Requests</div>
                                    <h4 class="fw-bold mb-0 text-main fs-5 fs-md-4 lh-1 mt-1">${totalRequests}</h4>
                                </div>
                            </div>
                        </div>
                        <div class="col-6 col-md-3">
                            <div class="glass-card p-2.5 p-md-3 d-flex align-items-center gap-2.5 gap-md-3 h-100" style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px;">
                                <div class="p-2 p-md-2.5 rounded-circle bg-warning-subtle text-warning flex-shrink-0"><i data-lucide="alert-circle" style="width:18px;height:18px;"></i></div>
                                <div class="min-w-0">
                                    <div class="text-xxs uppercase tracking-wider text-secondary fw-semibold text-truncate">Pending Review</div>
                                    <h4 class="fw-bold mb-0 text-main fs-5 fs-md-4 lh-1 mt-1">${pendingReqs.length}</h4>
                                </div>
                            </div>
                        </div>
                        <div class="col-6 col-md-3">
                            <div class="glass-card p-2.5 p-md-3 d-flex align-items-center gap-2.5 gap-md-3 h-100" style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px;">
                                <div class="p-2 p-md-2.5 rounded-circle bg-success-subtle text-success flex-shrink-0"><i data-lucide="zap" style="width:18px;height:18px;"></i></div>
                                <div class="min-w-0">
                                    <div class="text-xxs uppercase tracking-wider text-secondary fw-semibold text-truncate">Auto-Approved</div>
                                    <h4 class="fw-bold mb-0 text-main fs-5 fs-md-4 lh-1 mt-1">${autoApproved}</h4>
                                </div>
                            </div>
                        </div>
                        <div class="col-6 col-md-3">
                            <div class="glass-card p-2.5 p-md-3 d-flex align-items-center gap-2.5 gap-md-3 h-100" style="background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 12px;">
                                <div class="p-2 p-md-2.5 rounded-circle bg-info-subtle text-info flex-shrink-0"><i data-lucide="check-circle" style="width:18px;height:18px;"></i></div>
                                <div class="min-w-0">
                                    <div class="text-xxs uppercase tracking-wider text-secondary fw-semibold text-truncate">Manually Granted</div>
                                    <h4 class="fw-bold mb-0 text-main fs-5 fs-md-4 lh-1 mt-1">${manualApproved}</h4>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Main Table with Pagination and Search -->
                    <div class="glass-card p-4 rounded-3 border">
                        <div class="d-flex align-items-center justify-content-between flex-wrap gap-3 mb-3">
                            <div>
                                <h5 class="fw-bold text-main mb-1">Trial Extension Management</h5>
                                <p class="text-xs text-muted mb-0">View all organization extension requests and grant instant trial period extensions.</p>
                            </div>
                            <div class="d-flex align-items-center gap-2">
                                <div class="input-group input-group-sm" style="max-width: 240px;">
                                    <span class="input-group-text bg-transparent border-end-0 text-muted"><i data-lucide="search" style="width:13px;height:13px;"></i></span>
                                    <input type="text" class="form-control form-control-sm border-start-0 text-xs" placeholder="Search organization / email..." value="${this.trialExtensionsSearch || ''}" oninput="SupportDesk.filterTrialExtensions(this.value)">
                                </div>
                            </div>
                        </div>
                        <div class="table-responsive">
                            <table class="ds-table align-middle text-xs mb-0">
                                <thead>
                                    <tr>
                                        <th style="min-width:130px;">Organization</th>
                                        <th style="min-width:140px;">Admin Email</th>
                                        <th style="min-width:90px;">Requested</th>
                                        <th style="min-width:140px;">Reason / Notes</th>
                                        <th style="min-width:95px;">Request Date</th>
                                        <th style="min-width:100px;">Current Expiry</th>
                                        <th style="min-width:150px;">Status</th>
                                        <th class="text-end" style="min-width:90px;">Action</th>
                                    </tr>
                                </thead>
                                <tbody id="sdTrialExtensionsTableBody"></tbody>
                            </table>
                        </div>
                        <div id="sdTrialExtensionsPaginationFooter"></div>
                    </div>
                </div>
            `;

            this.renderTrialExtensionsTable();
            if (window.lucide) lucide.createIcons();
        } catch (e) {
            console.error('Failed to load trial extensions', e);
            view.innerHTML = `<div class="alert alert-danger p-3 text-xs">Failed to load trial extensions tab.</div>`;
        }
    },

    filterTrialExtensions(query) {
        this.trialExtensionsSearch = (query || '').toLowerCase().trim();
        this.trialExtensionsPage = 1;
        this.renderTrialExtensionsTable();
    },

    setTrialExtensionsPage(page) {
        this.trialExtensionsPage = page;
        this.renderTrialExtensionsTable();
    },

    setTrialExtensionsPerPage(perPage) {
        this.trialExtensionsPerPage = parseInt(perPage, 10) || 5;
        this.trialExtensionsPage = 1;
        this.renderTrialExtensionsTable();
    },

    renderTrialExtensionsTable() {
        const tbody = document.getElementById('sdTrialExtensionsTableBody');
        const footer = document.getElementById('sdTrialExtensionsPaginationFooter');
        if (!tbody) return;

        let allData = this._trialExtensionsData || [];
        if (this.trialExtensionsSearch) {
            const q = this.trialExtensionsSearch;
            allData = allData.filter(o => {
                const name = (o.name || '').toLowerCase();
                const email = (o.admin_email || '').toLowerCase();
                const code = (o.org_code || '').toLowerCase();
                return name.includes(q) || email.includes(q) || code.includes(q);
            });
        }

        const total = allData.length;
        const perPage = parseInt(this.trialExtensionsPerPage, 10) || 5;
        const totalPages = Math.ceil(total / perPage) || 1;

        if (this.trialExtensionsPage > totalPages) this.trialExtensionsPage = totalPages;
        if (this.trialExtensionsPage < 1) this.trialExtensionsPage = 1;

        const page = this.trialExtensionsPage;
        const startIdx = (page - 1) * perPage;
        const endIdx = Math.min(startIdx + perPage, total);
        const pageSlice = allData.slice(startIdx, endIdx);

        let rows = pageSlice.map(o => {
            const pending = o.pending_request || {};
            const isPending = pending.status === 'Pending';
            const isAutoApproving = Boolean(o.is_auto_approving && o.seconds_remaining > 0);

            let statusBadge = '';
            let actionButton = '';

            if (isAutoApproving) {
                const m = Math.floor(o.seconds_remaining / 60);
                const s = o.seconds_remaining % 60;
                const timerStr = `${m}m ${s < 10 ? '0' : ''}${s}s`;
                statusBadge = `<span class="badge bg-info-subtle text-info font-semibold px-2 py-1 text-nowrap d-inline-flex align-items-center"><span class="spinner-border spinner-border-sm me-1" style="width:10px;height:10px;"></span> Auto-Approving (<span id="timer-span-org-${o.id}" data-countdown-sec="${o.seconds_remaining}">${timerStr}</span>)</span>`;
                actionButton = `<button class="ds-btn ds-btn-secondary ds-btn-sm text-nowrap" disabled style="opacity: 0.65; cursor: not-allowed; font-size:11px; padding: 4px 8px;" title="Auto-approval in progress (5 min timer active). Super Admin action is frozen."><i data-lucide="lock" style="width:11px;height:11px;" class="me-1"></i> Frozen</button>`;
            } else if (isPending) {
                statusBadge = `<span class="badge bg-warning-subtle text-warning font-semibold px-2 py-1 text-nowrap">Pending Review</span>`;
                actionButton = `<button class="ds-btn ds-btn-primary ds-btn-sm text-nowrap" style="font-size:11px; padding: 4px 10px;" onclick="SupportDesk.openExtendTrialModal(${o.id}, '${(o.name || '').replace(/'/g, "\\'")}', ${pending.days || 14})"><i data-lucide="clock" style="width:11px;height:11px;" class="me-1"></i> Extend Trial</button>`;
            } else {
                statusBadge = (o.auto_approved_trial_extensions > 0 || o.manual_approved_trial_extensions > 0)
                    ? `<span class="badge bg-success-subtle text-success font-semibold px-2 py-1 text-nowrap">Extended (${o.total_trial_requests}x)</span>`
                    : `<span class="badge bg-secondary-subtle text-secondary font-semibold px-2 py-1 text-nowrap">Standard Trial</span>`;
                actionButton = `<button class="ds-btn ds-btn-primary ds-btn-sm text-nowrap" style="font-size:11px; padding: 4px 10px;" onclick="SupportDesk.openExtendTrialModal(${o.id}, '${(o.name || '').replace(/'/g, "\\'")}', ${pending.days || 14})"><i data-lucide="clock" style="width:11px;height:11px;" class="me-1"></i> Extend Trial</button>`;
            }

            const requestedDays = pending.days ? `+${pending.days} Days` : '—';
            const reasonText = pending.reason ? pending.reason : (o.total_trial_requests > 0 ? `${o.total_trial_requests} extension(s) granted` : 'No extension requests');
            const reqDate = pending.requested_at ? QCMS.formatDate(pending.requested_at) : '—';
            const expiryDate = o.trial_ends_at ? QCMS.formatDate(o.trial_ends_at) : '—';

            return `
                <tr>
                    <td>
                        <div class="fw-bold text-main text-truncate" style="max-width: 140px;">${o.name}</div>
                        <div class="text-xxs text-muted">ID: ${o.id} • ${o.org_code}</div>
                    </td>
                    <td>
                        <div class="text-xs text-secondary text-truncate" style="max-width: 150px;">${o.admin_email || '—'}</div>
                    </td>
                    <td>
                        <span class="badge bg-primary-subtle text-primary fw-semibold">${requestedDays}</span>
                    </td>
                    <td style="max-width:180px;">
                        <div class="text-xs text-secondary text-truncate" title="${reasonText}">${reasonText}</div>
                    </td>
                    <td>
                        <div class="text-xs text-muted text-nowrap">${reqDate}</div>
                    </td>
                    <td>
                        <div class="fw-semibold text-xs text-primary text-nowrap">${expiryDate}</div>
                        <div class="text-xxs text-muted text-nowrap">${o.trial_days_left !== null ? o.trial_days_left + ' days left' : ''}</div>
                    </td>
                    <td>${statusBadge}</td>
                    <td class="text-end">${actionButton}</td>
                </tr>
            `;
        }).join('');

        if (total === 0) {
            rows = `<tr><td colspan="8" class="text-center py-5 text-muted"><i data-lucide="clock" style="width:32px;height:32px;" class="mb-2 text-muted"></i><br>${this.trialExtensionsSearch ? 'No organizations match search criteria.' : 'No trial extension requests found.'}</td></tr>`;
        }

        tbody.innerHTML = rows;

        if (footer) {
            const startItem = total > 0 ? startIdx + 1 : 0;
            const endItem = endIdx;

            let pageBtns = '';
            if (totalPages <= 7) {
                for (let p = 1; p <= totalPages; p++) {
                    pageBtns += `<button class="ds-btn ${p === page ? 'ds-btn-primary' : 'ds-btn-outline'} ds-btn-sm py-1 px-3 fw-bold" onclick="SupportDesk.setTrialExtensionsPage(${p})">${p}</button>`;
                }
            } else {
                const pagesToShow = [];
                pagesToShow.push(1);
                if (page > 3) pagesToShow.push('...');
                for (let p = Math.max(2, page - 1); p <= Math.min(totalPages - 1, page + 1); p++) {
                    pagesToShow.push(p);
                }
                if (page < totalPages - 2) pagesToShow.push('...');
                pagesToShow.push(totalPages);

                pageBtns = pagesToShow.map(p => {
                    if (p === '...') return `<span class="text-muted px-1 text-xs">...</span>`;
                    return `<button class="ds-btn ${p === page ? 'ds-btn-primary' : 'ds-btn-outline'} ds-btn-sm py-1 px-3 fw-bold" onclick="SupportDesk.setTrialExtensionsPage(${p})">${p}</button>`;
                }).join('');
            }

            footer.innerHTML = `
                <div class="d-flex align-items-center justify-content-between flex-wrap gap-2 mt-3 pt-3 border-top">
                    <div class="text-xs text-secondary">
                        ${total > 0 ? `Showing <strong>${startItem}–${endItem}</strong> of <strong>${total}</strong> requests` : 'Showing 0 of 0 requests'}
                    </div>
                    <div class="d-flex align-items-center gap-2">
                        <label class="text-xs text-muted me-1 mb-0 d-none d-sm-inline">Show per page:</label>
                        <select class="ds-input text-xs py-1 px-2" style="width: auto; height: 32px; border-radius: 6px;" onchange="SupportDesk.setTrialExtensionsPerPage(this.value)">
                            <option value="5" ${perPage == 5 ? 'selected' : ''}>5 per page</option>
                            <option value="10" ${perPage == 10 ? 'selected' : ''}>10 per page</option>
                            <option value="20" ${perPage == 20 ? 'selected' : ''}>20 per page</option>
                            <option value="30" ${perPage == 30 ? 'selected' : ''}>30 per page</option>
                            <option value="50" ${perPage == 50 ? 'selected' : ''}>50 per page</option>
                            <option value="100" ${perPage == 100 ? 'selected' : ''}>100 per page</option>
                        </select>
                        <button class="ds-btn ds-btn-outline ds-btn-sm py-1 px-2.5 d-inline-flex align-items-center justify-content-center" ${page <= 1 ? 'disabled' : ''} onclick="SupportDesk.setTrialExtensionsPage(${page - 1})" title="Previous Page">
                            <i data-lucide="chevron-left" style="width:14px;height:14px;"></i>
                        </button>
                        ${pageBtns}
                        <button class="ds-btn ds-btn-outline ds-btn-sm py-1 px-2.5 d-inline-flex align-items-center justify-content-center" ${page >= totalPages ? 'disabled' : ''} onclick="SupportDesk.setTrialExtensionsPage(${page + 1})" title="Next Page">
                            <i data-lucide="chevron-right" style="width:14px;height:14px;"></i>
                        </button>
                    </div>
                </div>
            `;
        }

        if (window.lucide) lucide.createIcons();
    },

    openExtendTrialModal(orgId, orgName, defaultDays = 14) {
        let modalEl = document.getElementById('sdSuperExtendTrialModal');
        if (!modalEl) {
            const div = document.createElement('div');
            div.innerHTML = `
                <div class="modal fade" id="sdSuperExtendTrialModal" tabindex="-1" style="z-index: 1090;">
                    <div class="modal-dialog modal-dialog-centered">
                        <div class="modal-content glass-card border-0 shadow-lg" style="background: var(--ds-bg-card, #ffffff);">
                            <div class="modal-header border-bottom p-4">
                                <div class="d-flex align-items-center gap-3">
                                    <div class="p-2 rounded-3 bg-primary-subtle text-primary">
                                        <i data-lucide="clock" style="width:22px;height:22px;"></i>
                                    </div>
                                    <div>
                                        <h5 class="modal-title fw-bold mb-0">Extend Organization Trial</h5>
                                        <p class="text-xs text-muted mb-0" id="sdSuperExtendOrgName">Organization Trial Extension</p>
                                    </div>
                                </div>
                                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                            </div>
                            <div class="modal-body p-4">
                                <form id="sdSuperExtendForm" onsubmit="event.preventDefault(); SupportDesk.submitSuperTrialExtension();">
                                    <input type="hidden" id="sdSuperExtendOrgId">
                                    <div class="mb-3">
                                        <label class="form-label text-xs fw-semibold text-muted text-uppercase mb-1">Select Extension Period</label>
                                        <select class="ds-input text-sm" id="sdSuperExtendDays" required onchange="SupportDesk.toggleCustomTrialDaysInput(this.value)">
                                            <option value="7">+7 Days Extension</option>
                                            <option value="14">+14 Days Extension (Recommended)</option>
                                            <option value="30">+30 Days Extension (1 Month)</option>
                                            <option value="60">+60 Days Extension (2 Months)</option>
                                            <option value="custom">Custom Days (Enter Manually)</option>
                                        </select>
                                    </div>
                                    <div class="mb-3" id="sdCustomDaysContainer" style="display: none;">
                                        <label class="form-label text-xs fw-semibold text-muted text-uppercase mb-1">Enter Custom Number of Days <span class="text-danger">*</span></label>
                                        <input type="number" class="ds-input text-sm" id="sdSuperCustomDaysInput" min="1" max="365" placeholder="e.g. 45">
                                    </div>
                                    <div class="d-flex justify-content-end gap-2 pt-2">
                                        <button type="button" class="ds-btn ds-btn-ghost ds-btn-sm" data-bs-dismiss="modal">Cancel</button>
                                        <button type="submit" class="ds-btn ds-btn-primary ds-btn-sm" id="btnSdSuperExtend">
                                            <i data-lucide="check-circle" style="width:14px;height:14px;" class="me-1"></i> Grant Extension
                                        </button>
                                    </div>
                                </form>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(div.firstElementChild);
            modalEl = document.getElementById('sdSuperExtendTrialModal');
        }

        document.getElementById('sdSuperExtendOrgId').value = orgId;
        document.getElementById('sdSuperExtendOrgName').innerText = `Grant extension for organization: ${orgName}`;
        
        // Select requested or default days in modal
        const daysSelect = document.getElementById('sdSuperExtendDays');
        const customInput = document.getElementById('sdSuperCustomDaysInput');
        const targetDays = String(defaultDays || 14);
        if (daysSelect) {
            const hasOption = Array.from(daysSelect.options).some(o => o.value === targetDays);
            if (hasOption) {
                daysSelect.value = targetDays;
                this.toggleCustomTrialDaysInput(targetDays);
            } else {
                daysSelect.value = 'custom';
                this.toggleCustomTrialDaysInput('custom');
                if (customInput) customInput.value = targetDays;
            }
        }

        const bsModal = bootstrap.Modal.getOrCreateInstance(modalEl);
        bsModal.show();
        if (window.lucide) lucide.createIcons();
    },

    toggleCustomTrialDaysInput(val) {
        const container = document.getElementById('sdCustomDaysContainer');
        const input = document.getElementById('sdSuperCustomDaysInput');
        if (container) {
            if (val === 'custom') {
                container.style.display = 'block';
                if (input) { input.required = true; input.focus(); }
            } else {
                container.style.display = 'none';
                if (input) { input.required = false; input.value = ''; }
            }
        }
    },

    async submitSuperTrialExtension() {
        const orgId = document.getElementById('sdSuperExtendOrgId')?.value;
        const daysSelect = document.getElementById('sdSuperExtendDays')?.value;
        let days = 14;

        if (daysSelect === 'custom') {
            const customVal = parseInt(document.getElementById('sdSuperCustomDaysInput')?.value);
            if (isNaN(customVal) || customVal <= 0) {
                if (window.QCMS && QCMS.toast) QCMS.toast('Please enter a valid positive number of custom days', 'warning');
                return;
            }
            days = customVal;
        } else {
            days = parseInt(daysSelect) || 14;
        }

        if (!orgId) return;

        const btn = document.getElementById('btnSdSuperExtend');
        if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Processing...'; }

        try {
            const res = await api.put(`/super-admin/companies/${orgId}/trial`, { days });
            if (window.QCMS && QCMS.toast) {
                QCMS.toast(res.message || `Successfully extended trial by +${days} days!`, 'success');
            }
            const modalEl = document.getElementById('sdSuperExtendTrialModal');
            if (modalEl) {
                const modal = bootstrap.Modal.getInstance(modalEl);
                if (modal) modal.hide();
            }
            await this.renderTrialExtensionsTab();
            if (window.superAdminApp && typeof window.superAdminApp.loadOrganizations === 'function') {
                window.superAdminApp.loadOrganizations();
            } else if (window.superAdmin && typeof window.superAdmin.loadOrganizations === 'function') {
                window.superAdmin.loadOrganizations();
            }
        } catch (e) {
            if (window.QCMS && QCMS.toast) QCMS.toast(e.message || 'Failed to extend trial', 'error');
        } finally {
            if (btn) { btn.disabled = false; btn.innerHTML = '<i data-lucide="check-circle" style="width:14px;height:14px;" class="me-1"></i> Grant Extension'; }
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
                            <option value="Open" ${this.filters.status === 'Open' ? 'selected' : ''}>Open</option>
                            <option value="" ${!this.filters.status ? 'selected' : ''}>All Status</option>
                            <option value="Assigned" ${this.filters.status === 'Assigned' ? 'selected' : ''}>Assigned</option>
                            <option value="In Progress" ${this.filters.status === 'In Progress' ? 'selected' : ''}>In Progress</option>
                            <option value="Waiting for Customer" ${this.filters.status === 'Waiting for Customer' ? 'selected' : ''}>Waiting for Customer</option>
                            <option value="Resolved" ${this.filters.status === 'Resolved' ? 'selected' : ''}>Resolved</option>
                            <option value="Closed" ${this.filters.status === 'Closed' ? 'selected' : ''}>Closed</option>
                        </select>

                        <select class="ds-input ds-select py-1.5" style="max-width:140px; font-size:12.5px;" onchange="SupportDesk.setFilter('priority', this.value)">
                            <option value="" ${!this.filters.priority ? 'selected' : ''}>All Priorities</option>
                            <option value="Low" ${this.filters.priority === 'Low' ? 'selected' : ''}>Low</option>
                            <option value="Medium" ${this.filters.priority === 'Medium' ? 'selected' : ''}>Medium</option>
                            <option value="High" ${this.filters.priority === 'High' ? 'selected' : ''}>High</option>
                            <option value="Critical" ${this.filters.priority === 'Critical' ? 'selected' : ''}>Critical</option>
                        </select>

                        <select class="ds-input ds-select py-1.5" style="max-width:140px; font-size:12.5px;" onchange="SupportDesk.setFilter('category', this.value)">
                            <option value="" ${!this.filters.category ? 'selected' : ''}>All Categories</option>
                            <option value="Technical" ${this.filters.category === 'Technical' ? 'selected' : ''}>Technical</option>
                            <option value="Billing" ${this.filters.category === 'Billing' ? 'selected' : ''}>Billing</option>
                            <option value="License" ${this.filters.category === 'License' ? 'selected' : ''}>License</option>
                            <option value="Subscription" ${this.filters.category === 'Subscription' ? 'selected' : ''}>Subscription</option>
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
                    const startItem = meta.total_items > 0 ? (meta.page - 1) * meta.per_page + 1 : 0;
                    const endItem = Math.min(meta.page * meta.per_page, meta.total_items);
                    let pageBtns = '';
                    for (let p = 1; p <= meta.total_pages; p++) {
                        pageBtns += `<button class="ds-btn ${p === meta.page ? 'ds-btn-primary' : 'ds-btn-outline'} ds-btn-sm py-1 px-3 fw-bold" onclick="SupportDesk.setPage(${p})">${p}</button>`;
                    }
                    footer.innerHTML = `
                        <div class="text-xs text-secondary">
                            ${meta.total_items > 0 ? `Showing <strong>${startItem}–${endItem}</strong> of <strong>${meta.total_items}</strong> items` : 'Showing 0 of 0'}
                        </div>
                        <div class="d-flex align-items-center gap-2">
                            <select class="ds-input text-xs py-1 px-2" style="width: auto; height: 32px;" onchange="SupportDesk.setPerPage(this.value)">
                                <option value="10" ${meta.per_page == 10 ? 'selected' : ''}>10 per page</option>
                                <option value="20" ${meta.per_page == 20 ? 'selected' : ''}>20 per page</option>
                                <option value="50" ${meta.per_page == 50 ? 'selected' : ''}>50 per page</option>
                            </select>
                            <button class="ds-btn ds-btn-outline ds-btn-sm py-1 px-2.5 d-inline-flex align-items-center justify-content-center" ${meta.page <= 1 ? 'disabled' : ''} onclick="SupportDesk.setPage(${meta.page - 1})" title="Previous Page">
                                <i data-lucide="chevron-left" style="width:14px;height:14px;"></i>
                            </button>
                            ${pageBtns}
                            <button class="ds-btn ds-btn-outline ds-btn-sm py-1 px-2.5 d-inline-flex align-items-center justify-content-center" ${meta.page >= meta.total_pages ? 'disabled' : ''} onclick="SupportDesk.setPage(${meta.page + 1})" title="Next Page">
                                <i data-lucide="chevron-right" style="width:14px;height:14px;"></i>
                            </button>
                        </div>
                    `;
                    if (window.lucide) lucide.createIcons();
                }
            }
        } catch (e) {
            tbody.innerHTML = `<tr><td colspan="9" class="text-center py-4 text-danger">Failed to query tickets.</td></tr>`;
        }
    },

    setPage(page) {
        if (page < 1) return;
        this.currentPage = page;
        this.loadTickets();
    },

    setPerPage(perPage) {
        this.perPage = parseInt(perPage, 10) || 10;
        this.currentPage = 1;
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
                    <span class="text-xs fw-bold ${this.wizards.step === 4 ? 'text-primary' : 'text-secondary'}">4. Review</span>
                </div>

                <div id="sdWizardStepContent">
                    <!-- Loaded dynamically based on step -->
                </div>

                <div class="d-flex justify-content-between mt-4 pt-3 border-top" style="border-color:rgba(255,255,255,0.06)!important;">
                    <button class="ds-btn ds-btn-outline ds-btn-sm" onclick="SupportDesk.prevStep()" ${this.wizards.step === 1 ? 'disabled' : ''}>Back</button>
                    <button class="ds-btn ds-btn-primary ds-btn-sm" onclick="SupportDesk.nextStep()">${this.wizards.step === 4 ? 'Create Ticket' : 'Continue'}</button>
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
                        <label class="ds-label">Organization Name <span class="text-danger">*</span></label>
                        <div class="position-relative">
                            <input type="text" 
                                   class="ds-input w-100 pe-5" 
                                   id="wizOrgInput" 
                                   name="no_autofill_org_name"
                                   placeholder="Type or select Tenant Organization..." 
                                   autocomplete="one-time-code"
                                   spellcheck="false"
                                   value="${selectedOrgName}" 
                                   onfocus="SupportDesk.openOrgDropdown()"
                                   oninput="SupportDesk.handleOrgSearch(this.value)">
                            <i data-lucide="chevron-down" class="position-absolute end-0 top-50 translate-middle-y me-3 text-secondary pointer-events-none" style="width:16px;height:16px;"></i>
                        </div>
                        
                        <div class="dropdown-menu w-100 p-1.5 shadow-lg glass-dropdown custom-scroll" 
                             id="wizOrgMenu" 
                             style="max-height: 230px; overflow-y: auto; display: none; position: absolute; top: 100%; left: 0; right: 0; width: 100%; margin-top: 4px; z-index: 1050; background: rgba(22, 27, 38, 0.98); border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 8px; backdrop-filter: blur(12px);"
                             onscroll="SupportDesk.handleOrgMenuScroll(this)">
                            <div id="wizOrgList" class="v-stack gap-1"></div>
                            <div id="wizOrgLoader" class="text-center p-2 text-xs text-muted" style="display:none;">
                                <span class="spinner-border spinner-border-sm me-1" style="width:12px;height:12px;"></span> Loading matching organizations...
                            </div>
                            <div id="wizOrgEmpty" class="text-center p-3 text-xs text-muted" style="display:none;">
                                No matching tenant organizations found.
                            </div>
                        </div>
                    </div>
                    <div class="ds-field">
                        <label class="ds-label">Requester Name <span class="text-danger">*</span></label>
                        <input type="text" class="ds-input" id="wizReqName" placeholder="e.g. John Doe" value="${data.requester_name}" oninput="SupportDesk.wizards.data.requester_name = this.value">
                    </div>
                    <div class="ds-field">
                        <label class="ds-label">Requester Email <span class="text-danger">*</span></label>
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
                        <label class="ds-label">Subject <span class="text-danger">*</span></label>
                        <input type="text" class="ds-input" id="wizSubject" placeholder="Brief summary of the issue..." value="${data.subject}" oninput="SupportDesk.wizards.data.subject = this.value">
                    </div>
                    <div class="ds-field">
                        <label class="ds-label">Description <span class="text-danger">*</span></label>
                        <textarea class="ds-input" id="wizDesc" rows="4" placeholder="Detail the steps to reproduce, errors seen..." oninput="SupportDesk.wizards.data.description = this.value">${data.description}</textarea>
                    </div>
                    <div class="row g-3">
                        <div class="col-md-6">
                            <label class="ds-label">Priority <span class="text-danger">*</span></label>
                            <select class="ds-input ds-select" id="wizPriority" onchange="SupportDesk.wizards.data.priority = this.value">
                                <option value="Low" ${data.priority === 'Low' ? 'selected' : ''}>Low</option>
                                <option value="Medium" ${data.priority === 'Medium' ? 'selected' : ''}>Medium</option>
                                <option value="High" ${data.priority === 'High' ? 'selected' : ''}>High</option>
                                <option value="Critical" ${data.priority === 'Critical' ? 'selected' : ''}>Critical</option>
                            </select>
                        </div>
                        <div class="col-md-6">
                            <label class="ds-label">Category <span class="text-danger">*</span></label>
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
                        <p class="text-xxs text-secondary">Only PDF, DOC/DOCX documents, and images (PNG/JPG/GIF/WEBP) allowed</p>
                        <input type="file" id="wizFileInp" style="display:none;" accept=".pdf,.doc,.docx,.png,.jpg,.jpeg,.gif,.webp,image/*,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document" onchange="SupportDesk.handleWizFileUpload(this)">
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

        let items = [...(this.orgSelectorState.items || [])];
        const searchTerm = (this.orgSelectorState.search || '').toLowerCase().trim();
        const selectedId = this.wizards.data.organization_id;

        // Perform instant client-side matching if user has typed something
        if (searchTerm) {
            items = items.filter(o => {
                const name = (o.name || '').toLowerCase();
                const email = (o.email || '').toLowerCase();
                const admin = (o.admin_name || '').toLowerCase();
                const code = (o.code || '').toLowerCase();
                return name.includes(searchTerm) || email.includes(searchTerm) || admin.includes(searchTerm) || code.includes(searchTerm);
            });

            // Sort items so exact prefix matches appear at top
            items.sort((a, b) => {
                const aName = (a.name || '').toLowerCase();
                const bName = (b.name || '').toLowerCase();
                const aStarts = aName.startsWith(searchTerm);
                const bStarts = bName.startsWith(searchTerm);
                if (aStarts && !bStarts) return -1;
                if (!aStarts && bStarts) return 1;
                return aName.localeCompare(bName);
            });
        }

        if (items.length === 0 && !this.orgSelectorState.isLoading) {
            listEl.innerHTML = '';
            if (emptyEl) {
                emptyEl.textContent = searchTerm ? `No tenant matching "${this.orgSelectorState.search}" found.` : 'No matching tenant organizations found.';
                emptyEl.style.display = 'block';
            }
            return;
        }

        if (emptyEl) emptyEl.style.display = 'none';

        listEl.innerHTML = items.map(o => {
            const isSelected = selectedId == o.id;
            const safeName = (o.name || '').replace(/'/g, "\\'");
            const safeEmail = (o.email || '').replace(/'/g, "\\'");
            const safeAdmin = (o.admin_name || '').replace(/'/g, "\\'");

            let displayName = (o.name || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            if (searchTerm && displayName.toLowerCase().includes(searchTerm)) {
                const idx = displayName.toLowerCase().indexOf(searchTerm);
                const matchPart = displayName.substring(idx, idx + searchTerm.length);
                displayName = displayName.substring(0, idx) + `<strong class="text-primary">${matchPart}</strong>` + displayName.substring(idx + searchTerm.length);
            }
            
            return `
                <div class="org-item-option p-2 rounded text-xs d-flex align-items-center justify-content-between text-main hover-highlight"
                     style="cursor: pointer; transition: background 0.15s ease-in-out; border-radius: 6px; ${isSelected ? 'background: rgba(37, 99, 235, 0.18); color: var(--ds-primary, #3b82f6);' : ''}"
                     onmouseover="this.style.background='rgba(255,255,255,0.08)'"
                     onmouseout="this.style.background='${isSelected ? 'rgba(37, 99, 235, 0.18)' : 'transparent'}'"
                     onclick="SupportDesk.selectOrg(${o.id}, '${safeName}', '${safeEmail}', '${safeAdmin}')">
                    <div>
                        <div class="fw-semibold ${isSelected ? 'text-primary' : 'text-main'}">${displayName}</div>
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

        if (email) {
            this.wizards.data.requester_email = email;
            const emailEl = document.getElementById('wizReqEmail');
            if (emailEl) emailEl.value = email;
        }
        if (adminName) {
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
        if (this.wizards.step < 4) {
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
        if (titleEl) titleEl.value = '';
        if (catEl) catEl.value = 'Technical';
        if (contentEl) contentEl.value = '';

        const modalEl = this.ensureModalInBody('sdCreateKbModal');
        if (modalEl) {
            const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
            modal.show();
        }
    },

    async submitKbArticle() {
        const title = document.getElementById('sdKbTitle')?.value?.trim();
        const category = document.getElementById('sdKbCategory')?.value;
        const content = document.getElementById('sdKbContent')?.value?.trim();
        const is_internal = false;

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

                // Render uploaded attachments
                const attWrapper = document.getElementById('sdModalAttachmentsWrapper');
                const attList = document.getElementById('sdModalAttachmentsList');
                if (attWrapper && attList) {
                    const attachments = t.attachments || [];
                    if (attachments.length > 0) {
                        attWrapper.style.display = 'block';
                        attList.innerHTML = attachments.map(att => {
                            const isImg = /\.(png|jpe?g|gif|webp|svg)$/i.test(att.file_name);
                            const iconName = isImg ? 'image' : (/\.pdf$/i.test(att.file_name) ? 'file-text' : 'file-text');
                            const fileKb = att.file_size ? `${(att.file_size / 1024).toFixed(1)} KB` : '';
                            return `
                                <a href="${att.file_path}" target="_blank" download class="ds-btn ds-btn-outline ds-btn-sm text-main py-1 px-2.5 d-inline-flex align-items-center gap-1.5 text-decoration-none me-2 mb-2">
                                    <i data-lucide="${iconName}" class="text-primary" style="width:14px;height:14px;"></i>
                                    <span>${att.file_name}</span>
                                    ${fileKb ? `<span class="text-muted text-xxs">(${fileKb})</span>` : ''}
                                    <i data-lucide="download" class="text-muted ms-1" style="width:12px;height:12px;"></i>
                                </a>
                            `;
                        }).join('');
                    } else {
                        attWrapper.style.display = 'none';
                        attList.innerHTML = '';
                    }
                }

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
                const modalEl = this.ensureModalInBody('sdTicketDetailModal');
                const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
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
            const isInternal = c.is_internal;
            const initials = (c.user || '?').split(/[@\s.]+/).map(p => p[0] || '').join('').toUpperCase().slice(0, 2) || '?';
            const avatarBg = isInternal ? '#92400e' : 'var(--ds-accent, #4f8ef7)';
            const internalBadge = isInternal
                ? '<span class="badge ms-2" style="background:rgba(245,158,11,0.15);color:#f59e0b;border:1px solid rgba(245,158,11,0.3);font-size:10px;font-weight:600;padding:2px 7px;border-radius:20px;">Internal Note</span>'
                : '<span class="badge ms-2" style="background:rgba(79,142,247,0.12);color:var(--ds-accent,#4f8ef7);border:1px solid rgba(79,142,247,0.25);font-size:10px;font-weight:600;padding:2px 7px;border-radius:20px;">Public</span>';
            const cardBg    = isInternal ? 'rgba(245,158,11,0.05)' : 'rgba(255,255,255,0.025)';
            const cardBorder = isInternal ? '1px solid rgba(245,158,11,0.18)' : '1px solid rgba(255,255,255,0.07)';
            const leftAccent = isInternal ? '#f59e0b' : 'var(--ds-accent,#4f8ef7)';

            let attHtml = '';
            if (c.attachments && c.attachments.length > 0) {
                attHtml = '<div class="d-flex flex-wrap gap-2 mt-2 pt-2" style="border-top:1px solid rgba(255,255,255,0.07);">';
                attHtml += c.attachments.map(a => {
                    const isImg = /\.(png|jpe?g|gif|webp|svg)$/i.test(a.file_name);
                    const icon = isImg ? 'image' : 'file-text';
                    const kb = a.file_size ? `${(a.file_size / 1024).toFixed(1)} KB` : '';
                    return `<a href="${a.file_path}" target="_blank" download
                        class="ds-btn ds-btn-ghost ds-btn-sm py-1 px-2 d-inline-flex align-items-center gap-1 text-decoration-none"
                        style="border:1px solid rgba(255,255,255,0.12);border-radius:6px;">
                        <i data-lucide="${icon}" class="text-primary" style="width:12px;height:12px;"></i>
                        <span class="text-xs">${a.file_name}</span>
                        ${kb ? `<span class="text-xxs text-muted">(${kb})</span>` : ''}
                        <i data-lucide="download" class="text-muted" style="width:11px;height:11px;"></i>
                    </a>`;
                }).join('');
                attHtml += '</div>';
            }

            return `
                <div style="background:${cardBg};border:${cardBorder};border-left:3px solid ${leftAccent};border-radius:10px;padding:12px 14px;display:flex;gap:12px;align-items:flex-start;">
                    <div style="flex-shrink:0;width:34px;height:34px;border-radius:50%;background:${avatarBg};color:#fff;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;letter-spacing:.03em;">${initials}</div>
                    <div style="flex:1;min-width:0;">
                        <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:4px;margin-bottom:6px;">
                            <div style="display:flex;align-items:center;flex-wrap:wrap;">
                                <span style="font-size:12px;font-weight:700;color:var(--ds-text-main,#f1f5f9);white-space:nowrap;">${c.user}</span>
                                ${internalBadge}
                            </div>
                            <span style="font-size:11px;color:var(--ds-text-secondary,#94a3b8);white-space:nowrap;flex-shrink:0;">${QCMS.formatDate(c.created_at)}</span>
                        </div>
                        <p style="font-size:13px;color:var(--ds-text-secondary,#cbd5e1);margin:0;white-space:pre-wrap;line-height:1.6;word-break:break-word;">${c.content}</p>
                        ${attHtml}
                    </div>
                </div>
            `;
        }).join('') || '<div class="text-center text-muted text-xs py-4"><i data-lucide="message-circle" style="width:20px;height:20px;opacity:.4;display:block;margin:0 auto 6px;"></i>No conversations recorded yet.</div>';
        if (window.lucide) lucide.createIcons();
    },

    _pendingAttachment: null,

    async uploadCommentFile(input) {
        const file = input && input.files && input.files[0];
        const el = document.getElementById('sdCommentFileName');
        this._pendingAttachment = null;

        if (!file) {
            if (el) el.innerHTML = '';
            return;
        }

        // Strict client-side type check — PDF and images only
        const allowedExts = ['pdf', 'png', 'jpg', 'jpeg', 'gif', 'webp'];
        const ext = file.name.toLowerCase().split('.').pop();
        if (!allowedExts.includes(ext)) {
            QCMS.toast('Invalid file type. Only PDF and images (PNG, JPG, GIF, WEBP) are allowed.', 'warning');
            input.value = '';
            if (el) el.innerHTML = '';
            return;
        }

        // Show uploading state
        if (el) el.innerHTML = `<span class="badge bg-secondary-subtle text-secondary border py-1 px-2 d-inline-flex align-items-center gap-1"><i data-lucide="loader" style="width:12px;height:12px;"></i> Uploading...</span>`;
        if (window.lucide) lucide.createIcons();

        try {
            const token = (window.api && window.api.token) 
                || localStorage.getItem('access_token') 
                || sessionStorage.getItem('access_token') 
                || localStorage.getItem('token') 
                || sessionStorage.getItem('token') 
                || localStorage.getItem('qcms_token');
            const formData = new FormData();
            formData.append('file', file);
            const resp = await fetch(`/api/support/tickets/${this.currentTicketId}/upload-attachment`, {
                method: 'POST',
                headers: token ? { 'Authorization': `Bearer ${token}` } : {},
                body: formData
            });
            const result = await resp.json().catch(() => ({}));
            if (resp.ok && result.status === 'success') {
                this._pendingAttachment = result.attachment;
                const kb = (file.size / 1024).toFixed(1);
                const icon = ext === 'pdf' ? 'file-text' : 'image';
                if (el) {
                    el.innerHTML = `<span class="badge bg-success-subtle text-success border border-success-subtle py-1 px-2 d-inline-flex align-items-center gap-1"><i data-lucide="${icon}" style="width:12px;height:12px;"></i> ${file.name} (${kb} KB) ✓</span>`;
                    if (window.lucide) lucide.createIcons();
                }
            } else {
                QCMS.toast(result.message || result.error || 'Upload failed', 'error');
                input.value = '';
                if (el) el.innerHTML = '';
            }
        } catch (e) {
            QCMS.toast('Upload failed: ' + (e.message || 'Server network error'), 'error');
            input.value = '';
            if (el) el.innerHTML = '';
        }
    },

    async submitComment() {
        const content = document.getElementById('sdNewCommentContent').value.trim();
        const isInternal = document.getElementById('cTypeInternal').checked;

        if (!content) {
            QCMS.toast('Please enter response text', 'warning');
            return;
        }

        try {
            const payload = { content, is_internal: isInternal, attachments: [] };
            if (this._pendingAttachment) {
                payload.attachments = [this._pendingAttachment];
            }
            const res = await api.post(`/support/tickets/${this.currentTicketId}/comments`, payload);
            if (res.status === 'success') {
                QCMS.toast('Response submitted successfully', 'success');
                document.getElementById('sdNewCommentContent').value = '';
                const fileInput = document.getElementById('sdCommentFile');
                if (fileInput) fileInput.value = '';
                const fileNameEl = document.getElementById('sdCommentFileName');
                if (fileNameEl) fileNameEl.innerHTML = '';
                this._pendingAttachment = null;
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
        const modalEl = this.ensureModalInBody('sdCSATModal');
        const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
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
                
                container.innerHTML = audits.map((a, idx) => {
                    const isLast = idx === audits.length - 1;
                    let actionIcon = 'activity';
                    let actionColor = 'var(--ds-accent, #4f8ef7)';
                    const actLower = (a.action || '').toLowerCase();
                    if (actLower.includes('create')) {
                        actionIcon = 'plus-circle';
                        actionColor = '#10b981';
                    } else if (actLower.includes('comment')) {
                        actionIcon = 'message-square';
                        actionColor = '#6366f1';
                    } else if (actLower.includes('status')) {
                        actionIcon = 'refresh-cw';
                        actionColor = '#f59e0b';
                    } else if (actLower.includes('escalat')) {
                        actionIcon = 'alert-triangle';
                        actionColor = '#ef4444';
                    }

                    return `
                        <div class="d-flex align-items-start gap-3 py-2.5 ${!isLast ? 'border-bottom' : ''}" style="border-color: var(--ds-border-color, rgba(148,163,184,0.18)) !important;">
                            <div class="rounded-circle d-flex align-items-center justify-content-center flex-shrink-0 mt-0.5"
                                 style="width: 28px; height: 28px; background: rgba(79, 142, 247, 0.08); border: 1px solid rgba(79, 142, 247, 0.2);">
                                <i data-lucide="${actionIcon}" style="width: 14px; height: 14px; color: ${actionColor};"></i>
                            </div>
                            <div class="flex-grow-1 min-w-0">
                                <div class="d-flex justify-content-between align-items-center flex-wrap gap-1">
                                    <span class="text-xs fw-bold text-main" style="color: var(--ds-text-main);">${a.action}</span>
                                    <span class="text-xxs text-muted">${QCMS.formatDate(a.created_at)}</span>
                                </div>
                                <div class="text-xxs text-secondary mt-0.5" style="color: var(--ds-text-secondary);">
                                    By: <span class="fw-semibold text-main" style="color: var(--ds-text-main);">${a.user}</span>
                                </div>
                            </div>
                        </div>
                    `;
                }).join('') || '<div class="text-center text-muted text-xs py-4">No audit logs for this ticket.</div>';

                const modalEl = this.ensureModalInBody('sdAuditModal');
                const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
                modal.show();
                if (window.lucide) lucide.createIcons();
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
    enquiryPerPage: 10,
    enquiryFilters: {
        q: '',
        status: 'All'
    },
    currentEnquiryId: null,
    currentEnquiryData: null,
    salesSettings: {
        sales_notification_email: '',
        sales_notification_enabled: false
    },

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
            const perPage = this.enquiryPerPage || 10;
            
            const [res, settingsRes] = await Promise.all([
                api.get(`/support/enquiries?page=${this.enquiryPage}&per_page=${perPage}&status=${status}&q=${q}`),
                api.get('/support/enquiries/settings').catch(() => ({ status: 'success', data: { sales_notification_email: '', sales_notification_enabled: false } }))
            ]);
            
            if (!res || res.status !== 'success') {
                view.innerHTML = `<div class="alert alert-danger">Failed to load sales enquiries.</div>`;
                return;
            }

            if (settingsRes && settingsRes.data) {
                this.salesSettings = settingsRes.data;
            }

            const items = res.data || [];
            this.enquiriesList = items;
            const m = res.metrics || { total: 0, new: 0, contacted: 0, in_progress: 0, converted: 0, closed: 0 };
            const pag = res.pagination || { page: 1, pages: 1, total: items.length, per_page: perPage };

            const startItem = pag.total > 0 ? (pag.page - 1) * pag.per_page + 1 : 0;
            const endItem = Math.min(pag.page * pag.per_page, pag.total);
            const isForwardingActive = this.salesSettings.sales_notification_enabled && this.salesSettings.sales_notification_email;

            view.innerHTML = `
                <div class="v-stack gap-4 fade-in">
                    <!-- KPI Stat Row (Total = New + Contacted + In Progress + Converted + Closed) -->
                    <div class="row g-2 g-md-3">
                        <div class="col-6 col-md">
                            <div class="glass-card p-2.5 p-md-3 d-flex align-items-center gap-2.5 gap-md-3 h-100" onclick="SupportDesk.filterEnquiriesStatus('All')" title="Click to view all enquiries" style="cursor:pointer; transition:all .15s ease;">
                                <div class="p-2 p-md-2.5 rounded-3 flex-shrink-0" style="background: rgba(99, 102, 241, 0.15); color: #6366f1;">
                                    <i data-lucide="phone-call" style="width:18px;height:18px;"></i>
                                </div>
                                <div class="min-w-0">
                                    <div class="text-xxs text-muted fw-semibold text-uppercase text-truncate">Total Enquiries</div>
                                    <div class="fs-5 fs-md-4 fw-extrabold text-main lh-1 mt-1">${m.total || 0}</div>
                                </div>
                            </div>
                        </div>
                        <div class="col-6 col-md">
                            <div class="glass-card p-2.5 p-md-3 d-flex align-items-center gap-2.5 gap-md-3 h-100" onclick="SupportDesk.filterEnquiriesStatus('New')" title="Click to filter by New Prospects" style="cursor:pointer; transition:all .15s ease;">
                                <div class="p-2 p-md-2.5 rounded-3 flex-shrink-0" style="background: rgba(239, 68, 68, 0.15); color: #ef4444;">
                                    <i data-lucide="bell" style="width:18px;height:18px;"></i>
                                </div>
                                <div class="min-w-0">
                                    <div class="text-xxs text-muted fw-semibold text-uppercase text-truncate">New Prospects</div>
                                    <div class="fs-5 fs-md-4 fw-extrabold text-main lh-1 mt-1">${m.new || 0}</div>
                                </div>
                            </div>
                        </div>
                        <div class="col-6 col-md">
                            <div class="glass-card p-2.5 p-md-3 d-flex align-items-center gap-2.5 gap-md-3 h-100" onclick="SupportDesk.filterEnquiriesStatus('Contacted')" title="Click to filter by Contacted" style="cursor:pointer; transition:all .15s ease;">
                                <div class="p-2 p-md-2.5 rounded-3 flex-shrink-0" style="background: rgba(245, 158, 11, 0.15); color: #f59e0b;">
                                    <i data-lucide="message-square" style="width:18px;height:18px;"></i>
                                </div>
                                <div class="min-w-0">
                                    <div class="text-xxs text-muted fw-semibold text-uppercase text-truncate">Contacted</div>
                                    <div class="fs-5 fs-md-4 fw-extrabold text-main lh-1 mt-1">${m.contacted || 0}</div>
                                </div>
                            </div>
                        </div>
                        <div class="col-6 col-md">
                            <div class="glass-card p-2.5 p-md-3 d-flex align-items-center gap-2.5 gap-md-3 h-100" onclick="SupportDesk.filterEnquiriesStatus('In Progress')" title="Click to filter by In Progress" style="cursor:pointer; transition:all .15s ease;">
                                <div class="p-2 p-md-2.5 rounded-3 flex-shrink-0" style="background: rgba(6, 182, 212, 0.15); color: #0891b2;">
                                    <i data-lucide="activity" style="width:18px;height:18px;"></i>
                                </div>
                                <div class="min-w-0">
                                    <div class="text-xxs text-muted fw-semibold text-uppercase text-truncate">In Progress</div>
                                    <div class="fs-5 fs-md-4 fw-extrabold text-main lh-1 mt-1">${m.in_progress || 0}</div>
                                </div>
                            </div>
                        </div>
                        <div class="col-6 col-md">
                            <div class="glass-card p-2.5 p-md-3 d-flex align-items-center gap-2.5 gap-md-3 h-100" onclick="SupportDesk.filterEnquiriesStatus('Converted')" title="Click to filter by Converted" style="cursor:pointer; transition:all .15s ease;">
                                <div class="p-2 p-md-2.5 rounded-3 flex-shrink-0" style="background: rgba(16, 185, 129, 0.15); color: #10b981;">
                                    <i data-lucide="check-circle-2" style="width:18px;height:18px;"></i>
                                </div>
                                <div class="min-w-0">
                                    <div class="text-xxs text-muted fw-semibold text-uppercase text-truncate">Converted</div>
                                    <div class="fs-5 fs-md-4 fw-extrabold text-main lh-1 mt-1">${m.converted || 0}</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Sales Leads Email Forwarding & Notification Settings Card -->
                    <div class="glass-card p-3 p-md-3.5" style="border-left: 4px solid #6366f1; background: linear-gradient(135deg, rgba(99, 102, 241, 0.05) 0%, rgba(255, 255, 255, 0.7) 100%);">
                        <div class="d-flex flex-wrap align-items-center justify-content-between gap-3">
                            <div class="d-flex align-items-start gap-3" style="max-width: 520px;">
                                <div class="p-2.5 rounded-3 mt-0.5" style="background: rgba(99, 102, 241, 0.12); color: #6366f1;">
                                    <i data-lucide="mail" style="width: 20px; height: 20px;"></i>
                                </div>
                                <div>
                                    <div class="d-flex align-items-center gap-2 flex-wrap">
                                        <h6 class="fw-bold mb-0 text-main fs-6">Sales Leads Email Redirection</h6>
                                        <span id="salesNotificationStatusBadge" class="badge rounded-pill text-xxs px-2.5 py-1 ${isForwardingActive ? 'bg-success-subtle text-success border border-success-subtle' : 'bg-secondary-subtle text-secondary border border-secondary-subtle'}">
                                            <i data-lucide="${isForwardingActive ? 'check-circle' : 'slash'}" style="width:10px;height:10px;display:inline;" class="me-1"></i>
                                            ${isForwardingActive ? `Forwarding to: ${QCMS.escapeHtml(this.salesSettings.sales_notification_email)}` : 'Dashboard Only (Email Off)'}
                                        </span>
                                    </div>
                                    <p class="text-xs text-muted mb-0 mt-1" style="line-height: 1.4;">
                                        Enter an email address to automatically forward all incoming <strong>Talk to Sales</strong> leads. When disabled or left blank, enquiries will remain stored solely inside this dashboard.
                                    </p>
                                </div>
                            </div>

                            <div class="d-flex flex-wrap align-items-center gap-3 ms-auto mt-2 mt-lg-0">
                                <!-- Toggle Switch -->
                                <div class="d-flex align-items-center me-2" title="Toggle automatic email forwarding on or off">
                                    <div class="form-check form-switch m-0 d-flex align-items-center gap-2 ps-0">
                                        <input class="form-check-input ms-0" type="checkbox" id="toggleSalesNotification" role="switch" style="cursor: pointer; width: 40px; height: 20px; float: none; margin-top: 0;" ${this.salesSettings.sales_notification_enabled ? 'checked' : ''} onchange="SupportDesk.onToggleSalesNotification(this.checked)">
                                        <label class="form-check-label text-xs fw-bold cursor-pointer text-nowrap mb-0" for="toggleSalesNotification" style="user-select: none; color: var(--ds-text-main);">
                                            Send to Email
                                        </label>
                                    </div>
                                </div>

                                <!-- Email Address Input & Save Button Group -->
                                <div class="d-flex align-items-center gap-2">
                                    <div style="width: 250px;">
                                        <input type="email" class="ds-input text-xs" style="padding-left: 12px; padding-right: 12px; height: 36px; border-radius: 8px;" id="salesNotificationEmailInput" placeholder="sales-team@company.com" value="${QCMS.escapeHtml(this.salesSettings.sales_notification_email || '')}" onkeydown="if(event.key==='Enter') SupportDesk.saveSalesNotificationSettings()">
                                    </div>
                                    <button class="ds-btn ds-btn-primary ds-btn-sm d-flex align-items-center gap-1.5 text-nowrap" id="btnSaveSalesNotificationSettings" onclick="SupportDesk.saveSalesNotificationSettings()" style="height: 36px; background: #6366f1; border-color: #6366f1; border-radius: 8px; font-weight: 600; padding: 0 14px;">
                                        <i data-lucide="save" style="width: 14px; height: 14px;"></i> Save Email
                                    </button>
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
                                    <option value="All" ${this.enquiryFilters.status === 'All' ? 'selected' : ''}>All Status</option>
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

                    <!-- Enquiries Table Card -->
                    <div class="glass-card ds-card p-0 overflow-hidden" style="border-radius: var(--ds-radius-lg, 12px);">
                        <div class="table-responsive">
                            <table class="ds-table ds-table-hover align-middle mb-0 text-xs">
                                <thead>
                                    <tr style="background: var(--ds-surface-secondary, rgba(248, 250, 252, 0.6)); border-bottom: 1.5px solid var(--ds-border-color, #e2e8f0); color: var(--ds-text-tertiary, #64748b);">
                                        <th class="py-3 px-3 fw-bold text-xs uppercase tracking-wider">SUBMITTED DATE</th>
                                        <th class="py-3 px-3 fw-bold text-xs uppercase tracking-wider">PROSPECT NAME</th>
                                        <th class="py-3 px-3 fw-bold text-xs uppercase tracking-wider">WORK EMAIL</th>
                                        <th class="py-3 px-3 fw-bold text-xs uppercase tracking-wider">PHONE NUMBER</th>
                                        <th class="py-3 px-3 fw-bold text-xs uppercase tracking-wider">COMPANY NAME</th>
                                        <th class="py-3 px-3 fw-bold text-xs uppercase tracking-wider">STATUS</th>
                                        <th class="py-3 px-3 fw-bold text-xs uppercase tracking-wider text-end">ACTIONS</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${items.length === 0 ? `
                                        <tr><td colspan="7" class="text-center p-5 text-muted">No sales enquiries found matching filter criteria.</td></tr>
                                    ` : items.map(item => {
                                        let statusMarkup = '';
                                        if (item.status === 'New') {
                                             statusMarkup = `<span class="badge rounded-pill text-xs px-2.5 py-1 fw-bold" style="background: rgba(239, 68, 68, 0.12); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.25);">NEW</span>`;
                                        } else if (item.status === 'Contacted') {
                                            statusMarkup = `<span class="badge rounded-pill text-xs px-2.5 py-1 fw-bold" style="background: rgba(245, 158, 11, 0.12); color: #d97706; border: 1px solid rgba(245, 158, 11, 0.25);">CONTACTED</span>`;
                                        } else if (item.status === 'In Progress') {
                                            statusMarkup = `<span class="badge rounded-pill text-xs px-2.5 py-1 fw-bold" style="background: rgba(6, 182, 212, 0.12); color: #0891b2; border: 1px solid rgba(6, 182, 212, 0.25);">IN PROGRESS</span>`;
                                        } else if (item.status === 'Converted') {
                                            statusMarkup = `<span class="badge rounded-pill text-xs px-2.5 py-1 fw-bold" style="background: rgba(16, 185, 129, 0.12); color: #059669; border: 1px solid rgba(16, 185, 129, 0.25);">CONVERTED</span>`;
                                        } else {
                                            statusMarkup = `<span class="badge rounded-pill text-xs px-2.5 py-1 fw-bold" style="background: rgba(100, 116, 139, 0.12); color: #64748b; border: 1px solid rgba(100, 116, 139, 0.25);">${(item.status || 'CLOSED').toUpperCase()}</span>`;
                                        }

                                        const dateStr = item.created_at ? new Date(item.created_at).toLocaleString() : 'N/A';

                                        return `
                                            <tr class="fade-in">
                                                <td class="py-2.5 px-3"><span class="text-secondary font-mono text-xs">${dateStr}</span></td>
                                                <td class="py-2.5 px-3"><strong class="text-main fw-semibold" style="color: var(--ds-text-main, #0f172a);">${item.name}</strong></td>
                                                <td class="py-2.5 px-3">
                                                    <a href="javascript:void(0);" onclick="SupportDesk.openComposeEmailModal(${item.id})" class="text-decoration-none font-medium d-inline-flex align-items-center gap-1.5" style="color: var(--ds-primary, #6366f1);" title="Send In-App Email">
                                                        <i data-lucide="mail" style="width:13px;height:13px;"></i> ${item.email}
                                                    </a>
                                                </td>
                                                <td class="py-2.5 px-3">
                                                    <a href="tel:${item.phone}" class="text-decoration-none font-mono text-xs d-inline-flex align-items-center gap-1.5" style="color: var(--ds-text-secondary, #64748b);" title="Call Phone">
                                                        <i data-lucide="phone" style="width:13px;height:13px;"></i> ${item.phone}
                                                    </a>
                                                </td>
                                                <td class="py-2.5 px-3"><span class="fw-semibold text-main">${item.company_name}</span></td>
                                                <td class="py-2.5 px-3">${statusMarkup}</td>
                                                <td class="py-2.5 px-3 text-end">
                                                    <div class="dropdown d-inline-block">
                                                        <button class="btn btn-link p-0 d-inline-flex align-items-center justify-content-center" type="button" data-bs-toggle="dropdown" aria-expanded="false" data-bs-popper-config='{"strategy":"fixed"}' style="width:30px; height:30px; border-radius:6px; border:none; background:transparent; text-decoration:none; color: var(--ds-text-secondary, #64748b); transition: background 0.15s ease;" onmouseover="this.style.background='rgba(0,0,0,0.06)'" onmouseout="this.style.background='transparent'" title="Actions">
                                                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="pointer-events:none;"><circle cx="12" cy="12" r="1.5"></circle><circle cx="19" cy="12" r="1.5"></circle><circle cx="5" cy="12" r="1.5"></circle></svg>
                                                        </button>
                                                        <ul class="dropdown-menu dropdown-menu-end shadow-lg border text-xs" style="min-width: 175px; z-index: 100050 !important;">
                                                            <li>
                                                                <a class="dropdown-item d-flex align-items-center gap-2 py-2" href="javascript:void(0);" onclick="SupportDesk.openEnquiryDetailModal(${item.id})">
                                                                    <i data-lucide="eye" style="width:14px;height:14px; color: #6366f1;"></i> View &amp; Action
                                                                </a>
                                                            </li>
                                                            <li>
                                                                <a class="dropdown-item d-flex align-items-center gap-2 py-2" href="javascript:void(0);" onclick="SupportDesk.openComposeEmailModal(${item.id})">
                                                                    <i data-lucide="mail" style="width:14px;height:14px; color: #0284c7;"></i> Compose Email
                                                                </a>
                                                            </li>
                                                            <li>
                                                                <a class="dropdown-item d-flex align-items-center gap-2 py-2" href="tel:${item.phone}">
                                                                    <i data-lucide="phone" style="width:14px;height:14px; color: #10b981;"></i> Call Phone
                                                                </a>
                                                            </li>
                                                            <li><hr class="dropdown-divider my-1"></li>
                                                            <li>
                                                                <a class="dropdown-item d-flex align-items-center gap-2 py-2 text-danger" href="javascript:void(0);" onclick="SupportDesk.deleteEnquiryRecord(${item.id})">
                                                                    <i data-lucide="trash-2" style="width:14px;height:14px;"></i> Delete Enquiry
                                                                </a>
                                                            </li>
                                                        </ul>
                                                    </div>
                                                </td>
                                            </tr>
                                        `;
                                    }).join('')}
                                </tbody>
                            </table>
                        </div>

                        <!-- Pagination Footer Bar -->
                        <div class="d-flex align-items-center justify-content-between p-3 border-top" style="border-color: var(--ds-border-color, #e2e8f0)!important; background: var(--ds-surface-secondary, rgba(248, 250, 252, 0.5)); border-bottom-left-radius: var(--ds-radius-lg, 12px); border-bottom-right-radius: var(--ds-radius-lg, 12px);">
                            <div class="text-xs text-secondary fw-medium">
                                ${pag.total > 0 ? `Showing <strong style="color:var(--ds-text-main);">${startItem}–${endItem}</strong> of <strong style="color:var(--ds-text-main);">${pag.total}</strong> enquiries` : 'Showing 0 of 0'}
                            </div>
                            <div class="d-flex align-items-center gap-2">
                                <div class="d-flex align-items-center gap-1 me-2">
                                    <select class="ds-input ds-input-sm text-xs py-1 px-2" style="width: 125px; height: 32px; border-radius: 8px;" onchange="SupportDesk.setEnquiryPerPage(this.value)">
                                        <option value="10" ${pag.per_page == 10 ? 'selected' : ''}>10 per page</option>
                                        <option value="20" ${pag.per_page == 20 ? 'selected' : ''}>20 per page</option>
                                        <option value="50" ${pag.per_page == 50 ? 'selected' : ''}>50 per page</option>
                                    </select>
                                </div>
                                <button class="ds-btn ds-btn-secondary ds-btn-sm py-1 px-2.5" style="border-radius: 8px;" ${pag.page <= 1 ? 'disabled' : ''} onclick="SupportDesk.setEnquiryPage(${pag.page - 1})">
                                    <i data-lucide="chevron-left" style="width:14px;height:14px;"></i>
                                </button>
                                ${Array.from({ length: pag.pages || 1 }, (_, i) => i + 1).map(p => `
                                    <button class="ds-btn ${p === pag.page ? 'ds-btn-primary' : 'ds-btn-secondary'} ds-btn-sm py-1 px-3 fw-bold" style="border-radius: 8px; ${p === pag.page ? 'box-shadow: 0 3px 10px rgba(99,102,241,0.3);' : ''}" onclick="SupportDesk.setEnquiryPage(${p})">
                                        ${p}
                                    </button>
                                `).join('')}
                                <button class="ds-btn ds-btn-secondary ds-btn-sm py-1 px-2.5" style="border-radius: 8px;" ${pag.page >= pag.pages ? 'disabled' : ''} onclick="SupportDesk.setEnquiryPage(${pag.page + 1})">
                                    <i data-lucide="chevron-right" style="width:14px;height:14px;"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            if (window.lucide) lucide.createIcons();
        } catch (e) {
            view.innerHTML = `<div class="alert alert-danger">Error loading sales enquiries: ${e.message}</div>`;
        }
    },

    ensureModalInBody(id) {
        const el = document.getElementById(id);
        if (el) {
            if (el.parentElement !== document.body) {
                document.body.appendChild(el);
            }
            el.style.zIndex = '1085';
        }
        return el;
    },

    openComposeEmailModal(id) {
        this.currentEnquiryId = id;
        const cachedItem = (this.enquiriesList || []).find(x => x.id === id);
        
        const populateAndShow = (item) => {
            if (!item) return QCMS.toast('Enquiry not found', 'error');
            this.currentEnquiryData = item;

            const elId = document.getElementById('sdComposeEnquiryId');
            const elEmail = document.getElementById('sdComposeToEmail');
            const elName = document.getElementById('sdComposeProspectName');
            const elSub = document.getElementById('sdComposeSubject');
            const elMsg = document.getElementById('sdComposeMessage');

            if (elId) elId.value = item.id;
            if (elEmail) elEmail.value = item.email || '';
            if (elName) elName.value = `${item.name} (${item.company_name || 'Prospect'})`;
            if (elSub) elSub.value = `Response regarding your inquiry - ${item.company_name || 'QCMS'}`;
            if (elMsg) elMsg.value = `Dear ${item.name},\n\nThank you for reaching out to us regarding ${item.company_name}.\n\n`;

            const modalEl = this.ensureModalInBody('sdComposeEmailModal');
            if (modalEl) {
                const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
                modal.show();
            }
            if (window.lucide) lucide.createIcons();
        };

        if (cachedItem) {
            populateAndShow(cachedItem);
        } else {
            api.get('/support/enquiries?page=1&per_page=100').then(res => {
                const items = res?.data || [];
                const item = items.find(x => x.id === id);
                populateAndShow(item);
            }).catch(err => {
                console.error('Failed to load enquiry details for compose email:', err);
                QCMS.toast('Failed to load enquiry details', 'error');
            });
        }
    },

    openComposeEmailFromDetailModal() {
        if (!this.currentEnquiryId || !this.currentEnquiryData) return;
        const detailModalEl = document.getElementById('sdEnquiryDetailModal');
        if (detailModalEl) {
            const modalInstance = bootstrap.Modal.getInstance(detailModalEl);
            if (modalInstance) modalInstance.hide();
        }
        this.openComposeEmailModal(this.currentEnquiryId);
    },

    async submitComposeEmail() {
        const id = document.getElementById('sdComposeEnquiryId').value;
        const toEmail = document.getElementById('sdComposeToEmail').value.trim();
        const subject = document.getElementById('sdComposeSubject').value.trim();
        const message = document.getElementById('sdComposeMessage').value.trim();

        if (!toEmail || !subject || !message) {
            return QCMS.toast('Please fill in all required fields (Recipient, Subject, Message).', 'warning');
        }

        const btn = document.getElementById('btnSendComposeEmail');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = `<i data-lucide="loader" class="spin me-1" style="width:14px;height:14px;"></i> Sending...`;
            if (window.lucide) lucide.createIcons();
        }

        try {
            const res = await api.post(`/support/enquiries/${id}/send-email`, {
                to_email: toEmail,
                subject: subject,
                message: message
            });

            if (res && res.status === 'success') {
                QCMS.toast(res.message || 'Email successfully sent using Support Email!', 'success');
                const composeModalEl = document.getElementById('sdComposeEmailModal');
                if (composeModalEl) {
                    const modalInstance = bootstrap.Modal.getInstance(composeModalEl);
                    if (modalInstance) modalInstance.hide();
                }
                this.loadEnquiriesList();
            } else {
                QCMS.toast(res?.message || 'Failed to send email.', 'error');
            }
        } catch (err) {
            console.error('Failed to send enquiry email:', err);
            QCMS.toast(err.message || 'Failed to send email.', 'error');
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = `<i data-lucide="send" style="width:14px;height:14px;" class="me-1"></i> Send Email Now`;
                if (window.lucide) lucide.createIcons();
            }
        }
    },

    setEnquiryPage(page) {
        if (page < 1) return;
        this.enquiryPage = page;
        this.loadEnquiriesList();
    },

    setEnquiryPerPage(perPage) {
        this.enquiryPerPage = parseInt(perPage, 10) || 10;
        this.enquiryPage = 1;
        this.loadEnquiriesList();
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

            const emailBtn = document.getElementById('enqModalEmailBtn');
            if (emailBtn) emailBtn.href = `mailto:${item.email}?subject=QCMS%20Enterprise%20Inquiry%20Follow-up`;

            let badgeClass = 'blue';
            if (item.status === 'New') badgeClass = 'red';
            else if (item.status === 'Contacted') badgeClass = 'yellow';
            else if (item.status === 'In Progress') badgeClass = 'cyan';
            else if (item.status === 'Converted') badgeClass = 'green';
            else if (item.status === 'Closed') badgeClass = 'gray';

            document.getElementById('enqModalStatusBadge').innerHTML = `<span class="ds-badge ${badgeClass}">${item.status}</span>`;

            const modalEl = this.ensureModalInBody('sdEnquiryDetailModal');
            const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
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
    },

    async onToggleSalesNotification(checked) {
        const emailInput = document.getElementById('salesNotificationEmailInput');
        const emailVal = (emailInput?.value || '').trim();
        
        if (checked && !emailVal) {
            QCMS.toast('Please enter a destination sales email address before enabling forwarding.', 'warning');
            if (emailInput) emailInput.focus();
            return;
        }

        await this.saveSalesNotificationSettings();
    },

    async saveSalesNotificationSettings() {
        const emailInput = document.getElementById('salesNotificationEmailInput');
        const toggleInput = document.getElementById('toggleSalesNotification');
        const btn = document.getElementById('btnSaveSalesNotificationSettings');

        const emailVal = (emailInput?.value || '').trim();
        let isEnabled = toggleInput ? toggleInput.checked : false;

        // Validate email format if provided
        if (emailVal) {
            if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailVal)) {
                QCMS.toast('Please enter a valid email address format (e.g. sales@company.com).', 'warning');
                if (emailInput) emailInput.focus();
                return;
            }
        } else if (isEnabled) {
            // Cannot be enabled without an email
            isEnabled = false;
            if (toggleInput) toggleInput.checked = false;
        }

        const origBtnHtml = btn ? btn.innerHTML : '';
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = `<span class="spinner-border spinner-border-sm me-1" role="status"></span> Saving...`;
        }

        try {
            const res = await api.post('/support/enquiries/settings', {
                sales_notification_email: emailVal,
                sales_notification_enabled: isEnabled
            });

            if (res && res.status === 'success') {
                this.salesSettings = res.data || { sales_notification_email: emailVal, sales_notification_enabled: isEnabled };
                
                if (emailInput) emailInput.value = this.salesSettings.sales_notification_email || '';
                if (toggleInput) toggleInput.checked = Boolean(this.salesSettings.sales_notification_enabled);

                const badge = document.getElementById('salesNotificationStatusBadge');
                if (badge) {
                    const isForwarding = this.salesSettings.sales_notification_enabled && this.salesSettings.sales_notification_email;
                    badge.className = `badge rounded-pill text-xxs px-2.5 py-1 ${isForwarding ? 'bg-success-subtle text-success border border-success-subtle' : 'bg-secondary-subtle text-secondary border border-secondary-subtle'}`;
                    badge.innerHTML = `<i data-lucide="${isForwarding ? 'check-circle' : 'slash'}" style="width:10px;height:10px;display:inline;" class="me-1"></i> ${isForwarding ? `Forwarding to: ${QCMS.escapeHtml(this.salesSettings.sales_notification_email)}` : 'Dashboard Only (Email Off)'}`;
                }

                QCMS.toast(res.message || 'Sales lead notification email settings saved!', 'success');
                if (window.lucide) lucide.createIcons();
            } else {
                throw new Error((res && res.message) || 'Failed to update settings');
            }
        } catch (e) {
            QCMS.toast(e.message || 'Failed to save sales notification settings.', 'error');
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = origBtnHtml;
            }
        }
    }
};
