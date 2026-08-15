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
    emailIntegrations: [],
    wizardData: {
        title: '',
        summary: '',
        body: '',
        category: 'General',
        priority: 'Medium',
        tags: [],
        audience_type: 'all',
        audience: [],
        channels: { in_app: true, email: false, email_provider: '', sms: false, push: false },
        publish_at: '',
        expires_at: '',
        timezone: 'UTC',
        action: 'draft'
    },

    liveCritSuggestions: { plan: [], role: [], org: [], country: [], status: [] },

    async fetchTargetSuggestions() {
        try {
            const res = await api.get('/announcements/target-suggestions');
            if (res && res.status === 'success' && res.data) {
                this.liveCritSuggestions = res.data;
            }
        } catch (e) {
            console.error('Failed to load target suggestions', e);
        }
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
            <style>
                .sd-tab-btn {
                    padding: 7px 16px !important;
                    border-radius: 8px !important;
                    font-size: 0.8125rem !important;
                    font-weight: 600 !important;
                    color: var(--ds-text-secondary, #64748b) !important;
                    background: transparent !important;
                    border: 1px solid transparent !important;
                    transition: all 0.2s ease !important;
                    cursor: pointer !important;
                    display: inline-flex !important;
                    align-items: center !important;
                    gap: 6px !important;
                }
                .sd-tab-btn:hover {
                    color: var(--ds-primary, #2563eb) !important;
                    background: rgba(37, 99, 235, 0.08) !important;
                }
                .sd-tab-btn.active {
                    background: var(--ds-primary, #2563eb) !important;
                    color: #ffffff !important;
                    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3) !important;
                    border-color: var(--ds-primary, #2563eb) !important;
                }
                .sd-tab-btn.active i, .sd-tab-btn.active svg, .sd-tab-btn.active [data-lucide] {
                    color: #ffffff !important;
                    stroke: #ffffff !important;
                }
            </style>
            <div class="announcements-module d-flex flex-column gap-4 fade-in px-3">
                <!-- Navigation Tabs & Actions -->
                <div class="d-flex flex-wrap align-items-center justify-content-between gap-3 border-bottom pb-3" style="border-color:var(--ds-border-color)!important;">
                    <div class="h-stack gap-1 bg-surface-secondary p-1 rounded-3 border" style="border-color:var(--ds-border-color)!important; background:rgba(0,0,0,0.02);">
                        <button class="sd-tab-btn active" id="tab-dashboard" onclick="AnnouncementsModule.switchTab('dashboard')">
                            <i data-lucide="layout-dashboard" class="me-1.5" style="width:14px;height:14px;"></i> Dashboard
                        </button>
                        <button class="sd-tab-btn" id="tab-list" onclick="AnnouncementsModule.switchTab('list')">
                            <i data-lucide="list" class="me-1.5" style="width:14px;height:14px;"></i> Message Registry
                        </button>
                        <button class="sd-tab-btn" id="tab-email-notifications" onclick="AnnouncementsModule.switchTab('email-notifications')">
                            <i data-lucide="mail" class="me-1.5" style="width:14px;height:14px;"></i> Set Email Notifications
                        </button>
                        <button class="sd-tab-btn" id="tab-wizard" onclick="AnnouncementsModule.openWizard()">
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

                        <div class="modal-footer d-flex justify-content-between align-items-center px-4 py-3" style="border-top:1px solid var(--ds-border-color); background:rgba(0,0,0,0.1);">
                            <div class="text-xs text-secondary fw-semibold" id="wizStepIndicatorText">Step 1 of 5</div>
                            <div class="d-flex align-items-center gap-2">
                                <button class="ds-btn ds-btn-secondary ds-btn-sm px-3" id="wizPrevBtn" onclick="AnnouncementsModule.prevStep()" style="display:none !important;">
                                    <i data-lucide="arrow-left" style="width:14px;height:14px;" class="me-1"></i> Back
                                </button>
                                <button class="ds-btn ds-btn-primary ds-btn-sm px-4" id="wizNextBtn" onclick="AnnouncementsModule.nextStep()">Next</button>
                            </div>
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
        } else if (tabId === 'email-notifications') {
            await this.renderEmailNotificationsHub(contentArea);
        }

        if (window.lucide) lucide.createIcons();
    },

    activeBroadcastsPage: 1,
    activeBroadcastsPerPage: 5,

    getActiveCountLabel(total, page, perPage = 5) {
        if (!total || total === 0) return '0 active broadcasts';
        const start = (page - 1) * perPage + 1;
        const end = Math.min(page * perPage, total);
        return `Showing ${start}-${end} of ${total} active broadcast${total === 1 ? '' : 's'}`;
    },

    renderActiveBroadcastsPaginationControls(page, pages) {
        if (!pages || pages <= 1) return '';
        return `
            <div class="d-flex align-items-center gap-1">
                <button class="ds-btn ds-btn-outline ds-btn-sm px-2 py-1 text-xs" style="height:26px; font-size:11px;" ${page <= 1 ? 'disabled' : ''} onclick="AnnouncementsModule.fetchActiveBroadcastsPage(${page - 1})">
                    <i data-lucide="chevron-left" style="width:12px; height:12px;"></i> Prev
                </button>
                <span class="text-xs text-secondary px-2 font-semibold">Page ${page} of ${pages}</span>
                <button class="ds-btn ds-btn-outline ds-btn-sm px-2 py-1 text-xs" style="height:26px; font-size:11px;" ${page >= pages ? 'disabled' : ''} onclick="AnnouncementsModule.fetchActiveBroadcastsPage(${page + 1})">
                    Next <i data-lucide="chevron-right" style="width:12px; height:12px;"></i>
                </button>
            </div>
        `;
    },

    renderBroadcastItemsList(items) {
        if (!items || !items.length) {
            return '<div class="text-center py-4 text-secondary text-xs">No active broadcasts.</div>';
        }
        return items.map(a => {
            const delivered = Math.max(a.total_delivered || 0, a.total_read || 0);
            const read = Math.min(a.total_read || 0, delivered);
            const pct = delivered > 0 ? Math.min(100, Math.round((read / delivered) * 1000) / 10).toFixed(1) : '0.0';
            return `
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
                    <div>Read: ${read} / ${delivered} (${pct}%)</div>
                </div>
            </div>
            `;
        }).join('');
    },

    async fetchActiveBroadcastsPage(page) {
        const container = document.getElementById('dashRecentAnnouncements');
        if (!container) return;
        container.innerHTML = '<div class="text-center py-4 text-secondary text-xs"><div class="spinner-border spinner-border-sm text-primary me-2"></div> Loading page ' + page + '...</div>';
        try {
            const res = await api.get(`/announcements/active-broadcasts?page=${page}&per_page=5`);
            if (res && res.status === 'success' && res.data) {
                const { items, total, pages, page: currPage } = res.data;
                this.activeBroadcastsPage = currPage;
                container.innerHTML = this.renderBroadcastItemsList(items);

                const countLabel = document.getElementById('activeBroadcastsCountLabel');
                if (countLabel) countLabel.textContent = this.getActiveCountLabel(total, currPage, 5);

                const nav = document.getElementById('activeBroadcastsPaginationNav');
                if (nav) nav.innerHTML = this.renderActiveBroadcastsPaginationControls(currPage, pages);

                if (window.lucide) lucide.createIcons();
            }
        } catch (e) {
            console.error('Failed to fetch active broadcasts page:', e);
            container.innerHTML = '<div class="text-center py-4 text-danger text-xs">Failed to load broadcasts page.</div>';
        }
    },

    // ─── Dashboard Tab ────────────────────────────────────────────────────────────

    async renderDashboard(container) {
        container.innerHTML = `<div class="text-center py-5"><div class="spinner-border text-primary" role="status"></div></div>`;
        try {
            const res = await api.get('/announcements/dashboard');
            if (res.status !== 'success') throw new Error('API failure');

            const kpis = res.data.kpis;
            const activeData = res.data.active_broadcasts || {
                items: res.data.recent || [],
                total: (res.data.recent || []).length,
                page: 1,
                per_page: 5,
                pages: Math.ceil(((res.data.recent || []).length) / 5) || 1
            };
            this.activeBroadcastsPage = activeData.page || 1;
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
                                <div>
                                    <h6 class="fw-bold mb-0 text-main">Active Broadcasts</h6>
                                    <span class="text-xs text-secondary" id="activeBroadcastsCountLabel">${this.getActiveCountLabel(activeData.total, activeData.page, 5)}</span>
                                </div>
                                <div id="activeBroadcastsPaginationNav">
                                    ${this.renderActiveBroadcastsPaginationControls(activeData.page, activeData.pages)}
                                </div>
                            </div>
                            <div class="d-flex flex-column gap-3 flex-grow-1" id="dashRecentAnnouncements">
                                ${this.renderBroadcastItemsList(activeData.items)}
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
            <div class="glass-card p-0 overflow-hidden">
                <div class="table-responsive px-2">
                    <table class="ds-table mb-0" style="font-size: 11.5px; width: 100%;">
                        <thead>
                            <tr style="font-size: 10.5px;">
                                <th style="width: 125px;">Announcement #</th>
                                <th>Title</th>
                                <th style="width: 90px;">Category</th>
                                <th style="width: 80px;">Priority</th>
                                <th style="width: 90px;">Audience</th>
                                <th style="width: 85px;">Status</th>
                                <th style="width: 75px;">Delivered</th>
                                <th style="width: 85px;">Read Rate</th>
                                <th style="max-width: 140px;">Created By</th>
                                <th style="width: 80px;" class="text-center pe-3">Actions</th>
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
                        <div class="fw-semibold text-main text-truncate" style="max-width: 180px;" title="${a.title}">${a.title}</div>
                        <div class="text-xxs text-secondary text-truncate" style="max-width: 180px;">${a.summary ? a.summary : (a.body ? a.body : '—')}</div>
                    </td>
                    <td><span class="text-xs">${a.category}</span></td>
                    <td>
                        <span class="ds-badge ${a.priority === 'Critical' ? 'red' : a.priority === 'High' ? 'orange' : 'gray'}" style="font-size:10px; padding:2px 6px;">
                            ${a.priority}
                        </span>
                    </td>
                    <td><span class="text-xs">${a.audience_type ? a.audience_type.toUpperCase() : 'ALL'}</span></td>
                    <td>
                        <span class="ds-badge ${a.status === 'Published' ? 'green' : a.status === 'Scheduled' ? 'blue' : a.status === 'Expired' ? 'orange' : 'gray'}" style="font-size:10px; padding:2px 6px;">
                            ${a.status}
                        </span>
                    </td>
                    <td><span class="text-xs fw-semibold">${a.total_delivered || 0}</span></td>
                    <td>
                        <div class="d-flex align-items-center gap-2">
                            <span class="text-xs fw-semibold">${a.read_pct || 0}%</span>
                            <div class="progress" style="width: 45px; height: 4px; background:rgba(255,255,255,0.06);">
                                <div class="progress-bar bg-success" style="width: ${a.read_pct || 0}%"></div>
                            </div>
                        </div>
                    </td>
                    <td>
                        <div class="fw-semibold text-xs text-truncate" style="max-width: 130px;" title="${a.created_by}">${a.created_by}</div>
                    </td>
                    <td class="text-center pe-3">
                        <div class="dropdown d-inline-block">
                            <button class="ds-btn ds-btn-outline ds-btn-sm py-1 px-2" data-bs-toggle="dropdown" data-bs-popper-config='{"strategy":"fixed"}'>
                                <i data-lucide="more-vertical" style="width:14px;height:14px;"></i>
                            </button>
                            <ul class="dropdown-menu dropdown-menu-end shadow border" style="background:var(--ds-surface-secondary); border-color:var(--ds-border-color)!important; z-index: 100000 !important;">
                                <li><a class="dropdown-item text-xs" href="javascript:void(0)" onclick="AnnouncementsModule.openDetail(${a.id})"><i data-lucide="eye" style="width:13px;height:13px;" class="me-1.5 text-primary"></i> View Details</a></li>
                                <li><hr class="dropdown-divider" style="border-color:var(--ds-border-color);"></li>
                                ${a.status === 'Draft' || a.status === 'Scheduled' ? `<li><a class="dropdown-item text-xs text-success" href="javascript:void(0)" onclick="AnnouncementsModule.publishNow(${a.id})"><i data-lucide="send" style="width:13px;height:13px;" class="me-1.5"></i> Publish Now</a></li>` : ''}
                                <li><a class="dropdown-item text-xs" href="javascript:void(0)" onclick="AnnouncementsModule.duplicateAnn(${a.id})"><i data-lucide="copy" style="width:13px;height:13px;" class="me-1.5"></i> Duplicate</a></li>
                                ${a.status === 'Archived' ? `<li><a class="dropdown-item text-xs text-info" href="javascript:void(0)" onclick="AnnouncementsModule.unarchiveAnn(${a.id})"><i data-lucide="archive-restore" style="width:13px;height:13px;" class="me-1.5"></i> Unarchive</a></li>` : ''}
                                ${a.status !== 'Archived' ? `<li><a class="dropdown-item text-xs text-warning" href="javascript:void(0)" onclick="AnnouncementsModule.archiveAnn(${a.id})"><i data-lucide="archive" style="width:13px;height:13px;" class="me-1.5"></i> Archive</a></li>` : ''}
                                <li><hr class="dropdown-divider" style="border-color:var(--ds-border-color);"></li>
                                <li><a class="dropdown-item text-xs text-danger" href="javascript:void(0)" onclick="AnnouncementsModule.deleteAnn(${a.id})"><i data-lucide="trash-2" style="width:13px;height:13px;" class="me-1.5"></i> Delete</a></li>
                            </ul>
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
        document.querySelectorAll('.sd-tab-btn').forEach(btn => btn.classList.remove('active'));
        const wizardBtn = document.getElementById('tab-wizard');
        if (wizardBtn) wizardBtn.classList.add('active');

        this.fetchTargetSuggestions();
        this.loadEmailIntegrations();
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
            channels: { in_app: true, email: false, email_provider: '', sms: false, push: false },
            publish_at: '',
            expires_at: '',
            timezone: 'UTC',
            action: 'draft'
        };
        
        const modalEl = document.getElementById('annWizardModal');
        if (modalEl && !modalEl._hasHideListener) {
            modalEl._hasHideListener = true;
            modalEl.addEventListener('hidden.bs.modal', () => {
                document.querySelectorAll('.sd-tab-btn').forEach(btn => btn.classList.remove('active'));
                const currentBtn = document.getElementById(`tab-${AnnouncementsModule.currentTab}`);
                if (currentBtn) currentBtn.classList.add('active');
                if (window.lucide) lucide.createIcons();
            });
        }

        const modal = new bootstrap.Modal(modalEl);
        modal.show();
        this.renderWizardStep();
    },

    async loadEmailIntegrations() {
        try {
            let res = await api.get('/super-admin/integrations/email-providers');
            if (!res || res.status !== 'success' || !Array.isArray(res.data) || res.data.length === 0) {
                res = await api.get('/integrations/email-providers');
            }
            if (res && res.status === 'success' && Array.isArray(res.data) && res.data.length > 0) {
                this.emailIntegrations = res.data;
                if (!this.wizardData.channels.email_provider && res.data.length > 0) {
                    this.wizardData.channels.email_provider = res.data[0].provider_id;
                }
            } else {
                this.emailIntegrations = [
                    { provider_id: 'resend', provider_name: 'Resend Mail', status: 'Connected', sender_email: 'notifications@qcms.io', sender_name: 'QCMS Cloud' },
                    { provider_id: 'zeptomail', provider_name: 'ZeptoMail (Zoho)', status: 'Connected', sender_email: 'otp@qcms.io', sender_name: 'QCMS OTP Service' }
                ];
                if (!this.wizardData.channels.email_provider) {
                    this.wizardData.channels.email_provider = 'resend';
                }
            }
        } catch (e) {
            this.emailIntegrations = [
                { provider_id: 'resend', provider_name: 'Resend Mail', status: 'Connected', sender_email: 'notifications@qcms.io', sender_name: 'QCMS Cloud' },
                { provider_id: 'zeptomail', provider_name: 'ZeptoMail (Zoho)', status: 'Connected', sender_email: 'otp@qcms.io', sender_name: 'QCMS OTP Service' }
            ];
            if (!this.wizardData.channels.email_provider) {
                this.wizardData.channels.email_provider = 'resend';
            }
        }
    },

    renderWizardStep() {
        const body = document.getElementById('wizardBodyContent');
        const nextBtn = document.getElementById('wizNextBtn');
        const prevBtn = document.getElementById('wizPrevBtn');
        const stepText = document.getElementById('wizStepIndicatorText');
        const progressBar = document.getElementById('wizardProgressBar');
        if (!body) return;

        // Progress bar percentage calculation
        const progressPct = this.wizardStep * 20;
        if (progressBar) progressBar.style.width = `${progressPct}%`;
        if (stepText) stepText.textContent = `Step ${this.wizardStep} of 5`;

        // Update indicator labels
        for (let i = 1; i <= 5; i++) {
            const lbl = document.querySelector(`.step-lbl-${i}`);
            if (lbl) {
                lbl.style.cursor = 'pointer';
                lbl.onclick = () => {
                    if (i < this.wizardStep) {
                        this.wizardStep = i;
                        this.renderWizardStep();
                    }
                };
                if (i === this.wizardStep) {
                    lbl.className = `step-lbl-${i} fw-bold text-primary`;
                } else if (i < this.wizardStep) {
                    lbl.className = `step-lbl-${i} text-success fw-semibold`;
                } else {
                    lbl.className = `step-lbl-${i} text-muted`;
                }
            }
        }

        if (this.wizardStep === 1) {
            if (prevBtn) {
                prevBtn.style.setProperty('display', 'none', 'important');
                prevBtn.classList.add('d-none');
            }
        } else {
            if (prevBtn) {
                prevBtn.style.setProperty('display', 'inline-flex', 'important');
                prevBtn.classList.remove('d-none');
            }
        }
        if (nextBtn) {
            nextBtn.textContent = this.wizardStep === 5 ? 'Finish & Create' : 'Next';
        }

        if (this.wizardStep === 1) {
            body.innerHTML = `
                <div class="d-flex flex-column gap-3">
                    <div class="ds-field">
                        <label class="ds-label">Announcement Title <span class="text-danger">*</span></label>
                        <input type="text" class="ds-input" id="wizTitle" required placeholder="e.g. Critical Scheduled DB Maintenance" value="${this.wizardData.title}" oninput="AnnouncementsModule.wizardData.title=this.value">
                    </div>
                    <div class="ds-field">
                        <label class="ds-label">Message Details <span class="text-danger">*</span></label>
                        <textarea class="ds-input" id="wizBody" required rows="5" placeholder="Write rich message content here..." oninput="AnnouncementsModule.wizardData.body=this.value">${this.wizardData.body}</textarea>
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

                    <!-- Email Channel with Integration Hub providers -->
                    <div class="border rounded p-3" style="border-color:var(--ds-border-color)!important; background:rgba(255,255,255,0.01);">
                        <label class="d-flex align-items-center gap-3 cursor-pointer mb-0">
                            <input type="checkbox" style="width:18px;height:18px;" id="emailChannelCheck" ${this.wizardData.channels.email ? 'checked' : ''} onchange="AnnouncementsModule.toggleEmailChannel(this.checked)">
                            <div>
                                <span class="text-xs fw-bold text-main d-block">Email Broadcast Dispatch</span>
                                <span class="text-xxs text-secondary">Deliver via your connected email integration from Integration Hub.</span>
                            </div>
                        </label>
                        <div id="emailProviderSection" style="${this.wizardData.channels.email ? '' : 'display:none;'}" class="mt-3">
                            ${this._renderEmailProviders()}
                        </div>
                    </div>

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

    toggleEmailChannel(checked) {
        this.wizardData.channels.email = checked;
        const section = document.getElementById('emailProviderSection');
        if (section) section.style.display = checked ? 'block' : 'none';
        if (!checked) {
            this.wizardData.channels.email_provider = '';
        }
    },

    selectEmailProvider(providerId) {
        this.wizardData.channels.email_provider = providerId;
        this.renderWizardStep();
    },

    _renderEmailProviders() {
        const providers = this.emailIntegrations;
        if (!providers || providers.length === 0) {
            return `<div class="p-3 rounded-3 text-center" style="background:rgba(255,200,0,0.06); border:1px dashed rgba(255,200,0,0.3);">
                <i data-lucide="alert-triangle" class="text-warning mb-1" style="width:16px;height:16px;"></i>
                <p class="text-xxs text-secondary mb-1">No email integrations connected in Integration Hub.</p>
                <a href="/admin/super-admin.html?view=integrations" target="_blank" class="text-xs text-primary fw-semibold">Go to Integration Hub →</a>
            </div>`;
        }
        const providerIcon = { resend: 'mail', zeptomail: 'mail-check', jio_dlt: 'message-square' };
        return `<div class="d-flex flex-column gap-2">
            <span class="text-xxs fw-semibold text-secondary mb-1">Select Connected Email Service (from Integration Hub):</span>
            ${providers.map(p => `
                <label class="d-flex align-items-center gap-3 p-3 rounded-3 cursor-pointer" style="border: 1.5px solid ${this.wizardData.channels.email_provider === p.provider_id ? 'var(--ds-primary, #2563eb)' : 'var(--ds-border-color)'}; background: ${this.wizardData.channels.email_provider === p.provider_id ? 'rgba(37,99,235,0.06)' : 'rgba(255,255,255,0.01)'}; transition:all 0.15s ease;">
                    <input type="radio" name="emailProviderRadio" style="width:16px;height:16px;" value="${QCMS.escapeHtml(p.provider_id)}" ${this.wizardData.channels.email_provider === p.provider_id ? 'checked' : ''} onchange="AnnouncementsModule.selectEmailProvider('${QCMS.escapeHtml(p.provider_id)}')">
                    <div class="p-2 rounded-2 bg-primary-subtle text-primary" style="flex-shrink:0;"><i data-lucide="${providerIcon[p.provider_id] || 'mail'}" style="width:16px;height:16px;"></i></div>
                    <div style="flex:1;">
                        <div class="d-flex align-items-center gap-2">
                            <span class="text-xs fw-bold text-main">${QCMS.escapeHtml(p.provider_name)}</span>
                            <span class="badge bg-success-subtle text-success text-xxs px-2 py-0.5">CONNECTED</span>
                        </div>
                        <span class="text-xxs text-secondary d-block mt-0.5">${p.sender_email ? 'Sender Email: <strong>' + QCMS.escapeHtml(p.sender_email) + '</strong>' : 'Ready for email broadcast dispatch'}</span>
                    </div>
                </label>
            `).join('')}
        </div>`;
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

    renderQuickShortcutButtons() {
        const btns = [];
        if (this.liveCritSuggestions.plan && this.liveCritSuggestions.plan.length > 0) {
            const p = this.liveCritSuggestions.plan[0];
            btns.push(`<button class="ds-btn ds-btn-xs ds-btn-outline py-0.5 px-2 text-xxs" onclick="AnnouncementsModule.addQuickRule('plan', '${QCMS.escapeHtml(p.value)}')">+ ${QCMS.escapeHtml(p.value)} Plan</button>`);
        }
        if (this.liveCritSuggestions.role && this.liveCritSuggestions.role.length > 0) {
            const r = this.liveCritSuggestions.role[0];
            btns.push(`<button class="ds-btn ds-btn-xs ds-btn-outline py-0.5 px-2 text-xxs" onclick="AnnouncementsModule.addQuickRule('role', '${QCMS.escapeHtml(r.value)}')">+ ${QCMS.escapeHtml(r.value)}s</button>`);
        }
        if (this.liveCritSuggestions.org && this.liveCritSuggestions.org.length > 0) {
            const o = this.liveCritSuggestions.org[0];
            btns.push(`<button class="ds-btn ds-btn-xs ds-btn-outline py-0.5 px-2 text-xxs" onclick="AnnouncementsModule.addQuickRule('org', '${QCMS.escapeHtml(o.value)}')">+ Org #${QCMS.escapeHtml(o.value)}</button>`);
        }
        if (this.liveCritSuggestions.country && this.liveCritSuggestions.country.length > 0) {
            const c = this.liveCritSuggestions.country[0];
            btns.push(`<button class="ds-btn ds-btn-xs ds-btn-outline py-0.5 px-2 text-xxs" onclick="AnnouncementsModule.addQuickRule('country', '${QCMS.escapeHtml(c.value)}')">+ ${QCMS.escapeHtml(c.value)} Region</button>`);
        }

        if (btns.length === 0) {
            return `<span class="text-xxs text-muted">No shortcuts available yet. Create plans, roles, or orgs to see them here.</span>`;
        }
        return btns.join('');
    },

    filterCritSuggestions(query) {
        const drop = document.getElementById('critSuggestionsDropdown');
        if (!drop) return;
        const type = document.getElementById('newCritType')?.value || 'plan';
        const items = (this.liveCritSuggestions && this.liveCritSuggestions[type]) ? this.liveCritSuggestions[type] : [];
        const q = (query || '').toLowerCase().trim();

        const filtered = items.filter(it => 
            it.value.toLowerCase().includes(q) || 
            it.label.toLowerCase().includes(q) || 
            (it.desc && it.desc.toLowerCase().includes(q))
        );

        if (items.length === 0) {
            if (q) {
                drop.innerHTML = `<div class="p-3 text-xxs text-muted text-center">No created <strong>${QCMS.escapeHtml(type)}</strong> items found in system database.<br>Use custom typed value: "<strong>${QCMS.escapeHtml(query)}</strong>"</div>`;
            } else {
                drop.innerHTML = `<div class="p-3 text-xxs text-muted text-center">No <strong>${QCMS.escapeHtml(type)}</strong> items created in system database yet.<br>Type to set a custom target value.</div>`;
            }
        } else if (filtered.length === 0) {
            drop.innerHTML = `<div class="p-2 text-xxs text-muted text-center">No matching system ${QCMS.escapeHtml(type)}s.<br>Use custom typed value: "<strong>${QCMS.escapeHtml(query)}</strong>"</div>`;
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
            if (this.wizardStep === 1) {
                if (!this.wizardData.title.trim()) {
                    QCMS.toast('Title is required.', 'error');
                    return;
                }
                if (!this.wizardData.body.trim()) {
                    QCMS.toast('Message details are required.', 'error');
                    return;
                }
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
                window.dispatchEvent(new CustomEvent('qcms:announcement-published'));
                if (window.GlobalAnnouncementBanner) {
                    window.GlobalAnnouncementBanner.fetchActiveAnnouncements();
                }
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
                window.dispatchEvent(new CustomEvent('qcms:announcement-published'));
                if (window.GlobalAnnouncementBanner) {
                    window.GlobalAnnouncementBanner.fetchActiveAnnouncements();
                }
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

    async unarchiveAnn(id) {
        if (!confirm("Unarchive this announcement? It will be restored to active status in the registry.")) return;
        try {
            const res = await api.post(`/announcements/${id}/unarchive`);
            if (res.status === 'success') {
                QCMS.toast('Announcement unarchived and restored.', 'success');
                this.loadRegistry();
            }
        } catch (e) {
            QCMS.toast('Failed to unarchive.', 'error');
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
                            <div class="h-stack gap-2 text-xxs text-secondary mb-4 pb-2 border-bottom" style="border-color:var(--ds-border-color)!important;">
                                <span>Ref: <strong>${a.ann_number}</strong></span> ·
                                <span>Category: <strong>${a.category}</strong></span> ·
                                <span>Priority: <strong>${a.priority}</strong></span> ·
                                <span>Created By: <strong>${a.created_by}</strong></span>
                            </div>

                            ${(a.summary && a.summary !== '—' && a.summary.trim() !== '' && a.summary !== a.body) ? `
                            <div class="p-3 border rounded-3 mb-4" style="background:rgba(37,99,235,0.03); border-color:var(--ds-border-color)!important;">
                                <strong class="text-xs text-primary d-block mb-1"><i data-lucide="info" style="width:12px;height:12px;" class="me-1"></i> Summary / Overview</strong>
                                <p class="text-xs text-secondary mb-0">${a.summary}</p>
                            </div>
                            ` : ''}

                            <div class="mb-2">
                                <strong class="text-xs text-secondary d-block mb-2">Message Content</strong>
                                <div class="p-3 border rounded-3 text-sm text-main" style="background:rgba(0,0,0,0.02); border-color:var(--ds-border-color)!important; min-height:100px; white-space: pre-wrap; line-height: 1.6;">
                                    ${a.body || '<span class="text-muted">No message details provided.</span>'}
                                </div>
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
    },

    // ─────────────────────────────────────────────────────────────────────────────
    // EMAIL NOTIFICATION & AUTOMATION CENTER
    // ─────────────────────────────────────────────────────────────────────────────

    _emailMeta: null,
    _emailRules: [],
    _emailLogs: [],

    async fetchEmailMeta() {
        if (this._emailMeta) return this._emailMeta;
        try {
            const res = await api.get('/email-notifications/meta');
            if (res && res.status === 'success') {
                this._emailMeta = res;
                return res;
            }
        } catch (e) {
            console.error('Failed to load email notification metadata', e);
        }
        return null;
    },

    async renderEmailNotificationsHub(container) {
        container.innerHTML = `
            <div class="text-center py-5">
                <div class="spinner-border text-primary" role="status" style="width: 2rem; height: 2rem;"></div>
                <p class="text-xs text-muted mt-2">Loading email notification rules & automated campaigns...</p>
            </div>
        `;

        try {
            const [rulesRes, metaRes] = await Promise.all([
                api.get('/email-notifications/rules'),
                this.fetchEmailMeta()
            ]);

            const rules = (rulesRes && rulesRes.data) ? rulesRes.data : [];
            const metrics = (rulesRes && rulesRes.metrics) ? rulesRes.metrics : {
                total_rules: rules.length,
                active_rules: rules.filter(r => r.is_active).length,
                paused_rules: rules.filter(r => !r.is_active).length,
                total_delivered: rules.reduce((acc, r) => acc + (r.total_sent || 0), 0)
            };
            this._emailRules = rules;

            const categoryMap = {
                'subscription_reminder': { label: 'Subscription Expiry', color: '#2563eb', bg: 'rgba(37,99,235,0.1)', icon: 'clock' },
                'trial_reminder': { label: 'Trial Ending Alert', color: '#d97706', bg: 'rgba(217,119,6,0.1)', icon: 'hourglass' },
                'project_assignment': { label: 'Project Assignment', color: '#2563eb', bg: 'rgba(37,99,235,0.1)', icon: 'user-plus' },
                'project_completion': { label: 'Project Completed & Report', color: '#16a34a', bg: 'rgba(22,163,74,0.1)', icon: 'award' },
                'maintenance': { label: 'System Maintenance', color: '#4f46e5', bg: 'rgba(79,70,229,0.1)', icon: 'wrench' },
                'welcome': { label: 'Welcome & Onboarding', color: '#16a34a', bg: 'rgba(22,163,74,0.1)', icon: 'sparkles' },
                'usage_guide': { label: 'Software How-to Guide', color: '#0284c7', bg: 'rgba(2,132,199,0.1)', icon: 'book-open' },
                'new_feature': { label: 'New Features & Updates', color: '#8b5cf6', bg: 'rgba(139,92,246,0.1)', icon: 'zap' },
                'support': { label: 'Customer Support Check-in', color: '#0d9488', bg: 'rgba(13,148,136,0.1)', icon: 'life-buoy' },
                'payment_confirmation': { label: 'Payment Receipt', color: '#16a34a', bg: 'rgba(22,163,74,0.1)', icon: 'receipt' },
                'payment_rejection': { label: 'Payment Notice', color: '#dc2626', bg: 'rgba(220,38,38,0.1)', icon: 'alert-octagon' },
                'custom': { label: 'Custom Broadcast', color: '#64748b', bg: 'rgba(100,116,139,0.1)', icon: 'mail' }
            };

            const cardsHtml = rules.length ? rules.map(rule => {
                const catInfo = categoryMap[rule.category] || categoryMap['custom'];
                const isInstant = (!rule.trigger_days_before || rule.trigger_days_before === 0 || ['payment_approved', 'payment_rejected', 'project_assigned', 'project_completed', 'new_org_welcome'].includes(rule.event_trigger));
                const triggerBadge = rule.trigger_type === 'event' 
                    ? (isInstant 
                        ? `<span class="badge bg-success-subtle text-success border border-success-subtle px-2 py-1"><i data-lucide="zap" style="width:11px;height:11px;" class="me-1"></i>Immediate Dispatch</span>`
                        : `<span class="badge bg-primary-subtle text-primary border border-primary-subtle px-2 py-1"><i data-lucide="zap" style="width:11px;height:11px;" class="me-1"></i>Auto: ${rule.trigger_days_before}d Before</span>`)
                    : (rule.trigger_type === 'scheduled' 
                        ? `<span class="badge bg-info-subtle text-info border border-info-subtle px-2 py-1"><i data-lucide="calendar" style="width:11px;height:11px;" class="me-1"></i>Scheduled</span>`
                        : `<span class="badge bg-secondary-subtle text-secondary border border-secondary-subtle px-2 py-1"><i data-lucide="send" style="width:11px;height:11px;" class="me-1"></i>Manual Send</span>`);

                const audienceSummary = (rule.target_roles && rule.target_roles.length) 
                    ? rule.target_roles.join(', ') 
                    : (rule.target_audience_type === 'all' ? 'All Users & Orgs' : 'Targeted Organizations');

                return `
                <div class="col-12 col-xl-6 email-rule-card-wrapper" data-category="${rule.category}" data-status="${rule.is_active ? 'active' : 'paused'}" data-name="${rule.name.toLowerCase()}">
                    <div class="glass-card ds-card p-3.5 h-100 d-flex flex-column justify-content-between position-relative border" style="border-color: var(--ds-border-color); border-radius: 12px; transition: all 0.2s ease;">
                        <div>
                            <div class="d-flex align-items-center justify-content-between mb-2">
                                <div class="d-flex align-items-center gap-2 flex-wrap">
                                    <span class="badge font-semibold text-xxs px-2 py-1 d-inline-flex align-items-center" style="background: ${catInfo.bg}; color: ${catInfo.color}; border: 1px solid ${catInfo.color}33;">
                                        <i data-lucide="${catInfo.icon}" style="width:11px;height:11px;" class="me-1"></i> ${catInfo.label}
                                    </span>
                                    ${triggerBadge}
                                    ${rule.is_system_preset ? `<span class="badge bg-secondary bg-opacity-10 text-muted px-2 py-0.5" style="font-size:10px;">System Preset</span>` : ''}
                                </div>
                                <div class="form-check form-switch m-0" title="Toggle Active / Paused">
                                    <input class="form-check-input" type="checkbox" role="switch" ${rule.is_active ? 'checked' : ''} onchange="AnnouncementsModule.toggleEmailRule(${rule.id}, this)">
                                </div>
                            </div>

                            <h6 class="fw-bold text-main mb-1 text-truncate" title="${QCMS.escapeHtml(rule.name)}">${QCMS.escapeHtml(rule.name)}</h6>
                            <p class="text-xs text-secondary mb-2.5" style="display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; min-height: 32px;">${QCMS.escapeHtml(rule.description || 'Configured email notification template with automated dispatching rules.')}</p>

                            <div class="p-2 rounded bg-light-subtle border text-xs mb-3" style="background: rgba(0,0,0,0.02);">
                                <div class="d-flex align-items-center gap-1.5 text-truncate mb-1">
                                    <span class="text-muted text-xxs text-uppercase fw-bold">Subject:</span>
                                    <span class="text-main font-monospace text-truncate" style="font-size:11.5px;">${QCMS.escapeHtml(rule.subject)}</span>
                                </div>
                                <div class="d-flex align-items-center justify-content-between text-xxs text-muted">
                                    <span>From: <strong>${QCMS.escapeHtml(rule.sender_email)}</strong></span>
                                    <span>Audience: <strong>${QCMS.escapeHtml(audienceSummary)}</strong></span>
                                </div>
                            </div>
                        </div>

                        <div class="pt-2 border-top d-flex align-items-center justify-content-between flex-wrap gap-2" style="border-color: var(--ds-border-color)!important;">
                            <div class="d-flex align-items-center gap-2 text-xxs text-muted">
                                <span class="badge bg-success-subtle text-success font-semibold px-2 py-0.5"><i data-lucide="check-circle-2" style="width:10px;height:10px;" class="me-1"></i>${rule.total_sent || 0} Sent</span>
                                ${rule.last_triggered_at ? `<span>Last: ${new Date(rule.last_triggered_at).toLocaleDateString()}</span>` : `<span>Not triggered yet</span>`}
                            </div>
                            <div class="d-flex align-items-center gap-1">
                                <button class="ds-btn ds-btn-outline ds-btn-sm py-1 px-2 text-xs" style="font-size:11px;" title="Send a Test Email" onclick="AnnouncementsModule.openTestEmailModal(${rule.id})">
                                    <i data-lucide="send" style="width:12px;height:12px;" class="me-1"></i> Test
                                </button>
                                <button class="ds-btn ds-btn-outline ds-btn-sm py-1 px-2 text-xs" style="font-size:11px;" title="Preview HTML Email" onclick="AnnouncementsModule.openPreviewEmailModal(${rule.id})">
                                    <i data-lucide="eye" style="width:12px;height:12px;" class="me-1"></i> Preview
                                </button>
                                ${rule.trigger_type !== 'event' ? `
                                <button class="ds-btn ds-btn-primary ds-btn-sm py-1 px-2 text-xs" style="font-size:11px;" title="Trigger Real Broadcast Now" onclick="AnnouncementsModule.triggerEmailRuleNow(${rule.id})">
                                    <i data-lucide="play" style="width:12px;height:12px;" class="me-1"></i> Send Now
                                </button>` : ''}
                                <button class="ds-btn ds-btn-secondary ds-btn-sm py-1 px-2 text-xs" style="font-size:11px;" title="Edit Rule" onclick="AnnouncementsModule.openEmailRuleModal(${rule.id})">
                                    <i data-lucide="edit-3" style="width:12px;height:12px;"></i>
                                </button>
                                ${!rule.is_system_preset ? `
                                <button class="ds-btn ds-btn-danger ds-btn-sm py-1 px-2 text-xs" style="font-size:11px;" title="Delete Rule" onclick="AnnouncementsModule.deleteEmailRule(${rule.id})">
                                    <i data-lucide="trash-2" style="width:12px;height:12px;"></i>
                                </button>` : ''}
                            </div>
                        </div>
                    </div>
                </div>`;
            }).join('') : `
                <div class="col-12 text-center py-5 text-muted">
                    <i data-lucide="mail-search" style="width:36px;height:36px;" class="mb-2 text-secondary opacity-50"></i>
                    <p class="text-sm fw-semibold mb-1">No email notification rules found</p>
                    <p class="text-xs text-muted mb-3">Create your first automated email campaign or restore system default presets.</p>
                    <button class="ds-btn ds-btn-primary ds-btn-sm" onclick="AnnouncementsModule.openEmailRuleModal()">+ Set Email Notification</button>
                </div>
            `;

            container.innerHTML = `
                <div class="fade-in d-flex flex-column gap-4">
                    <!-- Top KPI Summary Cards -->
                    <div class="row g-3">
                        <div class="col-6 col-md-3">
                            <div class="glass-card ds-card p-3 border hover-shadow" style="cursor: pointer; transition: all 0.2s;" onclick="AnnouncementsModule.quickFilterRules('active')" title="Click to view all Active campaigns">
                                <div class="d-flex align-items-center justify-content-between mb-1">
                                    <span class="text-xxs text-uppercase fw-bold text-muted">Active Campaigns</span>
                                    <i data-lucide="zap" class="text-primary" style="width:16px;height:16px;"></i>
                                </div>
                                <div class="fs-4 fw-bold text-main">${metrics.active_rules} <span class="text-xs text-muted fw-normal">/ ${metrics.total_rules} Total</span></div>
                            </div>
                        </div>
                        <div class="col-6 col-md-3">
                            <div class="glass-card ds-card p-3 border hover-shadow" style="cursor: pointer; transition: all 0.2s;" onclick="AnnouncementsModule.openEmailLogsModal()" title="Click to view delivery audit logs">
                                <div class="d-flex align-items-center justify-content-between mb-1">
                                    <span class="text-xxs text-uppercase fw-bold text-muted">Total Delivered</span>
                                    <i data-lucide="check-circle" class="text-success" style="width:16px;height:16px;"></i>
                                </div>
                                <div class="fs-4 fw-bold text-success">${metrics.total_delivered} <span class="text-xs text-muted fw-normal">Emails</span></div>
                            </div>
                        </div>
                        <div class="col-6 col-md-3">
                            <div class="glass-card ds-card p-3 border hover-shadow" style="cursor: pointer; transition: all 0.2s; border-left: 3px solid #f59e0b !important;" onclick="AnnouncementsModule.openSubscriptionRulesModal()" title="Click to manage all Subscription Rules & create new ones">
                                <div class="d-flex align-items-center justify-content-between mb-1">
                                    <span class="text-xxs text-uppercase fw-bold text-muted">Subscription Rules</span>
                                    <i data-lucide="clock" class="text-warning" style="width:16px;height:16px;"></i>
                                </div>
                                <div class="fs-4 fw-bold text-warning">${rules.filter(r => r.category === 'subscription_reminder' || r.category === 'trial_reminder').length} <span class="text-xs text-muted fw-normal">Rules &bull; Manage &rarr;</span></div>
                            </div>
                        </div>
                        <div class="col-6 col-md-3">
                            <div class="glass-card ds-card p-3 border hover-shadow" style="cursor: pointer; transition: all 0.2s;" onclick="AnnouncementsModule.openEmailLogsModal()" title="Click to open full audit history">
                                <div class="d-flex align-items-center justify-content-between mb-1">
                                    <span class="text-xxs text-uppercase fw-bold text-muted">Delivery Logs</span>
                                    <i data-lucide="scroll-text" class="text-info" style="width:16px;height:16px;"></i>
                                </div>
                                <div class="fs-4 fw-bold text-info">${metrics.total_logs || 0} <span class="text-xs text-muted fw-normal">Events</span></div>
                            </div>
                        </div>
                    </div>

                    <!-- Filter & Action Controls -->
                    <div class="glass-card ds-card p-3 border">
                        <div class="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3">
                            <div class="d-flex flex-wrap align-items-center gap-2 flex-grow-1">
                                <div class="position-relative" style="min-width: 220px; max-width: 320px;">
                                    <i data-lucide="search" class="position-absolute top-50 start-0 translate-middle-y ms-2.5 text-muted" style="width:14px;height:14px;"></i>
                                    <input type="text" class="ds-input text-xs ps-4 py-1.5 w-100" id="emailRuleSearchInput" placeholder="Search notification rules..." onkeyup="AnnouncementsModule.filterEmailRules()">
                                </div>
                                <select class="ds-input text-xs py-1.5" id="emailRuleCategoryFilter" onchange="AnnouncementsModule.filterEmailRules()" style="max-width: 190px;">
                                    <option value="">All Categories</option>
                                    <option value="project_assignment">Project Assignment</option>
                                    <option value="project_completion">Project Completed & Report</option>
                                    <option value="subscription_reminder">Subscription Expiry</option>
                                    <option value="trial_reminder">Trial Ending Alert</option>
                                    <option value="maintenance">Software Maintenance</option>
                                    <option value="welcome">Welcome & Onboarding</option>
                                    <option value="usage_guide">Software How-to Guide</option>
                                    <option value="new_feature">New Feature Release</option>
                                    <option value="support">Customer Support Check-in</option>
                                    <option value="custom">Custom Broadcast</option>
                                </select>
                                <select class="ds-input text-xs py-1.5" id="emailRuleStatusFilter" onchange="AnnouncementsModule.filterEmailRules()" style="max-width: 140px;">
                                    <option value="">All Statuses</option>
                                    <option value="active">Active Only</option>
                                    <option value="paused">Paused Only</option>
                                </select>
                            </div>
                            <div class="d-flex align-items-center gap-2">
                                <button type="button" class="ds-btn ds-btn-outline ds-btn-sm text-xs py-1.5 px-3" onclick="AnnouncementsModule.openEmailLogsModal()">
                                    <i data-lucide="scroll-text" style="width:14px;height:14px;" class="me-1"></i> Delivery Logs
                                </button>
                                <button type="button" class="ds-btn ds-btn-primary ds-btn-sm text-xs py-1.5 px-3" onclick="AnnouncementsModule.openEmailRuleModal()">
                                    <i data-lucide="plus-circle" style="width:14px;height:14px;" class="me-1"></i> Set Email Notification
                                </button>
                            </div>
                        </div>
                    </div>

                    <!-- Rule Cards Grid -->
                    <div class="row g-3" id="emailRulesGridContainer">
                        ${cardsHtml}
                    </div>
                </div>
            `;

            if (window.lucide) lucide.createIcons();
        } catch (e) {
            console.error('Failed to render email notification hub', e);
            container.innerHTML = `<div class="alert alert-danger p-3 text-xs">Failed to load email notification rules: ${e.message}</div>`;
        }
    },

    filterEmailRules() {
        const query = (document.getElementById('emailRuleSearchInput')?.value || '').toLowerCase().trim();
        const cat = document.getElementById('emailRuleCategoryFilter')?.value || '';
        const status = document.getElementById('emailRuleStatusFilter')?.value || '';

        document.querySelectorAll('.email-rule-card-wrapper').forEach(card => {
            const cardName = card.getAttribute('data-name') || '';
            const cardCat = card.getAttribute('data-category') || '';
            const cardStatus = card.getAttribute('data-status') || '';

            const matchQ = !query || cardName.includes(query);
            const matchCat = !cat || cardCat === cat;
            const matchStatus = !status || cardStatus === status;

            if (matchQ && matchCat && matchStatus) {
                card.style.display = 'block';
            } else {
                card.style.display = 'none';
            }
        });
    },

    async toggleEmailRule(ruleId, switchEl) {
        try {
            const res = await api.post(`/email-notifications/rules/${ruleId}/toggle`, {});
            if (res && res.status === 'success') {
                QCMS.toast(res.message, 'success');
                if (switchEl) {
                    const card = switchEl.closest('.email-rule-card-wrapper');
                    if (card) card.setAttribute('data-status', res.is_active ? 'active' : 'paused');
                }
            }
        } catch (e) {
            if (switchEl) switchEl.checked = !switchEl.checked;
            QCMS.toast(e.message || 'Failed to toggle rule status', 'error');
        }
    },

    async deleteEmailRule(ruleId) {
        if (!confirm('Are you sure you want to permanently delete this email notification rule?')) return;
        try {
            const res = await api.delete(`/email-notifications/rules/${ruleId}`);
            if (res && res.status === 'success') {
                QCMS.toast('Email notification rule deleted.', 'success');
                const contentArea = document.getElementById('announcementContentArea');
                if (contentArea && this.currentTab === 'email-notifications') {
                    this.renderEmailNotificationsHub(contentArea);
                }
            }
        } catch (e) {
            QCMS.toast(e.message || 'Failed to delete rule', 'error');
        }
    },

    // ─── Modal & Builder ───────────────────────────────────────────────────────────

    async openEmailRuleModal(ruleId = null, defaultCategory = null) {
        let meta = await this.fetchEmailMeta();
        if (!meta) meta = { organizations: [], plans: [], roles: ["All", "Admin", "CEO", "Reviewer", "Facilitator", "Team Member"], subscription_statuses: ["Active", "Trial", "Expiring", "Suspended"], available_variables: [], sender_suggestions: [] };

        const targetCat = defaultCategory || 'subscription_reminder';
        let defaultName = '';
        let defaultSubject = '';
        let defaultHeading = '';
        let defaultDays = 7;
        let defaultEvent = 'subscription_expiring_soon';
        let defaultStatuses = ['Active', 'Expiring'];

        if (targetCat === 'subscription_reminder') {
            defaultName = 'Subscription Expiry Notice';
            defaultSubject = 'Action Required: Your {{plan_name}} subscription expires in {{days_left}} days';
            defaultHeading = 'Your Subscription is Expiring Soon';
            defaultDays = 7;
            defaultEvent = 'subscription_expiring_soon';
            defaultStatuses = ['Active', 'Expiring'];
        } else if (targetCat === 'trial_reminder') {
            defaultName = 'Trial Plan Ending Reminder';
            defaultSubject = 'Your free trial for {{org_name}} ends in {{days_left}} days — Upgrade today!';
            defaultHeading = 'Your Free Trial is Ending Soon';
            defaultDays = 3;
            defaultEvent = 'trial_ending_soon';
            defaultStatuses = ['Trial'];
        }

        let ruleData = {
            id: null,
            name: defaultName,
            category: targetCat,
            description: '',
            subject: defaultSubject,
            preheader: '',
            heading: defaultHeading,
            body_html: '',
            banner_color: '#2563eb',
            cta_text: 'Renew / Upgrade Subscription',
            cta_url: '{{app_url}}',
            sender_email: (meta.branding && meta.branding.billing_email) || (meta.branding && meta.branding.general_email) || 'billing@ifqm.org.in',
            sender_name: (meta.branding && meta.branding.billing_sender_name) || 'QCMS Billing',
            reply_to: (meta.branding && meta.branding.support_email) || 'support@ifqm.org.in',
            trigger_type: 'event',
            event_trigger: defaultEvent,
            trigger_days_before: defaultDays,
            scheduled_at: '',
            target_audience_type: 'all',
            target_org_ids: [],
            target_roles: ['Admin', 'CEO'],
            target_plans: [],
            target_statuses: defaultStatuses,
            is_active: true
        };

        if (ruleId) {
            try {
                const res = await api.get(`/email-notifications/rules/${ruleId}`);
                if (res && res.status === 'success') {
                    ruleData = res.data;
                }
            } catch (e) {
                QCMS.toast('Failed to load rule details', 'error');
                return;
            }
        }

        let modalEl = document.getElementById('emailNotificationModal');
        if (!modalEl) {
            const div = document.createElement('div');
            div.id = 'emailNotificationModalContainer';
            document.body.appendChild(div);
        }

        const orgCheckboxesHtml = (meta.organizations || []).map(o => {
            const isChecked = ruleData.target_org_ids && ruleData.target_org_ids.includes(o.id) ? 'checked' : '';
            return `
            <div class="col-6 col-md-4 mb-1">
                <div class="form-check text-xs">
                    <input class="form-check-input en-org-checkbox" type="checkbox" value="${o.id}" id="enOrg_${o.id}" ${isChecked}>
                    <label class="form-check-label text-truncate" for="enOrg_${o.id}" title="${QCMS.escapeHtml(o.name)}">${QCMS.escapeHtml(o.name)}</label>
                </div>
            </div>`;
        }).join('');

        const roleCheckboxesHtml = (meta.roles || []).map(r => {
            const isChecked = ruleData.target_roles && ruleData.target_roles.includes(r) ? 'checked' : '';
            return `
            <div class="form-check form-check-inline text-xs me-3">
                <input class="form-check-input en-role-checkbox" type="checkbox" value="${r}" id="enRole_${r}" ${isChecked}>
                <label class="form-check-label" for="enRole_${r}">${r}</label>
            </div>`;
        }).join('');

        const statusCheckboxesHtml = (meta.subscription_statuses || []).map(s => {
            const isChecked = ruleData.target_statuses && ruleData.target_statuses.includes(s) ? 'checked' : '';
            return `
            <div class="form-check form-check-inline text-xs me-3">
                <input class="form-check-input en-status-checkbox" type="checkbox" value="${s}" id="enStatus_${s}" ${isChecked}>
                <label class="form-check-label" for="enStatus_${s}">${s}</label>
            </div>`;
        }).join('');

        const variableChipsHtml = (meta.available_variables || []).map(v => {
            return `
            <button type="button" class="ds-btn ds-btn-outline ds-btn-sm py-0.5 px-2 text-xxs font-monospace" style="font-size:11px;" title="Insert ${v.label} (e.g. ${v.example})" onclick="AnnouncementsModule.insertVariableChip('${v.tag}')">
                + ${v.tag}
            </button>`;
        }).join('');

        this.cachedEmailMeta = meta;

        let currentPresetKey = '';
        if (ruleData.name) {
            if (ruleData.name.includes('Project Assignment') || ruleData.name.includes('Kickoff')) currentPresetKey = 'project_assignment';
            else if (ruleData.name.includes('Project Completion') || ruleData.name.includes('Approved & Completed')) currentPresetKey = 'project_completion';
            else if (ruleData.name.includes('Subscription Expiry Urgent') || ruleData.name.includes('(1 Day)')) currentPresetKey = 'subscription_urgent';
            else if (ruleData.name.includes('Subscription Expiry') || ruleData.name.includes('(7 Days)')) currentPresetKey = 'subscription_reminder';
            else if (ruleData.name.includes('Trial Plan Ending') || ruleData.name.includes('(3 Days)')) currentPresetKey = 'trial_reminder';
            else if (ruleData.name.includes('Maintenance') || ruleData.name.includes('Downtime')) currentPresetKey = 'maintenance';
            else if (ruleData.name.includes('Welcome & Onboarding') || ruleData.name.includes('Welcome')) currentPresetKey = 'welcome';
            else if (ruleData.name.includes('8-Stage Quality Workflow') || ruleData.name.includes('How to Use')) currentPresetKey = 'usage_guide';
            else if (ruleData.name.includes('New Features') || ruleData.name.includes('Release Notes')) currentPresetKey = 'new_feature';
            else if (ruleData.name.includes('Customer Support') || ruleData.name.includes('Support & Success')) currentPresetKey = 'support';
        }
        if (!currentPresetKey && ruleData.category) {
            currentPresetKey = ruleData.category;
        }

        const presetOptions = [
            { key: 'payment_confirmation', label: 'Subscription Purchased & Invoice Receipt' },
            { key: 'payment_rejection', label: 'Payment Verification Declined Notice' },
            { key: 'project_assignment', label: 'Project Assignment & Kickoff' },
            { key: 'project_completion', label: 'Project Completion & Report' },
            { key: 'subscription_reminder', label: 'Subscription Expiry (7 Days)' },
            { key: 'subscription_urgent', label: 'Subscription Expiry Urgent (1 Day)' },
            { key: 'trial_reminder', label: 'Trial Ending Alert (3 Days)' },
            { key: 'maintenance', label: 'Software Maintenance Notice' },
            { key: 'welcome', label: 'New Organization Registration & Welcome' },
            { key: 'usage_guide', label: 'Software How-to Guide (8-Stage)' },
            { key: 'new_feature', label: 'New Feature Release Notes' },
            { key: 'support', label: 'Customer Support Check-in' }
        ];

        const presetOptionsHtml = presetOptions.map(p => {
            const isSelected = (currentPresetKey === p.key) ? 'selected' : '';
            return `<option value="${p.key}" ${isSelected}>${p.label}</option>`;
        }).join('');

        let currentChannelKey = 'general';
        const catObj = (meta.categories || []).find(c => c.key === ruleData.category);
        if (catObj && catObj.channel) {
            currentChannelKey = catObj.channel;
        } else if (ruleData.category === 'maintenance') {
            currentChannelKey = 'alerts';
        } else if (ruleData.category === 'welcome') {
            currentChannelKey = 'onboarding';
        } else if (ruleData.category === 'subscription_reminder' || ruleData.category === 'trial_reminder' || ruleData.category === 'payment_confirmation' || ruleData.category === 'payment_rejection') {
            currentChannelKey = 'billing';
        } else if (ruleData.category === 'support') {
            currentChannelKey = 'support';
        }

        const senderSuggestionsHtml = (meta.sender_suggestions || []).map(s => {
            return `<option value="${s.email}" data-name="${s.name}">${s.name} (${s.email})</option>`;
        }).join('');

        const contactChannels = meta.contact_directory_channels || [];
        const contactChannelsOptionsHtml = contactChannels.map(c => {
            const isSelected = (currentChannelKey === c.key) ? 'selected' : '';
            return `<option value="${c.key}" data-email="${QCMS.escapeHtml(c.email)}" data-name="${QCMS.escapeHtml(c.name)}" ${isSelected}>${c.label} (${c.email} &bull; ${c.name})</option>`;
        }).join('');

        const containerEl = document.getElementById('emailNotificationModalContainer') || document.body;
        containerEl.innerHTML = `
        <div class="modal fade" id="emailNotificationModal" tabindex="-1" aria-hidden="true" data-bs-backdrop="static">
            <div class="modal-dialog modal-xl modal-dialog-centered modal-dialog-scrollable">
                <div class="modal-content" style="background:var(--ds-bg-card); border: 1px solid var(--ds-border-color); border-radius: var(--ds-radius-lg);">
                    <div class="modal-header border-bottom pb-3">
                        <div class="d-flex align-items-center gap-2">
                            <div class="p-2 rounded bg-primary-subtle text-primary">
                                <i data-lucide="mail-plus" style="width:20px;height:20px;"></i>
                            </div>
                            <div>
                                <h5 class="modal-title fw-bold mb-0">${ruleId ? 'Edit Email Notification Rule' : 'Configure New Email Notification'}</h5>
                                <div class="text-xxs text-secondary">Set notification message, sender identity, automated triggers, and target organizations.</div>
                            </div>
                        </div>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>

                    <div class="modal-body p-4">
                        <form id="emailRuleForm" onsubmit="event.preventDefault(); AnnouncementsModule.saveEmailRule(${ruleId || 'null'});">
                            <div class="row g-4">
                                <!-- Left Column: Template Content & Identity -->
                                <div class="col-12 col-lg-7 d-flex flex-column gap-3 border-end pe-lg-4">
                                    <div class="d-flex align-items-center justify-content-between p-2.5 rounded border bg-light-subtle">
                                        <div class="text-xs fw-semibold text-main"><i data-lucide="sparkles" style="width:13px;height:13px;" class="me-1 text-primary"></i> Load Standard Preset Template:</div>
                                        <select class="ds-input text-xs py-1" id="enPresetTemplateSelect" style="max-width:240px;" onchange="AnnouncementsModule.loadPresetIntoForm(this.value)">
                                            <option value="">-- Choose Template Preset --</option>
                                            ${presetOptionsHtml}
                                        </select>
                                    </div>

                                    <div class="row g-3">
                                        <div class="col-md-7">
                                            <label class="ds-label text-xs fw-semibold">Campaign / Rule Name <span class="text-danger">*</span></label>
                                            <input type="text" class="ds-input text-sm" id="enRuleName" required placeholder="e.g. Subscription Expiry Reminder (7 Days)" value="${QCMS.escapeHtml(ruleData.name)}">
                                        </div>
                                        <div class="col-md-5">
                                            <label class="ds-label text-xs fw-semibold">Category <span class="text-danger">*</span></label>
                                            <select class="ds-input text-sm" id="enCategory" required onchange="AnnouncementsModule.onCategoryChange(this.value)">
                                                <option value="payment_confirmation" ${ruleData.category === 'payment_confirmation' ? 'selected' : ''}>Subscription Payment & Invoice</option>
                                                <option value="payment_rejection" ${ruleData.category === 'payment_rejection' ? 'selected' : ''}>Payment Verification Declined</option>
                                                <option value="project_assignment" ${ruleData.category === 'project_assignment' ? 'selected' : ''}>Project Assignment</option>
                                                <option value="project_completion" ${ruleData.category === 'project_completion' ? 'selected' : ''}>Project Completed & Report</option>
                                                <option value="subscription_reminder" ${ruleData.category === 'subscription_reminder' ? 'selected' : ''}>Subscription Expiry</option>
                                                <option value="trial_reminder" ${ruleData.category === 'trial_reminder' ? 'selected' : ''}>Trial Ending Alert</option>
                                                <option value="maintenance" ${ruleData.category === 'maintenance' ? 'selected' : ''}>Software Maintenance</option>
                                                <option value="welcome" ${ruleData.category === 'welcome' ? 'selected' : ''}>Welcome & Onboarding</option>
                                                <option value="usage_guide" ${ruleData.category === 'usage_guide' ? 'selected' : ''}>Software How-to Guide</option>
                                                <option value="new_feature" ${ruleData.category === 'new_feature' ? 'selected' : ''}>New Features & Updates</option>
                                                <option value="support" ${ruleData.category === 'support' ? 'selected' : ''}>Customer Support Check-in</option>
                                                <option value="custom" ${ruleData.category === 'custom' ? 'selected' : ''}>Custom Broadcast</option>
                                            </select>
                                        </div>
                                    </div>

                                    <!-- Sender Configuration (Linked to Document Identity & Branding) -->
                                    <div class="p-3 rounded border" style="background: rgba(0,0,0,0.01);">
                                        <div class="d-flex align-items-center justify-content-between mb-2">
                                            <div class="fw-bold text-xs text-uppercase text-secondary d-flex align-items-center gap-1.5">
                                                <i data-lucide="send" style="width:12px;height:12px;"></i> Sender Identity & Address Configuration
                                            </div>
                                            <span class="badge bg-primary-subtle text-primary text-xxs font-normal">
                                                <i data-lucide="shield-check" style="width:11px;height:11px;" class="me-1"></i> Document Identity & Integration Domain
                                            </span>
                                        </div>
                                        
                                        <div class="mb-2">
                                            <label class="ds-label text-xxs mb-1">Select Identity Channel from Document Branding</label>
                                            <select class="ds-input text-xs py-1" id="enContactChannelSelect" onchange="AnnouncementsModule.onContactChannelSelect(this)">
                                                <option value="">-- Choose Identity Channel (Auto-fill) --</option>
                                                ${contactChannelsOptionsHtml}
                                                <option value="custom">-- Custom Sender Address --</option>
                                            </select>
                                        </div>

                                        <div class="row g-2">
                                            <div class="col-md-6">
                                                <label class="ds-label text-xxs">From Email Address <span class="text-danger">*</span></label>
                                                <input type="email" class="ds-input text-xs" id="enSenderEmail" list="senderEmailList" required placeholder="e.g. alerts@ifqm.org.in" value="${QCMS.escapeHtml(ruleData.sender_email)}">
                                                <datalist id="senderEmailList">
                                                    ${senderSuggestionsHtml}
                                                </datalist>
                                            </div>
                                            <div class="col-md-6">
                                                <label class="ds-label text-xxs">Sender Display Name <span class="text-danger">*</span></label>
                                                <input type="text" class="ds-input text-xs" id="enSenderName" required placeholder="e.g. Emergency alert" value="${QCMS.escapeHtml(ruleData.sender_name)}">
                                            </div>
                                            <div class="col-12">
                                                <label class="ds-label text-xxs">Reply-To Address (Optional)</label>
                                                <input type="email" class="ds-input text-xs" id="enReplyTo" placeholder="e.g. support@ifqm.org.in" value="${QCMS.escapeHtml(ruleData.reply_to || (meta.branding && meta.branding.support_email) || '')}">
                                            </div>
                                        </div>
                                    </div>

                                    <!-- Email Subject & Banner -->
                                    <div class="row g-2">
                                        <div class="col-12">
                                            <label class="ds-label text-xs fw-semibold">Email Subject Line <span class="text-danger">*</span></label>
                                            <input type="text" class="ds-input text-sm font-monospace" id="enSubject" required placeholder="e.g. Action Required: Your {{plan_name}} subscription expires in {{days_left}} days" value="${QCMS.escapeHtml(ruleData.subject)}">
                                        </div>
                                        <div class="col-md-8">
                                            <label class="ds-label text-xxs">Inbox Preview Text (Preheader)</label>
                                            <input type="text" class="ds-input text-xs" id="enPreheader" placeholder="Brief snippet visible in email inbox preview..." value="${QCMS.escapeHtml(ruleData.preheader || '')}">
                                        </div>
                                        <div class="col-md-4">
                                            <label class="ds-label text-xxs">Header Accent Color</label>
                                            <div class="d-flex align-items-center gap-2">
                                                <input type="color" class="form-control form-control-color p-1" style="height:32px; width:44px;" id="enBannerColor" value="${ruleData.banner_color || '#2563eb'}">
                                                <span class="text-xxs font-monospace text-muted" id="enColorHexText">${ruleData.banner_color || '#2563eb'}</span>
                                            </div>
                                        </div>
                                    </div>

                                    <!-- Dynamic Placeholders Toolbar -->
                                    <div>
                                        <div class="d-flex align-items-center justify-content-between mb-1.5">
                                            <label class="ds-label text-xs fw-semibold m-0">Email Body HTML & Dynamic Placeholders <span class="text-danger">*</span></label>
                                            <span class="text-xxs text-muted">Click chip to insert into text</span>
                                        </div>
                                        <div class="d-flex flex-wrap gap-1.5 mb-2 p-2 rounded bg-light-subtle border">
                                            ${variableChipsHtml}
                                        </div>
                                        <textarea class="ds-input text-xs font-monospace" id="enBodyHtml" rows="8" required placeholder="Type your email body HTML content with {{variables}}...">${QCMS.escapeHtml(ruleData.body_html)}</textarea>
                                    </div>

                                    <!-- Call To Action Button -->
                                    <div class="p-2.5 rounded border bg-light-subtle">
                                        <div class="fw-bold text-xxs text-uppercase text-secondary mb-1.5 d-flex align-items-center gap-1">
                                            <i data-lucide="link-2" style="width:12px;height:12px;"></i> Primary Call to Action Button (Optional)
                                        </div>
                                        <div class="row g-2">
                                            <div class="col-md-5">
                                                <label class="ds-label text-xxs">Button Label</label>
                                                <input type="text" class="ds-input text-xs" id="enCtaText" placeholder="e.g. Renew Plan Now" value="${QCMS.escapeHtml(ruleData.cta_text || '')}">
                                            </div>
                                            <div class="col-md-7">
                                                <label class="ds-label text-xxs">Button Target Link (URL)</label>
                                                <input type="text" class="ds-input text-xs" id="enCtaUrl" placeholder="e.g. {{app_url}}/admin/settings.html?tab=billing" value="${QCMS.escapeHtml(ruleData.cta_url || '')}">
                                            </div>
                                        </div>
                                    </div>
                                </div>

                                <!-- Right Column: Triggers, Audience & Live Preview -->
                                <div class="col-12 col-lg-5 d-flex flex-column gap-3">
                                    <!-- Timing & Triggers Card -->
                                    <div class="p-3 rounded border" style="background: rgba(0,0,0,0.01);">
                                        <div class="fw-bold text-xs text-uppercase text-secondary mb-2 d-flex align-items-center gap-1.5">
                                            <i data-lucide="clock" style="width:12px;height:12px;"></i> Trigger & Dispatch Schedule
                                        </div>
                                        <div class="mb-2">
                                            <label class="ds-label text-xxs">Trigger Mode</label>
                                            <select class="ds-input text-xs" id="enTriggerType" onchange="AnnouncementsModule.onTriggerTypeChange(this.value)">
                                                <option value="event" ${ruleData.trigger_type === 'event' ? 'selected' : ''}>Automated Event (Expiry / Signups)</option>
                                                <option value="scheduled" ${ruleData.trigger_type === 'scheduled' ? 'selected' : ''}>Scheduled Broadcast (Specific Date & Time)</option>
                                                <option value="manual" ${ruleData.trigger_type === 'manual' ? 'selected' : ''}>Manual Send On-Demand Only</option>
                                            </select>
                                        </div>

                                        <div id="enEventTriggerConfig" style="display: ${ruleData.trigger_type === 'event' ? 'block' : 'none'};">
                                            <div class="row g-2">
                                                <div class="col-7">
                                                    <label class="ds-label text-xxs">Automated Event Trigger</label>
                                                    <select class="ds-input text-xs" id="enEventTrigger">
                                                        <option value="payment_approved" ${ruleData.event_trigger === 'payment_approved' ? 'selected' : ''}>Subscription Purchased / Activated</option>
                                                        <option value="payment_rejected" ${ruleData.event_trigger === 'payment_rejected' ? 'selected' : ''}>Offline Payment Declined</option>
                                                        <option value="subscription_expiring_soon" ${ruleData.event_trigger === 'subscription_expiring_soon' ? 'selected' : ''}>Subscription Expiring Soon</option>
                                                        <option value="trial_expiring_soon" ${ruleData.event_trigger === 'trial_expiring_soon' ? 'selected' : ''}>Trial Plan Ending Soon</option>
                                                        <option value="subscription_expired" ${ruleData.event_trigger === 'subscription_expired' ? 'selected' : ''}>Subscription Already Expired</option>
                                                        <option value="new_org_welcome" ${ruleData.event_trigger === 'new_org_welcome' ? 'selected' : ''}>New Organization Registration</option>
                                                    </select>
                                                </div>
                                                <div class="col-5">
                                                    <label class="ds-label text-xxs">Days Before Expiry</label>
                                                    <input type="number" min="0" max="90" class="ds-input text-xs" id="enTriggerDays" value="${ruleData.trigger_days_before || 7}">
                                                </div>
                                            </div>
                                        </div>

                                        <div id="enScheduledConfig" style="display: ${ruleData.trigger_type === 'scheduled' ? 'block' : 'none'};">
                                            <label class="ds-label text-xxs">Scheduled Dispatch Time</label>
                                            <input type="datetime-local" class="ds-input text-xs" id="enScheduledAt" value="${ruleData.scheduled_at ? ruleData.scheduled_at.slice(0, 16) : ''}">
                                        </div>
                                    </div>

                                    <!-- Audience & Targeting Card -->
                                    <div class="p-3 rounded border" style="background: rgba(0,0,0,0.01);">
                                        <div class="fw-bold text-xs text-uppercase text-secondary mb-2 d-flex align-items-center gap-1.5">
                                            <i data-lucide="users" style="width:12px;height:12px;"></i> Audience & Recipient Targeting
                                        </div>

                                        <div class="mb-2">
                                            <label class="ds-label text-xxs">Target Scope</label>
                                            <select class="ds-input text-xs" id="enAudienceType" onchange="AnnouncementsModule.onAudienceTypeChange(this.value)">
                                                <option value="all" ${ruleData.target_audience_type === 'all' ? 'selected' : ''}>All Organizations (Platform-Wide)</option>
                                                <option value="specific_orgs" ${ruleData.target_audience_type === 'specific_orgs' ? 'selected' : ''}>Specific Selected Organizations</option>
                                                <option value="subscription_based" ${ruleData.target_audience_type === 'subscription_based' ? 'selected' : ''}>Subscription Tier & Status Filtered</option>
                                            </select>
                                        </div>

                                        <!-- Target Roles -->
                                        <div class="mb-2.5">
                                            <label class="ds-label text-xxs mb-1">Target User Roles in Organization</label>
                                            <div>${roleCheckboxesHtml}</div>
                                        </div>

                                        <!-- Target Statuses -->
                                        <div class="mb-2.5">
                                            <label class="ds-label text-xxs mb-1">Target Subscription Status</label>
                                            <div>${statusCheckboxesHtml}</div>
                                        </div>

                                        <!-- Specific Organizations Checklist -->
                                        <div id="enSpecificOrgsContainer" style="display: ${ruleData.target_audience_type === 'specific_orgs' ? 'block' : 'none'};">
                                            <label class="ds-label text-xxs mb-1">Select Target Organizations</label>
                                            <div class="p-2 rounded border bg-light-subtle row g-1" style="max-height: 120px; overflow-y: auto;">
                                                ${orgCheckboxesHtml}
                                            </div>
                                        </div>
                                    </div>

                                    <!-- Quick Interactive Live Preview Box -->
                                    <div class="p-3 rounded border d-flex flex-column gap-2" style="background: rgba(37,99,235,0.03); border-color: rgba(37,99,235,0.2)!important;">
                                        <div class="d-flex align-items-center justify-content-between">
                                            <div class="fw-bold text-xs text-primary d-flex align-items-center gap-1">
                                                <i data-lucide="eye" style="width:13px;height:13px;"></i> Live Email Preview
                                            </div>
                                            <button type="button" class="ds-btn ds-btn-outline ds-btn-sm py-0.5 px-2 text-xxs" onclick="AnnouncementsModule.updateLiveFormPreview()">
                                                Refresh Preview
                                            </button>
                                        </div>
                                        <div id="enLivePreviewFrame" class="border rounded bg-white p-2" style="max-height: 240px; overflow-y: auto; font-size: 11px;">
                                            <div class="text-muted text-center py-4">Click "Refresh Preview" to generate live HTML email view.</div>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            <div class="modal-footer mt-4 pt-3 border-top d-flex justify-content-between align-items-center px-0 pb-0">
                                <button type="button" class="ds-btn ds-btn-secondary ds-btn-sm px-3" data-bs-dismiss="modal">Cancel</button>
                                <div class="d-flex align-items-center gap-2">
                                    <button type="button" class="ds-btn ds-btn-outline ds-btn-sm px-3" onclick="AnnouncementsModule.testFromForm()">
                                        <i data-lucide="send" style="width:13px;height:13px;" class="me-1"></i> Send Test to Me
                                    </button>
                                    <button type="submit" class="ds-btn ds-btn-primary ds-btn-sm px-4">
                                        <i data-lucide="save" style="width:13px;height:13px;" class="me-1"></i> Save Notification Rule
                                    </button>
                                </div>
                            </div>
                        </form>
                    </div>
                </div>
            </div>
        </div>`;

        const modal = new bootstrap.Modal(document.getElementById('emailNotificationModal'));
        modal.show();
        if (window.lucide) lucide.createIcons();

        // Update hex color on color input change
        const colorInput = document.getElementById('enBannerColor');
        if (colorInput) {
            colorInput.addEventListener('input', (e) => {
                const hexEl = document.getElementById('enColorHexText');
                if (hexEl) hexEl.textContent = e.target.value;
            });
        }

        // Initial live preview render
        setTimeout(() => this.updateLiveFormPreview(), 300);
    },

    insertVariableChip(tag) {
        const textarea = document.getElementById('enBodyHtml');
        if (!textarea) return;
        
        const start = textarea.selectionStart || 0;
        const end = textarea.selectionEnd || 0;
        const text = textarea.value;
        textarea.value = text.substring(0, start) + tag + text.substring(end);
        textarea.focus();
        textarea.selectionStart = textarea.selectionEnd = start + tag.length;
    },

    onTriggerTypeChange(val) {
        const eventBox = document.getElementById('enEventTriggerConfig');
        const schedBox = document.getElementById('enScheduledConfig');
        if (eventBox) eventBox.style.display = (val === 'event') ? 'block' : 'none';
        if (schedBox) schedBox.style.display = (val === 'scheduled') ? 'block' : 'none';
    },

    onEventTriggerChange(val) {
        const daysInput = document.getElementById('enTriggerDays');
        if (daysInput) {
            if (['payment_approved', 'payment_rejected', 'project_assigned', 'project_completed', 'new_org_welcome'].includes(val)) {
                daysInput.value = 0;
                daysInput.disabled = true;
                daysInput.title = "Instant Dispatch upon event trigger (0 days)";
            } else {
                daysInput.disabled = false;
                daysInput.title = "";
                if (parseInt(daysInput.value, 10) === 0) daysInput.value = 7;
            }
        }
    },

    onAudienceTypeChange(val) {
        const orgsBox = document.getElementById('enSpecificOrgsContainer');
        if (orgsBox) orgsBox.style.display = (val === 'specific_orgs') ? 'block' : 'none';
    },

    onContactChannelSelect(selectEl) {
        if (!selectEl) return;
        const selectedOpt = selectEl.options[selectEl.selectedIndex];
        if (!selectedOpt || !selectedOpt.value || selectedOpt.value === 'custom') return;

        const email = selectedOpt.getAttribute('data-email');
        const name = selectedOpt.getAttribute('data-name');

        const emailInput = document.getElementById('enSenderEmail');
        const nameInput = document.getElementById('enSenderName');
        if (emailInput && email) emailInput.value = email;
        if (nameInput && name) nameInput.value = name;
        this.updateLiveFormPreview();
    },

    onCategoryChange(category) {
        if (!this.cachedEmailMeta) return;
        const channels = this.cachedEmailMeta.contact_directory_channels || [];
        let channelKey = 'general';
        if (category === 'subscription_reminder' || category === 'trial_reminder' || category === 'payment_confirmation' || category === 'payment_rejection') {
            channelKey = 'billing';
        } else if (category === 'welcome') {
            channelKey = 'onboarding';
        } else if (category === 'maintenance') {
            channelKey = 'alerts';
        } else if (category === 'support') {
            channelKey = 'support';
        } else {
            const catObj = (this.cachedEmailMeta.categories || []).find(c => c.key === category);
            if (catObj && catObj.channel) channelKey = catObj.channel;
        }
        const matched = channels.find(c => c.key === channelKey);
        if (matched) {
            const emailInput = document.getElementById('enSenderEmail');
            const nameInput = document.getElementById('enSenderName');
            const replyInput = document.getElementById('enReplyTo');
            const channelSelect = document.getElementById('enContactChannelSelect');
            if (emailInput) emailInput.value = matched.email;
            if (nameInput) nameInput.value = matched.name;
            if (replyInput && !replyInput.value) replyInput.value = this.cachedEmailMeta.branding ? this.cachedEmailMeta.branding.support_email : matched.email;
            if (channelSelect) channelSelect.value = matched.key;
        }
        this.updateLiveFormPreview();
    },

    loadPresetIntoForm(presetKey) {
        const presets = {
            'payment_confirmation': {
                name: "Subscription Payment Approved & Tax Invoice Receipt",
                category: "payment_confirmation",
                subject: "Payment Confirmed: Official Tax Invoice & Subscription Receipt for {{org_name}}",
                preheader: "Your subscription payment has been verified and approved. Invoice PDF attached.",
                heading: "Subscription Payment & Tax Invoice Receipt",
                banner_color: "#16a34a",
                body_html: "<p>Dear <strong>{{user_name}}</strong>,</p>\n<p>Thank you for your payment! We are pleased to confirm that your subscription payment for <strong>{{org_name}}</strong> has been successfully verified and approved.</p>\n<div style=\"background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 6px; padding: 16px; margin: 18px 0;\">\n    <strong>Payment &amp; Subscription Details:</strong><br>\n    • Organization: <strong>{{org_name}}</strong><br>\n    • Activated Plan: <strong>{{plan_name}}</strong> ({{billing_cycle}})<br>\n    • Amount Paid: <strong>INR {{amount}}</strong><br>\n    • Transaction Reference: <strong>{{transaction_id}}</strong><br>\n    • Subscription Expiry: <strong>{{expiry_date}}</strong>\n</div>\n<p>Your official computer-generated <strong>Tax Invoice PDF</strong> has been generated and attached directly to this email for your accounting records.</p>",
                cta_text: "Access Your Enterprise Portal",
                cta_url: "{{app_url}}/admin/settings.html?tab=billing",
                channel_key: "billing",
                trigger_type: "event",
                event_trigger: "payment_approved",
                trigger_days_before: 0
            },
            'payment_rejection': {
                name: "Offline Payment Verification Declined Notice",
                category: "payment_rejection",
                subject: "Payment Verification Update for {{org_name}} – Decision Notice",
                preheader: "Important update regarding your offline payment submission for {{plan_name}}.",
                heading: "Payment Proof Verification Declined",
                banner_color: "#dc2626",
                body_html: "<p>Dear <strong>{{user_name}}</strong>,</p>\n<p>Our finance team reviewed your payment submission for <strong>{{org_name}}</strong> (Ref: <strong>{{transaction_id}}</strong>), but could not approve it for the following reason:</p>\n<div style=\"background: #fef2f2; border: 1px solid #fecaca; border-radius: 6px; padding: 16px; margin: 18px 0; color: #991b1b;\">\n    <strong>Reason for Rejection:</strong><br>\n    <em>{{rejection_reason}}</em>\n</div>\n<p>Please review your payment details or upload a clear transaction screenshot with a valid bank UTR reference number.</p>",
                cta_text: "Resubmit Payment Proof / Retry",
                cta_url: "{{app_url}}/admin/settings.html?tab=billing",
                channel_key: "billing",
                trigger_type: "event",
                event_trigger: "payment_rejected",
                trigger_days_before: 0
            },
            'subscription_reminder': {
                name: "Subscription Expiry Reminder (7 Days)",
                category: "subscription_reminder",
                subject: "Action Required: Your {{plan_name}} subscription expires in 7 days",
                preheader: "Renew now to ensure uninterrupted team access to QCMS Enterprise OS.",
                heading: "Your Subscription is Expiring Soon",
                banner_color: "#2563eb",
                body_html: "<p>Dear <strong>{{user_name}}</strong>,</p>\n<p>This is a courtesy reminder that your organization's <strong>{{plan_name}}</strong> subscription for <strong>{{org_name}}</strong> will expire in <strong>{{days_left}} days</strong> on <strong>{{expiry_date}}</strong>.</p>\n<p>To avoid any disruption to your team's quality workflows and audit logs, please renew or upgrade your subscription plan today.</p>",
                cta_text: "Renew / Upgrade Plan Now",
                cta_url: "{{app_url}}/admin/settings.html?tab=billing",
                channel_key: "billing",
                trigger_type: "event",
                event_trigger: "subscription_expiring_soon",
                trigger_days_before: 7
            },
            'subscription_urgent': {
                name: "Subscription Expiry Urgent Notice (1 Day)",
                category: "subscription_reminder",
                subject: "URGENT: Your {{plan_name}} subscription expires tomorrow",
                preheader: "Immediate action required: Subscription for {{org_name}} expires in 24 hours.",
                heading: "Urgent: Final Subscription Expiry Notice",
                banner_color: "#dc2626",
                body_html: "<p>Dear <strong>{{user_name}}</strong>,</p>\n<p>Your subscription for <strong>{{org_name}}</strong> is scheduled to expire <strong>tomorrow, {{expiry_date}}</strong>.</p>\n<p>Please complete your payment checkout immediately using our instant payment options (UPI, Razorpay, Bank Transfer).</p>",
                cta_text: "Complete Immediate Renewal",
                cta_url: "{{app_url}}/admin/settings.html?tab=billing",
                channel_key: "billing",
                trigger_type: "event",
                event_trigger: "subscription_expiring_soon",
                trigger_days_before: 1
            },
            'trial_reminder': {
                name: "Trial Plan Ending Reminder (3 Days)",
                category: "trial_reminder",
                subject: "Your free trial for {{org_name}} ends in 3 days – Upgrade today!",
                preheader: "Keep your quality data, audits, and projects active with an enterprise plan.",
                heading: "Your Free Trial is Ending Soon",
                banner_color: "#d97706",
                body_html: "<p>Hello <strong>{{user_name}}</strong>,</p>\n<p>We hope your team is enjoying exploring <strong>QCMS Enterprise OS</strong>! Your free onboarding trial for <strong>{{org_name}}</strong> will conclude in <strong>{{days_left}} days</strong> on <strong>{{expiry_date}}</strong>.</p>\n<p>Upgrade to a commercial plan today to unlock unlimited projects, increased storage capacity, and full team collaboration.</p>",
                cta_text: "Explore Plans & Upgrade",
                cta_url: "{{app_url}}/admin/settings.html?tab=billing",
                channel_key: "billing",
                trigger_type: "event",
                event_trigger: "trial_expiring_soon",
                trigger_days_before: 3
            },
            'maintenance': {
                name: "Scheduled Software Maintenance & Downtime Notice",
                category: "maintenance",
                subject: "Scheduled Platform Maintenance Notice: QCMS Enterprise OS",
                preheader: "Notice of scheduled maintenance to enhance performance and security.",
                heading: "Scheduled System Maintenance",
                banner_color: "#4f46e5",
                body_html: "<p>Dear <strong>{{user_name}}</strong>,</p>\n<p>To ensure optimal platform reliability and security, we have scheduled a planned maintenance window on Sunday 02:00 AM – 04:00 AM IST.</p>\n<p>All data and project records remain completely secure.</p>",
                cta_text: "Check System Status",
                cta_url: "{{app_url}}/dashboard/dashboard-admin.html",
                channel_key: "alerts",
                trigger_type: "manual"
            },
            'welcome': {
                name: "Welcome & New Organization Registration Guide",
                category: "welcome",
                subject: "Welcome to QCMS Enterprise OS – Essential Onboarding & Setup Guide for {{org_name}}",
                preheader: "Welcome aboard {{org_name}}! Here is your complete administrator quickstart guide, trial details, and role manual.",
                heading: "Welcome to QCMS Enterprise Quality Management OS",
                banner_color: "#16a34a",
                body_html: "<p>Dear <strong>{{user_name}}</strong>,</p>\n<p>Congratulations and welcome to <strong>QCMS Enterprise OS</strong>! Your organization workspace for <strong>{{org_name}}</strong> has been successfully provisioned and is active.</p>\n<div style=\"background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 18px 20px; margin: 20px 0;\">\n    <div style=\"font-size: 15px; font-weight: bold; color: #166534; margin-bottom: 8px;\">🎯 Your Active Workspace &amp; Trial Plan Summary</div>\n    <table style=\"width: 100%; border-collapse: collapse; font-size: 13px; color: #1e293b;\">\n        <tr><td style=\"padding: 4px 0; width: 45%; color: #64748b;\">• <strong>Organization Name:</strong></td><td style=\"padding: 4px 0; font-weight: 600;\">{{org_name}}</td></tr>\n        <tr><td style=\"padding: 4px 0; color: #64748b;\">• <strong>Assigned Plan:</strong></td><td style=\"padding: 4px 0; font-weight: 600; color: #16a34a;\">{{plan_name}} (Free Trial)</td></tr>\n        <tr><td style=\"padding: 4px 0; color: #64748b;\">• <strong>Trial Period &amp; Validity:</strong></td><td style=\"padding: 4px 0; font-weight: 600;\">{{trial_days}} Days (Valid until {{trial_end_date}})</td></tr>\n        <tr><td style=\"padding: 4px 0; color: #64748b;\">• <strong>Team Capacity:</strong></td><td style=\"padding: 4px 0; font-weight: 600;\">Up to {{max_users}} User Accounts</td></tr>\n    </table>\n</div>\n<p>Log in to your admin portal and start building your 8-stage quality projects today!</p>",
                cta_text: "Access Administrator Dashboard",
                cta_url: "{{app_url}}/auth/login.html",
                channel_key: "onboarding",
                trigger_type: "event",
                event_trigger: "new_org_welcome"
            },
            'usage_guide': {
                name: "How to Use QCMS: 8-Stage Quality Workflow Guide",
                category: "usage_guide",
                subject: "Mastering the 8-Stage Problem Solving Workflow in QCMS",
                preheader: "Tips & best practices to accelerate quality improvement projects with your team.",
                heading: "Software Guide: 8-Stage Quality Methodology",
                banner_color: "#0284c7",
                body_html: "<p>Hello <strong>{{user_name}}</strong>,</p>\n<p>Discover how to leverage QCMS's built-in 8-Stage workflow for root cause analysis (Ishikawa & 5-Why) and corrective actions.</p>",
                cta_text: "Open Knowledge Base",
                cta_url: "{{app_url}}/projects/repository.html",
                channel_key: "general",
                trigger_type: "manual"
            },
            'new_feature': {
                name: "New Features & Release Notes Announcement",
                category: "new_feature",
                subject: "What's New in QCMS: New Features & Performance Enhancements",
                preheader: "Check out the latest updates, customizable permissions, and reporting tools.",
                heading: "New Platform Features & Updates",
                banner_color: "#8b5cf6",
                body_html: "<p>Dear <strong>{{user_name}}</strong>,</p>\n<p>We are excited to share the latest updates including Granular Role Access Control and Centralized Document Identity now live in your workspace!</p>",
                cta_text: "Explore New Features",
                cta_url: "{{app_url}}",
                channel_key: "general",
                trigger_type: "manual"
            },
            'support': {
                name: "Customer Support & Success Check-in",
                category: "support",
                subject: "How is your experience with QCMS? We're here to help!",
                preheader: "Connect with our dedicated support engineers for assistance or custom workflow setup.",
                heading: "Dedicated Support & Customer Success",
                banner_color: "#0d9488",
                body_html: "<p>Hello <strong>{{user_name}}</strong>,</p>\n<p>If you have any questions regarding system setup, user onboarding, or reporting, our dedicated technical team is available 24/7 to assist you.</p>",
                cta_text: "Open Support Helpdesk",
                cta_url: "{{app_url}}/admin/super-admin.html?view=support",
                channel_key: "support",
                trigger_type: "manual"
            },
            'project_assignment': {
                name: "Project Assignment & Kickoff Notification",
                category: "project_assignment",
                subject: "Assigned to Project: {{project_title}} ({{project_code}}) – {{assigned_role}}",
                preheader: "You have been assigned to project {{project_title}} in {{org_name}}.",
                heading: "New Project Assignment & Kickoff",
                banner_color: "#2563eb",
                body_html: "<p>Dear <strong>{{user_name}}</strong>,</p>\n<p>You have been assigned as <strong>{{assigned_role}}</strong> for the quality project <strong>{{project_title}}</strong> in <strong>{{org_name}}</strong>.</p>\n<div style=\"background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 16px; margin: 18px 0;\">\n    <strong>Project Overview:</strong><br>\n    • <strong>Project Code:</strong> {{project_code}}<br>\n    • <strong>Project Title:</strong> {{project_title}}<br>\n    • <strong>Category:</strong> {{project_category}}<br>\n    • <strong>Created By:</strong> {{created_by_name}}<br>\n    • <strong>Your Assigned Role:</strong> {{assigned_role}}<br>\n    • <strong>Problem Statement:</strong> {{problem_statement}}\n</div>\n<p>Please log in to your QCMS workspace to begin collaborating on Stage 1 (Problem Definition) and progress through the 8-Stage Problem Solving Workflow.</p>",
                cta_text: "Open Project & Start Stage 1",
                cta_url: "{{app_url}}/auth/login.html?redirect=/projects/workspace.html?id={{project_id}}",
                channel_key: "general",
                trigger_type: "event",
                event_trigger: "project_assigned"
            },
            'project_completion': {
                name: "Project Completion, Approval & Improvement Report",
                category: "project_completion",
                subject: "Project Successfully Approved & Completed: {{project_title}} ({{project_code}})",
                preheader: "Project {{project_title}} has achieved final Stage 8 approval and closure.",
                heading: "Congratulations! Project Officially Completed & Approved",
                banner_color: "#16a34a",
                body_html: "<p>Dear <strong>{{user_name}}</strong>,</p>\n<p>Congratulations to you and the entire project team! The quality improvement project <strong>{{project_title}}</strong> ({{project_code}}) has successfully received <strong>Final Reviewer Approval &amp; Official Closure</strong> across all 8 stages.</p>\n<div style=\"background: rgba(22,163,74,0.06); border: 1px solid rgba(22,163,74,0.25); border-radius: 6px; padding: 16px; margin: 18px 0;\">\n    <strong>Executive Summary &amp; Key Improvements:</strong><br>\n    • <strong>Project:</strong> {{project_title}} ({{project_code}})<br>\n    • <strong>Organization:</strong> {{org_name}}<br>\n    • <strong>Problem Addressed:</strong> {{problem_statement}}<br>\n    • <strong>Root Causes Resolved:</strong> Ishikawa &amp; 5-Why analysis verified.<br>\n    • <strong>Standardization:</strong> SOPs deployed and horizontal rollout established.<br>\n    • <strong>Final Status:</strong> Approved &amp; Archived in QCMS Knowledge Repository\n</div>\n<p>Your team's dedication to continuous quality improvement and rigorous compliance has delivered measurable impact. The complete approved project dossier is available in your Knowledge Repository.</p>",
                cta_text: "View Final Approved Project Report",
                cta_url: "{{app_url}}/auth/login.html?redirect=/projects/repository.html?project_id={{project_id}}",
                channel_key: "general",
                trigger_type: "event",
                event_trigger: "project_completed"
            }
        };

        const p = presets[presetKey];
        if (!p) return;

        if (document.getElementById('enRuleName')) document.getElementById('enRuleName').value = p.name;
        if (document.getElementById('enCategory')) document.getElementById('enCategory').value = p.category;
        if (document.getElementById('enSubject')) document.getElementById('enSubject').value = p.subject;
        if (document.getElementById('enPreheader')) document.getElementById('enPreheader').value = p.preheader || '';
        if (document.getElementById('enBannerColor')) document.getElementById('enBannerColor').value = p.banner_color || '#2563eb';
        if (document.getElementById('enColorHexText')) document.getElementById('enColorHexText').textContent = p.banner_color || '#2563eb';
        if (document.getElementById('enBodyHtml')) document.getElementById('enBodyHtml').value = p.body_html;
        if (document.getElementById('enCtaText')) document.getElementById('enCtaText').value = p.cta_text || '';
        if (document.getElementById('enCtaUrl')) document.getElementById('enCtaUrl').value = p.cta_url || '';

        // Dynamically resolve sender identity from live Contact Directory channels & branding
        const channels = (this.cachedEmailMeta && this.cachedEmailMeta.contact_directory_channels) || [];
        const matchedChannel = channels.find(c => c.key === p.channel_key) || channels.find(c => c.key === 'general');
        if (matchedChannel) {
            if (document.getElementById('enSenderEmail')) document.getElementById('enSenderEmail').value = matchedChannel.email;
            if (document.getElementById('enSenderName')) document.getElementById('enSenderName').value = matchedChannel.name;
            if (document.getElementById('enContactChannelSelect')) document.getElementById('enContactChannelSelect').value = matchedChannel.key;
        }

        if (document.getElementById('enTriggerType')) {
            document.getElementById('enTriggerType').value = p.trigger_type || 'manual';
            this.onTriggerTypeChange(p.trigger_type || 'manual');
        }
        if (p.event_trigger && document.getElementById('enEventTrigger')) {
            document.getElementById('enEventTrigger').value = p.event_trigger;
            this.onEventTriggerChange(p.event_trigger);
        }
        if (p.trigger_days_before !== undefined && document.getElementById('enTriggerDays')) {
            document.getElementById('enTriggerDays').value = p.trigger_days_before;
        }
        if (document.getElementById('enPresetTemplateSelect')) document.getElementById('enPresetTemplateSelect').value = presetKey;

        this.updateLiveFormPreview();
        QCMS.toast(`Preset "${p.name}" loaded with Contact Directory sender identity.`, 'info');
    },

    async updateLiveFormPreview() {
        const frame = document.getElementById('enLivePreviewFrame');
        if (!frame) return;

        const payload = {
            name: document.getElementById('enRuleName')?.value || 'Notification',
            category: document.getElementById('enCategory')?.value || 'custom',
            subject: document.getElementById('enSubject')?.value || 'Notification Subject',
            preheader: document.getElementById('enPreheader')?.value || '',
            heading: document.getElementById('enSubject')?.value || 'Notification',
            body_html: document.getElementById('enBodyHtml')?.value || '<p>Your email body content will appear here.</p>',
            banner_color: document.getElementById('enBannerColor')?.value || '#2563eb',
            cta_text: document.getElementById('enCtaText')?.value || '',
            cta_url: document.getElementById('enCtaUrl')?.value || '',
            sender_email: document.getElementById('enSenderEmail')?.value || 'notifications@qcms.com',
            sender_name: document.getElementById('enSenderName')?.value || 'QCMS Enterprise Notifications'
        };

        try {
            const res = await api.post('/email-notifications/preview', payload);
            if (res && res.html) {
                frame.innerHTML = `<iframe srcdoc="${QCMS.escapeHtml(res.html)}" style="width:100%; height:220px; border:none; border-radius:6px;"></iframe>`;
            }
        } catch (e) {
            frame.innerHTML = `<div class="text-danger text-center py-3 text-xs">Preview render error: ${e.message}</div>`;
        }
    },

    async saveEmailRule(ruleId = null) {
        const targetOrgIds = Array.from(document.querySelectorAll('.en-org-checkbox:checked')).map(cb => parseInt(cb.value));
        const targetRoles = Array.from(document.querySelectorAll('.en-role-checkbox:checked')).map(cb => cb.value);
        const targetStatuses = Array.from(document.querySelectorAll('.en-status-checkbox:checked')).map(cb => cb.value);

        const payload = {
            name: document.getElementById('enRuleName')?.value.trim(),
            category: document.getElementById('enCategory')?.value,
            sender_email: document.getElementById('enSenderEmail')?.value.trim(),
            sender_name: document.getElementById('enSenderName')?.value.trim(),
            reply_to: document.getElementById('enReplyTo')?.value.trim() || null,
            subject: document.getElementById('enSubject')?.value.trim(),
            preheader: document.getElementById('enPreheader')?.value.trim(),
            heading: document.getElementById('enSubject')?.value.trim(),
            banner_color: document.getElementById('enBannerColor')?.value,
            body_html: document.getElementById('enBodyHtml')?.value.trim(),
            cta_text: document.getElementById('enCtaText')?.value.trim() || null,
            cta_url: document.getElementById('enCtaUrl')?.value.trim() || null,
            trigger_type: document.getElementById('enTriggerType')?.value,
            event_trigger: document.getElementById('enEventTrigger')?.value || null,
            trigger_days_before: parseInt(document.getElementById('enTriggerDays')?.value || 7),
            scheduled_at: document.getElementById('enScheduledAt')?.value || null,
            target_audience_type: document.getElementById('enAudienceType')?.value,
            target_org_ids: targetOrgIds,
            target_roles: targetRoles,
            target_statuses: targetStatuses,
            is_active: true
        };

        if (!payload.name || !payload.subject || !payload.body_html) {
            QCMS.toast('Please fill in Rule Name, Subject, and Body HTML.', 'warning');
            return;
        }

        try {
            let res;
            if (ruleId) {
                res = await api.put(`/email-notifications/rules/${ruleId}`, payload);
            } else {
                res = await api.post('/email-notifications/rules', payload);
            }

            if (res && res.status === 'success') {
                QCMS.toast(res.message || 'Notification rule saved successfully!', 'success');
                const modalEl = document.getElementById('emailNotificationModal');
                if (modalEl) {
                    const bsModal = bootstrap.Modal.getInstance(modalEl);
                    if (bsModal) bsModal.hide();
                }
                const contentArea = document.getElementById('announcementContentArea');
                if (contentArea && this.currentTab === 'email-notifications') {
                    this.renderEmailNotificationsHub(contentArea);
                }
            }
        } catch (e) {
            QCMS.toast(e.message || 'Failed to save notification rule', 'error');
        }
    },

    async testFromForm() {
        const testEmail = prompt('Enter recipient email address to send test email preview:');
        if (!testEmail || !testEmail.trim()) return;

        const payload = {
            name: document.getElementById('enRuleName')?.value || 'Test',
            category: document.getElementById('enCategory')?.value || 'custom',
            sender_email: document.getElementById('enSenderEmail')?.value || 'notifications@qcms.com',
            sender_name: document.getElementById('enSenderName')?.value || 'QCMS Notifications',
            reply_to: document.getElementById('enReplyTo')?.value || null,
            subject: document.getElementById('enSubject')?.value || 'Test Subject',
            preheader: document.getElementById('enPreheader')?.value || '',
            heading: document.getElementById('enSubject')?.value || 'Test Heading',
            banner_color: document.getElementById('enBannerColor')?.value || '#2563eb',
            body_html: document.getElementById('enBodyHtml')?.value || '<p>Test email</p>',
            cta_text: document.getElementById('enCtaText')?.value || '',
            cta_url: document.getElementById('enCtaUrl')?.value || ''
        };

        try {
            // First save or preview
            const previewRes = await api.post('/email-notifications/preview', payload);
            QCMS.toast(`Dispatching test preview to ${testEmail.trim()}...`, 'info');
            // If rule has an ID we can use send-test endpoint
            alert(`Test email preview rendered successfully for: ${testEmail.trim()}`);
        } catch (e) {
            QCMS.toast(e.message || 'Failed to dispatch test email', 'error');
        }
    },

    async openTestEmailModal(ruleId) {
        const userStr = localStorage.getItem('user') || sessionStorage.getItem('user');
        const user = userStr ? JSON.parse(userStr) : {};
        const defaultEmail = user.email || 'harshithkd6@gmail.com';

        const testEmail = prompt('Send Test Email – Enter your destination email address:', defaultEmail);
        if (!testEmail || !testEmail.trim()) return;

        QCMS.toast(`Sending test email to ${testEmail.trim()}...`, 'info');
        try {
            const res = await api.post(`/email-notifications/rules/${ruleId}/send-test`, { email: testEmail.trim() });
            if (res && res.status === 'success') {
                QCMS.toast(res.message, 'success');
            } else {
                QCMS.toast(res.message || 'Test email failed', 'error');
            }
        } catch (e) {
            QCMS.toast(e.message || 'Failed to send test email', 'error');
        }
    },

    async triggerEmailRuleNow(ruleId) {
        try {
            QCMS.toast('Loading audience recipients...', 'info');
            const res = await api.get(`/email-notifications/rules/${ruleId}/recipients`);
            if (!res || res.status !== 'success') {
                QCMS.toast('Failed to load recipient details', 'error');
                return;
            }

            const data = res;
            let modalEl = document.getElementById('emailBroadcastConfirmModal');
            if (!modalEl) {
                const div = document.createElement('div');
                div.id = 'emailBroadcastConfirmModalContainer';
                document.body.appendChild(div);
            }

            const recipientsListHtml = (data.recipients && data.recipients.length > 0) ? `
                <div class="table-responsive rounded border mb-3" style="max-height: 240px; overflow-y: auto;">
                    <table class="table table-sm table-hover mb-0 text-xs">
                        <thead class="bg-light sticky-top">
                            <tr>
                                <th class="py-2 px-3">Recipient Name</th>
                                <th class="py-2 px-3">Email Address</th>
                                <th class="py-2 px-3">Role</th>
                                <th class="py-2 px-3">Organization</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${data.recipients.map(r => `
                                <tr>
                                    <td class="py-2 px-3 fw-semibold text-main">${QCMS.escapeHtml(r.name || 'User')}</td>
                                    <td class="py-2 px-3 font-monospace text-primary">${QCMS.escapeHtml(r.email)}</td>
                                    <td class="py-2 px-3"><span class="badge bg-secondary-subtle text-secondary font-normal">${QCMS.escapeHtml(r.role)}</span></td>
                                    <td class="py-2 px-3 text-secondary">${QCMS.escapeHtml(r.org_name || 'System')}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            ` : `
                <div class="alert alert-warning py-3 px-3 text-xs mb-3 d-flex align-items-center gap-2">
                    <i data-lucide="alert-triangle" style="width:16px;height:16px;" class="text-warning"></i>
                    <div>
                        <b>No active tenant users match your criteria.</b><br>
                        Check target roles/statuses or check <em>"Also send a copy to my administrator email"</em> below to test live delivery.
                    </div>
                </div>
            `;

            const container = document.getElementById('emailBroadcastConfirmModalContainer') || document.body;
            container.innerHTML = `
            <div class="modal fade" id="emailBroadcastConfirmModal" tabindex="-1" aria-hidden="true" data-bs-backdrop="static">
                <div class="modal-dialog modal-lg modal-dialog-centered">
                    <div class="modal-content" style="background:var(--ds-bg-card); border: 1px solid var(--ds-border-color); border-radius: var(--ds-radius-lg);">
                        <div class="modal-header border-bottom pb-3">
                            <div class="d-flex align-items-center gap-2">
                                <div class="p-2 rounded bg-primary-subtle text-primary">
                                    <i data-lucide="send" style="width:20px;height:20px;"></i>
                                </div>
                                <div>
                                    <h5 class="modal-title fw-bold mb-0">Confirm Email Broadcast Dispatch</h5>
                                    <div class="text-xxs text-secondary">Review campaign details and target recipients before broadcasting.</div>
                                </div>
                            </div>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body p-4">
                            <div class="p-3 rounded border bg-light-subtle mb-3">
                                <div class="row g-2 text-xs">
                                    <div class="col-md-7">
                                        <div class="text-secondary text-xxs font-semibold text-uppercase">Campaign Name</div>
                                        <div class="fw-bold text-main">${QCMS.escapeHtml(data.rule_name)}</div>
                                    </div>
                                    <div class="col-md-5">
                                        <div class="text-secondary text-xxs font-semibold text-uppercase">Sender Identity</div>
                                        <div class="fw-semibold text-main">${QCMS.escapeHtml(data.sender_name)} &lt;${QCMS.escapeHtml(data.sender_email)}&gt;</div>
                                    </div>
                                    <div class="col-12 mt-2 pt-2 border-top">
                                        <div class="text-secondary text-xxs font-semibold text-uppercase">Subject Line</div>
                                        <div class="font-monospace text-primary text-xs">${QCMS.escapeHtml(data.subject)}</div>
                                    </div>
                                </div>
                            </div>

                            <div class="d-flex align-items-center justify-content-between mb-2">
                                <div class="fw-bold text-xs text-uppercase text-secondary d-flex align-items-center gap-1.5">
                                    <i data-lucide="users" style="width:13px;height:13px;"></i> Target Recipients (${data.total_recipients})
                                </div>
                                <span class="badge bg-primary text-white text-xxs px-2 py-1">${data.total_recipients} Matched User(s)</span>
                            </div>

                            ${recipientsListHtml}

                            <div class="p-3 rounded border bg-white mb-2">
                                <div class="form-check text-xs">
                                    <input class="form-check-input" type="checkbox" id="enCcSuperAdminCheckbox" checked>
                                    <label class="form-check-label fw-semibold text-main" for="enCcSuperAdminCheckbox">
                                        Also send a live copy to my administrator email (${QCMS.escapeHtml(data.admin_email || 'harshithkd6@gmail.com')})
                                    </label>
                                    <div class="text-xxs text-secondary mt-0.5">Recommended: Ensures you receive a live copy of the broadcast in your active inbox.</div>
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer border-top d-flex justify-content-between p-3">
                            <button type="button" class="ds-btn ds-btn-secondary ds-btn-sm" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="ds-btn ds-btn-primary ds-btn-sm px-4" id="btnConfirmBroadcastDispatch" onclick="AnnouncementsModule.executeBroadcastDispatch(${ruleId})">
                                <i data-lucide="play" style="width:13px;height:13px;" class="me-1"></i> Confirm & Broadcast Now
                            </button>
                        </div>
                    </div>
                </div>
            </div>
            `;

            const modalInstance = new bootstrap.Modal(document.getElementById('emailBroadcastConfirmModal'));
            modalInstance.show();
            if (window.lucide) lucide.createIcons();
        } catch (e) {
            QCMS.toast(e.message || 'Failed to open broadcast confirmation', 'error');
        }
    },

    async executeBroadcastDispatch(ruleId) {
        const btn = document.getElementById('btnConfirmBroadcastDispatch');
        const ccAdmin = document.getElementById('enCcSuperAdminCheckbox') ? document.getElementById('enCcSuperAdminCheckbox').checked : false;

        if (btn) {
            btn.disabled = true;
            btn.innerHTML = `<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span> Broadcasting...`;
        }

        try {
            const res = await api.post(`/email-notifications/rules/${ruleId}/trigger-now`, {
                include_current_admin: ccAdmin
            });

            const modalEl = document.getElementById('emailBroadcastConfirmModal');
            if (modalEl) {
                const modalInst = bootstrap.Modal.getInstance(modalEl);
                if (modalInst) modalInst.hide();
            }

            if (res && res.status === 'success') {
                QCMS.toast(res.message || 'Notification broadcast successfully dispatched!', 'success');
                const contentArea = document.getElementById('announcementContentArea');
                if (contentArea && this.currentTab === 'email-notifications') {
                    this.renderEmailNotificationsHub(contentArea);
                }
            } else if (res && res.status === 'warning') {
                QCMS.toast(res.message, 'warning');
            } else {
                QCMS.toast(res.message || 'Broadcast completed with notice', 'info');
            }
        } catch (e) {
            QCMS.toast(e.message || 'Failed to trigger notification broadcast', 'error');
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = `<i data-lucide="play" style="width:13px;height:13px;" class="me-1"></i> Confirm & Broadcast Now`;
            }
        }
    },

    async openPreviewEmailModal(ruleId) {
        try {
            const res = await api.get(`/email-notifications/rules/${ruleId}`);
            if (!res || !res.data) return;
            const rule = res.data;

            const previewRes = await api.post('/email-notifications/preview', rule);
            const htmlContent = previewRes.html || '';

            let modalEl = document.getElementById('emailPreviewModal');
            if (!modalEl) {
                const div = document.createElement('div');
                div.id = 'emailPreviewModalContainer';
                document.body.appendChild(div);
            }

            const container = document.getElementById('emailPreviewModalContainer') || document.body;
            container.innerHTML = `
            <div class="modal fade" id="emailPreviewModal" tabindex="-1" aria-hidden="true">
                <div class="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable">
                    <div class="modal-content" style="background:var(--ds-bg-card); border: 1px solid var(--ds-border-color); border-radius: var(--ds-radius-lg);">
                        <div class="modal-header border-bottom d-flex align-items-center justify-content-between">
                            <div class="d-flex align-items-center gap-2">
                                <i data-lucide="mail-check" class="text-primary" style="width:20px;height:20px;"></i>
                                <h5 class="modal-title fw-bold mb-0">Email Preview: ${QCMS.escapeHtml(rule.name)}</h5>
                            </div>
                            <div class="d-flex align-items-center gap-2">
                                <div class="btn-group btn-group-sm" role="group">
                                    <button type="button" class="btn btn-outline-secondary active" id="btnPreviewDesktop" onclick="document.getElementById('previewIframe').style.maxWidth='100%'; this.classList.add('active'); document.getElementById('btnPreviewMobile').classList.remove('active');">Desktop</button>
                                    <button type="button" class="btn btn-outline-secondary" id="btnPreviewMobile" onclick="document.getElementById('previewIframe').style.maxWidth='390px'; this.classList.add('active'); document.getElementById('btnPreviewDesktop').classList.remove('active');">Mobile</button>
                                </div>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                        </div>
                        <div class="modal-body p-3 bg-light text-center" style="min-height: 480px;">
                            <div class="p-2.5 rounded border bg-white text-start text-xs mb-3 shadow-sm mx-auto" style="max-width: 600px;">
                                <div class="d-flex align-items-center gap-2 mb-1">
                                    <span class="text-muted text-xxs text-uppercase fw-bold" style="width:60px;">From:</span>
                                    <span class="fw-semibold text-main">${QCMS.escapeHtml(rule.sender_name)} &lt;${QCMS.escapeHtml(rule.sender_email)}&gt;</span>
                                </div>
                                <div class="d-flex align-items-center gap-2 mb-1">
                                    <span class="text-muted text-xxs text-uppercase fw-bold" style="width:60px;">Subject:</span>
                                    <span class="fw-bold text-main font-monospace">${QCMS.escapeHtml(rule.subject)}</span>
                                </div>
                                ${rule.preheader ? `
                                <div class="d-flex align-items-center gap-2">
                                    <span class="text-muted text-xxs text-uppercase fw-bold" style="width:60px;">Preheader:</span>
                                    <span class="text-secondary">${QCMS.escapeHtml(rule.preheader)}</span>
                                </div>` : ''}
                            </div>
                            <iframe id="previewIframe" srcdoc="${QCMS.escapeHtml(htmlContent)}" style="width:100%; max-width:100%; height:520px; border:1px solid #e2e8f0; border-radius:8px; background:#fff; transition: max-width 0.25s ease;" class="shadow-sm mx-auto"></iframe>
                        </div>
                        <div class="modal-footer border-top d-flex justify-content-between">
                            <button class="ds-btn ds-btn-outline ds-btn-sm" onclick="AnnouncementsModule.openTestEmailModal(${rule.id})">
                                <i data-lucide="send" style="width:13px;height:13px;" class="me-1"></i> Send Test Email
                            </button>
                            <button class="ds-btn ds-btn-secondary ds-btn-sm" data-bs-dismiss="modal">Close Preview</button>
                        </div>
                    </div>
                </div>
            </div>`;

            const modal = new bootstrap.Modal(document.getElementById('emailPreviewModal'));
            modal.show();
            if (window.lucide) lucide.createIcons();
        } catch (e) {
            QCMS.toast('Failed to load email preview', 'error');
        }
    },

    quickFilterRules(filterType) {
        const catSelect = document.getElementById('emailRuleCategoryFilter');
        const statusSelect = document.getElementById('emailRuleStatusFilter');
        const searchInput = document.getElementById('emailRuleSearchInput');

        if (filterType === 'active') {
            if (statusSelect) statusSelect.value = 'active';
            if (catSelect) catSelect.value = '';
            if (searchInput) searchInput.value = '';
        } else if (filterType === 'subscription') {
            if (statusSelect) statusSelect.value = '';
            if (catSelect) catSelect.value = 'subscription_reminder';
            if (searchInput) searchInput.value = '';
        }
        this.filterEmailRules();
    },

    openSubscriptionRulesModal() {
        const subscriptionRules = (this._emailRules || []).filter(r => 
            r.category === 'subscription_reminder' || r.category === 'trial_reminder'
        );

        let modalEl = document.getElementById('subscriptionRulesManagerModal');
        if (!modalEl) {
            const div = document.createElement('div');
            div.id = 'subscriptionRulesManagerModalContainer';
            document.body.appendChild(div);
        }

        const container = document.getElementById('subscriptionRulesManagerModalContainer') || document.body;

        const rulesListHtml = subscriptionRules.length > 0 ? subscriptionRules.map(rule => {
            const isTrial = rule.category === 'trial_reminder';
            const catBadge = isTrial
                ? `<span class="badge bg-warning-subtle text-warning font-semibold px-2 py-1"><i data-lucide="gift" style="width:11px;height:11px;" class="me-1"></i>Trial Ending</span>`
                : `<span class="badge bg-primary-subtle text-primary font-semibold px-2 py-1"><i data-lucide="clock" style="width:11px;height:11px;" class="me-1"></i>Subscription Expiry</span>`;

            const triggerText = (!rule.trigger_days_before || rule.trigger_days_before === 0)
                ? 'Immediate Dispatch'
                : `${rule.trigger_days_before} Day(s) Before ${isTrial ? 'Trial End' : 'Expiry'}`;

            return `
            <div class="p-3 rounded border bg-white mb-3 shadow-xs" style="border-left: 3px solid ${isTrial ? '#f59e0b' : '#2563eb'} !important;">
                <div class="d-flex align-items-center justify-content-between flex-wrap gap-2 mb-2">
                    <div class="d-flex align-items-center gap-2">
                        ${catBadge}
                        <span class="badge bg-light text-dark border text-xxs font-monospace">
                            <i data-lucide="zap" style="width:10px;height:10px;" class="me-1 text-warning"></i>${triggerText}
                        </span>
                        ${rule.is_system_preset ? `<span class="badge bg-secondary bg-opacity-10 text-muted px-2 py-0.5 text-xxs">System Preset</span>` : ''}
                    </div>
                    <div class="form-check form-switch m-0" title="Toggle Active / Paused">
                        <input class="form-check-input" type="checkbox" role="switch" ${rule.is_active ? 'checked' : ''} onchange="AnnouncementsModule.toggleEmailRule(${rule.id}, this)">
                    </div>
                </div>

                <div class="row g-2 align-items-center">
                    <div class="col-md-7">
                        <h6 class="fw-bold text-main mb-1 text-truncate">${QCMS.escapeHtml(rule.name)}</h6>
                        <div class="text-xs text-secondary font-monospace text-truncate" title="${QCMS.escapeHtml(rule.subject)}">
                            <span class="text-muted text-xxs text-uppercase fw-semibold">Subject:</span> ${QCMS.escapeHtml(rule.subject)}
                        </div>
                    </div>
                    <div class="col-md-5 text-md-end text-xxs text-muted">
                        <div>Sender: <strong>${QCMS.escapeHtml(rule.sender_email)}</strong></div>
                        <div>Audience: <strong>${QCMS.escapeHtml((rule.target_roles || []).join(', ') || 'All Roles')}</strong></div>
                    </div>
                </div>

                <div class="pt-2 mt-2 border-top d-flex align-items-center justify-content-between flex-wrap gap-2">
                    <div class="text-xxs text-muted">
                        <span class="badge bg-success-subtle text-success font-semibold px-2 py-0.5"><i data-lucide="check-circle-2" style="width:10px;height:10px;" class="me-1"></i>${rule.total_sent || 0} Sent</span>
                    </div>
                    <div class="d-flex align-items-center gap-1.5">
                        <button type="button" class="ds-btn ds-btn-outline ds-btn-sm py-1 px-2.5 text-xs" onclick="AnnouncementsModule.openTestEmailModal(${rule.id})">
                            <i data-lucide="send" style="width:11px;height:11px;" class="me-1"></i> Test
                        </button>
                        ${rule.trigger_type !== 'event' ? `
                        <button type="button" class="ds-btn ds-btn-primary ds-btn-sm py-1 px-2.5 text-xs" onclick="AnnouncementsModule.triggerEmailRuleNow(${rule.id})">
                            <i data-lucide="play" style="width:11px;height:11px;" class="me-1"></i> Send Now
                        </button>` : ''}
                        <button type="button" class="ds-btn ds-btn-secondary ds-btn-sm py-1 px-2.5 text-xs" onclick="bootstrap.Modal.getInstance(document.getElementById('subscriptionRulesManagerModal')).hide(); AnnouncementsModule.openEmailRuleModal(${rule.id});">
                            <i data-lucide="edit-3" style="width:11px;height:11px;" class="me-1"></i> Edit Rule
                        </button>
                        ${!rule.is_system_preset ? `
                        <button type="button" class="ds-btn ds-btn-danger ds-btn-sm py-1 px-2 text-xs" onclick="AnnouncementsModule.deleteEmailRule(${rule.id})">
                            <i data-lucide="trash-2" style="width:11px;height:11px;"></i>
                        </button>` : ''}
                    </div>
                </div>
            </div>`;
        }).join('') : `
            <div class="text-center py-5 text-muted border rounded bg-light-subtle">
                <i data-lucide="clock" style="width:36px;height:36px;" class="mb-2 text-warning opacity-50"></i>
                <p class="text-sm fw-semibold mb-1">No subscription rules configured yet</p>
                <p class="text-xs text-muted">Click "+ Create New Subscription Rule" below to set up automated expiry notices.</p>
            </div>
        `;

        container.innerHTML = `
        <div class="modal fade" id="subscriptionRulesManagerModal" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-xl modal-dialog-centered modal-dialog-scrollable">
                <div class="modal-content" style="background:var(--ds-bg-card); border: 1px solid var(--ds-border-color); border-radius: var(--ds-radius-lg);">
                    <div class="modal-header border-bottom d-flex align-items-center justify-content-between pb-3">
                        <div class="d-flex align-items-center gap-2">
                            <div class="p-2 rounded bg-warning-subtle text-warning">
                                <i data-lucide="clock" style="width:20px;height:20px;"></i>
                            </div>
                            <div>
                                <h5 class="modal-title fw-bold mb-0">Subscription &amp; Renewal Automation Rules</h5>
                                <div class="text-xxs text-secondary">Manage and customize automated reminder triggers, trial endings, and renewal notices for all organizations.</div>
                            </div>
                        </div>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>

                    <div class="modal-body p-4">
                        <div class="d-flex align-items-center justify-content-between flex-wrap gap-2 mb-3">
                            <div class="text-xs text-secondary">
                                Currently configured: <b>${subscriptionRules.length} Active Subscription Rule(s)</b>
                            </div>
                            <button type="button" class="ds-btn ds-btn-primary ds-btn-sm text-xs py-1.5 px-3" onclick="bootstrap.Modal.getInstance(document.getElementById('subscriptionRulesManagerModal')).hide(); AnnouncementsModule.openEmailRuleModal(null, 'subscription_reminder');">
                                <i data-lucide="plus-circle" style="width:13px;height:13px;" class="me-1"></i> + Create New Subscription Rule
                            </button>
                        </div>

                        ${rulesListHtml}
                    </div>

                    <div class="modal-footer border-top d-flex justify-content-between p-3">
                        <button type="button" class="ds-btn ds-btn-outline ds-btn-sm" onclick="bootstrap.Modal.getInstance(document.getElementById('subscriptionRulesManagerModal')).hide(); AnnouncementsModule.quickFilterRules('subscription');">
                            View In Main Board &rarr;
                        </button>
                        <button class="ds-btn ds-btn-secondary ds-btn-sm" data-bs-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        </div>`;

        const modal = new bootstrap.Modal(document.getElementById('subscriptionRulesManagerModal'));
        modal.show();
        if (window.lucide) lucide.createIcons();
    },

    _logPage: 1,
    _logPerPage: 10,
    _logSearch: '',
    _logSearchTimeout: null,
    _cachedLogsData: [],

    onLogsSearchInput(val) {
        this._logSearch = val || '';
        if (this._logSearchTimeout) clearTimeout(this._logSearchTimeout);
        this._logSearchTimeout = setTimeout(() => {
            this.loadLogsPage(1, true);
        }, 220);
    },

    async openEmailLogsModal() {
        this._logPage = 1;
        this._logSearch = '';

        let modalEl = document.getElementById('emailLogsModal');
        if (!modalEl) {
            const div = document.createElement('div');
            div.id = 'emailLogsModalContainer';
            document.body.appendChild(div);
        }

        const container = document.getElementById('emailLogsModalContainer') || document.body;
        container.innerHTML = `
        <div class="modal fade" id="emailLogsModal" tabindex="-1" aria-hidden="true" data-bs-backdrop="static">
            <div class="modal-dialog modal-xl modal-dialog-centered modal-dialog-scrollable">
                <div class="modal-content" style="background:var(--ds-bg-card); border: 1px solid var(--ds-border-color); border-radius: var(--ds-radius-lg);">
                    <div class="modal-header border-bottom d-flex align-items-center justify-content-between pb-3">
                        <div class="d-flex align-items-center gap-2">
                            <div class="p-2 rounded bg-primary-subtle text-primary">
                                <i data-lucide="scroll-text" style="width:20px;height:20px;"></i>
                            </div>
                            <div>
                                <h5 class="modal-title fw-bold mb-0">Email Delivery Logs & Audit History</h5>
                                <div class="text-xxs text-secondary">Complete audit history of automated email campaigns, target recipients, and delivery statuses.</div>
                            </div>
                        </div>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>

                    <div class="modal-body p-4" id="emailLogsModalBody">
                        <div class="text-center py-5">
                            <div class="spinner-border text-primary" role="status" style="width:2rem;height:2rem;"></div>
                            <p class="text-xs text-muted mt-2">Loading email delivery audit logs...</p>
                        </div>
                    </div>

                    <div class="modal-footer border-top d-flex justify-content-between align-items-center p-3" id="emailLogsModalFooter">
                        <div class="text-xs text-secondary" id="emailLogsPaginationInfo">Loading...</div>
                        <div class="d-flex align-items-center gap-2">
                            <button type="button" class="ds-btn ds-btn-outline ds-btn-sm" id="btnLogsPrevPage" onclick="AnnouncementsModule.changeLogsPage(-1)" disabled>
                                &larr; Previous
                            </button>
                            <span class="text-xs fw-bold px-2" id="logsPageIndicator">Page 1</span>
                            <button type="button" class="ds-btn ds-btn-outline ds-btn-sm" id="btnLogsNextPage" onclick="AnnouncementsModule.changeLogsPage(1)" disabled>
                                Next &rarr;
                            </button>
                            <button class="ds-btn ds-btn-secondary ds-btn-sm ms-2" data-bs-dismiss="modal">Close</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>`;

        const modal = new bootstrap.Modal(document.getElementById('emailLogsModal'));
        modal.show();
        if (window.lucide) lucide.createIcons();

        await this.loadLogsPage(1);
    },

    async loadLogsPage(page = 1, preserveFocus = false) {
        this._logPage = page;
        const body = document.getElementById('emailLogsModalBody');
        if (!body) return;

        if (!preserveFocus) {
            body.innerHTML = `
            <div class="text-center py-5">
                <div class="spinner-border text-primary" role="status" style="width:2rem;height:2rem;"></div>
                <p class="text-xs text-muted mt-2">Loading page ${page} of delivery logs...</p>
            </div>`;
        }

        try {
            const searchParam = encodeURIComponent(this._logSearch || '');
            const res = await api.get(`/email-notifications/logs?page=${page}&per_page=${this._logPerPage}&q=${searchParam}`);
            
            const logs = (res && res.data) ? res.data : [];
            this._cachedLogsData = logs;
            const total = res.total || 0;
            const totalPages = Math.max(1, res.pages || Math.ceil(total / this._logPerPage));

            // Update footer pagination controls
            const infoEl = document.getElementById('emailLogsPaginationInfo');
            const prevBtn = document.getElementById('btnLogsPrevPage');
            const nextBtn = document.getElementById('btnLogsNextPage');
            const pageIndicator = document.getElementById('logsPageIndicator');

            if (infoEl) {
                const startIdx = total > 0 ? (page - 1) * this._logPerPage + 1 : 0;
                const endIdx = Math.min(page * this._logPerPage, total);
                infoEl.innerHTML = `Showing <b>${startIdx}–${endIdx}</b> of <b>${total}</b> delivery log(s) &bull; 10 logs per page`;
            }
            if (prevBtn) prevBtn.disabled = page <= 1;
            if (nextBtn) nextBtn.disabled = page >= totalPages;
            if (pageIndicator) pageIndicator.textContent = `Page ${page} of ${totalPages}`;

            const unifiedSearchBoxHtml = `
                <div class="position-relative" style="min-width: 260px; max-width: 380px; width: 100%;">
                    <i data-lucide="search" class="position-absolute text-muted" style="width: 14px; height: 14px; left: 12px; top: 50%; transform: translateY(-50%); pointer-events: none;"></i>
                    <input type="text" class="form-control text-xs w-100" id="logsSearchInput" placeholder="Search by campaign, subject, sender..." value="${QCMS.escapeHtml(this._logSearch)}" oninput="AnnouncementsModule.onLogsSearchInput(this.value)" style="padding-left: 34px; padding-top: 6px; padding-bottom: 6px; border-radius: 8px; border: 1px solid var(--ds-border-color); background: #ffffff;">
                </div>
            `;

            if (!logs.length) {
                body.innerHTML = `
                <div class="mb-3 d-flex align-items-center justify-content-between gap-2">
                    ${unifiedSearchBoxHtml}
                </div>
                <div class="text-center py-5 text-muted border rounded bg-light-subtle">
                    <i data-lucide="inbox" style="width:36px;height:36px;" class="mb-2 text-secondary opacity-50"></i>
                    <p class="text-sm fw-semibold mb-1">No delivery logs found</p>
                    <p class="text-xs text-muted">When automated triggers fire or broadcasts are dispatched, audit records will appear here.</p>
                </div>`;
            } else {
                const rowsHtml = logs.map((l, idx) => {
                    const statusBadge = l.status === 'Delivered' 
                        ? `<span class="badge bg-success-subtle text-success font-semibold px-2 py-1"><i data-lucide="check-circle-2" style="width:10px;height:10px;" class="me-1"></i>Delivered</span>`
                        : (l.status === 'Partially Delivered' 
                            ? `<span class="badge bg-warning-subtle text-warning font-semibold px-2 py-1"><i data-lucide="alert-circle" style="width:10px;height:10px;" class="me-1"></i>Partial (${l.recipient_count})</span>`
                            : `<span class="badge bg-danger-subtle text-danger font-semibold px-2 py-1"><i data-lucide="x-circle" style="width:10px;height:10px;" class="me-1"></i>Failed</span>`);

                    const categoryBadge = `<span class="badge bg-secondary-subtle text-secondary font-normal text-xxs text-uppercase">${QCMS.escapeHtml((l.category || 'CUSTOM').replace('_', ' '))}</span>`;

                    return `
                    <tr style="cursor: pointer; transition: background 0.15s ease;" class="log-row-hover" onclick="AnnouncementsModule.openLogDetail(${l.id})" title="Click to view detailed recipients and organization breakdown">
                        <td class="py-3 px-3">
                            <div class="d-flex align-items-center gap-2">
                                <div>
                                    <div class="fw-bold text-main text-xs">${QCMS.escapeHtml(l.rule_name)}</div>
                                    <div class="mt-0.5">${categoryBadge}</div>
                                </div>
                            </div>
                        </td>
                        <td class="py-3 px-3">
                            <div class="text-xs text-primary font-monospace text-truncate" style="max-width:260px;" title="${QCMS.escapeHtml(l.subject)}">${QCMS.escapeHtml(l.subject)}</div>
                        </td>
                        <td class="py-3 px-3">
                            <div class="text-xs fw-semibold text-main">${QCMS.escapeHtml(l.sender_name || 'QCMS Engine')}</div>
                            <div class="text-xxs text-muted font-monospace">${QCMS.escapeHtml(l.sender_email)}</div>
                        </td>
                        <td class="py-3 px-3 text-center">
                            <span class="badge bg-primary-subtle text-primary font-semibold px-2.5 py-1 text-xs">
                                <i data-lucide="users" style="width:11px;height:11px;" class="me-1"></i>${l.recipient_count} Recipient(s)
                            </span>
                        </td>
                        <td class="py-3 px-3 text-center">${statusBadge}</td>
                        <td class="py-3 px-3">
                            <div class="text-xs text-secondary">${new Date(l.sent_at).toLocaleString()}</div>
                            <div class="text-xxs text-muted"><i data-lucide="user-check" style="width:10px;height:10px;" class="me-1"></i>${QCMS.escapeHtml(l.sent_by)}</div>
                        </td>
                        <td class="py-3 px-3 text-end">
                            <button type="button" class="ds-btn ds-btn-outline ds-btn-sm py-1 px-2 text-xxs" onclick="event.stopPropagation(); AnnouncementsModule.openLogDetail(${l.id})">
                                <i data-lucide="eye" style="width:11px;height:11px;" class="me-1"></i> View Details
                            </button>
                        </td>
                    </tr>`;
                }).join('');

                body.innerHTML = `
                <div class="d-flex flex-column gap-3">
                    <div class="d-flex align-items-center justify-content-between flex-wrap gap-2">
                        ${unifiedSearchBoxHtml}
                        <div class="d-flex align-items-center gap-2">
                            <span class="badge bg-light text-dark border text-xs px-2.5 py-1.5"><i data-lucide="table" style="width:12px;height:12px;" class="me-1 text-primary"></i> 10 Logs / Page</span>
                            <button type="button" class="ds-btn ds-btn-outline ds-btn-sm text-xs py-1 px-2.5" onclick="AnnouncementsModule.loadLogsPage(${page})" title="Refresh logs list">
                                <i data-lucide="refresh-cw" style="width:12px;height:12px;"></i>
                            </button>
                        </div>
                    </div>

                    <div class="table-responsive rounded border">
                        <table class="table table-hover align-middle mb-0">
                            <thead class="bg-light-subtle border-bottom">
                                <tr class="text-xxs text-uppercase text-secondary font-semibold">
                                    <th class="py-2.5 px-3">Campaign / Rule</th>
                                    <th class="py-2.5 px-3">Subject Line</th>
                                    <th class="py-2.5 px-3">Sender Identity</th>
                                    <th class="py-2.5 px-3 text-center">Recipients</th>
                                    <th class="py-2.5 px-3 text-center">Status</th>
                                    <th class="py-2.5 px-3">Dispatched At</th>
                                    <th class="py-2.5 px-3 text-end">Action</th>
                                </tr>
                            </thead>
                            <tbody>${rowsHtml}</tbody>
                        </table>
                    </div>
                </div>`;
            }

            if (window.lucide) lucide.createIcons();

            if (preserveFocus) {
                const searchEl = document.getElementById('logsSearchInput');
                if (searchEl) {
                    searchEl.focus();
                    const len = searchEl.value.length;
                    searchEl.setSelectionRange(len, len);
                }
            }
        } catch (e) {
            body.innerHTML = `<div class="alert alert-danger p-3 text-xs">Failed to load logs: ${e.message}</div>`;
        }
    },

    changeLogsPage(delta) {
        const targetPage = this._logPage + delta;
        if (targetPage >= 1) {
            this.loadLogsPage(targetPage);
        }
    },

    openLogDetail(logId) {
        const log = (this._cachedLogsData || []).find(l => l.id === logId);
        if (!log) return;

        const body = document.getElementById('emailLogsModalBody');
        if (!body) return;

        const recipients = log.recipients_summary || [];

        const recipientRowsHtml = recipients.length > 0 ? recipients.map(r => {
            const statusBadge = r.status === 'Delivered'
                ? `<span class="badge bg-success-subtle text-success font-semibold px-2 py-0.5 text-xxs"><i data-lucide="check" style="width:10px;height:10px;" class="me-1"></i>Delivered</span>`
                : `<span class="badge bg-danger-subtle text-danger font-semibold px-2 py-0.5 text-xxs"><i data-lucide="x" style="width:10px;height:10px;" class="me-1"></i>Failed</span>`;

            return `
            <tr>
                <td class="py-2.5 px-3 fw-semibold text-main text-xs">${QCMS.escapeHtml(r.name || 'User')}</td>
                <td class="py-2.5 px-3 font-monospace text-primary text-xs">${QCMS.escapeHtml(r.email)}</td>
                <td class="py-2.5 px-3 text-xs">
                    <span class="badge bg-secondary-subtle text-secondary font-normal">${QCMS.escapeHtml(r.role || 'User')}</span>
                </td>
                <td class="py-2.5 px-3 text-xs text-secondary fw-semibold">
                    <i data-lucide="building-2" style="width:12px;height:12px;" class="me-1 text-primary"></i>${QCMS.escapeHtml(r.org || 'Platform Administration')}
                </td>
                <td class="py-2.5 px-3 text-center">${statusBadge}</td>
            </tr>`;
        }).join('') : `
            <tr>
                <td colspan="5" class="text-center py-4 text-muted text-xs">No detailed recipient rows recorded for this batch.</td>
            </tr>
        `;

        body.innerHTML = `
        <div class="fade-in d-flex flex-column gap-3">
            <div class="d-flex align-items-center justify-content-between pb-2 border-bottom">
                <button type="button" class="ds-btn ds-btn-outline ds-btn-sm text-xs py-1 px-3" onclick="AnnouncementsModule.loadLogsPage(${this._logPage})">
                    &larr; Back to All Delivery Logs
                </button>
                <div class="d-flex align-items-center gap-2">
                    <span class="badge bg-primary text-white text-xs px-2.5 py-1">Audit Record #${log.id}</span>
                    <span class="badge bg-success-subtle text-success text-xs px-2.5 py-1">${log.status}</span>
                </div>
            </div>

            <!-- Campaign Information Header Card -->
            <div class="p-3 rounded border bg-light-subtle">
                <div class="row g-3 text-xs">
                    <div class="col-md-6">
                        <div class="text-secondary text-xxs font-semibold text-uppercase">Campaign / Rule Name</div>
                        <div class="fw-bold text-main fs-6">${QCMS.escapeHtml(log.rule_name)}</div>
                        <div class="text-xxs text-muted mt-0.5">Category: <span class="badge bg-secondary-subtle text-secondary text-xxs">${QCMS.escapeHtml(log.category || 'custom')}</span></div>
                    </div>
                    <div class="col-md-6">
                        <div class="text-secondary text-xxs font-semibold text-uppercase">Sender Identity</div>
                        <div class="fw-bold text-main">${QCMS.escapeHtml(log.sender_name || 'QCMS Engine')} &lt;${QCMS.escapeHtml(log.sender_email)}&gt;</div>
                        <div class="text-xxs text-muted mt-0.5">Dispatched at: <b>${new Date(log.sent_at).toLocaleString()}</b> by <b>${QCMS.escapeHtml(log.sent_by)}</b></div>
                    </div>
                    <div class="col-12 pt-2 border-top">
                        <div class="text-secondary text-xxs font-semibold text-uppercase">Subject Line</div>
                        <div class="font-monospace text-primary text-xs fw-semibold">${QCMS.escapeHtml(log.subject)}</div>
                    </div>
                </div>
            </div>

            <!-- Recipients Breakdown Table -->
            <div class="d-flex align-items-center justify-content-between mt-1">
                <div class="fw-bold text-xs text-uppercase text-secondary d-flex align-items-center gap-1.5">
                    <i data-lucide="users" style="width:13px;height:13px;"></i> Dispatched Recipients &amp; Organizations (${recipients.length})
                </div>
                <span class="badge bg-primary-subtle text-primary text-xs px-2.5 py-1">${recipients.length} Total Delivered</span>
            </div>

            <div class="table-responsive rounded border" style="max-height: 320px; overflow-y: auto;">
                <table class="table table-hover align-middle mb-0">
                    <thead class="bg-light sticky-top border-bottom">
                        <tr class="text-xxs text-uppercase text-secondary font-semibold">
                            <th class="py-2.5 px-3">Recipient Name</th>
                            <th class="py-2.5 px-3">Email Address</th>
                            <th class="py-2.5 px-3">Role</th>
                            <th class="py-2.5 px-3">Organization</th>
                            <th class="py-2.5 px-3 text-center">Status</th>
                        </tr>
                    </thead>
                    <tbody>${recipientRowsHtml}</tbody>
                </table>
            </div>
        </div>`;

        if (window.lucide) lucide.createIcons();
    }
};

window.AnnouncementsModule = AnnouncementsModule;

