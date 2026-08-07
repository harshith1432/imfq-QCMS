/**
 * QCMS Enterprise OS - Announcements Module
 * Reusable component for platform-wide and org-scoped communication governance.
 */

const AnnouncementsModule = {
    containerId: null,
    currentTab: 'dashboard', // dashboard, list, wizard, kb, ai
    currentPage: 1,
    perPage: 20,
    sortBy: 'created_at',
    sortOrder: 'desc',
    searchQuery: '',
    filters: {
        status: '',
        priority: '',
        category: '',
        date_preset: ''
    },
    
    // Wizard state
    wizardStep: 1,
    wizardData: {
        title: '',
        summary: '',
        body: '',
        category: 'General',
        priority: 'Medium',
        tags: [],
        audience_type: 'all',
        audience: [],
        channels: { in_app: true, email: false, sms: false, push: false },
        publish_at: '',
        expires_at: '',
        timezone: 'UTC',
        action: 'draft'
    },

    CRIT_SUGGESTIONS: {
        'plan': [
            { value: 'Enterprise', label: 'Enterprise Plan', desc: 'Unlimited Users & High Performance' },
            { value: 'Professional', label: 'Professional Plan', desc: '50 Users Limit' },
            { value: 'Starter', label: 'Starter Plan', desc: '10 Users Limit' },
            { value: 'Enterprise Test Matrix Plan', label: 'Enterprise Test Matrix Plan', desc: 'Custom Sandbox Tier' },
            { value: 'Custom', label: 'Custom Contract', desc: 'Tailored Enterprise Plan' }
        ],
        'role': [
            { value: 'Admin', label: 'Admin (Tenant Leader)', desc: 'Organization Admin Control' },
            { value: 'SuperAdmin', label: 'Super Admin', desc: 'Platform Governance & Operations' },
            { value: 'Reviewer', label: 'Quality Reviewer', desc: 'Gatekeeper Approval Permissions' },
            { value: 'Facilitator', label: 'Methodology Facilitator', desc: 'RCA & Quality Guidance' },
            { value: 'Team Leader', label: 'Project Team Leader', desc: 'Project Owner & Lead' },
            { value: 'Team Member', label: 'Team Contributor', desc: 'Execution & Data Input' }
        ],
        'org': [
            { value: '1', label: 'Org #1 — Quality Circle Inc', desc: 'ID: 1 · Active Enterprise Tier' },
            { value: '2', label: 'Org #2 — ACME Enterprise', desc: 'ID: 2 · Professional Tier' },
            { value: '3', label: 'Org #3 — Global QC Systems', desc: 'ID: 3 · Starter Tier' }
        ],
        'country': [
            { value: 'IN', label: 'IN — India', desc: 'Asia-Pacific Region' },
            { value: 'US', label: 'US — United States', desc: 'North America Region' },
            { value: 'UK', label: 'UK — United Kingdom', desc: 'Europe Region' },
            { value: 'DE', label: 'DE — Germany', desc: 'Europe Region' },
            { value: 'FR', label: 'FR — France', desc: 'Europe Region' },
            { value: 'ES', label: 'ES — Spain', desc: 'Europe Region' },
            { value: 'CA', label: 'CA — Canada', desc: 'North America Region' },
            { value: 'AU', label: 'AU — Australia', desc: 'Asia-Pacific Region' },
            { value: 'SG', label: 'SG — Singapore', desc: 'Asia-Pacific Region' },
            { value: 'AE', label: 'AE — UAE', desc: 'Middle East Region' }
        ],
        'status': [
            { value: 'Active', label: 'Active Subscription', desc: 'Running active accounts' },
            { value: 'Trial', label: 'Trial Period', desc: 'Orgs currently in 14-day trial' },
            { value: 'Suspended', label: 'Suspended Account', desc: 'Locked organization accounts' },
            { value: 'Expired', label: 'Expired Subscription', desc: 'Unpaid or lapsed subscriptions' }
        ]
    },

    async init(containerId) {
        this.containerId = containerId;
        this.renderShell();
        this.switchTab(this.currentTab);
    },

    renderShell() {
        const container = document.getElementById(this.containerId);
        if (!container) return;

        container.innerHTML = `
            <div class="announcements-module d-flex flex-column gap-4 fade-in px-3">
                <!-- Navigation Tabs & Actions -->
                <div class="d-flex flex-wrap align-items-center justify-content-between gap-3 border-bottom pb-3" style="border-color:var(--ds-border-color)!important;">
                    <div class="h-stack gap-1 bg-surface-secondary p-1 rounded-3 border" style="border-color:var(--ds-border-color)!important; background:rgba(255,255,255,0.02);">
                        <button class="ds-btn ds-btn-sm rounded-2 px-3 sd-tab-btn active" id="tab-dashboard" onclick="AnnouncementsModule.switchTab('dashboard')">
                            <i data-lucide="layout-dashboard" class="me-1.5" style="width:14px;height:14px;"></i> Dashboard
                        </button>
                        <button class="ds-btn ds-btn-sm rounded-2 px-3 sd-tab-btn" id="tab-list" onclick="AnnouncementsModule.switchTab('list')">
                            <i data-lucide="list" class="me-1.5" style="width:14px;height:14px;"></i> Message Registry
                        </button>
                        <button class="ds-btn ds-btn-sm rounded-2 px-3 sd-tab-btn" id="tab-wizard" onclick="AnnouncementsModule.openWizard()">
                            <i data-lucide="plus-circle" class="me-1.5" style="width:14px;height:14px;"></i> Compose Broadcast
                        </button>
                    </div>
                </div>

                <!-- Dynamic View Content Container -->
                <div id="announcementContentArea" class="fade-in"></div>
            </div>

            <!-- 5-Step Creation Wizard Modal -->
            <div class="modal fade" id="annWizardModal" tabindex="-1" aria-hidden="true" data-bs-backdrop="static">
                <div class="modal-dialog modal-lg modal-dialog-centered">
                    <div class="modal-content" style="background:var(--ds-bg-card); border: 1px solid var(--ds-border-color); border-radius: var(--ds-radius-lg);">
                        <div class="modal-header" style="border-bottom:1px solid var(--ds-border-color);">
                            <div class="h-stack gap-2">
                                <i data-lucide="megaphone" class="text-primary" style="width:20px;height:20px;"></i>
                                <h5 class="modal-title fw-bold" id="annWizardTitle">Compose New Broadcast</h5>
                            </div>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        
                        <!-- Step Indicator Progress Bar -->
                        <div class="px-4 pt-3">
                            <div class="d-flex justify-content-between text-xs text-muted mb-2">
                                <span class="step-lbl-1 fw-bold text-primary">1. Basic Info</span>
                                <span class="step-lbl-2">2. Audience Targeting</span>
                                <span class="step-lbl-3">3. Channels</span>
                                <span class="step-lbl-4">4. Scheduling</span>
                                <span class="step-lbl-5">5. Review</span>
                            </div>
                            <div class="progress" style="height: 6px; background:rgba(255,255,255,0.06);">
                                <div class="progress-bar progress-bar-striped progress-bar-animated bg-primary" id="wizardProgressBar" role="progressbar" style="width: 20%;" aria-valuenow="20" aria-valuemin="0" aria-valuemax="100"></div>
                            </div>
                        </div>

                        <div class="modal-body p-4" id="wizardBodyContent" style="max-height: 65vh; overflow-y: auto;">
                            <!-- Injected dynamically -->
                        </div>

                        <div class="modal-footer" style="border-top:1px solid var(--ds-border-color); background:rgba(0,0,0,0.1);">
                            <button class="ds-btn ds-btn-outline ds-btn-sm px-3" id="wizPrevBtn" onclick="AnnouncementsModule.prevStep()">Back</button>
                            <button class="ds-btn ds-btn-primary ds-btn-sm px-4" id="wizNextBtn" onclick="AnnouncementsModule.nextStep()">Next</button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Detail Slide-Over Modal / Side Sheet -->
            <div class="modal fade" id="annDetailModal" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog modal-xl modal-dialog-centered modal-dialog-scrollable">
                    <div class="modal-content" style="background:var(--ds-bg-card); border: 1px solid var(--ds-border-color); border-radius: var(--ds-radius-lg);">
                        <div class="modal-header" style="border-bottom:1px solid var(--ds-border-color);">
                            <div class="d-flex align-items-center gap-2">
                                <span class="ds-badge" id="detailStatusBadge" style="font-size:10px; padding:2px 6px;">Status</span>
                                <h5 class="modal-title fw-bold" id="detailTitle">Announcement Details</h5>
                            </div>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body p-4" id="detailModalBody">
                            <!-- Injected dynamically -->
                        </div>
                        <div class="modal-footer" style="border-top: 1px solid var(--ds-border-color);">
                            <button class="ds-btn ds-btn-secondary" data-bs-dismiss="modal">Close</button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Move modals to body to prevent stacking context/z-index issues
        const wizardModal = document.getElementById('annWizardModal');
        const detailModal = document.getElementById('annDetailModal');
        if (wizardModal) document.body.appendChild(wizardModal);
        if (detailModal) document.body.appendChild(detailModal);
    },

    async switchTab(tabId) {
        this.currentTab = tabId;
        
        // Update tab styling
        document.querySelectorAll('.sd-tab-btn').forEach(btn => btn.classList.remove('active'));
        const activeTabBtn = document.getElementById(`tab-${tabId}`);
        if (activeTabBtn) activeTabBtn.classList.add('active');

        const contentArea = document.getElementById('announcementContentArea');
        if (!contentArea) return;

        if (tabId === 'dashboard') {
            await this.renderDashboard(contentArea);
        } else if (tabId === 'list') {
            await this.renderList(contentArea);
        }

        if (window.lucide) lucide.createIcons();
    },

    // ─── Dashboard Tab ────────────────────────────────────────────────────────────

    async renderDashboard(container) {
        container.innerHTML = `<div class="text-center py-5"><div class="spinner-border text-primary" role="status"></div></div>`;
        try {
            const res = await api.get('/announcements/dashboard');
            if (res.status !== 'success') throw new Error('API failure');

            const kpis = res.data.kpis;
            const recent = res.data.recent;
            const byCategory = res.data.by_category;
            const byPriority = res.data.by_priority;

            const cardColors = {
                'active_announcements': '#10b981',
                'archived': '#6b7280',
                'ctr': '#2563eb',
                'drafts': '#8b5cf6',
                'expired': '#f59e0b',
                'failed_deliveries': '#ef4444',
                'high_priority': '#ef4444',
                'read_pct': '#10b981',
                'scheduled': '#3b82f6',
                'total_announcements': '#8b5cf6',
                'total_views': '#2563eb',
                'unread_pct': '#f59e0b'
            };

            let cardHtml = '';
            for (const [key, card] of Object.entries(kpis)) {
                if (['ctr', 'read_pct', 'unread_pct'].includes(key)) continue;
                const label = key.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
                const trendIcon = card.growth >= 0 ? 'trending-up' : 'trending-down';
                const trendClass = card.growth >= 0 ? 'text-success' : 'text-danger';
                const growthSign = card.growth > 0 ? '+' : '';
                const cardColor = cardColors[key] || '#6b7280';
                
                cardHtml += `
                    <div class="clickable transition" onclick="AnnouncementsModule.switchTab('list')" title="${card.tooltip || label}">
                        <div class="anc-kpi-card" title="${card.tooltip || label}">
                            <div class="kpi-icon" style="background: rgba(var(--ds-primary-rgb), 0.08);">
                                <i data-lucide="${card.icon}" style="width:11px; height:11px; color:${cardColor};"></i>
                            </div>
                            <div class="kpi-label" title="${card.tooltip || label}">${label}</div>
                            <div class="kpi-value">${card.value}${card.suffix || ''}</div>
                            <div class="kpi-accent" style="background:${cardColor};"></div>
                            ${card.growth !== 0 ? `
                                <div style="display:flex; align-items:center; gap:2px; font-size:9px; font-weight:bold; margin-top:2px;" class="${trendClass}">
                                    <i data-lucide="${trendIcon}" style="width:9px; height:9px;"></i>
                                    <span>${growthSign}${card.growth}%</span>
                                </div>` : `
                                <div style="height: 13px;"></div>
                            `}
                        </div>
                    </div>
                `;
            }

            container.innerHTML = `
                <div class="anc-kpi-grid">
                    ${cardHtml}
                </div>

                <div class="row g-4 mt-1 align-items-stretch">
                    <div class="col-lg-7 d-flex">
                        <div class="glass-card w-100 d-flex flex-column p-4" style="overflow: visible;">
                            <div class="d-flex justify-content-between align-items-center mb-3">
                                <h6 class="fw-bold mb-0 text-main">Active Broadcasts</h6>
                                <span class="text-xs text-secondary">Last 10 messages</span>
                            </div>
                            <div class="d-flex flex-column gap-3 flex-grow-1" id="dashRecentAnnouncements">
                                ${recent.map(a => `
                                    <div class="p-3 rounded-3 border d-flex justify-content-between align-items-start" style="border-color:var(--ds-border-color)!important; background:rgba(255,255,255,0.01); transition: all 0.2s ease-in-out;" onmouseover="this.style.background='rgba(255,255,255,0.03)'; this.style.transform='translateY(-2px)';" onmouseout="this.style.background='rgba(255,255,255,0.01)'; this.style.transform='none';">
                                        <div class="d-flex flex-column gap-1">
                                            <div class="d-flex align-items-center gap-2">
                                                <span class="badge ${a.priority === 'Critical' ? 'bg-danger' : a.priority === 'High' ? 'bg-warning' : 'bg-secondary'} bg-opacity-15 text-main text-xxs px-2 py-0.5">${a.priority}</span>
                                                <span class="text-xs text-secondary">${a.category}</span>
                                            </div>
                                            <a href="javascript:void(0)" class="fw-bold text-sm text-main text-decoration-none" style="transition: color 0.15s ease;" onmouseover="this.style.color='var(--ds-primary)'" onmouseout="this.style.color=''" onclick="AnnouncementsModule.openDetail(${a.id})">${a.title}</a>
                                            <p class="text-xs text-muted mb-0 text-truncate" style="max-width:450px;">${a.summary || ''}</p>
                                        </div>
                                        <div class="text-end text-xxs text-secondary">
                                            <div class="fw-semibold">${a.ann_number}</div>
                                            <div>Read: ${a.total_read} / ${a.total_delivered} (${a.read_pct}%)</div>
                                        </div>
                                    </div>
                                `).join('') || '<div class="text-center py-4 text-secondary text-xs">No active broadcasts.</div>'}
                            </div>
                        </div>
                    </div>
                    
                    <div class="col-lg-5 d-flex">
                        <div class="glass-card w-100 d-flex flex-column p-4" style="overflow: visible;">
                            <h6 class="fw-bold mb-3 text-main">Distribution Analysis</h6>
                            <div class="d-flex flex-column gap-4 flex-grow-1 justify-content-start">
                                <div>
                                    <span class="text-xs text-secondary d-block mb-2">Category distribution</span>
                                    <div class="d-flex flex-column gap-2">
                                        ${Object.entries(byCategory).map(([cat, val]) => `
                                            <div class="d-flex align-items-center gap-2">
                                                <span class="text-xs text-secondary text-truncate" style="width:100px;">${cat}</span>
                                                <div class="progress flex-grow-1" style="height:6px; background:rgba(255,255,255,0.06);">
                                                    <div class="progress-bar bg-primary" style="width:${(val / kpis.total_announcements.value * 100) || 0}%"></div>
                                                </div>
                                                <span class="text-xs fw-bold text-main text-end ms-2" style="min-width:30px;">${val}</span>
                                            </div>
                                        `).join('') || '<div class="text-center text-xs text-secondary py-2">No category data.</div>'}
                                    </div>
                                </div>
 
                                <div class="border-top pt-3" style="border-color:var(--ds-border-color)!important;">
                                    <span class="text-xs text-secondary d-block mb-2">Priority distribution</span>
                                    <div class="d-flex flex-column gap-2">
                                        ${Object.entries(byPriority).map(([pri, val]) => `
                                            <div class="d-flex align-items-center gap-2">
                                                <span class="text-xs text-secondary text-truncate" style="width:100px;">${pri}</span>
                                                <div class="progress flex-grow-1" style="height:6px; background:rgba(255,255,255,0.06);">
                                                    <div class="progress-bar bg-warning" style="width:${(val / kpis.total_announcements.value * 100) || 0}%"></div>
                                                </div>
                                                <span class="text-xs fw-bold text-main text-end ms-2" style="min-width:30px;">${val}</span>
                                            </div>
                                        `).join('') || '<div class="text-center text-xs text-secondary py-2">No priority data.</div>'}
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        } catch (e) {
            container.innerHTML = `<div class="alert alert-danger">Error loading announcements dashboard data.</div>`;
        }
    },

    // ─── Message Registry List Tab ────────────────────────────────────────────────

    async renderList(container) {
        container.innerHTML = `
            <!-- Filter & Search Bar -->
            <div class="glass-card mb-4">
                <div class="row g-3">
                    <div class="col-md-4">
                        <div class="position-relative">
                            <i data-lucide="search" class="position-absolute text-muted" style="left:12px; top:12px; width:16px;height:16px;"></i>
                            <input type="text" class="ds-input ps-5" placeholder="Search title, ID, categories..." id="annSearchInput" value="${this.searchQuery}" oninput="AnnouncementsModule.debouncedSearch(this.value)">
                        </div>
                    </div>
                    <div class="col-md-2">
                        <select class="ds-input ds-select py-1.5" id="filterStatus" onchange="AnnouncementsModule.setFilter('status', this.value)">
                            <option value="">All Status</option>
                            <option value="Draft" ${this.filters.status === 'Draft' ? 'selected' : ''}>Draft</option>
                            <option value="Scheduled" ${this.filters.status === 'Scheduled' ? 'selected' : ''}>Scheduled</option>
                            <option value="Published" ${this.filters.status === 'Published' ? 'selected' : ''}>Published</option>
                            <option value="Expired" ${this.filters.status === 'Expired' ? 'selected' : ''}>Expired</option>
                            <option value="Archived" ${this.filters.status === 'Archived' ? 'selected' : ''}>Archived</option>
                        </select>
                    </div>
                    <div class="col-md-2">
                        <select class="ds-input ds-select py-1.5" id="filterPriority" onchange="AnnouncementsModule.setFilter('priority', this.value)">
                            <option value="">All Priorities</option>
                            <option value="Low" ${this.filters.priority === 'Low' ? 'selected' : ''}>Low</option>
                            <option value="Medium" ${this.filters.priority === 'Medium' ? 'selected' : ''}>Medium</option>
                            <option value="High" ${this.filters.priority === 'High' ? 'selected' : ''}>High</option>
                            <option value="Critical" ${this.filters.priority === 'Critical' ? 'selected' : ''}>Critical</option>
                        </select>
                    </div>
                    <div class="col-md-2">
                        <select class="ds-input ds-select py-1.5" id="filterCategory" onchange="AnnouncementsModule.setFilter('category', this.value)">
                            <option value="">All Categories</option>
                            <option value="General" ${this.filters.category === 'General' ? 'selected' : ''}>General</option>
                            <option value="Maintenance" ${this.filters.category === 'Maintenance' ? 'selected' : ''}>Maintenance</option>
                            <option value="Security" ${this.filters.category === 'Security' ? 'selected' : ''}>Security</option>
                            <option value="Billing" ${this.filters.category === 'Billing' ? 'selected' : ''}>Billing</option>
                            <option value="Feature Release" ${this.filters.category === 'Feature Release' ? 'selected' : ''}>Feature Release</option>
                        </select>
                    </div>
                    <div class="col-md-2">
                        <button class="ds-btn ds-btn-outline w-100" onclick="AnnouncementsModule.resetFilters()">Reset Filters</button>
                    </div>
                </div>
            </div>

            <!-- Table Card -->
            <div class="glass-card p-0">
                <div class="table-responsive">
                    <table class="ds-table mb-0" style="font-size: 11.5px;">
                        <thead>
                            <tr style="font-size: 10.5px;">
                                <th>Announcement #</th>
                                <th>Title</th>
                                <th>Category</th>
                                <th>Priority</th>
                                <th>Audience</th>
                                <th>Status</th>
                                <th>Delivered</th>
                                <th>Read Rate</th>
                                <th>Created By</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody id="annRegistryTableBody">
                            <!-- Loaded via API -->
                        </tbody>
                    </table>
                </div>
                <div class="d-flex align-items-center justify-content-between p-3 border-top" style="border-color:var(--ds-border-color)!important;" id="annRegistryPagination">
                    <!-- Dynamic pagination footer -->
                </div>
            </div>
        `;
        await this.loadRegistry();
    },

    async loadRegistry() {
        const tbody = document.getElementById('annRegistryTableBody');
        if (!tbody) return;

        tbody.innerHTML = `<tr><td colspan="10" class="text-center py-4"><div class="spinner-border spinner-border-sm text-primary"></div></td></tr>`;

        let params = new URLSearchParams();
        params.append('page', this.currentPage);
        params.append('per_page', this.perPage);
        params.append('sort_by', this.sortBy);
        params.append('sort_order', this.sortOrder);
        if (this.searchQuery) params.append('q', this.searchQuery);
        for (const [k, v] of Object.entries(this.filters)) {
            if (v) params.append(k, v);
        }

        try {
            const res = await api.get(`/announcements/?${params.toString()}`);
            if (res.status !== 'success') throw new Error('API failed');

            const list = res.data;
            const meta = res.meta;

            tbody.innerHTML = list.map(a => `
                <tr class="align-middle">
                    <td><span class="ds-badge gray" style="font-family:monospace;">${a.ann_number}</span></td>
                    <td>
                        <div class="fw-semibold text-main text-truncate" style="max-width: 200px;" title="${a.title}">${a.title}</div>
                        <div class="text-xxs text-secondary">${a.summary ? a.summary.substring(0, 45) + '...' : '—'}</div>
                    </td>
                    <td><span class="text-xs">${a.category}</span></td>
                    <td>
                        <span class="ds-badge ${a.priority === 'Critical' ? 'red' : a.priority === 'High' ? 'orange' : 'gray'}" style="font-size:10px; padding:2px 6px;">
                            ${a.priority}
                        </span>
                    </td>
                    <td><span class="text-xs">${a.audience_type.toUpperCase()}</span></td>
                    <td>
                        <span class="ds-badge ${a.status === 'Published' ? 'green' : a.status === 'Scheduled' ? 'blue' : a.status === 'Expired' ? 'orange' : 'gray'}" style="font-size:10px; padding:2px 6px;">
                            ${a.status}
                        </span>
                    </td>
                    <td><span class="text-xs fw-semibold">${a.total_delivered}</span></td>
                    <td>
                        <div class="d-flex align-items-center gap-2">
                            <span class="text-xs fw-semibold">${a.read_pct}%</span>
                            <div class="progress" style="width: 50px; height: 4px; background:rgba(255,255,255,0.06);">
                                <div class="progress-bar bg-success" style="width: ${a.read_pct}%"></div>
                            </div>
                        </div>
                    </td>
                    <td>
                        <div class="fw-semibold text-xs">${a.created_by}</div>
                    </td>
                    <td>
                        <div class="h-stack gap-1">
                            <button class="ds-btn ds-btn-outline ds-btn-sm py-1 px-2" onclick="AnnouncementsModule.openDetail(${a.id})">Details</button>
                            <div class="dropdown">
                                <button class="ds-btn ds-btn-outline ds-btn-sm py-1 px-1.5" data-bs-toggle="dropdown" data-bs-boundary="viewport"><i data-lucide="more-vertical" style="width:14px;height:14px;"></i></button>
                                <ul class="dropdown-menu dropdown-menu-end shadow border" style="background:var(--ds-surface-secondary); border-color:var(--ds-border-color)!important;">
                                    ${a.status === 'Draft' || a.status === 'Scheduled' ? `<li><a class="dropdown-item text-xs text-success" href="javascript:void(0)" onclick="AnnouncementsModule.publishNow(${a.id})">Publish Now</a></li>` : ''}
                                    <li><a class="dropdown-item text-xs" href="javascript:void(0)" onclick="AnnouncementsModule.duplicateAnn(${a.id})">Duplicate</a></li>
                                    ${a.status !== 'Archived' ? `<li><a class="dropdown-item text-xs text-warning" href="javascript:void(0)" onclick="AnnouncementsModule.archiveAnn(${a.id})">Archive</a></li>` : ''}
                                    <li><hr class="dropdown-divider" style="border-color:var(--ds-border-color);"></li>
                                    <li><a class="dropdown-item text-xs text-danger" href="javascript:void(0)" onclick="AnnouncementsModule.deleteAnn(${a.id})">Delete</a></li>
                                </ul>
                            </div>
                        </div>
                    </td>
                </tr>
            `).join('') || '<tr><td colspan="10" class="text-center py-4 text-secondary">No broadcasts recorded.</td></tr>';

            const pagination = document.getElementById('annRegistryPagination');
            if (pagination && meta) {
                pagination.innerHTML = `
                    <div class="text-xs text-secondary">Showing page ${meta.page} of ${meta.pages} (${meta.total} items)</div>
                    <div class="h-stack gap-2">
                        <button class="ds-btn ds-btn-outline ds-btn-sm" ${meta.page === 1 ? 'disabled' : ''} onclick="AnnouncementsModule.setPage(${meta.page - 1})">Prev</button>
                        <button class="ds-btn ds-btn-outline ds-btn-sm" ${meta.page === meta.pages ? 'disabled' : ''} onclick="AnnouncementsModule.setPage(${meta.page + 1})">Next</button>
                    </div>
                `;
            }

            if (window.lucide) lucide.createIcons();

        } catch (e) {
            tbody.innerHTML = `<tr><td colspan="10" class="text-center text-danger py-4">Error fetching list.</td></tr>`;
        }
    },

    debouncedSearch(val) {
        if (this.searchTimeout) clearTimeout(this.searchTimeout);
        this.searchTimeout = setTimeout(() => {
            AnnouncementsModule.searchQuery = val.trim();
            AnnouncementsModule.currentPage = 1;
            AnnouncementsModule.loadRegistry();
        }, 350);
    },

    setFilter(key, val) {
        this.filters[key] = val;
        this.currentPage = 1;
        this.loadRegistry();
    },

    resetFilters() {
        this.searchQuery = '';
        const searchInput = document.getElementById('annSearchInput');
        if (searchInput) searchInput.value = '';
        this.filters = { status: '', priority: '', category: '', date_preset: '' };
        this.currentPage = 1;
        this.loadRegistry();
    },

    setPage(p) {
        this.currentPage = p;
        this.loadRegistry();
    },

    // ─── AI Tab ───────────────────────────────────────────────────────────────────

    async renderAI(container) {
        container.innerHTML = `<div class="text-center py-5"><div class="spinner-border text-primary" role="status"></div></div>`;
        try {
            const res = await api.get('/announcements/ai-insights');
            if (res.status !== 'success') throw new Error('AI API failure');
            
            const stats = res.data;

            container.innerHTML = `
                <div class="row g-4">
                    <div class="col-lg-4">
                        <div class="glass-card d-flex flex-column gap-3 text-center py-4">
                            <div class="mx-auto bg-primary bg-opacity-10 p-3 rounded-circle" style="width:60px;height:60px;">
                                <i data-lucide="sparkles" class="text-primary" style="width:28px;height:28px;"></i>
                            </div>
                            <div>
                                <h6 class="fw-bold mb-1 text-main">Engagement Score</h6>
                                <h2 class="fw-bold text-main mb-0">${stats.engagement_score}%</h2>
                                <span class="text-xs text-secondary">Based on historical CTR & reads</span>
                            </div>
                            <div class="progress mt-2 mx-auto" style="height:6px; width:80%; background:rgba(255,255,255,0.06);">
                                <div class="progress-bar bg-primary" style="width:${stats.engagement_score}%"></div>
                            </div>
                        </div>
                    </div>

                    <div class="col-lg-4">
                        <div class="glass-card d-flex flex-column gap-3 text-center py-4">
                            <div class="mx-auto bg-success bg-opacity-10 p-3 rounded-circle" style="width:60px;height:60px;">
                                <i data-lucide="clock" class="text-success" style="width:28px;height:28px;"></i>
                            </div>
                            <div>
                                <h6 class="fw-bold mb-1 text-main">Best Publish Time</h6>
                                <h5 class="fw-bold text-success mb-1">${stats.best_publish_times[0]}</h5>
                                <span class="text-xs text-secondary">Peak audience activity</span>
                            </div>
                            <span class="text-xxs text-secondary border-top pt-2">Alternative: ${stats.best_publish_times[1]}</span>
                        </div>
                    </div>

                    <div class="col-lg-4">
                        <div class="glass-card d-flex flex-column gap-3 text-center py-4">
                            <div class="mx-auto bg-warning bg-opacity-10 p-3 rounded-circle" style="width:60px;height:60px;">
                                <i data-lucide="shield-alert" class="text-warning" style="width:28px;height:28px;"></i>
                            </div>
                            <div>
                                <h6 class="fw-bold mb-1 text-main">Predicted Read Rate</h6>
                                <h2 class="fw-bold text-main mb-0">${stats.predicted_read_rate}%</h2>
                                <span class="text-xs text-secondary">Expected reach forecast</span>
                            </div>
                            <span class="text-xxs text-secondary border-top pt-2">Target Suggestion: ${stats.suggested_category} Alert</span>
                        </div>
                    </div>

                    <div class="col-12">
                        <div class="glass-card">
                            <h6 class="fw-bold mb-3 text-main">AI Security & Reach Recommendations</h6>
                            <div class="d-flex flex-column gap-3">
                                ${stats.recommendations.map(rec => `
                                    <div class="d-flex align-items-start gap-3 p-3 rounded-3" style="background:rgba(255,255,255,0.02); border: 1px solid var(--ds-border-color);">
                                        <div class="bg-primary bg-opacity-10 p-1.5 rounded-2 mt-0.5">
                                            <i data-lucide="check" class="text-primary" style="width:14px;height:14px;"></i>
                                        </div>
                                        <div>
                                            <span class="text-xs text-main fw-semibold d-block">Co-pilot Suggestion</span>
                                            <span class="text-xs text-secondary">${rec}</span>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    </div>
                </div>
            `;
            if (window.lucide) lucide.createIcons();
        } catch (e) {
            container.innerHTML = `<div class="alert alert-danger">Error loading AI dashboard.</div>`;
        }
    },

    // ─── 5-Step Creation Wizard Modal ─────────────────────────────────────────────

    openWizard() {
        this.wizardStep = 1;
        this.wizardData = {
            title: '',
            summary: '',
            body: '',
            category: 'General',
            priority: 'Medium',
            tags: [],
            audience_type: 'all',
            audience: [],
            channels: { in_app: true, email: false, sms: false, push: false },
            publish_at: '',
            expires_at: '',
            timezone: 'UTC',
            action: 'draft'
        };
        
        const modal = new bootstrap.Modal(document.getElementById('annWizardModal'));
        modal.show();
        this.renderWizardStep();
    },

    renderWizardStep() {
        const body = document.getElementById('wizardBodyContent');
        const nextBtn = document.getElementById('wizNextBtn');
        const prevBtn = document.getElementById('wizPrevBtn');
        const progressBar = document.getElementById('wizardProgressBar');
        if (!body) return;

        // Progress bar percentage calculation
        const progressPct = this.wizardStep * 20;
        progressBar.style.width = `${progressPct}%`;

        // Update indicator labels
        for (let i = 1; i <= 5; i++) {
            const lbl = document.querySelector(`.step-lbl-${i}`);
            if (lbl) {
                if (i === this.wizardStep) {
                    lbl.className = `step-lbl-${i} fw-bold text-primary`;
                } else if (i < this.wizardStep) {
                    lbl.className = `step-lbl-${i} text-success fw-semibold`;
                } else {
                    lbl.className = `step-lbl-${i} text-muted`;
                }
            }
        }

        prevBtn.style.display = this.wizardStep === 1 ? 'none' : 'inline-block';
        nextBtn.textContent = this.wizardStep === 5 ? 'Finish & Create' : 'Next';

        if (this.wizardStep === 1) {
            body.innerHTML = `
                <div class="d-flex flex-column gap-3">
                    <div class="ds-field">
                        <label class="ds-label">Announcement Title <span class="text-danger">*</span></label>
                        <input type="text" class="ds-input" id="wizTitle" required placeholder="e.g. Critical Scheduled DB Maintenance" value="${this.wizardData.title}" oninput="AnnouncementsModule.wizardData.title=this.value">
                    </div>
                    <div class="ds-field">
                        <label class="ds-label">Message Details (HTML content)</label>
                        <textarea class="ds-input" id="wizBody" rows="5" placeholder="Write rich message content here..." oninput="AnnouncementsModule.wizardData.body=this.value">${this.wizardData.body}</textarea>
                    </div>
                    <div class="row g-3">
                        <div class="col-md-6">
                            <div class="ds-field">
                                <label class="ds-label">Category</label>
                                <select class="ds-input ds-select" id="wizCategory" onchange="AnnouncementsModule.wizardData.category=this.value">
                                    <option value="General" ${this.wizardData.category === 'General' ? 'selected' : ''}>General</option>
                                    <option value="Maintenance" ${this.wizardData.category === 'Maintenance' ? 'selected' : ''}>Maintenance</option>
                                    <option value="Security" ${this.wizardData.category === 'Security' ? 'selected' : ''}>Security Alert</option>
                                    <option value="Billing" ${this.wizardData.category === 'Billing' ? 'selected' : ''}>Billing Update</option>
                                    <option value="Feature Release" ${this.wizardData.category === 'Feature Release' ? 'selected' : ''}>Feature Release</option>
                                </select>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="ds-field">
                                <label class="ds-label">Priority</label>
                                <select class="ds-input ds-select" id="wizPriority" onchange="AnnouncementsModule.wizardData.priority=this.value">
                                    <option value="Low" ${this.wizardData.priority === 'Low' ? 'selected' : ''}>Low</option>
                                    <option value="Medium" ${this.wizardData.priority === 'Medium' ? 'selected' : ''}>Medium</option>
                                    <option value="High" ${this.wizardData.priority === 'High' ? 'selected' : ''}>High</option>
                                    <option value="Critical" ${this.wizardData.priority === 'Critical' ? 'selected' : ''}>Critical</option>
                                </select>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        } else if (this.wizardStep === 2) {
            body.innerHTML = `
                <div class="d-flex flex-column gap-3">
                    <div class="ds-field">
                        <label class="ds-label">Target Audience Pool</label>
                        <select class="ds-input ds-select" id="wizAudienceType" onchange="AnnouncementsModule.setAudienceType(this.value)">
                            <option value="all" ${this.wizardData.audience_type === 'all' ? 'selected' : ''}>All Organizations (Platform-wide)</option>
                            <option value="selected" ${this.wizardData.audience_type === 'selected' ? 'selected' : ''}>Custom Targets (Advanced Criteria Rules)</option>
                        </select>
                    </div>
                    
                    <div id="audienceCriteriaSection" style="${this.wizardData.audience_type === 'selected' ? '' : 'display:none;'}">
                        <div class="border rounded-3 p-3 bg-body-tertiary bg-opacity-25" style="border-color:var(--ds-border-color)!important;">
                            <div class="d-flex align-items-center justify-content-between mb-3">
                                <span class="text-xs fw-bold text-main d-flex align-items-center gap-1.5"><i data-lucide="filter" class="text-primary" style="width:14px;height:14px;"></i> Advanced Target Criteria</span>
                                <span class="badge bg-primary-subtle text-primary text-xxs px-2 py-0.5" id="targetRuleCountBadge">${this.wizardData.audience.length} Active Rules</span>
                            </div>

                            <div class="row g-2 align-items-end mb-3">
                                <div class="col-md-4">
                                    <label class="text-xxs fw-semibold text-secondary mb-1">Criterion Type</label>
                                    <select class="ds-input ds-select py-1.5 text-xs" id="newCritType" onchange="AnnouncementsModule.onCritTypeChange(this.value)">
                                        <option value="plan">Subscription Plan</option>
                                        <option value="role">User Role</option>
                                        <option value="org">Org ID / Name</option>
                                        <option value="country">Country / Region</option>
                                        <option value="status">Account Status</option>
                                    </select>
                                </div>
                                <div class="col-md-5 position-relative">
                                    <label class="text-xxs fw-semibold text-secondary mb-1">Target Value Search</label>
                                    <div class="position-relative">
                                        <input type="text" class="ds-input py-1.5 text-xs w-100 pe-4" id="newCritValue" placeholder="Search subscription plan..." autocomplete="off" oninput="AnnouncementsModule.filterCritSuggestions(this.value)" onfocus="AnnouncementsModule.showCritSuggestions()" onblur="setTimeout(() => AnnouncementsModule.hideCritSuggestions(), 200)">
                                        <i data-lucide="search" class="position-absolute end-0 top-50 translate-middle-y me-2 text-muted" style="width:13px;height:13px;pointer-events:none;"></i>
                                    </div>
                                    <!-- Search Autocomplete Suggestions Dropdown -->
                                    <div id="critSuggestionsDropdown" class="glass-dropdown position-absolute w-100 mt-1 shadow-lg border rounded-3 p-1" style="max-height: 220px; overflow-y: auto; z-index: 1050; display: none; background: var(--ds-surface-card, #ffffff); border-color: var(--ds-border-color)!important;">
                                    </div>
                                </div>
                                <div class="col-md-3">
                                    <button class="ds-btn ds-btn-primary ds-btn-sm w-100 py-2 text-xs fw-semibold" onclick="AnnouncementsModule.addCriterion()">
                                        <i data-lucide="plus" class="me-1" style="width:12px;height:12px;"></i> Add Rule
                                    </button>
                                </div>
                            </div>

                            <!-- Quick Preset Shortcuts -->
                            <div class="d-flex align-items-center gap-1.5 mb-3 flex-wrap p-2 rounded-2 border" style="background: rgba(255,255,255,0.02); border-color:var(--ds-border-color)!important;">
                                <span class="text-xxs text-secondary fw-semibold">Quick Shortcuts:</span>
                                <button class="ds-btn ds-btn-xs ds-btn-outline py-0.5 px-2 text-xxs" onclick="AnnouncementsModule.addQuickRule('plan', 'Enterprise')">+ Enterprise</button>
                                <button class="ds-btn ds-btn-xs ds-btn-outline py-0.5 px-2 text-xxs" onclick="AnnouncementsModule.addQuickRule('role', 'SuperAdmin')">+ SuperAdmins</button>
                                <button class="ds-btn ds-btn-xs ds-btn-outline py-0.5 px-2 text-xxs" onclick="AnnouncementsModule.addQuickRule('role', 'Admin')">+ Org Admins</button>
                                <button class="ds-btn ds-btn-xs ds-btn-outline py-0.5 px-2 text-xxs" onclick="AnnouncementsModule.addQuickRule('country', 'IN')">+ India Region</button>
                            </div>

                            <div class="d-flex flex-wrap gap-2 mt-2" id="criteriaBadgeList">
                            </div>
                        </div>
                    </div>
                </div>
            `;
            setTimeout(() => this.renderCriteriaBadges(), 0);
        } else if (this.wizardStep === 3) {
            body.innerHTML = `
                <div class="d-flex flex-column gap-3">
                    <span class="text-xs fw-semibold text-secondary">Enable Delivery Channels</span>
                    
                    <label class="d-flex align-items-center gap-3 p-3 rounded border cursor-pointer hover-card" style="border-color:var(--ds-border-color)!important; background:rgba(255,255,255,0.01);">
                        <input type="checkbox" style="width:18px;height:18px;" ${this.wizardData.channels.in_app ? 'checked' : ''} onchange="AnnouncementsModule.wizardData.channels.in_app=this.checked">
                        <div>
                            <span class="text-xs fw-bold text-main d-block">In-App Notification Center</span>
                            <span class="text-xxs text-secondary">Deliver instant alerts inside the QCMS notification panel.</span>
                        </div>
                    </label>

                    <label class="d-flex align-items-center gap-3 p-3 rounded border cursor-pointer hover-card" style="border-color:var(--ds-border-color)!important; background:rgba(255,255,255,0.01);">
                        <input type="checkbox" style="width:18px;height:18px;" ${this.wizardData.channels.email ? 'checked' : ''} onchange="AnnouncementsModule.wizardData.channels.email=this.checked">
                        <div>
                            <span class="text-xs fw-bold text-main d-block">Email Broadcast Dispatch</span>
                            <span class="text-xxs text-secondary">SMTP fallback delivery directly to target user inboxes.</span>
                        </div>
                    </label>

                </div>
            `;
        } else if (this.wizardStep === 4) {
            body.innerHTML = `
                <div class="d-flex flex-column gap-3">
                    <div class="ds-field">
                        <label class="ds-label">Publish Action</label>
                        <select class="ds-input ds-select" id="wizActionType" onchange="AnnouncementsModule.setScheduleMode(this.value)">
                            <option value="draft" ${this.wizardData.action === 'draft' ? 'selected' : ''}>Save Draft (No delivery)</option>
                            <option value="publish" ${this.wizardData.action === 'publish' ? 'selected' : ''}>Publish Immediately</option>
                            <option value="schedule" ${this.wizardData.action === 'schedule' ? 'selected' : ''}>Schedule Future Broadcast</option>
                        </select>
                    </div>

                    <div id="scheduleDetailsSection" style="${this.wizardData.action === 'schedule' ? '' : 'display:none;'}">
                        <div class="row g-3">
                            <div class="col-md-6">
                                <div class="ds-field">
                                    <label class="ds-label">Publish Date & Time <span class="text-danger">*</span></label>
                                    <input type="datetime-local" class="ds-input" id="wizPublishAt" value="${this.wizardData.publish_at || ''}" onchange="AnnouncementsModule.wizardData.publish_at=this.value">
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="ds-field">
                                    <label class="ds-label">Expiry Date & Time</label>
                                    <input type="datetime-local" class="ds-input" id="wizExpiresAt" value="${this.wizardData.expires_at || ''}" onchange="AnnouncementsModule.wizardData.expires_at=this.value">
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        } else if (this.wizardStep === 5) {
            body.innerHTML = `
                <div class="d-flex flex-column gap-3">
                    <span class="text-xs fw-semibold text-secondary">Confirm Details Before Delivery</span>
                    
                    <div class="p-3 border rounded" style="background:rgba(255,255,255,0.01); border-color:var(--ds-border-color)!important;">
                        <h6 class="fw-bold text-main mb-1">${this.wizardData.title || '[Untitled]'}</h6>
                        <span class="badge bg-primary bg-opacity-15 text-primary text-xxs mb-3">${this.wizardData.category} · ${this.wizardData.priority}</span>
                        <p class="text-xs text-muted mb-2">${this.wizardData.body ? (this.wizardData.body.length > 120 ? this.wizardData.body.substring(0, 120) + '...' : this.wizardData.body) : 'No message content configured.'}</p>
                        <div class="text-xxs text-secondary border-top pt-2">
                            <span>Status: ${this.wizardData.action.toUpperCase()}</span> ·
                            <span>Audience: ${this.wizardData.audience_type === 'all' ? 'All Organizations' : `${this.wizardData.audience.length} Criteria rules`}</span>
                        </div>
                    </div>
                </div>
            `;
        }
        if (window.lucide) lucide.createIcons();
    },

    setAudienceType(val) {
        this.wizardData.audience_type = val;
        const section = document.getElementById('audienceCriteriaSection');
        if (section) section.style.display = val === 'selected' ? 'block' : 'none';
    },

    setScheduleMode(val) {
        this.wizardData.action = val;
        const section = document.getElementById('scheduleDetailsSection');
        if (section) section.style.display = val === 'schedule' ? 'block' : 'none';
    },

    onCritTypeChange(type) {
        const input = document.getElementById('newCritValue');
        if (!input) return;
        input.value = '';
        const placeholders = {
            'plan': 'Search plan e.g. Enterprise, Starter...',
            'role': 'Search role e.g. Admin, Reviewer...',
            'org': 'Search Org ID or Name e.g. 1...',
            'country': 'Search country e.g. IN, US, UK...',
            'status': 'Search status e.g. Active, Trial...'
        };
        input.placeholder = placeholders[type] || 'Search target value...';
        this.filterCritSuggestions('');
    },

    showCritSuggestions() {
        const type = document.getElementById('newCritType')?.value || 'plan';
        const val = document.getElementById('newCritValue')?.value || '';
        this.filterCritSuggestions(val);
    },

    hideCritSuggestions() {
        const drop = document.getElementById('critSuggestionsDropdown');
        if (drop) drop.style.display = 'none';
    },

    filterCritSuggestions(query) {
        const drop = document.getElementById('critSuggestionsDropdown');
        if (!drop) return;
        const type = document.getElementById('newCritType')?.value || 'plan';
        const items = this.CRIT_SUGGESTIONS[type] || [];
        const q = (query || '').toLowerCase().trim();

        const filtered = items.filter(it => 
            it.value.toLowerCase().includes(q) || 
            it.label.toLowerCase().includes(q) || 
            (it.desc && it.desc.toLowerCase().includes(q))
        );

        if (filtered.length === 0) {
            if (q) {
                drop.innerHTML = `<div class="p-2 text-xxs text-muted text-center">Use custom typed value: "<strong>${QCMS.escapeHtml(query)}</strong>"</div>`;
            } else {
                drop.innerHTML = `<div class="p-2 text-xxs text-muted text-center">Type to search options...</div>`;
            }
        } else {
            drop.innerHTML = filtered.map(it => `
                <div class="p-2 rounded-2 cursor-pointer hover-bg-primary-subtle d-flex align-items-center justify-content-between text-xs my-0.5" style="transition: background 0.15s;" onmousedown="AnnouncementsModule.selectCritSuggestion('${QCMS.escapeHtml(it.value)}')">
                    <div>
                        <div class="fw-bold text-main" style="font-size: 12px;">${QCMS.escapeHtml(it.label)}</div>
                        <div class="text-xxs text-secondary" style="font-size: 10px;">${QCMS.escapeHtml(it.desc || '')}</div>
                    </div>
                    <span class="badge bg-primary-subtle text-primary text-xxs font-monospace">${QCMS.escapeHtml(it.value)}</span>
                </div>
            `).join('');
        }
        drop.style.display = 'block';
    },

    selectCritSuggestion(val) {
        const input = document.getElementById('newCritValue');
        if (input) {
            input.value = val;
        }
        this.hideCritSuggestions();
    },

    addQuickRule(type, val) {
        const select = document.getElementById('newCritType');
        if (select) select.value = type;
        const input = document.getElementById('newCritValue');
        if (input) input.value = val;
        this.addCriterion();
    },

    addCriterion() {
        const typeSelect = document.getElementById('newCritType');
        const valueInput = document.getElementById('newCritValue');
        if (!typeSelect || !valueInput) return;

        const type = typeSelect.value;
        const value = valueInput.value.trim();
        if (!value) {
            QCMS.toast('Please enter or select a target value.', 'warning');
            return;
        }

        const exists = this.wizardData.audience.some(c => c.type === type && c.value.toLowerCase() === value.toLowerCase());
        if (exists) {
            QCMS.toast('Target rule already exists.', 'info');
            return;
        }

        this.wizardData.audience.push({ type, value });
        valueInput.value = '';
        this.hideCritSuggestions();
        this.renderCriteriaBadges();
    },

    removeCriterion(idx) {
        this.wizardData.audience.splice(idx, 1);
        this.renderCriteriaBadges();
    },

    renderCriteriaBadges() {
        const div = document.getElementById('criteriaBadgeList');
        const countBadge = document.getElementById('targetRuleCountBadge');
        if (countBadge) {
            countBadge.innerText = `${this.wizardData.audience.length} Active Rules`;
        }
        if (!div) return;

        const typeLabels = {
            'plan': { label: 'Plan', icon: 'credit-card', color: 'primary' },
            'role': { label: 'Role', icon: 'user-check', color: 'info' },
            'org': { label: 'Org', icon: 'building-2', color: 'warning' },
            'country': { label: 'Country', icon: 'globe', color: 'success' },
            'status': { label: 'Status', icon: 'zap', color: 'danger' }
        };

        if (this.wizardData.audience.length === 0) {
            div.innerHTML = '<span class="text-xs text-muted">No custom targets defined. Broadcast defaults to all.</span>';
            return;
        }

        div.innerHTML = this.wizardData.audience.map((crit, idx) => {
            const meta = typeLabels[crit.type] || { label: crit.type, icon: 'filter', color: 'secondary' };
            return `
                <span class="badge bg-${meta.color}-subtle text-${meta.color} border border-${meta.color}-subtle d-inline-flex align-items-center gap-1.5 px-2.5 py-1.5 rounded-pill text-xs shadow-sm">
                    <i data-lucide="${meta.icon}" style="width:12px;height:12px;"></i>
                    <strong>${meta.label}:</strong> ${QCMS.escapeHtml(crit.value)}
                    <a href="javascript:void(0)" class="text-danger fw-bold ms-1 text-decoration-none" onclick="AnnouncementsModule.removeCriterion(${idx})" title="Remove Rule">&times;</a>
                </span>
            `;
        }).join('');

        if (window.lucide) lucide.createIcons();
    },

    prevStep() {
        if (this.wizardStep > 1) {
            this.wizardStep--;
            this.renderWizardStep();
        }
    },

    async nextStep() {
        if (this.wizardStep < 5) {
            if (this.wizardStep === 1 && !this.wizardData.title.trim()) {
                QCMS.toast('Title is required.', 'error');
                return;
            }
            this.wizardStep++;
            this.renderWizardStep();
        } else {
            // Submit form
            await this.submitWizard();
        }
    },

    async submitWizard() {
        try {
            // Process times into ISO payload
            let payload = { ...this.wizardData };
            if (payload.action === 'schedule' && payload.publish_at) {
                payload.publish_at = new Date(payload.publish_at).toISOString();
            } else if (payload.action === 'publish') {
                payload.publish_at = new Date().toISOString();
            }
            if (payload.expires_at) {
                payload.expires_at = new Date(payload.expires_at).toISOString();
            }

            const res = await api.post('/announcements/', payload);
            if (res.status === 'success') {
                QCMS.toast('Broadcast successfully initialized!', 'success');
                const modalEl = document.getElementById('annWizardModal');
                const modal = bootstrap.Modal.getInstance(modalEl);
                if (modal) modal.hide();
                
                this.switchTab('list');
            } else {
                QCMS.toast(res.message || 'Failure writing broadcast.', 'error');
            }
        } catch (e) {
            QCMS.toast('Failed to save announcement.', 'error');
        }
    },

    // ─── Actions ──────────────────────────────────────────────────────────────────

    async publishNow(id) {
        if (!confirm("Are you sure you want to publish this announcement live immediately?")) return;
        try {
            const res = await api.post(`/announcements/${id}/publish`);
            if (res.status === 'success') {
                QCMS.toast('Broadcast went live successfully!', 'success');
                this.loadRegistry();
            }
        } catch (e) {
            QCMS.toast('Error publishing announcement.', 'error');
        }
    },

    async duplicateAnn(id) {
        try {
            const res = await api.post(`/announcements/${id}/duplicate`);
            if (res.status === 'success') {
                QCMS.toast('Draft announcement duplicated.', 'success');
                this.loadRegistry();
            }
        } catch (e) {
            QCMS.toast('Failed to duplicate.', 'error');
        }
    },

    async archiveAnn(id) {
        if (!confirm("Archive this announcement? It will no longer be visible to targeted organizations.")) return;
        try {
            const res = await api.post(`/announcements/${id}/archive`);
            if (res.status === 'success') {
                QCMS.toast('Announcement archived.', 'success');
                this.loadRegistry();
            }
        } catch (e) {
            QCMS.toast('Failed to archive.', 'error');
        }
    },

    async deleteAnn(id) {
        if (!confirm("Danger! Delete this announcement? This action is immutable and will log an audit event.")) return;
        try {
            const res = await api.delete(`/announcements/${id}`);
            if (res.status === 'success') {
                QCMS.toast('Announcement deleted and audit log stored.', 'success');
                this.loadRegistry();
            }
        } catch (e) {
            QCMS.toast('Failed to delete.', 'error');
        }
    },

    // ─── Detail Drawer & Statistics ───────────────────────────────────────────────

    async openDetail(id) {
        const body = document.getElementById('detailModalBody');
        const statusBadge = document.getElementById('detailStatusBadge');
        if (!body) return;

        body.innerHTML = `<div class="text-center py-5"><div class="spinner-border text-primary" role="status"></div></div>`;
        const modal = new bootstrap.Modal(document.getElementById('annDetailModal'));
        modal.show();

        try {
            const detailRes = await api.get(`/announcements/${id}`);
            const readsRes = await api.get(`/announcements/${id}/reads`);
            const auditRes = await api.get(`/announcements/${id}/audit`);

            if (detailRes.status !== 'success' || readsRes.status !== 'success' || auditRes.status !== 'success') {
                throw new Error('Endpoint load fail');
            }

            const a = detailRes.data;
            const reads = readsRes.data;
            const audits = auditRes.data;

            statusBadge.className = `ds-badge ${a.status === 'Published' ? 'green' : a.status === 'Scheduled' ? 'blue' : a.status === 'Expired' ? 'orange' : 'gray'}`;
            statusBadge.textContent = a.status;

            body.innerHTML = `
                <div class="row g-4">
                    <div class="col-lg-7">
                        <div class="glass-card p-4 mb-4">
                            <h4 class="fw-bold text-main mb-2">${a.title}</h4>
                            <div class="h-stack gap-2 text-xxs text-secondary mb-4">
                                <span>Ref: ${a.ann_number}</span> ·
                                <span>Category: ${a.category}</span> ·
                                <span>Priority: ${a.priority}</span> ·
                                <span>Created By: ${a.created_by}</span>
                            </div>
                            <div class="p-3 border rounded-3 mb-4" style="background:rgba(255,255,255,0.01); border-color:var(--ds-border-color)!important;">
                                <strong class="text-xs text-secondary d-block mb-1">Teaser</strong>
                                <p class="text-xs text-muted mb-0">${a.summary || '—'}</p>
                            </div>
                            <div class="text-sm text-main" style="min-height:100px;">
                                ${a.body || '<span class="text-muted">No message details provided.</span>'}
                            </div>
                        </div>

                        <!-- Read Receipts / Analytics Details -->
                        <div class="glass-card p-4">
                            <h6 class="fw-bold text-main mb-3">Read Statistics</h6>
                            <div class="row g-3 text-center mb-4">
                                <div class="col-3">
                                    <div class="p-2 border rounded" style="background:rgba(255,255,255,0.01); border-color:var(--ds-border-color)!important;">
                                        <div class="text-xs text-secondary">Delivered</div>
                                        <strong class="text-lg text-main">${reads.total_delivered}</strong>
                                    </div>
                                </div>
                                <div class="col-3">
                                    <div class="p-2 border rounded" style="background:rgba(255,255,255,0.01); border-color:var(--ds-border-color)!important;">
                                        <div class="text-xs text-secondary">Read</div>
                                        <strong class="text-lg text-success">${reads.total_read}</strong>
                                    </div>
                                </div>
                                <div class="col-3">
                                    <div class="p-2 border rounded" style="background:rgba(255,255,255,0.01); border-color:var(--ds-border-color)!important;">
                                        <div class="text-xs text-secondary">Unread</div>
                                        <strong class="text-lg text-warning">${reads.unread}</strong>
                                    </div>
                                </div>
                                <div class="col-3">
                                    <div class="p-2 border rounded" style="background:rgba(255,255,255,0.01); border-color:var(--ds-border-color)!important;">
                                        <div class="text-xs text-secondary">CTR</div>
                                        <strong class="text-lg text-info">${reads.ctr}%</strong>
                                    </div>
                                </div>
                            </div>
                            
                            <span class="text-xs text-secondary d-block mb-2">Device distribution</span>
                            <div class="d-flex flex-column gap-2">
                                ${Object.entries(reads.by_device).map(([d, count]) => `
                                    <div class="d-flex align-items-center gap-2">
                                        <span class="text-xs text-secondary" style="width:80px;">${d}</span>
                                        <div class="progress flex-grow-1" style="height:6px; background:rgba(255,255,255,0.06);">
                                            <div class="progress-bar bg-info" style="width:${(count / reads.total_delivered * 100) || 0}%"></div>
                                        </div>
                                        <span class="text-xs fw-bold text-main" style="width:25px; text-align:right;">${count}</span>
                                    </div>
                                `).join('') || '<span class="text-xs text-muted text-center py-2">No read activities recorded yet.</span>'}
                            </div>
                        </div>
                    </div>

                    <div class="col-lg-5">
                        <!-- Targeting Info -->
                        <div class="glass-card p-4 mb-4">
                            <h6 class="fw-bold text-main mb-3">Target Scope</h6>
                            <div class="d-flex flex-column gap-2 mb-3">
                                <div class="d-flex justify-content-between text-xs border-bottom pb-2" style="border-color:var(--ds-border-color)!important;">
                                    <span class="text-secondary">Target Type</span>
                                    <span class="text-main fw-semibold">${a.audience_type.toUpperCase()}</span>
                                </div>
                                <div class="d-flex justify-content-between text-xs border-bottom pb-2" style="border-color:var(--ds-border-color)!important;">
                                    <span class="text-secondary">Scheduled Date</span>
                                    <span class="text-main fw-semibold">${a.publish_at ? new Date(a.publish_at).toLocaleDateString() : 'Immediate'}</span>
                                </div>
                                <div class="d-flex justify-content-between text-xs pb-2">
                                    <span class="text-secondary">Expires Date</span>
                                    <span class="text-main fw-semibold">${a.expires_at ? new Date(a.expires_at).toLocaleDateString() : 'Never'}</span>
                                </div>
                            </div>
                            
                            <span class="text-xs text-secondary d-block mb-2">Enabled Channels</span>
                            <div class="h-stack gap-1.5 flex-wrap">
                                ${Object.entries(a.channels).filter(([_, active]) => active).map(([ch]) => `
                                    <span class="ds-badge gray text-xxs">${ch.replace('_', ' ').toUpperCase()}</span>
                                `).join('') || '<span class="text-xs text-muted">No channels selected.</span>'}
                            </div>
                        </div>

                        <!-- Audit Logs Timeline -->
                        <div class="glass-card p-4">
                            <h6 class="fw-bold text-main mb-3">Registry Audit Trail</h6>
                            <div class="d-flex flex-column gap-3">
                                ${audits.map(l => `
                                    <div class="d-flex gap-3 position-relative pb-2 border-bottom" style="border-color:var(--ds-border-color)!important;">
                                        <div class="d-flex flex-column align-items-center">
                                            <div class="bg-primary rounded-circle" style="width:8px;height:8px;margin-top:5px;"></div>
                                        </div>
                                        <div>
                                            <span class="text-xs text-main fw-bold d-block">${l.action}</span>
                                            <span class="text-xxs text-secondary d-block">${new Date(l.timestamp).toLocaleString()} · by ${l.actor}</span>
                                            <span class="text-xxs text-muted d-block font-monospace">${l.ip_address}</span>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    </div>
                </div>
            `;
            if (window.lucide) lucide.createIcons();

        } catch (e) {
            body.innerHTML = `<div class="alert alert-danger">Error fetching detail logs.</div>`;
        }
    },

    // ─── Export CSV ───────────────────────────────────────────────────────────────

    async exportCSV() {
        try {
            const res = await api.post('/announcements/export', { format: 'csv' });
            if (res.status === 'success') {
                const blob = new Blob([res.csv], { type: 'text/csv;charset=utf-8;' });
                const link = document.createElement("a");
                const url = URL.createObjectURL(blob);
                link.setAttribute("href", url);
                link.setAttribute("download", `Announcements_Export_${new Date().toISOString().slice(0, 10)}.csv`);
                link.style.visibility = 'hidden';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                QCMS.toast('Export downloaded successfully.', 'success');
            }
        } catch (e) {
            QCMS.toast('Export failed.', 'error');
        }
    }
};

window.AnnouncementsModule = AnnouncementsModule;
