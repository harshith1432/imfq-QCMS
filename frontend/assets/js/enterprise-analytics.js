/**
 * Enterprise Analytics Platform JS Engine
 * single source of truth for both regular tenant and platform admin centers.
 */

const EnterpriseAnalytics = {
    currentTab: 'overview',
    filters: {
        date_range: 'Last 30 Days',
        organization: '',
        plan: '',
        country: '',
        industry: '',
        license_type: '',
        module: '',
        status: '',
        start_date: '',
        end_date: ''
    },
    charts: {},
    realtimeTimer: null,
    isSuperAdmin: false,
    userRole: 'Team Member',
    userPermissions: {},

    _formatINR(num) {
        if (window.QCMS && typeof QCMS.formatINR === 'function') {
            return QCMS.formatINR(num);
        }
        if (num === null || num === undefined || isNaN(num)) return '₹0';
        const val = Math.abs(Number(num));
        const sign = Number(num) < 0 ? '-' : '';
        return `${sign}₹${val.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
    },

    _toast(msg, type = 'info') {
        if (window.QCMS && typeof QCMS.toast === 'function') {
            QCMS.toast(msg, type);
        } else if (window.api && typeof api.showNotification === 'function') {
            api.showNotification(msg, type);
        } else {
            console.log(`[Toast ${type}] ${msg}`);
        }
    },

    async init(containerId, isSuper = false) {
        this.isSuperAdmin = isSuper;
        const profile = await this.getProfile();
        if (profile) {
            this.userRole = profile.role?.name || 'Team Member';
            const subRole = (profile.custom_fields || {}).get?.('super_admin_role') || (profile.custom_fields || {}).super_admin_role || 'Owner';
            this.userPermissions = {
                role: this.userRole,
                subRole: subRole
            };
        }
        
        this.renderLayout(containerId);
        this.bindEvents();
        await this.loadFiltersData();
        await this.refreshDashboard();
        this.startRealtimeUpdates();
    },

    async getProfile() {
        try {
            return await api.get('/auth/me');
        } catch (e) {
            console.error("Failed to load user profile", e);
            return null;
        }
    },

    renderLayout(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return;

        // Apply Premium Glassmorphism and Layout structure
        container.innerHTML = `
            <div class="enterprise-analytics-wrapper v-stack gap-2 px-3" style="margin-top: -12px;">
                
                <!-- KPI Grid -->
                <div class="w-100 pb-1" id="eaKpiGrid" style="margin-bottom: 10px !important;">
                    <!-- Loaded dynamically -->
                </div>


                <!-- Navigation Tabs -->
                <div class="ds-tab-group scroll-x flex-nowrap" style="position: relative; z-index: 1; border-bottom:1px solid rgba(255,255,255,0.08); width: 100%; max-width: 100%; overflow-x: auto; white-space: nowrap; margin-bottom: 18px !important;">
                    <button class="ds-tab active" id="ea-tab-overview" onclick="EnterpriseAnalytics.switchTab('overview')" style="padding: 6px 10px !important; gap: 4px !important; font-size: 11.5px;"><i data-lucide="layout" class="me-1" style="width:13px; height:13px;"></i> Overview</button>
                    <button class="ds-tab" id="ea-tab-revenue" onclick="EnterpriseAnalytics.switchTab('revenue')" style="padding: 6px 10px !important; gap: 4px !important; font-size: 11.5px;"><i data-lucide="indian-rupee" class="me-1" style="width:13px; height:13px;"></i> Revenue</button>
                    ${this.isSuperAdmin ? `<button class="ds-tab" id="ea-tab-organizations" onclick="EnterpriseAnalytics.switchTab('organizations')" style="padding: 6px 10px !important; gap: 4px !important; font-size: 11.5px;"><i data-lucide="building" class="me-1" style="width:13px; height:13px;"></i> Tenants</button>` : ''}
                    <button class="ds-tab" id="ea-tab-support" onclick="EnterpriseAnalytics.switchTab('support')" style="padding: 6px 10px !important; gap: 4px !important; font-size: 11.5px;"><i data-lucide="life-buoy" class="me-1" style="width:13px; height:13px;"></i> Support</button>
                </div>

                <!-- Tab Contents -->
                <div class="ea-tab-content-container" id="eaTabContent" style="margin-top: 6px !important;">
                    <!-- Dynamic rendering -->
                </div>
            </div>
            
            <!-- Custom Date Modal -->
            <div class="modal fade" id="customDateModal" tabindex="-1">
                <div class="modal-dialog modal-dialog-centered" style="max-width:400px;">
                    <div class="modal-content glass-card" style="background: var(--ds-bg-surface, #ffffff); border: 1px solid var(--ds-border-color, #cbd5e1); color: var(--ds-text-main, #0f172a); border-radius: 16px; box-shadow: 0 20px 40px rgba(0,0,0,0.25);">
                        <div class="modal-header border-0 pb-0">
                            <h5 class="modal-title fw-bold" style="color:var(--ds-text-main);">Custom Date Range</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <div class="v-stack gap-3">
                                <div class="ds-field">
                                    <label class="ds-label">Start Date</label>
                                    <input type="date" class="ds-input" id="customStartDate">
                                </div>
                                <div class="ds-field">
                                    <label class="ds-label">End Date</label>
                                    <input type="date" class="ds-input" id="customEndDate">
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer border-0">
                            <button class="ds-btn ds-btn-outline ds-btn-sm" data-bs-dismiss="modal">Cancel</button>
                            <button class="ds-btn ds-btn-primary ds-btn-sm" onclick="EnterpriseAnalytics.applyCustomDate()">Apply</button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Custom Report Builder Modal -->
            <div class="modal fade" id="reportBuilderModal" tabindex="-1">
                <div class="modal-dialog modal-lg modal-dialog-centered">
                    <div class="modal-content glass-card" style="background: var(--ds-bg-surface, #ffffff); border: 1px solid var(--ds-border-color, #cbd5e1); color: var(--ds-text-main, #0f172a); border-radius: 16px; box-shadow: 0 20px 40px rgba(0,0,0,0.25);">
                        <div class="modal-header border-0 pb-0">
                            <h5 class="modal-title fw-bold" style="color:var(--ds-text-main);"><i data-lucide="sliders" class="me-2 text-primary"></i> Custom Report Builder</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body pb-0">
                            <div class="row g-4">
                                <div class="col-md-6">
                                    <div class="ds-field mb-3">
                                        <label class="ds-label">Report Title</label>
                                        <input type="text" class="ds-input" id="reportTitle" placeholder="e.g. Q3 Regional User Growth">
                                    </div>
                                    <div class="ds-field mb-3">
                                        <label class="ds-label">Description</label>
                                        <textarea class="ds-input" id="reportDesc" rows="2" placeholder="Describe the purpose of this report..."></textarea>
                                    </div>
                                    <div class="ds-field mb-3">
                                        <label class="ds-label">Select Metrics</label>
                                        <div class="v-stack gap-2 bg-dark-50 p-2.5 rounded" style="max-height:180px; overflow-y:auto; border:1px solid var(--ds-border-color);">
                                            <label class="text-sm cursor-pointer d-flex align-items-center"><input type="checkbox" value="revenue" class="report-metric me-2"> Completed Revenue</label>
                                            <label class="text-sm cursor-pointer d-flex align-items-center"><input type="checkbox" value="mrr" class="report-metric me-2"> Monthly Recurring Revenue (MRR)</label>
                                            <label class="text-sm cursor-pointer d-flex align-items-center"><input type="checkbox" value="arr" class="report-metric me-2"> Annual Recurring Revenue (ARR)</label>
                                            <label class="text-sm cursor-pointer d-flex align-items-center"><input type="checkbox" value="active_users" class="report-metric me-2"> Active Users</label>
                                            <label class="text-sm cursor-pointer d-flex align-items-center"><input type="checkbox" value="api_calls" class="report-metric me-2"> API Requests</label>
                                            <label class="text-sm cursor-pointer d-flex align-items-center"><input type="checkbox" value="storage" class="report-metric me-2"> Storage Footprint</label>
                                            <label class="text-sm cursor-pointer d-flex align-items-center"><input type="checkbox" value="support_tickets" class="report-metric me-2"> Support Ticket Volume</label>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-6">
                                    <div class="ds-field mb-3">
                                        <label class="ds-label">Group By</label>
                                        <select class="ds-input ds-select" id="reportGroupBy">
                                            <option value="month">Month (Trends)</option>
                                            <option value="plan">Subscription Plan</option>
                                            <option value="country">Country</option>
                                            <option value="industry">Industry</option>
                                            <option value="status">Status</option>
                                        </select>
                                    </div>
                                    <div class="ds-field mb-3">
                                        <label class="ds-label">Visualization Type</label>
                                        <select class="ds-input ds-select" id="reportChartType">
                                            <option value="line">Line Chart</option>
                                            <option value="bar">Bar Chart</option>
                                            <option value="pie">Pie Chart</option>
                                        </select>
                                    </div>
                                    <div class="ds-field mb-3">
                                        <label class="ds-label">Email Schedule</label>
                                        <select class="ds-input ds-select" id="reportSchedule">
                                            <option value="none">No Schedule</option>
                                            <option value="daily">Daily PDF</option>
                                            <option value="weekly">Weekly PDF</option>
                                            <option value="monthly">Monthly Excel</option>
                                        </select>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="modal-footer border-0">
                            <button class="ds-btn ds-btn-outline ds-btn-sm" data-bs-dismiss="modal">Cancel</button>
                            <button class="ds-btn ds-btn-primary ds-btn-sm" onclick="EnterpriseAnalytics.saveCustomReport()"><i data-lucide="check" class="me-1" style="width:14px;"></i> Save & Generate Report</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        if (window.lucide) lucide.createIcons();
    },

    bindEvents() {
        // Any specific event listeners
    },

    async loadFiltersData() {
        try {
            if (this.isSuperAdmin) {
                const orgData = await api.get('/super-admin/companies?page=1&per_page=200');
                // API returns { status, data: [...], pagination } 
                const orgs = orgData.data || orgData.organizations || [];
                const filterOrg = document.getElementById('filterOrg');
                if (filterOrg) {
                    filterOrg.innerHTML = '<option value="">All Tenants</option>' +
                        orgs.map(o => `<option value="${o.id}">${o.name}</option>`).join('');
                }
            }
        } catch (e) {
            console.error("Failed to load organizations for filters", e);
        }
    },

    setDateRange(range) {
        this.filters.date_range = range;
        const el1 = document.getElementById('selectedDateRange');
        if (el1) el1.textContent = range;
        document.querySelectorAll('.topHeaderDateRangeLabel').forEach(el => el.textContent = range);
        this.refreshDashboard();
    },

    setSearch(q) {
        if (this._searchTimer) clearTimeout(this._searchTimer);
        this._searchTimer = setTimeout(() => {
            const queryVal = (q || '').trim();
            this.filters.q = queryVal;
            this.filters.search = queryVal;
            this.refreshDashboard();
        }, 300);
    },

    showCustomDateModal() {
        const modalEl = document.getElementById('customDateModal');
        if (modalEl && modalEl.parentNode !== document.body) {
            document.body.appendChild(modalEl);
        }
        let modal = bootstrap.Modal.getInstance(modalEl);
        if (!modal) {
            modal = new bootstrap.Modal(modalEl);
        }
        modal.show();
    },

    applyCustomDate() {
        const start = document.getElementById('customStartDate').value;
        const end = document.getElementById('customEndDate').value;
        if (!start || !end) {
            this._toast('Please select both start and end dates', 'warning');
            return;
        }
        this.filters.date_range = 'Custom Range';
        this.filters.start_date = start;
        this.filters.end_date = end;
        const labelStr = `${start} to ${end}`;
        const el1 = document.getElementById('selectedDateRange');
        if (el1) el1.textContent = labelStr;
        document.querySelectorAll('.topHeaderDateRangeLabel').forEach(el => el.textContent = labelStr);
        
        bootstrap.Modal.getInstance(document.getElementById('customDateModal')).hide();
        this.refreshDashboard();
    },

    setFilter(key, value) {
        this.filters[key] = value;
        this.refreshDashboard();
    },

    buildQueryParams() {
        let params = new URLSearchParams();
        for (const [k, v] of Object.entries(this.filters)) {
            if (v) params.append(k, v);
        }
        return params.toString();
    },

    async refreshDashboard() {
        await this.loadKPIs();
        await this.loadTabContent();
    },

    async loadKPIs() {
        const grid = document.getElementById('eaKpiGrid');
        if (!grid) return;

        grid.innerHTML = Array(7).fill(0).map(() => `
            <div class="ea-kpi-card" style="height: 60px; justify-content: center;">
                <div class="spinner-border spinner-border-sm text-primary" role="status"></div>
            </div>
        `).join('');

        try {
            const query = this.buildQueryParams();
            const res = await api.get(`/analytics/enterprise/dashboard?${query}`);
            if (res.status === 'success') {
                const data = res.data;
                
                const formatVal = (key, val) => {
                    if (val === null || val === undefined) return '0';
                    if (key.includes('revenue') || key === 'mrr' || key === 'arr') {
                        return this._formatINR(val);
                    }
                    return val.toLocaleString ? val.toLocaleString() : String(val);
                };

                const cardColors = {
                    'total_revenue': '#10b981', // green
                    'mrr': '#2563eb', // blue
                    'arr': '#8b5cf6', // purple
                    'total_orgs': '#f59e0b', // orange
                    'active_users': '#f59e0b', // orange
                    'storage_usage': '#3b82f6', // blue
                    'api_usage': '#6366f1', // purple
                    'total_support_tickets': '#ef4444', // red
                };

                const cards = [
                    { id: 'total_revenue', title: 'Total Revenue', key: 'total_revenue', tab: 'revenue', desc: 'Total gross cumulative financial revenue earned across all subscriptions & plans.' },
                    { id: 'mrr', title: 'MRR (Monthly)', key: 'mrr', tab: 'revenue', desc: 'Monthly Recurring Revenue — predictable recurring income expected per month.' },
                    { id: 'arr', title: 'ARR (Annual)', key: 'arr', tab: 'revenue', desc: 'Annual Recurring Revenue — annualized financial projection over 12 months.' },
                    this.isSuperAdmin ? { id: 'total_orgs', title: 'Active Tenants', key: 'active_orgs', tab: 'organizations', desc: 'Total number of active customer organisations operating on the platform.' } : { id: 'active_users', title: 'Active Users', key: 'active_users', tab: 'users', desc: 'Total active user accounts across organisation workspaces.' },
                    { id: 'storage_usage', title: 'Platform Storage Usage', key: 'storage_usage', tab: 'overview', desc: 'Total cloud database storage & media file attachments consumed across the platform.' },
                    { id: 'total_support_tickets', title: 'Support Tickets', key: 'total_support_tickets', tab: 'support', desc: 'Total helpdesk support tickets and assistance requests submitted by users.' }
                ];

                grid.innerHTML = cards.map((c, index) => {
                    const card = data[c.key] || { value: 0, growth: 0, icon: 'info' };
                    const growthVal = parseFloat(card.growth || 0);
                    const growthClass = growthVal > 0 ? 'text-success' : (growthVal < 0 ? 'text-danger' : 'text-muted');
                    const growthIcon = growthVal > 0 ? 'trending-up' : (growthVal < 0 ? 'trending-down' : 'minus');
                    const growthText = growthVal > 0 ? `+${growthVal}%` : (growthVal < 0 ? `${growthVal}%` : `Steady`);
                    const cardColor = cardColors[c.id] || '#6b7280';
                    const alignClass = index === 0 ? 'align-left' : (index === cards.length - 1 ? 'align-right' : '');

                    return `
                        <div class="clickable transition" onclick="EnterpriseAnalytics.switchTab('${c.tab}')" style="flex: 1; min-width: 95px; position: relative;">
                            <div class="ea-kpi-card" title="${c.desc}">
                                <div class="kpi-icon" style="background: rgba(var(--ds-primary-rgb), 0.08);">
                                    <i data-lucide="${card.icon}" style="width:11px; height:11px; color:${cardColor};"></i>
                                </div>
                                <div class="kpi-label">${c.title}</div>
                                <div class="kpi-value">${formatVal(c.key, card.value)}</div>
                                <div class="kpi-accent" style="background:${cardColor};"></div>
                                <div class="ea-kpi-tooltip ${alignClass}">
                                    <div class="ea-kpi-tooltip-title" style="color: ${cardColor};">${c.title}</div>
                                    <div class="ea-kpi-tooltip-desc">${c.desc}</div>
                                </div>
                            </div>
                        </div>
                    `;
                }).join('');
                if (window.lucide) lucide.createIcons();
            }
        } catch (e) {
            console.error(e);
            grid.innerHTML = `<div class="col-12"><div class="alert alert-danger">Error loading KPI stats. Please verify connections.</div></div>`;
        }
    },

    switchTab(tabId) {
        this.currentTab = tabId;
        document.querySelectorAll('.ds-tab').forEach(t => t.classList.remove('active'));
        const activeTab = document.getElementById(`ea-tab-${tabId}`);
        if (activeTab) activeTab.classList.add('active');
        
        this.loadTabContent();
    },

    async loadTabContent() {
        const content = document.getElementById('eaTabContent');
        if (!content) return;

        // Destroy previous charts
        Object.keys(this.charts).forEach(k => {
            if (this.charts[k]) { this.charts[k].destroy(); delete this.charts[k]; }
        });

        content.innerHTML = `
            <div class="d-flex justify-content-center p-5">
                <div class="spinner-border text-primary" role="status"></div>
            </div>
        `;

        const query = this.buildQueryParams();

        try {
            if (this.currentTab === 'overview') {
                content.innerHTML = `
                    <div class="row g-4 fade-in">
                        <div class="col-lg-12">
                            <div class="glass-card">
                                <div class="ds-card-header"><h6 class="card-title">Executive Revenue Overview</h6></div>
                                <div class="ds-card-body"><div style="height:320px;"><canvas id="revenueOverviewChart"></canvas></div></div>
                            </div>
                        </div>
                    </div>
                `;
                
                let revRes = { trends: { labels: [], values: [] } };
                try {
                    revRes = await api.get(`/analytics/revenue?${query}`);
                } catch (e) {
                    console.warn("Failed to load revenue analytics", e);
                }
                
                // Plot overview chart
                const roCtx = document.getElementById('revenueOverviewChart')?.getContext('2d');
                if (roCtx && revRes.trends) {
                    this.charts.revOver = new Chart(roCtx, {
                        type: 'line',
                        data: {
                            labels: revRes.trends.labels,
                            datasets: [{
                                label: 'Revenue (INR)',
                                data: revRes.trends.values,
                                borderColor: '#10b981',
                                backgroundColor: 'rgba(16,185,129,0.12)',
                                borderWidth: 2.5,
                                fill: true,
                                tension: 0.35,
                                pointRadius: 3,
                                pointHoverRadius: 6,
                                pointBackgroundColor: '#10b981'
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: { display: false },
                                tooltip: {
                                    callbacks: {
                                        label: function(ctx) {
                                            return ' Revenue: ₹' + Number(ctx.parsed.y).toLocaleString('en-IN', { minimumFractionDigits: 2 });
                                        }
                                    }
                                }
                            },
                            scales: {
                                x: {
                                    grid: { display: false },
                                    ticks: { maxRotation: 45, font: { size: 11 } }
                                },
                                y: {
                                    beginAtZero: true,
                                    ticks: {
                                        callback: function(val) {
                                            return '₹' + Number(val).toLocaleString('en-IN');
                                        },
                                        font: { size: 11 }
                                    }
                                }
                            }
                        }
                    });
                }
            }
            
            else if (this.currentTab === 'revenue') {
                content.innerHTML = `
                    <div class="v-stack gap-4 fade-in">
                        <div class="row g-4">
                            <div class="col-lg-6">
                                <div class="glass-card">
                                    <div class="ds-card-header"><h6 class="card-title">Monthly Revenue Trends</h6></div>
                                    <div class="ds-card-body"><div style="height:260px;"><canvas id="revMonthlyChart"></canvas></div></div>
                                </div>
                            </div>
                            <div class="col-lg-6">
                                <div class="glass-card">
                                    <div class="ds-card-header"><h6 class="card-title">3-Month Revenue Forecasting</h6></div>
                                    <div class="ds-card-body"><div style="height:260px;"><canvas id="revForecastChart"></canvas></div></div>
                                </div>
                            </div>
                        </div>
                        <div class="glass-card p-0">
                            <div class="ds-card-header border-bottom py-3 px-4"><h6 class="card-title mb-0">Financial Drill-Down Details</h6></div>
                            <div class="table-responsive">
                                <table class="ds-table mb-0">
                                    <thead>
                                        <tr>
                                            <th>Organization</th>
                                            <th>Subscription UID</th>
                                            <th>Active Plan</th>
                                            <th>Invoices Paid</th>
                                            <th class="text-end">Total Contribution</th>
                                        </tr>
                                    </thead>
                                    <tbody id="revDrillBody"></tbody>
                                </table>
                            </div>
                            <div class="ds-card-body py-3 px-4 border-top d-flex justify-content-between align-items-center flex-wrap gap-2" style="border-color:var(--ds-border-color)!important;">
                                <div class="text-xs text-muted" id="revDrillInfo">—</div>
                                <div class="d-flex gap-1 align-items-center">
                                    <select class="ds-input" id="revDrillPerPage" style="height:30px; font-size:12px; padding: 3px 24px 3px 8px; width:80px;" onchange="EnterpriseAnalytics.setRevDrillPerPage(this.value)">
                                        <option value="5" selected>5</option>
                                        <option value="10">10</option>
                                        <option value="20">20</option>
                                        <option value="50">50</option>
                                        <option value="100">100</option>
                                    </select>
                                    <span class="text-xs text-muted ms-1">per page</span>
                                    <div id="revDrillPagBtns" class="ms-2 d-flex gap-1"></div>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                
                const revRes = await api.get(`/analytics/revenue?${query}`);
                const drillRes = await api.get(`/analytics/drilldown?segment=revenue&${query}`);
                
                // Plot Charts
                const mCtx = document.getElementById('revMonthlyChart')?.getContext('2d');
                if (mCtx && revRes.trends) {
                    this.charts.revMonthly = new Chart(mCtx, {
                        type: 'bar',
                        data: {
                            labels: revRes.trends.labels,
                            datasets: [{ label: 'Completed Payments', data: revRes.trends.values, backgroundColor: 'rgba(59,130,246,0.85)', borderRadius: 5 }]
                        },
                        options: { responsive: true, maintainAspectRatio: false }
                    });
                }
                
                const fCtx = document.getElementById('revForecastChart')?.getContext('2d');
                if (fCtx && revRes.forecast) {
                    this.charts.revForecast = new Chart(fCtx, {
                        type: 'line',
                        data: {
                            labels: revRes.forecast.labels,
                            datasets: [{ label: 'Forecasted Revenue', data: revRes.forecast.values, borderColor: '#ef4444', borderDash: [6,6], fill: false, tension: 0.3 }]
                        },
                        options: { responsive: true, maintainAspectRatio: false }
                    });
                }
                
                // Pop Drill down
                this._revDrillList = drillRes.drilldown || [];
                this._revDrillPage = 1;
                this._revDrillPerPage = this._revDrillPerPage || 5;
                this.renderRevDrillTable();
            }
            
            else if (this.currentTab === 'organizations') {
                content.innerHTML = `
                    <div class="row g-4 fade-in">
                        <div class="col-lg-12">
                            <div class="glass-card">
                                <div class="ds-card-header"><h6 class="card-title">Tenants by Industry</h6></div>
                                <div class="ds-card-body"><div style="height:280px;"><canvas id="orgIndustryChart"></canvas></div></div>
                            </div>
                        </div>
                    </div>
                `;
                
                let orgRes = { industries: {} };
                try {
                    orgRes = await api.get(`/analytics/organizations?${query}`);
                } catch (e) {
                    console.warn("Failed to load organizations analytics", e);
                }
                
                const indCtx = document.getElementById('orgIndustryChart')?.getContext('2d');
                if (indCtx) {
                    const inds = (orgRes && orgRes.industries && Object.keys(orgRes.industries).length > 0) ? orgRes.industries : { 'Default Industry': 1 };
                    this.charts.orgInd = new Chart(indCtx, {
                        type: 'bar',
                        data: {
                            labels: Object.keys(inds),
                            datasets: [{ label: 'Tenants', data: Object.values(inds), backgroundColor: '#8b5cf6', borderRadius: 4 }]
                        },
                        options: { responsive: true, maintainAspectRatio: false }
                    });
                }
            }
            
            else if (this.currentTab === 'users') {
                content.innerHTML = `
                    <div class="v-stack gap-4 fade-in">
                        <div class="row g-4">
                            <div class="col-lg-8">
                                <div class="glass-card">
                                    <div class="ds-card-header"><h6 class="card-title">Department Distribution</h6></div>
                                    <div class="ds-card-body"><div style="height:260px;"><canvas id="userDeptChart"></canvas></div></div>
                                </div>
                            </div>
                            <div class="col-lg-4">
                                <div class="glass-card text-center p-4 d-flex flex-column justify-content-center" style="min-height:300px;">
                                    <h2 class="fw-bold mb-1" style="font-size:3rem; color:var(--ds-accent);" id="activeDAU">0</h2>
                                    <div class="text-sm text-secondary fw-semibold uppercase">Daily Active Users (DAU)</div>
                                    <h4 class="fw-bold mt-4 mb-1" style="font-size:2rem; color:var(--ds-text-main);" id="activeMAU">0</h4>
                                    <div class="text-xs text-secondary uppercase">Monthly Active Engagement (MAU)</div>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                
                const uRes = await api.get(`/analytics/users?${query}`);
                document.getElementById('activeDAU').textContent = uRes.dau;
                document.getElementById('activeMAU').textContent = uRes.mau;
                
                const deptCtx = document.getElementById('userDeptChart')?.getContext('2d');
                if (deptCtx && uRes.departments) {
                    this.charts.userDept = new Chart(deptCtx, {
                        type: 'bar',
                        data: {
                            labels: Object.keys(uRes.departments),
                            datasets: [{ label: 'Users Count', data: Object.values(uRes.departments), backgroundColor: '#06b6d4', borderRadius: 4 }]
                        },
                        options: { responsive: true, maintainAspectRatio: false }
                    });
                }
            }

            else if (this.currentTab === 'licenses') {
                content.innerHTML = `
                    <div class="row g-4 fade-in">
                        <div class="col-md-4">
                            <div class="glass-card p-4 text-center">
                                <h3 class="fw-bold text-success mb-1" id="licActive">0</h3>
                                <div class="text-xs text-secondary uppercase font-semibold">Active Licenses</div>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="glass-card p-4 text-center">
                                <h3 class="fw-bold text-danger mb-1" id="licExpired">0</h3>
                                <div class="text-xs text-secondary uppercase font-semibold">Expired Licenses</div>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="glass-card p-4 text-center">
                                <h3 class="fw-bold text-warning mb-1" id="licForecast">0</h3>
                                <div class="text-xs text-secondary uppercase font-semibold">Expiring in 30 Days</div>
                            </div>
                        </div>
                    </div>
                `;
                
                const licRes = await api.get(`/analytics/licenses?${query}`);
                document.getElementById('licActive').textContent = licRes.active;
                document.getElementById('licExpired').textContent = licRes.expired;
                document.getElementById('licForecast').textContent = licRes.expiry_forecast_30d;
            }
            
            else if (this.currentTab === 'modules') {
                content.innerHTML = `
                    <div class="row g-4 fade-in">
                        <div class="col-lg-8">
                            <div class="glass-card">
                                <div class="ds-card-header"><h6 class="card-title">Feature Module Usage Frequency</h6></div>
                                <div class="ds-card-body"><div style="height:260px;"><canvas id="modUsageChart"></canvas></div></div>
                            </div>
                        </div>
                        <div class="col-lg-4">
                            <div class="glass-card p-4 d-flex flex-column justify-content-center h-100">
                                <div class="mb-3 text-start">
                                    <div class="text-xxs uppercase font-semibold text-secondary">Most Utilized Feature</div>
                                    <div class="fs-5 fw-bold text-primary mt-1" id="mostUsedFeature">-</div>
                                </div>
                                <div class="mb-3 text-start">
                                    <div class="text-xxs uppercase font-semibold text-secondary">Least Utilized Feature</div>
                                    <div class="fs-5 fw-bold text-warning mt-1" id="leastUsedFeature">-</div>
                                </div>
                                <div class="text-start">
                                    <div class="text-xxs uppercase font-semibold text-secondary">Averaged Core Adoption</div>
                                    <div class="fs-5 fw-bold text-success mt-1" id="adoptionRate">-</div>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                
                const modRes = await api.get(`/analytics/modules?${query}`);
                document.getElementById('mostUsedFeature').textContent = modRes.most_used;
                document.getElementById('leastUsedFeature').textContent = modRes.least_used;
                document.getElementById('adoptionRate').textContent = `${modRes.adoption_rate}%`;
                
                const muCtx = document.getElementById('modUsageChart')?.getContext('2d');
                if (muCtx && modRes.usage_distribution) {
                    this.charts.modUsage = new Chart(muCtx, {
                        type: 'bar',
                        data: {
                            labels: Object.keys(modRes.usage_distribution),
                            datasets: [{ label: 'API / Page Hits', data: Object.values(modRes.usage_distribution), backgroundColor: '#a855f7', borderRadius: 4 }]
                        },
                        options: { responsive: true, maintainAspectRatio: false }
                    });
                }
            }
            
            else if (this.currentTab === 'support') {
                content.innerHTML = `
                    <div class="row g-4 fade-in">
                        <div class="col-lg-6">
                            <div class="glass-card">
                                <div class="ds-card-header"><h6 class="card-title">Support Ticket Volume by Priority</h6></div>
                                <div class="ds-card-body"><div style="height:260px;"><canvas id="ticketPriorityChart"></canvas></div></div>
                            </div>
                        </div>
                        <div class="col-lg-6">
                            <div class="glass-card p-4 d-flex flex-column justify-content-center h-100">
                                <div class="row text-center">
                                    <div class="col-6 border-end">
                                        <h3 class="fw-bold text-main" id="openTickets">0</h3>
                                        <div class="text-xxs uppercase text-secondary">Open Issues</div>
                                    </div>
                                    <div class="col-6">
                                        <h3 class="fw-bold text-success" id="slaCompliance">0%</h3>
                                        <div class="text-xxs uppercase text-secondary">SLA Compliance</div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                
                const supRes = await api.get(`/analytics/support?${query}`);
                document.getElementById('openTickets').textContent = supRes.open;
                document.getElementById('slaCompliance').textContent = `${supRes.sla_compliance_rate}%`;
                
                const prioCtx = document.getElementById('ticketPriorityChart')?.getContext('2d');
                if (prioCtx) {
                    const dist = supRes.priority_distribution && Object.keys(supRes.priority_distribution).length > 0
                        ? supRes.priority_distribution
                        : { 'High': 0, 'Medium': 0, 'Low': 0 };
                    
                    this.charts.ticketPrio = new Chart(prioCtx, {
                        type: 'doughnut',
                        data: {
                            labels: Object.keys(dist),
                            datasets: [{ data: Object.values(dist), backgroundColor: ['#ef4444', '#f59e0b', '#3b82f6'], borderWidth: 0 }]
                        },
                        options: { responsive: true, maintainAspectRatio: false, cutout: '75%' }
                    });
                }
            }
            
            else if (this.currentTab === 'system') {
                content.innerHTML = `
                    <div class="row g-4 fade-in">
                        <div class="col-md-3">
                            <div class="glass-card p-4 text-center">
                                <h4 class="fw-bold text-primary mb-1" id="sysCPU">0%</h4>
                                <div class="text-xxs text-secondary uppercase">CPU Allocation</div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="glass-card p-4 text-center">
                                <h4 class="fw-bold text-success mb-1" id="sysRAM">0%</h4>
                                <div class="text-xxs text-secondary uppercase">RAM Allocation</div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="glass-card p-4 text-center">
                                <h4 class="fw-bold text-warning mb-1" id="sysDisk">0%</h4>
                                <div class="text-xxs text-secondary uppercase">Disk Space</div>
                            </div>
                        </div>
                        <div class="col-md-3">
                            <div class="glass-card p-4 text-center">
                                <h4 class="fw-bold text-danger mb-1" id="sysError">0%</h4>
                                <div class="text-xxs text-secondary uppercase">Failure rate</div>
                            </div>
                        </div>
                    </div>
                `;
                const sysRes = await api.get(`/analytics/system?${query}`);
                document.getElementById('sysCPU').textContent = `${sysRes.cpu_usage}%`;
                document.getElementById('sysRAM').textContent = `${sysRes.memory_usage}%`;
                document.getElementById('sysDisk').textContent = `${sysRes.disk_usage}%`;
                document.getElementById('sysError').textContent = `${sysRes.error_rate}%`;
            }
            
            else if (this.currentTab === 'ai') {
                content.innerHTML = `
                    <div class="v-stack gap-4 fade-in">
                        <div class="glass-card p-4" style="background: linear-gradient(135deg, rgba(139,92,246,0.15) 0%, rgba(59,130,246,0.1) 100%); border: 1px solid rgba(139,92,246,0.3);">
                            <div class="d-flex align-items-center gap-2 mb-2">
                                <i data-lucide="sparkles" class="text-primary" style="width:20px; height:20px;"></i>
                                <h5 class="fw-bold mb-0 text-main" style="color:var(--ds-text-main);">AI Forecasting & Platform Health Index</h5>
                            </div>
                            <p class="text-sm text-secondary mb-0">Predictive recommendations calculated via automated data aggregation and regressional projections. AI recommendations are purely advisory.</p>
                        </div>
                        <div class="row g-4" id="aiScorecards">
                            <!-- Populated -->
                        </div>
                        <div class="glass-card p-0">
                            <div class="ds-card-header border-bottom py-3 px-4"><h6 class="card-title mb-0">Actionable Recommendations</h6></div>
                            <div class="list-group list-group-flush" id="aiRecsList"></div>
                        </div>
                    </div>
                `;
                
                const aiRes = await api.get(`/analytics/ai-insights?${query}`);
                
                const scorecards = document.getElementById('aiScorecards');
                if (scorecards && aiRes.risk_scores) {
                    scorecards.innerHTML = `
                        <div class="col-md-4">
                            <div class="glass-card p-4 text-center">
                                <div class="fs-6 text-secondary uppercase font-semibold">Churn Risk score</div>
                                <h2 class="fw-bold text-warning mt-2 mb-0">${aiRes.risk_scores.churn_risk_score}/100</h2>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="glass-card p-4 text-center">
                                <div class="fs-6 text-secondary uppercase font-semibold">License Expiry Risk</div>
                                <h2 class="fw-bold text-danger mt-2 mb-0">${aiRes.risk_scores.license_risk_score}/100</h2>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="glass-card p-4 text-center">
                                <div class="fs-6 text-secondary uppercase font-semibold">Platform Health Index</div>
                                <h2 class="fw-bold text-success mt-2 mb-0">${aiRes.risk_scores.platform_health_score}/100</h2>
                            </div>
                        </div>
                    `;
                }
                
                const recsList = document.getElementById('aiRecsList');
                if (recsList && aiRes.recommendations) {
                    recsList.innerHTML = aiRes.recommendations.map(r => `
                        <div class="list-group-item p-4 border-0 border-bottom d-flex align-items-start gap-3" style="border-color:var(--ds-border-color)!important;">
                            <div class="ds-badge ${r.impact === 'High' ? 'red' : (r.impact === 'Medium' ? 'orange' : 'blue')} mt-1">${r.impact}</div>
                            <div style="flex:1;">
                                <h6 class="fw-bold text-main mb-1" style="color:var(--ds-text-main);">${r.title}</h6>
                                <p class="text-sm text-secondary mb-2">${r.message}</p>
                                <div class="text-xs fw-bold text-primary" style="display:flex; align-items:center; gap:4px;">
                                    <i data-lucide="help-circle" style="width:12px; height:12px;"></i>
                                    <span>Suggested action: ${r.action}</span>
                                </div>
                            </div>
                        </div>
                    `).join('') || '<div class="p-4 text-center text-muted">No advisory issues detected. All platform metrics are within normal bounds.</div>';
                }
                if (window.lucide) lucide.createIcons();
            }
        } catch (e) {
            console.error("Failed to load tab contents", e);
            content.innerHTML = `<div class="alert alert-danger m-4">Failed to fetch data for tab: ${this.currentTab}</div>`;
        }
    },

    openReportBuilder() {
        const modalEl = document.getElementById('reportBuilderModal');
        if (modalEl && modalEl.parentNode !== document.body) {
            document.body.appendChild(modalEl);
        }
        let modal = bootstrap.Modal.getInstance(modalEl);
        if (!modal) {
            modal = new bootstrap.Modal(modalEl);
        }
        modal.show();
    },

    async saveCustomReport() {
        const titleEl = document.getElementById('reportTitle');
        const title = titleEl ? titleEl.value.trim() : '';
        const descEl = document.getElementById('reportDescription') || document.getElementById('reportDesc');
        const desc = descEl ? descEl.value.trim() : '';
        const checkedMetrics = Array.from(document.querySelectorAll('.report-metric:checked, .report-metric-check:checked')).map(el => el.value);

        if (!title) {
            this._toast('Report Title is required', 'warning');
            return;
        }
        if (checkedMetrics.length === 0) {
            this._toast('Please check at least one metric to visualize', 'warning');
            return;
        }

        try {
            const res = await api.post('/analytics/reports', {
                title,
                description: desc,
                config: {
                    metrics: checkedMetrics,
                    chart_type: document.getElementById('reportChartType')?.value || 'bar',
                    filters: this.filters
                }
            });
            if (res.status === 'success') {
                this._toast('Custom Report created successfully', 'success');
                const modal = bootstrap.Modal.getInstance(document.getElementById('reportBuilderModal') || document.getElementById('customReportBuilderModal'));
                if (modal) modal.hide();
                this.refreshDashboard();
            }
        } catch (e) {
            console.error(e);
            this._toast('Failed to save custom report schema', 'error');
        }
    },

    async triggerExport(format) {
        try {
            const fmt = (format || 'CSV').toUpperCase();
            if (fmt === 'PRINT') {
                window.print();
                return;
            }
            
            this._toast(`Generating ${fmt} file...`, 'info');
            const token = api.token || sessionStorage.getItem('token') || localStorage.getItem('token') || '';
            const reportType = this.currentTab || 'overview';
            const downloadUrl = `/api/reports/download-mock?type=${reportType}&format=${fmt}`;

            const fileRes = await fetch(downloadUrl, {
                method: 'GET',
                headers: {
                    'Authorization': token ? `Bearer ${token}` : ''
                }
            });

            if (!fileRes.ok) {
                const errText = await fileRes.text().catch(() => '');
                throw new Error(`Server returned status ${fileRes.status}: ${errText.slice(0, 100)}`);
            }

            const blob = await fileRes.blob();
            const blobUrl = URL.createObjectURL(blob);

            let ext = fmt.toLowerCase();
            if (ext === 'excel') ext = 'xlsx';

            let filename = `QCMS_${reportType}_Report_${new Date().toISOString().slice(0, 10)}.${ext}`;
            const disposition = fileRes.headers.get('Content-Disposition') || '';
            const fnMatch = disposition.match(/filename[^;=\n]*=([^;\n]*)/);
            if (fnMatch) {
                filename = fnMatch[1].replace(/['"]/g, '').trim();
            }

            const a = document.createElement('a');
            a.href = blobUrl;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            setTimeout(() => URL.revokeObjectURL(blobUrl), 5000);

            this._toast(`${fmt} file downloaded successfully`, 'success');
        } catch (e) {
            console.error('[Export Error]', e);
            this._toast('Export failed: ' + (e.message || 'Error generating report file'), 'error');
        }
    },

    renderRevDrillTable() {
        const tbody = document.getElementById('revDrillBody');
        const info = document.getElementById('revDrillInfo');
        const btns = document.getElementById('revDrillPagBtns');
        const perPageSelect = document.getElementById('revDrillPerPage');

        const list = this._revDrillList || [];
        const page = this._revDrillPage || 1;
        const perPage = this._revDrillPerPage || 5;
        const total = list.length;
        const totalPages = Math.max(1, Math.ceil(total / perPage));

        if (perPageSelect) perPageSelect.value = perPage;

        const start = (page - 1) * perPage;
        const pageData = list.slice(start, start + perPage);

        if (tbody) {
            tbody.innerHTML = pageData.map(d => `
                <tr>
                    <td><div class="fw-bold text-main" style="color:var(--ds-text-main);">${d.organization}</div></td>
                    <td><span class="ds-badge gray">${d.subscription_uid}</span></td>
                    <td>${d.plan}</td>
                    <td>${d.invoice_count}</td>
                    <td class="text-end fw-bold" style="color:var(--ds-text-main);">${this._formatINR(d.total_paid)}</td>
                </tr>
            `).join('') || '<tr><td colspan="5" class="text-center py-4 text-muted">No historical billing data available.</td></tr>';
        }

        if (info) {
            const startItem = total > 0 ? start + 1 : 0;
            const endItem = Math.min(page * perPage, total);
            info.textContent = total > 0 ? `Showing ${startItem}–${endItem} of ${total}` : 'No results';
        }

        if (btns) {
            let btnHtml = `<button class="ds-btn ds-btn-sm ds-btn-ghost" ${page <= 1 ? 'disabled' : ''} onclick="EnterpriseAnalytics.revDrillGoToPage(${page - 1})"><i data-lucide="chevron-left" style="width:14px;height:14px;"></i></button>`;
            for (let i = 1; i <= totalPages; i++) {
                btnHtml += `<button class="ds-btn ds-btn-sm ${i === page ? 'ds-btn-primary' : 'ds-btn-ghost'}" onclick="EnterpriseAnalytics.revDrillGoToPage(${i})">${i}</button>`;
            }
            btnHtml += `<button class="ds-btn ds-btn-sm ds-btn-ghost" ${page >= totalPages ? 'disabled' : ''} onclick="EnterpriseAnalytics.revDrillGoToPage(${page + 1})"><i data-lucide="chevron-right" style="width:14px;height:14px;"></i></button>`;
            btns.innerHTML = btnHtml;
        }

        if (window.lucide) lucide.createIcons();
    },

    setRevDrillPerPage(v) {
        this._revDrillPerPage = parseInt(v, 10) || 5;
        this._revDrillPage = 1;
        this.renderRevDrillTable();
    },

    revDrillGoToPage(p) {
        this._revDrillPage = p;
        this.renderRevDrillTable();
    },

    startRealtimeUpdates() {
        if (this.realtimeTimer) clearInterval(this.realtimeTimer);
        this.realtimeTimer = setInterval(async () => {
            try {
                const query = this.buildQueryParams();
                const res = await api.get(`/analytics/realtime?${query}`);
                if (res.status === 'success') {
                    // Update live tickers if on dashboard
                    const liveUsers = document.getElementById('activeDAU');
                    if (liveUsers && this.currentTab === 'users') {
                        liveUsers.textContent = res.live_active_users;
                    }
                }
            } catch (e) {
                console.error("Real-time telemetry poll failed", e);
            }
        }, 15000); // 15 seconds poll interval
    }
};
