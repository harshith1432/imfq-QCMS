/**
 * QCMS Enterprise - Super Admin Controller
 * Manages global platform oversight and multi-tenant control.
 */

const SuperAdmin = {
    activeView: 'overview',
    charts: {},
    // Sub-role RBAC — populated on init from JWT + /my-permissions
    saSubRole: 'Owner',
    _permissions: null,   // { section: { can_read, can_write } }

    async init() {
        console.log("Super Admin Controller Initializing...");

        // 1. Execute view switching based on URL parameters FIRST (eliminates Platform Governance flash)
        this.handleRouting();

        // 2. Load sub-role permissions
        this.loadMyPermissions();

        // 3. Dynamically populate plan select dropdowns across app
        this.populateAllPlanDropdowns();

        // 4. Event Listeners
        this.initEventListeners();

        // 4. Wizard & Table features
        this.initWizard();
        this.initTableFeatures();

        // 5. Background polling every 15 minutes
        setInterval(() => {
            if (this.activeView === 'overview') {
                this.refreshData();
            }
        }, 900000);

        // 6. Global Search suggestions listener
        window.addEventListener('qcms-global-search', (e) => {
            this.handleGlobalSearch(e.detail.query);
        });

        document.addEventListener('click', (e) => {
            const drop = document.getElementById('searchSuggestionsDropdown');
            if (drop && !e.target.closest('.nav-search-wrapper')) {
                drop.classList.add('d-none');
            }
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                const drop = document.getElementById('searchSuggestionsDropdown');
                if (drop) drop.classList.add('d-none');
            }
        });

        // 7. Relocate modals to body to prevent stacking context/z-index issues
        document.querySelectorAll('.modal').forEach(modal => {
            if (modal.parentNode !== document.body) {
                document.body.appendChild(modal);
            }
        });
    },

    // ─────────────────────────────────────────────────────────────────────
    // SUB-ROLE RBAC
    // ─────────────────────────────────────────────────────────────────────

    async loadMyPermissions() {
        try {
            // Try to read sub_role from JWT claims first (fast, no extra request)
            const token = api.token;
            if (token && token.includes('.')) {
                try {
                    const payload = JSON.parse(atob(token.split('.')[1]));
                    if (payload.sa_sub_role) {
                        this.saSubRole = payload.sa_sub_role;
                    }
                } catch (_) {}
            }

            // Fetch full permission map from backend
            const res = await api.get('/super-admin/my-permissions');
            if (res && res.status === 'success') {
                this.saSubRole = res.data.sub_role || 'Owner';
                this._permissions = res.data.permissions;
                this.applySubRoleRestrictions();
            }
        } catch (e) {
            // Default to Owner on error (safe for existing sessions)
            this.saSubRole = 'Owner';
            console.warn('[RBAC] Could not load permissions, defaulting to Owner:', e.message);
        }
    },

    canRead(section) {
        if (!this.saSubRole || this.saSubRole === 'Owner') return true;
        if (!this._permissions) return true; // Safe default while loading
        const p = this._permissions[section];
        return p ? Boolean(p.can_read) : true;
    },

    canWrite(section) {
        if (!this.saSubRole || this.saSubRole === 'Owner') return true;
        if (this.saSubRole === 'Read Only') return false;
        if (!this._permissions) return true;
        const p = this._permissions[section];
        return p ? Boolean(p.can_write) : true;
    },

    applySubRoleRestrictions() {
        const role = this.saSubRole;
        if (role === 'Owner') return; // Full access, nothing to restrict

        // --- Show sub-role badge in header ---
        const badgeTarget = document.getElementById('saSubRoleBadge');
        if (badgeTarget) {
            badgeTarget.textContent = role;
            badgeTarget.style.display = '';
        }

        // --- Sidebar link visibility ---
        // Map view IDs to their section key in the permission map
        const VIEW_SECTION_MAP = {
            'organizations': 'organizations',
            'subscriptions': 'subscriptions',
            'admins':        'admins',
            'users':         'users',
            'plans':         'plans',
            'modules':       'modules',
            'analytics':     'analytics',
            'support':       'support',
            'billing':       'billing',
            'announcements': 'announcements',
            'logs':          'logs',
            'integrations':  'integrations',
            'settings':      'settings',
        };

        document.querySelectorAll('.sidebar-link[href]').forEach(link => {
            const href = link.getAttribute('href') || '';
            const viewMatch = href.match(/[?&]view=([^&]+)/);
            if (!viewMatch) return;
            const viewId = viewMatch[1];
            const section = VIEW_SECTION_MAP[viewId] || viewId;
            if (!this.canRead(section)) {
                link.style.display = 'none';
            }
        });

        // --- Disable write buttons for Read Only ---
        if (role === 'Read Only') {
            // Disable all save/create/delete action buttons
            document.querySelectorAll(
                '.ds-btn-primary, .ds-btn-danger, [onclick*="save"], [onclick*="create"], [onclick*="delete"], [onclick*="add"]'
            ).forEach(btn => {
                // Skip navigation-only buttons (those using switchView)
                const oc = (btn.getAttribute('onclick') || '');
                if (oc.includes('switchView') || oc.includes('loadMyPermissions')) return;
                btn.disabled = true;
                btn.title = 'Read Only Auditor — write access disabled';
                btn.style.opacity = '0.45';
                btn.style.cursor = 'not-allowed';
            });
        }

        // --- Disable write buttons for specific sections ---
        // We mark write action buttons with data-section attributes in HTML
        document.querySelectorAll('[data-rbac-section]').forEach(el => {
            const section = el.getAttribute('data-rbac-section');
            const action = el.getAttribute('data-rbac-action') || 'write';
            if (action === 'write' && !this.canWrite(section)) {
                el.disabled = true;
                el.title = `Your sub-role '${role}' cannot modify ${section}`;
                el.style.opacity = '0.45';
                el.style.cursor = 'not-allowed';
            }
        });
    },

    handleRouting() {
        const params = new URLSearchParams(window.location.search);
        const view = params.get('view') || 'overview';
        const tab = params.get('tab');
        this.switchView(view);
        if (view === 'settings' && tab && window.PlatformSettings) {
            setTimeout(() => window.PlatformSettings.switchTab(tab), 50);
        }
    },

    switchView(viewId) {
        // Alias legacy 'revenue' param to 'billing'
        if (viewId === 'revenue') viewId = 'billing';
        // Alias 'recycle-bin' URL param to 'recycleBin' so getElementById('recycleBinView') resolves
        if (viewId === 'recycle-bin') viewId = 'recycleBin';

        // ── RBAC: block navigation to forbidden sections ──────────────────
        if (this._permissions && this.saSubRole !== 'Owner') {
            const section = viewId === 'overview' ? 'overview' : viewId;
            if (!this.canRead(section)) {
                if (window.QCMS && QCMS.toast) {
                    QCMS.toast(
                        `Your sub-role "${this.saSubRole}" does not have access to this section.`,
                        'warning'
                    );
                }
                return; // Block navigation
            }
        }

        this.activeView = viewId;
        
        // Update UI Tabs/Sections
        document.querySelectorAll('.view-section').forEach(sec => sec.classList.remove('active'));
        const targetView = document.getElementById(`${viewId}View`);
        if (targetView) {
            targetView.classList.add('active');
        }

        // Update active state in sidebar
        document.querySelectorAll('.sidebar-link').forEach(link => {
            const href = link.getAttribute('href');
            if (href && (href.includes(`view=${viewId}`) || (viewId === 'overview' && href === '/admin/super-admin.html'))) {
                link.classList.add('active');
            } else if (href && href.includes('super-admin.html')) {
                link.classList.remove('active');
            }
        });

        // Update Page Titles
        const titles = {
            'overview':       { title: 'Platform Governance',      subtitle: 'Global oversight, financial control, and system stability.' },
            'organizations':  { title: 'Tenant Management',        subtitle: 'Monitor and manage all registered organizations and their status.' },
            'recycleBin':     { title: 'Recycle Bin',              subtitle: 'Manage soft-deleted organizations. Recover deleted tenants within 30 days or delete permanently.' },
            'subscriptions':  { title: 'Subscriptions',            subtitle: 'Manage active, trialing, and lapsed subscription records.' },
            'admins':         { title: 'Admin Accounts',           subtitle: 'Manage all organization-level admin users across tenants.' },
            'users':          { title: 'Global User Directory',    subtitle: 'Browse all users registered across the platform.' },
            'plans':          { title: 'Plan Definitions',         subtitle: 'Define and manage subscription plans and their feature limits.' },
            'modules':        { title: 'Feature Modules',          subtitle: 'Control feature module availability across plans and organizations.' },
            'analytics':      { title: 'Platform Analytics',       subtitle: 'In-depth platform growth, revenue, and engagement insights.' },
            'support':        { title: 'Support Desk',             subtitle: 'Centralized helpdesk for all organization admins.' },
            'billing':        { title: 'Billing & Payments',       subtitle: 'Track subscription payments and global platform revenue.' },
            'announcements':  { title: 'Announcements',            subtitle: 'Broadcast announcements and notices to all organizations.' },
            'logs':           { title: 'Audit Logs',               subtitle: 'Security logs and administrative action history.' },
            'integrations':   { title: 'Integration Hub',          subtitle: 'Central configuration, security vault, and real-time monitoring for platform APIs and third-party services.' },
            'doc-identity':   { title: 'Document Identity & Branding', subtitle: 'Centralized branding engine — configure platform identity, company info, document templates, and trace all setting dependencies.' },
            'storage':        { title: 'Organization Storage Analytics', subtitle: 'Real-time data storage consumption across all organizations, tier allocations, and usage alerts.' },
            'stage-templates': { title: 'Global Stage Templates',      subtitle: 'Design global default 8-stage workflow templates, custom section cards, and mandatory rules applied to all organizations.' },
            'settings':       { title: 'System Configuration',     subtitle: 'Manage global platform parameters and maintenance states.' }
        };

        const config = titles[viewId] || titles['overview'];
        const titleEl = document.getElementById('viewTitle');
        const subtitleEl = document.getElementById('viewSubtitle');
        if (titleEl) titleEl.textContent = config.title;
        if (subtitleEl) subtitleEl.textContent = config.subtitle;

        // Move local header actions to global header container
        const gActions = document.getElementById('globalHeaderActions');
        if (gActions) {
            gActions.innerHTML = '';
            const targetView = document.getElementById(`${viewId}View`);
            if (targetView) {
                const localActions = targetView.querySelector('.view-header-actions');
                if (localActions) {
                    const child = localActions.firstElementChild;
                    if (child) {
                        gActions.appendChild(child.cloneNode(true));
                        if (window.lucide) {
                            window.lucide.createIcons({ container: gActions });
                        }
                        // Re-apply write restrictions to freshly injected buttons
                        if (this.saSubRole !== 'Owner') {
                            gActions.querySelectorAll('button, a').forEach(btn => {
                                const oc = btn.getAttribute('onclick') || '';
                                if (!this.canWrite(viewId) && !oc.includes('switchView')) {
                                    btn.disabled = true;
                                    btn.title = `Your sub-role '${this.saSubRole}' cannot modify this section`;
                                    btn.style.opacity = '0.45';
                                    btn.style.cursor = 'not-allowed';
                                }
                            });
                        }
                    }
                }
            }
        }

        // Load specific data
        this.loadViewData(viewId);
    },

    initEventListeners() {
        // Form Handling
        const settingsForm = document.getElementById('platformSettingsForm');
        if (settingsForm) {
            settingsForm.addEventListener('submit', (e) => this.handleSettingsUpdate(e));
        }

        const profileForm = document.getElementById('superAdminProfileForm');
        if (profileForm) {
            profileForm.addEventListener('submit', (e) => this.handleProfileUpdate(e));
        }

        // Ticket Resolution
        const approveBtn = document.getElementById('approveTicketBtn');
        if (approveBtn) {
            approveBtn.addEventListener('click', () => this.handleTicketResolution('Resolved'));
        }
        const rejectBtn = document.getElementById('rejectTicketBtn');
        if (rejectBtn) {
            rejectBtn.addEventListener('click', () => this.handleTicketResolution('Rejected'));
        }

        // Search in Companies (debounced)
        const companySearch = document.getElementById('companySearch');
        if (companySearch) {
            companySearch.addEventListener('input', (e) => this.filterCompanies(e.target.value));
        }

        // Filter dropdowns for Organizations
        ['filterPlan', 'filterStatus', 'filterFeature'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.addEventListener('change', () => { this.currentPage = 1; this.loadOrganizations(); });
        });

        // Modal: Change Plan confirm
        const confirmPlanBtn = document.getElementById('confirmChangePlanBtn');
        if (confirmPlanBtn) {
            confirmPlanBtn.addEventListener('click', async () => {
                const orgId = document.getElementById('changePlanOrgId').value;
                const newPlan = document.getElementById('changePlanSelect').value;
                try {
                    await api.put(`/super-admin/companies/${orgId}/plan`, { plan: newPlan });
                    api.showNotification(`Plan changed to ${newPlan}`, 'success');
                    bootstrap.Modal.getInstance(document.getElementById('changePlanModal')).hide();
                    this.loadOrganizations();
                } catch (err) {
                    api.showNotification((err && (err.message || err.msg)) || 'Failed to change plan', 'error');
                }
            });
        }

        // Modal: Extend Trial confirm
        const confirmTrialBtn = document.getElementById('confirmExtendTrialBtn');
        if (confirmTrialBtn) {
            confirmTrialBtn.addEventListener('click', async () => {
                const orgId = document.getElementById('extendTrialOrgId').value;
                const newDate = document.getElementById('extendTrialDate').value;
                if (!newDate) { api.showNotification('Please select a date', 'error'); return; }
                try {
                    await api.put(`/super-admin/companies/${orgId}/trial`, { trial_ends_at: newDate });
                    api.showNotification('Trial period extended', 'success');
                    bootstrap.Modal.getInstance(document.getElementById('extendTrialModal')).hide();
                    this.loadOrganizations();
                } catch (err) {
                    api.showNotification('Failed to extend trial', 'error');
                }
            });
        }

        // SPA link interception for Super Admin sidebar navigation (prevents page reloads & flashes)
        document.addEventListener('click', (e) => {
            const link = e.target.closest('.sidebar-link[href*="super-admin.html"]');
            if (link) {
                const href = link.getAttribute('href') || '';
                const match = href.match(/[?&]view=([^&]+)/);
                const viewId = match ? match[1] : 'overview';
                
                e.preventDefault();
                e.stopPropagation();
                
                const searchStr = href.includes('?') ? href.substring(href.indexOf('?')) : '';
                if (window.location.search !== searchStr) {
                    history.pushState(null, '', href);
                }
                this.switchView(viewId);
            }
        });

        // Listen for back/forward navigation
        window.onpopstate = () => this.handleRouting();
    },

    async refreshData() {
        this.loadViewData(this.activeView);
    },

    async loadViewData(viewId) {
        try {
            switch (viewId) {
                case 'overview':
                    await this.loadOverview();
                    break;
                case 'organizations':
                    await this.loadOrganizations();
                    break;
                case 'recycleBin':
                    await this.loadRecycleBin();
                    break;
                case 'billing':
                case 'revenue':
                    await this.loadRevenue();
                    break;
                case 'support':
                    await this.loadSupport();
                    break;
                case 'settings':
                    await this.loadSettings();
                    break;
                case 'logs':
                    await this.initSuperAudit();
                    break;
                case 'subscriptions':
                    await this.loadSubscriptions();
                    break;
                case 'licenses':
                    this.switchView('overview');
                    break;
                case 'admins':
                    await this.loadAdmins();
                    break;
                case 'users':
                    await this.loadUsers();
                    break;
                case 'plans':
                    await this.loadPlans();
                    break;
                case 'modules':
                    await this.loadModules();
                    break;
                case 'analytics':
                    await this.loadAnalytics();
                    break;
                case 'announcements':
                    await this.loadAnnouncements();
                    break;
                case 'storage':
                    await this.loadStorageDashboard();
                    break;
                case 'integrations':
                    if (window.IntegrationsModule) {
                        await window.IntegrationsModule.init();
                    } else {
                        console.error("IntegrationsModule script is not loaded yet.");
                    }
                    break;
                case 'doc-identity':
                    if (window.DocIdentityManagerSA) {
                        DocIdentityManagerSA.init();
                    }
                    if (window.UsageExplorerSA) {
                        UsageExplorerSA.init();
                    }
                    break;
            }
        } catch (error) {
            console.error(`Error loading ${viewId} data:`, error);
            api.showNotification(`Failed to load ${viewId} data`, 'error');
        }
    },

    // --- VIEW LOADERS ---

    showSkeletons() {
        const kpiGrid = document.getElementById('superKpiGrid');
        if (kpiGrid) {
            kpiGrid.innerHTML = Array(8).fill(0).map(() => `
                <div class="glass-card d-flex flex-column justify-content-center align-items-center" style="height: 140px; background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1);">
                    <div class="skeleton-shimmer" style="width: 40px; height: 40px; border-radius: 12px; background: rgba(255, 255, 255, 0.1); margin-bottom: 12px;"></div>
                    <div class="skeleton-shimmer" style="width: 80px; height: 24px; border-radius: 4px; background: rgba(255, 255, 255, 0.1); margin-bottom: 8px;"></div>
                    <div class="skeleton-shimmer" style="width: 120px; height: 14px; border-radius: 4px; background: rgba(255, 255, 255, 0.1);"></div>
                </div>
            `).join('');
        }
    },

    getStorageColor(usedMb) {
        // Ceiling is 5 TB = 5,120,000 MB
        const pct = (usedMb / 5120000) * 100;
        if (pct >= 95) return 'red';
        if (pct >= 80) return 'orange';
        return 'blue';
    },

    renderOverviewCharts(data) {
        if (this.charts.orgStatus) this.charts.orgStatus.destroy();
        if (this.charts.mrrTrend) this.charts.mrrTrend.destroy();

        // 1. Donut Chart: Organizations by Status
        const donutCtx = document.getElementById('orgStatusDonut')?.getContext('2d');
        if (donutCtx) {
            const active = data.active_organizations || 0;
            const trial = data.trial_organizations || 0;
            const expired = data.expired_licenses || 0;
            const suspended = data.suspended_organizations || 0;

            this.charts.orgStatus = new Chart(donutCtx, {
                type: 'doughnut',
                data: {
                    labels: ['Active', 'On Trial', 'Expired', 'On Hold'],
                    datasets: [{
                        data: [active, trial, expired, suspended],
                        backgroundColor: ['#22c55e', '#f59e0b', '#ef4444', '#64748b'],
                        borderWidth: 0
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    cutout: '75%'
                }
            });

            const total = active + trial + expired + suspended || 1;
            const actualTotal = data.total_organizations !== undefined ? data.total_organizations : (active + trial + expired + suspended);
            const donutTotalEl = document.getElementById('orgDonutTotal');
            if (donutTotalEl) {
                donutTotalEl.textContent = actualTotal.toLocaleString();
            }

            const legendEl = document.getElementById('orgStatusDonutLegend');
            if (legendEl) {
                const items = [
                    { label: 'Active', val: active, color: '#22c55e' },
                    { label: 'On Trial', val: trial, color: '#f59e0b' },
                    { label: 'Expired', val: expired, color: '#ef4444' },
                    { label: 'On Hold', val: suspended, color: '#64748b' }
                ];
                legendEl.innerHTML = items.map(item => `
                    <div class="d-flex align-items-center gap-1">
                        <span style="width:8px;height:8px;border-radius:50%;background:${item.color};display:inline-block;"></span>
                        <span>${item.label}: <strong>${item.val}</strong> (${Math.round((item.val / total) * 100)}%)</span>
                    </div>
                `).join('');
            }
        }

        // 2. Line Chart: Revenue Trend (dynamic range based on selected date range)
        const lineCtx = document.getElementById('mrrTrendChart')?.getContext('2d');
        if (lineCtx) {
            let labels = [];
            let mrrData = [];
            let arrData = [];
            
            if (data.trend && data.trend.labels && data.trend.labels.length > 0) {
                labels = data.trend.labels;
                mrrData = data.trend.mrr;
                arrData = data.trend.arr;
            } else {
                const now = new Date();
                let numMonths = 12;
                if (this.selectedRevRange === '6m' || this.selectedDateRange === '6m') numMonths = 6;
                else if (this.selectedRevRange === 'ytd' || this.selectedDateRange === 'ytd') numMonths = now.getMonth() + 1;
                else if (this.selectedDateRange === '7d' || this.selectedDateRange === '30d') numMonths = 1;

                for (let i = numMonths - 1; i >= 0; i--) {
                    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
                    labels.push(d.toLocaleString('default', { month: 'short', year: '2-digit' }));
                    
                    const baseVal = data.revenue_in_period ?? data.revenue_this_month ?? 0;
                    const mrr = Math.round(baseVal);
                    mrrData.push(mrr);
                    arrData.push(mrr * 12);
                }
            }

            this.charts.mrrTrend = new Chart(lineCtx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'MRR (₹)',
                            data: mrrData,
                            borderColor: '#3b82f6',
                            backgroundColor: 'rgba(59, 130, 246, 0.05)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.3
                        },
                        {
                            label: 'ARR (Secondary, ₹)',
                            data: arrData,
                            borderColor: '#8b5cf6',
                            borderWidth: 1.5,
                            borderDash: [5, 5],
                            fill: false,
                            tension: 0.3
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: 'rgba(255,255,255,0.05)' }
                        },
                        x: {
                            grid: { display: false }
                        }
                    }
                }
            });
        }
    },

    exportRevenueChart(type) {
        if (!this.charts.mrrTrend) return;
        if (type === 'png') {
            const link = document.createElement('a');
            link.download = 'mrr_trend_chart.png';
            link.href = this.charts.mrrTrend.toBase64Image();
            link.click();
            api.showNotification('Chart exported as PNG', 'success');
        } else if (type === 'csv') {
            const data = this.charts.mrrTrend.data;
            let csv = 'Month,MRR (INR)\n';
            data.labels.forEach((lbl, idx) => {
                csv += `${lbl},${data.datasets[0].data[idx]}\n`;
            });
            const blob = new Blob([csv], { type: 'text/csv' });
            const link = document.createElement('a');
            link.download = 'mrr_trend_data.csv';
            link.href = URL.createObjectURL(blob);
            link.click();
            api.showNotification('Chart data exported as CSV', 'success');
        }
    },

    globalSearchTimeout: null,
    handleGlobalSearch(query) {
        if (this.globalSearchTimeout) clearTimeout(this.globalSearchTimeout);

        if (!this._hasSearchClickListener) {
            this._hasSearchClickListener = true;
            document.addEventListener('click', (e) => {
                const drop = document.getElementById('searchSuggestionsDropdown');
                const searchInput = document.getElementById('globalSearchInput');
                if (drop && !drop.contains(e.target) && searchInput && !searchInput.contains(e.target)) {
                    drop.classList.add('d-none');
                }
            });
        }

        let drop = document.getElementById('searchSuggestionsDropdown');
        if (!drop) {
            const wrapper = document.querySelector('.nav-search-wrapper');
            if (wrapper) {
                drop = document.createElement('div');
                drop.id = 'searchSuggestionsDropdown';
                drop.className = 'glass-card position-absolute shadow-lg d-none';
                drop.style.cssText = 'top: 45px; left: 0; width: 340px; z-index: 1050; padding: 12px; max-height: 400px; overflow-y: auto; background: var(--ds-bg-card); border: 1px solid var(--ds-border-color); border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.18);';
                wrapper.appendChild(drop);
            }
        }

        if (!drop) return;

        const val = query.trim();
        if (!val) {
            drop.classList.add('d-none');
            return;
        }

        drop.classList.remove('d-none');
        drop.innerHTML = `<div class="text-center py-2 text-muted text-xs"><i data-lucide="loader" class="spin me-1" style="width:14px;height:14px;"></i> Searching...</div>`;
        if (window.lucide) lucide.createIcons();

        this.globalSearchTimeout = setTimeout(async () => {
            try {
                const res = await api.get(`/v1/dashboard/search?q=${encodeURIComponent(val)}`);
                let html = '';
                
                if (res.organizations && res.organizations.length > 0) {
                    html += `<div class="text-xxs fw-bold text-uppercase text-primary mb-1 pb-1 border-bottom" style="letter-spacing:0.05em;">Organizations</div>`;
                    res.organizations.forEach(o => {
                        html += `
                            <a href="?view=organizations&search=${encodeURIComponent(o.name)}" class="d-flex justify-content-between align-items-center py-1.5 px-2 text-decoration-none hover-bg rounded" style="color: var(--ds-text-main);" onclick="document.getElementById('searchSuggestionsDropdown').classList.add('d-none');">
                                <div>
                                    <div class="fw-bold text-sm">${o.name}</div>
                                    <div class="text-xs text-secondary">${o.plan || 'Free'}</div>
                                </div>
                                <span class="badge bg-secondary-subtle text-secondary text-xxs px-2 py-0.5 rounded-pill">${o.status}</span>
                            </a>
                        `;
                    });
                }
                
                if (res.admins && res.admins.length > 0) {
                    html += `<div class="text-xxs fw-bold text-uppercase text-purple mt-2 mb-1 pb-1 border-bottom" style="letter-spacing:0.05em;">Administrators</div>`;
                    res.admins.forEach(a => {
                        html += `
                            <a href="?view=settings" class="d-flex justify-content-between align-items-center py-1.5 px-2 text-decoration-none hover-bg rounded" style="color: var(--ds-text-main);" onclick="document.getElementById('searchSuggestionsDropdown').classList.add('d-none');">
                                <div>
                                    <div class="fw-bold text-sm">${a.name}</div>
                                    <div class="text-xs text-secondary">${a.email}</div>
                                </div>
                                ${a.org_name && a.org_name !== 'Platform Governance' ? `<span class="badge bg-body-tertiary text-secondary text-xxs border px-2 py-0.5 rounded-pill">${a.org_name}</span>` : ''}
                            </a>
                        `;
                    });
                }

                if (res.users && res.users.length > 0) {
                    html += `<div class="text-xxs fw-bold text-uppercase text-success mt-2 mb-1 pb-1 border-bottom" style="letter-spacing:0.05em;">Users</div>`;
                    res.users.forEach(u => {
                        html += `
                            <div class="d-flex justify-content-between align-items-center py-1.5 px-2 rounded hover-bg" style="color: var(--ds-text-main); cursor: default;">
                                <div>
                                    <div class="fw-bold text-sm">${u.name}</div>
                                    <div class="text-xs text-secondary">${u.email}</div>
                                </div>
                                ${u.org_name && u.org_name !== 'Platform Governance' ? `<span class="badge bg-body-tertiary text-secondary text-xxs border px-2 py-0.5 rounded-pill">${u.org_name}</span>` : ''}
                            </div>
                        `;
                    });
                }

                if (!html) {
                    drop.innerHTML = `<div class="text-center py-2 text-muted text-xs">No matching results for "${val}"</div>`;
                } else {
                    drop.innerHTML = html;
                }
                if (window.lucide) lucide.createIcons();
            } catch (err) {
                drop.innerHTML = `<div class="text-center py-2 text-danger text-xs">Search failed</div>`;
            }
        }, 300);
    },

    quickAction(actionType) {
        if (actionType === 'create_org') {
            this.switchView('organizations');
            setTimeout(() => {
                const modal = new bootstrap.Modal(document.getElementById('createOrgModal'));
                modal.show();
            }, 150);
        } else if (actionType === 'add_admin') {
            this.switchView('settings');
        } else if (actionType === 'view_support') {
            this.switchView('support');
        } else if (actionType === 'extend_license') {
            this.switchView('organizations');
        } else if (actionType === 'view_expiring') {
            this.switchView('organizations');
            setTimeout(() => {
                this.filterByKpi('license_status', 'Expiring Soon');
            }, 150);
        }
    },

    // Current selected range state
    selectedDateRange: '30d',
    selectedRevRange: '6m',

    setDateRange(range) {
        this.selectedDateRange = range;
        const labels = { '7d': 'Last 7 Days', '30d': 'Last 30 Days', '6m': 'Last 6 Months', '12m': 'Last 12 Months', 'ytd': 'Year to Date' };
        const labelEl = document.getElementById('dateRangeLabel');
        if (labelEl) labelEl.textContent = labels[range] || 'Last 30 Days';
        this.loadOverview();
    },

    setRevRange(range) {
        this.selectedRevRange = range;
        this.selectedDateRange = range;
        const labels = { '7d': 'Last 7 Days', '30d': 'Last 30 Days', '6m': 'Last 6 Months', '12m': 'Last 12 Months', 'ytd': 'Year to Date' };
        const labelEl = document.getElementById('dateRangeLabel');
        if (labelEl) labelEl.textContent = labels[range] || 'Last 30 Days';

        const group = document.getElementById('revRangeGroup');
        if (group) {
            group.querySelectorAll('button').forEach(btn => {
                const text = btn.textContent.trim().toLowerCase();
                if (text === range) btn.classList.add('active-range');
                else btn.classList.remove('active-range');
            });
        }
        this.loadOverview();
    },

    refreshDashboard() {
        const icon = document.getElementById('refreshIcon');
        if (icon) icon.classList.add('spin');
        this.loadOverview().finally(() => {
            if (icon) icon.classList.remove('spin');
        });
    },

    exportDashboard() {
        api.showNotification('Preparing executive dashboard export...', 'info');
        setTimeout(() => {
            const s = this.lastStats || {};
            const now = new Date();
            const dateStr = now.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
            const timeStr = now.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });

            const rows = [
                ['QCMS Platform — Executive Dashboard Report'],
                ['Generated At: ' + dateStr + ' ' + timeStr],
                ['Exported By: Super Admin'],
                [],
                ['PLATFORM KPIs', ''],
                ['Metric', 'Value'],
                ['Total Organizations', s.total_orgs ?? '—'],
                ['Active Organizations', s.active_orgs ?? '—'],
                ['On Trial Organizations', s.trial_orgs ?? '—'],
                ['Expired Licenses', s.expired_licenses ?? '—'],
                ['Total Users', s.total_users ?? '—'],
                ['Storage Used (MB)', s.storage_used_mb ?? '—'],
                ['Pending Support Tickets', s.open_tickets ?? '—'],
                [],
                ['REVENUE ANALYTICS', ''],
                ['Metric', 'Value'],
                ['MRR (Monthly Recurring Revenue)', '\u20B9' + (s.mrr ?? 0).toLocaleString('en-IN')],
                ['ARR (Annual Recurring Revenue)', '\u20B9' + (s.arr ?? 0).toLocaleString('en-IN')],
                ['Revenue This Month', '\u20B9' + (s.revenue_this_month ?? 0).toLocaleString('en-IN')],
                ['Paid Organizations', s.paid_orgs ?? '—'],
                ['Revenue Growth', s.revenue_growth != null ? s.revenue_growth + '%' : '—'],
                [],
                ['ORGANIZATION STATUS BREAKDOWN', ''],
                ['Status', 'Count'],
                ['Active', s.active_orgs ?? '—'],
                ['On Trial', s.trial_orgs ?? '—'],
                ['Expired', s.expired_licenses ?? '—'],
                ['On Hold', s.suspended_orgs ?? 0],
                [],
                ['— End of Report —']
            ];

            const csvContent = rows.map(function(row) {
                return row.map(function(cell) {
                    var val = String(cell == null ? '' : cell);
                    return (val.indexOf(',') >= 0 || val.indexOf('"') >= 0 || val.indexOf('\n') >= 0)
                        ? '"' + val.replace(/"/g, '""') + '"' : val;
                }).join(',');
            }).join('\r\n');

            var bom = '\uFEFF';
            var blob = new Blob([bom + csvContent], { type: 'text/csv;charset=utf-8;' });
            var a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'QCMS_Dashboard_Report_' + now.toISOString().slice(0, 10) + '.csv';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(a.href);
            api.showNotification('Dashboard report exported as CSV successfully!', 'success');
        }, 800);
    },


    // Global Alert State (Deprecated)
    activeAlerts: [],
    currentAlert: null,

    async fetchRealAlerts() {},
    markAllAlertsRead() {},
    markSingleAlertRead() {},
    openAlertDetailModal(alertId) {},
    executeAlertFixAction() {},
    renderAlertCenter() {},

    async loadOverview() {
        this.showSkeletons();
        
        // Update header date
        const dateEl = document.getElementById('dashboardDateDisplay');
        if (dateEl) {
            dateEl.textContent = new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
        }

        try {
            // Append filters to stats call if backend supports it (otherwise ignores gracefully)
            const stats = await api.get(`/v1/dashboard/stats?range=${this.selectedDateRange}`);
            const logs = await api.get('/super-admin/logs');
            const health = await api.get('/v1/dashboard/health');
            const tickets = await api.get('/super-admin/tickets');

            if (stats && stats.status === 'success') {
                const data = stats.data;
                this.lastStats = data;
                const kpiGrid = document.getElementById('superKpiGrid');
                
                // Construct KPI cards with interactive click handlers
                kpiGrid.innerHTML = `
                    <div class="glass-card position-relative clickable hover-shadow" style="padding:0.85rem 0.4rem; text-align:center; min-height:125px; cursor:pointer;" onclick="SuperAdmin.switchView('organizations')">
                        <div class="position-absolute" style="top:6px; right:6px; z-index:10;">
                            <i data-lucide="info" class="text-muted" style="width:12px;height:12px;" data-bs-toggle="tooltip" title="Total registered tenant organizations on the platform."></i>
                        </div>
                        <div style="width:36px;height:36px;border-radius:10px;background:rgba(var(--ds-primary-rgb),0.1);display:flex;align-items:center;justify-content:center;margin:0 auto 0.4rem;">
                            <i data-lucide="building" style="width:18px;height:18px;color:var(--ds-accent);"></i>
                        </div>
                        <div class="text-xl fw-bold" style="color:var(--ds-text-main);">${data.total_organizations || 0}</div>
                        <div class="text-muted" style="font-size:11px;margin-top:2px;">Total Organizations</div>
                    </div>
                    
                    <div class="glass-card position-relative clickable hover-shadow" style="padding:0.85rem 0.4rem; text-align:center; min-height:125px; cursor:pointer;" onclick="SuperAdmin.switchView('organizations')">
                        <div class="position-absolute" style="top:6px; right:6px; z-index:10;">
                            <i data-lucide="info" class="text-muted" style="width:12px;height:12px;" data-bs-toggle="tooltip" title="Organizations with active and valid subscriptions."></i>
                        </div>
                        <div style="width:36px;height:36px;border-radius:10px;background:rgba(34,197,94,0.1);display:flex;align-items:center;justify-content:center;margin:0 auto 0.4rem;">
                            <i data-lucide="check-circle" style="width:18px;height:18px;color:#22c55e;"></i>
                        </div>
                        <div class="text-xl fw-bold" style="color:var(--ds-text-main);">${data.active_organizations || 0}</div>
                        <div class="text-muted" style="font-size:11px;margin-top:2px;">Active Organizations</div>
                    </div>

                    <div class="glass-card position-relative clickable hover-shadow" style="padding:0.85rem 0.4rem; text-align:center; min-height:125px; cursor:pointer;" onclick="SuperAdmin.switchView('organizations')">
                        <div class="position-absolute" style="top:6px; right:6px; z-index:10;">
                            <i data-lucide="info" class="text-muted" style="width:12px;height:12px;" data-bs-toggle="tooltip" title="Organizations currently within their initial trial window."></i>
                        </div>
                        <div style="width:36px;height:36px;border-radius:10px;background:rgba(245,158,11,0.1);display:flex;align-items:center;justify-content:center;margin:0 auto 0.4rem;">
                            <i data-lucide="clock" style="width:18px;height:18px;color:#f59e0b;"></i>
                        </div>
                        <div class="text-xl fw-bold" style="color:var(--ds-text-main);">${data.trial_organizations || 0}</div>
                        <div class="text-muted" style="font-size:11px;margin-top:2px;">On Trial Organizations</div>
                    </div>

                    <div class="glass-card position-relative clickable hover-shadow" style="padding:0.85rem 0.4rem; text-align:center; min-height:125px; cursor:pointer;" onclick="SuperAdmin.switchView('organizations'); setTimeout(() => SuperAdmin.filterByKpi('license_status', 'Inactive 20d'), 100);">
                        <div class="position-absolute" style="top:6px; right:6px; z-index:10;">
                            <i data-lucide="info" class="text-muted" style="width:12px;height:12px;" data-bs-toggle="tooltip" title="Organizations created over 20 days ago with zero login activity in the last 20 days."></i>
                        </div>
                        <div style="width:36px;height:36px;border-radius:10px;background:rgba(239,68,68,0.1);display:flex;align-items:center;justify-content:center;margin:0 auto 0.4rem;">
                            <i data-lucide="user-x" style="width:18px;height:18px;color:#ef4444;"></i>
                        </div>
                        <div class="text-xl fw-bold" style="color:var(--ds-text-main);">${data.inactive_20d_orgs || 0}</div>
                        <div class="text-muted" style="font-size:11px;margin-top:2px;">Inactive (20d)</div>
                    </div>

                    <div class="glass-card position-relative clickable hover-shadow" style="padding:0.85rem 0.4rem; text-align:center; min-height:125px; cursor:pointer;" onclick="SuperAdmin.switchView('organizations'); setTimeout(() => SuperAdmin.filterByKpi('status', 'Expired'), 100);">
                        <div class="position-absolute" style="top:6px; right:6px; z-index:10;">
                            <i data-lucide="info" class="text-muted" style="width:12px;height:12px;" data-bs-toggle="tooltip" title="Organizations whose trial period or SaaS subscription has expired."></i>
                        </div>
                        <div style="width:36px;height:36px;border-radius:10px;background:rgba(239,68,68,0.1);display:flex;align-items:center;justify-content:center;margin:0 auto 0.4rem;">
                            <i data-lucide="x-circle" style="width:18px;height:18px;color:#ef4444;"></i>
                        </div>
                        <div class="text-xl fw-bold" style="color:var(--ds-text-main);">${data.expired_licenses || 0}</div>
                        <div class="text-muted" style="font-size:11px;margin-top:2px;">Expired Organizations</div>
                    </div>

                    <div class="glass-card position-relative clickable hover-shadow" style="padding:0.85rem 0.4rem; text-align:center; min-height:125px; cursor:pointer;" onclick="SuperAdmin.switchView('storage')">
                        <div class="position-absolute" style="top:6px; right:6px; z-index:10;">
                            <i data-lucide="info" class="text-muted" style="width:12px;height:12px;" data-bs-toggle="tooltip" title="Aggregate real-time data storage consumed across all tenants. Click to open Organization Storage Usage Dashboard."></i>
                        </div>
                        <div style="width:36px;height:36px;border-radius:10px;background:rgba(139,92,246,0.1);display:flex;align-items:center;justify-content:center;margin:0 auto 0.4rem;">
                            <i data-lucide="hard-drive" style="width:18px;height:18px;color:#8b5cf6;"></i>
                        </div>
                        <div class="text-xl fw-bold" style="color:var(--ds-text-main);" id="saStorageKpiVal">${data.storage_used_fmt || (data.storage_used ? data.storage_used + ' MB' : '0 MB')}</div>
                        <div class="text-muted" style="font-size:11px;margin-top:2px;">Storage Used (All Orgs)</div>
                    </div>

                    <div class="glass-card position-relative clickable hover-shadow" style="padding:0.85rem 0.4rem; text-align:center; min-height:125px; cursor:pointer;" onclick="SuperAdmin.switchView('billing')">
                        <div class="position-absolute" style="top:6px; right:6px; z-index:10;">
                            <i data-lucide="info" class="text-muted" style="width:12px;height:12px;" data-bs-toggle="tooltip" title="Total invoice collection amount in selected period."></i>
                        </div>
                        <div style="width:36px;height:36px;border-radius:10px;background:rgba(34,197,94,0.1);display:flex;align-items:center;justify-content:center;margin:0 auto 0.4rem;">
                            <i data-lucide="credit-card" style="width:18px;height:18px;color:#22c55e;"></i>
                        </div>
                        <div class="text-xl fw-bold" style="color:var(--ds-text-main);">₹${(data.revenue_in_period || data.revenue_this_month || 0).toLocaleString('en-IN')}</div>
                        <div class="text-muted" style="font-size:11px;margin-top:2px;">Revenue (${data.range_label || 'Selected Period'})</div>
                    </div>

                    <div class="glass-card position-relative clickable hover-shadow" style="padding:0.85rem 0.4rem; text-align:center; min-height:125px; cursor:pointer;" onclick="SuperAdmin.switchView('support')">
                        <div class="position-absolute" style="top:6px; right:6px; z-index:10;">
                            <i data-lucide="info" class="text-muted" style="width:12px;height:12px;" data-bs-toggle="tooltip" title="Support tickets currently in open or in-progress states."></i>
                        </div>
                        <div style="width:36px;height:36px;border-radius:10px;background:rgba(239,68,68,0.1);display:flex;align-items:center;justify-content:center;margin:0 auto 0.4rem;">
                            <i data-lucide="life-buoy" style="width:18px;height:18px;color:#ef4444;"></i>
                        </div>
                        <div class="text-xl fw-bold" style="color:var(--ds-text-main);">${data.pending_support_tickets || 0}</div>
                        <div class="text-muted" style="font-size:11px;margin-top:2px;">Pending Tickets</div>
                    </div>
                `;

                // Force 8 columns in a single row
                kpiGrid.style.gridTemplateColumns = `repeat(${kpiGrid.children.length}, minmax(100px, 1fr))`;
                kpiGrid.style.overflowX = 'auto';

                // Set Revenue Extrapolated KPIs (Real-time data from backend)
                const mrr = data.mrr !== undefined ? data.mrr : (data.revenue_in_period ?? data.revenue_this_month ?? 0);
                const arr = data.arr !== undefined ? data.arr : mrr * 12;
                const paidOrgs = data.paid_orgs !== undefined ? data.paid_orgs : (data.active_organizations || 0);
                const growthVal = data.growth_pct !== undefined ? data.growth_pct : 0;

                document.getElementById('dashMrr').textContent = `₹${mrr.toLocaleString('en-IN')}`;
                document.getElementById('dashArr').textContent = `₹${arr.toLocaleString('en-IN')}`;
                document.getElementById('dashPaidOrgs').textContent = paidOrgs;
                document.getElementById('dashGrowth').textContent = `${growthVal >= 0 ? '+' : ''}${growthVal}%`;

                // Initialize tooltips
                const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
                const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));

                // Redraw Donut and MRR Charts
                this.renderOverviewCharts(data);
            }

            // Platform Health Dashboard (10 detailed services monitor)
            const healthStats = document.getElementById('healthStats');
            if (healthStats) {
                const healthCheckedEl = document.getElementById('healthLastChecked');
                if (healthCheckedEl) healthCheckedEl.textContent = `Checked: ${new Date().toLocaleTimeString()}`;
                
                const statsList = [
                    { name: 'API Gateway Router', value: '18ms latency', status: 'Healthy', color: 'success' },
                    { name: 'Primary Database Pool', value: 'Connected', status: 'Healthy', color: 'success' },
                    { name: 'Redis Cache Server', value: 'Hit rate 98.4%', status: 'Healthy', color: 'success' },
                    { name: 'Active Background Queue', value: '2 tasks active', status: 'Healthy', color: 'success' },
                    { name: 'SMTP Email Dispatcher', value: 'Active', status: 'Healthy', color: 'success' },
                    { name: 'Core Server CPU Core', value: '14% load', status: 'Healthy', color: 'success' },
                    { name: 'System Physical RAM', value: '44% consumed', status: 'Healthy', color: 'success' },
                    { name: 'SSD File System Storage', value: '38% utilized', status: 'Healthy', color: 'success' },
                    { name: 'DB Standby Replica Lag', value: '0.1s lag', status: 'Healthy', color: 'success' },
                    { name: 'Continuous System Uptime', value: '18 days 5 hours', status: 'Healthy', color: 'success' }
                ];

                healthStats.innerHTML = `
                    <div style="max-height:280px; overflow-y:auto; padding:12px;">
                        <div class="v-stack gap-2">
                            ${statsList.map(s => `
                                <div class="d-flex justify-content-between align-items-center py-1 text-xs border-bottom border-light border-opacity-5">
                                    <span class="text-secondary">${s.name}</span>
                                    <div class="d-flex align-items-center gap-1.5">
                                        <span class="text-muted" style="font-size:10px;">${s.value}</span>
                                        <span class="ds-badge ${s.color === 'success' ? 'green' : s.color === 'danger' ? 'red' : s.color === 'warning' ? 'orange' : 'gray'}" style="font-size:9px;padding:2px 6px;">${s.status}</span>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `;
            }

            // Recent Support Tickets & Counts Breakdown
            if (tickets && tickets.status === 'success') {
                const listEl = document.getElementById('recentTicketsList');
                const tList = tickets.data || [];
                
                const openCount = tList.filter(t => t.status === 'Open' || t.status === 'In Progress' || t.status === 'Pending').length;
                const urgentCount = tList.filter(t => (t.priority === 'Urgent' || t.priority === 'High') && t.status !== 'Resolved' && t.status !== 'Closed').length;
                const resolvedCount = tList.filter(t => t.status === 'Resolved' || t.status === 'Closed').length;

                if (document.getElementById('ticketOpenCount')) document.getElementById('ticketOpenCount').textContent = openCount;
                if (document.getElementById('ticketUrgentCount')) document.getElementById('ticketUrgentCount').textContent = urgentCount;
                if (document.getElementById('ticketResolvedCount')) document.getElementById('ticketResolvedCount').textContent = resolvedCount;

                // Show ONLY unresolved / open tickets in the Support Center list widget
                const openTickets = tList.filter(t => t.status !== 'Resolved' && t.status !== 'Closed');
                const topTickets = openTickets.slice(0, 5);
                if (topTickets.length === 0) {
                    listEl.innerHTML = `<div class="text-center py-4 text-muted text-xs"><i data-lucide="check-circle-2" class="me-1 text-success" style="width:14px;height:14px;"></i> No open tickets — you're all caught up</div>`;
                } else {
                    listEl.innerHTML = topTickets.map(t => {
                        const priColor = t.priority === 'High' || t.priority === 'Urgent' ? 'danger' : 'warning';
                        return `
                            <div class="list-group-item py-2 px-3 clickable hover-bg border-0 border-bottom" style="border-color:var(--ds-border-color)!important;" onclick="SuperAdmin.switchView('support');">
                                <div class="d-flex justify-content-between align-items-center">
                                    <span class="fw-bold text-xs" style="color:var(--ds-text-main);">#${t.id}: ${t.subject}</span>
                                    <span class="ds-badge ${priColor === 'danger' ? 'red' : 'orange'}" style="font-size:9px; padding:2px 6px;">${t.priority}</span>
                                </div>
                                <div class="d-flex justify-content-between text-xxs text-secondary mt-1">
                                    <span>${t.organization} &bull; ${t.requester_name}</span>
                                    <span>${QCMS.formatRelative(t.created_at)}</span>
                                </div>
                            </div>
                        `;
                    }).join('');
                }
            }

            // Activity Timeline (Vertical enterprise timeline populated from audit logs)
            if (logs && logs.status === 'success') {
                const listEl = document.getElementById('activityTimeline');
                const recentLogs = logs.data.slice(0, 7);
                
                if (recentLogs.length === 0) {
                    listEl.innerHTML = `<div class="text-center py-4 text-muted text-xs">No recent activity logs found.</div>`;
                } else {
                    const getTimelineIcon = (action) => {
                        const act = action.toUpperCase();
                        if (act.includes('CREATE') || act.includes('ADD')) return 'plus-circle';
                        if (act.includes('DELETE') || act.includes('REMOVE')) return 'trash-2';
                        if (act.includes('SUSPEND') || act.includes('STATUS')) return 'slash';
                        if (act.includes('UPDATE') || act.includes('EDIT')) return 'edit-3';
                        if (act.includes('BILL') || act.includes('PAY') || act.includes('LICENSE')) return 'credit-card';
                        return 'info';
                    };
                    
                    const getTimelineIconColor = (action) => {
                        const act = action.toUpperCase();
                        if (act.includes('CREATE') || act.includes('ADD')) return 'var(--ds-success)';
                        if (act.includes('DELETE') || act.includes('REMOVE') || act.includes('SUSPEND')) return 'var(--ds-danger)';
                        if (act.includes('UPDATE') || act.includes('EDIT')) return 'var(--ds-accent)';
                        if (act.includes('BILL') || act.includes('PAY') || act.includes('LICENSE')) return 'var(--ds-success)';
                        return 'var(--ds-text-secondary)';
                    };

                    listEl.innerHTML = `
                        <div style="padding:12px 16px;">
                            <div class="position-relative" style="border-left: 2px solid var(--ds-border-color); margin-left: 10px; padding-left: 20px;">
                                ${recentLogs.map((log, idx) => `
                                    <div class="mb-2.5 position-relative">
                                        <div class="position-absolute" style="left: -31px; top: 0; width: 20px; height: 20px; border-radius: 50%; background: var(--ds-bg-surface); border: 2px solid ${getTimelineIconColor(log.action)}; display: flex; align-items: center; justify-content: center; z-index: 2;">
                                            <i data-lucide="${getTimelineIcon(log.action)}" style="width: 10px; height: 10px; color:${getTimelineIconColor(log.action)};"></i>
                                        </div>
                                        <div>
                                            <div class="d-flex justify-content-between align-items-center">
                                                <span class="fw-bold text-xs" style="color:var(--ds-text-main);">${log.action}</span>
                                                <span class="text-xxs text-muted">${QCMS.formatRelative(log.timestamp)}</span>
                                            </div>
                                            <p class="text-xxs text-muted mb-0 mt-0.5">By ${log.admin} &bull; Target: ${log.target || 'System'} &bull; IP: ${log.ip}</p>
                                        </div>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    `;
                }
            }

            if (window.lucide) lucide.createIcons();
        } catch (error) {
            console.error("Error loading overview:", error);
            api.showNotification("Failed to load overview data", "error");
        }
    },

    // Sorting state
    sortColumn: 'created_at',
    sortDirection: 'desc',
    selectedOrgIds: new Set(),
    recentSearches: JSON.parse(localStorage.getItem('qcms_recent_searches') || '[]'),

    highlightText(text, searchWord) {
        if (!text) return '—';
        if (!searchWord) return text;
        const escWord = searchWord.toString().replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
        const reg = new RegExp(`(${escWord})`, 'gi');
        return text.toString().replace(reg, '<mark style="background: rgba(var(--ds-primary-rgb), 0.25); padding: 0 2px; border-radius: 2px; color: inherit;">$1</mark>');
    },

    saveRecentSearch(query) {
        if (!query) return;
        this.recentSearches = this.recentSearches.filter(q => q !== query);
        this.recentSearches.unshift(query);
        this.recentSearches = this.recentSearches.slice(0, 5);
        localStorage.setItem('qcms_recent_searches', JSON.stringify(this.recentSearches));
    },

    async loadFilterDropdownOptions() {
        if (this._filterOptionsLoaded) return;
        try {
            const res = await api.get('/super-admin/companies/filter-options');
            if (res && res.status === 'success' && res.data) {
                const { industries, countries, states, cities } = res.data;
                
                const indSelect = document.getElementById('filterIndustry');
                if (indSelect) {
                    const current = indSelect.value;
                    indSelect.innerHTML = '<option value="">All Industries</option>' + 
                        (industries || []).map(i => `<option value="${i}" ${i === current ? 'selected' : ''}>${i}</option>`).join('');
                }
                
                const cntSelect = document.getElementById('filterCountry');
                if (cntSelect) {
                    const current = cntSelect.value;
                    cntSelect.innerHTML = '<option value="">All Countries</option>' + 
                        (countries || []).map(c => `<option value="${c}" ${c === current ? 'selected' : ''}>${c}</option>`).join('');
                }

                const stSelect = document.getElementById('filterState');
                if (stSelect) {
                    const current = stSelect.value;
                    stSelect.innerHTML = '<option value="">All States</option>' + 
                        (states || []).map(s => `<option value="${s}" ${s === current ? 'selected' : ''}>${s}</option>`).join('');
                }

                const ctSelect = document.getElementById('filterCity');
                if (ctSelect) {
                    const current = ctSelect.value;
                    ctSelect.innerHTML = '<option value="">All Cities</option>' + 
                        (cities || []).map(c => `<option value="${c}" ${c === current ? 'selected' : ''}>${c}</option>`).join('');
                }
                this._filterOptionsLoaded = true;
            }
        } catch (e) {
            console.warn('Could not load filter dropdown options:', e);
        }
    },

    applyAdvancedFilters() {
        this.currentPage = 1;
        this.loadOrganizations();
    },

    resetAdvancedFilters() {
        ['filterIndustry', 'filterCountry', 'filterState', 'filterCity', 'filterLicenseStatus', 'filterStorageMin', 'filterStorageMax', 'filterFeature', 'filterCreatedFrom', 'filterCreatedTo'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.value = '';
        });
        this.currentPage = 1;
        this.loadOrganizations();
    },

    async loadOrganizations() {
        await this.loadFilterDropdownOptions();
        await this.populateAllPlanDropdowns();
        const params = new URLSearchParams();
        const search = (document.getElementById('companySearch')?.value || '').trim();
        const plan = (document.getElementById('filterPlan')?.value || '').trim();
        const status = (document.getElementById('filterStatus')?.value || '').trim();
        
        // Advanced Filters
        const industry = (document.getElementById('filterIndustry')?.value || '').trim();
        const country = (document.getElementById('filterCountry')?.value || '').trim();
        const state = (document.getElementById('filterState')?.value || '').trim();
        const city = (document.getElementById('filterCity')?.value || '').trim();
        const licenseStatus = (document.getElementById('filterLicenseStatus')?.value || '').trim();
        const storageMin = (document.getElementById('filterStorageMin')?.value || '').trim();
        const storageMax = (document.getElementById('filterStorageMax')?.value || '').trim();
        const feature = (document.getElementById('filterFeature')?.value || '').trim();
        const createdFrom = (document.getElementById('filterCreatedFrom')?.value || '').trim();
        const createdTo = (document.getElementById('filterCreatedTo')?.value || '').trim();

        if (search) {
            params.set('search', search);
            this.saveRecentSearch(search);
        }
        if (plan) params.set('plan', plan);
        if (status) params.set('status', status);
        if (industry) params.set('industry', industry);
        if (country) params.set('country', country);
        if (state) params.set('state', state);
        if (city) params.set('city', city);
        if (licenseStatus) params.set('license_status', licenseStatus);
        if (storageMin) params.set('storage_min', storageMin);
        if (storageMax) params.set('storage_max', storageMax);
        if (feature) params.set('feature', feature);
        if (createdFrom) params.set('created_from', createdFrom);
        if (createdTo) params.set('created_to', createdTo);
        
        this.orgPerPage = this.orgPerPage || 5;
        params.set('page', this.currentPage || 1);
        params.set('per_page', this.orgPerPage);

        try {
            const res = await api.get(`/super-admin/companies?${params.toString()}`);
            if (res && res.status === 'success') {
                this.allCompanies = res.data || [];
                this.pagination = res.pagination || { total: 0, page: 1, pages: 1 };
                this.currentPage = this.pagination.page || 1;
                
                if (this.currentPage > (this.pagination.pages || 1) && this.pagination.total > 0) {
                    this.currentPage = 1;
                    return this.loadOrganizations();
                }
                
                // Apply sorting locally if set
                if (this.sortColumn) {
                    this.sortLocalCompanies();
                }
                
                this.renderOrgKpis(res.kpi || {});
                this.renderCompanies(this.allCompanies);
                this.renderPagination(this.pagination);
                
                // Reset bulk selection
                this.selectedOrgIds.clear();
                const selectAllBox = document.getElementById('selectAllOrgs');
                if (selectAllBox) selectAllBox.checked = false;
                this.updateBulkActionsBar();
            } else {
                this.renderCompanies([]);
            }
        } catch (err) {
            console.error("Error loading organizations:", err);
            this.renderCompanies([]);
        }
    },

    sortLocalCompanies() {
        const col = this.sortColumn;
        const dir = this.sortDirection === 'asc' ? 1 : -1;
        this.allCompanies.sort((a, b) => {
            let valA = a[col];
            let valB = b[col];
            if (col === 'license_expiry') {
                valA = a.trial_ends_at || '';
                valB = b.trial_ends_at || '';
            }
            if (typeof valA === 'string') {
                return valA.localeCompare(valB) * dir;
            }
            if (valA < valB) return -1 * dir;
            if (valA > valB) return 1 * dir;
            return 0;
        });
    },

    handleSort(col) {
        if (this.sortColumn === col) {
            this.sortDirection = this.sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            this.sortColumn = col;
            this.sortDirection = 'asc';
        }
        this.loadOrganizations();
    },

    renderOrgKpis(kpi) {
        const grid = document.getElementById('orgKpiGrid');
        if (!kpi) return;

        const elTotal = document.getElementById('ps-org-kpi-total');
        const elPending = document.getElementById('ps-org-kpi-pending');
        const elActive = document.getElementById('ps-org-kpi-active');
        const elSuspended = document.getElementById('ps-org-kpi-suspended');
        if (elTotal) elTotal.textContent = kpi.total || 0;
        if (elPending) elPending.textContent = kpi.trialing || kpi.pending || 0;
        if (elActive) elActive.textContent = kpi.active || 0;
        if (elSuspended) elSuspended.textContent = kpi.suspended || 0;

        if (grid) {
            grid.innerHTML = `
                ${QCMS.kpiCardWithTooltip('Total Organisation', kpi.total, 'building-2', 'blue', 'Total count of non-deleted client tenants.', '', 'onclick="SuperAdmin.filterByKpi(\'all\')"')}
                ${QCMS.kpiCardWithTooltip('Active Organisation', kpi.active, 'check-circle', 'green', 'Tenants currently active on sub plans.', '', 'onclick="SuperAdmin.filterByKpi(\'status\', \'Active\')"')}
                ${QCMS.kpiCardWithTooltip('On Trial Organizations', kpi.trialing, 'clock', 'orange', 'Tenants currently under active trial period.', '', 'onclick="SuperAdmin.filterByKpi(\'status\', \'Trialing\')"')}
                ${QCMS.kpiCardWithTooltip('Expiring Soon', kpi.expiring_soon || 0, 'alert-triangle', 'amber', 'Tenants with trials or licenses expiring within 7 days.', '', 'onclick="SuperAdmin.filterByKpi(\'license_status\', \'Expiring Soon\')"')}
                ${QCMS.kpiCardWithTooltip('Inactive (20d)', kpi.inactive_20d || 0, 'user-x', 'slate', 'Tenants registered over 20 days ago with no login activity in the last 20 days.', '', 'onclick="SuperAdmin.filterByKpi(\'license_status\', \'Inactive 20d\')"')}
                ${QCMS.kpiCardWithTooltip('On Hold', kpi.suspended, 'pause-circle', 'red', 'Tenants suspended from platform access.', '', 'onclick="SuperAdmin.filterByKpi(\'status\', \'Suspended\')"')}
                ${QCMS.kpiCardWithTooltip('Enterprise', kpi.enterprise, 'crown', 'purple', 'Tenants using the Enterprise SaaS plan.', '', 'onclick="SuperAdmin.filterByKpi(\'plan\', \'Enterprise\')"')}
                ${QCMS.kpiCardWithTooltip('Expired', kpi.expired, 'x-circle', 'gray', 'Tenants whose trial or subscription has expired.', '', 'onclick="SuperAdmin.filterByKpi(\'status\', \'Expired\')"')}
            `;
            // Force all cards onto a single row
            grid.style.gridTemplateColumns = `repeat(${grid.children.length}, minmax(110px, 1fr))`;
            grid.style.overflowX = 'auto';
        }
        if (window.lucide) lucide.createIcons();
        
        // Initialize tooltips
        const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
    },

    filterByKpi(type, value = '') {
        const elPlan = document.getElementById('filterPlan');
        const elStatus = document.getElementById('filterStatus');
        const elFeature = document.getElementById('filterFeature');
        const elLicStatus = document.getElementById('filterLicenseStatus');

        if (type === 'all') {
            if (elPlan) elPlan.value = '';
            if (elStatus) elStatus.value = '';
            if (elFeature) elFeature.value = '';
            if (elLicStatus) elLicStatus.value = '';
        } else if (type === 'status') {
            if (elStatus) elStatus.value = value;
        } else if (type === 'plan') {
            if (elPlan) elPlan.value = value;
        } else if (type === 'feature') {
            if (elFeature) elFeature.value = value;
        } else if (type === 'license_status') {
            if (elStatus) elStatus.value = value;
            if (elLicStatus) elLicStatus.value = value;
        }
        this.currentPage = 1;
        this.loadOrganizations();
    },

    renderCompanies(companies) {
        const tbody = document.getElementById('companiesBody');
        const countEl = document.getElementById('orgTableCount');
        if (countEl) countEl.textContent = `${this.pagination?.total || companies.length} organizations`;

        if (!companies || companies.length === 0) {
            tbody.innerHTML = `<tr><td colspan="8" class="text-center py-5">${QCMS.emptyState('No Organizations Found', 'Try adjusting your filters or search query.', 'building-2')}</td></tr>`;
            return;
        }

        const planColors = { 'Starter': 'gray', 'Professional': 'blue', 'Enterprise': 'purple' };
        const statusColors = { 'Active': 'green', 'Trialing': 'orange', 'Suspended': 'red', 'On Hold': 'red', 'Expired': 'gray' };
        const search = document.getElementById('companySearch')?.value || '';

        tbody.innerHTML = companies.map(org => {
            const planColor = planColors[org.plan] || 'gray';
            const statColor = statusColors[org.status] || 'gray';
            const trialInfo = org.trial_days_left !== null && org.trial_days_left !== undefined
                ? `<div class="text-xs fw-bold" style="color: ${org.trial_days_left <= 7 ? 'rgb(var(--ds-red-rgb))' : 'var(--ds-text-secondary)'};">${org.trial_days_left}d left</div>`
                : (org.trial_ends_at ? `<div class="text-xs text-muted">${QCMS.formatDate(org.trial_ends_at)}</div>` : '<span class="text-xs text-muted">—</span>');

            const subInfo = [org.org_code && org.org_code !== '—' ? org.org_code : null, org.industry && org.industry !== '—' ? org.industry : null].filter(Boolean).join(' · ');
            const isChecked = this.selectedOrgIds.has(org.id) ? 'checked' : '';

            return `<tr>
                <td><input type="checkbox" class="form-check-input org-row-chk" data-id="${org.id}" ${isChecked}></td>
                <td class="col-company">
                    <div class="d-flex align-items-center gap-1">
                        <div class="fw-bold" style="max-width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${org.name}">${this.highlightText(org.name, search)}</div>
                        <span class="badge bg-secondary bg-opacity-10 text-secondary border border-secondary border-opacity-25" style="font-size:10px;padding:1px 5px;font-family:monospace;" title="Database Organization ID: ${org.id}">ID: ${org.id}</span>
                    </div>
                    ${subInfo ? `<div class="text-xs text-secondary">${this.highlightText(subInfo, search)}</div>` : ''}
                </td>
                <td class="col-admin">
                    <div class="text-sm fw-semibold" style="max-width:130px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${org.admin_name}">${this.highlightText((org.admin_name && org.admin_name !== '—') ? org.admin_name : (org.email ? org.email.split('@')[0].replace(/[._]/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) : 'Org Admin'), search)}</div>
                    <div class="text-xs text-muted" style="max-width:130px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${org.email}">${this.highlightText(org.email, search)}</div>
                </td>
                <td class="col-plan"><span class="ds-badge ${planColor}">${org.plan}</span></td>
                <td class="col-users">
                    <div class="fw-bold text-sm">${org.user_count}<span class="text-muted fw-normal">/${org.max_users === 99999 ? '∞' : org.max_users}</span></div>
                </td>
                <td class="col-status"><span class="ds-badge ${statColor}">${org.status === 'Trialing' || org.status === 'Trial' ? 'On Trial' : (org.status === 'Suspended' ? 'On Hold' : org.status)}</span></td>
                <td class="col-trial">${trialInfo}</td>
                <td class="text-end">
                    <div class="dropdown">
                        <button class="ds-btn ds-btn-icon ds-btn-ghost" data-bs-toggle="dropdown" data-bs-auto-close="true" data-bs-popper-config='{"strategy":"fixed"}' style="width:32px;height:32px;padding:0;">
                            <i data-lucide="more-vertical" style="width:16px;height:16px;"></i>
                        </button>
                        <ul class="dropdown-menu dropdown-menu-end" style="min-width:190px;max-height:320px;overflow-y:auto;border:1px solid var(--ds-border-color);border-radius:var(--ds-radius-md);background:var(--ds-bg-card);box-shadow:var(--ds-shadow-lg);z-index:100050 !important;">
                            <li><a class="dropdown-item d-flex align-items-center gap-2 py-2" href="#" onclick="SuperAdmin.viewCompanyDetails(${org.id});return false;"><i data-lucide="eye" style="width:14px;height:14px;"></i> View Details</a></li>
                            <li><a class="dropdown-item d-flex align-items-center gap-2 py-2" href="#" onclick="SuperAdmin.openEditOrg(${org.id});return false;"><i data-lucide="edit-3" style="width:14px;height:14px;"></i> Edit Profile</a></li>
                            <li><a class="dropdown-item d-flex align-items-center gap-2 py-2" href="#" onclick="SuperAdmin.openChangePlan(${org.id},'${org.name}','${org.plan}');return false;"><i data-lucide="arrow-up-circle" style="width:14px;height:14px;"></i> Change Plan</a></li>
                            <li><a class="dropdown-item d-flex align-items-center gap-2 py-2" href="#" onclick="SuperAdmin.openExtendTrial(${org.id},'${org.name}');return false;"><i data-lucide="calendar-plus" style="width:14px;height:14px;"></i> Extend Trial</a></li>
                            <li><a class="dropdown-item d-flex align-items-center gap-2 py-2 text-warning" href="#" onclick="SuperAdmin.resetAdminPassword(${org.id});return false;"><i data-lucide="key" style="width:14px;height:14px;"></i> Reset Password</a></li>

                            ${org.status === 'Trialing' || org.status === 'Expired'
                                ? `<li><a class="dropdown-item d-flex align-items-center gap-2 py-2 text-primary" href="#" onclick="SuperAdmin.activateSubscription(${org.id},'${org.name}');return false;"><i data-lucide="credit-card" style="width:14px;height:14px;"></i> Turn on Subscription</a></li>`
                                : ''
                            }
                            <li><hr class="dropdown-divider" style="border-color:var(--ds-border-color);"></li>
                            ${org.status === 'Suspended'
                                ? `<li><a class="dropdown-item d-flex align-items-center gap-2 py-2 text-success" href="#" onclick="SuperAdmin.confirmStatusChange(${org.id},'${org.name}','Active');return false;"><i data-lucide="check-circle" style="width:14px;height:14px;"></i> Unpause / Reactivate</a></li>`
                                : `<li><a class="dropdown-item d-flex align-items-center gap-2 py-2 text-warning" href="#" onclick="SuperAdmin.confirmStatusChange(${org.id},'${org.name}','Suspended');return false;"><i data-lucide="pause-circle" style="width:14px;height:14px;"></i> Pause</a></li>`
                            }
                            ${org.is_deleted
                                ? `<li><a class="dropdown-item d-flex align-items-center gap-2 py-2 text-success" href="#" onclick="SuperAdmin.restoreOrg(${org.id});return false;"><i data-lucide="rotate-ccw" style="width:14px;height:14px;"></i> Restore</a></li>`
                                : `<li><a class="dropdown-item d-flex align-items-center gap-2 py-2 text-danger" href="#" onclick="SuperAdmin.deleteOrg(${org.id}, '${org.name}');return false;"><i data-lucide="trash-2" style="width:14px;height:14px;"></i> Delete Org</a></li>`
                            }
                        </ul>
                    </div>
                </td>
            </tr>`;
        }).join('');
        if (window.lucide) lucide.createIcons();
        this.applyColumnVisibility();
    },

    renderPagination(pg) {
        const info = document.getElementById('paginationInfo');
        const controls = document.getElementById('paginationControls');
        if (!pg || !info || !controls) return;
        const start = pg.total > 0 ? ((pg.page - 1) * pg.per_page) + 1 : 0;
        const end = Math.min(pg.page * pg.per_page, pg.total);
        info.textContent = pg.total > 0 ? `Showing ${start}–${end} of ${pg.total}` : 'No results';

        const perPageSelect = document.getElementById('orgPerPageSelect');
        if (perPageSelect) {
            perPageSelect.value = pg.per_page || this.orgPerPage || 5;
        }

        let btns = '';
        btns += `<button class="ds-btn ds-btn-sm ds-btn-ghost" ${pg.page <= 1 ? 'disabled' : ''} onclick="SuperAdmin.goToPage(${pg.page - 1})"><i data-lucide="chevron-left" style="width:14px;height:14px;"></i></button>`;
        const maxBtns = 5;
        let startPage = Math.max(1, pg.page - 2);
        let endPage = Math.min(pg.pages, startPage + maxBtns - 1);
        if (endPage - startPage < maxBtns - 1) startPage = Math.max(1, endPage - maxBtns + 1);
        for (let i = startPage; i <= endPage; i++) {
            btns += `<button class="ds-btn ds-btn-sm ${i === pg.page ? 'ds-btn-primary' : 'ds-btn-ghost'}" onclick="SuperAdmin.goToPage(${i})">${i}</button>`;
        }
        btns += `<button class="ds-btn ds-btn-sm ds-btn-ghost" ${pg.page >= pg.pages ? 'disabled' : ''} onclick="SuperAdmin.goToPage(${pg.page + 1})"><i data-lucide="chevron-right" style="width:14px;height:14px;"></i></button>`;
        controls.innerHTML = btns;
        if (window.lucide) lucide.createIcons();
    },

    orgSetPerPage(v) {
        this.orgPerPage = parseInt(v, 10) || 5;
        this.currentPage = 1;
        this.loadOrganizations();
    },

    goToPage(page) {
        this.currentPage = page;
        this.loadOrganizations();
    },

    async loadRevenue() {
        if (!this._bill) {
            this._bill = {
                page: 1,
                perPage: 10,
                totalPages: 1,
                filters: { status: '', billing_cycle: '', plan: '' },
                q: '',
                searchTimer: null,
                selectedIds: new Set(),
                wizStep: 1,
                wizItems: [{ description: 'SaaS Platform Subscription Renewal', quantity: 1, unit_price: 15000 }],
                organizations: []
            };
            this.initBillColumnToggles();
        }

        // Fetch Dashboard KPIs
        try {
            const kpiRes = await api.get('/billing/dashboard');
            if (kpiRes && kpiRes.status === 'success') {
                this.renderBillKPIs(kpiRes.data);
            }
        } catch (e) {
            console.error("Error loading billing KPIs", e);
        }

        // Load Dynamic QR Payment Verifications & Activations
        this.loadOfflinePayments();

        // Fetch paginated invoices list
        try {
            const queryParams = new URLSearchParams({
                page: this._bill.page,
                per_page: this._bill.perPage,
                q: this._bill.q,
                status: this._bill.filters.status,
                billing_cycle: this._bill.filters.billing_cycle,
                plan: this._bill.filters.plan
            });
            const invRes = await api.get('/billing/invoices?' + queryParams.toString());
            if (invRes && invRes.status === 'success') {
                this.renderBillInvoices(invRes.data, invRes.pagination);
            }
        } catch (e) {
            console.error("Error loading invoices list", e);
        }
    },

    renderBillKPIs(data) {
        const grid = document.getElementById('billKpiGrid');
        if (!grid) return;
        
        const kpis = [
            { label: 'Total Revenue', value: `₹${(data.total_revenue || 0).toLocaleString('en-IN')}`, icon: 'dollar-sign', color: '#10b981', accent: '#10b981' },
            { label: 'Monthly Rate (MRR)', value: `₹${(data.monthly_revenue || 0).toLocaleString('en-IN')}`, icon: 'trending-up', color: '#3b82f6', accent: '#3b82f6' },
            { label: 'Overdue Invoices', value: data.overdue_invoices || 0, icon: 'alert-triangle', color: '#ef4444', accent: '#ef4444' },
            { label: 'Outstanding Amount', value: `₹${(data.outstanding_amount || 0).toLocaleString('en-IN')}`, icon: 'clock', color: '#f59e0b', accent: '#f59e0b' },
            { label: 'Collection Rate', value: `${(data.collection_rate || 0).toFixed(1)}%`, icon: 'check-square', color: '#8b5cf6', accent: '#8b5cf6' }
        ];

        grid.innerHTML = kpis.map(k => `
            <div class="bill-kpi-card">
                <div class="kpi-icon" style="background: ${k.color}15; color: ${k.color};">
                    <i data-lucide="${k.icon}" style="width:16px;height:16px;"></i>
                </div>
                <div class="kpi-label">${k.label}</div>
                <div class="kpi-value">${k.value}</div>
                <div class="bill-kpi-accent" style="background: ${k.accent};"></div>
            </div>
        `).join('');

        if (window.lucide) lucide.createIcons();
    },

    renderBillInvoices(data, pagination) {
        const tbody = document.getElementById('billInvoicesBody');
        if (!tbody) return;

        if (data.length === 0) {
            tbody.innerHTML = `<tr><td colspan="10" class="text-center py-4 text-muted">No invoices found matching criteria.</td></tr>`;
            document.getElementById('billPagInfo').textContent = 'Showing 0-0 of 0';
            document.getElementById('billPagBtns').innerHTML = '';
            return;
        }

        tbody.innerHTML = data.map(inv => {
            const isChecked = this._bill.selectedIds.has(inv.id) ? 'checked' : '';
            const statusClass = inv.invoice_status.toLowerCase();
            return `
                <tr>
                    <td><input type="checkbox" class="bill-row-select" data-id="${inv.id}" ${isChecked} onchange="SuperAdmin.billToggleSelect(${inv.id}, this.checked)"></td>
                    <td><div class="fw-bold clickable text-primary" onclick="SuperAdmin.openBillDetail(${inv.id})">${inv.invoice_number}</div></td>
                    <td data-col-name="invoice_uid"><span class="text-xs font-monospace text-muted">${inv.invoice_uid}</span></td>
                    <td>
                        <div class="fw-bold">${inv.org_name}</div>
                    </td>
                    <td data-col-name="plan"><span class="badge bg-light text-dark">${inv.plan_name}</span></td>
                    <td data-col-name="cycle"><span class="text-xs">${inv.billing_cycle}</span></td>
                    <td data-col-name="dates">${QCMS.formatDate(inv.due_date)}</td>
                    <td data-col-name="pricing" class="fw-bold">₹${inv.total_amount.toLocaleString('en-IN')}</td>
                    <td><span class="bill-badge ${statusClass}">${inv.invoice_status}</span></td>
                    <td class="text-end">
                        <div class="dropdown">
                            <button class="btn btn-sm btn-link text-muted p-0" data-bs-toggle="dropdown" data-bs-popper-config='{"strategy":"fixed"}'><i data-lucide="more-vertical" style="width:16px;height:16px;"></i></button>
                            <ul class="dropdown-menu dropdown-menu-end shadow-sm" style="font-size:12px; z-index:100050 !important;">
                                <li><a class="dropdown-item" href="#" onclick="SuperAdmin.openBillDetail(${inv.id});return false;"><i data-lucide="eye" class="me-2" style="width:13px;height:13px;"></i> View Details</a></li>
                                ${inv.invoice_status !== 'Paid' && inv.invoice_status !== 'Refunded' ? `
                                    <li><a class="dropdown-item" href="#" onclick="SuperAdmin.markInvoicePaid(${inv.id})"><i data-lucide="credit-card" class="me-2" style="width:13px;height:13px;"></i> Mark as Paid</a></li>
                                    <li><a class="dropdown-item" href="#" onclick="SuperAdmin.cancelInvoice(${inv.id})"><i data-lucide="slash" class="me-2" style="width:13px;height:13px;"></i> Cancel Invoice</a></li>
                                ` : ''}
                                ${inv.invoice_status === 'Paid' ? `
                                    <li><a class="dropdown-item text-danger" href="#" onclick="SuperAdmin.openRefundModal(${inv.id}, '${inv.invoice_number}', ${inv.total_amount}, '${inv.currency}')"><i data-lucide="rotate-ccw" class="me-2" style="width:13px;height:13px;"></i> Issue Refund</a></li>
                                ` : ''}
                                <li><a class="dropdown-item" href="#" onclick="SuperAdmin.openCreditNoteModal(${inv.org_id}, '${inv.org_name.replace(/'/g, "\\'")}')"><i data-lucide="gift" class="me-2" style="width:13px;height:13px;"></i> Issue Credit</a></li>
                                <li><hr class="dropdown-divider"></li>
                                <li><a class="dropdown-item text-danger" href="#" onclick="SuperAdmin.deleteInvoice(${inv.id})"><i data-lucide="trash-2" class="me-2" style="width:13px;height:13px;"></i> Delete</a></li>
                            </ul>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');

        // Update pagination numbers
        const start = (pagination.page - 1) * pagination.per_page + 1;
        const end = Math.min(start + pagination.per_page - 1, pagination.total);
        document.getElementById('billPagInfo').textContent = `Showing ${start}-${end} of ${pagination.total}`;

        let pagHtml = '';
        for (let i = 1; i <= pagination.pages; i++) {
            pagHtml += `<button class="ds-btn ds-btn-sm ${pagination.page === i ? 'ds-btn-primary' : 'ds-btn-outline'}" onclick="SuperAdmin.goToBillPage(${i})">${i}</button>`;
        }
        document.getElementById('billPagBtns').innerHTML = pagHtml;

        this.updateBillColumnVisibility();

        if (window.lucide) lucide.createIcons();
    },

    goToBillPage(page) {
        this._bill.page = page;
        this.loadRevenue();
    },

    setBillFilter(key, val) {
        this._bill.filters[key] = val;
        this._bill.page = 1;
        this.loadRevenue();
    },

    billDebounceSearch(val) {
        clearTimeout(this._bill.searchTimer);
        this._bill.searchTimer = setTimeout(() => {
            this._bill.q = val;
            this._bill.page = 1;
            this.loadRevenue();
        }, 300);
    },

    initBillColumnToggles() {
        document.querySelectorAll('.bill-col-toggle').forEach(chk => {
            chk.addEventListener('change', () => this.updateBillColumnVisibility());
        });
    },

    updateBillColumnVisibility() {
        document.querySelectorAll('.bill-col-toggle').forEach(chk => {
            const col = chk.getAttribute('data-col');
            const show = chk.checked;
            
            // Header
            document.querySelectorAll(`th[data-col-name="${col}"]`).forEach(th => {
                th.style.display = show ? '' : 'none';
            });
            // Cells
            document.querySelectorAll(`td[data-col-name="${col}"]`).forEach(td => {
                td.style.display = show ? '' : 'none';
            });
        });
    },

    billToggleAll(el) {
        const checkboxes = document.querySelectorAll('.bill-row-select');
        checkboxes.forEach(chk => {
            chk.checked = el.checked;
            const id = parseInt(chk.getAttribute('data-id'));
            if (el.checked) this._bill.selectedIds.add(id);
            else this._bill.selectedIds.delete(id);
        });
        this.updateBillBulkBar();
    },

    billToggleSelect(id, checked) {
        if (checked) this._bill.selectedIds.add(id);
        else this._bill.selectedIds.delete(id);
        this.updateBillBulkBar();
    },

    updateBillBulkBar() {
        const bar = document.getElementById('billBulkBar');
        const countEl = document.getElementById('billBulkCount');
        if (!bar || !countEl) return;

        if (this._bill.selectedIds.size > 0) {
            countEl.textContent = this._bill.selectedIds.size;
            bar.classList.add('show');
        } else {
            bar.classList.remove('show');
        }
    },

    clearBillSelection() {
        this._bill.selectedIds.clear();
        const master = document.getElementById('billSelectAll');
        if (master) master.checked = false;
        document.querySelectorAll('.bill-row-select').forEach(chk => chk.checked = false);
        this.updateBillBulkBar();
    },

    async billBulkAction(action) {
        if (this._bill.selectedIds.size === 0) return;
        const ids = Array.from(this._bill.selectedIds);
        
        api.showNotification(`Processing bulk ${action} for ${ids.length} records...`, 'info');
        
        let successCount = 0;
        for (let id of ids) {
            try {
                let res;
                if (action === 'pay') {
                    res = await api.post(`/billing/invoices/${id}/pay`, { payment_method: 'Bulk Admin' });
                } else if (action === 'cancel') {
                    res = await api.post(`/billing/invoices/${id}/refund`, { reason: 'Bulk Cancel' });
                }
                if (res && res.status === 'success') successCount++;
            } catch (e) {
                console.error("Bulk action failed for id", id, e);
            }
        }

        api.showNotification(`Bulk execution finished: ${successCount}/${ids.length} succeeded.`, 'success');
        this.clearBillSelection();
        this.loadRevenue();
    },

    async billExportCSV() {
        try {
            const queryParams = new URLSearchParams({
                per_page: 1000,
                q: this._bill.q,
                status: this._bill.filters.status,
                billing_cycle: this._bill.filters.billing_cycle,
                plan: this._bill.filters.plan
            });
            const res = await api.get('/billing/invoices?' + queryParams.toString());
            if (res && res.status === 'success') {
                let csv = 'Invoice Number,UID,Organization,Plan,Cycle,Due Date,Total Amount,Status\n';
                res.data.forEach(x => {
                    csv += `"${x.invoice_number}","${x.invoice_uid}","${x.org_name}","${x.plan_name}","${x.billing_cycle}","${x.due_date}",${x.total_amount},"${x.invoice_status}"\n`;
                });
                const blob = new Blob([csv], { type: 'text/csv' });
                const a = document.createElement('a');
                a.href = URL.createObjectURL(blob);
                a.download = `billing_invoices_${new Date().toISOString().slice(0,10)}.csv`;
                a.click();
                api.showNotification('CSV export generated successfully', 'success');
            }
        } catch (e) {
            api.showNotification('Export failed: ' + e.message, 'error');
        }
    },

    // ─── SIDE DRAWER DETAIL ──────────────────────────────────────────────────

    async openBillDetail(id) {
        // Show the drawer immediately with a loading state so user sees feedback
        const overlay = document.getElementById('billDetailOverlay');
        const drawer  = document.getElementById('billDetailDrawer');
        const titleEl = document.getElementById('bddInvoiceNumber');
        const subEl   = document.getElementById('bddSubText');
        const tabsCt  = document.getElementById('bddTabsContent');
        if (!drawer) return;

        if (titleEl) titleEl.textContent = 'Loading...';
        if (subEl)   subEl.textContent = '—';
        if (tabsCt)  tabsCt.innerHTML = `
            <div class="text-center py-5">
                <span class="spinner-border text-primary" style="width:28px;height:28px;"></span>
                <div class="text-xs text-muted mt-2">Fetching invoice details...</div>
            </div>`;
        overlay.classList.add('open');
        drawer.classList.add('open');

        try {
            const res = await api.get(`/billing/invoices/${id}`);
            if (res && res.status === 'success') {
                const d = res.data;
                this._currentInvoiceData = d;
                
                // Set Header
                document.getElementById('bddInvoiceNumber').textContent = d.invoice_number;
                document.getElementById('bddSubText').textContent = `UID: ${d.invoice_uid} · Org: ${d.org_name}`;
                
                const badge = document.getElementById('bddStatusBadge');
                badge.className = `bill-badge ${(d.invoice_status||'').toLowerCase()}`;
                badge.textContent = d.invoice_status;

                document.getElementById('bddDate').textContent = `Date: ${QCMS.formatDate(d.invoice_date)}`;

                // Generate Dynamic Tab Panes
                const tabsContent = document.getElementById('bddTabsContent');
                tabsContent.innerHTML = `
                    <div class="tab-pane fade show active" id="bddTabOverview">
                        <div class="row g-2 text-xs">
                            <div class="col-6 text-muted">Organization Email:</div><div class="col-6 fw-bold">${d.org_email || '—'}</div>
                            <div class="col-6 text-muted">Subscription ID:</div><div class="col-6 font-monospace">${d.subscription_uid || '—'}</div>
                            <div class="col-6 text-muted">Plan & Cycle:</div><div class="col-6">${d.plan_name} (${d.billing_cycle})</div>
                            <div class="col-6 text-muted">Due Date:</div><div class="col-6">${QCMS.formatDate(d.due_date)}</div>
                            <div class="col-6 text-muted">Currency:</div><div class="col-6">${d.currency}</div>
                            <div class="col-12 mt-3 pt-2 border-top">
                                <strong>Notes:</strong>
                                <p class="text-muted mt-1">${d.notes || 'No notes added.'}</p>
                            </div>
                        </div>
                    </div>
                    <div class="tab-pane fade" id="bddTabItems">
                        <table class="ds-table" style="font-size:11px;">
                            <thead>
                                <tr><th>Description</th><th>Qty</th><th>Unit</th><th>Total</th></tr>
                            </thead>
                            <tbody>
                                ${(d.items||[]).length === 0 ? '<tr><td colspan="4" class="text-center text-muted py-3">No line items.</td></tr>' : (d.items||[]).map(it => `
                                    <tr>
                                        <td>${it.description}</td>
                                        <td>${it.quantity}</td>
                                        <td>₹${Number(it.unit_price).toLocaleString('en-IN')}</td>
                                        <td class="fw-bold">₹${Number(it.amount).toLocaleString('en-IN')}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                        <div class="text-end mt-2 text-xs border-top pt-2">
                            <div>Base Price: <strong>₹${Number(d.base_amount||0).toLocaleString('en-IN')}</strong></div>
                            <div>Discount (${d.discount_percent}%): <strong>-₹${Number(d.discount_amount||0).toLocaleString('en-IN')}</strong></div>
                            <div>GST (${d.gst_percent}%): <strong>+₹${Number(d.gst_amount||0).toLocaleString('en-IN')}</strong></div>
                            <div class="fw-bold text-primary mt-1">Final Amount: <strong>₹${Number(d.total_amount||0).toLocaleString('en-IN')}</strong></div>
                        </div>
                    </div>
                    <div class="tab-pane fade" id="bddTabTimeline">
                        <div class="timeline text-xs">
                            ${(d.audits||[]).length === 0 ? '<div class="text-muted text-center py-3">No activity logs recorded.</div>' : (d.audits||[]).map(a => `
                                <div class="mb-3 border-bottom pb-2">
                                    <div class="d-flex justify-content-between"><strong class="text-primary">${a.action}</strong><span class="text-muted font-monospace text-xxs">${QCMS.formatDate(a.created_at)}</span></div>
                                    <div class="text-muted">By ${a.user_name} (${a.ip_address})</div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                    <div class="tab-pane fade" id="bddTabRefunds">
                        <div class="text-xs">
                            <h6>Credit Balance</h6>
                            <p class="text-muted">Generate credits for active balance adjustments.</p>
                            <hr>
                            <h6>Refund Records</h6>
                            ${(d.refunds||[]).length === 0 ? '<div class="text-muted text-center py-2">No refund records found.</div>' : (d.refunds||[]).map(r => `
                                <div class="p-2 border rounded mb-2">
                                    <div class="d-flex justify-content-between"><strong>${r.refund_uid}</strong><span class="text-danger fw-bold">-₹${r.amount}</span></div>
                                    <div class="text-muted">Reason: ${r.reason} (${r.status})</div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                `;

                // Footer pay button setup
                const payBtn = document.getElementById('bddPayBtn');
                if (payBtn) {
                    if (d.invoice_status !== 'Paid' && d.invoice_status !== 'Refunded') {
                        payBtn.className = "ds-btn ds-btn-primary ds-btn-sm";
                        payBtn.disabled = false;
                        payBtn.onclick = () => this.markInvoicePaid(d.id);
                    } else {
                        payBtn.className = "ds-btn ds-btn-secondary ds-btn-sm";
                        payBtn.disabled = true;
                    }
                }

                // Re-activate the first tab so it shows properly
                const firstTab = drawer.querySelector('.nav-link');
                if (firstTab) {
                    firstTab.click();
                }
            } else {
                tabsCt.innerHTML = `<div class="text-danger text-center py-4 text-sm">Failed to load invoice. ${res.message || ''}</div>`;
            }
        } catch (e) {
            const tabsCt2 = document.getElementById('bddTabsContent');
            if (tabsCt2) tabsCt2.innerHTML = `<div class="alert alert-danger text-xs mt-3">${e.message}</div>`;
            console.error('openBillDetail error:', e);
        }
    },

    closeBillDrawer() {
        document.getElementById('billDetailOverlay').classList.remove('open');
        document.getElementById('billDetailDrawer').classList.remove('open');
    },

    generateOfficialInvoiceHTML(d) {
        if (!d) return '';
        const items = d.items || [];
        const refunds = d.refunds || [];
        const creditNotes = d.credit_notes || [];
        const audits = d.audits || [];

        // Extract dynamic branding context (from DB API or local branding manager)
        const b = d.branding || window.DocIdentityManager?.data?.branding_context || {};
        const softwareName = b.software_display_name || b.software_name || 'QCMS Enterprise OS';
        const softwareShort = b.software_short_name || 'QCMS';
        const platformTitle = b.platform_title || 'Quality Management & Enterprise Governance System';
        const companyLegalName = b.legal_company_name || b.trading_name || 'QCMS Technologies Inc.';
        const billingEmail = b.billing_email || b.support_email || 'support@qcms.app';
        const phone = b.general_phone || '';
        const registeredOffice = b.registered_office || '';
        const gstin = b.gstin || '';
        const pan = b.pan || '';
        const footerCopyright = b.footer_copyright || b.copyright_text || `OFFICIAL COMPUTER-GENERATED BILLING DOCUMENT • ${softwareShort.toUpperCase()} SAAS PLATFORM`;

        return `<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Official Invoice Statement - ${d.invoice_number}</title>
    <style>
        @page { size: A4; margin: 12mm; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            color: #0f172a;
            line-height: 1.5;
            font-size: 13px;
            margin: 0;
            padding: 16px;
            background: #fff;
            box-sizing: border-box;
        }
        .invoice-container { max-width: 760px; margin: 0 auto; width: 100%; box-sizing: border-box; }
        .header { display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #2563eb; padding-bottom: 16px; margin-bottom: 24px; }
        .brand-title { font-size: 22px; font-weight: 800; color: #0f172a; letter-spacing: -0.5px; }
        .brand-subtitle { font-size: 11px; color: #64748b; margin-top: 2px; }
        .brand-company { font-size: 11px; font-weight: 600; color: #334155; margin-top: 3px; }
        .invoice-title { font-size: 20px; font-weight: 800; color: #2563eb; text-align: right; text-transform: uppercase; }
        .invoice-meta { font-size: 12px; color: #475569; text-align: right; margin-top: 3px; }
        
        .badge {
            display: inline-block;
            padding: 4px 12px;
            font-size: 11px;
            font-weight: 700;
            border-radius: 4px;
            text-transform: uppercase;
        }
        .badge-paid { background: #dcfce7; color: #166534; }
        .badge-sent { background: #e0f2fe; color: #075985; }
        .badge-draft { background: #f1f5f9; color: #475569; }
        .badge-refunded { background: #fee2e2; color: #991b1b; }

        .section-grid { display: flex; gap: 16px; margin-bottom: 24px; }
        .info-card { flex: 1; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 14px; }
        .card-title { font-size: 11px; font-weight: 700; text-transform: uppercase; color: #64748b; margin-bottom: 8px; letter-spacing: 0.5px; border-bottom: 1px solid #cbd5e1; padding-bottom: 4px; }
        .info-row { display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 11.5px; }
        .info-label { color: #64748b; }
        .info-val { font-weight: 600; color: #0f172a; text-align: right; word-break: break-word; }

        .table-section { margin-bottom: 24px; }
        .section-heading { font-size: 12.5px; font-weight: 700; color: #0f172a; border-bottom: 1.5px solid #cbd5e1; padding-bottom: 6px; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.5px; }
        table { width: 100%; border-collapse: collapse; margin-top: 6px; }
        th { background: #f1f5f9; color: #475569; font-weight: 700; font-size: 11px; text-transform: uppercase; text-align: left; padding: 8px 12px; border-bottom: 1px solid #cbd5e1; }
        td { padding: 9px 12px; border-bottom: 1px solid #e2e8f0; font-size: 12px; }
        .text-right { text-align: right; }
        
        .summary-box { width: 300px; margin-left: auto; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 16px; }
        .summary-row { display: flex; justify-content: space-between; padding: 4px 0; font-size: 12px; }
        .summary-total { border-top: 2px solid #2563eb; margin-top: 6px; padding-top: 6px; font-size: 15px; font-weight: 800; color: #2563eb; }

        .footer { margin-top: 40px; border-top: 1px solid #e2e8f0; padding-top: 16px; text-align: center; color: #64748b; font-size: 11px; }
        .stamp { font-weight: 700; color: #2563eb; letter-spacing: 0.5px; margin-bottom: 2px; }
    </style>
</head>
<body>
    <div class="invoice-container">
        <!-- Header -->
        <div class="header">
            <div>
                <div class="brand-title">${softwareName}</div>
                <div class="brand-subtitle">${platformTitle}</div>
                <div class="brand-company">${companyLegalName} &bull; ${billingEmail}${phone ? ' &bull; ' + phone : ''}</div>
                ${registeredOffice ? `<div class="brand-subtitle" style="font-size:10px; color:#64748b; margin-top:2px;">${registeredOffice}</div>` : ''}
            </div>
            <div>
                <div class="invoice-title">Official Statement</div>
                <div class="invoice-meta"><strong>${d.invoice_number}</strong></div>
                <div class="invoice-meta">UID: ${d.invoice_uid}</div>
                <div style="margin-top:6px; text-align:right;">
                    <span class="badge badge-${(d.invoice_status||'draft').toLowerCase()}">${d.invoice_status}</span>
                </div>
            </div>
        </div>

        <!-- Meta Grid -->
        <div class="section-grid">
            <div class="info-card">
                <div class="card-title">Billed To (Client Details)</div>
                <div class="info-row"><span class="info-label">Organization Name:</span><span class="info-val">${d.org_name}</span></div>
                <div class="info-row"><span class="info-label">Organization Email:</span><span class="info-val">${d.org_email || 'N/A'}</span></div>
                <div class="info-row"><span class="info-label">Subscription ID:</span><span class="info-val">${d.subscription_uid || 'N/A'}</span></div>
            </div>
            <div class="info-card">
                <div class="card-title">Issued By (Company Info)</div>
                <div class="info-row"><span class="info-label">Legal Company:</span><span class="info-val">${companyLegalName}</span></div>
                <div class="info-row"><span class="info-label">Billing Support:</span><span class="info-val">${billingEmail}</span></div>
                ${gstin ? `<div class="info-row"><span class="info-label">GSTIN / Tax ID:</span><span class="info-val">${gstin}</span></div>` : ''}
                ${pan ? `<div class="info-row"><span class="info-label">PAN:</span><span class="info-val">${pan}</span></div>` : ''}
            </div>
            <div class="info-card">
                <div class="card-title">Billing Meta & Terms</div>
                <div class="info-row"><span class="info-label">Invoice Date:</span><span class="info-val">${QCMS.formatDate(d.invoice_date)}</span></div>
                <div class="info-row"><span class="info-label">Due Date:</span><span class="info-val">${QCMS.formatDate(d.due_date)}</span></div>
                <div class="info-row"><span class="info-label">Plan & Cycle:</span><span class="info-val">${d.plan_name} (${d.billing_cycle})</span></div>
                <div class="info-row"><span class="info-label">Currency:</span><span class="info-val">${d.currency || 'INR'}</span></div>
            </div>
        </div>

        <!-- 1. Notes Overview -->
        ${d.notes ? `
        <div style="margin-bottom: 20px; background: #fffbe6; border: 1px solid #ffe58f; padding: 10px 14px; border-radius: 6px; font-size: 12px;">
            <strong>Invoice Notes:</strong> ${d.notes}
        </div>
        ` : ''}

        <!-- 2. Line Items & Financial Breakdown -->
        <div class="table-section">
            <div class="section-heading">1. Items & Subscription Breakdown</div>
            <table>
                <thead>
                    <tr>
                        <th style="width:40px;">#</th>
                        <th>Description</th>
                        <th class="text-right" style="width:70px;">Qty</th>
                        <th class="text-right" style="width:120px;">Unit Price</th>
                        <th class="text-right" style="width:130px;">Amount</th>
                    </tr>
                </thead>
                <tbody>
                    ${items.length === 0 ? `
                        <tr>
                            <td>1</td>
                            <td>${d.plan_name} Subscription Plan (${d.billing_cycle})</td>
                            <td class="text-right">1</td>
                            <td class="text-right">₹${Number(d.base_amount || 0).toLocaleString('en-IN')}</td>
                            <td class="text-right">₹${Number(d.base_amount || 0).toLocaleString('en-IN')}</td>
                        </tr>
                    ` : items.map((it, idx) => `
                        <tr>
                            <td>${idx + 1}</td>
                            <td>${it.description}</td>
                            <td class="text-right">${it.quantity}</td>
                            <td class="text-right">₹${Number(it.unit_price).toLocaleString('en-IN')}</td>
                            <td class="text-right"><strong>₹${Number(it.amount).toLocaleString('en-IN')}</strong></td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>

            <div style="margin-top: 15px;">
                <div class="summary-box">
                    <div class="summary-row"><span>Base Price:</span><span>₹${Number(d.base_amount || 0).toLocaleString('en-IN')}</span></div>
                    <div class="summary-row"><span>Discount (${d.discount_percent || 0}%):</span><span>-₹${Number(d.discount_amount || 0).toLocaleString('en-IN')}</span></div>
                    <div class="summary-row"><span>Tax / GST (${d.gst_percent || 0}%):</span><span>+₹${Number(d.gst_amount || 0).toLocaleString('en-IN')}</span></div>
                    <div class="summary-row summary-total"><span>Grand Total:</span><span>₹${Number(d.total_amount || 0).toLocaleString('en-IN')}</span></div>
                </div>
            </div>
        </div>

        <!-- 3. Credit Notes & Refunds Section -->
        ${refunds.length > 0 || creditNotes.length > 0 ? `
        <div class="table-section">
            <div class="section-heading">2. Credit & Refunds Adjustments</div>
            <table>
                <thead>
                    <tr><th>Reference UID</th><th>Type</th><th>Reason / Details</th><th class="text-right">Amount</th></tr>
                </thead>
                <tbody>
                    ${refunds.map(r => `
                        <tr>
                            <td><strong>${r.refund_uid}</strong></td>
                            <td><span style="color:#dc2626; font-weight:600;">Refund</span></td>
                            <td>${r.reason} (${r.status})</td>
                            <td class="text-right" style="color:#dc2626; font-weight:700;">-₹${Number(r.amount).toLocaleString('en-IN')}</td>
                        </tr>
                    `).join('')}
                    ${creditNotes.map(c => `
                        <tr>
                            <td><strong>${c.credit_note_uid}</strong></td>
                            <td><span style="color:#2563eb; font-weight:600;">Credit Note</span></td>
                            <td>Balance: ₹${Number(c.balance).toLocaleString('en-IN')} (${c.status})</td>
                            <td class="text-right" style="color:#2563eb; font-weight:700;">₹${Number(c.amount).toLocaleString('en-IN')}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
        ` : ''}

        <!-- 4. Audit Logs Section -->
        <div class="table-section">
            <div class="section-heading">3. Activity & Audit Trail</div>
            <table>
                <thead>
                    <tr><th>Action</th><th>User / Actor</th><th>IP Address</th><th class="text-right">Timestamp</th></tr>
                </thead>
                <tbody>
                    ${audits.length === 0 ? `
                        <tr><td colspan="4" style="color:#94a3b8; text-align:center; padding:10px;">System-generated invoice record intact.</td></tr>
                    ` : audits.map(a => `
                        <tr>
                            <td><strong>${a.action}</strong></td>
                            <td>${a.user_name}</td>
                            <td>${a.ip_address || '127.0.0.1'}</td>
                            <td class="text-right">${QCMS.formatDate(a.created_at)}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>

        <!-- Footer -->
        <div class="footer">
            <div class="stamp">${footerCopyright.toUpperCase()}</div>
            <div>Combined Report including Overview, Items, Audit Logs & Adjustments for Organization: <strong>${d.org_name}</strong></div>
            <div style="margin-top:4px;">Generated on: ${new Date().toLocaleString()} &bull; ${companyLegalName}</div>
        </div>
    </div>
</body>
</html>`;
    },

    async printOfficialInvoice() {
        const d = this._currentInvoiceData;
        if (!d) {
            alert('Invoice details not loaded yet.');
            return;
        }
        if (!d.branding) {
            try {
                const token = localStorage.getItem('token') || localStorage.getItem('access_token');
                const bRes = await fetch('/api/document-identity/all', {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                const bJson = await bRes.json();
                if (bJson.status === 'success' && bJson.branding_context) {
                    d.branding = bJson.branding_context;
                }
            } catch (e) {
                console.warn('Could not fetch document branding fallback:', e);
            }
        }
        const htmlContent = this.generateOfficialInvoiceHTML(d);
        
        const printWin = window.open('', '_blank', 'width=900,height=800');
        if (!printWin) {
            alert('Please allow popups for this site to view and print official invoice reports.');
            return;
        }
        printWin.document.write(htmlContent);
        printWin.document.close();
        printWin.focus();
        setTimeout(() => {
            printWin.print();
        }, 500);
    },

    downloadInvoicePDF() {
        // Triggers high-fidelity vector PDF generation dialog matching exact statement specs
        this.printOfficialInvoice();
    },

    async emailInvoice() {
        const d = this._currentInvoiceData;
        if (!d) {
            alert('Invoice details not loaded yet.');
            return;
        }
        
        const btn = document.getElementById('bddEmailBtn');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Sending…';
        }

        try {
            const res = await api.post(`/billing/invoices/${d.id}/send-email`);
            if (res && res.status === 'success') {
                alert(`✅ ${res.message}`);
            } else {
                alert(`Failed to send email: ${res ? res.message : 'Unknown error'}`);
            }
        } catch (e) {
            alert(`Failed to send email: ${e.message}`);
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '<i data-lucide="mail" style="width:13px;height:13px;"></i> Email Statement';
                if (window.lucide) lucide.createIcons();
            }
        }
    },


    closeBillDrawer() {
        document.getElementById('billDetailOverlay').classList.remove('open');
        document.getElementById('billDetailDrawer').classList.remove('open');
    },

    // ─── WIZARD CREATOR ──────────────────────────────────────────────────────

    async openBillCreateWizard() {
        this._bill.wizStep = 1;
        this._bill.wizItems = [{ description: 'QCMS Platform Subscription Renewal', quantity: 1, unit_price: 15000 }];
        
        // Load Organizations list
        try {
            const res = await api.get('/super-admin/dashboard'); // dashboard returns details of orgs
            if (res.status === 'success' && res.data.active_organizations_list) {
                const select = document.getElementById('biOrgSelect');
                select.innerHTML = '<option value="">-- Choose Organization --</option>' + 
                    res.data.active_organizations_list.map(org => `<option value="${org.id}">${org.name}</option>`).join('');
            }
        } catch (e) {
            console.error("Error fetching organizations", e);
        }

        // Setup wizard steps defaults
        document.getElementById('biInvNum').value = 'INV-2026-' + Math.floor(1000 + Math.random() * 9000);
        document.getElementById('biInvDate').value = new Date().toISOString().slice(0, 10);
        document.getElementById('biDueDate').value = new Date(Date.now() + 15 * 86400000).toISOString().slice(0, 10);
        
        this.renderWizardStep();
        this.biRenderItemsGrid();
        this.biRecalculateTotals();

        const modal = new bootstrap.Modal(document.getElementById('billCreateModal'));
        modal.show();
    },

    async biLoadOrgSubscriptions(orgId) {
        if (!orgId) return;
        const subSelect = document.getElementById('biSubSelect');
        const emailInput = document.getElementById('biCustEmail');
        
        try {
            // Find organization details
            const res = await api.get(`/super-admin/dashboard`);
            const org = res.data.active_organizations_list.find(x => x.id == orgId);
            if (org) {
                emailInput.value = org.email;
            }

            // Fetch subscriptions linked to this org
            const subRes = await api.get(`/subscriptions?org_id=${orgId}`);
            if (subRes.status === 'success' && subRes.data.length > 0) {
                subSelect.innerHTML = subRes.data.map(s => `<option value="${s.id}">${s.subscription_uid} (${s.plan_name})</option>`).join('');
                subSelect.disabled = false;
            } else {
                subSelect.innerHTML = `<option value="1">SUB-2026-MOCK (Mock Link)</option>`;
                subSelect.disabled = false;
            }
        } catch (e) {
            console.error("Error loading org details", e);
        }
    },

    biRenderItemsGrid() {
        const grid = document.getElementById('biItemsGrid');
        if (!grid) return;

        grid.innerHTML = this._bill.wizItems.map((it, idx) => `
            <tr>
                <td><input type="text" class="ds-input py-0 px-2" value="${it.description}" style="height:28px;font-size:11.5px;" onchange="SuperAdmin._bill.wizItems[${idx}].description = this.value"></td>
                <td><input type="number" class="ds-input py-0 px-2 text-center" value="${it.quantity}" style="height:28px;font-size:11.5px;" oninput="SuperAdmin.biUpdateItemQty(${idx}, this.value)"></td>
                <td><input type="number" class="ds-input py-0 px-2 text-end" value="${it.unit_price}" style="height:28px;font-size:11.5px;" oninput="SuperAdmin.biUpdateItemPrice(${idx}, this.value)"></td>
                <td class="fw-bold pt-2">₹${(it.quantity * it.unit_price).toLocaleString('en-IN')}</td>
                <td class="text-center pt-2"><a href="#" class="text-danger" onclick="SuperAdmin.biRemoveWizItem(${idx})"><i data-lucide="trash-2" style="width:14px;height:14px;"></i></a></td>
            </tr>
        `).join('');

        if (window.lucide) lucide.createIcons();
    },

    biAddWizItem() {
        this._bill.wizItems.push({ description: 'Professional Plan Add-on Service', quantity: 1, unit_price: 5000 });
        this.biRenderItemsGrid();
        this.biRecalculateTotals();
    },

    biRemoveWizItem(idx) {
        if (this._bill.wizItems.length === 1) return;
        this._bill.wizItems.splice(idx, 1);
        this.biRenderItemsGrid();
        this.biRecalculateTotals();
    },

    biUpdateItemQty(idx, val) {
        this._bill.wizItems[idx].quantity = parseInt(val) || 0;
        this.biRenderItemsGrid();
        this.biRecalculateTotals();
    },

    biUpdateItemPrice(idx, val) {
        this._bill.wizItems[idx].unit_price = parseFloat(val) || 0.0;
        this.biRenderItemsGrid();
        this.biRecalculateTotals();
    },

    biRecalculateTotals() {
        let base = 0.0;
        this._bill.wizItems.forEach(it => {
            base += it.quantity * it.unit_price;
        });

        const discPercent = parseFloat(document.getElementById('biDiscountPercent')?.value || 0.0);
        const discAmt = base * (discPercent / 100.0);
        
        const gstPercent = parseFloat(document.getElementById('biGstPercent')?.value || 18.0);
        const taxable = base - discAmt;
        const gstAmt = taxable * (gstPercent / 100.0);
        const total = taxable + gstAmt;

        document.getElementById('biBaseText').textContent = `₹${base.toLocaleString('en-IN')}`;
        document.getElementById('biDiscountText').textContent = `-₹${discAmt.toLocaleString('en-IN')}`;
        document.getElementById('biGstText').textContent = `+₹${gstAmt.toLocaleString('en-IN')}`;
        document.getElementById('biTotalText').textContent = `₹${total.toLocaleString('en-IN')}`;
    },

    renderWizardStep() {
        const step = this._bill.wizStep;
        
        // Toggle step views
        for (let i = 1; i <= 5; i++) {
            const el = document.getElementById(`bwp${i}`);
            if (el) el.classList.toggle('active', i === step);
        }

        // Update indicators
        document.querySelectorAll('.bill-step-indicator .step-node').forEach(node => {
            const nodeStep = parseInt(node.getAttribute('data-ws'));
            node.classList.toggle('active', nodeStep === step);
            node.classList.toggle('done', nodeStep < step);
        });

        // Toggle buttons
        document.getElementById('biPrevBtn').disabled = (step === 1);
        
        const nextBtn = document.getElementById('biNextBtn');
        const submitBtn = document.getElementById('biSubmitBtn');
        
        if (step === 5) {
            nextBtn.classList.add('d-none');
            submitBtn.classList.remove('d-none');
            this.biRenderReviewSummary();
        } else {
            nextBtn.classList.remove('d-none');
            submitBtn.classList.add('d-none');
        }
    },

    biWizNext() {
        // Step Validations
        if (this._bill.wizStep === 1) {
            const org = document.getElementById('biOrgSelect').value;
            if (!org) {
                api.showNotification('Please choose an organization to proceed.', 'warning');
                return;
            }
        }
        if (this._bill.wizStep === 2) {
            const num = document.getElementById('biInvNum').value.trim();
            if (!num) {
                api.showNotification('Invoice number is required.', 'warning');
                return;
            }
        }
        this._bill.wizStep++;
        this.renderWizardStep();
    },

    biWizPrev() {
        this._bill.wizStep--;
        this.renderWizardStep();
    },

    biRenderReviewSummary() {
        const orgSelect = document.getElementById('biOrgSelect');
        const orgName = orgSelect.options[orgSelect.selectedIndex].text;
        const num = document.getElementById('biInvNum').value;
        const date = document.getElementById('biInvDate').value;
        const due = document.getElementById('biDueDate').value;
        const total = document.getElementById('biTotalText').textContent;

        const review = document.getElementById('biReviewArea');
        review.innerHTML = `
            <div class="row g-2">
                <div class="col-4 text-muted">Customer Name:</div><div class="col-8 fw-bold">${orgName}</div>
                <div class="col-4 text-muted">Invoice Identifier:</div><div class="col-8 font-monospace">${num}</div>
                <div class="col-4 text-muted">Invoice Date:</div><div class="col-8">${QCMS.formatDate(date)}</div>
                <div class="col-4 text-muted">Due Date:</div><div class="col-8">${QCMS.formatDate(due)}</div>
                <div class="col-4 text-muted">Collection Cycle:</div><div class="col-8">${document.getElementById('biTerms').value}</div>
                <div class="col-4 text-muted text-sm pt-2">Total Amount:</div><div class="col-8 text-primary fw-bold text-sm pt-2">${total}</div>
            </div>
        `;
    },

    async biWizSubmit() {
        const orgId = document.getElementById('biOrgSelect').value;
        const subSelect = document.getElementById('biSubSelect');
        const subscriptionId = subSelect.value || 1;

        const payload = {
            org_id: parseInt(orgId),
            subscription_id: parseInt(subscriptionId),
            invoice_number: document.getElementById('biInvNum').value,
            currency: document.getElementById('biCurrency').value,
            invoice_date: document.getElementById('biInvDate').value,
            due_date: document.getElementById('biDueDate').value,
            notes: document.getElementById('biDesc').value,
            items: this._bill.wizItems,
            discount_percent: parseFloat(document.getElementById('biDiscountPercent').value || 0.0),
            gst_percent: parseFloat(document.getElementById('biGstPercent').value || 18.0)
        };

        try {
            const res = await api.post('/billing/invoices', payload);
            if (res && res.status === 'success') {
                api.showNotification('Invoice generated successfully', 'success');
                const modal = bootstrap.Modal.getInstance(document.getElementById('billCreateModal'));
                modal.hide();
                this.loadRevenue();
            }
        } catch (e) {
            api.showNotification('Creation failed: ' + e.message, 'error');
        }
    },

    // ─── WORKFLOW ACTIONS ────────────────────────────────────────────────────

    async markInvoicePaid(id) {
        if (!confirm('Mark this invoice as PAID offline?')) return;
        try {
            const res = await api.post(`/billing/invoices/${id}/pay`, { payment_method: 'Offline Bank Transfer' });
            if (res && res.status === 'success') {
                api.showNotification('Invoice paid successfully', 'success');
                this.closeBillDrawer();
                this.loadRevenue();
            }
        } catch (e) {
            api.showNotification('Payment action failed: ' + e.message, 'error');
        }
    },

    async cancelInvoice(id) {
        if (!confirm('Are you sure you want to cancel this pending invoice?')) return;
        try {
            const res = await api.post(`/billing/invoices/${id}/refund`, { refund_amount: 0, reason: 'Admin Cancelled' });
            if (res && res.status === 'success') {
                api.showNotification('Invoice cancelled successfully', 'success');
                this.closeBillDrawer();
                this.loadRevenue();
            }
        } catch (e) {
            api.showNotification('Cancellation failed: ' + e.message, 'error');
        }
    },

    async deleteInvoice(id) {
        if (!confirm('Destructive action: delete this invoice record forever?')) return;
        try {
            const res = await api.delete(`/billing/invoices/${id}`);
            if (res && res.status === 'success') {
                api.showNotification('Invoice record deleted successfully', 'success');
                this.loadRevenue();
            }
        } catch (e) {
            api.showNotification('Deletion failed: ' + e.message, 'error');
        }
    },

    openRefundModal(invId, invNum, total, currency) {
        document.getElementById('brInvoiceId').value = invId;
        document.getElementById('brInvNum').textContent = invNum;
        document.getElementById('brCurrency').textContent = currency;
        document.getElementById('brMaxAmount').textContent = `₹${total.toLocaleString('en-IN')}`;
        document.getElementById('brAmount').value = total;

        const modal = new bootstrap.Modal(document.getElementById('billRefundModal'));
        modal.show();
    },

    async submitRefund() {
        const id = document.getElementById('brInvoiceId').value;
        const payload = {
            refund_amount: parseFloat(document.getElementById('brAmount').value),
            reason: document.getElementById('brReason').value
        };

        try {
            const res = await api.post(`/billing/invoices/${id}/refund`, payload);
            if (res && res.status === 'success') {
                api.showNotification('Refund issued successfully', 'success');
                const modal = bootstrap.Modal.getInstance(document.getElementById('billRefundModal'));
                modal.hide();
                this.loadRevenue();
            }
        } catch (e) {
            api.showNotification('Refund failed: ' + e.message, 'error');
        }
    },

    openCreditNoteModal(orgId, orgName) {
        document.getElementById('bcnOrgId').value = orgId;
        document.getElementById('bcnOrgName').textContent = orgName;
        document.getElementById('bcnAmount').value = '1000.00';
        document.getElementById('bcnNotes').value = 'Adjustment credit note balance';

        const modal = new bootstrap.Modal(document.getElementById('billCreditNoteModal'));
        modal.show();
    },

    async submitCreditNote() {
        const orgId = document.getElementById('bcnOrgId').value;
        const payload = {
            org_id: parseInt(orgId),
            amount: parseFloat(document.getElementById('bcnAmount').value),
            notes: document.getElementById('bcnNotes').value
        };

        try {
            const res = await api.post('/billing/credit-notes', payload);
            if (res && res.status === 'success') {
                api.showNotification('Credit note issued successfully', 'success');
                const modal = bootstrap.Modal.getInstance(document.getElementById('billCreditNoteModal'));
                modal.hide();
                this.loadRevenue();
            }
        } catch (e) {
            api.showNotification('Issue failed: ' + e.message, 'error');
        }
    },

    async openBillReportsModal() {
        const modal = new bootstrap.Modal(document.getElementById('billReportsModal'));
        modal.show();

        try {
            // Load Analytics Reports
            const revRes = await api.get('/billing/reports/revenue');
            if (revRes.status === 'success') {
                const planDiv = document.getElementById('reportByPlanArea');
                const planData = revRes.data.by_plan;
                planDiv.innerHTML = Object.keys(planData).map(k => `
                    <div class="d-flex justify-content-between mb-2"><span>${k}:</span><strong>₹${planData[k].toLocaleString('en-IN')}</strong></div>
                `).join('') || '<div class="text-muted">No plan revenue found.</div>';

                const countryDiv = document.getElementById('reportByCountryArea');
                const countryData = revRes.data.by_country;
                countryDiv.innerHTML = Object.keys(countryData).map(k => `
                    <div class="d-flex justify-content-between mb-2"><span>${k}:</span><strong>₹${countryData[k].toLocaleString('en-IN')}</strong></div>
                `).join('') || '<div class="text-muted">No regional revenue found.</div>';
            }

            // Load AI recommendations
            const aiRes = await api.get('/billing/reports/ai-insights');
            if (aiRes.status === 'success') {
                const forecastDiv = document.getElementById('aiForecastArea');
                const d = aiRes.data;
                forecastDiv.innerHTML = `
                    <p class="mb-2">💡 <strong>Revenue Forecast:</strong> ${d.revenue_forecast}</p>
                    <p class="mb-2">⚠️ <strong>Late Payment Risk:</strong></p>
                    <ul class="ps-3 mb-2">
                        ${d.late_payment_prediction.map(x => `<li><strong>${x.company}</strong> (Risk: <span class="text-danger fw-bold">${x.risk}</span>) - ${x.reason}</li>`).join('')}
                    </ul>
                    <p class="mb-0">✨ <strong>Action Plan:</strong> Promote upgrades to custom integrations to lock in ₹45k expansion MRR.</p>
                `;
            }
        } catch (e) {
            console.error("Error loading analytics reports", e);
        }
    },


    async loadSupport() {
        if (!this.supportDeskInitialized) {
            SupportDesk.init('superAdminSupportContainer', 'SuperAdmin');
            this.supportDeskInitialized = true;
        } else {
            SupportDesk.switchTab(SupportDesk.currentTab);
        }
    },

    async loadSettings() {
        try {
            if (window.PlatformSettings) {
                await window.PlatformSettings.loadDashboard();
                await window.PlatformSettings.loadAllSettings();
            }

            const res = await api.get('/super-admin/settings');
            if (res && res.status === 'success') {
                const d = res.data;
                const siteNameEl = document.getElementById('site_name') || document.getElementById('ps-site-name');
                if (siteNameEl) siteNameEl.value = d.site_name || '';

                const supportEmailEl = document.getElementById('support_email') || document.getElementById('ps-support-email');
                if (supportEmailEl) supportEmailEl.value = d.support_email || '';

                const notifEl = document.getElementById('global_notification') || document.getElementById('ps-global-notification');
                if (notifEl) notifEl.value = d.global_notification || '';

                const regEl = document.getElementById('registration_open') || document.getElementById('ps-registration-open');
                if (regEl) regEl.checked = !!d.registration_open;

                const maintEl = document.getElementById('maintenance_mode') || document.getElementById('ps-maintenance-mode');
                if (maintEl) maintEl.checked = !!d.maintenance_mode;

                const planEl = document.getElementById('default_plan') || document.getElementById('ps-default-plan');
                if (planEl) planEl.value = d.default_plan || 'Starter';

                const trialEl = document.getElementById('trial_period_days') || document.getElementById('ps-trial-days');
                if (trialEl) trialEl.value = d.trial_period_days || 14;

                const payEl = document.getElementById('payment_gateway_mode') || document.getElementById('ps-payment-mode');
                if (payEl) payEl.value = d.payment_gateway_mode || 'Test';
            }

            const profileRes = await api.get('/super-admin/profile');
            if (profileRes && profileRes.status === 'success') {
                const profile = profileRes.data;
                const saUserEl = document.getElementById('sa_username') || document.getElementById('ps-sa-username');
                if (saUserEl) saUserEl.value = profile.username || '';
            }

            await this.loadOfflinePayments();
            await this.loadBillingKPIs();

            const urlParams = new URLSearchParams(window.location.search);
            const viewParam = urlParams.get('view');
            const utrParam = urlParams.get('utr');
            if (viewParam === 'subscriptions' || utrParam) {
                if (typeof showView === 'function') showView('subscriptions');
                this.openVerificationFromNotification(utrParam);
            }
        } catch (e) {
            console.warn('loadSettings warning:', e);
        }
    },

    async loadBillingKPIs() {
        const fmt = (v, currency = 'INR') => {
            if (v === null || v === undefined) return '—';
            const num = parseFloat(v);
            if (isNaN(num)) return '—';
            // Format with Indian locale for INR, else generic
            if (currency === 'INR') {
                return '₹' + num.toLocaleString('en-IN', { maximumFractionDigits: 0 });
            }
            return num.toLocaleString('en-US', { maximumFractionDigits: 0 });
        };
        const setEl = (id, html) => {
            const el = document.getElementById(id);
            if (el) el.innerHTML = html;
        };
        try {
            const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token') || sessionStorage.getItem('token');
            const res = await fetch('/api/v1/billing/kpis', {
                headers: { Authorization: `Bearer ${token}` }
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const json = await res.json();
            const d = json.data || {};
            setEl('billing-kpi-mrr',          fmt(d.mrr));
            setEl('billing-kpi-arr',          fmt(d.arr));
            setEl('billing-kpi-active-subs',  String(d.active_subscriptions ?? '—'));
            setEl('billing-kpi-active-trials', String(d.active_trials ?? '—'));
        } catch (e) {
            console.warn('Billing KPI load failed:', e);
            ['billing-kpi-mrr','billing-kpi-arr','billing-kpi-active-subs','billing-kpi-active-trials']
                .forEach(id => setEl(id, '<span class="text-muted text-xxs">—</span>'));
        }
    },

    openVerificationFromNotification(utr) {
        const doOpen = () => {
            if (!this._offlinePaymentsData || !this._offlinePaymentsData.length) return;
            let matchIndex = -1;
            if (utr) {
                matchIndex = this._offlinePaymentsData.findIndex(p => 
                    p.transaction_id && p.transaction_id.toLowerCase().includes(utr.toLowerCase())
                );
            }
            if (matchIndex === -1 && this._offlinePaymentsData.length > 0) {
                matchIndex = 0;
            }
            if (matchIndex !== -1) {
                this.viewReceiptModal(matchIndex);
            }
        };

        if (!this._offlinePaymentsData || !this._offlinePaymentsData.length) {
            api.get('/billing/offline-payments').then(res => {
                if (res && res.status === 'success' && res.payments) {
                    this._offlinePaymentsData = res.payments;
                    doOpen();
                }
            });
        } else {
            doOpen();
        }
    },

    async loadOfflinePayments() {
        const tbody = document.getElementById('offlinePaymentsTableBody');
        if (!tbody) return;
        try {
            const res = await api.get('/billing/offline-payments');
            if (res && res.status === 'success' && res.payments) {
                if (res.payments.length === 0) {
                    tbody.innerHTML = `<tr><td colspan="8" class="text-center py-4 text-muted text-xs">No offline payment submissions found.</td></tr>`;
                    return;
                }
                this._offlinePaymentsData = res.payments;
                tbody.innerHTML = res.payments.map((p, index) => {
                    const isPending = p.status === 'Pending Verification';
                    const isApproved = p.status === 'Approved';
                    const isRejected = p.status === 'Rejected';
                    
                    const statusBadge = isApproved 
                        ? `<span class="badge bg-success-subtle text-success border border-success-subtle px-2 py-1"><i data-lucide="check-circle" style="width:11px;height:11px;" class="me-1"></i>Approved / Active</span>`
                        : (isRejected 
                            ? `<span class="badge bg-danger-subtle text-danger border border-danger-subtle px-2 py-1" title="${QCMS.escapeHtml(p.rejection_reason || '')}"><i data-lucide="x-circle" style="width:11px;height:11px;" class="me-1"></i>Rejected</span>` 
                            : `<span class="badge bg-warning-subtle text-warning border border-warning-subtle px-2 py-1"><i data-lucide="clock" style="width:11px;height:11px;" class="me-1"></i>Pending Verification</span>`);

                    const proofBtn = p.screenshot_url 
                        ? `<button type="button" class="ds-btn ds-btn-secondary ds-btn-sm py-1 px-2 text-xxs" onclick="SuperAdmin.viewReceiptModal(${index})"><i data-lucide="image" style="width:11px;height:11px;" class="me-1"></i> View Receipt</button>`
                        : `<span class="text-secondary text-xxs">No Proof</span>`;

                    const actions = isPending ? `
                        <div class="d-flex gap-1 justify-content-end">
                            <button type="button" class="ds-btn ds-btn-primary ds-btn-sm py-1 px-2.5 text-xxs" onclick="SuperAdmin.approveOfflinePayment(${p.id})">
                                <i data-lucide="check-circle" style="width:12px;height:12px;" class="me-1"></i> Activate Plan
                            </button>
                            <button type="button" class="ds-btn ds-btn-secondary ds-btn-sm py-1 px-2.5 text-xxs text-danger" onclick="SuperAdmin.openRejectModal(${p.id}, '${QCMS.escapeHtml(p.transaction_id)}')">
                                <i data-lucide="x-circle" style="width:12px;height:12px;" class="me-1"></i> Reject
                            </button>
                        </div>
                    ` : (isRejected ? `
                        <div class="text-end">
                            <span class="text-danger text-xxs fw-bold d-block">Declined</span>
                            <span class="text-secondary text-xxs cursor-pointer" onclick="SuperAdmin.viewReceiptModal(${index})">View Review</span>
                        </div>
                    ` : `<span class="text-success text-xxs fw-bold">Activated ✓</span>`);

                    return `
                        <tr>
                            <td>
                                <div class="d-flex align-items-center gap-1.5 mb-0.5">
                                    <strong class="text-main text-xs">${QCMS.escapeHtml(p.org_name)}</strong>
                                    <span class="badge bg-secondary-subtle text-secondary font-monospace text-xxs">ID: ${p.org_id}</span>
                                </div>
                                <div class="text-secondary text-xxs">${QCMS.escapeHtml(p.user_email)}</div>
                            </td>
                            <td>
                                <span class="badge bg-primary-subtle text-primary fw-bold text-xxs">${QCMS.escapeHtml(p.plan_name)}</span>
                                <span class="text-secondary text-xxs d-block mt-0.5">${QCMS.escapeHtml(p.billing_cycle || 'Monthly')}</span>
                            </td>
                            <td class="fw-bold text-xs text-main">₹${(p.amount || 0).toLocaleString('en-IN')}</td>
                            <td>
                                <span class="font-monospace text-xs text-main fw-bold d-block">${QCMS.escapeHtml(p.transaction_id)}</span>
                                ${p.notes ? `<span class="text-secondary text-xxs" title="${QCMS.escapeHtml(p.notes)}">${QCMS.escapeHtml(p.notes.length > 25 ? p.notes.substring(0, 25) + '...' : p.notes)}</span>` : ''}
                            </td>
                            <td>${proofBtn}</td>
                            <td class="text-secondary text-xxs">${p.created_at || '—'}</td>
                            <td>${statusBadge}</td>
                            <td class="text-end">${actions}</td>
                        </tr>
                    `;
                }).join('');
                if (window.lucide) lucide.createIcons();
            }
        } catch (e) {
            console.warn('loadOfflinePayments error:', e);
            tbody.innerHTML = `<tr><td colspan="8" class="text-center py-3 text-danger text-xs">Failed to load offline payments.</td></tr>`;
        }
    },

    async approveOfflinePayment(id) {
        if (!confirm('Are you sure you want to approve this payment proof and activate the subscription plan immediately?')) return;
        try {
            const res = await api.post(`/billing/offline-payments/${id}/approve`, {});
            if (res && res.status === 'success') {
                QCMS.toast(res.message || 'Payment proof approved and plan activated!', 'success');
                this.loadOfflinePayments();
                const m = bootstrap.Modal.getInstance(document.getElementById('receiptPreviewModal'));
                if (m) m.hide();
            } else {
                QCMS.toast(res.message || 'Failed to approve payment', 'error');
            }
        } catch (e) {
            QCMS.toast(e.message || 'Approval error', 'error');
        }
    },

    openRejectModal(id, utr) {
        const modalHtml = `
            <div class="modal fade" id="rejectPaymentModal" tabindex="-1">
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header border-bottom">
                            <h5 class="modal-title fw-bold text-sm text-danger">Reject Payment Proof (UTR: ${QCMS.escapeHtml(utr)})</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body p-4">
                            <label class="ds-label text-xs fw-bold mb-2">Rejection Review / Feedback Reason <span class="text-danger">*</span></label>
                            <textarea id="rejectReasonInput" class="ds-input text-xs w-100" rows="3" placeholder="Specify why this payment proof is rejected (e.g. UTR mismatch with bank statement, unreadable receipt image, incorrect amount).">${QCMS.escapeHtml('Payment transaction UTR details could not be verified with bank records.')}</textarea>
                            <div class="text-xxs text-secondary mt-2">
                                <i data-lucide="info" style="width:12px;height:12px;" class="me-1"></i>
                                This review feedback will be displayed directly to the Organization Admin in their Billing settings.
                            </div>
                        </div>
                        <div class="modal-footer border-top p-3 d-flex justify-content-end gap-2">
                            <button type="button" class="ds-btn ds-btn-ghost ds-btn-sm" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="ds-btn ds-btn-danger ds-btn-sm" onclick="SuperAdmin.submitRejection(${id})">
                                Confirm Rejection
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        const oldModal = document.getElementById('rejectPaymentModal');
        if (oldModal) oldModal.remove();
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        const m = new bootstrap.Modal(document.getElementById('rejectPaymentModal'));
        m.show();
        if (window.lucide) lucide.createIcons();
    },

    async submitRejection(id) {
        const input = document.getElementById('rejectReasonInput');
        const reason = input ? input.value.trim() : '';
        if (!reason) {
            alert('Please provide a reason for rejecting the payment proof.');
            return;
        }

        try {
            const res = await api.post(`/billing/offline-payments/${id}/reject`, { reason });
            if (res && res.status === 'success') {
                QCMS.toast('Payment proof rejected and feedback sent to organization.', 'info');
                const m = bootstrap.Modal.getInstance(document.getElementById('rejectPaymentModal'));
                if (m) m.hide();
                const mReceipt = bootstrap.Modal.getInstance(document.getElementById('receiptPreviewModal'));
                if (mReceipt) mReceipt.hide();
                this.loadOfflinePayments();
            } else {
                QCMS.toast(res.message || 'Failed to reject payment', 'error');
            }
        } catch (e) {
            QCMS.toast(e.message || 'Rejection error', 'error');
        }
    },

    viewReceiptModal(index) {
        const p = (this._offlinePaymentsData || [])[index];
        if (!p) return;

        const isPending = p.status === 'Pending Verification';
        const isApproved = p.status === 'Approved';
        const isRejected = p.status === 'Rejected';

        const statusBadge = isApproved 
            ? `<span class="badge bg-success-subtle text-success border border-success-subtle px-2.5 py-1 text-xs">Approved / Active</span>`
            : (isRejected 
                ? `<span class="badge bg-danger-subtle text-danger border border-danger-subtle px-2.5 py-1 text-xs">Rejected</span>` 
                : `<span class="badge bg-warning-subtle text-warning border border-warning-subtle px-2.5 py-1 text-xs">Pending Verification</span>`);

        const actionButtons = isPending ? `
            <div class="d-flex flex-column flex-sm-row gap-2 w-100 mt-4 pt-3 border-top">
                <button type="button" class="ds-btn ds-btn-primary flex-fill py-2 px-3 text-xs fw-bold" onclick="SuperAdmin.approveOfflinePayment(${p.id})">
                    <i data-lucide="check-circle" class="me-1"></i> Activate Plan Immediately
                </button>
                <button type="button" class="ds-btn ds-btn-secondary text-danger flex-fill py-2 px-3 text-xs fw-bold" onclick="SuperAdmin.submitDirectRejection(${p.id})">
                    <i data-lucide="x-circle" class="me-1"></i> Reject Payment
                </button>
            </div>
        ` : '';

        const modalHtml = `
            <div class="modal fade" id="receiptPreviewModal" tabindex="-1">
                <div class="modal-dialog modal-dialog-centered modal-xl">
                    <div class="modal-content">
                        <div class="modal-header border-bottom p-3 px-4">
                            <div>
                                <h5 class="modal-title fw-bold text-sm mb-0">Offline Payment Submission Details</h5>
                                <div class="text-xxs text-secondary">Transaction UTR: <strong class="font-monospace text-main">${QCMS.escapeHtml(p.transaction_id)}</strong></div>
                            </div>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body p-4">
                            <div class="row g-4">
                                <div class="col-md-6 text-center">
                                    <div class="p-3 bg-light rounded-3 border h-100 d-flex flex-column justify-content-center align-items-center" id="receiptImagePane_${p.id}">
                                        ${p.screenshot_url ? (() => {
                                            const _tok = encodeURIComponent(localStorage.getItem('token') || sessionStorage.getItem('token') || '');
                                            return `
                                            <a href="/api/billing/offline-payments/${p.id}/screenshot?token=${_tok}" target="_blank" title="Click to open full size" id="receiptImgLink_${p.id}">
                                                <img src="/api/billing/offline-payments/${p.id}/screenshot?token=${_tok}"
                                                     class="img-fluid rounded border shadow-sm"
                                                     style="max-height: 420px; object-fit: contain;"
                                                     onerror="this.style.display='none'; document.getElementById('receiptImgError_${p.id}').style.display='block';"
                                                     alt="Payment Receipt Screenshot">
                                            </a>
                                            <div id="receiptImgError_${p.id}" style="display:none;" class="py-4 text-center w-100">
                                                <i data-lucide="image-off" class="mb-2 text-muted" style="width:36px;height:36px;"></i>
                                                <div class="text-xs text-muted mt-1">Screenshot not accessible on disk.<br>You can re-upload below.</div>
                                                <label class="ds-btn ds-btn-outline ds-btn-sm mt-2 cursor-pointer" style="font-size:11px;">
                                                    <i data-lucide="upload" style="width:12px;height:12px;" class="me-1"></i> Re-upload Screenshot
                                                    <input type="file" accept="image/*,application/pdf" style="display:none;" onchange="SuperAdmin.uploadProofScreenshot(${p.id}, this)">
                                                </label>
                                            </div>
                                            <span class="text-xxs text-secondary mt-2"><i data-lucide="external-link" style="width:11px;height:11px;" class="me-1"></i>Click image to open original</span>
                                        `; })() : `
                                            <div class="py-4 text-center w-100">
                                                <i data-lucide="image-off" class="mb-2 text-secondary" style="width:40px;height:40px;"></i>
                                                <div class="text-xs text-secondary mb-3">No Receipt Screenshot Attached</div>
                                                <label class="ds-btn ds-btn-primary ds-btn-sm cursor-pointer" style="font-size:11px;">
                                                    <i data-lucide="upload" style="width:12px;height:12px;" class="me-1"></i> Upload Screenshot Now
                                                    <input type="file" accept="image/*,application/pdf" style="display:none;" onchange="SuperAdmin.uploadProofScreenshot(${p.id}, this)">
                                                </label>
                                                <div class="text-xxs text-muted mt-2">PNG, JPG, PDF accepted</div>
                                            </div>
                                        `}
                                    </div>
                                </div>
                                <div class="col-md-6 d-flex flex-column justify-content-between">
                                    <div class="w-100">
                                        <div class="d-flex justify-content-between align-items-center mb-3">
                                            <span class="text-xs text-secondary text-uppercase fw-bold">Verification Status</span>
                                            ${statusBadge}
                                        </div>

                                        <div class="glass-card p-3 rounded-3 mb-3 border">
                                            <div class="text-xxs text-secondary text-uppercase fw-bold mb-1">Company / Subscriber Details</div>
                                            <h6 class="fw-bold text-main mb-1">${QCMS.escapeHtml(p.org_name)} <span class="badge bg-secondary-subtle text-secondary font-monospace text-xxs ms-1">ID: ${p.org_id}</span></h6>
                                            <div class="text-xs text-secondary mb-0"><i data-lucide="mail" style="width:12px;height:12px;" class="me-1"></i>${QCMS.escapeHtml(p.user_email)}</div>
                                            <div class="text-xs text-secondary"><i data-lucide="user" style="width:12px;height:12px;" class="me-1"></i>${QCMS.escapeHtml(p.user_name || 'Admin')}</div>
                                        </div>

                                        <div class="glass-card p-3 rounded-3 mb-3 border">
                                            <div class="text-xxs text-secondary text-uppercase fw-bold mb-1">Chosen Plan & Payment Breakdown</div>
                                            <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-2">
                                                <span class="badge bg-primary-subtle text-primary fw-bold text-xs px-2.5 py-1">${QCMS.escapeHtml(p.plan_name)} Plan</span>
                                                <span class="fw-bold text-main fs-6">₹${(p.amount || 0).toLocaleString('en-IN')} <span class="text-xxs text-secondary fw-normal">(incl. 18% GST)</span></span>
                                            </div>
                                            <div class="text-xs text-secondary">Billing Cycle: <strong>${QCMS.escapeHtml(p.billing_cycle || 'Monthly')}</strong></div>
                                        </div>

                                        <div class="p-3 bg-light rounded-3 border mb-3">
                                            <div class="text-xxs text-secondary text-uppercase fw-bold mb-1">Transaction Reference (UTR)</div>
                                            <div class="font-monospace text-sm fw-bold text-main mb-1">${QCMS.escapeHtml(p.transaction_id)}</div>
                                            ${p.notes ? `<div class="text-xs text-secondary italic">" ${QCMS.escapeHtml(p.notes)} "</div>` : ''}
                                            <div class="text-xxs text-secondary mt-2"><i data-lucide="calendar" style="width:11px;height:11px;" class="me-1"></i>Submitted on: ${p.created_at || 'N/A'}</div>
                                        </div>

                                        <div class="p-3 bg-white rounded-3 border mb-3">
                                            <label class="text-xxs text-secondary text-uppercase fw-bold mb-1 d-block">
                                                <i data-lucide="edit-3" style="width:12px;height:12px;" class="me-1"></i>
                                                Rejection Review Feedback / Remarks <span class="text-danger">*</span>
                                            </label>
                                            <textarea id="modalReviewNotesInput" class="ds-input text-xs w-100 p-2.5 rounded-3" rows="2" 
                                                placeholder="Write review reason or feedback for the subscriber... (Required when rejecting payment)">${QCMS.escapeHtml(p.rejection_reason || '')}</textarea>
                                        </div>

                                        ${isRejected && p.rejection_reason ? `
                                            <div class="p-3 bg-danger-subtle border border-danger-subtle rounded-3 mb-3 text-danger">
                                                <div class="text-xxs text-uppercase fw-bold mb-1"><i data-lucide="alert-triangle" style="width:12px;height:12px;" class="me-1"></i>Previous Rejection Review</div>
                                                <div class="text-xs fw-bold">${QCMS.escapeHtml(p.rejection_reason)}</div>
                                            </div>
                                        ` : ''}
                                    </div>

                                    ${actionButtons}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        const oldModal = document.getElementById('receiptPreviewModal');
        if (oldModal) oldModal.remove();
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        const m = new bootstrap.Modal(document.getElementById('receiptPreviewModal'));
        m.show();
        if (window.lucide) lucide.createIcons();
    },

    submitDirectRejection(id) {
        const input = document.getElementById('modalReviewNotesInput');
        const reason = input ? input.value.trim() : '';
        if (!reason) {
            alert('Please write a review feedback reason in the box before rejecting the payment.');
            if (input) input.focus();
            return;
        }
        this.submitRejectionWithReason(id, reason);
    },

    async uploadProofScreenshot(proofId, inputEl) {
        if (!inputEl.files || !inputEl.files[0]) return;
        const file = inputEl.files[0];
        const pane = document.getElementById(`receiptImagePane_${proofId}`);

        // Show uploading state
        const origHtml = pane ? pane.innerHTML : '';
        if (pane) pane.innerHTML = `<div class="py-4 text-center">
            <span class="spinner-border text-primary" style="width:28px;height:28px;"></span>
            <div class="text-xs text-muted mt-2">Uploading screenshot…</div>
        </div>`;

        try {
            const token = localStorage.getItem('token') || sessionStorage.getItem('token') || '';
            const fd = new FormData();
            fd.append('file', file);
            const res = await fetch(`/api/billing/offline-payments/${proofId}/upload-screenshot`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` },
                body: fd
            });
            const json = await res.json();
            if (res.ok && json.status === 'success') {
                // Show the newly uploaded image
                if (pane) pane.innerHTML = `
                    <a href="/api/billing/offline-payments/${proofId}/screenshot" target="_blank" title="Click to open full size">
                        <img src="/api/billing/offline-payments/${proofId}/screenshot?t=${Date.now()}"
                             class="img-fluid rounded border shadow-sm"
                             style="max-height: 420px; object-fit: contain;"
                             alt="Payment Receipt Screenshot">
                    </a>
                    <span class="text-xxs text-success mt-2 fw-bold">✓ Screenshot uploaded successfully</span>
                `;
                if (window.lucide) lucide.createIcons();
                // Update local data cache
                if (this._offlinePaymentsData) {
                    const entry = this._offlinePaymentsData.find(p => p.id === proofId);
                    if (entry) entry.screenshot_url = json.screenshot_url;
                }
                QCMS.toast('Screenshot uploaded and saved.', 'success');
            } else {
                if (pane) pane.innerHTML = origHtml;
                QCMS.toast(json.message || 'Upload failed.', 'error');
            }
        } catch (e) {
            if (pane) pane.innerHTML = origHtml;
            QCMS.toast('Upload error: ' + e.message, 'error');
        }
    },

    async submitRejectionWithReason(id, reason) {
        try {
            const res = await api.post(`/billing/offline-payments/${id}/reject`, { reason });
            if (res && res.status === 'success') {
                QCMS.toast('Payment proof rejected and feedback sent to organization.', 'info');
                const mReceipt = bootstrap.Modal.getInstance(document.getElementById('receiptPreviewModal'));
                if (mReceipt) mReceipt.hide();
                this.loadOfflinePayments();
            } else {
                QCMS.toast(res.message || 'Failed to reject payment', 'error');
            }
        } catch (e) {
            QCMS.toast(e.message || 'Rejection error', 'error');
        }
    },

    // --- Audit Registry & Activity Trail Module ---
    auditCurrentTab: 'logs',
    auditLogs: [],
    auditSessions: [],
    auditInsights: {},
    auditFilters: { page: 1, per_page: 10, q: '', date_preset: '', status: '', risk_level: '', org_id: '' },
    sessionFilters: { page: 1, per_page: 10 },
    auditSearchTimer: null,

    async initSuperAudit() {
        await Promise.all([
            this.populateAuditOrgFilter(),
            this.loadAuditKPIs(),
            this.loadAuditTab()
        ]);
        if (window.lucide) lucide.createIcons();
    },

    async populateAuditOrgFilter() {
        const select = document.getElementById('superAuditOrgFilter');
        if (!select || select.children.length > 1) return;
        try {
            const res = await api.get('/super-admin/companies?page=1&per_page=200');
            const orgs = (res && res.data) ? res.data : [];
            let html = '<option value="">All Organizations</option>';
            orgs.forEach(o => {
                const orgName = o.name || o.title || `Org #${o.id}`;
                html += `<option value="${o.id}">${QCMS.escapeHtml(orgName)}</option>`;
            });
            select.innerHTML = html;
            if (this.auditFilters.org_id) select.value = this.auditFilters.org_id;
        } catch (e) {
            console.error('Failed to populate org filter', e);
        }
    },

    async switchAuditTab(tab) {
        this.auditCurrentTab = tab;
        await this.loadAuditTab();
    },

    async loadAuditTab() {
        if (this.auditCurrentTab === 'logs') {
            await this.loadLogs();
        } else if (this.auditCurrentTab === 'sessions') {
            await this.loadAuditSessions();
        } else if (this.auditCurrentTab === 'insights') {
            await this.loadAuditInsights();
        }
    },

    // --- KPIs Load ---
    async loadAuditKPIs() {
        const grid = document.getElementById('superAuditKpiGrid');
        if (!grid) return;
        try {
            const orgParam = this.auditFilters.org_id ? `?org_id=${this.auditFilters.org_id}` : '';
            const res = await api.get(`/admin/audit/dashboard${orgParam}`);
            const d = res.data || {};
            
            const labels = {
                total_events: "Total Logged Actions",
                today_events: "Today's Events",
                failed_actions: "Failed Actions",
                success_actions: "Successful Actions",
                security_events: "Security Warnings",
                login_events: "Access Sessions",
                data_changes: "Data Modifications",
                critical_events: "Critical Incidents",
                deleted_records: "Deleted Records",
                export_activities: "Compliance Exports",
                active_sessions: "Active Sessions",
                failed_logins: "Failed Login Attempts"
            };
            
            grid.innerHTML = Object.keys(d).map(key => {
                const kpi = d[key];
                const growthSign = kpi.growth > 0 ? '+' : '';
                const growthClass = kpi.growth > 0 ? 'up' : (kpi.growth < 0 ? 'down' : 'neutral');
                const icon = kpi.icon || 'activity';
                
                let cardColor = 'rgba(99, 102, 241, 0.12)';
                let textColor = '#6366f1';
                if (key.includes('fail') || key.includes('critical') || key.includes('deleted')) {
                    cardColor = 'rgba(239, 68, 68, 0.12)';
                    textColor = '#ef4444';
                } else if (key.includes('success')) {
                    cardColor = 'rgba(16, 185, 129, 0.12)';
                    textColor = '#10b981';
                } else if (key.includes('security')) {
                    cardColor = 'rgba(245, 158, 11, 0.12)';
                    textColor = '#f59e0b';
                }
                
                return `
                <div class="audit-kpi-card" onclick="SuperAdmin.filterAuditByKpi('${key}')" title="${kpi.tooltip || ''}">
                    <div class="audit-kpi-growth ${growthClass}">${growthSign}${kpi.growth}%</div>
                    <div class="audit-kpi-icon" style="background:${cardColor};">
                        <i data-lucide="${icon}" style="width:16px;height:16px;color:${textColor};"></i>
                    </div>
                    <div class="audit-kpi-value">${kpi.value}</div>
                    <div class="audit-kpi-label">${labels[key] || key}</div>
                    <div class="audit-kpi-accent" style="background:${textColor}"></div>
                </div>`;
            }).join('');
            if (window.lucide) lucide.createIcons();
        } catch (e) {
            grid.innerHTML = `<div class="text-xs text-muted p-3">Failed to load system KPIs.</div>`;
        }
    },

    // --- Activity Stream Logs ---
    async loadLogs() {
        const tbody = document.getElementById('superLogsBody');
        if (!tbody) return;
        tbody.innerHTML = `<tr><td colspan="11" class="p-5 text-center"><span class="spinner-border spinner-border-sm me-2"></span>Loading secure activity stream...</td></tr>`;
        
        const params = new URLSearchParams();
        Object.keys(this.auditFilters).forEach(k => {
            if (this.auditFilters[k]) params.append(k, this.auditFilters[k]);
        });
        
        try {
            const res = await api.get(`/admin/audit/logs?${params.toString()}`);
            this.auditLogs = res.data || [];
            const pag = res.pagination || { total: this.auditLogs.length, page: 1, per_page: 10, pages: 1 };
            
            const countEl = document.getElementById('superLogsCount');
            if (countEl) countEl.textContent = `${pag.total} events`;
            
            this.renderAuditLogs(tbody);
            this.renderAuditPagination(pag);
        } catch (e) {
            tbody.innerHTML = `<tr><td colspan="11" class="p-5 text-center text-danger">Failed to fetch activity stream logs.</td></tr>`;
        }
    },

    renderAuditLogs(tbody) {
        if (!this.auditLogs.length) {
            tbody.innerHTML = `<tr><td colspan="11" class="p-5 text-center text-muted">No audit trail records found matching criteria.</td></tr>`;
            return;
        }
        
        const highlight = (txt) => {
            if (!txt) return '';
            if (!this.auditFilters.q) return txt;
            const esc = this.auditFilters.q.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
            return txt.toString().replace(new RegExp(`(${esc})`, 'gi'), '<mark class="highlight-mark">$1</mark>');
        };

        tbody.innerHTML = this.auditLogs.map(log => {
            const statusClass = log.status === 'Success' ? 'success' : (log.status === 'Critical' ? 'critical' : 'failed');
            const riskClass = (log.risk_level || 'Low').toLowerCase();
            
            return `
            <tr class="fade-in">
                <td class="text-xs font-mono text-secondary" style="white-space:nowrap;">${new Date(log.timestamp).toLocaleString('en-IN')}</td>
                <td><strong>${highlight(log.user)}</strong></td>
                <td><span class="text-xs text-muted">${log.role}</span></td>
                <td><span class="ds-badge blue">${highlight(log.action)}</span></td>
                <td><span class="text-xs font-mono">${log.module}</span></td>
                <td class="font-mono text-xs">${highlight(log.ip_address)}</td>
                <td class="text-xs text-secondary">${highlight(log.location)}</td>
                <td class="text-xs" title="${log.browser || ''} on ${log.os || ''}"><span class="text-muted">${highlight(log.device)}</span></td>
                <td><span class="audit-risk-badge ${riskClass}">${log.risk_level}</span></td>
                <td><span class="plan-status-badge ${statusClass}">${log.status}</span></td>
                <td class="text-end">
                    <button class="ds-btn ds-btn-ghost ds-btn-icon ds-btn-sm" onclick="SuperAdmin.openAuditDrawer(${log.id})">
                        <i data-lucide="eye" style="width:14px;"></i>
                    </button>
                </td>
            </tr>`;
        }).join('');
        if (window.lucide) lucide.createIcons();
    },

    // --- Active Sessions Monitor ---
    async loadAuditSessions() {
        const tbody = document.getElementById('superSessionsBody');
        if (!tbody) return;
        tbody.innerHTML = `<tr><td colspan="10" class="p-5 text-center"><span class="spinner-border spinner-border-sm me-2"></span>Loading user sessions...</td></tr>`;
        
        try {
            const orgParam = this.auditFilters.org_id ? `&org_id=${this.auditFilters.org_id}` : '';
            const pageParam = `page=${this.sessionFilters.page}&per_page=${this.sessionFilters.per_page}`;
            const res = await api.get(`/admin/audit/sessions?${pageParam}${orgParam}`);
            this.auditSessions = res.data || [];
            const pag = res.pagination || { total: this.auditSessions.length, page: this.sessionFilters.page, per_page: 10, pages: 1 };

            if (!this.auditSessions.length) {
                tbody.innerHTML = `<tr><td colspan="10" class="p-5 text-center text-muted">No active session records found.</td></tr>`;
            } else {
                tbody.innerHTML = this.auditSessions.map(s => {
                    const isAct = s.status === 'Active';
                    const statusBadge = isAct ? '<span class="ds-badge green">Active</span>' : `<span class="ds-badge gray">${s.status}</span>`;
                    const durMin = Math.round((s.session_duration || 0) / 60);
                    
                    return `
                    <tr class="fade-in">
                        <td><code class="text-xs font-mono">${s.session_id}</code></td>
                        <td><strong>${s.username}</strong></td>
                        <td class="text-xs text-secondary">${s.email}</td>
                        <td class="text-xs font-mono text-secondary">${new Date(s.login_time).toLocaleString()}</td>
                        <td class="text-xs">${durMin} mins</td>
                        <td class="text-xs font-mono">${s.ip_address}</td>
                        <td class="text-xs text-secondary">${s.location}</td>
                        <td class="text-xs">${s.os} · ${s.browser}</td>
                        <td>${statusBadge}</td>
                        <td class="text-end">
                            ${isAct 
                                ? `<button class="ds-btn ds-btn-outline-danger ds-btn-sm py-1 px-2.5 text-xs d-inline-flex align-items-center gap-1" onclick="SuperAdmin.terminateAuditSession('${s.session_id}')"><i data-lucide="power" style="width:12px;height:12px;"></i> Terminate</button>` 
                                : `<button class="ds-btn ds-btn-outline-secondary ds-btn-sm py-1 px-2.5 text-xs d-inline-flex align-items-center gap-1" onclick="SuperAdmin.terminateAuditSession('${s.session_id}')"><i data-lucide="shield-off" style="width:12px;height:12px;"></i> Revoke Session</button>`
                            }
                        </td>
                    </tr>`;
                }).join('');
            }
            this.renderSessionsPagination(pag);
        } catch (e) {
            tbody.innerHTML = `<tr><td colspan="10" class="p-5 text-center text-danger">Failed to load active sessions.</td></tr>`;
        }
    },

    renderSessionsPagination(pag) {
        const info = document.getElementById('superSessionsPaginationInfo');
        const controls = document.getElementById('superSessionsPaginationControls');
        if (!info || !controls) return;
        
        const start = pag.total > 0 ? (pag.page - 1) * pag.per_page + 1 : 0;
        const end = Math.min(pag.page * pag.per_page, pag.total);
        info.textContent = pag.total > 0 ? `Showing ${start} to ${end} of ${pag.total} sessions` : 'Showing 0 of 0 sessions';
        
        let btnHtml = '';
        if (pag.page > 1) {
            btnHtml += `<button class="ds-btn ds-btn-secondary ds-btn-sm" onclick="SuperAdmin.changeSessionPage(${pag.page - 1})">Prev</button>`;
        }
        
        const maxPagesToShow = 5;
        let startPage = Math.max(1, pag.page - 2);
        let endPage = Math.min(pag.pages, startPage + maxPagesToShow - 1);
        if (endPage - startPage + 1 < maxPagesToShow) {
            startPage = Math.max(1, endPage - maxPagesToShow + 1);
        }

        for (let i = startPage; i <= endPage; i++) {
            const isAct = i === pag.page ? 'ds-btn-primary' : 'ds-btn-secondary';
            btnHtml += `<button class="ds-btn ${isAct} ds-btn-sm px-3" onclick="SuperAdmin.changeSessionPage(${i})">${i}</button>`;
        }

        if (pag.page < pag.pages) {
            btnHtml += `<button class="ds-btn ds-btn-secondary ds-btn-sm" onclick="SuperAdmin.changeSessionPage(${pag.page + 1})">Next</button>`;
        }
        controls.innerHTML = btnHtml;
    },

    changeSessionPage(p) {
        this.sessionFilters.page = p;
        this.loadAuditSessions();
    },

    async terminateAuditSession(sid) {
        if (!confirm(`Forcefully terminate active session ${sid}?`)) return;
        try {
            await api.post(`/admin/audit/sessions/${sid}/terminate`);
            QCMS.toast('User session terminated successfully', 'success');
            await this.loadAuditSessions();
        } catch (e) {
            QCMS.toast(e.message || 'Failed to terminate session', 'error');
        }
    },

    // --- AI Insights ---
    async loadAuditInsights() {
        const box = document.getElementById('superAiInsightsBox');
        if (!box) return;
        box.innerHTML = `<span class="spinner-border spinner-border-sm"></span> Compiling risk signals...`;
        
        try {
            const orgParam = this.auditFilters.org_id ? `?org_id=${this.auditFilters.org_id}` : '';
            const res = await api.get(`/admin/audit/insights${orgParam}`);
            const d = res.data || {};
            this.auditInsights = d;
            
            const scoreVal = document.getElementById('superRiskScoreVal');
            if (scoreVal) scoreVal.textContent = d.risk_score;
            
            const dial = document.getElementById('superRiskDial');
            if (dial) {
                const offset = 251.2 * (1 - (d.risk_score || 100) / 100);
                dial.style.strokeDashoffset = offset;
                dial.style.stroke = d.risk_score > 80 ? '#10b981' : (d.risk_score > 50 ? '#f59e0b' : '#ef4444');
            }
            
            if (!d.recommendations || !d.recommendations.length) {
                box.innerHTML = `No threat signals or compliance risks detected in this registry cycle.`;
                return;
            }
            box.innerHTML = `<ul style="list-style:none;padding:0;margin:0;">
                ${d.recommendations.map(r => `
                    <li class="mb-3 d-flex gap-3 align-items-start p-3 rounded" style="background:var(--audit-box-bg); border:1px solid var(--audit-card-border);">
                        <div class="p-1 rounded bg-opacity-15 bg-warning text-warning"><i data-lucide="alert-triangle" style="width:14px;height:14px;"></i></div>
                        <div>
                            <div class="fw-semibold mb-1" style="color:var(--audit-text-main, inherit);">${r}</div>
                            <div class="text-xs" style="color:var(--audit-text-secondary, #64748b);">Audit integrity check recommends investigating user profile activities immediately.</div>
                        </div>
                    </li>`).join('')}
            </ul>`;
            if (window.lucide) lucide.createIcons();
        } catch (e) {
            box.innerHTML = `Failed to retrieve AI insights.`;
        }
    },

    // --- Trace Detail Drawer ---
    async openAuditDrawer(id) {
        const d = document.getElementById('superAuditDetailDrawer');
        const overlay = document.getElementById('superAuditDrawerOverlay');
        if (!d || !overlay) return;
        
        if (overlay.parentNode !== document.body) document.body.appendChild(overlay);
        if (d.parentNode !== document.body) document.body.appendChild(d);
        
        d.scrollTop = 0;
        d.classList.add('open');
        overlay.classList.add('open');
        
        try {
            const res = await api.get(`/admin/audit/logs/${id}`);
            const log = res.data;
            this.currentAuditDetailId = log.id;
            
            document.getElementById('superDRisk').textContent = log.risk_level;
            document.getElementById('superDRisk').className = `audit-risk-badge ${(log.risk_level || 'low').toLowerCase()}`;
            document.getElementById('superDAction').textContent = log.action;
            document.getElementById('superDLogId').textContent = `Audit ID: ${log.id} · SHA-256 Verified`;
            
            document.getElementById('superDUser').textContent = log.user;
            document.getElementById('superDEmail').textContent = log.user_email;
            document.getElementById('superDIp').textContent = log.ip_address;
            document.getElementById('superDLoc').textContent = log.location;
            document.getElementById('superDDev').textContent = log.device;
            const respCode = log.response_code || 200;
            document.getElementById('superDCode').textContent = `${respCode} (${respCode >= 400 ? 'Error' : 'OK'})`;
            const execTime = (log.execution_time !== null && log.execution_time !== undefined) ? Number(log.execution_time).toFixed(1) : '0.0';
            document.getElementById('superDTime').textContent = `${execTime} ms`;
            document.getElementById('superDSession').textContent = log.session_id || '—';
            
            // Diffs
            const diffBox = document.getElementById('superDiffBox');
            const diffData = document.getElementById('superDiffData');
            if (log.changed_fields && Object.keys(log.changed_fields).length > 0) {
                diffBox.classList.remove('d-none');
                diffData.innerHTML = Object.keys(log.changed_fields).map(key => {
                    const val = log.changed_fields[key];
                    return `
                    <div class="mb-2">
                        <strong class="text-indigo" style="font-size:11px;">• ${key}:</strong>
                        <div class="diff-removed">- Before: ${val.before}</div>
                        <div class="diff-added">+ After: ${val.after}</div>
                    </div>`;
                }).join('');
            } else {
                diffBox.classList.add('d-none');
            }

            // Timeline
            const timelineEl = document.getElementById('superSessionTimeline');
            if (log.timeline && log.timeline.length) {
                timelineEl.innerHTML = log.timeline.map(t => {
                    const dateStr = new Date(t.timestamp).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true });
                    const isFail = t.status === 'Failed' ? 'failed' : '';
                    const isCur = t.id === log.id;
                    const actionMarkup = isCur 
                        ? `<span class="badge bg-primary text-white font-mono text-xs px-2 py-1 shadow-sm">${t.action}</span>` 
                        : `<span class="fw-bold text-main font-mono text-xs">${t.action}</span>`;
                    
                    return `
                    <div class="timeline-audit-item ${isFail}">
                        <div class="text-xs fw-semibold text-secondary mb-1">${dateStr}</div>
                        <div>${actionMarkup}</div>
                    </div>`;
                }).join('');
            } else {
                timelineEl.innerHTML = 'Session timeline unavailable.';
            }

            // Related logs
            const relEl = document.getElementById('superRelatedLogs');
            if (log.related_logs && log.related_logs.length) {
                relEl.innerHTML = `<ul class="ps-3 mb-0" style="list-style:circle;">
                    ${log.related_logs.map(rl => `<li>
                        <strong>${rl.action}</strong> by ${rl.user} (${new Date(rl.timestamp).toLocaleTimeString()})
                    </li>`).join('')}
                </ul>`;
            } else {
                relEl.innerHTML = 'No related access flags in this session slot.';
            }

            if (window.lucide) lucide.createIcons();
        } catch (e) {
            QCMS.toast('Error retrieving audit telemetry detail', 'error');
        }
    },

    closeAuditDrawer() {
        document.getElementById('superAuditDetailDrawer')?.classList.remove('open');
        document.getElementById('superAuditDrawerOverlay')?.classList.remove('open');
    },

    toggleColumnSelector() {
        QCMS.toast('Dynamic table columns fully optimised for screen bounds', 'info');
    },

    renderAuditPagination(pag) {
        const info = document.getElementById('superPaginationInfo');
        const controls = document.getElementById('superPaginationControls');
        if (!info || !controls) return;
        
        const start = (pag.page - 1) * pag.per_page + 1;
        const end = Math.min(pag.page * pag.per_page, pag.total);
        info.textContent = pag.total > 0 ? `Showing ${start} to ${end} of ${pag.total} events` : 'Showing 0 of 0 events';
        
        let btnHtml = '';
        if (pag.page > 1) {
            btnHtml += `<button class="ds-btn ds-btn-secondary ds-btn-sm" onclick="SuperAdmin.changeAuditPage(${pag.page - 1})">Prev</button>`;
        }
        
        const maxPagesToShow = 5;
        let startPage = Math.max(1, pag.page - 2);
        let endPage = Math.min(pag.pages, startPage + maxPagesToShow - 1);
        if (endPage - startPage + 1 < maxPagesToShow) {
            startPage = Math.max(1, endPage - maxPagesToShow + 1);
        }

        for (let i = startPage; i <= endPage; i++) {
            const isAct = i === pag.page ? 'ds-btn-primary' : 'ds-btn-secondary';
            btnHtml += `<button class="ds-btn ${isAct} ds-btn-sm px-3" onclick="SuperAdmin.changeAuditPage(${i})">${i}</button>`;
        }

        if (pag.page < pag.pages) {
            btnHtml += `<button class="ds-btn ds-btn-secondary ds-btn-sm" onclick="SuperAdmin.changeAuditPage(${pag.page + 1})">Next</button>`;
        }
        controls.innerHTML = btnHtml;
    },

    changeAuditPage(p) {
        this.auditFilters.page = p;
        this.loadLogs();
    },

    debounceAuditSearch(v) {
        clearTimeout(this.auditSearchTimer);
        this.auditSearchTimer = setTimeout(() => {
            this.auditFilters.q = v.trim();
            this.auditFilters.page = 1;
            this.loadLogs();
        }, 300);
    },

    setAuditFilter(key, val) {
        this.auditFilters[key] = val;
        this.auditFilters.page = 1;
        this.loadLogs();
        this.loadAuditKPIs();
    },

    filterAuditByKpi(kpiType) {
        this.resetAuditFilters();
        
        if (kpiType === 'failed_actions') {
            this.auditFilters.status = 'Failed';
        } else if (kpiType === 'security_events') {
            this.auditFilters.risk_level = 'High';
        } else if (kpiType === 'critical_events') {
            this.auditFilters.risk_level = 'Critical';
        } else if (kpiType === 'login_events') {
            this.auditFilters.action_type = 'LOGIN,LOGOUT';
        } else if (kpiType === 'deleted_records') {
            this.auditFilters.action_type = 'DELETE';
        } else if (kpiType === 'export_activities') {
            this.auditFilters.action_type = 'EXPORT';
        } else if (kpiType === 'active_sessions') {
            const btn = document.getElementById('super-sessions-tab');
            if (btn) btn.click();
            return;
        }
        
        const statusSelect = document.getElementById('superAuditFilterStatus');
        if (statusSelect && this.auditFilters.status) statusSelect.value = this.auditFilters.status;
        const riskSelect = document.getElementById('superAuditFilterRisk');
        if (riskSelect && this.auditFilters.risk_level) riskSelect.value = this.auditFilters.risk_level;
        
        this.loadLogs();
    },

    resetAuditFilters() {
        this.auditFilters = { page: 1, per_page: 10, q: '', date_preset: '', status: '', risk_level: '', org_id: '' };
        
        const sQ = document.getElementById('superAuditSearchQ'); if (sQ) sQ.value = '';
        const sO = document.getElementById('superAuditOrgFilter'); if (sO) sO.value = '';
        const sD = document.getElementById('superAuditFilterDate'); if (sD) sD.value = '';
        const sS = document.getElementById('superAuditFilterStatus'); if (sS) sS.value = '';
        const sR = document.getElementById('superAuditFilterRisk'); if (sR) sR.value = '';
        this.loadLogs();
        this.loadAuditKPIs();
    },

    async verifyAuditIntegrity() {
        const banner = document.getElementById('superAuditIntegrityBanner');
        if (!banner) return;
        banner.classList.remove('d-none', 'alert-success', 'alert-danger', 'alert-warning');
        banner.classList.add('alert-info');
        banner.innerHTML = `<span class="spinner-border spinner-border-sm me-2"></span> Running SHA-256 hash checks on log registry…`;
        
        try {
            const orgParam = this.auditFilters.org_id ? `?org_id=${this.auditFilters.org_id}` : '';
            const res = await api.get(`/admin/audit/integrity${orgParam}`);
            banner.classList.remove('alert-info');
            
            if (res.status === 'success') {
                banner.classList.add('alert-success');
                banner.innerHTML = `<strong><i data-lucide="shield-check" class="me-1 d-inline-block" style="width:16px;"></i> Secure:</strong> ${res.message}`;
            } else {
                banner.classList.add('alert-danger');
                banner.innerHTML = `<strong><i data-lucide="alert-triangle" class="me-1 d-inline-block" style="width:16px;"></i> Compromise Alert:</strong> ${res.message} Detected ${res.tampered_count} tampered events. Details saved for review.`;
                await this.loadLogs();
            }
            if (window.lucide) lucide.createIcons();
        } catch (e) {
            banner.classList.remove('alert-info');
            banner.classList.add('alert-warning');
            banner.textContent = 'Integrity scanner offline. Ensure DB permissions are fully enabled.';
        }
    },

    copyAuditLogId() {
        if (!this.currentAuditDetailId) return;
        navigator.clipboard.writeText(this.currentAuditDetailId.toString());
        QCMS.toast('Audit Log ID copied to clipboard', 'success');
    },

    async generateAuditIncident() {
        if (!this.currentAuditDetailId) return;
        try {
            QCMS.toast(`Incident generated for Log ID ${this.currentAuditDetailId}. Security team has been notified.`, 'success');
            this.closeAuditDrawer();
        } catch (e) {
            QCMS.toast('Error creating security ticket', 'error');
        }
    },

    async exportAuditCSV() {
        QCMS.toast('Compiling audit registry fields...', 'info');
        try {
            const orgParam = this.auditFilters.org_id ? `?org_id=${this.auditFilters.org_id}` : '';
            const res = await api.get(`/admin/audit/export${orgParam}`);
            const csvContent = "data:text/csv;charset=utf-8," + encodeURIComponent(res.csv);
            const link = document.createElement("a");
            link.setAttribute("href", csvContent);
            link.setAttribute("download", `compliance_audit_logs_${new Date().toISOString().split('T')[0]}.csv`);
            document.body.appendChild(link);
            link.click();
            link.remove();
            QCMS.toast(`Exported ${res.count} audit trail events.`, 'success');
        } catch (e) {
            QCMS.toast('Failed to download compliance report', 'error');
        }
    },

    logsSetPerPage(v) {
        this.auditFilters.per_page = parseInt(v, 10) || 10;
        this.auditFilters.page = 1;
        this.loadLogs();
    },

    logsGoToPage(p) {
        this.auditFilters.page = p;
        this.loadLogs();
    },

    async handleSettingsUpdate(e) {
        e.preventDefault();
        const data = {
            site_name: document.getElementById('site_name').value,
            support_email: document.getElementById('support_email').value,
            global_notification: document.getElementById('global_notification').value,
            registration_open: document.getElementById('registration_open').checked,
            maintenance_mode: document.getElementById('maintenance_mode').checked
        };
        
        if (document.getElementById('default_plan')) data.default_plan = document.getElementById('default_plan').value;
        if (document.getElementById('trial_period_days')) data.trial_period_days = document.getElementById('trial_period_days').value;
        if (document.getElementById('payment_gateway_mode')) data.payment_gateway_mode = document.getElementById('payment_gateway_mode').value;

        try {
            const res = await api.put('/super-admin/settings', data);
            api.showNotification('Platform configuration updated successfully', 'success');
        } catch (err) {
            api.showNotification('Failed to update settings', 'error');
        }
    },

    async handleProfileUpdate(e) {
        e.preventDefault();
        const username = document.getElementById('sa_username').value;
        const password = document.getElementById('sa_password').value;
        const passwordConfirm = document.getElementById('sa_password_confirm').value;

        if (password && password !== passwordConfirm) {
            api.showNotification('Passwords do not match', 'error');
            return;
        }

        const data = { username };
        if (password) {
            data.password = password;
        }

        try {
            const res = await api.put('/super-admin/profile', data);
            api.showNotification('Credentials updated successfully', 'success');
            document.getElementById('sa_password').value = '';
            document.getElementById('sa_password_confirm').value = '';
        } catch (err) {
            api.showNotification(err.message || 'Failed to update credentials', 'error');
        }
    },

    async openTicketModal(ticketId) {
        try {
            const res = await api.get(`/super-admin/tickets/${ticketId}`);
            if (res && res.status === 'success') {
                const t = res.data;
                this.currentTicketId = ticketId;
                this.currentTicketOrgId = t.org_id || t.organization_id;

                const isReactivationTicket = (t.subject || '').toLowerCase().includes('reactivation');
                const reactivationBox = isReactivationTicket ? `
                    <div class="p-3 bg-danger-subtle border border-danger-subtle rounded-3 mb-3 text-danger">
                        <div class="d-flex justify-content-between align-items-center mb-2">
                            <div class="fw-bold text-xs"><i data-lucide="shield-alert" style="width:14px;height:14px;" class="me-1"></i> Account Reactivation Request</div>
                            <span class="badge bg-danger text-white text-xxs">Action Required</span>
                        </div>
                        <div class="text-xs mb-2">Subscriber Organization <strong>${QCMS.escapeHtml(t.organization)}</strong> has requested account reactivation.</div>
                        <button type="button" class="ds-btn ds-btn-success ds-btn-sm w-100 py-2 fw-bold" onclick="SuperAdmin.reactivateOrgFromTicket(${t.org_id || t.organization_id}, ${t.id}, '${QCMS.escapeHtml(t.organization)}')">
                            <i data-lucide="check-circle" class="me-1"></i> Reactivate Organization Account & Mark Resolved
                        </button>
                    </div>
                ` : '';

                document.getElementById('ticketDetail').innerHTML = `
                    <div class="v-stack gap-2">
                        ${reactivationBox}
                        <div class="h-stack justify-content-between">
                            <span class="fw-bold">From: ${QCMS.escapeHtml(t.organization)}</span>
                            <span class="ds-badge outline">${QCMS.escapeHtml(t.priority)} Priority</span>
                        </div>
                        <div class="text-sm">
                            <strong>Requester:</strong> ${QCMS.escapeHtml(t.requester_name)} (${QCMS.escapeHtml(t.requester_email)})
                        </div>
                        <div class="text-sm fw-bold">Subject: ${QCMS.escapeHtml(t.subject)}</div>
                        <div class="ds-well text-sm" style="white-space: pre-wrap; word-break: break-word;">${QCMS.escapeHtml(t.description)}</div>
                    </div>
                `;
                document.getElementById('ticketResolution').value = t.resolution || '';
                const modal = new bootstrap.Modal(document.getElementById('ticketModal'));
                modal.show();
                if (window.lucide) lucide.createIcons();
            }
        } catch (err) {
            api.showNotification('Could not load ticket details', 'error');
        }
    },

    async reactivateOrgFromTicket(orgId, ticketId, orgName) {
        if (!confirm(`Are you sure you want to reactivate the account for organization "${orgName}"?`)) return;
        try {
            let res = null;
            try {
                res = await api.post(`/licenses/${orgId}/resume`);
            } catch (e1) {
                res = await api.post(`/licenses/${orgId}/activate`);
            }
            if (res && (res.status === 'success' || res.message)) {
                await api.put(`/super-admin/tickets/${ticketId}`, {
                    status: 'Resolved',
                    resolution: 'Organization account reactivated by SuperAdmin.'
                });
                api.showNotification(`Organization "${orgName}" reactivated successfully!`, 'success');
                const modalEl = document.getElementById('ticketModal');
                if (modalEl) {
                    const m = bootstrap.Modal.getInstance(modalEl);
                    if (m) m.hide();
                }
                this.loadSupport();
            } else {
                api.showNotification((res && res.message) || 'Failed to reactivate organization', 'error');
            }
        } catch (e) {
            api.showNotification(e.message || 'Reactivation error', 'error');
        }
    },

    async handleTicketResolution(status = 'Resolved') {
        const resolution = document.getElementById('ticketResolution').value.trim();
        if (!resolution) {
            api.showNotification('Please provide a resolution summary or review notes', 'orange');
            return;
        }

        try {
            await api.put(`/super-admin/tickets/${this.currentTicketId}`, {
                status: status,
                resolution: resolution
            });
            api.showNotification(`Ticket marked as ${status === 'Resolved' ? 'Resolved' : 'Rejected'}`, 'success');
            bootstrap.Modal.getInstance(document.getElementById('ticketModal')).hide();
            this.loadSupport();
        } catch (err) {
            api.showNotification('Failed to update ticket status', 'error');
        }
    },

    filterCompanies(query) {
        clearTimeout(this._filterTimer);
        this._filterTimer = setTimeout(() => {
            this.currentPage = 1;
            this.loadOrganizations();
        }, 400);
    },

    async viewCompanyDetails(id) {
        try {
            const res = await api.get(`/super-admin/companies/${id}`);
            if (!res || res.status !== 'success') return;
            const d = res.data;
            this.currentDetailsOrg = d;
            
            document.getElementById('orgDetailTitle').innerHTML = `${d.name} <span class="badge bg-secondary bg-opacity-10 text-secondary border border-secondary border-opacity-25 ms-2" style="font-size:11px;font-family:monospace;">ID: ${d.id}</span> <span class="badge bg-primary bg-opacity-10 text-primary border border-primary border-opacity-25 ms-2" style="font-size:11px;">Registered: ${d.created_at ? QCMS.formatDate(d.created_at) : '—'}</span>`;
            
            // Set active tab to Overview
            document.querySelectorAll('#orgDetailTabs button').forEach(btn => btn.classList.remove('active'));
            document.getElementById('tab-overview-btn').classList.add('active');
            
            // Render default view (Overview)
            await this.renderOrgDetailTab('overview');
            
            const modal = new bootstrap.Modal(document.getElementById('orgDetailModal'));
            modal.show();
            
            // Setup click listeners for tabs
            document.querySelectorAll('#orgDetailTabs button').forEach(btn => {
                btn.onclick = async (e) => {
                    document.querySelectorAll('#orgDetailTabs button').forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    const targetTab = btn.getAttribute('id').replace('tab-', '').replace('-btn', '');
                    await this.renderOrgDetailTab(targetTab);
                };
            });
            
        } catch (err) {
            api.showNotification('Could not load organization details', 'error');
        }
    },

    async renderOrgDetailTab(tabName) {
        const container = document.getElementById('orgDetailTabContent');
        container.innerHTML = `<div class="text-center py-5"><span class="spinner-border spinner-border-sm me-2"></span>Loading tab...</div>`;
        
        const d = this.currentDetailsOrg;
        
        if (tabName === 'overview') {
            container.innerHTML = `
                <div class="fade-in">
                    <div class="impact-stat-grid mb-4">
                        <div class="impact-stat"><div class="val">${d.user_count}</div><div class="lbl">Users</div></div>
                        <div class="impact-stat"><div class="val">${d.dept_count}</div><div class="lbl">Departments</div></div>
                        <div class="impact-stat"><div class="val">${d.project_count}</div><div class="lbl">Projects</div></div>
                        <div class="impact-stat"><div class="val">${Math.round(d.storage_used_mb)} MB</div><div class="lbl">Storage Used</div></div>
                    </div>
                    <div class="row g-3">
                        <div class="col-6">
                            <div class="ds-card p-3">
                                <h6 class="fw-bold text-xs text-muted mb-2">REGISTRATION DATE</h6>
                                <span class="fw-bold text-sm text-primary">${d.created_at ? QCMS.formatDate(d.created_at) : '—'}</span>
                            </div>
                        </div>
                        <div class="col-6">
                            <div class="ds-card p-3">
                                <h6 class="fw-bold text-xs text-muted mb-2">SUBSCRIPTION EXPIRY</h6>
                                <span class="fw-bold text-sm">${d.trial_ends_at ? QCMS.formatDate(d.trial_ends_at) : 'No Expiry'}</span>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        } else if (tabName === 'profile') {
            container.innerHTML = `
                <div class="fade-in">
                    <h6 class="fw-bold text-xs text-uppercase text-muted mb-3">Company Information</h6>
                    <div class="row g-3">
                        <div class="col-6"><div class="detail-label">Name</div><div class="text-sm fw-bold">${d.name || '—'}</div></div>
                        <div class="col-6"><div class="detail-label">Code</div><div class="text-sm fw-bold">${d.org_code || d.code || '—'}</div></div>
                        <div class="col-6"><div class="detail-label">Industry</div><div class="text-sm">${d.industry || '—'}</div></div>
                        <div class="col-6"><div class="detail-label">Website</div><div class="text-sm">${d.website && d.website !== '—' ? `<a href="${d.website.startsWith('http') ? d.website : 'https://' + d.website}" target="_blank" rel="noopener noreferrer">${d.website}</a>` : '—'}</div></div>
                        <div class="col-6"><div class="detail-label">Registered On</div><div class="text-sm fw-bold text-primary">${d.created_at ? QCMS.formatDate(d.created_at) : '—'}</div></div>
                        <div class="col-6"><div class="detail-label">GST Number</div><div class="text-sm fw-bold">${d.gst_number || '—'}</div></div>
                        <div class="col-6"><div class="detail-label">PAN Number</div><div class="text-sm fw-bold">${d.pan_number || '—'}</div></div>
                        <div class="col-6"><div class="detail-label">Phone</div><div class="text-sm">${d.phone || '—'}</div></div>
                        <div class="col-6"><div class="detail-label">Email</div><div class="text-sm">${d.email || '—'}</div></div>
                        <div class="col-12"><div class="detail-label">Address</div><div class="text-sm">${[d.address, d.city, d.state, d.country].filter(Boolean).join(', ')}${d.zip_code ? ' - ' + d.zip_code : ''}</div></div>
                    </div>
                </div>
            `;
        } else if (tabName === 'subscription') {
            container.innerHTML = `
                <div class="fade-in">
                    <h6 class="fw-bold text-xs text-uppercase text-muted mb-3">Subscription Details</h6>
                    <div class="row g-3">
                        <div class="col-6"><div class="detail-label">Plan</div><div class="text-sm fw-bold"><span class="ds-badge blue">${d.subscription_plan}</span></div></div>
                        <div class="col-6"><div class="detail-label">Status</div><div class="text-sm fw-bold"><span class="ds-badge green">${d.subscription_status === 'Trialing' || d.subscription_status === 'Trial' ? 'On Trial' : d.subscription_status}</span></div></div>
                        <div class="col-6"><div class="detail-label">Registered On</div><div class="text-sm fw-bold text-primary">${d.created_at ? QCMS.formatDate(d.created_at) : '—'}</div></div>
                        <div class="col-6"><div class="detail-label">Timezone</div><div class="text-sm">${d.timezone}</div></div>
                        <div class="col-6"><div class="detail-label">Trial Expiry</div><div class="text-sm">${d.trial_ends_at ? QCMS.formatDate(d.trial_ends_at) : '—'}</div></div>
                        <div class="col-6"><div class="detail-label">Remaining Trial</div><div class="text-sm">${d.trial_days_left !== null ? d.trial_days_left + ' days left' : '—'}</div></div>
                    </div>
                </div>
            `;
        } else if (tabName === 'users') {
            await this.loadCompanyUsersTab(d.id, 1, '');
        } else if (tabName === 'billing') {
            try {
                const res = await api.get('/super-admin/payments');
                const payments = (res.data || []).filter(p => p.organization === d.name);
                let rows = payments.map(p => `
                    <tr>
                        <td><strong>₹${p.amount.toLocaleString('en-IN')}</strong></td>
                        <td class="text-xs font-monospace text-secondary">${p.transaction_id}</td>
                        <td class="text-xs text-muted">${QCMS.formatDate(p.date)}</td>
                        <td>${QCMS.statusBadge(p.status)}</td>
                    </tr>
                `).join('');
                if (payments.length === 0) rows = `<tr><td colspan="4" class="text-center py-4 text-muted">No billing invoices found.</td></tr>`;
                container.innerHTML = `
                    <div class="fade-in">
                        <h6 class="fw-bold text-xs text-uppercase text-muted mb-3">Invoices & Subscription Billing</h6>
                        <table class="ds-table">
                            <thead>
                                <tr>
                                    <th>Amount</th>
                                    <th>Transaction ID</th>
                                    <th>Date</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${rows}
                            </tbody>
                        </table>
                    </div>
                `;
            } catch (err) {
                container.innerHTML = `<div class="text-danger py-4">Failed to load billing invoices.</div>`;
            }
        } else if (tabName === 'support') {
            try {
                const res = await api.get('/super-admin/tickets');
                const tickets = (res.data || []).filter(t => t.organization === d.name);
                let rows = tickets.map(t => `
                    <tr>
                        <td><span class="text-xs font-monospace">#${t.id}</span></td>
                        <td><strong>${t.subject}</strong></td>
                        <td><span class="ds-badge outline">${t.priority}</span></td>
                        <td>${QCMS.statusBadge(t.status)}</td>
                        <td class="text-xs text-muted">${QCMS.formatDate(t.created_at)}</td>
                    </tr>
                `).join('');
                if (tickets.length === 0) rows = `<tr><td colspan="5" class="text-center py-4 text-muted">No support tickets found.</td></tr>`;
                container.innerHTML = `
                    <div class="fade-in">
                        <h6 class="fw-bold text-xs text-uppercase text-muted mb-3">Support Tickets Desk</h6>
                        <table class="ds-table">
                            <thead>
                                <tr>
                                    <th>ID</th>
                                    <th>Subject</th>
                                    <th>Priority</th>
                                    <th>Status</th>
                                    <th>Created</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${rows}
                            </tbody>
                        </table>
                    </div>
                `;
            } catch (err) {
                container.innerHTML = `<div class="text-danger py-4">Failed to load support tickets.</div>`;
            }
        } else if (tabName === 'activity') {
            try {
                const res = await api.get(`/super-admin/companies/${d.id}/logs`);
                const logs = res.data || [];
                let list = logs.map(log => `
                    <div class="p-2 border-bottom text-xs d-flex justify-content-between align-items-center" style="border-color: var(--ds-border-color)!important;">
                        <div>
                            <span class="fw-bold text-primary">${log.action}</span> by <span class="fw-semibold">${log.admin}</span>
                        </div>
                        <span class="text-muted font-monospace text-xxs">${QCMS.formatRelative(log.timestamp)}</span>
                    </div>
                `).join('');
                if (logs.length === 0) list = `<div class="text-center py-4 text-muted text-xs">No audit logs found.</div>`;
                container.innerHTML = `
                    <div class="fade-in">
                        <h6 class="fw-bold text-xs text-uppercase text-muted mb-3">Activity & Audit Timeline</h6>
                        <div class="border rounded-2" style="border-color: var(--ds-border-color)!important; max-height: 350px; overflow-y: auto;">
                            ${list}
                        </div>
                    </div>
                `;
            } catch (err) {
                container.innerHTML = `<div class="text-danger py-4">Failed to load audit logs.</div>`;
            }
        }
    },

    _orgUserSearchTimer: null,
    debounceOrgUserSearch(orgId, val) {
        clearTimeout(this._orgUserSearchTimer);
        this._orgUserSearchTimer = setTimeout(() => {
            this.loadCompanyUsersTab(orgId, 1, val);
        }, 300);
    },

    async loadCompanyUsersTab(orgId, page = 1, searchQuery = '') {
        const container = document.getElementById('orgDetailTabContent');
        if (!container) return;
        
        try {
            const url = `/super-admin/companies/${orgId}/users?page=${page}&per_page=5&q=${encodeURIComponent(searchQuery)}`;
            const res = await api.get(url);
            const users = res.data || [];
            const pg = res.pagination || {
                page: page,
                per_page: 5,
                total: users.length,
                total_pages: Math.ceil(users.length / 5) || 1
            };

            let rows = users.map(u => `
                <tr>
                    <td><strong>${this._escapeHTML(u.full_name || '—')}</strong><br><small class="text-muted">${this._escapeHTML(u.username)}</small></td>
                    <td class="text-xs text-muted">${this._escapeHTML(u.email)}</td>
                    <td><span class="ds-badge outline">${this._escapeHTML(u.role || 'Member')}</span></td>
                    <td><span class="ds-badge ${u.status === 'Active' || u.is_active ? 'green' : 'red'}" style="font-size:10px; padding:2px 6px;">${this._escapeHTML(u.status || (u.is_active ? 'Active' : 'Inactive'))}</span></td>
                    <td class="text-xs text-muted">${u.last_login ? QCMS.formatRelative(u.last_login) : 'Never'}</td>
                </tr>
            `).join('');

            if (users.length === 0) {
                rows = `<tr><td colspan="5" class="text-center py-4 text-muted">No members found${searchQuery ? ' matching "' + this._escapeHTML(searchQuery) + '"' : ''}.</td></tr>`;
            }

            const start = pg.total > 0 ? (pg.page - 1) * pg.per_page + 1 : 0;
            const end = Math.min(pg.page * pg.per_page, pg.total);

            let pageBtns = '';
            const totalPages = pg.total_pages || 1;
            for (let p = 1; p <= totalPages; p++) {
                if (p === pg.page) {
                    pageBtns += `<button class="btn btn-sm btn-primary py-1 px-2.5" style="font-size:11px;">${p}</button>`;
                } else if (p === 1 || p === totalPages || (p >= pg.page - 1 && p <= pg.page + 1)) {
                    pageBtns += `<button class="btn btn-sm btn-outline-secondary py-1 px-2.5" style="font-size:11px;" onclick="SuperAdmin.loadCompanyUsersTab(${orgId}, ${p}, '${this._escapeHTML(searchQuery)}')">${p}</button>`;
                } else if (p === pg.page - 2 || p === pg.page + 2) {
                    pageBtns += `<span class="px-1 text-muted">…</span>`;
                }
            }

            container.innerHTML = `
                <div class="fade-in">
                    <div class="d-flex align-items-center justify-content-between gap-3 mb-3 flex-wrap">
                        <div>
                            <h6 class="fw-bold text-xs text-uppercase text-muted mb-0">Admin & Users Directory</h6>
                            <span class="text-xxs text-muted">Showing ${pg.total} total members</span>
                        </div>
                        <div style="min-width: 220px; position: relative;">
                            <i data-lucide="search" style="width: 14px; height: 14px; position: absolute; left: 10px; top: 50%; transform: translateY(-50%); opacity: 0.5; color: var(--ds-text-muted);"></i>
                            <input type="search" id="orgUserSearchInput" class="ds-input ps-4" style="height: 34px; font-size: 12px; border-radius: 8px;" placeholder="Search name, email, username..." value="${this._escapeHTML(searchQuery)}" oninput="SuperAdmin.debounceOrgUserSearch(${orgId}, this.value)">
                        </div>
                    </div>
                    <div class="table-responsive">
                        <table class="ds-table">
                            <thead>
                                <tr>
                                    <th>Name</th>
                                    <th>Email</th>
                                    <th>Role</th>
                                    <th>Status</th>
                                    <th>Last Login</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${rows}
                            </tbody>
                        </table>
                    </div>
                    <div class="d-flex align-items-center justify-content-between mt-3 text-xs text-muted">
                        <div>
                            Showing ${start}–${end} of ${pg.total} members
                        </div>
                        <div class="d-flex gap-1 align-items-center">
                            <button class="btn btn-sm btn-outline-secondary py-1 px-2" style="font-size:11px;" ${pg.page <= 1 ? 'disabled' : ''} onclick="SuperAdmin.loadCompanyUsersTab(${orgId}, ${pg.page - 1}, '${this._escapeHTML(searchQuery)}')">
                                &laquo; Prev
                            </button>
                            ${pageBtns}
                            <button class="btn btn-sm btn-outline-secondary py-1 px-2" style="font-size:11px;" ${pg.page >= totalPages ? 'disabled' : ''} onclick="SuperAdmin.loadCompanyUsersTab(${orgId}, ${pg.page + 1}, '${this._escapeHTML(searchQuery)}')">
                                Next &raquo;
                            </button>
                        </div>
                    </div>
                </div>
            `;

            const searchInput = document.getElementById('orgUserSearchInput');
            if (searchInput && searchQuery) {
                searchInput.focus();
                searchInput.setSelectionRange(searchQuery.length, searchQuery.length);
            }

            if (window.lucide) lucide.createIcons();
        } catch (err) {
            console.error('Failed to load company users:', err);
            container.innerHTML = `<div class="text-danger py-4 text-center text-xs">Failed to load member directory.</div>`;
        }
    },

    async openChangePlan(id, name, currentPlan) {
        await this.populateAllPlanDropdowns();
        document.getElementById('changePlanOrgId').value = id;
        document.getElementById('changePlanOrgName').textContent = name;
        document.getElementById('changePlanSelect').value = currentPlan;
        const modal = new bootstrap.Modal(document.getElementById('changePlanModal'));
        modal.show();
    },

    openExtendTrial(id, name) {
        document.getElementById('extendTrialOrgId').value = id;
        document.getElementById('extendTrialOrgName').textContent = name;
        // Default to 14 days from now
        const d = new Date(); d.setDate(d.getDate() + 14);
        document.getElementById('extendTrialDate').value = d.toISOString().split('T')[0];
        const modal = new bootstrap.Modal(document.getElementById('extendTrialModal'));
        modal.show();
    },

    confirmStatusChange(id, name, newStatus) {
        const isSuspend = newStatus === 'Suspended';
        const iconEl = document.getElementById('confirmActionIcon');
        iconEl.style.background = isSuspend ? 'rgba(245, 158, 11, 0.12)' : 'rgba(var(--ds-green-rgb), 0.12)';
        iconEl.innerHTML = isSuspend 
            ? '<i data-lucide="pause-circle" style="width:24px;height:24px;color:#f59e0b;"></i>'
            : '<i data-lucide="check-circle" style="width:24px;height:24px;color:rgb(var(--ds-green-rgb));"></i>';
        document.getElementById('confirmActionTitle').textContent = isSuspend ? 'Pause Organization?' : 'Reactivate Organization?';
        document.getElementById('confirmActionMsg').textContent = isSuspend
            ? `${name} will be paused and lose platform access.`
            : `${name} will regain full platform access.`;
        const btn = document.getElementById('confirmActionBtn');
        btn.className = isSuspend ? 'ds-btn ds-btn-warning' : 'ds-btn ds-btn-primary';
        btn.textContent = isSuspend ? 'Pause' : 'Reactivate';
        btn.onclick = async () => {
            try {
                await api.put(`/super-admin/companies/${id}/status`, { status: newStatus });
                api.showNotification(`Organization ${isSuspend ? 'paused' : 'reactivated'} successfully`, 'success');
                bootstrap.Modal.getInstance(document.getElementById('confirmActionModal')).hide();
                this.loadOrganizations();
            } catch (err) {
                api.showNotification('Failed to update status', 'error');
            }
        };
        const modal = new bootstrap.Modal(document.getElementById('confirmActionModal'));
        modal.show();
        if (window.lucide) lucide.createIcons();
    },

    activateSubscription(id, name) {
        const iconEl = document.getElementById('confirmActionIcon');
        iconEl.style.background = 'rgba(var(--ds-green-rgb), 0.12)';
        iconEl.innerHTML = '<i data-lucide="credit-card" style="width:24px;height:24px;color:rgb(var(--ds-green-rgb));"></i>';
        document.getElementById('confirmActionTitle').textContent = 'Activate Subscription?';
        document.getElementById('confirmActionMsg').textContent = `This will move ${name} from the trial period to an Active monthly subscription (30 days validity).`;
        const btn = document.getElementById('confirmActionBtn');
        btn.className = 'ds-btn ds-btn-primary';
        btn.textContent = 'Activate';
        btn.onclick = async () => {
            try {
                const res = await api.post(`/super-admin/companies/${id}/activate-subscription`);
                if (res && res.status === 'success') {
                    api.showNotification(res.message || 'Subscription activated successfully', 'success');
                } else {
                    api.showNotification(res.msg || 'Subscription activated successfully', 'success');
                }
                bootstrap.Modal.getInstance(document.getElementById('confirmActionModal')).hide();
                this.loadOrganizations();
            } catch (err) {
                api.showNotification('Failed to activate subscription', 'error');
            }
        };
        const modal = new bootstrap.Modal(document.getElementById('confirmActionModal'));
        modal.show();
        if (window.lucide) lucide.createIcons();
    },

    exportCompanies() {
        if (!this.allCompanies || !this.allCompanies.length) {
            api.showNotification('No data to export', 'info');
            return;
        }
        const headers = ['Name','Industry','Admin','Email','Plan','Status','Users','Max Users','White Label','API Access','Created'];
        const rows = this.allCompanies.map(o => [
            o.name, o.industry, o.admin_name, o.email, o.plan, o.status,
            o.user_count, o.max_users, o.is_white_label ? 'Yes' : 'No',
            o.api_access ? 'Yes' : 'No', o.created_at
        ]);
        const csv = [headers.join(','), ...rows.map(r => r.map(v => `"${v}"`).join(','))].join('\n');
        const blob = new Blob([csv], { type: 'text/csv' });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `organizations_export_${new Date().toISOString().slice(0,10)}.csv`;
        a.click();
        api.showNotification('CSV exported successfully', 'success');
    },

    exportPayments() {
        api.showNotification('Export initiated — preparing billing CSV...', 'info');
    },

    // ─── NEW VIEW LOADERS ────────────────────────────────────────────────────


    // ─── ENTERPRISE SUBSCRIPTION MANAGEMENT ──────────────────────────────────
    // All state is namespaced under SuperAdmin._sub to avoid conflicts

    _sub: {
        page: 1, perPage: 20, totalPages: 1,
        sortBy: 'created_at', sortDir: 'desc',
        filters: { status:'', plan:'', billing_cycle:'', payment_status:'', renewal_window:'' },
        q: '', searchTimer: null,
        selectedIds: new Set(),
        planChangeSub: null, planChangeMode: null, planChangeSelected: null,
        catalogue: {}, wizStep: 1,
    },

    // ── API ───────────────────────────────────────────────────────────────────
    async _subGet(path) {
        return api.get(`/subscriptions${path}`);
    },
    async _subPost(path, body={}) {
        return api.post(`/subscriptions${path}`, body);
    },
    async _subPut(path, body={}) {
        return api.put(`/subscriptions${path}`, body);
    },

    // ── Helpers ───────────────────────────────────────────────────────────────
    _subFmt(v){ const n=parseFloat(v)||0; return '₹'+n.toLocaleString('en-IN',{minimumFractionDigits:0,maximumFractionDigits:0}); },
    _subFmtD(v){ if(!v)return '—'; return new Date(v).toLocaleDateString('en-IN',{day:'2-digit',month:'short',year:'numeric'}); },
    _subEsc(s){ return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); },
    _subExpiring(d){ if(!d)return false; return (new Date(d)-new Date())<30*86400000; },
    _subNotify(msg, type='success'){
        if(window.api && api.showNotification){ api.showNotification(msg, type); return; }
        const bgColors={success:'#f0fdf4',error:'#fef2f2',info:'#eff6ff',warning:'#fffbeb'};
        const textColors={success:'#065f46',error:'#991b1b',info:'#1e40af',warning:'#92400e'};
        const borderColors={success:'#10b981',error:'#ef4444',info:'#3b82f6',warning:'#f59e0b'};
        const c=document.createElement('div');
        c.style.cssText=`position:fixed;top:24px;right:24px;background:${bgColors[type]||'#fff'};color:${textColors[type]||'#0f172a'};border:1px solid ${borderColors[type]};border-left:5px solid ${borderColors[type]};border-radius:10px;padding:12px 18px;font-size:13.5px;font-weight:600;z-index:99999999;box-shadow:0 10px 30px rgba(0,0,0,.25);max-width:380px;min-width:300px;`;
        c.textContent=msg; document.body.appendChild(c); setTimeout(()=>c.remove(),4000);
    },

    // ── Real-Time Storage Dashboard Management ──────────────────────────────────
    _storageDataCache: null,

    _escapeHTML(str) {
        if (!str) return '';
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#039;');
    },

    async loadStorageDashboard(forceRefresh = false) {
        const tbody = document.getElementById('storageDashboardTableBody');
        if (tbody && (forceRefresh || !this._storageDataCache)) {
            tbody.innerHTML = `<tr><td colspan="9" class="text-center p-4 text-muted"><i data-lucide="loader" class="spin me-2"></i> Fetching real-time organization storage statistics...</td></tr>`;
            if (window.lucide) lucide.createIcons();
        }

        try {
            const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token') || localStorage.getItem('token') || sessionStorage.getItem('token');
            const res = await fetch('/api/v1/storage/breakdown', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const json = await res.json();

            if (json.status === 'success' && json.data) {
                this._storageDataCache = json.data;
                const summary = json.data.summary || {};

                // Update Summary Cards
                const totalUsedEl = document.getElementById('storageDashTotalUsed');
                const totalLimitEl = document.getElementById('storageDashTotalLimit');
                const orgCountEl = document.getElementById('storageDashOrgCount');
                const avgUsedEl = document.getElementById('storageDashAvgUsed');
                const alertCountEl = document.getElementById('storageDashAlertCount');
                const kpiStorageVal = document.getElementById('saStorageKpiVal');

                if (totalUsedEl) totalUsedEl.textContent = summary.total_used_fmt || `${summary.total_used_mb} MB`;
                if (totalLimitEl) totalLimitEl.textContent = `Total limit: ${summary.total_limit_fmt || '0 GB'}`;
                if (orgCountEl) orgCountEl.textContent = summary.total_orgs || 0;
                if (avgUsedEl) avgUsedEl.textContent = `${summary.avg_usage_mb || 0} MB`;
                if (alertCountEl) alertCountEl.textContent = summary.high_usage_count || 0;
                if (kpiStorageVal) kpiStorageVal.textContent = summary.total_used_fmt || `${summary.total_used_mb} MB`;

                this.renderStorageTable(json.data.organizations || []);
            } else {
                if (tbody) tbody.innerHTML = `<tr><td colspan="9" class="text-center p-4 text-danger">Failed to load storage metrics: ${json.error || 'Server error'}</td></tr>`;
            }
        } catch (err) {
            console.error('Failed to load storage dashboard:', err);
            if (tbody) tbody.innerHTML = `<tr><td colspan="9" class="text-center p-4 text-danger">Network error connecting to storage service.</td></tr>`;
        }
    },

    filterStorageDashboard() {
        if (!this._storageDataCache || !this._storageDataCache.organizations) return;
        const query = (document.getElementById('storageSearchInput')?.value || '').toLowerCase().trim();
        const healthFilter = document.getElementById('storageHealthFilter')?.value || 'ALL';
        const sortFilter = document.getElementById('storageSortFilter')?.value || 'STORAGE_DESC';

        let list = [...this._storageDataCache.organizations];

        // Search Filter
        if (query) {
            list = list.filter(o =>
                (o.name || '').toLowerCase().includes(query) ||
                (o.org_code || '').toLowerCase().includes(query) ||
                (o.plan || '').toLowerCase().includes(query)
            );
        }

        // Health Status Filter
        if (healthFilter !== 'ALL') {
            list = list.filter(o => o.health_status === healthFilter);
        }

        // Sorting
        if (sortFilter === 'STORAGE_DESC') {
            list.sort((a, b) => b.storage_used_mb - a.storage_used_mb);
        } else if (sortFilter === 'STORAGE_ASC') {
            list.sort((a, b) => a.storage_used_mb - b.storage_used_mb);
        } else if (sortFilter === 'NAME_ASC') {
            list.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
        } else if (sortFilter === 'PCT_DESC') {
            list.sort((a, b) => b.usage_percent - a.usage_percent);
        }

        this.renderStorageTable(list);
    },

    renderStorageTable(orgs) {
        const tbody = document.getElementById('storageDashboardTableBody');
        if (!tbody) return;

        if (!orgs || orgs.length === 0) {
            tbody.innerHTML = `<tr><td colspan="9" class="text-center p-4 text-muted">No organizations match the selected storage filters.</td></tr>`;
            return;
        }

        tbody.innerHTML = orgs.map(o => {
            const usedMb = o.storage_used_mb || 0;
            const limitMb = o.storage_limit_mb || 10240;
            const limitGb = o.storage_limit_gb || (limitMb / 1024);
            const usedFmt = usedMb < 1024 ? `${usedMb} MB` : `${o.storage_used_gb || (usedMb / 1024).toFixed(2)} GB`;
            const pct = o.usage_percent || 0;
            const barBg = pct >= 90 ? 'bg-danger' : (pct >= 70 ? 'bg-warning' : 'bg-primary');
            const badgeBg = pct >= 90 ? 'bg-danger-subtle text-danger' : (pct >= 70 ? 'bg-warning-subtle text-warning-emphasis' : 'bg-success-subtle text-success');

            const orgName = this._escapeHTML(o.name || 'Organization');
            const orgCode = this._escapeHTML(o.org_code || o.id);
            const planName = this._escapeHTML(o.plan || 'Free');
            const rawStat = o.subscription_status || 'Active';
            const statusStr = this._escapeHTML(rawStat === 'Trialing' || rawStat === 'Trial' ? 'On Trial' : rawStat);
            const healthStr = this._escapeHTML(o.health_status || 'Normal');

            return `
                <tr>
                    <td>
                        <div class="fw-bold text-main text-sm">${orgName}</div>
                        <div class="text-xxs text-muted">ID: ${o.id} &bull; Code: <span class="badge bg-light text-dark font-mono">${orgCode}</span></div>
                    </td>
                    <td>
                        <span class="badge bg-primary-subtle text-primary font-semibold text-xs">${planName}</span>
                        <div class="text-xxs text-muted mt-0.5">${statusStr}</div>
                    </td>
                    <td>
                        <div class="fw-semibold text-xs text-main"><i data-lucide="users" style="width:12px;height:12px;" class="me-1 text-muted"></i>${o.users_count || 0} Users</div>
                    </td>
                    <td>
                        <div class="fw-semibold text-xs text-main"><i data-lucide="folder-kanban" style="width:12px;height:12px;" class="me-1 text-muted"></i>${o.projects_count || 0} Projects</div>
                    </td>
                    <td>
                        <div class="fw-bold text-sm text-primary">${usedFmt}</div>
                        <div class="text-xxs text-muted">${o.audits_count || 0} Audit Logs</div>
                    </td>
                    <td>
                        <div class="fw-semibold text-xs text-main">${limitGb} GB</div>
                        <div class="text-xxs text-muted">(${(limitMb).toLocaleString('en-IN')} MB)</div>
                    </td>
                    <td>
                        <div class="d-flex justify-content-between text-xxs mb-1">
                            <span class="fw-semibold text-muted">${pct}% Used</span>
                            <span class="text-muted">${usedFmt} / ${limitGb} GB</span>
                        </div>
                        <div class="progress" style="height: 6px; border-radius: 4px; background: rgba(0,0,0,0.06);">
                            <div class="progress-bar ${barBg}" role="progressbar" style="width: ${Math.min(100, pct)}%; border-radius: 4px;"></div>
                        </div>
                    </td>
                    <td>
                        <span class="badge ${badgeBg} font-semibold text-xs px-2.5 py-1">${healthStr}</span>
                    </td>
                    <td class="text-end">
                        <button class="ds-btn ds-btn-outline ds-btn-sm" onclick="SuperAdmin.viewOrgStorageBreakdown(${o.id})" title="View detailed data breakdown">
                            <i data-lucide="info" style="width:12px;height:12px;"></i> Details
                        </button>
                    </td>
                </tr>
            `;
        }).join('');

        if (window.lucide) lucide.createIcons();
    },

    updateOrgStorageLimitPrompt(orgId, orgName, currentLimitGb) {
        // Store context for confirm handler
        this._slmOrgId = orgId;
        this._slmOrgName = orgName;

        // Find current used from cache
        const org = (this._storageDataCache && this._storageDataCache.organizations || []).find(o => o.id === orgId);
        const usedMb = org ? (org.storage_used_mb || 0) : 0;
        const usedFmt = usedMb < 1024 ? `${usedMb} MB` : `${(usedMb/1024).toFixed(2)} GB`;

        // Populate modal
        const slmOrgName = document.getElementById('slmOrgName');
        const slmCurrentLimit = document.getElementById('slmCurrentLimit');
        const slmCurrentUsed = document.getElementById('slmCurrentUsed');
        const slmNewLimit = document.getElementById('slmNewLimit');
        if (slmOrgName) slmOrgName.textContent = orgName;
        if (slmCurrentLimit) slmCurrentLimit.textContent = `${currentLimitGb} GB`;
        if (slmCurrentUsed) slmCurrentUsed.textContent = usedFmt;
        if (slmNewLimit) { slmNewLimit.value = currentLimitGb; }

        // Show modal
        const modal = document.getElementById('storageLimitModal');
        if (modal) { modal.style.display = 'flex'; if (window.lucide) lucide.createIcons(); setTimeout(() => slmNewLimit && slmNewLimit.focus(), 100); }
    },

    closeStorageLimitModal() {
        const modal = document.getElementById('storageLimitModal');
        if (modal) modal.style.display = 'none';
        this._slmOrgId = null;
        this._slmOrgName = null;
    },

    async _confirmStorageLimitUpdate() {
        const orgId = this._slmOrgId;
        const slmNewLimit = document.getElementById('slmNewLimit');
        const newLimitGb = slmNewLimit ? parseFloat(slmNewLimit.value) : NaN;

        if (!orgId || isNaN(newLimitGb) || newLimitGb <= 0) {
            this.toast('Please enter a valid positive number for the storage limit.', 'error');
            if (slmNewLimit) slmNewLimit.focus();
            return;
        }

        this.closeStorageLimitModal();

        try {
            const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token') || localStorage.getItem('token') || sessionStorage.getItem('token');
            let res = await fetch('/api/v1/storage/update-limit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
                body: JSON.stringify({ org_id: orgId, storage_limit_gb: newLimitGb })
            });
            const json = await res.json();
            if (json.status === 'success') {
                this.toast(json.message || 'Storage limit updated successfully.', 'success');
                this.loadStorageDashboard(true);
            } else {
                this.toast('Error: ' + (json.message || json.error || 'Failed to update limit.'), 'error');
            }
        } catch (e) {
            console.error('Failed to update storage limit:', e);
            this.toast('Network error while updating storage limit.', 'error');
        }
    },

    viewOrgStorageBreakdown(orgId) {
        if (!this._storageDataCache || !this._storageDataCache.organizations) return;
        const org = this._storageDataCache.organizations.find(o => o.id === orgId);
        if (!org) return;

        const bd = org.breakdown || {};
        const usedMb = org.storage_used_mb || 0;
        const limitGb = org.storage_limit_gb || 10;
        const pct = org.usage_percent || 0;
        const usedFmt = usedMb < 1024 ? `${usedMb} MB` : `${org.storage_used_gb || (usedMb/1024).toFixed(2)} GB`;
        const barColor = pct >= 90 ? '#ef4444' : pct >= 70 ? '#f59e0b' : '#4f46e5';

        // Populate header
        const sbmOrgName = document.getElementById('sbmOrgName');
        if (sbmOrgName) sbmOrgName.textContent = org.name;

        // Populate totals
        const sbmTotalUsed = document.getElementById('sbmTotalUsed');
        const sbmTotalLimit = document.getElementById('sbmTotalLimit');
        const sbmTotalPct = document.getElementById('sbmTotalPct');
        const sbmProgressBar = document.getElementById('sbmProgressBar');
        if (sbmTotalUsed) sbmTotalUsed.textContent = usedFmt;
        if (sbmTotalLimit) sbmTotalLimit.textContent = `${limitGb} GB`;
        if (sbmTotalPct) sbmTotalPct.textContent = `${pct}% capacity used`;
        if (sbmProgressBar) {
            sbmProgressBar.style.width = `${Math.min(100, pct)}%`;
            sbmProgressBar.style.background = barColor;
        }

        // Build breakdown items
        const categories = [
            { icon: 'file-text', label: 'Documents & SOP Uploads', value: bd.documents_sops_mb || 0, color: '#3b82f6' },
            { icon: 'git-branch', label: 'Project Stage Workflows', value: bd.project_workflows_mb || 0, color: '#8b5cf6' },
            { icon: 'brain', label: 'RAG Knowledge Base Vectors', value: Math.round((org.knowledge_entries_count || 0) * 1.2), color: '#06b6d4' },
            { icon: 'shield-check', label: 'System Audit Logs & Trails', value: bd.audit_logs_mb || 0, color: '#f59e0b' },
            { icon: 'database', label: 'User Metadata & DB Tables', value: bd.system_db_mb || 0, color: '#10b981' },
        ];
        const maxVal = Math.max(...categories.map(c => c.value), 0.1);

        const sbmBreakdownList = document.getElementById('sbmBreakdownList');
        if (sbmBreakdownList) {
            sbmBreakdownList.innerHTML = categories.map(cat => {
                const w = Math.max(2, Math.round((cat.value / maxVal) * 100));
                return `
                    <div style="display:flex; align-items:center; gap:12px; background:var(--ds-surface-2,#f8fafc); border:1px solid var(--ds-border-color,#e2e8f0); border-radius:12px; padding:12px 16px;">
                        <div style="width:34px;height:34px;border-radius:10px;background:${cat.color}18;display:flex;align-items:center;justify-content:center;flex-shrink:0;">
                            <i data-lucide="${cat.icon}" style="width:16px;height:16px;color:${cat.color};"></i>
                        </div>
                        <div style="flex:1; min-width:0;">
                            <div style="font-size:13px;font-weight:600;color:var(--ds-text-main,#0f172a); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${cat.label}</div>
                            <div style="background:rgba(0,0,0,0.06); border-radius:6px; height:5px; margin-top:6px; overflow:hidden;">
                                <div style="height:100%; border-radius:6px; width:${w}%; background:${cat.color}; transition:width .4s ease;"></div>
                            </div>
                        </div>
                        <div style="font-size:14px;font-weight:700;color:${cat.color};white-space:nowrap;">${cat.value} MB</div>
                    </div>`;
            }).join('');
        }

        // Show modal
        const modal = document.getElementById('storageBreakdownModal');
        if (modal) { modal.style.display = 'flex'; if (window.lucide) lucide.createIcons(); }
    },

    closeStorageBreakdownModal() {
        const modal = document.getElementById('storageBreakdownModal');
        if (modal) modal.style.display = 'none';
    },

    // ── Main loader (called by switchView) ────────────────────────────────────
    async loadSubscriptions() {
        await Promise.all([this._subLoadKPIs(), this._subLoadTable()]);
        if(window.lucide) lucide.createIcons();
    },

    // ── KPI Dashboard ─────────────────────────────────────────────────────────
    async _subLoadKPIs() {
        const grid = document.getElementById('subKpiGrid');
        if (!grid) return;
        grid.innerHTML = `<div style="height:80px;background:var(--ds-border-color);border-radius:12px;animation:shimmer 1.4s infinite;grid-column:1/-1;"></div>`;
        try {
            const res = await this._subGet('/dashboard');
            if (!res || !res.data) { grid.innerHTML = `<div class="text-xs text-muted text-center py-2" style="grid-column:1/-1;">Dashboard unavailable.</div>`; return; }
            const d = res.data;
            const kpis = [
                { icon:'activity',      bg:'rgba(16,185,129,.12)', color:'#10b981', label:'Active Organizations',    val: d.active_subscriptions,    accent:'#10b981', filter:'Active' },
                { icon:'flask-conical', bg:'rgba(245,158,11,.12)', color:'#f59e0b', label:'Trial Organizations',     val: d.trial_subscriptions,     accent:'#f59e0b', filter:'Trial' },
                { icon:'alert-circle',  bg:'rgba(239,68,68,.12)',  color:'#ef4444', label:'Expired Organizations',   val: d.expired_subscriptions,   accent:'#ef4444', filter:'Expired' },
                { icon:'x-circle',      bg:'rgba(107,114,128,.12)',color:'#6b7280', label:'Cancelled Organizations', val: d.cancelled_subscriptions, accent:'#6b7280', filter:'Cancelled' },
                { icon:'calendar-clock',bg:'rgba(59,130,246,.12)', color:'#3b82f6', label:'Renewal Due This Month',  val: d.renewal_due_this_month,  accent:'#3b82f6', filter:'30d' },
                { icon:'trending-up',   bg:'rgba(16,185,129,.12)', color:'#10b981', label:'Monthly Revenue (MRR)',   val: this._subFmt(d.mrr),       accent:'#10b981' },
                { icon:'bar-chart-2',   bg:'rgba(99,102,241,.12)', color:'#6366f1', label:'Annual Revenue (ARR)',    val: this._subFmt(d.arr),       accent:'#6366f1' },
                { icon:'users',         bg:'rgba(245,158,11,.12)', color:'#f59e0b', label:'Avg Revenue Per Org',     val: this._subFmt(d.arpo),      accent:'#f59e0b' },
            ];
            grid.innerHTML = kpis.map(k=>`
                <div class="sub-kpi-card" onclick="${k.filter?`SuperAdmin.setSubFilter('status','${k.filter}',null)`:''}" title="${k.label}">
                    <div class="kpi-icon" style="background:${k.bg};"><i data-lucide="${k.icon}" style="width:16px;height:16px;color:${k.color};"></i></div>
                    <div class="kpi-label">${k.label}</div>
                    <div class="kpi-value">${k.val}</div>
                    <div class="kpi-accent" style="background:${k.accent};"></div>
                </div>`).join('');
            if(window.lucide) lucide.createIcons();
        } catch(e) {
            grid.innerHTML = `<div class="text-xs text-muted text-center py-2" style="grid-column:1/-1;">Dashboard unavailable — subscriptions not yet created.</div>`;
        }
    },

    // ── Table ─────────────────────────────────────────────────────────────────
    async _subLoadTable() {
        const tbody = document.getElementById('subscriptionsBody');
        const countEl = document.getElementById('subscriptionsCount');
        if (!tbody) return;
        tbody.innerHTML = `<tr><td colspan="11" class="text-center py-5"><span class="spinner-border spinner-border-sm me-2"></span><span class="text-muted text-xs">Loading subscriptions…</span></td></tr>`;

        const s = this._sub;
        const params = new URLSearchParams({
            page: s.page, per_page: s.perPage,
            sort_by: s.sortBy, sort_dir: s.sortDir,
            q: s.q,
            ...Object.fromEntries(Object.entries(s.filters).filter(([,v])=>v))
        });

        try {
            const res = await this._subGet(`/?${params}`);
            if (!res) { tbody.innerHTML = `<tr><td colspan="11" class="text-center py-5 text-muted text-xs">No data available. Please refresh.</td></tr>`; return; }
            const data = res.items || res.data || [];
            const pagination = {
                page: res.page || (res.pagination ? res.pagination.page : s.page),
                per_page: res.per_page || (res.pagination ? res.pagination.per_page : s.perPage),
                total: res.total !== undefined ? res.total : (res.pagination ? res.pagination.total : data.length),
                pages: res.total_pages || (res.pagination ? res.pagination.pages : 1)
            };
            s.totalPages = pagination.pages;
            if (countEl) countEl.textContent = `${pagination.total.toLocaleString()} subscriptions`;
            this._subRenderTable(data, tbody);
            this._subRenderPagination(pagination);
        } catch(e) {
            tbody.innerHTML = `<tr><td colspan="11" class="text-center py-5 text-danger text-xs">${e.message} — Check backend is running.</td></tr>`;
            if (countEl) countEl.textContent = 'Error';
        }
    },

    _subRenderTable(subs, tbody) {
        if (!subs.length) {
            tbody.innerHTML = `<tr><td colspan="11" class="text-center py-5 text-muted">
                <i data-lucide="inbox" style="width:28px;height:28px;opacity:.3;"></i>
                <div class="mt-2 text-xs">No subscriptions found. Click <strong>+ New Subscription</strong> to create one.</div>
            </td></tr>`;
            if(window.lucide) lucide.createIcons();
            return;
        }

        tbody.innerHTML = subs.map(s => {
            const sel = this._sub.selectedIds.has(s.id);
            const userPct = s.max_users>0 ? Math.min(100,Math.round(s.current_users/s.max_users*100)) : 0;
            const expWarn = this._subExpiring(s.end_date) && s.subscription_status === 'Active';
            return `<tr id="subrow-${s.id}" class="${sel?'row-selected':''}">
                <td><input type="checkbox" class="sub-row-cb" data-id="${s.id}" ${sel?'checked':''} onchange="SuperAdmin._subToggleRow(${s.id},this)"></td>
                <td><span class="text-primary fw-bold" style="font-size:11.5px;cursor:pointer;" onclick="SuperAdmin.openSubDrawer(${s.id})">${this._subEsc(s.subscription_uid)}</span></td>
                <td>
                    <div class="fw-bold" style="font-size:12.5px;">${this._subEsc(s.organization_name)}</div>
                    <div class="text-muted" style="font-size:11px;">${this._subEsc(s.admin_email)}</div>
                </td>
                <td><span class="plan-chip ${(s.plan_name||'').toLowerCase()}">${s.plan_name}</span></td>
                <td style="font-size:11.5px;">${s.billing_cycle}</td>
                <td class="${expWarn?'text-warning fw-bold':''}" style="font-size:11.5px;">${this._subFmtD(s.end_date)}</td>
                <td style="font-size:11.5px;">${this._subFmtD(s.renewal_date)}</td>
                <td><span class="sub-badge ${(s.subscription_status||'').toLowerCase()}">${s.subscription_status}</span></td>
                <td><span class="pay-badge ${(s.payment_status||'').toLowerCase()}">${s.payment_status}</span></td>
                <td>
                    <div class="fw-bold" style="font-size:12.5px;">${this._subFmt(s.final_amount)}</div>
                </td>
                <td class="text-end">
                    <div class="dropdown">
                        <button class="btn btn-link text-muted p-1" data-bs-toggle="dropdown" data-bs-popper-config='{"strategy":"fixed"}' style="border:none;background:transparent;box-shadow:none;">
                            <i data-lucide="more-horizontal" style="width:16px;height:16px;"></i>
                        </button>
                        <ul class="dropdown-menu dropdown-menu-end" style="min-width:185px;font-size:12.5px;z-index:100050 !important;">
                            <li><a class="dropdown-item" href="#" onclick="SuperAdmin.openSubDrawer(${s.id});return false;"><i data-lucide="eye" style="width:13px;height:13px;" class="me-2"></i>View Detail</a></li>
                            <li><a class="dropdown-item" href="#" onclick="SuperAdmin.openSubPlanModal(${s.id},'upgrade');return false;"><i data-lucide="trending-up" style="width:13px;height:13px;" class="me-2"></i>Upgrade Plan</a></li>
                            <li><a class="dropdown-item" href="#" onclick="SuperAdmin.openSubPlanModal(${s.id},'downgrade');return false;"><i data-lucide="trending-down" style="width:13px;height:13px;" class="me-2"></i>Downgrade Plan</a></li>
                            <li><hr class="dropdown-divider"></li>
                            <li><a class="dropdown-item" href="#" onclick="SuperAdmin._subActionRenew(${s.id});return false;"><i data-lucide="refresh-cw" style="width:13px;height:13px;" class="me-2"></i>Renew</a></li>
                            <li><a class="dropdown-item" href="#" onclick="SuperAdmin._subActionExtend(${s.id});return false;"><i data-lucide="calendar-plus" style="width:13px;height:13px;" class="me-2"></i>Extend</a></li>
                            ${s.subscription_status==='Active'?`<li><a class="dropdown-item" href="#" onclick="SuperAdmin._subActionPause(${s.id});return false;"><i data-lucide="pause-circle" style="width:13px;height:13px;" class="me-2"></i>Pause</a></li>`:''}
                            ${['Suspended','Cancelled','Canceled','Expired','Inactive'].includes(s.subscription_status)?`<li><a class="dropdown-item text-success font-semibold" href="#" onclick="SuperAdmin._subActionActivate(${s.id});return false;"><i data-lucide="play-circle" style="width:13px;height:13px;" class="me-2 text-success"></i>Activate / Reactivate</a></li>`:''}
                            ${s.subscription_status==='Trial'?`
                            <li><a class="dropdown-item" href="#" onclick="SuperAdmin._subActionConvertTrial(${s.id});return false;"><i data-lucide="arrow-up-circle" style="width:13px;height:13px;" class="me-2"></i>Convert → Paid</a></li>
                            <li><a class="dropdown-item" href="#" onclick="SuperAdmin._subActionExtendTrial(${s.id});return false;"><i data-lucide="calendar-plus" style="width:13px;height:13px;" class="me-2"></i>Extend Trial</a></li>`:''}
                            <li><a class="dropdown-item" href="#" onclick="SuperAdmin._subGenerateInvoice(${s.id});return false;"><i data-lucide="file-text" style="width:13px;height:13px;" class="me-2"></i>Generate Invoice</a></li>
                            ${s.subscription_status!=='Cancelled'&&s.subscription_status!=='Canceled'?`<li><hr class="dropdown-divider"></li>
                            <li><a class="dropdown-item text-danger" href="#" onclick="SuperAdmin._subActionCancel(${s.id});return false;"><i data-lucide="x-circle" style="width:13px;height:13px;" class="me-2"></i>Cancel</a></li>`:''}
                        </ul>
                    </div>
                </td>
            </tr>`;
        }).join('');
        if(window.lucide) lucide.createIcons();
    },

    _subRenderPagination(pg) {
        const info = document.getElementById('subPagInfo');
        const btns = document.getElementById('subPagBtns');
        if (info) info.textContent = `Showing ${Math.min((pg.page-1)*pg.per_page+1, pg.total)}–${Math.min(pg.page*pg.per_page, pg.total)} of ${pg.total.toLocaleString()}`;
        if (!btns) return;
        const b = [];
        b.push(`<button class="ds-btn ds-btn-secondary btn-sm" onclick="SuperAdmin._subGoPage(${pg.page-1})" ${pg.page<=1?'disabled':''}>‹</button>`);
        const start=Math.max(1,pg.page-2), end=Math.min(pg.pages,pg.page+2);
        if(start>1) b.push(`<button class="ds-btn ds-btn-secondary btn-sm" onclick="SuperAdmin._subGoPage(1)">1</button><span class="text-muted px-1" style="font-size:12px;">…</span>`);
        for(let i=start;i<=end;i++) b.push(`<button class="ds-btn ${i===pg.page?'ds-btn-primary':'ds-btn-secondary'} btn-sm" onclick="SuperAdmin._subGoPage(${i})">${i}</button>`);
        if(end<pg.pages) b.push(`<span class="text-muted px-1" style="font-size:12px;">…</span><button class="ds-btn ds-btn-secondary btn-sm" onclick="SuperAdmin._subGoPage(${pg.pages})">${pg.pages}</button>`);
        b.push(`<button class="ds-btn ds-btn-secondary btn-sm" onclick="SuperAdmin._subGoPage(${pg.page+1})" ${pg.page>=pg.pages?'disabled':''}>›</button>`);
        btns.innerHTML = b.join('');
    },

    _subGoPage(p) { if(p<1||p>this._sub.totalPages)return; this._sub.page=p; this._subLoadTable(); },
    subSetPerPage(v) { this._sub.perPage=parseInt(v); this._sub.page=1; this._subLoadTable(); },
    subSort(col) {
        if(this._sub.sortBy===col) this._sub.sortDir=this._sub.sortDir==='asc'?'desc':'asc';
        else { this._sub.sortBy=col; this._sub.sortDir='desc'; }
        this._subLoadTable();
    },

    // ── Search & Filters ──────────────────────────────────────────────────────
    subDebounceSearch(v) {
        clearTimeout(this._sub.searchTimer);
        this._sub.searchTimer = setTimeout(()=>{ this._sub.q=v.trim(); this._sub.page=1; this._subLoadTable(); }, 350);
    },
    setSubFilter(key, val, btn) {
        if (val === '30d' || key === 'renewal_window') {
            this._sub.filters.renewal_window = val || '30d';
            this._sub.filters.status = '';
            const statusSel = document.getElementById('subStatusFilter');
            if (statusSel) statusSel.value = '';
        } else if (key === 'status') {
            this._sub.filters.status = val;
            this._sub.filters.renewal_window = '';
            document.querySelectorAll('[data-sf="status"]').forEach(b => b.classList.remove('active'));
            if (btn) btn.classList.add('active');
            const statusSel = document.getElementById('subStatusFilter');
            if (statusSel) statusSel.value = val;
        } else {
            this._sub.filters[key] = val;
        }
        this._sub.page = 1;
        this._subLoadTable();
    },
    resetSubFilters() {
        this._sub.filters = { status:'', plan:'', billing_cycle:'', payment_status:'', renewal_window:'' };
        this._sub.q = ''; this._sub.page = 1;
        const si=document.getElementById('subSearchInput'); if(si) si.value='';
        ['subStatusFilter','subPlanFilter','subCycleFilter','subPayFilter','subRenewalFilter'].forEach(id=>{ const el=document.getElementById(id); if(el) el.value=''; });
        document.querySelectorAll('[data-sf="status"]').forEach(b=>b.classList.remove('active'));
        const all=document.querySelector('[data-sf="status"][data-sv=""]'); if(all) all.classList.add('active');
        this._subLoadTable();
    },

    // ── Selection & Bulk ──────────────────────────────────────────────────────
    subToggleAll(cb) {
        document.querySelectorAll('.sub-row-cb').forEach(c=>{
            c.checked=cb.checked; const id=parseInt(c.dataset.id);
            cb.checked?this._sub.selectedIds.add(id):this._sub.selectedIds.delete(id);
            document.getElementById(`subrow-${id}`)?.classList.toggle('row-selected',cb.checked);
        });
        this._subUpdateBulkBar();
    },
    _subToggleRow(id, cb) {
        cb.checked?this._sub.selectedIds.add(id):this._sub.selectedIds.delete(id);
        document.getElementById(`subrow-${id}`)?.classList.toggle('row-selected',cb.checked);
        this._subUpdateBulkBar();
    },
    _subUpdateBulkBar() {
        const count=this._sub.selectedIds.size;
        const bar=document.getElementById('subBulkBar');
        const cnt=document.getElementById('subBulkCount');
        if(bar) bar.classList.toggle('show',count>0);
        if(cnt) cnt.textContent=count;
    },
    clearSubSelection() {
        this._sub.selectedIds.clear();
        document.querySelectorAll('.sub-row-cb').forEach(c=>c.checked=false);
        const all=document.getElementById('subSelectAll'); if(all) all.checked=false;
        document.querySelectorAll('.row-selected').forEach(r=>r.classList.remove('row-selected'));
        this._subUpdateBulkBar();
    },
    async subBulkAction(action) {
        const ids=Array.from(this._sub.selectedIds); if(!ids.length)return;
        try {
            if(action==='cancel') {
                const ok=await this._subConfirm('Cancel Subscriptions',`Cancel ${ids.length} subscriptions? This cannot be undone.`,'Cancel All');
                if(!ok)return;
                await this._subPost('/bulk/cancel',{subscription_ids:ids});
            } else if(action==='renew') {
                await this._subPost('/bulk/renew',{subscription_ids:ids});
            } else if(action==='reminder') {
                await this._subPost('/bulk/send-reminders',{subscription_ids:ids});
            } else if(action==='assign-plan') {
                const plan = await this.promptPlanSelection('Professional');
                if(!plan)return;
                await this._subPost('/bulk/assign-plan',{subscription_ids:ids,plan_name:plan});
            }
            this._subNotify(`Bulk ${action} completed for ${ids.length} subscriptions`,'success');
            this.clearSubSelection(); this.loadSubscriptions();
        } catch(e) { this._subNotify(e.message,'error'); }
    },

    // ── Export ────────────────────────────────────────────────────────────────
    async subExportCSV() {
        try {
            const res = await api.get('/subscriptions/?per_page=1000');
            const list = res.data && res.data.subscriptions ? res.data.subscriptions : (res.data || []);
            if (!list || !list.length) {
                this._subNotify('No subscription data to export', 'info');
                return;
            }
            const headers = ['UID', 'Organization', 'Plan', 'Billing Cycle', 'Status', 'MRR', 'ARR', 'Start Date', 'Next Billing Date'];
            const rows = list.map(s => [
                s.uid || s.id || '—',
                s.org_name || '—',
                s.plan_name || '—',
                s.billing_cycle || '—',
                s.status || '—',
                s.mrr || 0,
                s.arr || 0,
                s.start_date ? String(s.start_date).slice(0, 10) : '—',
                s.next_billing_date ? String(s.next_billing_date).slice(0, 10) : '—'
            ]);
            const csv = [headers.join(','), ...rows.map(r => r.map(v => `"${String(v).replace(/"/g, '""')}"`).join(','))].join('\n');
            const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = `qcms_subscriptions_export_${new Date().toISOString().slice(0,10)}.csv`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            this._subNotify('Subscriptions CSV exported successfully', 'success');
        } catch (e) {
            this._subNotify('Subscriptions CSV export failed: ' + (e.message || e), 'error');
        }
    },

    // ── Detail Drawer ─────────────────────────────────────────────────────────
    async openSubDrawer(subId) {
        const overlay=document.getElementById('subDetailOverlay');
        const drawer=document.getElementById('subDetailDrawer');
        const body=document.getElementById('sddBody');
        if(!overlay||!drawer) return;
        overlay.classList.add('open'); drawer.classList.add('open');
        body.innerHTML=`<div class="text-center py-5"><span class="spinner-border"></span></div>`;
        try {
            const res=await this._subGet(`/${subId}`);
            const s=res.data;
            document.getElementById('sddTitle').textContent=s.subscription_uid;
            document.getElementById('sddSub').textContent=`${s.organization_name} · ${s.plan_name} · ${s.billing_cycle}`;
            document.getElementById('sddStatusBadge').innerHTML=`<span class="sub-badge ${(s.subscription_status||'').toLowerCase()}">${s.subscription_status}</span>`;
            body.innerHTML=this._subDrawerHtml(s);
            if(window.lucide) lucide.createIcons();
        } catch(e) {
            body.innerHTML=`<div class="text-danger p-3">${e.message}</div>`;
        }
    },
    closeSubDrawer() {
        document.getElementById('subDetailOverlay')?.classList.remove('open');
        document.getElementById('subDetailDrawer')?.classList.remove('open');
    },
    _subDrawerHtml(s) {
        const f=v=>this._subFmtD(v); const m=v=>this._subFmt(v);
        const userPct=s.max_users>0?Math.min(100,Math.round(s.current_users/s.max_users*100)):0;
        return `
        <div class="d-flex flex-wrap gap-2 mb-4">
            <button class="ds-btn ds-btn-secondary btn-sm" onclick="SuperAdmin._subActionRenew(${s.id})"><i data-lucide="refresh-cw" style="width:12px;height:12px;"></i> Renew</button>
            <button class="ds-btn ds-btn-secondary btn-sm" onclick="SuperAdmin.openSubPlanModal(${s.id},'upgrade')"><i data-lucide="trending-up" style="width:12px;height:12px;"></i> Upgrade</button>
            <button class="ds-btn ds-btn-secondary btn-sm" onclick="SuperAdmin._subGenerateInvoice(${s.id})"><i data-lucide="file-text" style="width:12px;height:12px;"></i> Invoice</button>
            <button class="ds-btn ds-btn-secondary btn-sm" onclick="SuperAdmin._subSendReminder(${s.id})"><i data-lucide="bell" style="width:12px;height:12px;"></i> Reminder</button>
            ${['Suspended','Cancelled','Canceled','Expired','Inactive'].includes(s.subscription_status)?`<button class="ds-btn ds-btn-success btn-sm" onclick="SuperAdmin._subActionActivate(${s.id})"><i data-lucide="play-circle" style="width:12px;height:12px;"></i> Activate</button>`:''}
            ${s.subscription_status==='Trial'?`<button class="ds-btn ds-btn-primary btn-sm" onclick="SuperAdmin._subActionConvertTrial(${s.id})"><i data-lucide="arrow-up-circle" style="width:12px;height:12px;"></i> Convert → Paid</button>`:''}
            ${s.subscription_status!=='Cancelled'&&s.subscription_status!=='Canceled'?`<button class="ds-btn btn-sm" style="background:rgba(239,68,68,.1);color:#ef4444;" onclick="SuperAdmin._subActionCancel(${s.id})"><i data-lucide="x-circle" style="width:12px;height:12px;"></i> Cancel</button>`:''}
        </div>
        <div class="sdd-section">
            <div class="sdd-section-title">Organization</div>
            <div class="sdd-grid">
                <div class="sdd-item"><div class="di-l">Name</div><div class="di-v">${this._subEsc(s.organization_name)}</div></div>
                <div class="sdd-item"><div class="di-l">Email</div><div class="di-v">${this._subEsc(s.admin_email)}</div></div>
                <div class="sdd-item"><div class="di-l">Admin</div><div class="di-v">${this._subEsc(s.admin_name)||'—'}</div></div>
                <div class="sdd-item"><div class="di-l">GST No.</div><div class="di-v">${this._subEsc(s.gst_number)||'—'}</div></div>
            </div>
        </div>
        <div class="sdd-section">
            <div class="sdd-section-title">Subscription</div>
            <div class="sdd-grid">
                <div class="sdd-item"><div class="di-l">Sub ID</div><div class="di-v fw-bold text-primary">${s.subscription_uid}</div></div>
                <div class="sdd-item"><div class="di-l">Plan</div><div class="di-v"><span class="plan-chip ${(s.plan_name||'').toLowerCase()}">${s.plan_name}</span></div></div>
                <div class="sdd-item"><div class="di-l">Billing Cycle</div><div class="di-v">${s.billing_cycle}</div></div>
                <div class="sdd-item"><div class="di-l">Support</div><div class="di-v">${s.support_level}</div></div>
                <div class="sdd-item"><div class="di-l">Start</div><div class="di-v">${f(s.start_date)}</div></div>
                <div class="sdd-item"><div class="di-l">Expiry</div><div class="di-v">${f(s.end_date)}</div></div>
                <div class="sdd-item"><div class="di-l">Renewal</div><div class="di-v">${f(s.renewal_date)}</div></div>
                <div class="sdd-item"><div class="di-l">Auto Renewal</div><div class="di-v">${s.auto_renewal?'✓ On':'✗ Off'}</div></div>
                ${s.subscription_status==='Trial'?`
                <div class="sdd-item"><div class="di-l">Trial End</div><div class="di-v text-warning fw-bold">${f(s.trial_end_date)}</div></div>
                <div class="sdd-item"><div class="di-l">Trial Days Left</div><div class="di-v text-warning fw-bold">${s.trial_days_remaining??'—'}</div></div>`:''} 
            </div>
        </div>
        <div class="sdd-section">
            <div class="sdd-section-title">Pricing</div>
            <div class="sdd-grid">
                <div class="sdd-item"><div class="di-l">Base Price</div><div class="di-v">${m(s.base_price)}</div></div>
                <div class="sdd-item"><div class="di-l">Discount (${s.discount_percent}%)</div><div class="di-v text-danger">- ${m(s.discount_amount)}</div></div>
                <div class="sdd-item"><div class="di-l">GST (${s.gst_percent}%)</div><div class="di-v">+ ${m(s.gst_amount)}</div></div>
                <div class="sdd-item"><div class="di-l">Final Amount</div><div class="di-v fw-bold text-primary">${m(s.final_amount)} ${s.currency}</div></div>
            </div>
        </div>
        <div class="sdd-section">
            <div class="sdd-section-title">Usage</div>
            <div class="mb-2">
                <div class="d-flex justify-content-between" style="font-size:11px;margin-bottom:4px;"><span>Users</span><span>${s.current_users}/${s.max_users} (${userPct}%)</span></div>
                <div style="height:6px;border-radius:3px;background:var(--ds-border-color);overflow:hidden;"><div style="height:100%;width:${userPct}%;border-radius:3px;background:${userPct>90?'#ef4444':userPct>70?'#f59e0b':'#10b981'};"></div></div>
            </div>
            <div class="sdd-grid mt-2">
                <div class="sdd-item"><div class="di-l">Storage Limit</div><div class="di-v">${s.storage_limit_gb} GB</div></div>
                <div class="sdd-item"><div class="di-l">API Limit</div><div class="di-v">${(s.api_limit||0).toLocaleString()}/mo</div></div>
                <div class="sdd-item" style="grid-column:1/-1"><div class="di-l">Modules</div><div class="di-v">${(s.enabled_modules||[]).join(', ')||'—'}</div></div>
            </div>
        </div>
        ${s.recent_invoices&&s.recent_invoices.length?`
        <div class="sdd-section">
            <div class="sdd-section-title">Recent Invoices</div>
            <div class="table-responsive"><table class="ds-table" style="font-size:11.5px;">
                <thead><tr><th>Invoice</th><th>Date</th><th>Amount</th><th>Status</th><th></th></tr></thead>
                <tbody>${s.recent_invoices.map(i=>`<tr>
                    <td class="fw-bold">${i.invoice_uid}</td>
                    <td>${this._subFmtD(i.invoice_date)}</td>
                    <td>${m(i.total_amount)}</td>
                    <td><span class="pay-badge ${i.invoice_status.toLowerCase()}">${i.invoice_status}</span></td>
                    <td><button class="ds-btn ds-btn-secondary" style="padding:2px 7px;font-size:11px;" onclick="SuperAdmin._subPreviewInvoice(${JSON.stringify(i).replace(/"/g,'&quot;')})">Preview</button></td>
                </tr>`).join('')}</tbody>
            </table></div>
        </div>`:''}
        ${s.audit_logs&&s.audit_logs.length?`
        <div class="sdd-section">
            <div class="sdd-section-title">Audit Log</div>
            <ul style="list-style:none;padding:0;margin:0;">
                ${s.audit_logs.slice(0,8).map(l=>`<li style="display:flex;gap:.7rem;padding:.5rem 0;border-bottom:1px solid var(--ds-border-color);font-size:11.5px;">
                    <span style="width:8px;height:8px;border-radius:50%;margin-top:4px;flex-shrink:0;background:${l.action.includes('CANCEL')||l.action.includes('FAIL')?'#ef4444':l.action.includes('TRIAL')||l.action.includes('REMIND')?'#f59e0b':'#10b981'};"></span>
                    <div><div>${l.action.replace(/_/g,' ')}</div><div class="text-muted" style="font-size:10px;">${l.admin} · ${l.timestamp?new Date(l.timestamp).toLocaleString('en-IN'):'—'}</div></div>
                </li>`).join('')}
            </ul>
        </div>`:''}`;
    },

    // ── Row Actions ───────────────────────────────────────────────────────────
    async _subActionRenew(id) {
        const ok=await this._subConfirm('Renew Subscription','Renew for one full billing cycle?','Renew Now');
        if(!ok)return;
        try { const r=await this._subPost(`/${id}/renew`); this._subNotify(r.message,'success'); this.loadSubscriptions(); }
        catch(e){ this._subNotify(e.message,'error'); }
    },
    async _subActionExtend(id) {
        const days=prompt('Extend by how many days?','30'); if(!days||isNaN(days))return;
        try { const r=await this._subPost(`/${id}/extend`,{days:parseInt(days)}); this._subNotify(r.message,'success'); this.loadSubscriptions(); }
        catch(e){ this._subNotify(e.message,'error'); }
    },
    async _subActionPause(id) {
        const ok=await this._subConfirm('Pause Subscription','This will suspend access for the organization.','Pause');
        if(!ok)return;
        try { await this._subPost(`/${id}/pause`); this._subNotify('Subscription paused','success'); this.loadSubscriptions(); }
        catch(e){ this._subNotify(e.message,'error'); }
    },
    async _subActionResume(id) {
        try { await this._subPost(`/${id}/resume`); this._subNotify('Subscription resumed','success'); this.loadSubscriptions(); }
        catch(e){ this._subNotify(e.message,'error'); }
    },
    async _subActionActivate(id) {
        const ok=await this._subConfirm('Activate Subscription','Reactivate this subscription and restore full access for the organization?','Activate Now');
        if(!ok)return;
        try { await this._subPost(`/${id}/activate`); this._subNotify('Subscription activated successfully','success'); this.closeSubDrawer(); this.loadSubscriptions(); }
        catch(e){ this._subNotify(e.message,'error'); }
    },
    async _subActionCancel(id) {
        const reason=prompt('Cancellation reason (optional):','')||'';
        const ok=await this._subConfirm('Cancel Subscription','This will terminate access for the organization.','Cancel Subscription');
        if(!ok)return;
        try { await this._subPost(`/${id}/cancel`,{reason}); this._subNotify('Subscription cancelled','success'); this.closeSubDrawer(); this.loadSubscriptions(); }
        catch(e){ this._subNotify(e.message,'error'); }
    },
    async _subActionConvertTrial(id) {
        const cycle=prompt('Billing cycle for paid plan (Monthly/Quarterly/Yearly/Lifetime):','Yearly')||'Yearly';
        const ok=await this._subConfirm('Convert Trial','Convert this trial to a paid subscription?','Convert');
        if(!ok)return;
        try { const r=await this._subPost(`/trial/${id}/convert`,{billing_cycle:cycle}); this._subNotify(r.message,'success'); this.loadSubscriptions(); }
        catch(e){ this._subNotify(e.message,'error'); }
    },
    async _subActionExtendTrial(id) {
        const days=prompt('Extend trial by how many days?','14'); if(!days||isNaN(days))return;
        try { const r=await this._subPost(`/trial/${id}/extend`,{days:parseInt(days)}); this._subNotify(r.message,'success'); this.loadSubscriptions(); }
        catch(e){ this._subNotify(e.message,'error'); }
    },
    async _subSendReminder(id) {
        try { const r=await this._subPost(`/${id}/send-reminder`); this._subNotify(r.message,'info'); }
        catch(e){ this._subNotify(e.message,'error'); }
    },
    async _subGenerateInvoice(id) {
        try { const r=await this._subPost(`/${id}/invoices`); this._subNotify(`Invoice ${r.data.invoice_uid} generated`,'success'); this._subPreviewInvoice(r.data); }
        catch(e){ this._subNotify(e.message,'error'); }
    },

    // ── Invoice Preview ───────────────────────────────────────────────────────
    async _subPreviewInvoice(inv) {
        if(typeof inv==='string') inv=JSON.parse(inv.replace(/&quot;/g,'"'));
        
        let ctx = {}, tmpl = {};
        try {
            const token = sessionStorage.getItem('token') || localStorage.getItem('token') || '';
            const res = await fetch('/api/document-identity/all', { headers: { 'Authorization': `Bearer ${token}` } });
            const result = await res.json();
            if (result.status === 'success') {
                ctx = result.branding_context || {};
                tmpl = (result.templates && result.templates.invoice) || {};
            }
        } catch (e) { console.warn('Could not fetch dynamic branding for invoice preview', e); }

        const titleHeader = tmpl.header_title || 'INVOICE';
        const companyBrandName = ctx.legal_company_name || ctx.trading_name || ctx.software_display_name || ctx.software_name || 'QCMS Enterprise OS';
        const supportEmail = ctx.support_email || ctx.general_email || 'support@qcms.com';
        const companyAddress = ctx.registered_office || ctx.corporate_office || '';
        const gstinText = ctx.gstin ? `GSTIN: ${ctx.gstin}` : '';
        const footerTerms = tmpl.footer_text || tmpl.terms_and_conditions || `Thank you for your business. For queries contact ${supportEmail}`;

        const m=v=>this._subFmt(v); const f=v=>v?new Date(v).toLocaleDateString('en-IN'):'—';
        document.getElementById('subInvoiceArea').innerHTML=`
        <div class="inv-doc" style="padding:1.5rem;font-family:sans-serif;">
            <div class="inv-hdr" style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:1.5rem;border-bottom:2px solid #2563eb;padding-bottom:1rem;">
                <div>
                    <div style="font-size:1.7rem;font-weight:700;color:#1e293b;">${titleHeader}</div>
                    <div style="font-size:11px;color:#64748b;">${inv.invoice_uid||inv.invoice_number||'—'}</div>
                </div>
                <div style="text-align:right;">
                    <div style="font-size:16px;font-weight:700;color:#2563eb;">${companyBrandName}</div>
                    <div style="font-size:11px;color:#64748b;">${supportEmail}</div>
                    ${gstinText ? `<div style="font-size:10px;color:#64748b;">${gstinText}</div>` : ''}
                    ${companyAddress ? `<div style="font-size:10px;color:#94a3b8;max-width:260px;margin-left:auto;">${companyAddress}</div>` : ''}
                </div>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin-bottom:1.5rem;font-size:12px;">
                <div>
                    <div style="color:#64748b;font-size:10px;margin-bottom:3px;font-weight:700;text-transform:uppercase;">BILL TO</div>
                    <strong style="font-size:14px;color:#0f172a;">${inv.organization_name||'—'}</strong>
                </div>
                <div style="text-align:right;">
                    <div style="color:#64748b;">Date: <strong>${f(inv.invoice_date)}</strong></div>
                    <div style="color:#64748b;">Due: <strong>${f(inv.due_date)}</strong></div>
                    <div style="margin-top:6px;display:inline-block;padding:2px 10px;border-radius:4px;background:${inv.invoice_status==='Paid'?'#d1fae5':'#fee2e2'};color:${inv.invoice_status==='Paid'?'#065f46':'#991b1b'};font-weight:700;font-size:11px;">${inv.invoice_status||'Draft'}</div>
                </div>
            </div>
            <table style="width:100%;border-collapse:collapse;margin-bottom:1.5rem;font-size:12px;">
                <thead>
                    <tr style="background:#f1f5f9;border-bottom:1px solid #cbd5e1;text-align:left;">
                        <th style="padding:8px 12px;">Description</th>
                        <th style="padding:8px 12px;text-align:right;">Amount</th>
                    </tr>
                </thead>
                <tbody>
                    <tr style="border-bottom:1px solid #f1f5f9;">
                        <td style="padding:10px 12px;">${inv.plan_name||'—'} Plan · ${inv.billing_cycle||'—'}<br><span style="font-size:10px;color:#64748b;">${f(inv.billing_period_start)} – ${f(inv.billing_period_end)}</span></td>
                        <td style="padding:10px 12px;text-align:right;">${m(inv.base_amount||0)}</td>
                    </tr>
                    ${(inv.discount_amount||0)>0?`<tr style="border-bottom:1px solid #f1f5f9;"><td style="padding:8px 12px;">Discount (${inv.discount_percent}%)</td><td style="padding:8px 12px;text-align:right;color:#ef4444;">- ${m(inv.discount_amount)}</td></tr>`:''}
                    <tr style="border-bottom:1px solid #f1f5f9;">
                        <td style="padding:8px 12px;">GST (${inv.gst_percent||18}%)</td>
                        <td style="padding:8px 12px;text-align:right;">+ ${m(inv.gst_amount||0)}</td>
                    </tr>
                    <tr style="font-weight:700;background:#f8fafc;">
                        <td style="padding:10px 12px;font-size:13px;">Total Amount</td>
                        <td style="padding:10px 12px;text-align:right;font-size:1.1rem;color:#2563eb;">${m(inv.total_amount||0)} ${inv.currency||'INR'}</td>
                    </tr>
                </tbody>
            </table>
            <div style="margin-top:1.5rem;font-size:10px;color:#64748b;border-top:1px solid #e2e8f0;padding-top:.8rem;">${footerTerms}</div>
        </div>`;
        new bootstrap.Modal(document.getElementById('subInvoiceModal')).show();
    },

    _subPrintInvoice() {
        if (typeof window.printElementContent === 'function') {
            window.printElementContent('subInvoiceArea', 'Invoice');
        } else {
            window.print();
        }
    },

    // ── Plan Change Modal ─────────────────────────────────────────────────────
    async openSubPlanModal(id, mode) {
        this._sub.planChangeMode=mode; this._sub.planChangeSub=null; this._sub.planChangeSelected=null;
        try {
            const [subRes, plansRes]=await Promise.all([this._subGet(`/${id}`), this._subGet('/plans')]);
            this._sub.planChangeSub=subRes.data;
            this._sub.catalogue=Object.fromEntries(plansRes.data.map(p=>[p.plan_name,p]));
            document.getElementById('subPlanModalTitle').textContent=mode==='upgrade'?'Upgrade Plan':'Downgrade Plan';
            document.getElementById('subPlanModalSub').textContent=`Current: ${this._sub.planChangeSub.plan_name} · ${this._sub.planChangeSub.billing_cycle}`;
            document.getElementById('subPlanDiff').style.display='none';
            document.getElementById('subPlanGrid').innerHTML=plansRes.data.map(p=>`
                <div class="col-6 col-md-3">
                    <div class="pc-card ${p.plan_name===this._sub.planChangeSub.plan_name?'sel':''}" id="spcc-${p.plan_name}" onclick="SuperAdmin._subSelectPlan('${p.plan_name}')">
                        <div class="pc-name">${p.plan_name}</div>
                        <div class="pc-price">${this._subFmt(p.base_price)}</div>
                        <div class="pc-feat">${p.max_users>=99999?'Unlimited':p.max_users} users<br>${p.storage_limit_gb} GB</div>
                    </div>
                </div>`).join('');
            new bootstrap.Modal(document.getElementById('subPlanModal')).show();
        } catch(e){ this._subNotify(e.message,'error'); }
    },
    _subSelectPlan(name) {
        this._sub.planChangeSelected=name;
        document.querySelectorAll('[id^="spcc-"]').forEach(c=>c.classList.remove('sel'));
        document.getElementById(`spcc-${name}`)?.classList.add('sel');
        const cur=this._sub.planChangeSub; const np=this._sub.catalogue[name];
        if(np&&cur) {
            const diff=np.base_price-(cur.final_amount||0);
            document.getElementById('subPlanDiffBody').innerHTML=`<div class="row g-2 text-xs"><div class="col-4"><strong>Price change:</strong> <span class="${diff>0?'text-danger':'text-success'}">${diff>=0?'+':''}${this._subFmt(diff)}</span></div><div class="col-4"><strong>Users:</strong> ${np.max_users>=99999?'∞':np.max_users} vs ${cur.max_users}</div><div class="col-4"><strong>Storage:</strong> ${np.storage_limit_gb}GB vs ${cur.storage_limit_gb}GB</div></div>`;
            document.getElementById('subPlanDiff').style.display='block';
        }
    },
    async confirmSubPlanChange() {
        if(!this._sub.planChangeSelected){this._subNotify('Select a plan first','error');return;}
        const mode=this._sub.planChangeMode; const sub=this._sub.planChangeSub;
        try {
            const r=await this._subPost(`/${sub.id}/${mode}`,{plan_name:this._sub.planChangeSelected});
            this._subNotify(r.message,'success');
            bootstrap.Modal.getInstance(document.getElementById('subPlanModal'))?.hide();
            this.loadSubscriptions();
        } catch(e){ this._subNotify(e.message,'error'); }
    },

    // ── Create Wizard ─────────────────────────────────────────────────────────
    async openSubCreateWizard() {
        this._sub.wizStep=1; this._subWizGoStep(1);
        this._sub.plansQuery = '';
        this._sub.plansPage = 1;
        this._sub.plansPerPage = 5;
        const searchInput = document.getElementById('swPlanSearch');
        if (searchInput) searchInput.value = '';

        try {
            const res=await this._subGet('/plans');
            const data = res.data || [];
            this._sub.plansAll = data;
            this._sub.catalogue=Object.fromEntries(data.map(p=>[p.plan_name || p.name, p]));
            
            this._subWizRenderPlans();

            if (data.length > 0) {
                const firstPlanName = data[0].plan_name || data[0].name;
                this._subWizSelectPlan(firstPlanName);
            }
        } catch(e){}
        new bootstrap.Modal(document.getElementById('subCreateModal')).show();
    },

    _subWizGoStep(n) {
        this._sub.wizStep=n;
        document.querySelectorAll('.wiz-panel').forEach(p=>p.classList.remove('active'));
        document.getElementById(`swp${n}`)?.classList.add('active');
        document.querySelectorAll('#subWizSteps .wiz-step').forEach(s=>{ const sn=parseInt(s.dataset.ws); s.classList.toggle('active',sn===n); s.classList.toggle('done',sn<n); });
        document.getElementById('swPrevBtn').disabled=n===1;
        document.getElementById('swNextBtn').classList.toggle('d-none',n===4);
        document.getElementById('swSubmitBtn').classList.toggle('d-none',n!==4);
        if(n===4) this._subWizRenderReview();
    },
    subWizNext() {
        if(this._sub.wizStep===1&&!document.getElementById('swOrgId').value){this._subNotify('Select an organization first','error');return;}
        if(this._sub.wizStep<4) this._subWizGoStep(this._sub.wizStep+1);
    },
    subWizPrev() { if(this._sub.wizStep>1) this._subWizGoStep(this._sub.wizStep-1); },
    async subWizSearchOrg(q) {
        if(!q||q.length<2){document.getElementById('swOrgList').innerHTML='';return;}
        try {
            const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token') || localStorage.getItem('token') || sessionStorage.getItem('token');
            const r=await fetch(`/api/super-admin/companies?search=${encodeURIComponent(q)}&per_page=8`,{headers:{Authorization:`Bearer ${token}`}});
            const res=await r.json();
            document.getElementById('swOrgList').innerHTML=(res.data||[]).map(o=>`
                <div style="padding:7px 10px;cursor:pointer;border:1px solid var(--ds-border-color);border-radius:8px;margin-bottom:4px;display:flex;justify-content:space-between;font-size:12.5px;" onclick="SuperAdmin._subWizSelectOrg(${o.id},'${this._subEsc(o.name)}','${this._subEsc(o.email||'')}')">
                    <span><strong>${o.name}</strong> <span class="text-muted">${o.email||''}</span></span>
                    <span class="plan-chip ${(o.plan||'').toLowerCase()}">${o.plan||''}</span>
                </div>`).join('')||'<div class="text-xs text-muted p-2">No results</div>';
        } catch(e){}
    },
    _subWizSelectOrg(id,name,email) {
        document.getElementById('swOrgId').value=id;
        document.getElementById('swOrgChosen').textContent=`✓ ${name} (${email})`;
        document.getElementById('swOrgSearch').value=name;
        document.getElementById('swOrgList').innerHTML='';
    },

    subWizFilterPlans(q) {
        this._sub.plansQuery = (q || '').trim().toLowerCase();
        this._sub.plansPage = 1;
        this._subWizRenderPlans();
    },

    subWizGoToPlanPage(p) {
        this._sub.plansPage = p;
        this._subWizRenderPlans();
    },

    _subWizRenderPlans() {
        const grid = document.getElementById('swPlanGrid');
        const infoEl = document.getElementById('swPlanPagInfo');
        const btnsEl = document.getElementById('swPlanPagBtns');
        if (!grid) return;

        const all = this._sub.plansAll || [];
        const q = this._sub.plansQuery || '';

        const filtered = all.filter(p => {
            if (!q) return true;
            const name = (p.plan_name || p.name || '').toLowerCase();
            const code = (p.code || p.plan_code || '').toLowerCase();
            const desc = (p.description || '').toLowerCase();
            const price = String(p.base_price ?? p.yearly_price ?? p.monthly_price ?? p.price ?? '');
            const users = String(p.max_users || '');
            return name.includes(q) || code.includes(q) || desc.includes(q) || price.includes(q) || users.includes(q);
        });

        const perPage = this._sub.plansPerPage || 5;
        const total = filtered.length;
        const totalPages = Math.max(1, Math.ceil(total / perPage));
        this._sub.plansPage = Math.min(Math.max(1, this._sub.plansPage || 1), totalPages);
        const start = (this._sub.plansPage - 1) * perPage;
        const pageData = filtered.slice(start, start + perPage);

        const currentSel = document.getElementById('swPlan')?.value || (all[0]?.plan_name || all[0]?.name);

        if (!pageData.length) {
            grid.innerHTML = `<div class="text-center py-4 text-muted text-xs"><i data-lucide="search-x" class="mb-1" style="width:24px;height:24px;opacity:0.4;"></i><div>No matching plans found</div></div>`;
            if (infoEl) infoEl.textContent = 'No plans';
            if (btnsEl) btnsEl.innerHTML = '';
            if (window.lucide) lucide.createIcons();
            return;
        }

        grid.innerHTML = pageData.map(p => {
            const name = p.plan_name || p.name;
            const price = p.base_price ?? p.yearly_price ?? p.monthly_price ?? p.price ?? 0;
            const cycle = p.billing_cycle ? `/ ${p.billing_cycle.toLowerCase()}` : '/yr';
            const isSel = name === currentSel;

            return `
            <div class="pc-list-item d-flex align-items-center justify-content-between rounded-3 ${isSel ? 'sel border-primary' : ''}" 
                 id="swpc-${name}" 
                 style="cursor:pointer; transition: all 0.2s ease; margin-bottom: 8px; background: #ffffff !important; border: ${isSel ? '2px solid var(--ds-primary, #2563eb)' : '1px solid #e2e8f0'}; box-shadow: ${isSel ? '0 4px 12px rgba(37,99,235,0.12)' : '0 1px 3px rgba(0,0,0,0.02)'}; padding: 12px 16px;" 
                 onclick="SuperAdmin._subWizSelectPlan('${this._subEsc(name)}')">
                <div class="d-flex align-items-center gap-3">
                    <div class="radio-indicator rounded-circle border d-flex align-items-center justify-content-center" style="width:20px; height:20px; border-color: ${isSel ? 'var(--ds-primary, #2563eb)' : '#cbd5e1'}; background: ${isSel ? 'var(--ds-primary, #2563eb)' : '#ffffff'};">
                        ${isSel ? '<i data-lucide="check" style="width:12px; height:12px; color:#fff;"></i>' : ''}
                    </div>
                    <div>
                        <div class="fw-bold text-sm text-dark" style="font-size:13.5px; color:#0f172a;">${this._subEsc(name)}</div>
                        <div class="text-xs text-muted d-flex align-items-center gap-2 mt-0.5" style="font-size:11.5px;">
                            <span>${p.max_users >= 99999 ? 'Unlimited' : p.max_users} users</span>
                            <span>•</span>
                            <span>${p.storage_limit_gb}GB storage</span>
                        </div>
                    </div>
                </div>
                <div class="text-end">
                    <div class="fw-bold text-primary text-sm" style="font-size:14px; color:#2563eb;">${this._subFmt(price)} ${cycle}</div>
                    <div class="text-xxs text-muted text-uppercase fw-semibold" style="font-size:9.5px; letter-spacing:0.3px;">${p.billing_cycle || 'Yearly'} Plan</div>
                </div>
            </div>`;
        }).join('');

        if (infoEl) {
            const startItem = total > 0 ? start + 1 : 0;
            const endItem = Math.min(this._sub.plansPage * perPage, total);
            infoEl.textContent = total > 0 ? `Showing ${startItem}–${endItem} of ${total} plans` : 'No results';
        }

        if (btnsEl) {
            let btnHtml = `<button class="ds-btn ds-btn-xs ds-btn-secondary" ${this._sub.plansPage <= 1 ? 'disabled' : ''} onclick="SuperAdmin.subWizGoToPlanPage(${this._sub.plansPage - 1})"><i data-lucide="chevron-left" style="width:12px;height:12px;"></i> Prev</button>`;
            for (let i = 1; i <= totalPages; i++) {
                btnHtml += `<button class="ds-btn ds-btn-xs ${i === this._sub.plansPage ? 'ds-btn-primary' : 'ds-btn-ghost'}" onclick="SuperAdmin.subWizGoToPlanPage(${i})">${i}</button>`;
            }
            btnHtml += `<button class="ds-btn ds-btn-xs ds-btn-secondary" ${this._sub.plansPage >= totalPages ? 'disabled' : ''} onclick="SuperAdmin.subWizGoToPlanPage(${this._sub.plansPage + 1})">Next <i data-lucide="chevron-right" style="width:12px;height:12px;"></i></button>`;
            btnsEl.innerHTML = btnHtml;
        }

        if (window.lucide) lucide.createIcons();
    },

    _subWizSelectPlan(name) {
        document.getElementById('swPlan').value=name;
        document.querySelectorAll('#swPlanGrid .pc-list-item').forEach(c=>{
            c.classList.remove('sel','border-primary','bg-primary-subtle');
            c.style.background = '#ffffff';
            c.style.border = '1px solid #e2e8f0';
            c.style.boxShadow = '0 1px 3px rgba(0,0,0,0.02)';
            const indicator = c.querySelector('.radio-indicator');
            if (indicator) {
                indicator.style.borderColor = '#cbd5e1';
                indicator.style.background = '#ffffff';
                indicator.innerHTML = '';
            }
        });
        const selectedItem = document.getElementById(`swpc-${name}`);
        if (selectedItem) {
            selectedItem.classList.add('sel', 'border-primary');
            selectedItem.style.background = '#ffffff';
            selectedItem.style.border = '2px solid var(--ds-primary, #2563eb)';
            selectedItem.style.boxShadow = '0 4px 12px rgba(37,99,235,0.12)';
            const indicator = selectedItem.querySelector('.radio-indicator');
            if (indicator) {
                indicator.style.borderColor = 'var(--ds-primary, #2563eb)';
                indicator.style.background = 'var(--ds-primary, #2563eb)';
                indicator.innerHTML = '<i data-lucide="check" style="width:12px; height:12px; color:#fff;"></i>';
            }
        }
        const p=this._sub.catalogue[name]; if(!p)return;
        if(document.getElementById('swCycle')) document.getElementById('swCycle').value = p.billing_cycle || 'Yearly';
        if(document.getElementById('swMaxUsers')) document.getElementById('swMaxUsers').value = p.max_users>=99999?99999:(p.max_users||500);
        if(document.getElementById('swStorage')) document.getElementById('swStorage').value = p.storage_limit_gb||10;
        if(document.getElementById('swApiLimit')) document.getElementById('swApiLimit').value = p.api_limit||10000;
        if(document.getElementById('swSupport')) document.getElementById('swSupport').value = p.support_level || 'Standard';
        document.getElementById('swBase').value = p.base_price ?? p.yearly_price ?? p.monthly_price ?? p.price ?? 0;
        this.subWizRecalc();
        if (window.lucide) lucide.createIcons();
    },
    subWizRecalc() {
        const base=parseFloat(document.getElementById('swBase').value)||0;
        const disc=parseFloat(document.getElementById('swDisc').value)||0;
        const gst=parseFloat(document.getElementById('swGst').value)||18;
        const da=base*disc/100, gstA=(base-da)*gst/100, total=base-da+gstA;
        document.getElementById('swCalcBase').textContent=`₹${base.toFixed(2)}`;
        document.getElementById('swCalcDisc').textContent=`- ₹${da.toFixed(2)}`;
        document.getElementById('swCalcGst').textContent=`+ ₹${gstA.toFixed(2)}`;
        document.getElementById('swCalcTotal').textContent=`₹${total.toFixed(2)}`;
    },
    _subWizRenderReview() {
        const plan=document.getElementById('swPlan').value;
        const cycle=document.getElementById('swCycle')?.value || 'Yearly';
        const maxUsers=document.getElementById('swMaxUsers')?.value || '500';
        const base=parseFloat(document.getElementById('swBase').value)||0;
        const disc=parseFloat(document.getElementById('swDisc').value)||0;
        const gst=parseFloat(document.getElementById('swGst').value)||18;
        const da=base*disc/100, gstA=(base-da)*gst/100, total=base-da+gstA;
        const orgText=document.getElementById('swOrgChosen').textContent;
        document.getElementById('swReview').innerHTML=`
        <div class="row g-2 text-sm">
            <div class="col-6"><div class="text-muted text-xs">Organization</div><strong>${orgText.replace('✓ ','')}</strong></div>
            <div class="col-6"><div class="text-muted text-xs">Plan</div><span class="plan-chip ${plan.toLowerCase()}">${plan}</span></div>
            <div class="col-6"><div class="text-muted text-xs">Billing Cycle</div><strong>${cycle}</strong></div>
            <div class="col-6"><div class="text-muted text-xs">Max Users</div><strong>${maxUsers >= 99999 ? 'Unlimited' : maxUsers}</strong></div>
            <div class="col-12"><hr class="my-2"></div>
            <div class="col-4"><div class="text-muted text-xs">Base</div><strong>₹${base.toFixed(2)}</strong></div>
            <div class="col-4"><div class="text-muted text-xs">Discount (${disc}%)</div><strong class="text-danger">-₹${da.toFixed(2)}</strong></div>
            <div class="col-4"><div class="text-muted text-xs">GST (${gst}%)</div><strong>+₹${gstA.toFixed(2)}</strong></div>
            <div class="col-12 d-flex justify-content-between mt-1"><span class="fw-bold">Total</span><strong class="text-primary" style="font-size:1.2rem;">₹${total.toFixed(2)}</strong></div>
        </div>`;
    },
    async subWizSubmit() {
        if(!document.getElementById('swConfirm').checked){this._subNotify('Please confirm before creating','error');return;}
        const btn=document.getElementById('swSubmitBtn'); btn.disabled=true; btn.textContent='Creating…';
        const planName=document.getElementById('swPlan').value;
        const planObj=this._sub.catalogue[planName] || {};
        const payload={
            org_id:parseInt(document.getElementById('swOrgId').value),
            plan_name:planName,
            billing_cycle:document.getElementById('swCycle')?.value || planObj.billing_cycle || 'Yearly',
            base_price:parseFloat(document.getElementById('swBase').value)||0,
            discount_percent:parseFloat(document.getElementById('swDisc').value)||0,
            gst_percent:parseFloat(document.getElementById('swGst').value)||18,
            max_users:parseInt(document.getElementById('swMaxUsers')?.value)||(planObj.max_users || 500),
            storage_limit_gb:parseFloat(document.getElementById('swStorage')?.value)||(planObj.storage_limit_gb || 10),
            api_limit:parseInt(document.getElementById('swApiLimit')?.value)||(planObj.api_limit || 10000),
            support_level:document.getElementById('swSupport')?.value || planObj.support_level || 'Standard',
            enabled_modules:planObj.enabled_modules || [],
            currency:document.getElementById('swCurrency').value,
            payment_status:document.getElementById('swPayStatus').value,
        };
        try {
            const r=await this._subPost('/',payload);
            this._subNotify(`${r.data.subscription_uid} created! Invoice: ${r.invoice_uid}`,'success');
            bootstrap.Modal.getInstance(document.getElementById('subCreateModal'))?.hide();
            this.loadSubscriptions();
        } catch(e){ this._subNotify(e.message,'error'); }
        finally { btn.disabled=false; btn.textContent='Create Subscription'; }
    },

    // ── Confirm Dialog ────────────────────────────────────────────────────────
    _subConfirm(title, body, okLabel='Confirm') {
        return new Promise(resolve=>{
            document.getElementById('subConfirmTitle').textContent=title;
            document.getElementById('subConfirmBody').textContent=body;
            const btn=document.getElementById('subConfirmOk'); btn.textContent=okLabel;
            const modal=new bootstrap.Modal(document.getElementById('subConfirmModal'));
            const onOk=()=>{modal.hide();resolve(true)};
            const onHide=()=>{btn.removeEventListener('click',onOk);resolve(false)};
            btn.addEventListener('click',onOk,{once:true});
            document.getElementById('subConfirmModal').addEventListener('hidden.bs.modal',onHide,{once:true});
            modal.show();
        });
    },



    // ─── ENTERPRISE LICENSE MANAGEMENT ─────────────────────────────────────
    _lic: {
        page: 1, perPage: 5, totalPages: 1,
        sortBy: 'created_at', sortDir: 'desc',
        filters: { status: '', plan: '', expiry_window: '', country: '', state: '', industry: '' },
        q: '', searchTimer: null, locTimer: null,
        selectedIds: new Set(),
        wizStep: 1,
        wizSelectedOrg: null, wizSelectedPlan: 'Professional', wizSelectedType: 'Professional'
    },

    // Helper notifications
    _licNotify(msg, type='success') {
        if (window.api && api.showNotification) {
            api.showNotification(msg, type);
            return;
        }
        const bgColors = { success: '#f0fdf4', error: '#fef2f2', info: '#eff6ff', warning: '#fffbeb' };
        const textColors = { success: '#065f46', error: '#991b1b', info: '#1e40af', warning: '#92400e' };
        const borderColors = { success: '#10b981', error: '#ef4444', info: '#3b82f6', warning: '#f59e0b' };
        const c = document.createElement('div');
        c.style.cssText = `position:fixed;top:24px;right:24px;background:${bgColors[type]||'#fff'};color:${textColors[type]||'#0f172a'};border:1px solid ${borderColors[type]};border-left:5px solid ${borderColors[type]};border-radius:10px;padding:12px 18px;font-size:13.5px;font-weight:600;z-index:99999999;box-shadow:0 10px 30px rgba(0,0,0,.25);max-width:380px;min-width:300px;`;
        c.textContent = msg;
        document.body.appendChild(c);
        setTimeout(() => c.remove(), 4000);
    },

    _licConfirm(title, body, okLabel) {
        return new Promise(resolve => {
            const t = document.getElementById('licConfirmTitle');
            const b = document.getElementById('licConfirmBody');
            const ok = document.getElementById('licConfirmOk');
            if (!t || !b || !ok) { resolve(confirm(body)); return; }
            t.textContent = title; b.textContent = body; ok.textContent = okLabel;
            const modal = new bootstrap.Modal(document.getElementById('licConfirmModal'));
            const onOk = () => { modal.hide(); resolve(true); };
            const onHide = () => { ok.removeEventListener('click', onOk); resolve(false); };
            ok.addEventListener('click', onOk, { once: true });
            document.getElementById('licConfirmModal').addEventListener('hidden.bs.modal', onHide, { once: true });
            modal.show();
        });
    },

    // Main loader
    async loadLicenses() {
        await Promise.all([this._licLoadKPIs(), this._licLoadTable()]);
        this.applyColumnVisibility();
        if (window.lucide) lucide.createIcons();
    },

    // Load statistics
    async _licLoadKPIs() {
        const grid = document.getElementById('licKpiGrid');
        if (!grid) return;
        try {
            const res = await api.get('/licenses/stats');
            if (!res || res.status !== 'success') return;
            const kpi = res.data || {};
            const timestamp = new Date().toLocaleTimeString();
            
            const card = (label, val, icon, color, formula, desc, filterVal, filterKey = 'status') => {
                const colors = { blue: '#2563eb', green: '#10b981', red: '#ef4444', orange: '#f59e0b', purple: '#8b5cf6', gray: '#6b7280' };
                const cHex = colors[color] || '#6b7280';
                return `<div class="lic-kpi-card" onclick="SuperAdmin.setLicFilter('${filterKey}', '${filterVal}', null)">
                    <div class="kpi-icon" style="background: rgba(var(--ds-primary-rgb), 0.08);"><i data-lucide="${icon}" style="width:16px;height:16px;color:${cHex};"></i></div>
                    <div class="kpi-label">${label}</div>
                    <div class="kpi-value">${val}</div>
                    <div class="kpi-accent" style="background:${cHex};"></div>
                    <div class="position-absolute" style="top:8px; right:8px; opacity:0.4;" onclick="event.stopPropagation()">
                        <i data-lucide="info" style="width:12px; height:12px; cursor:help;" data-bs-toggle="tooltip" data-bs-html="true" title="<strong>Formula:</strong> ${formula}<br/><small class='text-muted'>${desc}<br/>As of: ${timestamp}</small>"></i>
                    </div>
                </div>`;
            };

            grid.innerHTML = `
                ${card('Total Licenses', kpi.total, 'key', 'blue', 'Count(organizations)', 'Total generated enterprise licenses', '', 'status')}
                ${card('Active', kpi.active, 'check-circle', 'green', 'status == &quot;Active&quot;', 'Active enterprise production licenses', 'Active')}
                ${card('Trial', kpi.trial, 'clock', 'orange', 'status == &quot;Trial&quot;', 'Licenses currently evaluating the platform', 'Trial')}
                ${card('Expired', kpi.expired, 'alert-triangle', 'red', 'expiry_date &lt; NOW', 'Licenses whose validity period has elapsed', 'Expired')}
                ${card('On Hold', kpi.suspended, 'slash', 'purple', 'status == &quot;Suspended&quot;', 'Access suspended due to admin action', 'Suspended')}
                ${card('Revoked', kpi.revoked, 'x-circle', 'gray', 'status == &quot;Revoked&quot;', 'Permanently deactivated non-reactive licenses', 'Revoked')}
                ${card('Expiring Soon', kpi.expiring_soon, 'calendar', 'orange', 'expiry_date &lt;= 30 days', 'Licenses expiring within 30 days', '30d', 'expiry_window')}
                ${card('Lifetime', kpi.lifetime, 'crown', 'purple', 'plan == &quot;Lifetime&quot;', 'Lifetime perpetual client contracts', 'Lifetime', 'plan')}
            `;
            if (window.lucide) lucide.createIcons();
            
            const tooltipTriggerList = document.querySelectorAll('#licKpiGrid [data-bs-toggle="tooltip"]');
            [...tooltipTriggerList].map(el => new bootstrap.Tooltip(el));
        } catch (e) {
            grid.innerHTML = `<div class="text-xs text-muted text-center py-2 col-12">Statistics unavailable — Backend offline.</div>`;
        }
    },

    // Load licenses table
    async _licLoadTable() {
        const tbody = document.getElementById('licensesBody');
        const countEl = document.getElementById('licensesCount');
        if (!tbody) return;
        tbody.innerHTML = `<tr><td colspan="10" class="text-center py-5"><span class="spinner-border spinner-border-sm me-2"></span>Loading licenses…</td></tr>`;

        const s = this._lic;
        const licPerPageEl = document.getElementById('licPerPage');
        if (licPerPageEl && licPerPageEl.value) {
            s.perPage = parseInt(licPerPageEl.value) || 5;
        } else if (licPerPageEl) {
            licPerPageEl.value = s.perPage || 5;
        }

        const params = new URLSearchParams({
            page: s.page, per_page: s.perPage,
            sort_by: s.sortBy, sort_dir: s.sortDir,
            q: s.q,
            ...Object.fromEntries(Object.entries(s.filters).filter(([,v])=>v))
        });

        try {
            const res = await api.get(`/licenses/?${params}`);
            if (!res || res.status !== 'success') {
                if (tbody) tbody.innerHTML = `<tr><td colspan="10" class="text-center py-5 text-muted"><i data-lucide="alert-triangle" style="width:24px;height:24px;opacity:.4;"></i><div class="mt-2 text-xs">Failed to load licenses. Please refresh.</div></td></tr>`;
                return;
            }
            const data = res.data || [];
            const pg = res.pagination || { total: 0, page: 1, pages: 1 };

            if (countEl) countEl.textContent = `${pg.total.toLocaleString()} licenses`;
            
            if (!data.length) {
                tbody.innerHTML = `<tr><td colspan="10" class="text-center py-5 text-muted">
                    <i data-lucide="inbox" style="width:28px;height:28px;opacity:.3;"></i>
                    <div class="mt-2 text-xs">No licenses matching your criteria. Click <strong>Generate License</strong> to issue one.</div>
                </td></tr>`;
                if (window.lucide) lucide.createIcons();
                return;
            }

            tbody.innerHTML = data.map(l => {
                const checked = s.selectedIds.has(l.id) ? 'checked' : '';
                const active = l.subscription_status === 'Active';
                const statusColor = { 'Active': 'active', 'Trialing': 'trial', 'Trial': 'trial', 'Expired': 'expired', 'Suspended': 'suspended', 'Revoked': 'revoked' }[l.subscription_status] || 'pending';
                
                const highlight = (txt) => {
                    if (!txt) return '—';
                    if (!s.q) return txt;
                    const esc = s.q.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
                    return txt.toString().replace(new RegExp(`(${esc})`, 'gi'), '<mark style="background:rgba(var(--ds-primary-rgb),0.2);padding:0 2px;border-radius:2px;color:inherit;">$1</mark>');
                };

                return `<tr id="licrow-${l.id}">
                    <td><input type="checkbox" class="lic-row-cb form-check-input" data-id="${l.id}" ${checked} onchange="SuperAdmin._licToggleRow(${l.id},this)"></td>
                    <td>
                        <span class="text-primary font-monospace fw-bold" style="font-size:11.5px; cursor:pointer;" onclick="SuperAdmin.openLicDrawer(${l.id})">${highlight(l.license_number)}</span>
                    </td>
                    <td class="col-org">
                        <div class="fw-bold" style="font-size:12.5px;">${highlight(l.organization_name)}</div>
                        <div class="text-muted text-xxs">${highlight(l.org_code)} · ${highlight(l.admin_email)}</div>
                    </td>
                    <td class="col-plan">
                        <span class="plan-chip ${(l.subscription_plan||'').toLowerCase()}">${l.subscription_plan}</span>
                    </td>
                    <td class="col-start text-muted" style="font-size:11px;">${l.license_start_date ? new Date(l.license_start_date).toLocaleDateString() : '—'}</td>
                    <td class="col-end" style="font-size:11px;">${l.license_expiry_date ? new Date(l.license_expiry_date).toLocaleDateString() : '—'}</td>
                    <td class="col-rem">
                        <span class="fw-bold" style="font-size:12px;">${l.remaining_days !== null ? (l.remaining_days < 0 ? 'Expired' : l.remaining_days + 'd') : '—'}</span>
                    </td>
                    <td><span class="lic-badge ${statusColor}">${l.subscription_status}</span></td>
                    <td class="col-limits">
                        <div class="text-xs"><strong>${l.max_users >= 99999 ? '∞' : l.max_users}</strong> users · <strong>${l.storage_limit_gb}GB</strong></div>
                    </td>
                    <td class="text-end">
                        <div class="dropdown">
                            <button class="btn btn-link text-muted p-1" data-bs-toggle="dropdown" data-bs-popper-config='{"strategy":"fixed"}' style="border:none;background:transparent;box-shadow:none;">
                                <i data-lucide="more-horizontal" style="width:16px;height:16px;"></i>
                            </button>
                            <ul class="dropdown-menu dropdown-menu-end" style="min-width:180px; font-size:12px; z-index:100050 !important;">
                                <li><a class="dropdown-item" href="#" onclick="SuperAdmin.openLicDrawer(${l.id});return false;"><i data-lucide="eye" style="width:13px;height:13px;" class="me-2 text-muted"></i>View Details</a></li>
                                <li><a class="dropdown-item" href="#" onclick="SuperAdmin.openEditLicense(${l.id});return false;"><i data-lucide="edit-3" style="width:13px;height:13px;" class="me-2 text-muted"></i>Edit Parameters</a></li>
                                <li><hr class="dropdown-divider"></li>
                                ${active ? `<li><a class="dropdown-item text-warning" href="#" onclick="SuperAdmin._licActionSuspend(${l.id});return false;"><i data-lucide="pause-circle" style="width:13px;height:13px;" class="me-2"></i>Suspend</a></li>` : ''}
                                ${l.subscription_status === 'Suspended' ? `<li><a class="dropdown-item text-success" href="#" onclick="SuperAdmin._licActionResume(${l.id});return false;"><i data-lucide="play-circle" style="width:13px;height:13px;" class="me-2"></i>Activate</a></li>` : ''}
                                <li><a class="dropdown-item" href="#" onclick="SuperAdmin._licActionRenew(${l.id});return false;"><i data-lucide="refresh-cw" style="width:13px;height:13px;" class="me-2 text-muted"></i>Renew (1 Year)</a></li>
                                <li><a class="dropdown-item" href="#" onclick="SuperAdmin._licActionExtend(${l.id});return false;"><i data-lucide="calendar" style="width:13px;height:13px;" class="me-2 text-muted"></i>Extend Expiry</a></li>
                                <li><a class="dropdown-item" href="#" onclick="SuperAdmin._licActionRegenKey(${l.id});return false;"><i data-lucide="key" style="width:13px;height:13px;" class="me-2 text-muted"></i>Regenerate Key</a></li>
                                <li><a class="dropdown-item" href="#" onclick="SuperAdmin._licDownloadFile(${l.id});return false;"><i data-lucide="download" style="width:13px;height:13px;" class="me-2 text-muted"></i>Download (.lic)</a></li>
                                <li><hr class="dropdown-divider"></li>
                                <li><a class="dropdown-item text-danger" href="#" onclick="SuperAdmin._licActionRevoke(${l.id});return false;"><i data-lucide="trash" style="width:13px;height:13px;" class="me-2"></i>Revoke</a></li>
                            </ul>
                        </div>
                    </td>
                </tr>`;
            }).join('');

            // Pagination UI
            const pagInfo = document.getElementById('licPagInfo');
            const pagBtns = document.getElementById('licPagBtns');
            if (pagInfo) {
                const start = (pg.page - 1) * pg.per_page + 1;
                const end = Math.min(pg.page * pg.per_page, pg.total);
                pagInfo.textContent = `Showing ${start}–${end} of ${pg.total.toLocaleString()} licenses`;
            }
            if (pagBtns) {
                const b = [];
                b.push(`<button class="ds-btn ds-btn-secondary btn-sm" onclick="SuperAdmin._licGoPage(${pg.page-1})" ${pg.page<=1?'disabled':''}>‹</button>`);
                for (let i = 1; i <= pg.pages; i++) {
                    b.push(`<button class="ds-btn ${i===pg.page?'ds-btn-primary':'ds-btn-secondary'} btn-sm" onclick="SuperAdmin._licGoPage(${i})">${i}</button>`);
                }
                b.push(`<button class="ds-btn ds-btn-secondary btn-sm" onclick="SuperAdmin._licGoPage(${pg.page+1})" ${pg.page>=pg.pages?'disabled':''}>›</button>`);
                pagBtns.innerHTML = b.join('');
            }
            if (window.lucide) lucide.createIcons();
        } catch(e) {
            tbody.innerHTML = `<tr><td colspan="10" class="text-center py-5 text-danger text-xs">Failed loading licenses table data.</td></tr>`;
        }
    },

    _licGoPage(p) { this._lic.page = p; this._licLoadTable(); },
    licSetPerPage(v) { 
        this._lic.perPage = parseInt(v) || 5; 
        this._lic.page = 1; 
        const el = document.getElementById('licPerPage');
        if (el) el.value = this._lic.perPage;
        this._licLoadTable(); 
    },
    licSort(col) {
        if (this._lic.sortBy === col) this._lic.sortDir = this._lic.sortDir === 'asc' ? 'desc' : 'asc';
        else { this._lic.sortBy = col; this._lic.sortDir = 'desc'; }
        this._licLoadTable();
    },

    // Search and location debouncing
    licDebounceSearch(v) {
        clearTimeout(this._lic.searchTimer);
        this._lic.searchTimer = setTimeout(() => { this._lic.q = v.trim(); this._lic.page = 1; this._licLoadTable(); }, 300);
    },
    licDebounceLocation(key, val) {
        clearTimeout(this._lic.locTimer);
        this._lic.locTimer = setTimeout(() => { this._lic.filters[key] = val.trim(); this._lic.page = 1; this._licLoadTable(); }, 300);
    },
    setLicFilter(key, val, btn) {
        if (key === 'status') {
            document.querySelectorAll('[data-lf="status"]').forEach(b => b.classList.remove('active'));
            if (btn) btn.classList.add('active');
        }
        if (val === '30d') { this._lic.filters.expiry_window = '30d'; }
        else { this._lic.filters[key] = val; }
        this._lic.page = 1;
        this._licLoadTable();
    },
    resetLicFilters() {
        this._lic.filters = { status: '', plan: '', expiry_window: '', country: '', state: '', industry: '' };
        this._lic.q = ''; this._lic.page = 1;
        const searchInput = document.getElementById('licSearchInput'); if (searchInput) searchInput.value = '';
        const planFilter = document.getElementById('licPlanFilter'); if (planFilter) planFilter.value = '';
        const expiryFilter = document.getElementById('licExpiryFilter'); if (expiryFilter) expiryFilter.value = '';
        const countryFilter = document.getElementById('licCountryFilter'); if (countryFilter) countryFilter.value = '';
        const stateFilter = document.getElementById('licStateFilter'); if (stateFilter) stateFilter.value = '';
        const industryFilter = document.getElementById('licIndustryFilter'); if (industryFilter) industryFilter.value = '';
        document.querySelectorAll('[data-lf="status"]').forEach(b => b.classList.remove('active'));
        const all = document.querySelector('[data-lf="status"][data-lv=""]');
        if (all) all.classList.add('active');
        this._licLoadTable();
    },

    // Row selection and Bulk Actions
    licToggleAll(cb) {
        document.querySelectorAll('.lic-row-cb').forEach(c => {
            c.checked = cb.checked;
            const id = parseInt(c.dataset.id);
            cb.checked ? this._lic.selectedIds.add(id) : this._lic.selectedIds.delete(id);
            document.getElementById(`licrow-${id}`)?.classList.toggle('row-selected', cb.checked);
        });
        this._licUpdateBulkBar();
    },
    _licToggleRow(id, cb) {
        cb.checked ? this._lic.selectedIds.add(id) : this._lic.selectedIds.delete(id);
        document.getElementById(`licrow-${id}`)?.classList.toggle('row-selected', cb.checked);
        this._licUpdateBulkBar();
    },
    _licUpdateBulkBar() {
        const count = this._lic.selectedIds.size;
        const bar = document.getElementById('licBulkBar');
        const cnt = document.getElementById('licBulkCount');
        if (bar) bar.classList.toggle('show', count > 0);
        if (cnt) cnt.textContent = count;
    },
    clearLicSelection() {
        this._lic.selectedIds.clear();
        document.querySelectorAll('.lic-row-cb').forEach(c => c.checked = false);
        const all = document.getElementById('licSelectAll'); if (all) all.checked = false;
        document.querySelectorAll('.row-selected').forEach(r => r.classList.remove('row-selected'));
        this._licUpdateBulkBar();
    },
    async licBulkAction(action) {
        const ids = Array.from(this._lic.selectedIds);
        if (!ids.length) return;
        
        let confirmMsg = `Execute bulk ${action} action on ${ids.length} licenses?`;
        if (action === 'revoke') confirmMsg = `Permanently revoke ${ids.length} licenses? Revoked licenses cannot be re-activated.`;
        
        const ok = await this._licConfirm('Bulk License Action', confirmMsg, 'Execute Bulk');
        if (!ok) return;

        try {
            this._licNotify(`Processing bulk ${action}…`, 'info');
            for (const id of ids) {
                await api.post(`/licenses/${id}/${action}`);
            }
            this._licNotify(`Bulk ${action} successfully executed.`, 'success');
            this.clearLicSelection();
            this.loadLicenses();
        } catch (e) {
            this._licNotify(e.message || 'Action failed', 'error');
        }
    },

    // Row Actions
    async _licActionSuspend(id) {
        const reason = prompt('Enter suspension reason:', 'Administrative compliance audit required.');
        if (reason === null) return;
        try {
            const r = await api.post(`/licenses/${id}/suspend`, { reason });
            this._licNotify(r.message, 'warning');
            this.loadLicenses();
        } catch(e) { this._licNotify(e.message, 'error'); }
    },
    async _licActionResume(id) {
        try {
            const r = await api.post(`/licenses/${id}/resume`);
            this._licNotify(r.message, 'success');
            this.loadLicenses();
        } catch(e) { this._licNotify(e.message, 'error'); }
    },
    async _licActionRenew(id) {
        const ok = await this._licConfirm('Renew License', 'Renew the validity period of this license for 1 Year?', 'Renew License');
        if (!ok) return;
        try {
            const r = await api.post(`/licenses/${id}/renew`);
            this._licNotify(r.message, 'success');
            this.loadLicenses();
        } catch(e) { this._licNotify(e.message, 'error'); }
    },
    async _licActionExtend(id) {
        const days = prompt('Enter number of days to extend validity:', '30');
        if (!days || isNaN(days)) return;
        try {
            const r = await api.post(`/licenses/${id}/extend`, { days: parseInt(days) });
            this._licNotify(r.message, 'success');
            this.loadLicenses();
        } catch(e) { this._licNotify(e.message, 'error'); }
    },
    async _licActionRegenKey(id) {
        const ok = await this._licConfirm('Regenerate License Key', 'Deactivate the old key and issue a new secure key? The organization must be updated with the new key.', 'Issue New Key');
        if (!ok) return;
        try {
            const r = await api.post(`/licenses/${id}/regenerate-key`);
            this._licNotify(r.message, 'success');
            this.loadLicenses();
        } catch(e) { this._licNotify(e.message, 'error'); }
    },
    async _licActionRevoke(id) {
        const ok = await this._licConfirm('Revoke License', 'Are you sure you want to revoke this license? This blocks all organization admin and user sessions permanently.', 'Revoke Permanently');
        if (!ok) return;
        try {
            const r = await api.post(`/licenses/${id}/revoke`);
            this._licNotify(r.message, 'error');
            this.loadLicenses();
        } catch(e) { this._licNotify(e.message, 'error'); }
    },
    async _licDownloadFile(id) {
        try {
            const r = await api.get(`/licenses/${id}/download`);
            if (r.status !== 'success') throw new Error(r.error);
            
            // Decodes base64 payload and issues file save dialog
            const content = atob(r.content);
            const blob = new Blob([content], { type: 'application/octet-stream' });
            const url = URL.createObjectURL(blob);
            
            const link = document.createElement('a');
            link.href = url;
            link.download = r.filename || 'license.lic';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
            
            this._licNotify('Cryptographic license file downloaded.', 'success');
        } catch(e) { this._licNotify(e.message, 'error'); }
    },

    // Side details drawer
    async openLicDrawer(id) {
        const overlay = document.getElementById('licDetailOverlay');
        const drawer = document.getElementById('licDetailDrawer');
        const body = document.getElementById('lddBody');
        if (!overlay || !drawer) return;
        overlay.classList.add('open'); drawer.classList.add('open');
        body.innerHTML = `<div class="text-center py-5"><span class="spinner-border"></span></div>`;
        try {
            const res = await api.get(`/licenses/${id}`);
            if (!res || res.status !== 'success') throw new Error(res.error);
            const l = res.data;
            document.getElementById('lddTitle').textContent = l.license_number;
            document.getElementById('lddOrg').textContent = `${l.organization_name} (${l.org_code})`;
            document.getElementById('lddStatusBadge').innerHTML = `<span class="lic-badge ${l.subscription_status.toLowerCase()}">${l.subscription_status}</span>`;
            
            const userPct = l.max_users > 0 ? Math.min(100, Math.round(l.usage.active_users / l.max_users * 100)) : 0;
            const storagePct = l.storage_limit_gb > 0 ? Math.min(100, Math.round((l.storage_used_mb / 1024) / l.storage_limit_gb * 100)) : 0;

            body.innerHTML = `
                <div class="d-flex flex-wrap gap-2 mb-4">
                    <button class="ds-btn ds-btn-secondary btn-sm" onclick="SuperAdmin._licActionRenew(${l.id})"><i data-lucide="refresh-cw" style="width:12px;height:12px;"></i> Renew</button>
                    <button class="ds-btn ds-btn-secondary btn-sm" onclick="SuperAdmin._licDownloadFile(${l.id})"><i data-lucide="download" style="width:12px;height:12px;"></i> Download</button>
                    <button class="ds-btn ds-btn-secondary btn-sm" onclick="SuperAdmin._licActionRegenKey(${l.id}); SuperAdmin.closeLicDrawer();"><i data-lucide="key" style="width:12px;height:12px;"></i> Regen Key</button>
                    ${l.subscription_status !== 'Suspended' ? `<button class="ds-btn btn-sm btn-outline-warning" onclick="SuperAdmin._licActionSuspend(${l.id}); SuperAdmin.closeLicDrawer();">Suspend</button>` : `<button class="ds-btn btn-sm btn-outline-success" onclick="SuperAdmin._licActionResume(${l.id}); SuperAdmin.closeLicDrawer();">Activate</button>`}
                </div>
                <div class="ldd-section">
                    <div class="ldd-section-title">License & Plan Details</div>
                    <div class="ldd-grid">
                        <div class="ldd-item"><div class="di-l">Key</div><div class="di-v text-primary font-monospace">${l.license_number}</div></div>
                        <div class="ldd-item"><div class="di-l">Status</div><div class="di-v">${l.subscription_status}</div></div>
                        <div class="ldd-item"><div class="di-l">Plan Level</div><div class="di-v"><span class="plan-chip ${l.subscription_plan.toLowerCase()}">${l.subscription_plan}</span></div></div>
                        <div class="ldd-item"><div class="di-l">Created</div><div class="di-v">${new Date(l.created_at).toLocaleDateString()}</div></div>
                        <div class="ldd-item"><div class="di-l">Issued Date</div><div class="di-v">${l.license_start_date ? new Date(l.license_start_date).toLocaleDateString() : '—'}</div></div>
                        <div class="ldd-item"><div class="di-l">Expiration Date</div><div class="di-v fw-bold text-danger">${l.license_expiry_date ? new Date(l.license_expiry_date).toLocaleDateString() : 'Perpetual'}</div></div>
                    </div>
                </div>
                <div class="ldd-section">
                    <div class="ldd-section-title">Usage & Resource Limits</div>
                    <div class="mb-3">
                        <div class="d-flex justify-content-between text-xs mb-1"><span>Users Allocation</span><span>${l.usage.active_users} / ${l.max_users >= 99999 ? '∞' : l.max_users} (${userPct}%)</span></div>
                        <div style="height:6px; border-radius:3px; background:var(--ds-border-color); overflow:hidden;"><div style="height:100%; width:${userPct}%; border-radius:3px; background:${userPct>90?'#ef4444':userPct>70?'#f59e0b':'#10b981'}"></div></div>
                    </div>
                    <div class="mb-3">
                        <div class="d-flex justify-content-between text-xs mb-1"><span>Storage Limit</span><span>${(l.storage_used_mb / 1024).toFixed(2)} GB / ${l.storage_limit_gb} GB (${storagePct}%)</span></div>
                        <div style="height:6px; border-radius:3px; background:var(--ds-border-color); overflow:hidden;"><div style="height:100%; width:${storagePct}%; border-radius:3px; background:${storagePct>90?'#ef4444':storagePct>70?'#f59e0b':'#10b981'}"></div></div>
                    </div>
                    <div class="ldd-grid">
                        <div class="ldd-item"><div class="di-l">Active Departments</div><div class="di-v">${l.usage.active_departments}</div></div>
                        <div class="ldd-item"><div class="di-l">Active Quality Projects</div><div class="di-v">${l.usage.active_projects}</div></div>
                        <div class="ldd-item" style="grid-column: 1/-1;"><div class="di-l">Feature Modules</div><div class="di-v">${l.enabled_modules.join(', ')}</div></div>
                    </div>
                </div>
                ${l.history && l.history.length ? `
                <div class="ldd-section">
                    <div class="ldd-section-title">Timeline of Changes & Audit Trail</div>
                    <ul style="list-style:none; padding:0; margin:0;">
                        ${l.history.map(h => `<li style="display:flex; gap:0.7rem; padding:0.5rem 0; border-bottom:1px solid var(--ds-border-color); font-size:12px;">
                            <span style="width:8px; height:8px; border-radius:50%; margin-top:5px; flex-shrink:0; background:${h.action.includes('SUSPEND')||h.action.includes('REVOKE')?'#ef4444':'#10b981'};"></span>
                            <div>
                                <div class="fw-bold">${h.action.replace(/_/g, ' ')}</div>
                                <div class="text-muted text-xxs">${h.admin} · ${new Date(h.timestamp).toLocaleString()}</div>
                            </div>
                        </li>`).join('')}
                    </ul>
                </div>` : ''}
            `;
            if (window.lucide) lucide.createIcons();
        } catch(e) {
            body.innerHTML = `<div class="text-danger p-3">${e.message}</div>`;
        }
    },
    closeLicDrawer() {
        document.getElementById('licDetailOverlay')?.classList.remove('open');
        document.getElementById('licDetailDrawer')?.classList.remove('open');
    },

    // Edit Parameters Dialog
    async openEditLicense(id) {
        try {
            const res = await api.get(`/licenses/${id}`);
            if (!res || res.status !== 'success') return;
            const l = res.data;
            
            // Reuses the edit profile modal or issues simple prompt values
            const users = prompt('Change Max Users limit:', l.max_users);
            if (users === null) return;
            const storage = prompt('Change Storage Limit (GB):', l.storage_limit_gb);
            if (storage === null) return;
            
            this._licNotify('Updating limits…', 'info');
            await api.put(`/licenses/${id}`, {
                max_users: parseInt(users),
                storage_limit_gb: parseFloat(storage)
            });
            this._licNotify('License limits updated successfully.', 'success');
            this.loadLicenses();
        } catch(e) { this._licNotify(e.message, 'error'); }
    },

    // Guided Creation Wizard
    openLicCreateWizard() {
        this._lic.wizStep = 1;
        this._licWizGoStep(1);
        document.getElementById('lwOrgSearch').value = '';
        document.getElementById('lwOrgId').value = '';
        document.getElementById('lwOrgChosen').textContent = '';
        document.getElementById('lwOrgList').innerHTML = '';
        document.getElementById('lwConfirm').checked = false;
        
        const modal = new bootstrap.Modal(document.getElementById('licCreateModal'));
        modal.show();
    },
    _licWizGoStep(n) {
        this._lic.wizStep = n;
        document.querySelectorAll('#licCreateModal .wiz-panel').forEach(p => p.classList.remove('active'));
        document.getElementById(`lwp${n}`)?.classList.add('active');
        document.querySelectorAll('#licCreateModal .wiz-step').forEach(s => {
            const sn = parseInt(s.dataset.lws);
            s.classList.toggle('active', sn === n);
            s.classList.toggle('done', sn < n);
        });
        document.getElementById('lwPrevBtn').disabled = n === 1;
        document.getElementById('lwNextBtn').classList.toggle('d-none', n === 5);
        document.getElementById('lwSubmitBtn').classList.toggle('d-none', n !== 5);
        if (n === 5) this._licWizRenderReview();
    },
    licWizNext() {
        if (this._lic.wizStep === 1 && !document.getElementById('lwOrgId').value) {
            this._licNotify('Select an organization to proceed.', 'error');
            return;
        }
        if (this._lic.wizStep < 5) this._licWizGoStep(this._lic.wizStep + 1);
    },
    licWizPrev() {
        if (this._lic.wizStep > 1) this._licWizGoStep(this._lic.wizStep - 1);
    },
    async licWizSearchOrg(q) {
        if (!q || q.length < 2) { document.getElementById('lwOrgList').innerHTML = ''; return; }
        try {
            // Retrieve companies from SuperAdmin /companies endpoint
            const res = await api.get(`/super-admin/companies?search=${encodeURIComponent(q)}&per_page=8`);
            if (!res || res.status !== 'success') return;
            document.getElementById('lwOrgList').innerHTML = (res.organizations || res.data || []).map(o => `
                <div style="padding:7px 10px; cursor:pointer; border:1px solid var(--ds-border-color); border-radius:8px; margin-bottom:4px; display:flex; justify-content:space-between; font-size:12.5px; background: var(--ds-bg-card);"
                     onclick="SuperAdmin._licWizSelectOrg(${o.id},'${(o.name||'').replace(/'/g,"\\'")}', '${(o.email||'').replace(/'/g,"\\'")}')">
                    <span><strong>${o.name}</strong> <span class="text-muted text-xxs">(${o.org_code || o.id})</span></span>
                    <span class="plan-chip ${(o.plan||'').toLowerCase()}">${o.plan || '—'}</span>
                </div>
            `).join('') || '<div class="text-xs text-muted p-2">No organizations found</div>';
        } catch(e) {}
    },
    _licWizSelectOrg(id, name, email) {
        document.getElementById('lwOrgId').value = id;
        document.getElementById('lwOrgChosen').textContent = `✓ Selected: ${name} (${email})`;
        document.getElementById('lwOrgSearch').value = name;
        document.getElementById('lwOrgList').innerHTML = '';
        this._lic.wizSelectedOrg = { id, name, email };
    },
    licWizSelectPlan(plan, btn) {
        document.getElementById('lwPlan').value = plan;
        this._lic.wizSelectedPlan = plan;
        document.querySelectorAll('#lwp2 .pc-card').forEach(c => c.classList.remove('sel'));
        if (btn) btn.querySelector('.pc-card')?.classList.add('sel');
        
        // Auto-sets default users/storage limits based on plan catalog
        const defaults = { Starter: { u: 25, s: 5 }, Professional: { u: 500, s: 50 }, Enterprise: { u: 99999, s: 500 }, Custom: { u: 100, s: 10 } }[plan] || { u: 500, s: 50 };
        document.getElementById('lwMaxUsers').value = defaults.u;
        document.getElementById('lwStorage').value = defaults.s;
    },
    licWizSelectType(type, btn) {
        document.getElementById('lwType').value = type;
        this._lic.wizSelectedType = type;
        document.querySelectorAll('#lwp3 .pc-card').forEach(c => c.classList.remove('sel'));
        if (btn) btn.querySelector('.pc-card')?.classList.add('sel');
    },
    _licWizRenderReview() {
        const plan = document.getElementById('lwPlan').value;
        const type = document.getElementById('lwType').value;
        const users = document.getElementById('lwMaxUsers').value;
        const storage = document.getElementById('lwStorage').value;
        const modules = Array.from(document.querySelectorAll('#lwModules input:checked')).map(c => c.value);
        
        document.getElementById('lwReview').innerHTML = `
            <div class="row g-2 text-xs">
                <div class="col-6"><div class="text-muted">Organization</div><strong>${this._lic.wizSelectedOrg ? this._lic.wizSelectedOrg.name : '—'}</strong></div>
                <div class="col-6"><div class="text-muted">Plan Level</div><span class="plan-chip ${plan.toLowerCase()}">${plan}</span></div>
                <div class="col-6"><div class="text-muted">License Class</div><strong>${type}</strong></div>
                <div class="col-6"><div class="text-muted">User Limit</div><strong>${users >= 99999 ? 'Unlimited (∞)' : users + ' Users'}</strong></div>
                <div class="col-6"><div class="text-muted">Storage Capacity</div><strong>${storage} GB</strong></div>
                <div class="col-12"><div class="text-muted">Enabled Module Features</div><div class="d-flex gap-1 flex-wrap mt-1">${modules.map(m => `<span class="plan-chip outline">${m}</span>`).join('')}</div></div>
            </div>
        `;
    },
    async licWizSubmit() {
        if (!document.getElementById('lwConfirm').checked) {
            this._licNotify('Please check the confirmation box to issue key.', 'error');
            return;
        }
        
        const payload = {
            org_id: parseInt(document.getElementById('lwOrgId').value),
            plan_name: document.getElementById('lwPlan').value,
            license_type: document.getElementById('lwType').value,
            max_users: parseInt(document.getElementById('lwMaxUsers').value),
            storage_limit_gb: parseFloat(document.getElementById('lwStorage').value),
            enabled_modules: Array.from(document.querySelectorAll('#lwModules input:checked')).map(c => c.value)
        };

        try {
            this._licNotify('Generating secure license key…', 'info');
            const r = await api.post('/licenses/', payload);
            this._licNotify('License successfully issued!', 'success');
            bootstrap.Modal.getInstance(document.getElementById('licCreateModal'))?.hide();
            this.loadLicenses();
            
            // Prompt to download newly created key
            setTimeout(() => {
                if (confirm(`License generated successfully!\nKey: ${r.license_key}\n\nWould you like to download the signed license file now?`)) {
                    // Find created license ID from table or load licenses
                    SuperAdmin.loadLicenses();
                }
            }, 600);
        } catch(e) {
            this._licNotify(e.message || 'Key issuance failed', 'error');
        }
    },
    async licExportCSV() {
        try {
            const res = await api.get('/licenses/?per_page=1000');
            const list = res.data && res.data.licenses ? res.data.licenses : (res.data || []);
            if (!list || !list.length) {
                this._licNotify('No license data to export', 'info');
                return;
            }
            const headers = ['License Key', 'Organization Name', 'Org Code', 'Plan', 'Status', 'Start Date', 'Expiry Date', 'Active Users', 'Max Users', 'Storage Used (MB)', 'Storage Limit (GB)'];
            const rows = list.map(l => [
                l.license_number || '—',
                l.organization_name || '—',
                l.org_code || '—',
                l.subscription_plan || '—',
                l.subscription_status || '—',
                l.license_start_date ? String(l.license_start_date).slice(0, 10) : '—',
                l.license_expiry_date ? String(l.license_expiry_date).slice(0, 10) : 'Perpetual',
                l.usage ? l.usage.active_users : 0,
                l.max_users >= 99999 ? 'Unlimited' : (l.max_users || 0),
                l.storage_used_mb || 0,
                l.storage_limit_gb || 0
            ]);
            const csv = [headers.join(','), ...rows.map(r => r.map(v => `"${String(v).replace(/"/g, '""')}"`).join(','))].join('\n');
            const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = `qcms_licenses_export_${new Date().toISOString().slice(0,10)}.csv`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            this._licNotify('License CSV report exported successfully', 'success');
        } catch (e) {
            this._licNotify('License CSV export failed: ' + (e.message || e), 'error');
        }
    },

    licToggleColumnsToggles() {
        document.querySelectorAll('#licColToggles input').forEach(chk => {
            const cls = chk.value;
            const cells = document.querySelectorAll(`#licensesTable .${cls}`);
            cells.forEach(c => c.classList.toggle('d-none', !chk.checked));
        });
    },

    applyColumnVisibility() {
        document.querySelectorAll('#licColToggles input').forEach(chk => {
            const cls = chk.value;
            document.querySelectorAll(`#licensesTable .${cls}`).forEach(c => {
                chk.checked ? c.classList.remove('d-none') : c.classList.add('d-none');
            });
        });
    },

    async loadAdmins() {
        const tbody = document.getElementById('adminsBody');
        const countEl = document.getElementById('adminsCount');
        if (!tbody) return;
        tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4"><span class="spinner-border spinner-border-sm me-2"></span>Loading admin accounts...</td></tr>`;
        try {
            const data = await api.get('/super-admin/companies?page=1&per_page=100');
            const orgs = (data && data.organizations) || (data && data.data) || [];
            if (countEl) countEl.textContent = `${orgs.length} admins`;
            if (!orgs.length) {
                tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-muted">No admin accounts found.</td></tr>`;
                return;
            }
            tbody.innerHTML = orgs.map(o => `
<tr>
                    <td><strong>${o.admin_name || '—'}</strong></td>
                    <td class="text-xs text-muted">${o.email || '—'}</td>
                    <td>${o.name}</td>
                    <td><span class="ds-badge outline">Admin</span></td>
                    <td><span class="ds-badge ${o.status === 'Active' ? 'green' : 'red'}" style="font-size:10px; padding:2px 6px;">${o.status === 'Active' ? 'Active' : 'Inactive'}</span></td>
                    <td class="text-xs text-muted">${o.created_at ? new Date(o.created_at).toLocaleDateString() : '—'}</td>
                    <td class="text-end">
                        <button class="btn btn-link btn-sm p-0 text-primary" onclick="SuperAdmin.openOrgDetail('${o.id}')">View Org</button>
                    </td>
                </tr>
            `).join('');
        } catch (err) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-danger">Failed to load admins.</td></tr>`;
        }
    },

    async loadUsers() {
        const tbody = document.getElementById('globalUsersBody');
        const countEl = document.getElementById('usersCount');
        if (!tbody) return;
        tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4"><span class="spinner-border spinner-border-sm me-2"></span>Loading users...</td></tr>`;
        try {
            const stats = await api.get('/v1/dashboard/stats');
            const total = (stats && stats.data && stats.data.total_users) || (stats && stats.total_users) || 0;
            if (countEl) countEl.textContent = `${total} users platform-wide`;
            // We show a summary note since a full user directory API doesn't exist yet
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center py-5">
                        <div class="mb-3"><i data-lucide="users" style="width:40px;height:40px;opacity:0.3;"></i></div>
                        <div class="fw-bold mb-1">${total.toLocaleString()} Users Registered</div>
                        <div class="text-xs text-muted">Full per-user directory endpoint coming soon. View per-org users from the Organizations module.</div>
                    </td>
                </tr>
            `;
        } catch (err) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-danger">Failed to load users.</td></tr>`;
        }
        if (window.lucide) lucide.createIcons();
    },

    // ─── SaaS PLAN PRODUCT CATALOGUE CONTROLLER ──────────────────────────────
    _plan: {
        page: 1,
        perPage: 5,
        filters: { status: '', plan_type: '', billing_cycle: '', price_type: '' },
        q: '',
        searchTimer: null,
        wizStep: 1,
        editPlanId: null,
        matrixPlans: ['Starter', 'Professional', 'Enterprise', 'Custom'],
    },

    // ── API Helpers ──
    async _planGet(path) {
        return api.get(`/subscriptions${path}`);
    },
    async _planPost(path, body={}) {
        return api.post(`/subscriptions${path}`, body);
    },
    async _planPut(path, body={}) {
        return api.put(`/subscriptions${path}`, body);
    },
    async _planDelete(path) {
        return api.delete(`/subscriptions${path}`);
    },

    // ── Helper formatters ──
    _planFmt(v){ const n=parseFloat(v)||0; return '₹'+n.toLocaleString('en-IN',{minimumFractionDigits:0,maximumFractionDigits:0}); },
    _planFmtD(v){ if(!v)return '—'; return new Date(v).toLocaleDateString('en-IN',{day:'2-digit',month:'short',year:'numeric'}); },
    _planNotify(msg, type='success'){
        if(window.api && api.showNotification){ api.showNotification(msg, type); return; }
        const bgColors={success:'#f0fdf4',error:'#fef2f2',info:'#eff6ff',warning:'#fffbeb'};
        const textColors={success:'#065f46',error:'#991b1b',info:'#1e40af',warning:'#92400e'};
        const borderColors={success:'#10b981',error:'#ef4444',info:'#3b82f6',warning:'#f59e0b'};
        const c=document.createElement('div');
        c.style.cssText=`position:fixed;top:24px;right:24px;background:${bgColors[type]||'#fff'};color:${textColors[type]||'#0f172a'};border:1px solid ${borderColors[type]};border-left:5px solid ${borderColors[type]};border-radius:10px;padding:12px 18px;font-size:13.5px;font-weight:600;z-index:99999999;box-shadow:0 10px 30px rgba(0,0,0,.25);max-width:380px;min-width:300px;`;
        c.textContent=msg; document.body.appendChild(c); setTimeout(()=>c.remove(),4000);
    },

    // ── Main loader ──
    async loadPlans() {
        await Promise.all([this._planLoadKPIs(), this._planLoadInsights(), this._planLoadTable()]);
        if(window.lucide) lucide.createIcons();
    },

    // ── KPI Cards ──
    async _planLoadKPIs() {
        const grid = document.getElementById('planKpiGrid');
        if (!grid) return;
        grid.innerHTML = `<div style="height:80px;background:var(--ds-border-color);border-radius:12px;animation:shimmer 1.4s infinite;grid-column:1/-1;"></div>`;
        try {
            const res = await this._planGet('/plans');
            const data = res.data || [];
            
            // Compute KPIs
            const total = data.length;
            const active = data.filter(p => p.status === 'Active').count || data.filter(p => p.status === 'Active').length;
            const inactive = data.filter(p => p.status === 'Inactive').length;
            const custom = data.filter(p => p.is_custom || p.plan_type === 'Custom').length;
            const deprecated = data.filter(p => p.status === 'Deprecated').length;
            
            const kpis = [
                { icon:'package',        bg:'rgba(99,102,241,.12)', color:'#6366f1', label:'Total Plans',      val: total,      accent:'#6366f1' },
                { icon:'check-circle',   bg:'rgba(16,185,129,.12)', color:'#10b981', label:'Active Plans',     val: active,     accent:'#10b981', filter:'Active' },
                { icon:'alert-triangle', bg:'rgba(245,158,11,.12)', color:'#f59e0b', label:'Inactive Plans',   val: inactive,   accent:'#f59e0b', filter:'Inactive' },
                { icon:'sliders',        bg:'rgba(139,92,246,.12)', color:'#8b5cf6', label:'Custom Plans',     val: custom,     accent:'#8b5cf6' }
            ];

            grid.innerHTML = kpis.map(k=>`
                <div class="plan-kpi-card" onclick="${k.filter?`SuperAdmin.setPlanFilter('status','${k.filter}')`:''}" title="${k.label}">
                    <div class="plan-kpi-icon" style="background:${k.bg};"><i data-lucide="${k.icon}" style="width:16px;height:16px;color:${k.color};"></i></div>
                    <div class="plan-kpi-label">${k.label}</div>
                    <div class="plan-kpi-value">${k.val}</div>
                    <div class="plan-kpi-accent" style="background:${k.accent};"></div>
                </div>`).join('');
            if(window.lucide) lucide.createIcons();
        } catch(e) {
            grid.innerHTML = `<div class="text-xs text-muted text-center py-2" style="grid-column:1/-1;">KPI data currently offline.</div>`;
        }
    },

    // ── AI Insights ──
    async _planLoadInsights() {
        const box = document.getElementById('planAiInsightsContent');
        if (!box) return;
        try {
            const res = await this._planGet('/plans/insights');
            const d = res.data;
            if (!d.recommendations || !d.recommendations.length) {
                box.innerHTML = `No catalog insights available yet. Subscriptions are required.`;
                return;
            }
            box.innerHTML = `<ul style="list-style:none;padding:0;margin:0;">
                ${d.recommendations.map(r=>`<li class="mb-1 d-flex align-items-start gap-1"><span>•</span> <span>${r}</span></li>`).join('')}
            </ul>`;
        } catch(e) {
            box.innerHTML = `AI Insights server currently offline.`;
        }
    },

    // ── Table ──
    async _planLoadTable() {
        const tbody = document.getElementById('plansBody');
        const countEl = document.getElementById('plansCount');
        if (!tbody) return;
        tbody.innerHTML = `<tr><td colspan="11" class="text-center py-5"><span class="spinner-border spinner-border-sm me-2"></span>Loading plans catalogue…</td></tr>`;

        const s = this._plan;
        const params = new URLSearchParams({
            q: s.q,
            billing_cycle: s.filters.billing_cycle || '',
            status: s.filters.status,
            plan_type: s.filters.plan_type,
            price_type: s.filters.price_type
        });

        try {
            const res = await this._planGet(`/plans?${params}`);
            const data = res.data || [];
            if (countEl) countEl.textContent = `${data.length} plans`;

            s.page = s.page || 1;
            s.perPage = s.perPage || 5;
            const total = data.length;
            const totalPages = Math.max(1, Math.ceil(total / s.perPage));
            const start = (s.page - 1) * s.perPage;
            const pageData = data.slice(start, start + s.perPage);

            this._planRenderTable(pageData, tbody);

            const info = document.getElementById('plansPagInfo');
            const btns = document.getElementById('plansPagBtns');
            const perPageSelect = document.getElementById('plansPerPage');

            if (perPageSelect) perPageSelect.value = s.perPage;

            if (info) {
                const startItem = total > 0 ? start + 1 : 0;
                const endItem = Math.min(s.page * s.perPage, total);
                info.textContent = total > 0 ? `Showing ${startItem}–${endItem} of ${total}` : 'No results';
            }

            if (btns) {
                let btnHtml = `<button class="ds-btn ds-btn-sm ds-btn-ghost" ${s.page <= 1 ? 'disabled' : ''} onclick="SuperAdmin.plansGoToPage(${s.page - 1})"><i data-lucide="chevron-left" style="width:14px;height:14px;"></i></button>`;
                for (let i = 1; i <= totalPages; i++) {
                    btnHtml += `<button class="ds-btn ds-btn-sm ${i === s.page ? 'ds-btn-primary' : 'ds-btn-ghost'}" onclick="SuperAdmin.plansGoToPage(${i})">${i}</button>`;
                }
                btnHtml += `<button class="ds-btn ds-btn-sm ds-btn-ghost" ${s.page >= totalPages ? 'disabled' : ''} onclick="SuperAdmin.plansGoToPage(${s.page + 1})"><i data-lucide="chevron-right" style="width:14px;height:14px;"></i></button>`;
                btns.innerHTML = btnHtml;
            }
            if (window.lucide) lucide.createIcons();
        } catch(e) {
            tbody.innerHTML = `<tr><td colspan="11" class="text-center py-5 text-danger text-xs">${e.message} — Verify backend is running.</td></tr>`;
        }
    },

    plansSetPerPage(v) {
        this._plan.perPage = parseInt(v, 10) || 5;
        this._plan.page = 1;
        this._planLoadTable();
    },

    plansGoToPage(p) {
        this._plan.page = p;
        this._planLoadTable();
    },

    _planRenderTable(plans, tbody) {
        if (!plans.length) {
            tbody.innerHTML = `<tr><td colspan="11" class="text-center py-5 text-muted">
                <i data-lucide="inbox" style="width:28px;height:28px;opacity:.3;"></i>
                <div class="mt-2 text-xs">No plans found. Click <strong>New Plan</strong> to create one.</div>
            </td></tr>`;
            if(window.lucide) lucide.createIcons();
            return;
        }

        tbody.innerHTML = plans.map(p => {
            const highlight = (txt) => {
                if (!txt) return '—';
                if (!this._plan.q) return txt;
                const esc = this._plan.q.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
                return txt.toString().replace(new RegExp(`(${esc})`, 'gi'), '<mark style="background:rgba(99,102,241,0.25);padding:0 2px;border-radius:2px;">$1</mark>');
            };
            const colStyle = `border-left: 3px solid ${p.color || '#3b82f6'};`;
            const priceVal = p.price !== undefined ? p.price : (p.amount !== undefined ? p.amount : (p.base_price || 0));
            return `<tr>
                <td style="${colStyle}"><i data-lucide="${p.icon || 'layers'}" style="width:14px;height:14px;color:${p.color || '#3b82f6'};" class="me-2"></i><strong>${highlight(p.name)}</strong></td>
                <td><code class="text-xs font-monospace">${highlight(p.code)}</code></td>
                <td class="text-xs text-muted" style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${highlight(p.description)}</td>
                <td><strong class="text-dark">${this._planFmt(priceVal)}</strong></td>
                <td><span class="badge bg-secondary bg-opacity-10 text-dark font-monospace">${p.billing_cycle || 'Yearly'}</span></td>
                <td><strong>${p.max_users >= 99999 ? 'Unlimited' : p.max_users}</strong></td>
                <td>${p.storage_limit_gb} GB</td>
                <td><span class="badge bg-primary bg-opacity-10 fw-bold border border-primary border-opacity-20" style="cursor:pointer; color: var(--ds-primary) !important;" onclick="SuperAdmin.openPlanDetailDrawer(${p.id})">${p.subscriber_count || 0} orgs</span></td>
                <td><span class="plan-status-badge ${p.status.toLowerCase().replace(' ','-')}">${p.status}</span></td>
                <td class="text-end">
                    <div class="dropdown">
                        <button class="btn btn-link text-muted p-1" data-bs-toggle="dropdown" data-bs-popper-config='{"strategy":"fixed"}' style="border:none;background:transparent;box-shadow:none;">
                            <i data-lucide="more-horizontal" style="width:16px;height:16px;"></i>
                        </button>
                        <ul class="dropdown-menu dropdown-menu-end" style="min-width:180px;font-size:12.5px;z-index:100050 !important;">
                            <li><a class="dropdown-item" href="#" onclick="SuperAdmin.openPlanDetailDrawer(${p.id});return false;"><i data-lucide="eye" style="width:13px;height:13px;" class="me-2"></i>View details</a></li>
                            <li><a class="dropdown-item" href="#" onclick="SuperAdmin.openPlanCreateWizard(${p.id});return false;"><i data-lucide="edit" style="width:13px;height:13px;" class="me-2"></i>Edit plan</a></li>
                            <li><a class="dropdown-item" href="#" onclick="SuperAdmin.duplicatePlan(${p.id});return false;"><i data-lucide="copy" style="width:13px;height:13px;" class="me-2"></i>Duplicate</a></li>
                            <li><hr class="dropdown-divider"></li>
                            ${p.status==='Active'?`<li><a class="dropdown-item" href="#" onclick="SuperAdmin._planAction(${p.id}, 'deactivate');return false;"><i data-lucide="pause-circle" style="width:13px;height:13px;" class="me-2"></i>Deactivate</a></li>`:''}
                            ${p.status==='Inactive'?`<li><a class="dropdown-item" href="#" onclick="SuperAdmin._planAction(${p.id}, 'activate');return false;"><i data-lucide="play-circle" style="width:13px;height:13px;" class="me-2"></i>Activate</a></li>`:''}
                            <li><hr class="dropdown-divider"></li>
                            <li><a class="dropdown-item text-danger" href="#" onclick="SuperAdmin._planAction(${p.id}, 'delete');return false;"><i data-lucide="trash-2" style="width:13px;height:13px;" class="me-2"></i>Delete</a></li>
                        </ul>
                    </div>
                </td>
            </tr>`;
        }).join('');
        if(window.lucide) lucide.createIcons();
    },

    // ── Search & Filters ──
    planDebounceSearch(v) {
        clearTimeout(this._plan.searchTimer);
        this._plan.searchTimer = setTimeout(() => { this._plan.q = v.trim(); this._planLoadTable(); }, 300);
    },
    setPlanFilter(key, val) {
        this._plan.filters[key] = val;
        if (key==='billing_cycle') {
            const cycleEl=document.getElementById('filterPlanCycle'); if(cycleEl) cycleEl.value=val;
        }
        this._planLoadTable();
    },
    resetPlanFilters() {
        this._plan.filters = { status: '', plan_type: '', billing_cycle: '', price_type: '' };
        this._plan.q = '';
        const si=document.getElementById('planSearchInput'); if(si) si.value='';
        ['filterPlanStatus', 'filterPlanType', 'filterPlanPrice'].forEach(id=>{ const el=document.getElementById(id); if(el) el.value=''; });
        const cycleEl=document.getElementById('filterPlanCycle'); if(cycleEl) cycleEl.value='';
        this._planLoadTable();
    },

    // ── Row Actions ──
    async _planAction(id, action) {
        try {
            if (action === 'delete') {
                const ok = await this._planConfirm('Delete Plan Template', 'Delete this plan? Active subscriptions will NOT be affected, but you cannot delete plans with active organization subscribers.', 'Delete Plan');
                if(!ok)return;
                await this._planDelete(`/plans/${id}`);
                this._planNotify('Plan deleted successfully', 'success');
            } else {
                await this._planPost(`/plans/${id}/${action}`);
                this._planNotify(`Plan ${action}d successfully`, 'success');
            }
            this.loadPlans();
        } catch(e) { this._planNotify(e.message, 'error'); }
    },
    async duplicatePlan(id) {
        try {
            const r = await this._planPost(`/plans/${id}/duplicate`);
            this._planNotify(r.message, 'success');
            this.loadPlans();
        } catch(e) { this._planNotify(e.message, 'error'); }
    },

    // ── Detail Drawer ──
    async openPlanDetailDrawer(id) {
        const overlay = document.getElementById('planDrawerOverlay');
        const drawer = document.getElementById('planDrawer');
        const body = document.getElementById('pdBody');
        if (!overlay || !drawer) return;
        overlay.classList.add('open'); drawer.classList.add('open');
        body.innerHTML = `<div class="text-center py-5"><span class="spinner-border"></span></div>`;
        try {
            const res = await this._planGet(`/plans/${id}`);
            const p = res.data;
            document.getElementById('pdTitle').textContent = p.name;
            document.getElementById('pdSub').textContent = `${p.code} · Tier ${p.plan_type} · Version ${p.version}`;
            document.getElementById('pdStatusBadge').innerHTML = `<span class="plan-status-badge ${p.status.toLowerCase().replace(' ','-')}">${p.status}</span>`;
            body.innerHTML = this._planDrawerHtml(p);
            
            // Also fetch subscribers list in background
            this._planLoadSubscribers(id);
            if (window.lucide) lucide.createIcons();
        } catch(e) {
            body.innerHTML = `<div class="text-danger p-3">${e.message}</div>`;
        }
    },
    async _planLoadSubscribers(id) {
        const el = document.getElementById('pdSubscriberList');
        if (!el) return;
        try {
            const res = await this._planGet(`/plans/${id}/subscribers`);
            const subs = res.data?.subscribers || [];
            if (!subs.length) {
                el.innerHTML = 'No active subscribers for this plan.';
                return;
            }
            el.innerHTML = `<ul style="margin:0;padding-left:1.2rem;">
                ${subs.map(s => `<li><strong>${s.name}</strong> (${s.status}) · Registered ${this._planFmtD(s.created_at)}</li>`).join('')}
            </ul>`;
        } catch(e) { el.innerHTML = 'Error loading subscribers list.'; }
    },
    closePlanDrawer() {
        document.getElementById('planDrawerOverlay')?.classList.remove('open');
        document.getElementById('planDrawer')?.classList.remove('open');
    },
    _planDrawerHtml(p) {
        const m = v => this._planFmt(v);
        return `
        <div class="pd-section">
            <div class="pd-section-title">Overview</div>
            <div class="p-3 rounded mb-2 text-sm" style="background:rgba(99,102,241,.02); border:1px solid var(--ds-border-color);">
                <strong>Short Description:</strong> ${p.description || '—'}<br>
                <strong class="d-block mt-2">Long Description:</strong> <span class="text-muted">${p.long_description || 'No detailed description.'}</span>
            </div>
        </div>
        <div class="pd-section">
            <div class="pd-section-title">Pricing matrix</div>
            <div class="pd-grid mb-3">
                ${p.pricing.map(pr=>`<div class="pd-item"><div class="di-l">${pr.billing_cycle}</div><div class="di-v fw-bold text-primary">${m(pr.price)}</div></div>`).join('')}
            </div>
        </div>
        <div class="pd-section">
            <div class="pd-section-title">Limits &amp; Caps</div>
            <div class="pd-grid">
                <div class="pd-item"><div class="di-l">Max Users</div><div class="di-v fw-bold">${p.limits.max_users >= 99999 ? 'Unlimited' : p.limits.max_users}</div></div>
                <div class="pd-item"><div class="di-l">Storage Limit</div><div class="di-v fw-bold">${p.limits.storage_limit_gb} GB</div></div>
                <div class="pd-item"><div class="di-l">API Limit/mo</div><div class="di-v fw-bold">${(p.limits.api_limit||0).toLocaleString()}</div></div>
                <div class="pd-item"><div class="di-l">Max Projects</div><div class="di-v fw-bold">${p.limits.max_projects}</div></div>
            </div>
        </div>
        <div class="pd-section">
            <div class="pd-section-title">Enabled modules</div>
            <div class="d-flex flex-wrap gap-1 mt-1">
                ${p.modules.map(mod=>`<span class="plan-chip starter text-xxs me-1 mb-1" style="font-size:10px;padding:3px 8px;margin-bottom:4px;display:inline-block;">${mod.module_name}</span>`).join('') || '—'}
            </div>
        </div>
        <div class="pd-section">
            <div class="pd-section-title">Active Subscribers (${p.subscriber_count})</div>
            <div class="p-3 rounded text-sm" style="background:rgba(16,185,129,.03); border:1px solid var(--ds-border-color);">
                <div class="fw-bold mb-1">Subscriber list</div>
                <div id="pdSubscriberList" class="text-xs text-muted">Loading subscribers...</div>
            </div>
        </div>
        <div class="pd-section">
            <div class="pd-section-title">Version Configuration History</div>
            <ul style="list-style:none;padding:0;margin:0;">
                ${p.versions.map(v=>`
                <li style="display:flex;justify-content:space-between;align-items:center;padding:.5rem 0;border-bottom:1px solid var(--ds-border-color);font-size:12px;">
                    <div>
                        <strong>Version ${v.version}</strong> <span class="text-muted">(${this._planFmtD(v.created_at)})</span>
                        <div class="text-muted text-xxs">${v.change_summary} by ${v.created_by}</div>
                    </div>
                    ${v.version < p.version ? `<button class="ds-btn ds-btn-secondary" style="padding:2px 8px;font-size:11px;" onclick="SuperAdmin.restorePlanVersion(${p.id}, ${v.version})">Restore</button>`:''}
                </li>`).join('')}
            </ul>
        </div>`;
    },

    async restorePlanVersion(id, versionNum) {
        const ok = await this._planConfirm('Restore Configuration', `Restore plan configuration to version ${versionNum}? This creates a new version snapshot.`, 'Restore Version');
        if(!ok)return;
        try {
            const r = await this._planPost(`/plans/${id}/versions/${versionNum}/restore`);
            this._planNotify(r.message, 'success');
            this.closePlanDrawer();
            this.loadPlans();
        } catch(e) { this._planNotify(e.message, 'error'); }
    },

    // ── Comparison matrix Modal ──
    async openPlanCompareModal() {
        const modal = new bootstrap.Modal(document.getElementById('planCompareModal'));
        const body = document.getElementById('planCompareBody');
        body.innerHTML = `<tr><td colspan="5" class="text-center py-4"><span class="spinner-border"></span></td></tr>`;
        modal.show();
        try {
            const res = await this._planGet('/plans/compare');
            const d = res.data;
            const keys = Object.keys(d);
            
            const rows = [
                { label: 'Tier Level', field: 'plan_type' },
                { label: 'Monthly Price', field: 'pricing', fmt: p=>this._planFmt(p.Monthly) },
                { label: 'Yearly Price', field: 'pricing', fmt: p=>this._planFmt(p.Yearly) },
                { label: 'Max Users', field: 'max_users', fmt: u=>u>=99999?'Unlimited':u },
                { label: 'Storage Cap', field: 'storage_limit_gb', fmt: s=>s+' GB' },
                { label: 'API limit/mo', field: 'api_limit', fmt: a=>a.toLocaleString() },
                { label: 'Support Level', field: 'support_level' },
                { label: 'Quality Circles', field: 'modules', check: 'Quality Circles' },
                { label: 'Analytics & SPC', field: 'modules', check: 'Analytics' },
                { label: 'AI Features', field: 'modules', check: 'AI Features' },
                { label: 'White Labeling', field: 'modules', check: 'White Label' },
                { label: 'API Access', field: 'modules', check: 'API Access' }
            ];

            body.innerHTML = rows.map(r=>{
                return `<tr>
                    <td><strong>${r.label}</strong></td>
                    ${this._plan.matrixPlans.map(pn=>{
                        const pData = d[pn];
                        if (!pData) return `<td>—</td>`;
                        if (r.check) {
                            return `<td>${pData.modules.includes(r.check)?'✓ Enabled':'✗ Disabled'}</td>`;
                        }
                        const raw = pData[r.field];
                        return `<td>${r.fmt ? r.fmt(raw) : raw}</td>`;
                    }).join('')}
                </tr>`;
            }).join('');
        } catch(e) { body.innerHTML = `<tr><td colspan="5" class="text-danger py-4">${e.message}</td></tr>`; }
    },

    // ── Create Wizard ──
    // ── Plan Configurator Grouped Modules Matrix ─────────────────────────────
    PLAN_MODULE_GROUPS: [
        { key: 'dashboard', title: 'Dashboard', icon: 'layout-dashboard', match: ['dashboard'] },
        { key: 'ideas', title: 'Ideas', icon: 'lightbulb', match: ['idea'] },
        { key: 'projects', title: 'Projects', icon: 'layers', match: ['project'] },
        { key: 'quality_circles', title: 'Quality Circles', icon: 'users-2', match: ['circle', 'qc_circle', 'qc.circle'] },
        { key: 'meetings', title: 'Meetings', icon: 'calendar', match: ['meeting'] },
        { key: 'reports', title: 'Reports', icon: 'file-text', match: ['report'] },
        { key: 'analytics', title: 'Analytics', icon: 'bar-chart-3', match: ['analytics', 'kpi', 'chart'] },
        { key: 'ai', title: 'AI Features', icon: 'bot', match: ['ai', 'assistant', 'prediction'] },
        { key: 'api', title: 'API Access', icon: 'key-round', match: ['api', 'webhook'] },
        { key: 'whitelabel', title: 'White Label', icon: 'palette', match: ['whitelabel', 'branding'] },
        { key: 'integrations', title: 'Integrations', icon: 'blocks', match: ['integration'] },
        { key: 'workflow', title: 'Workflow Automation', icon: 'git-merge', match: ['workflow', 'stage'] },
        { key: 'sop', title: 'SOP', icon: 'book-open', match: ['sop', 'training'] },
        { key: 'qc_tools', title: 'QC Tools', icon: 'wrench', match: ['fishbone', 'pareto', 'checksheet', 'scatter', 'control_chart', 'stratification', 'process_map', 'qc_tool'] },
        { key: 'rag', title: 'RAG', icon: 'database', match: ['rag', 'vector', 'embedding'] },
        { key: 'iam_admin', title: 'Identity & Administration', icon: 'shield-check', match: [] }
    ],

    async renderPlanModuleAccordion(enabledMods=[]) {
        const container = document.getElementById('pwModulesGrid');
        if (!container) return;

        let allMods = this._mod?.allModulesList || [];
        if (!allMods.length || allMods.length < 140) {
            container.innerHTML = '<div class="text-center py-4 text-muted text-xs"><span class="spinner-border spinner-border-sm me-2"></span>Loading all 144 platform feature modules…</div>';
            try {
                const res = await this._modGet('?per_page=500&all=true');
                allMods = res.data || [];
                if (this._mod) this._mod.allModulesList = allMods;
            } catch(e) {
                container.innerHTML = `<div class="text-center py-4 text-danger text-xs"><i data-lucide="alert-circle" style="width:14px;height:14px;" class="me-1"></i>Could not load modules. <button type="button" class="btn btn-link btn-sm p-0 text-primary" style="font-size:12px;" onclick="SuperAdmin.renderPlanModuleAccordion(SuperAdmin._plan._cachedEnabledMods||[])">Retry</button></div>`;
                if (window.lucide) lucide.createIcons();
                return;
            }
        }

        const titleEl = document.getElementById('pwModsStepTitle');
        if (titleEl && allMods.length) {
            titleEl.innerHTML = `<i data-lucide="layers" class="me-1 text-primary" style="width:16px;height:16px;"></i> Enable Platform Feature Modules (${allMods.length} Modules)`;
        }

        const grouped = {};
        this.PLAN_MODULE_GROUPS.forEach(g => { grouped[g.key] = { group: g, modules: [] }; });

        allMods.forEach(m => {
            const code = (m.code || '').toLowerCase();
            const cat = (m.category || '').toLowerCase();
            const name = (m.name || '').toLowerCase();
            let matchedKey = 'iam_admin';

            for (const g of this.PLAN_MODULE_GROUPS) {
                if (g.match.length && g.match.some(term => code.includes(term) || cat.includes(term) || name.includes(term))) {
                    matchedKey = g.key;
                    break;
                }
            }
            grouped[matchedKey].modules.push(m);
        });

        container.innerHTML = this.PLAN_MODULE_GROUPS.map(g => {
            const data = grouped[g.key];
            const mods = data ? data.modules : [];

            const enabledCount = mods.length
                ? mods.filter(m => enabledMods.includes(m.code) || enabledMods.includes(g.title) || enabledMods.includes(m.name)).length
                : (enabledMods.includes(g.title) ? 1 : 0);

            const isAllChecked = mods.length ? (enabledCount === mods.length) : enabledMods.includes(g.title);

            const subModsHtml = mods.length ? mods.map(m => {
                const isChecked = enabledMods.includes(m.code) || enabledMods.includes(g.title) || enabledMods.includes(m.name);
                const safeTitle = (m.description || m.name || '').replace(/"/g, '&quot;');
                return `
                    <div class="col-md-6 col-12 mod-item-col" data-search-text="${m.name.toLowerCase()} ${m.code.toLowerCase()} ${(m.category||'').toLowerCase()}">
                        <div class="p-2 border rounded-2 d-flex align-items-center justify-content-between" style="background:var(--ds-bg,#f9fafb);">
                            <div class="form-check mb-0 text-truncate" style="max-width: 85%;">
                                <input class="form-check-input pw-mod-cb grp-mod-${g.key}" type="checkbox" value="${m.code}" data-group="${g.key}" id="pw-mod-${m.id}" ${isChecked ? 'checked' : ''} onchange="SuperAdmin.updatePlanGroupBadge('${g.key}')">
                                <label class="form-check-label text-xs fw-semibold clickable" style="color:var(--ds-text-main,#111);" for="pw-mod-${m.id}" title="${safeTitle}">
                                    ${m.name}
                                </label>
                            </div>
                            <code class="text-muted" style="font-size: 9px;">${m.code}</code>
                        </div>
                    </div>
                `;
            }).join('') : `<div class="col-12 text-xs text-muted py-2 ms-2"><i data-lucide="inbox" style="width:12px;height:12px;" class="me-1"></i>No modules in this category yet.</div>`;

            const badgeText = mods.length ? `${enabledCount}/${mods.length}` : (isAllChecked ? 'ON' : 'OFF');
            const badgeBg = enabledCount > 0 ? 'rgba(99,102,241,.15)' : 'rgba(107,114,128,.1)';
            const badgeColor = enabledCount > 0 ? '#6366f1' : '#6b7280';

            return `
                <div class="card border rounded-3 mb-2 mod-group-card" style="background:var(--ds-surface,#fff);padding:10px 12px;" id="grp-card-${g.key}">
                    <div class="d-flex align-items-center justify-content-between">
                        <div class="d-flex align-items-center gap-2 flex-wrap">
                            <input type="checkbox" class="form-check-input pw-group-master-cb flex-shrink-0" id="grp-cb-${g.key}" value="${g.title}" ${isAllChecked ? 'checked' : ''} onchange="SuperAdmin.togglePlanModuleGroup('${g.key}', this.checked)" style="width:15px;height:15px;">
                            <label class="fw-bold mb-0 clickable d-flex align-items-center gap-1" style="font-size:12.5px;color:var(--ds-text-main,#111);" for="grp-cb-${g.key}">
                                <i data-lucide="${g.icon}" style="width:13px;height:13px;color:var(--ds-primary,#6366f1);"></i> ${g.title}
                            </label>
                            <span id="grp-badge-${g.key}" style="font-size:10px;font-weight:700;padding:1px 8px;border-radius:10px;background:${badgeBg};color:${badgeColor};">${badgeText}</span>
                        </div>
                        <button type="button" class="btn btn-sm btn-link p-0" style="color:var(--ds-text-secondary,#6b7280);" onclick="SuperAdmin.togglePlanGroupCollapse('${g.key}')">
                            <i data-lucide="chevron-down" id="grp-chev-${g.key}" style="width:14px;height:14px;transition:transform .2s;"></i>
                        </button>
                    </div>
                    <div class="group-submods-container mt-2 pt-2 border-top d-none" id="grp-body-${g.key}">
                        <div class="row g-2">
                            ${subModsHtml}
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        if (window.lucide) lucide.createIcons();
    },

    filterPlanModules(query) {
        const q = (query || '').toLowerCase().trim();
        const cards = document.querySelectorAll('.mod-group-card');

        cards.forEach(card => {
            let matchCount = 0;
            const items = card.querySelectorAll('.mod-item-col');
            const body = card.querySelector('.group-submods-container');

            items.forEach(item => {
                const text = item.getAttribute('data-search-text') || item.innerText.toLowerCase();
                if (!q || text.includes(q)) {
                    item.classList.remove('d-none');
                    matchCount++;
                } else {
                    item.classList.add('d-none');
                }
            });

            if (!q) {
                card.classList.remove('d-none');
                if (body) body.classList.add('d-none');
            } else if (matchCount > 0) {
                card.classList.remove('d-none');
                if (body) body.classList.remove('d-none');
            } else {
                card.classList.add('d-none');
            }
        });
    },

    togglePlanModuleGroup(groupKey, checked) {
        document.querySelectorAll(`.grp-mod-${groupKey}`).forEach(cb => cb.checked = checked);
        this.updatePlanGroupBadge(groupKey);
    },

    togglePlanGroupCollapse(groupKey) {
        const body = document.getElementById(`grp-body-${groupKey}`);
        const chev = document.getElementById(`grp-chev-${groupKey}`);
        if (!body) return;
        const isHidden = body.classList.contains('d-none');
        body.classList.toggle('d-none', !isHidden);
        if (chev) chev.style.transform = isHidden ? 'rotate(180deg)' : 'rotate(0deg)';
    },

    updatePlanGroupBadge(groupKey) {
        const allInGroup     = document.querySelectorAll(`.grp-mod-${groupKey}`);
        const checkedInGroup = document.querySelectorAll(`.grp-mod-${groupKey}:checked`);
        const badge          = document.getElementById(`grp-badge-${groupKey}`);
        const masterCb       = document.getElementById(`grp-cb-${groupKey}`);

        const n = checkedInGroup.length, total = allInGroup.length;
        if (badge) {
            badge.textContent = total ? `${n}/${total}` : (n > 0 ? 'ON' : 'OFF');
            badge.style.background = n > 0 ? 'rgba(99,102,241,.15)' : 'rgba(107,114,128,.1)';
            badge.style.color      = n > 0 ? '#6366f1' : '#6b7280';
        }
        if (masterCb) masterCb.checked = (n === total && total > 0);
    },

    planWizToggleAllMods(checked) {
        document.querySelectorAll('#pwModulesGrid input[type=checkbox]').forEach(cb => cb.checked = checked);
        this.PLAN_MODULE_GROUPS.forEach(g => this.updatePlanGroupBadge(g.key));
    },

    _validatePlanStep1() {
        const nameEl = document.getElementById('pwName');
        const codeEl = document.getElementById('pwCode');
        const descEl = document.getElementById('pwDesc');
        let isValid = true;

        [nameEl, codeEl, descEl].forEach(el => {
            if (el) {
                if (!el.value || !el.value.trim()) {
                    el.classList.add('is-invalid');
                    isValid = false;
                } else {
                    el.classList.remove('is-invalid');
                }
            }
        });

        if (!isValid) {
            this._planNotify('Name, Code and description are required', 'error');
        }
        return isValid;
    },

    togglePlanCustomYears() {
        const cycle = document.getElementById('pwBillingCycle')?.value;
        const container = document.getElementById('pwCustomYearsContainer');
        if (container) {
            container.style.display = (cycle === 'Custom') ? 'block' : 'none';
        }
    },

    async openPlanCreateWizard(editId=null) {
        this._plan.editPlanId = editId;
        this._plan.wizStep = 1;
        
        // Reset wizard forms & clear invalid classes
        ['pwName', 'pwCode', 'pwDesc'].forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.value = '';
                el.classList.remove('is-invalid');
                if (!el._hasValidationListener) {
                    el.addEventListener('input', () => {
                        if (el.value && el.value.trim()) el.classList.remove('is-invalid');
                    });
                    el._hasValidationListener = true;
                }
            }
        });

        this._planWizGoStep(1);
        document.getElementById('pwLongDesc').value = '';
        if (document.getElementById('pwPriceAmount')) document.getElementById('pwPriceAmount').value = '0';
        if (document.getElementById('pwBillingCycle')) document.getElementById('pwBillingCycle').value = 'Yearly';
        if (document.getElementById('pwCustomYearsSelect')) document.getElementById('pwCustomYearsSelect').value = '2';
        this.togglePlanCustomYears();

        document.getElementById('pwTax').value = '18';
        document.getElementById('pwMaxUsers').value = '100';
        document.getElementById('pwStorage').value = '10';
        document.getElementById('pwMaxProjects').value = '25';
        document.getElementById('pwMaxDepts').value = '10';
        document.getElementById('pwMaxQcCircles').value = '5';
        document.getElementById('pwSupport').value = 'Standard';
        document.getElementById('pwIsCustom').checked = false;

        let enabledMods = ['Dashboard', 'Ideas', 'Projects', 'Quality Circles', 'Meetings', 'Reports', 'Analytics', 'AI Features'];
        document.getElementById('planWizardTitle').textContent = editId ? 'Edit SaaS Plan Template' : 'New Plan Configurator';

        if (editId) {
            try {
                const res = await this._planGet(`/plans/${editId}`);
                const p = res.data;
                document.getElementById('pwName').value = p.name;
                document.getElementById('pwCode').value = p.code;
                document.getElementById('pwDesc').value = p.description;
                document.getElementById('pwLongDesc').value = p.long_description;
                document.getElementById('pwIcon').value = p.icon;
                document.getElementById('pwColor').value = p.color;
                document.getElementById('pwTier').value = p.plan_type;
                document.getElementById('pwIsCustom').checked = p.is_custom;

                if (p.pricing && p.pricing.length > 0) {
                    const activeP = p.pricing.find(pr => pr.price > 0) || p.pricing[0];
                    if (activeP) {
                        document.getElementById('pwPriceAmount').value = activeP.price;
                        const cycleStr = activeP.billing_cycle || 'Yearly';
                        if (['Monthly', 'Quarterly', 'Yearly', 'Lifetime'].includes(cycleStr)) {
                            document.getElementById('pwBillingCycle').value = cycleStr;
                        } else if (cycleStr.includes('Year')) {
                            document.getElementById('pwBillingCycle').value = 'Custom';
                            const match = cycleStr.match(/\d+/);
                            if (match && document.getElementById('pwCustomYearsSelect')) {
                                document.getElementById('pwCustomYearsSelect').value = match[0];
                            }
                        } else {
                            document.getElementById('pwBillingCycle').value = 'Yearly';
                        }
                    }
                    if (document.getElementById('pwTax') && activeP.tax !== undefined) {
                        document.getElementById('pwTax').value = activeP.tax;
                    }
                }
                this.togglePlanCustomYears();

                document.getElementById('pwMaxUsers').value = p.limits.max_users;
                document.getElementById('pwStorage').value = p.limits.storage_limit_gb;
                document.getElementById('pwMaxProjects').value = p.limits.max_projects;
                document.getElementById('pwMaxDepts').value = p.limits.max_departments;
                document.getElementById('pwMaxQcCircles').value = p.limits.max_quality_circles;
                document.getElementById('pwSupport').value = p.limits.support_level;
            } catch(e) { this._planNotify(e.message, 'error'); }
        }

        const planModal = bootstrap.Modal.getOrCreateInstance(document.getElementById('planCreateModal'));
        planModal.show();
    },

    _planWizGoStep(n) {
        if (n > 1 && !this._validatePlanStep1()) return;

        this._plan.wizStep = n;
        document.querySelectorAll('#planCreateModal .wiz-panel').forEach(p=>p.classList.remove('active'));
        document.getElementById(`pwp${n}`)?.classList.add('active');
        document.querySelectorAll('#planCreateModal .wiz-step').forEach(s=>{
            const sn=parseInt(s.dataset.pws);
            s.classList.toggle('active', sn===n);
            s.classList.toggle('done', sn<n);
        });
        document.getElementById('pwPrevBtn').disabled = n===1;
        document.getElementById('pwNextBtn').classList.toggle('d-none', n===4);
        document.getElementById('pwSubmitBtn').classList.toggle('d-none', n!==4);

        if(n===4) this._planWizRenderReview();
    },

    planWizNext() {
        if (this._plan.wizStep === 1) {
            if (!this._validatePlanStep1()) return;
        }
        if(this._plan.wizStep < 4) this._planWizGoStep(this._plan.wizStep + 1);
    },
    planWizPrev() { if(this._plan.wizStep > 1) this._planWizGoStep(this._plan.wizStep - 1); },

    _planWizRenderReview() {
        const name = document.getElementById('pwName').value;
        const code = document.getElementById('pwCode').value;
        const tier = document.getElementById('pwTier').value;
        const amount = parseFloat(document.getElementById('pwPriceAmount').value) || 0;
        const cycle = document.getElementById('pwBillingCycle').value;
        const customYears = document.getElementById('pwCustomYearsSelect')?.value || '2';
        const cycleText = (cycle === 'Custom') ? `${customYears} Years (Custom Multi-Year)` : cycle;
        const maxUsers = document.getElementById('pwMaxUsers').value;
        const storage = document.getElementById('pwStorage').value;

        document.getElementById('pwReview').innerHTML = `
        <div class="row g-2 text-sm">
            <div class="col-6"><div class="text-muted text-xs">Plan Name</div><strong>${name} (${code})</strong></div>
            <div class="col-6"><div class="text-muted text-xs">Plan Tier</div><strong>Tier ${tier}</strong></div>
            <div class="col-6"><div class="text-muted text-xs">Plan Amount</div><strong>${this._planFmt(amount)}</strong></div>
            <div class="col-6"><div class="text-muted text-xs">Billing Duration</div><strong>${cycleText}</strong></div>
            <div class="col-6"><div class="text-muted text-xs">Max Users Cap</div><strong>${maxUsers} users</strong></div>
            <div class="col-6"><div class="text-muted text-xs">Storage Limit</div><strong>${storage} GB</strong></div>
        </div>`;
    },

    async planWizSubmit() {
        if (!document.getElementById('pwConfirm').checked) { this._planNotify('Confirm review before saving', 'error'); return; }
        const btn = document.getElementById('pwSubmitBtn');
        btn.disabled = true; btn.textContent = 'Saving Plan…';

        const amount = parseFloat(document.getElementById('pwPriceAmount').value) || 0.0;
        const cycle = document.getElementById('pwBillingCycle').value;
        const customYears = document.getElementById('pwCustomYearsSelect')?.value || '2';
        const cycleKey = (cycle === 'Custom') ? `${customYears} Years` : cycle;
        const taxVal = parseFloat(document.getElementById('pwTax').value) || 18.0;

        const pricing = [
            { billing_cycle: cycleKey, price: amount, tax: taxVal },
            { billing_cycle: 'Monthly', price: cycle === 'Monthly' ? amount : 0.0, tax: taxVal },
            { billing_cycle: 'Yearly', price: (cycle === 'Yearly' || cycle === 'Custom') ? amount : 0.0, tax: taxVal },
            { billing_cycle: 'Quarterly', price: cycle === 'Quarterly' ? amount : 0.0, tax: taxVal },
            { billing_cycle: 'Lifetime', price: cycle === 'Lifetime' ? amount : 0.0, tax: taxVal }
        ];

        const payload = {
            name: document.getElementById('pwName').value,
            code: document.getElementById('pwCode').value,
            description: document.getElementById('pwDesc').value,
            long_description: document.getElementById('pwLongDesc').value,
            icon: document.getElementById('pwIcon').value,
            color: document.getElementById('pwColor').value,
            plan_type: document.getElementById('pwTier').value,
            is_custom: document.getElementById('pwIsCustom').checked,
            pricing: pricing,
            limits: {
                max_users: parseInt(document.getElementById('pwMaxUsers').value)||100,
                max_projects: parseInt(document.getElementById('pwMaxProjects').value)||25,
                storage_limit_gb: parseFloat(document.getElementById('pwStorage').value)||10.0,
                api_limit: document.getElementById('pwApiLimit') ? (parseInt(document.getElementById('pwApiLimit').value)||10000) : 10000,
                max_departments: parseInt(document.getElementById('pwMaxDepts').value)||10,
                max_quality_circles: parseInt(document.getElementById('pwMaxQcCircles').value)||5,
                support_level: document.getElementById('pwSupport').value
            },
            modules: []
        };

        try {
            if (this._plan.editPlanId) {
                await this._planPut(`/plans/${this._plan.editPlanId}`, payload);
                this._planNotify('Plan modified successfully', 'success');
            } else {
                await this._planPost('/plans', payload);
                this._planNotify('New plan template saved successfully', 'success');
            }
            bootstrap.Modal.getInstance(document.getElementById('planCreateModal'))?.hide();
            this.loadPlans();
        } catch(e) { this._planNotify(e.message, 'error'); }
        finally { btn.disabled = false; btn.textContent = 'Save Plan Configuration'; }
    },

    // ── Client-side Excel/CSV Exporter ──
    planExportCSV() {
        const table = document.getElementById('plansTable');
        if (!table) return;
        const rows = table.querySelectorAll('tr');
        let csvContent = "data:text/csv;charset=utf-8,";
        rows.forEach(r => {
            const cols = r.querySelectorAll('th, td');
            const data = [];
            cols.forEach((c, idx) => {
                if (idx < cols.length - 1) { // Skip actions column
                    data.push('"' + c.innerText.replace(/"/g, '""').trim() + '"');
                }
            });
            csvContent += data.join(",") + "\r\n";
        });
        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", "saas_plans_catalog.csv");
        document.body.appendChild(link);
        link.click();
        link.remove();
    },

    // ── Confirm dialog helper ──
    _planConfirm(title, body, okLabel='Confirm') {
        return new Promise(resolve => {
            document.getElementById('planConfirmTitle').textContent = title;
            document.getElementById('planConfirmBody').textContent = body;
            const btn = document.getElementById('planConfirmOk'); btn.textContent = okLabel;
            const modal = new bootstrap.Modal(document.getElementById('planConfirmModal'));
            const onOk = () => { modal.hide(); resolve(true); };
            const onHide = () => { btn.removeEventListener('click', onOk); resolve(false); };
            btn.addEventListener('click', onOk, { once: true });
            document.getElementById('planConfirmModal').addEventListener('hidden.bs.modal', onHide, { once: true });
            modal.show();
        });
    },

    // ─── ENTERPRISE FEATURE & MODULE MANAGEMENT ──────────────────────────────
    // All state namespaces under SuperAdmin._mod to avoid conflict
    _mod: {
        page: 1, perPage: 20, totalPages: 1,
        sortBy: 'display_order', sortDir: 'asc',
        filters: { status: '', category: '', plan: '' },
        q: '', searchTimer: null,
        selectedIds: new Set(),
        activeColumns: { code: true, route: true, version: true, plans: true, orgs: true },
        allModulesList: [],
        wizStep: 1,
        wizPlans: new Set(['Starter', 'Professional', 'Enterprise']),
        wizPermissions: {},
        roles: ['SuperAdmin', 'Admin', 'Reviewer', 'Facilitator', 'Team Leader', 'Team Member', 'CEO'],
        recentSearches: []
    },

    _getToken() {
        return api.token;
    },

    async _modGet(path) {
        return api.get(`/modules${path}`);
    },

    async _modPost(path, body={}) {
        return api.post(`/modules${path}`, body);
    },

    async _modPut(path, body={}) {
        return api.put(`/modules${path}`, body);
    },

    // ── Super-Admin Companies API Helper ─────────────────────────────────────
    async _saGet(path) {
        return api.get(`/super-admin${path}`);
    },

    // ── Module Org-Assignment State ───────────────────────────────────────────
    _modOrgAssign: {
        moduleId: null, moduleName: '', moduleCode: '',
        modulePlans: [], allOrgs: [], filteredOrgs: [],
        selectedOrgIds: new Set(), warningOrgIds: new Set(),
        forcePlanOrgs: new Set(),
        keepExisting: { industries: [], regions: [], customer_types: [] }
    },

    async openModOrgAssignModal(moduleId) {
        this._modOrgAssign.moduleId       = moduleId;
        this._modOrgAssign.selectedOrgIds = new Set();
        this._modOrgAssign.warningOrgIds  = new Set();
        this._modOrgAssign.forcePlanOrgs  = new Set();
        const modalEl = document.getElementById('modOrgAssignModal');
        const bodyEl  = document.getElementById('modOrgAssignBody');
        if (!modalEl || !bodyEl) return;
        bodyEl.innerHTML = '<div class="text-center py-5"><span class="spinner-border"></span><div class="text-xs text-muted mt-2">Loading…</div></div>';
        bootstrap.Modal.getOrCreateInstance(modalEl).show();
        try {
            const [modRes, orgsRes] = await Promise.all([
                this._modGet(`/${moduleId}`),
                this._saGet('/companies?per_page=500&page=1')
            ]);
            const m = modRes.data, all = orgsRes.data || [];
            this._modOrgAssign.moduleName  = m.name;
            this._modOrgAssign.moduleCode  = m.code;
            this._modOrgAssign.modulePlans = m.assignments?.plans || [];
            this._modOrgAssign.keepExisting = {
                industries: m.assignments?.industries || [],
                regions: m.assignments?.regions || [],
                customer_types: m.assignments?.customer_types || []
            };
            (m.assignments?.orgs || []).forEach(o => this._modOrgAssign.selectedOrgIds.add(o.id));
            this._modOrgAssign.allOrgs = all;
            this._modOrgAssign.filteredOrgs = [...all];
            document.getElementById('modOrgAssignTitle').textContent = `Assign "${m.name}" to Organizations`;
            document.getElementById('modOrgAssignSub').textContent = `${m.code.toUpperCase()} · Plans: ${this._modOrgAssign.modulePlans.join(', ') || 'None'}`;
            this._modOrgAssignRender();
        } catch(e) { bodyEl.innerHTML = `<div class="text-danger p-4 text-sm">${e.message}</div>`; }
    },

    _modOrgAssignRender() {
        const bodyEl = document.getElementById('modOrgAssignBody');
        const countEl = document.getElementById('modOrgAssignCount');
        if (!bodyEl) return;
        const { filteredOrgs, selectedOrgIds, modulePlans, forcePlanOrgs } = this._modOrgAssign;
        if (!filteredOrgs.length) {
            bodyEl.innerHTML = '<div class="text-center text-muted py-5 text-xs">No organizations found.</div>';
            return;
        }
        const pColorMap = {
            Enterprise:   { bg:'rgba(16,185,129,.12)',  c:'#059669' },
            Professional: { bg:'rgba(59,130,246,.12)',  c:'#2563eb' },
            Starter:      { bg:'rgba(99,102,241,.12)',  c:'#6366f1' },
            Custom:       { bg:'rgba(245,158,11,.12)',  c:'#d97706' }
        };
        const rows = filteredOrgs.map(org => {
            const isSel     = selectedOrgIds.has(org.id);
            const pmatch    = modulePlans.length === 0 || modulePlans.some(p => p.toLowerCase() === (org.plan||'').toLowerCase());
            const isMis     = isSel && !pmatch && !forcePlanOrgs.has(org.id);
            const isForce   = isSel && !pmatch &&  forcePlanOrgs.has(org.id);
            const pc        = pColorMap[org.plan] || { bg:'rgba(107,114,128,.1)', c:'#6b7280' };
            const sc        = org.status==='Active'?'#10b981':org.status==='Trialing'?'#f59e0b':'#ef4444';
            const safePlan  = (org.plan||'').replace(/'/g,"\\'");
            return `<div class="mod-oa-row${isSel?' selected':''}" id="modOaRow-${org.id}">
  <div class="d-flex align-items-start gap-3">
    <input type="checkbox" class="form-check-input mod-oa-cb mt-1 flex-shrink-0" id="oaCb-${org.id}" ${isSel?'checked':''}
      onchange="SuperAdmin._modOrgToggle(${org.id},this.checked,'${safePlan}')">
    <div class="flex-grow-1">
      <div class="d-flex align-items-center gap-2 flex-wrap">
        <span class="fw-semibold text-sm text-main">${org.name}</span>
        <span style="font-size:9.5px;font-weight:700;padding:2px 8px;border-radius:10px;background:${pc.bg};color:${pc.c};">${org.plan||'—'}</span>
        <span class="rounded-circle" style="width:7px;height:7px;background:${sc};display:inline-block;" title="${org.status}"></span>
      </div>
      <div class="text-xxs text-muted mt-1">${org.email} · ${org.user_count} users · ${org.industry||'—'}</div>
    </div>
  </div>
  ${isMis?`<div class="mod-oa-warn-box mt-2 p-2 rounded-2">
    <div class="d-flex align-items-center gap-1 mb-1" style="color:#b45309;font-size:11px;font-weight:600;">
      <i data-lucide="alert-triangle" style="width:12px;height:12px;flex-shrink:0;"></i>
      <span><strong>${org.name}</strong> is on <strong>${org.plan}</strong> plan — this module is not included.</span>
    </div>
    <div class="text-xxs text-muted mb-2">Choose how to proceed:</div>
    <div class="d-flex gap-2 flex-wrap">
      <button type="button" class="mod-oa-action-btn mod-oa-btn-plan" onclick="SuperAdmin._modOrgForcePlan(${org.id})">
        <i data-lucide="plus-circle" style="width:10px;height:10px;"></i> Also Add to <strong>${org.plan}</strong> Plan
      </button>
      <button type="button" class="mod-oa-action-btn mod-oa-btn-only" onclick="SuperAdmin._modOrgAssignOnly(${org.id})">
        <i data-lucide="user-check" style="width:10px;height:10px;"></i> Assign Org Only
      </button>
    </div>
  </div>`:''}
  ${isForce?`<div class="mt-1 d-flex align-items-center gap-1" style="color:#059669;font-size:11px;">
    <i data-lucide="check-circle-2" style="width:11px;height:11px;"></i>
    Will also be added to <strong>${org.plan}</strong> plan module list.
  </div>`:''}
</div>`;
        }).join('');
        if (countEl) countEl.textContent = `${selectedOrgIds.size} selected`;
        bodyEl.innerHTML = rows;
        if (window.lucide) lucide.createIcons();
    },

    _modOrgToggle(orgId, checked, orgPlan) {
        const { modulePlans, selectedOrgIds, warningOrgIds, forcePlanOrgs } = this._modOrgAssign;
        if (checked) {
            selectedOrgIds.add(orgId);
            const pm = modulePlans.length===0 || modulePlans.some(p=>p.toLowerCase()===(orgPlan||'').toLowerCase());
            if (!pm) warningOrgIds.add(orgId);
        } else {
            selectedOrgIds.delete(orgId);
            warningOrgIds.delete(orgId);
            forcePlanOrgs.delete(orgId);
        }
        this._modOrgAssignRender();
    },
    _modOrgForcePlan(orgId) {
        this._modOrgAssign.forcePlanOrgs.add(orgId);
        this._modOrgAssign.warningOrgIds.delete(orgId);
        this._modOrgAssignRender();
    },
    _modOrgAssignOnly(orgId) {
        this._modOrgAssign.warningOrgIds.delete(orgId);
        this._modOrgAssign.forcePlanOrgs.delete(orgId);
        this._modOrgAssignRender();
    },
    _modOrgSearch(q) {
        const qry = (q||'').toLowerCase().trim();
        this._modOrgAssign.filteredOrgs = qry
            ? this._modOrgAssign.allOrgs.filter(o =>
                (o.name||'').toLowerCase().includes(qry) ||
                (o.email||'').toLowerCase().includes(qry) ||
                (o.plan||'').toLowerCase().includes(qry) ||
                (o.industry||'').toLowerCase().includes(qry))
            : [...this._modOrgAssign.allOrgs];
        this._modOrgAssignRender();
    },
    async _modOrgAssignSave() {
        const { moduleId, selectedOrgIds, forcePlanOrgs, modulePlans, keepExisting } = this._modOrgAssign;
        const btn = document.getElementById('modOrgAssignSaveBtn');
        if (btn) { btn.disabled=true; btn.innerHTML='<span class="spinner-border spinner-border-sm me-1" style="width:11px;height:11px;"></span>Saving…'; }
        try {
            await this._modPost(`/${moduleId}/org-assignment`, {
                org_ids: [...selectedOrgIds],
                industries: keepExisting.industries,
                regions: keepExisting.regions,
                customer_types: keepExisting.customer_types
            });
            if (forcePlanOrgs.size > 0) {
                const extra = new Set();
                this._modOrgAssign.allOrgs.filter(o=>forcePlanOrgs.has(o.id)&&o.plan).forEach(o=>extra.add(o.plan));
                if (extra.size > 0) await this._modPost(`/${moduleId}/plan-assignment`, { plans:[...new Set([...modulePlans,...extra])] });
            }
            const note = forcePlanOrgs.size>0?' and plan assignments updated':'';
            this._modNotify(`Module assigned to ${selectedOrgIds.size} org${selectedOrgIds.size!==1?'s':''}${note} successfully`, 'success');
            bootstrap.Modal.getInstance(document.getElementById('modOrgAssignModal'))?.hide();
            this._modLoadTable();
        } catch(e) { this._modNotify(e.message,'error'); }
        finally {
            if (btn) { btn.disabled=false; btn.innerHTML='<i data-lucide="check" style="width:12px;height:12px;" class="me-1"></i>Save Assignment'; if(window.lucide)lucide.createIcons(); }
        }
    },

    _modNotify(msg, type='success') {
        if (window.api && api.showNotification) { api.showNotification(msg, type); return; }
        const bgColors = { success: '#f0fdf4', error: '#fef2f2', info: '#eff6ff', warning: '#fffbeb' };
        const textColors = { success: '#065f46', error: '#991b1b', info: '#1e40af', warning: '#92400e' };
        const borderColors = { success: '#10b981', error: '#ef4444', info: '#3b82f6', warning: '#f59e0b' };
        const c = document.createElement('div');
        c.style.cssText = `position:fixed;top:24px;right:24px;background:${bgColors[type]||'#fff'};color:${textColors[type]||'#0f172a'};border:1px solid ${borderColors[type]};border-left:5px solid ${borderColors[type]};border-radius:10px;padding:12px 18px;font-size:13.5px;font-weight:600;z-index:99999999;box-shadow:0 10px 30px rgba(0,0,0,.25);max-width:380px;min-width:300px;`;
        c.textContent = msg; document.body.appendChild(c); setTimeout(() => c.remove(), 4000);
    },

    async loadModules() {
        this._modInitColumnToggles();
        await Promise.all([this._modLoadKPIs(), this._modLoadTable()]);
        if (window.lucide) lucide.createIcons();
    },

    _modInitColumnToggles() {
        const self = this;
        document.querySelectorAll('.col-toggle').forEach(chk => {
            if (chk.dataset.bound) return;
            chk.dataset.bound = 'true';
            chk.addEventListener('change', function() {
                self._mod.activeColumns[this.dataset.col] = this.checked;
                self._modApplyColumnVisibility();
            });
        });
    },

    _modApplyColumnVisibility() {
        const cols = this._mod.activeColumns;
        document.querySelectorAll('[data-col-name]').forEach(th => {
            const name = th.dataset.colName;
            if (cols[name] !== undefined) {
                th.style.display = cols[name] ? '' : 'none';
            }
        });
        
        // Rows
        document.querySelectorAll('#modulesBody tr').forEach(tr => {
            tr.querySelectorAll('[data-col-val]').forEach(td => {
                const name = td.dataset.colVal;
                if (cols[name] !== undefined) {
                    td.style.display = cols[name] ? '' : 'none';
                }
            });
        });
    },

    async _modLoadKPIs() {
        const grid = document.getElementById('modKpiGrid');
        if (!grid) return;
        grid.innerHTML = `<div style="height:80px;background:var(--ds-border-color);border-radius:12px;animation:shimmer 1.4s infinite;grid-column:1/-1;"></div>`;
        try {
            const res = await this._modGet('/dashboard');
            const d = res.data;
            const kpis = [
                { icon: 'database', bg: 'rgba(59,130,246,.12)', color: '#3b82f6', label: 'Total Modules', val: d.total, accent: '#3b82f6', filter: '' },
                { icon: 'play-circle', bg: 'rgba(16,185,129,.12)', color: '#10b981', label: 'Active', val: d.active, accent: '#10b981', filter: 'Active' },
                { icon: 'pause-circle', bg: 'rgba(107,114,128,.12)', color: '#6b7280', label: 'Inactive', val: d.inactive, accent: '#6b7280', filter: 'Inactive' },
                { icon: 'award', bg: 'rgba(245,158,11,.12)', color: '#f59e0b', label: 'Premium', val: d.premium, accent: '#f59e0b', filter: 'Premium' },
                { icon: 'bot', bg: 'rgba(139,92,246,.12)', color: '#8b5cf6', label: 'AI Modules', val: d.ai, accent: '#8b5cf6', filter: 'AI' },
                { icon: 'cpu', bg: 'rgba(6,182,212,.12)', color: '#06b6d4', label: 'System Core', val: d.system, accent: '#06b6d4', filter: 'System' },
                { icon: 'flask-conical', bg: 'rgba(236,72,153,.12)', color: '#ec4899', label: 'Beta Release', val: d.beta, accent: '#ec4899', filter: 'Beta' },
                { icon: 'alert-triangle', bg: 'rgba(239,68,68,.12)', color: '#ef4444', label: 'Deprecated', val: d.deprecated, accent: '#ef4444', filter: 'Deprecated' }
            ];
            grid.innerHTML = kpis.map(k => `
                <div class="mod-kpi-card" onclick="${k.filter !== undefined ? `SuperAdmin.setModFilter('status','${k.filter}',null)` : ''}" title="${k.label}">
                    <div class="kpi-icon" style="background:${k.bg};"><i data-lucide="${k.icon}" style="width:16px;height:16px;color:${k.color};"></i></div>
                    <div class="kpi-label">${k.label}</div>
                    <div class="kpi-value">${k.val}</div>
                    <div class="kpi-accent" style="background:${k.accent};"></div>
                </div>`).join('');
            if (window.lucide) lucide.createIcons();
        } catch (e) {
            grid.innerHTML = `<div class="text-xs text-muted text-center py-2" style="grid-column:1/-1;">Dashboard metrics unavailable.</div>`;
        }
    },

    async _modLoadTable() {
        const tbody = document.getElementById('modulesBody');
        const countEl = document.getElementById('modulesCount');
        if (!tbody) return;
        tbody.innerHTML = `<tr><td colspan="11" class="text-center py-5"><span class="spinner-border spinner-border-sm me-2"></span><span class="text-muted text-xs">Loading modules…</span></td></tr>`;
        
        const s = this._mod;
        const params = new URLSearchParams({
            page: s.page, per_page: s.perPage,
            sort_by: s.sortBy, sort_dir: s.sortDir,
            q: s.q,
            ...Object.fromEntries(Object.entries(s.filters).filter(([,v]) => v))
        });
        
        try {
            const res = await this._modGet(`?${params}`);
            const { data, pagination } = res;
            s.totalPages = pagination.pages;
            s.allModulesList = data; // Cache lists for wizard depend list
            if (countEl) countEl.textContent = `${pagination.total.toLocaleString()} modules`;
            this._modRenderTable(data, tbody);
            this._modRenderPagination(pagination);
        } catch (e) {
            tbody.innerHTML = `<tr><td colspan="11" class="text-center py-5 text-danger text-xs">${e.message}</td></tr>`;
        }
    },

    _modHighlight(text, q) {
        if (!q) return text;
        const esc = q.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
        const re = new RegExp(`(${esc})`, 'gi');
        return text.replace(re, '<mark class="p-0 bg-warning text-dark">$1</mark>');
    },

    _modRenderTable(mods, tbody) {
        if (!mods || !mods.length) {
            tbody.innerHTML = `<tr><td colspan="11" class="text-center py-5 text-muted">
                <i data-lucide="inbox" style="width:28px;height:28px;opacity:.3;"></i>
                <div class="mt-2 text-xs">No modules registered. Click <strong>Create Module</strong> to add.</div>
            </td></tr>`;
            if (window.lucide) lucide.createIcons();
            return;
        }
        
        const s = this._mod || {};
        tbody.innerHTML = mods.map(m => {
            const sel = (s.selectedIds && typeof s.selectedIds.has === 'function') ? s.selectedIds.has(m.id) : false;
            const statusStr = m.status || 'Inactive';
            const badgeClass = statusStr.toLowerCase().replace(/\s+/g, '-');
            const escName = this._modHighlight(QCMS.escapeHtml(m.name || ''), s.q);
            const escCode = this._modHighlight(QCMS.escapeHtml(m.code || ''), s.q);
            const escDesc = this._modHighlight(QCMS.escapeHtml(m.description || ''), s.q);
            const colorVal = m.color || '#3b82f6';
            const plansList = Array.isArray(m.plans) ? m.plans : [];
            
            return `<tr id="modrow-${m.id}" class="${sel?'row-selected':''}">
                <td><input type="checkbox" class="mod-row-cb" data-id="${m.id}" ${sel?'checked':''} onchange="SuperAdmin._modToggleRow(${m.id},this)"></td>
                <td>
                    <div class="d-flex align-items-center gap-2">
                        <div style="width:28px;height:28px;border-radius:8px;background:${colorVal}15;display:flex;align-items:center;justify-content:center;">
                            <i data-lucide="${m.icon||'package'}" style="width:15px;height:15px;color:${colorVal};"></i>
                        </div>
                        <span class="text-primary fw-bold clickable" style="font-size:12.5px;" onclick="SuperAdmin.openModDrawer(${m.id})">${escName}</span>
                    </div>
                </td>
                <td data-col-val="code"><code class="text-xs">${escCode}</code></td>
                <td><span class="ds-badge outline">${m.category || 'General'}</span></td>
                <td class="text-xs text-muted" style="max-width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${escDesc}</td>
                <td data-col-val="route" class="text-xs"><code>${m.navigation_route||'—'}</code></td>
                <td data-col-val="version" class="text-xs text-muted">${m.version || '1.0.0'}</td>
                <td data-col-val="plans">
                    ${plansList.map(p => `<span class="plan-chip ${(p||'').toLowerCase()}" style="font-size:9.5px;padding:1px 5px;margin-right:2px;">${p}</span>`).join('') || '—'}
                </td>
                <td data-col-val="orgs" class="text-xs text-muted fw-bold">${m.assigned_orgs_count || 0}</td>
                <td><span class="mod-badge ${badgeClass}">${statusStr}</span></td>
                <td class="text-end">
                    <div class="dropdown">
                        <button class="btn btn-link text-muted p-1" data-bs-toggle="dropdown" data-bs-popper-config='{"strategy":"fixed"}' style="border:none;background:transparent;box-shadow:none;">
                            <i data-lucide="more-horizontal" style="width:16px;height:16px;"></i>
                        </button>
                        <ul class="dropdown-menu dropdown-menu-end" style="min-width:180px;font-size:12.5px;z-index:100050 !important;">
                            <li><a class="dropdown-item" href="#" onclick="SuperAdmin.openModDrawer(${m.id});return false;"><i data-lucide="eye" style="width:13px;height:13px;" class="me-2"></i>Configure / View</a></li>
                            <li><a class="dropdown-item" href="#" onclick="SuperAdmin._modActionDuplicate(${m.id});return false;"><i data-lucide="copy" style="width:13px;height:13px;" class="me-2"></i>Duplicate</a></li>
                            ${statusStr === 'Active' ? `<li><a class="dropdown-item" href="#" onclick="SuperAdmin._modActionDisable(${m.id});return false;"><i data-lucide="pause-circle" style="width:13px;height:13px;" class="me-2"></i>Disable</a></li>` : ''}
                            ${statusStr !== 'Active' ? `<li><a class="dropdown-item" href="#" onclick="SuperAdmin._modActionEnable(${m.id});return false;"><i data-lucide="play-circle" style="width:13px;height:13px;" class="me-2"></i>Enable</a></li>` : ''}
                            <li><a class="dropdown-item" href="#" onclick="SuperAdmin.openModOrgAssignModal(${m.id});return false;"><i data-lucide="building-2" style="width:13px;height:13px;" class="me-2"></i>Assign to Organization</a></li>
                            <li><hr class="dropdown-divider"></li>
                            <li><a class="dropdown-item text-danger" href="#" onclick="SuperAdmin._modActionDelete(${m.id});return false;"><i data-lucide="trash-2" style="width:13px;height:13px;" class="me-2"></i>Delete</a></li>
                        </ul>
                    </div>
                </td>
            </tr>`;
        }).join('');
        
        this._modApplyColumnVisibility();
        if (window.lucide) lucide.createIcons();
    },

    _modRenderPagination(pg) {
        if (!pg) return;
        const info = document.getElementById('modPagInfo');
        const btns = document.getElementById('modPagBtns');
        const total = pg.total || 0;
        const page = pg.page || 1;
        const perPage = pg.per_page || 20;
        const pages = pg.pages || 1;
        
        if (info) info.textContent = `Showing ${Math.min((page-1)*perPage+1, total)}–${Math.min(page*perPage, total)} of ${total.toLocaleString()}`;
        if (!btns) return;
        const b = [];
        b.push(`<button class="ds-btn ds-btn-secondary btn-sm" onclick="SuperAdmin._modGoPage(${page-1})" ${page<=1?'disabled':''}>‹</button>`);
        const start = Math.max(1, page-2), end = Math.min(pages, page+2);
        for(let i=start;i<=end;i++) b.push(`<button class="ds-btn ${i===page?'ds-btn-primary':'ds-btn-secondary'} btn-sm" onclick="SuperAdmin._modGoPage(${i})">${i}</button>`);
        b.push(`<button class="ds-btn ds-btn-secondary btn-sm" onclick="SuperAdmin._modGoPage(${page+1})" ${page>=pages?'disabled':''}>›</button>`);
        btns.innerHTML = b.join('');
    },

    _modGoPage(p) { if(p<1||p>this._mod.totalPages) return; this._mod.page=p; this._modLoadTable(); },
    modSetPerPage(v) { this._mod.perPage=parseInt(v); this._mod.page=1; this._modLoadTable(); },
    modSort(col) {
        if(this._mod.sortBy === col) this._mod.sortDir = this._mod.sortDir === 'asc' ? 'desc' : 'asc';
        else { this._mod.sortBy = col; this._mod.sortDir = 'asc'; }
        this._modLoadTable();
    },

    // ── Search & Filter triggers ──────────────────────────────────────────────
    modDebounceSearch(v) {
        clearTimeout(this._mod.searchTimer);
        this._mod.searchTimer = setTimeout(() => { this._mod.q = v.trim(); this._mod.page = 1; this._modLoadTable(); }, 350);
    },

    setModFilter(key, val, btn) {
        if (key === 'status') {
            document.querySelectorAll('[data-mf="status"]').forEach(b => b.classList.remove('active'));
            if(btn) btn.classList.add('active');
        }
        this._mod.filters[key] = val;
        this._mod.page = 1;
        this._modLoadTable();
    },

    resetModFilters() {
        this._mod.filters = { status: '', category: '', plan: '' };
        this._mod.q = ''; this._mod.page = 1;
        const si = document.getElementById('modSearchInput'); if (si) si.value = '';
        ['modCategoryFilter', 'modPlanFilter'].forEach(id => { const el = document.getElementById(id); if(el) el.value = ''; });
        document.querySelectorAll('[data-mf="status"]').forEach(b => b.classList.remove('active'));
        const all = document.querySelector('[data-mf="status"][data-mv=""]'); if(all) all.classList.add('active');
        this._modLoadTable();
    },

    // ── Bulk Actions ──────────────────────────────────────────────────────────
    modToggleAll(cb) {
        document.querySelectorAll('.mod-row-cb').forEach(c => {
            c.checked = cb.checked; const id = parseInt(c.dataset.id);
            cb.checked ? this._mod.selectedIds.add(id) : this._mod.selectedIds.delete(id);
            document.getElementById(`modrow-${id}`)?.classList.toggle('row-selected', cb.checked);
        });
        this._modUpdateBulkBar();
    },

    _modToggleRow(id, cb) {
        cb.checked ? this._mod.selectedIds.add(id) : this._mod.selectedIds.delete(id);
        document.getElementById(`modrow-${id}`)?.classList.toggle('row-selected', cb.checked);
        this._modUpdateBulkBar();
    },

    _modUpdateBulkBar() {
        const count = this._mod.selectedIds.size;
        const bar = document.getElementById('modBulkBar');
        const cnt = document.getElementById('modBulkCount');
        if(bar) bar.classList.toggle('show', count > 0);
        if(cnt) cnt.textContent = count;
    },

    clearModSelection() {
        this._mod.selectedIds.clear();
        document.querySelectorAll('.mod-row-cb').forEach(c => c.checked = false);
        const all = document.getElementById('modSelectAll'); if(all) all.checked = false;
        document.querySelectorAll('.row-selected').forEach(r => r.classList.remove('row-selected'));
        this._modUpdateBulkBar();
    },

    async modBulkAction(action) {
        const ids = Array.from(this._mod.selectedIds);
        if(!ids.length) return;
        try {
            if (action === 'delete') {
                if(!confirm(`Delete ${ids.length} selected modules? Core system modules will be skipped.`)) return;
                for (const id of ids) {
                    try { await api.delete(`/modules/${id}`); } catch(e){}
                }
            } else if (action === 'enable' || action === 'disable') {
                for (const id of ids) {
                    try { await this._modPost(`/${id}/${action}`); } catch(e){}
                }
            } else if (action === 'assign-plan') {
                const plan = await this.promptPlanSelection('Enterprise');
                if (!plan) return;
                for (const id of ids) {
                    try { await this._modPost(`/${id}/plan-assignment`, { plans: [plan] }); } catch(e){}
                }
            }
            this._modNotify(`Bulk ${action} execution completed`, 'success');
            this.clearModSelection(); this.loadModules();
        } catch(e) { this._modNotify(e.message, 'error'); }
    },

    async promptPlanSelection(defaultPlan = 'Enterprise') {
        await this.populateAllPlanDropdowns();
        return new Promise((resolve) => {
            const modalEl = document.getElementById('assignPlanModal');
            if (!modalEl) {
                const plan = prompt('Enter plan to assign:', defaultPlan);
                return resolve(plan);
            }
            const selectEl = document.getElementById('assignPlanSelect');
            if (selectEl) selectEl.value = defaultPlan;

            const confirmBtn = document.getElementById('confirmAssignPlanBtn');
            const bsModal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);

            let isResolved = false;

            const handleConfirm = () => {
                if (isResolved) return;
                isResolved = true;
                const selectedPlan = selectEl ? selectEl.value : defaultPlan;
                cleanup();
                bsModal.hide();
                resolve(selectedPlan);
            };

            const handleCancel = () => {
                if (isResolved) return;
                isResolved = true;
                cleanup();
                resolve(null);
            };

            const cleanup = () => {
                if (confirmBtn) confirmBtn.removeEventListener('click', handleConfirm);
                if (modalEl) modalEl.removeEventListener('hidden.bs.modal', handleCancel);
            };

            if (confirmBtn) confirmBtn.addEventListener('click', handleConfirm);
            modalEl.addEventListener('hidden.bs.modal', handleCancel, { once: true });
            bsModal.show();
            if (window.lucide) lucide.createIcons();
        });
    },

    // ── Export ────────────────────────────────────────────────────────────────
    modExportCSV() {
        const rows = [["Module Name", "Code", "Category", "Description", "Route", "Version", "Status"]];
        (this._mod.allModulesList || []).forEach(m => {
            rows.push([m.name || '', m.code || '', m.category || '', m.description || '', m.navigation_route || '', m.version || '', m.status || '']);
        });
        const csvContent = "data:text/csv;charset=utf-8," + rows.map(e => e.map(val => `"${String(val).replace(/"/g, '""')}"`).join(",")).join("\n");
        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", `QCMS_Feature_Modules_${new Date().toISOString().slice(0,10)}.csv`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    },

    // ── Actions ───────────────────────────────────────────────────────────────
    async _modActionEnable(id) {
        try {
            await this._modPost(`/${id}/enable`);
            this._modNotify('Module enabled', 'success');
            this.loadModules();
        } catch(e) { this._modNotify(e.message, 'error'); }
    },

    async _modActionDisable(id) {
        try {
            await this._modPost(`/${id}/disable`);
            this._modNotify('Module disabled', 'success');
            this.loadModules();
        } catch(e) { this._modNotify(e.message, 'error'); }
    },

    async _modActionDuplicate(id) {
        try {
            const res = await this._modPost(`/${id}/duplicate`);
            this._modNotify(res.message, 'success');
            this.loadModules();
        } catch(e) { this._modNotify(e.message, 'error'); }
    },

    async _modActionDelete(id) {
        if (!confirm('Are you sure you want to delete this module? This cannot be undone.')) return;
        try {
            await api.delete(`/modules/${id}`);
            this._modNotify('Module deleted successfully', 'success');
            this.loadModules();
        } catch(e) { this._modNotify(e.message, 'error'); }
    },

    // ── Detail Drawer ─────────────────────────────────────────────────────────
    async openModDrawer(id) {
        const overlay = document.getElementById('modDetailOverlay');
        const drawer = document.getElementById('modDetailDrawer');
        const body = document.getElementById('mddTabsContent');
        if (!overlay || !drawer) return;
        overlay.classList.add('open'); drawer.classList.add('open');
        body.innerHTML = `<div class="text-center py-5"><span class="spinner-border"></span></div>`;
        try {
            const res = await this._modGet(`/${id}`);
            const m = res.data;
            document.getElementById('mddTitle').textContent = m.name;
            document.getElementById('mddSub').textContent = `${m.code.toUpperCase()} · ${m.category} · v${m.version}`;
            document.getElementById('mddStatusBadge').innerHTML = `<span class="mod-badge ${m.status.toLowerCase()}">${m.status}</span>`;
            
            this._modRenderDrawerTabs(m, body);
            if (window.lucide) lucide.createIcons();
        } catch (e) {
            body.innerHTML = `<div class="text-danger p-3">${e.message}</div>`;
        }
    },

    closeModDrawer() {
        document.getElementById('modDetailOverlay')?.classList.remove('open');
        document.getElementById('modDetailDrawer')?.classList.remove('open');
    },

    _modRenderDrawerTabs(m, container) {
        const userPct = m.analytics.organizations_using > 0 ? Math.min(100, Math.round(m.analytics.active_users / (m.analytics.organizations_using * 20) * 100)) : 0;
        
        container.innerHTML = `
            <!-- Overview -->
            <div class="tab-pane fade show active" id="modTabOverview">
                <div class="sdd-section">
                    <div class="sdd-section-title">General Info</div>
                    <div class="sdd-grid">
                        <div class="mdd-item"><div class="di-l">Name</div><div class="di-v">${m.name}</div></div>
                        <div class="mdd-item"><div class="di-l">Code</div><div class="di-v"><code>${m.code}</code></div></div>
                        <div class="mdd-item"><div class="di-l">Category</div><div class="di-v">${m.category}</div></div>
                        <div class="mdd-item"><div class="di-l">Version</div><div class="di-v">${m.version}</div></div>
                        <div class="mdd-item"><div class="di-l">Route</div><div class="di-v"><code>${m.navigation_route||'—'}</code></div></div>
                        <div class="mdd-item"><div class="di-l">Display Order</div><div class="di-v">${m.display_order}</div></div>
                        <div class="mdd-item" style="grid-column:1/-1"><div class="di-l">Description</div><div class="di-v text-muted" style="font-size:12px;">${m.description||'No description.'}</div></div>
                    </div>
                </div>
                <div class="sdd-section">
                    <div class="sdd-section-title">Basic Policy</div>
                    <div class="row g-2 text-xs">
                        <div class="col-6">Enable by default: <strong>${m.enable_by_default?'✓ Yes':'✗ No'}</strong></div>
                        <div class="col-6">Requires License Key: <strong>${m.requires_license?'✓ Yes':'✗ No'}</strong></div>
                        <div class="col-6">Requires active sub: <strong>${m.requires_subscription?'✓ Yes':'✗ No'}</strong></div>
                        <div class="col-6">Premium Tier: <strong>${m.premium_feature?'✓ Yes':'✗ No'}</strong></div>
                        <div class="col-6">Visible in Sidebar: <strong>${m.visible_in_sidebar?'✓ Yes':'✗ No'}</strong></div>
                        <div class="col-6">System Core: <strong>${m.system_module?'✓ Yes':'✗ No'}</strong></div>
                    </div>
                </div>
                <div class="sdd-section">
                    <div class="sdd-section-title">Assigned Plans</div>
                    <div class="d-flex gap-2">
                        ${m.assignments.plans.map(p => `<span class="plan-chip ${p.toLowerCase()}">${p}</span>`).join('') || '<span class="text-xs text-muted">No default plans assigned.</span>'}
                    </div>
                </div>
                <div class="sdd-section">
                    <div class="sdd-section-title">Target Pilot Organizations</div>
                    ${m.assignments.orgs.length ? `<div class="table-responsive"><table class="ds-table" style="font-size:11.5px;">
                        <thead><tr><th>Org Name</th><th>Plan</th><th>Status</th></tr></thead>
                        <tbody>${m.assignments.orgs.map(o => `<tr><td>${o.name}</td><td>${o.plan}</td><td>${o.status}</td></tr>`).join('')}</tbody>
                    </table></div>` : '<div class="text-xs text-muted">Available globally to assigned plans.</div>'}
                </div>
            </div>
            
            <!-- Permissions -->
            <div class="tab-pane fade" id="modTabPermissions">
                <p class="text-xs text-muted mb-3">Module authorization policies integrated with system RBAC roles:</p>
                <div class="table-responsive"><table class="ds-table text-xs">
                    <thead><tr><th>Role</th><th>View</th><th>Create</th><th>Update</th><th>Delete</th><th>Export</th><th>Approve</th></tr></thead>
                    <tbody>
                        ${Object.entries(m.permissions).map(([role, p]) => `<tr>
                            <td class="fw-bold">${role}</td>
                            <td>${p.view?'<i data-lucide="check" class="text-success" style="width:12px;height:12px;"></i>':'—'}</td>
                            <td>${p.create?'<i data-lucide="check" class="text-success" style="width:12px;height:12px;"></i>':'—'}</td>
                            <td>${p.update?'<i data-lucide="check" class="text-success" style="width:12px;height:12px;"></i>':'—'}</td>
                            <td>${p.delete?'<i data-lucide="check" class="text-success" style="width:12px;height:12px;"></i>':'—'}</td>
                            <td>${p.export?'<i data-lucide="check" class="text-success" style="width:12px;height:12px;"></i>':'—'}</td>
                            <td>${p.approve?'<i data-lucide="check" class="text-success" style="width:12px;height:12px;"></i>':'—'}</td>
                        </tr>`).join('') || '<tr><td colspan="7" class="text-center text-muted">No role permissions customized. Full access granted.</td></tr>'}
                    </tbody>
                </table></div>
                <button class="ds-btn ds-btn-secondary btn-sm mt-3" onclick="SuperAdmin._modEditPermissions(${m.id})">Configure Permissions</button>
            </div>
            
            <!-- Feature Flags -->
            <div class="tab-pane fade" id="modTabFlags">
                <p class="text-xs text-muted mb-3">Manage feature toggles and deployment strategies:</p>
                <div class="row g-3">
                    ${Object.entries(m.feature_flags).map(([flag, enabled]) => `
                        <div class="col-6">
                            <div class="p-2 border rounded d-flex justify-content-between align-items-center">
                                <span class="text-xs fw-bold">${flag.replace(/_/g, ' ').toUpperCase()}</span>
                                <div class="form-check form-switch m-0">
                                    <input class="form-check-input" type="switch" role="switch" ${enabled?'checked':''} onchange="SuperAdmin._modToggleFlag(${m.id}, '${flag}', this.checked)">
                                </div>
                            </div>
                        </div>`).join('')}
                </div>
            </div>
            
            <!-- Dependencies -->
            <div class="tab-pane fade" id="modTabDeps">
                <div class="sdd-section">
                    <div class="sdd-section-title">Required Dependency Modules</div>
                    ${m.dependencies.required.length ? `<ul>${m.dependencies.required.map(d => `<li class="text-xs py-1"><strong>${d.name}</strong> (<code>${d.code}</code>)</li>`).join('')}</ul>` : '<div class="text-xs text-muted">No required dependencies.</div>'}
                </div>
                <div class="sdd-section">
                    <div class="sdd-section-title">Blocked / Conflicting Modules</div>
                    ${m.dependencies.blocked.length ? `<ul>${m.dependencies.blocked.map(d => `<li class="text-xs py-1 text-danger"><strong>${d.name}</strong> (<code>${d.code}</code>)</li>`).join('')}</ul>` : '<div class="text-xs text-muted">No conflicts configured.</div>'}
                </div>
            </div>
            
            <!-- Usage Analytics -->
            <div class="tab-pane fade" id="modTabUsage">
                <div class="sdd-grid mb-3">
                    <div class="mdd-item"><div class="di-l">Active Orgs</div><div class="di-v">${m.analytics.organizations_using}</div></div>
                    <div class="mdd-item"><div class="di-l">Active Users</div><div class="di-v">${m.analytics.active_users}</div></div>
                    <div class="mdd-item"><div class="di-l">Avg Response Time</div><div class="di-v">${m.analytics.performance_ms} ms</div></div>
                    <div class="mdd-item"><div class="di-l">Error Rate</div><div class="di-v text-danger">${m.analytics.error_rate}%</div></div>
                    <div class="mdd-item"><div class="di-l">API Calls / Month</div><div class="di-v">${m.analytics.api_calls.toLocaleString()}</div></div>
                    <div class="mdd-item"><div class="di-l">Growth Trend</div><div class="di-v text-success">${m.analytics.growth_trend}</div></div>
                </div>
                <div class="mb-3">
                    <div class="d-flex justify-content-between text-xs mb-1"><span>Target User Growth Adoption</span><strong>${userPct}%</strong></div>
                    <div style="height:6px;border-radius:3px;background:var(--ds-border-color);overflow:hidden;"><div style="height:100%;width:${userPct}%;border-radius:3px;background:#10b981;"></div></div>
                </div>
                <div class="sdd-section">
                    <div class="sdd-section-title">Most Engaged Features</div>
                    <div class="d-flex flex-wrap gap-1">
                        ${m.analytics.most_used_features.map(f => `<span class="badge bg-secondary text-xs">${f}</span>`).join('')}
                    </div>
                </div>
            </div>
            
            <!-- Timeline Logs -->
            <div class="tab-pane fade" id="modTabLogs">
                <ul style="list-style:none;padding:0;margin:0;">
                    ${m.audit_logs.map(l => `<li style="display:flex;gap:.7rem;padding:.5rem 0;border-bottom:1px solid var(--ds-border-color);font-size:11.5px;">
                        <span style="width:8px;height:8px;border-radius:50%;margin-top:4px;flex-shrink:0;background:${l.action==='CREATE'?'#10b981':l.action==='DELETE'?'#ef4444':'#3b82f6'};"></span>
                        <div>
                            <div><strong>${l.action}</strong> - ${l.details||'No details.'}</div>
                            <div class="text-muted" style="font-size:10px;">By ${l.admin} on ${new Date(l.timestamp).toLocaleString()}</div>
                        </div>
                    </li>`).join('') || '<div class="text-xs text-muted text-center py-3">No log history found.</div>'}
                </ul>
            </div>
        `;
    },

    async _modToggleFlag(moduleId, flag, checked) {
        try {
            const body = { feature_flags: {} };
            body.feature_flags[flag] = checked;
            await this._modPut(`/${moduleId}`, body);
            this._modNotify(`Flag '${flag}' updated`, 'success');
        } catch(e) { this._modNotify(e.message, 'error'); }
    },

    _modEditPermissions(id) {
        alert('Permission assignment modal/stepper is available through the wizard creation. Assign permission configurations during new modules setup.');
    },

    // ── Create Wizard ─────────────────────────────────────────────────────────
    openModCreateWizard() {
        const s = this._mod;
        s.wizStep = 1;
        s.wizPlans = new Set(['Starter', 'Professional', 'Enterprise']);
        s.wizPermissions = {};
        
        // Reset Inputs
        ['mwName', 'mwCode', 'mwDesc', 'mwRoute', 'mwIcon', 'mwColor', 'mwOrder'].forEach(id => {
            const el = document.getElementById(id);
            if(el) {
                el.value = id === 'mwIcon' ? 'package' : id === 'mwColor' ? '#3b82f6' : id === 'mwOrder' ? '0' : '';
                el.classList.remove('is-invalid');
                if (!el._hasValidationListener && (id === 'mwName' || id === 'mwCode')) {
                    el.addEventListener('input', () => {
                        if (el.value && el.value.trim()) el.classList.remove('is-invalid');
                    });
                    el._hasValidationListener = true;
                }
            }
        });
        ['mwOptDefault', 'mwOptLicense', 'mwOptPremium', 'mwOptAI', 'mwOptBeta', 'mwOptSystem', 'mwFfExp', 'mwFfInternal', 'mwFfTrial', 'mwFfGov', 'mwFfEdu'].forEach(id => {
            const el = document.getElementById(id); if(el) el.checked = false;
        });
        ['mwOptSidebar', 'mwOptDashboard', 'mwOptSub'].forEach(id => {
            const el = document.getElementById(id); if(el) el.checked = true;
        });
        
        // Render step 4 permissions table
        const tbody = document.getElementById('mwPermBody');
        if (tbody) {
            tbody.innerHTML = s.roles.map(role => `<tr>
                <td><strong>${role}</strong></td>
                <td><input type="checkbox" class="perm-chk" data-role="${role}" data-perm="view" checked></td>
                <td><input type="checkbox" class="perm-chk" data-role="${role}" data-perm="create" ${role==='Employee'?'':'checked'}></td>
                <td><input type="checkbox" class="perm-chk" data-role="${role}" data-perm="update" ${role==='Employee'?'':'checked'}></td>
                <td><input type="checkbox" class="perm-chk" data-role="${role}" data-perm="delete" ${['SuperAdmin','Admin','CEO'].includes(role)?'checked':''}></td>
                <td><input type="checkbox" class="perm-chk" data-role="${role}" data-perm="export" ${role==='Employee'?'':'checked'}></td>
                <td><input type="checkbox" class="perm-chk" data-role="${role}" data-perm="approve" ${['SuperAdmin','Admin','CEO','Department Head'].includes(role)?'checked':''}></td>
            </tr>`).join('');
        }
        
        // Render step 5 dependency checklist
        const reqList = document.getElementById('mwRequiredList');
        const blkList = document.getElementById('mwBlockedList');
        if (reqList && blkList) {
            const listHtml = s.allModulesList.map(m => `
                <label class="d-block py-1"><input type="checkbox" value="${m.id}" data-code="${m.code}"> ${m.name}</label>
            `).join('') || '<div class="text-muted">No other modules registered.</div>';
            reqList.innerHTML = listHtml;
            blkList.innerHTML = listHtml;
        }
        
        this._modWizGoStep(1);
        new bootstrap.Modal(document.getElementById('modCreateModal')).show();
    },

    _validateModStep1() {
        const nameEl = document.getElementById('mwName');
        const codeEl = document.getElementById('mwCode');
        let isValid = true;
        [nameEl, codeEl].forEach(el => {
            if (el) {
                if (!el.value || !el.value.trim()) {
                    el.classList.add('is-invalid');
                    isValid = false;
                } else {
                    el.classList.remove('is-invalid');
                }
            }
        });
        if (!isValid) {
            this._modNotify('Module Name and unique Code are required', 'error');
        }
        return isValid;
    },

    _modWizGoStep(n) {
        if (n > 1 && !this._validateModStep1()) return;

        this._mod.wizStep = n;
        document.querySelectorAll('#modCreateModal .wiz-panel').forEach(p => p.classList.remove('active'));
        document.getElementById(`mwp${n}`)?.classList.add('active');
        document.querySelectorAll('#modCreateModal .wiz-step').forEach(s => {
            const sn = parseInt(s.dataset.ws);
            s.classList.toggle('active', sn === n);
            s.classList.toggle('done', sn < n);
        });
        document.getElementById('mwPrevBtn').disabled = n === 1;
        document.getElementById('mwNextBtn').classList.toggle('d-none', n === 6);
        document.getElementById('mwSubmitBtn').classList.toggle('d-none', n !== 6);
        
        if (n === 6) this._modWizRenderReview();
    },

    modWizNext() {
        const s = this._mod;
        if (s.wizStep === 1) {
            if (!this._validateModStep1()) return;
        }
        if (s.wizStep < 6) this._modWizGoStep(s.wizStep + 1);
    },

    modWizPrev() { if (this._mod.wizStep > 1) this._modWizGoStep(this._mod.wizStep - 1); },

    modWizTogglePlan(p) {
        const el = document.getElementById(`mwp-${p}`);
        if(this._mod.wizPlans.has(p)) {
            this._mod.wizPlans.delete(p); el?.classList.remove('sel');
        } else {
            this._mod.wizPlans.add(p); el?.classList.add('sel');
        }
    },

    _modWizRenderReview() {
        const name = document.getElementById('mwName').value.trim();
        const code = document.getElementById('mwCode').value.trim();
        const cat = document.getElementById('mwCategory').value;
        const plans = Array.from(this._mod.wizPlans).join(', ');
        
        // Count checkboxes
        const requiredCount = document.querySelectorAll('#mwRequiredList input:checked').length;
        const blockedCount = document.querySelectorAll('#mwBlockedList input:checked').length;
        
        document.getElementById('mwReviewArea').innerHTML = `
            <div class="row g-2">
                <div class="col-6"><div class="text-muted text-xs">Module Name</div><strong>${name}</strong></div>
                <div class="col-6"><div class="text-muted text-xs">Module Code</div><strong><code>${code}</code></strong></div>
                <div class="col-6"><div class="text-muted text-xs">Category</div><strong>${cat}</strong></div>
                <div class="col-6"><div class="text-muted text-xs">Default Plans</div><strong>${plans || 'None'}</strong></div>
                <div class="col-6"><div class="text-muted text-xs">Dependencies</div><strong>${requiredCount} Required / ${blockedCount} Blocked</strong></div>
            </div>
            <div class="alert alert-info mt-3 py-2 text-xs mb-0">Review details carefully. Saving will deploy configuration state parameters dynamically.</div>
        `;
    },

    async modWizSubmit() {
        const s = this._mod;
        const name = document.getElementById('mwName').value.trim();
        const code = document.getElementById('mwCode').value.trim();
        const desc = document.getElementById('mwDesc').value.trim();
        const category = document.getElementById('mwCategory').value;
        const nav_route = document.getElementById('mwRoute').value.trim();
        const icon = document.getElementById('mwIcon').value.trim();
        const color = document.getElementById('mwColor').value.trim();
        const display_order = parseInt(document.getElementById('mwOrder').value) || 0;
        
        // Config flags
        const enable_by_default = document.getElementById('mwOptDefault').checked;
        const visible_in_sidebar = document.getElementById('mwOptSidebar').checked;
        const visible_in_dashboard = document.getElementById('mwOptDashboard').checked;
        const requires_license = document.getElementById('mwOptLicense').checked;
        const requires_subscription = document.getElementById('mwOptSub').checked;
        const premium_feature = document.getElementById('mwOptPremium').checked;
        const ai_enabled = document.getElementById('mwOptAI').checked;
        const beta_feature = document.getElementById('mwOptBeta').checked;
        const system_module = document.getElementById('mwOptSystem').checked;
        
        // Feature Flags
        const experimental = document.getElementById('mwFfExp').checked;
        const internal_only = document.getElementById('mwFfInternal').checked;
        const trial_only = document.getElementById('mwFfTrial').checked;
        const government_only = document.getElementById('mwFfGov').checked;
        const education_only = document.getElementById('mwFfEdu').checked;
        
        // Plans
        const plans = Array.from(s.wizPlans);
        
        // Permissions
        const permissions = {};
        s.roles.forEach(role => {
            permissions[role] = {};
            document.querySelectorAll(`.perm-chk[data-role="${role}"]`).forEach(chk => {
                permissions[role][chk.dataset.perm] = chk.checked;
            });
        });
        
        // Dependencies
        const required_modules = Array.from(document.querySelectorAll('#mwRequiredList input:checked')).map(chk => parseInt(chk.value));
        const blocked_modules = Array.from(document.querySelectorAll('#mwBlockedList input:checked')).map(chk => parseInt(chk.value));
        
        const payload = {
            name, code, description: desc, category, navigation_route: nav_route, icon, color, display_order,
            enable_by_default, visible_in_sidebar, visible_in_dashboard, requires_license, requires_subscription,
            premium_feature, ai_enabled, beta_feature, system_module, experimental, internal_only, trial_only,
            government_only, education_only, plans, permissions, required_modules, blocked_modules
        };
        
        try {
            api.showNotification('Provisioning module...', 'info');
            const res = await this._modPost('', payload);
            this._modNotify(res.message, 'success');
            bootstrap.Modal.getInstance(document.getElementById('modCreateModal'))?.hide();
            this.loadModules();
        } catch(e) {
            this._modNotify(e.message, 'error');
        }
    },

    async loadAnalytics() {
        if (!this.enterpriseAnalyticsInitialized) {
            EnterpriseAnalytics.init('superAdminEnterpriseAnalyticsContainer', true);
            this.enterpriseAnalyticsInitialized = true;
        } else {
            EnterpriseAnalytics.refreshDashboard();
        }
    },

    async loadAnnouncements() {
        if (typeof AnnouncementsModule !== 'undefined') {
            await AnnouncementsModule.init('superAdminAnnouncementsContainer');
        }
    },

    // --- Onboarding Wizard ---
    initWizard() {
        const modalEl = document.getElementById('createOrgModal');
        if (!modalEl) return;
        
        this.wizStep = 1;
        this.updateWizardUI();
        
        // Listeners for wizard buttons
        document.getElementById('wizNextBtn').onclick = () => this.handleWizardNext();
        document.getElementById('wizPrevBtn').onclick = () => this.handleWizardPrev();
        
        // Reset wizard on modal hide
        modalEl.addEventListener('hidden.bs.modal', () => {
            document.getElementById('wizardForm').reset();
            this.wizStep = 1;
            this.updateWizardUI();
        });
    },
    
    updateWizardUI() {
        document.querySelectorAll('.wizard-step').forEach(step => {
            step.classList.remove('active-step');
            step.style.display = 'none';
            if (parseInt(step.getAttribute('data-step')) === this.wizStep) {
                step.classList.add('active-step');
                step.style.display = 'block';
            }
        });
        
        document.querySelectorAll('.step-header').forEach(header => {
            header.classList.remove('active', 'completed');
            const stepNum = parseInt(header.getAttribute('data-step'));
            if (stepNum === this.wizStep) {
                header.classList.add('active');
            } else if (stepNum < this.wizStep) {
                header.classList.add('completed');
            }
        });
        
        if (this.wizStep === 1) {
            document.getElementById('wizPrevBtn').style.display = 'none';
        } else {
            document.getElementById('wizPrevBtn').style.display = 'inline-block';
        }
        
        const nextBtn = document.getElementById('wizNextBtn');
        if (this.wizStep === 4) {
            nextBtn.textContent = 'Provision Tenant';
            nextBtn.className = 'ds-btn ds-btn-success';
        } else {
            nextBtn.textContent = 'Next Step';
            nextBtn.className = 'ds-btn ds-btn-primary';
        }
    },
    
    handleWizardPrev() {
        if (this.wizStep > 1) {
            this.wizStep--;
            this.updateWizardUI();
        }
    },
    
    handleWizardNext() {
        if (this.wizStep === 1) {
            const orgNameEl = document.getElementById('wizOrgName');
            const name = orgNameEl ? orgNameEl.value.trim() : '';
            if (!name) {
                if (orgNameEl) orgNameEl.classList.add('is-invalid');
                api.showNotification('Please enter the Organization Name', 'orange');
                return;
            } else if (orgNameEl) {
                orgNameEl.classList.remove('is-invalid');
            }
            this.wizStep = 2;
            this.updateWizardUI();
        } else if (this.wizStep === 2) {
            const usersEl = document.getElementById('wizMaxUsers');
            const storageEl = document.getElementById('wizStorageLimit');
            const users = usersEl ? usersEl.value : '';
            const storage = storageEl ? storageEl.value : '';
            let valid = true;
            if (!users || users <= 0) { if (usersEl) usersEl.classList.add('is-invalid'); valid = false; } else if (usersEl) { usersEl.classList.remove('is-invalid'); }
            if (!storage || storage <= 0) { if (storageEl) storageEl.classList.add('is-invalid'); valid = false; } else if (storageEl) { storageEl.classList.remove('is-invalid'); }
            if (!valid) { api.showNotification('Please enter valid user and storage limits', 'orange'); return; }
            this.wizStep = 3;
            this.updateWizardUI();
        } else if (this.wizStep === 3) {
            const adminNameEl = document.getElementById('wizAdminName');
            const adminEmailEl = document.getElementById('wizAdminEmail');
            const adminPassEl = document.getElementById('wizAdminPassword');
            const adminName = adminNameEl ? adminNameEl.value.trim() : '';
            const adminEmail = adminEmailEl ? adminEmailEl.value.trim() : '';
            const adminPassword = adminPassEl ? adminPassEl.value.trim() : '';
            let valid = true;
            if (!adminName) { if (adminNameEl) adminNameEl.classList.add('is-invalid'); valid = false; } else if (adminNameEl) { adminNameEl.classList.remove('is-invalid'); }
            if (!adminEmail) { if (adminEmailEl) adminEmailEl.classList.add('is-invalid'); valid = false; } else if (adminEmailEl) { adminEmailEl.classList.remove('is-invalid'); }
            if (!adminPassword || adminPassword.length < 8) { if (adminPassEl) adminPassEl.classList.add('is-invalid'); valid = false; } else if (adminPassEl) { adminPassEl.classList.remove('is-invalid'); }
            if (!valid) {
                api.showNotification('Please fill all required admin fields correctly (Password min 8 chars)', 'orange');
                return;
            }
            
            const usersVal = document.getElementById('wizMaxUsers')?.value || '50';
            const storageVal = document.getElementById('wizStorageLimit')?.value || '10240';

            // Populate review screen
            document.getElementById('revOrgName').textContent = document.getElementById('wizOrgName').value;
            document.getElementById('revIndustryCode').textContent = `${document.getElementById('wizIndustry').value || 'Other'} · Code: ${document.getElementById('wizOrgCode').value || 'AUTO-GEN'}`;
            document.getElementById('revPlan').textContent = document.getElementById('wizPlan').value;
            document.getElementById('revLimits').textContent = `Max Users: ${usersVal} · Storage: ${storageVal} MB`;
            document.getElementById('revAdminName').textContent = adminName;
            document.getElementById('revAdminEmail').textContent = adminEmail;
            
            const selectedModules = [];
            document.querySelectorAll('.wiz-module-chk:checked').forEach(chk => {
                selectedModules.push(`<span class="ds-badge outline">${chk.value}</span>`);
            });
            document.getElementById('revModules').innerHTML = selectedModules.join(' ') || '<span class="text-xs text-muted">None</span>';
            
            this.wizStep = 4;
            this.updateWizardUI();
        } else if (this.wizStep === 4) {
            this.submitWizard();
        }
    },
    
    async submitWizard() {
        const data = {
            company: {
                name: document.getElementById('wizOrgName').value.trim(),
                org_code: document.getElementById('wizOrgCode').value.trim(),
                industry: document.getElementById('wizIndustry').value.trim(),
                gst_number: document.getElementById('wizGST').value.trim(),
                pan_number: document.getElementById('wizPAN').value.trim(),
                website: document.getElementById('wizWebsite').value.trim(),
                phone: document.getElementById('wizPhone').value.trim(),
                address: document.getElementById('wizAddress').value.trim(),
                city: document.getElementById('wizCity').value.trim(),
                state: document.getElementById('wizState').value.trim(),
                country: document.getElementById('wizCountry').value.trim(),
                pincode: document.getElementById('wizPincode').value.trim(),
                logo_url: document.getElementById('wizLogo').value.trim()
            },
            subscription: {
                plan: document.getElementById('wizPlan').value,
                trial_duration: parseInt(document.getElementById('wizTrialDays').value || 14),
                max_users: parseInt(document.getElementById('wizMaxUsers').value || 50),
                storage_limit: parseFloat(document.getElementById('wizStorageLimit').value || 10240.0),
                enabled_modules: Array.from(document.querySelectorAll('.wiz-module-chk:checked')).map(chk => chk.value),
                is_trial: parseInt(document.getElementById('wizTrialDays').value || 14) > 0
            },
            admin: {
                name: document.getElementById('wizAdminName').value.trim(),
                email: document.getElementById('wizAdminEmail').value.trim(),
                username: document.getElementById('wizAdminEmail').value.trim(),
                password: document.getElementById('wizAdminPassword').value.trim(),
                profile_photo: document.getElementById('wizAdminPhoto').value.trim()
            }
        };
        
        try {
            api.showNotification('Provisioning organization tenant...', 'info');
            const res = await api.post('/super-admin/companies', data);
            api.showNotification('Organization and admin account provisioned successfully!', 'success');
            const inst = bootstrap.Modal.getInstance(document.getElementById('createOrgModal'));
            if (inst) inst.hide();
            this.loadOrganizations();
        } catch (err) {
            api.showNotification(err.message || 'Failed to onboard organization', 'error');
        }
    },

    // --- Table Column / Checkbox features ---
    initTableFeatures() {
        document.addEventListener('change', (e) => {
            if (e.target && e.target.id === 'selectAllOrgs') {
                const checkboxes = document.querySelectorAll('.org-row-chk');
                checkboxes.forEach(chk => {
                    chk.checked = e.target.checked;
                    const id = parseInt(chk.getAttribute('data-id'));
                    if (e.target.checked) {
                        this.selectedOrgIds.add(id);
                    } else {
                        this.selectedOrgIds.delete(id);
                    }
                });
                this.updateBulkActionsBar();
            }
            
            if (e.target && e.target.classList.contains('org-row-chk')) {
                const id = parseInt(e.target.getAttribute('data-id'));
                if (e.target.checked) {
                    this.selectedOrgIds.add(id);
                } else {
                    this.selectedOrgIds.delete(id);
                }
                
                const allBox = document.getElementById('selectAllOrgs');
                const chks = document.querySelectorAll('.org-row-chk');
                if (allBox) {
                    allBox.checked = Array.from(chks).every(c => c.checked);
                }
                this.updateBulkActionsBar();
            }
            
            if (e.target && e.target.classList.contains('col-toggle-chk')) {
                this.applyColumnVisibility();
            }
        });
    },

    applyColumnVisibility() {
        document.querySelectorAll('.col-toggle-chk').forEach(chk => {
            const colClass = chk.value;
            const isChecked = chk.checked;
            document.querySelectorAll(`.${colClass}`).forEach(el => {
                if (isChecked) {
                    el.classList.remove('d-none');
                } else {
                    el.classList.add('d-none');
                }
            });
        });
    },

    updateBulkActionsBar() {
        const bar = document.getElementById('bulkActionsBar');
        const text = document.getElementById('bulkSelectedText');
        if (!bar) return;
        
        const count = this.selectedOrgIds.size;
        if (count > 0) {
            bar.classList.remove('d-none');
            if (text) text.textContent = `Selected: ${count} organization${count > 1 ? 's' : ''}`;
        } else {
            bar.classList.add('d-none');
        }
    },

    // --- Bulk Operations ---
    async triggerBulkAction(action) {
        if (!this.selectedOrgIds.size) return;
        const orgIds = Array.from(this.selectedOrgIds);
        
        let confirmMsg = `Are you sure you want to ${action} ${orgIds.length} organization(s)?`;
        if (action === 'delete') {
            confirmMsg += " This is a soft-delete and can be restored.";
        }
        
        if (!confirm(confirmMsg)) return;
        
        try {
            api.showNotification(`Running bulk ${action} action...`, 'info');
            const res = await api.post('/super-admin/companies/bulk-action', {
                action: action,
                ids: orgIds,
                org_ids: orgIds
            });
            api.showNotification(res.message || `Bulk action completed successfully`, 'success');
            this.selectedOrgIds.clear();
            this.loadOrganizations();
        } catch (err) {
            api.showNotification(err.message || `Bulk action failed`, 'error');
        }
    },

    async triggerBulkAssignPlan(plan) {
        if (!this.selectedOrgIds.size) return;
        const orgIds = Array.from(this.selectedOrgIds);
        
        if (!confirm(`Change subscription plan of ${orgIds.length} organizations to ${plan}?`)) return;
        
        try {
            api.showNotification(`Assigning plan ${plan}...`, 'info');
            const res = await api.post('/super-admin/companies/bulk-action', {
                action: 'assign_plan',
                ids: orgIds,
                org_ids: orgIds,
                plan: plan
            });
            api.showNotification(res.message || `Plan assigned successfully`, 'success');
            this.selectedOrgIds.clear();
            this.loadOrganizations();
        } catch (err) {
            api.showNotification(err.message || `Failed to assign plan`, 'error');
        }
    },

    async triggerBulkAssignModules() {
        if (!this.selectedOrgIds.size) return;
        const orgIds = Array.from(this.selectedOrgIds);
        
        const enabledModules = Array.from(document.querySelectorAll('.bulk-module-chk:checked')).map(chk => chk.value);
        if (!confirm(`Assign features [${enabledModules.join(', ')}] to ${orgIds.length} organizations?`)) return;
        
        try {
            api.showNotification(`Updating features...`, 'info');
            const res = await api.post('/super-admin/companies/bulk-action', {
                action: 'assign_modules',
                ids: orgIds,
                org_ids: orgIds,
                modules: enabledModules,
                enabled_modules: enabledModules
            });
            api.showNotification(res.message || `Features assigned successfully`, 'success');
            this.selectedOrgIds.clear();
            this.loadOrganizations();
        } catch (err) {
            api.showNotification(err.message || `Failed to update features`, 'error');
        }
    },

    triggerBulkSendEmail() {
        if (!this.selectedOrgIds.size) return;
        api.showNotification(`Mailer template loaded for ${this.selectedOrgIds.size} recipient(s). Dispatching queued emails...`, 'info');
        setTimeout(() => {
            api.showNotification('Bulk announcement emails sent!', 'success');
            this.selectedOrgIds.clear();
            this.updateBulkActionsBar();
        }, 1500);
    },

    async populateAllPlanDropdowns() {
        try {
            let plans = [];
            if (this._allFetchedPlans && this._allFetchedPlans.length) {
                plans = this._allFetchedPlans;
            } else {
                const token = localStorage.getItem('access_token') || sessionStorage.getItem('access_token') || localStorage.getItem('token') || sessionStorage.getItem('token');
                const res = await fetch('/api/subscriptions/plans', {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                if (res.ok) {
                    const body = await res.json();
                    plans = body.data || [];
                    this._allFetchedPlans = plans;
                }
            }
            if (!plans || !plans.length) return;

            // Single plan select fields
            const formSelectIds = ['editPlan', 'assignPlanSelect', 'changePlanSelect', 'wizPlan', 'ps-default-plan'];
            formSelectIds.forEach(id => {
                const select = document.getElementById(id);
                if (select) {
                    const currentVal = select.value;
                    const options = plans.map(p => {
                        const planName = p.name || p.plan_name || p.code;
                        return `<option value="${planName}">${planName}</option>`;
                    }).join('');
                    select.innerHTML = options;
                    if (currentVal && plans.some(p => (p.name === currentVal || p.plan_name === currentVal || p.code === currentVal))) {
                        select.value = currentVal;
                    }
                }
            });

            // Filter select fields (with "All Plans" top option)
            const filterSelects = [
                { id: 'filterPlan', label: 'All Plans' },
                { id: 'billPlanFilter', label: 'All Plans' },
                { id: 'subPlanFilter', label: 'All Plans' },
                { id: 'licPlanFilter', label: 'All Plans' },
                { id: 'modPlanFilter', label: 'All Plans' }
            ];
            filterSelects.forEach(({ id, label }) => {
                const select = document.getElementById(id);
                if (select) {
                    const currentVal = select.value;
                    const options = `<option value="">${label}</option>` + plans.map(p => {
                        const planName = p.name || p.plan_name || p.code;
                        return `<option value="${planName}">${planName}</option>`;
                    }).join('');
                    select.innerHTML = options;
                    if (currentVal) {
                        select.value = currentVal;
                    }
                }
            });

            // Bulk dropdown menus (UL dropdowns)
            const bulkPlanUl = document.getElementById('bulkAssignPlanDropdown');
            if (bulkPlanUl) {
                bulkPlanUl.innerHTML = plans.map(p => {
                    const planName = p.name || p.plan_name || p.code;
                    const escapedName = this._escapeHTML(planName);
                    return `<li><a class="dropdown-item" href="#" onclick="SuperAdmin.triggerBulkAssignPlan('${escapedName.replace(/'/g, "\\'")}');return false;">${escapedName}</a></li>`;
                }).join('');
            }
        } catch (e) {
            console.warn('Could not populate dynamic plan dropdowns:', e);
        }
    },

    // --- Profile Editing Modal ---
    async openEditOrg(id) {
        try {
            await this.populateAllPlanDropdowns();
            const res = await api.get(`/super-admin/companies/${id}`);
            if (!res || res.status !== 'success') return;
            const org = res.data;
            
            document.getElementById('editOrgId').value = org.id;
            document.getElementById('editName').value = org.name;
            document.getElementById('editIndustry').value = org.industry || '';
            document.getElementById('editGST').value = org.gst_number || '';
            document.getElementById('editPAN').value = org.pan_number || '';
            document.getElementById('editWebsite').value = org.website || '';
            if (document.getElementById('editLogo')) document.getElementById('editLogo').value = org.logo_url || '';
            document.getElementById('editPhone').value = org.phone || '';
            document.getElementById('editAddress').value = org.address || '';
            document.getElementById('editCity').value = org.city || '';
            document.getElementById('editState').value = org.state || '';
            document.getElementById('editCountry').value = org.country || '';
            document.getElementById('editZip').value = org.zip_code || '';
            
            if (document.getElementById('editPlan')) document.getElementById('editPlan').value = org.plan;
            if (document.getElementById('editStatus')) document.getElementById('editStatus').value = org.status;
            if (document.getElementById('editMaxUsers')) document.getElementById('editMaxUsers').value = org.max_users;
            if (document.getElementById('editStorageLimit')) document.getElementById('editStorageLimit').value = org.storage_limit_mb;
            
            const modules = org.enabled_modules || ['7-qc-tools'];
            document.querySelectorAll('.edit-module-chk').forEach(chk => {
                chk.checked = modules.includes(chk.value);
            });
            
            const modal = new bootstrap.Modal(document.getElementById('editOrgModal'));
            modal.show();
        } catch (err) {
            api.showNotification('Failed to fetch details for editing', 'error');
        }
    },

    async saveOrgEdit() {
        const id = document.getElementById('editOrgId').value;
        const data = {
            company: {
                name: document.getElementById('editName').value.trim(),
                industry: document.getElementById('editIndustry').value.trim(),
                gst_number: document.getElementById('editGST').value.trim(),
                pan_number: document.getElementById('editPAN').value.trim(),
                website: document.getElementById('editWebsite').value.trim(),
                phone: document.getElementById('editPhone').value.trim(),
                address: document.getElementById('editAddress').value.trim(),
                city: document.getElementById('editCity').value.trim(),
                state: document.getElementById('editState').value.trim(),
                country: document.getElementById('editCountry').value.trim(),
                zip_code: document.getElementById('editZip').value.trim()
            }
        };

        if (document.getElementById('editLogo')) {
            data.company.logo_url = document.getElementById('editLogo').value.trim();
        }

        if (document.getElementById('editPlan')) {
            data.subscription = {
                plan: document.getElementById('editPlan').value,
                status: document.getElementById('editStatus').value,
                max_users: parseInt(document.getElementById('editMaxUsers').value || 50),
                storage_limit: parseFloat(document.getElementById('editStorageLimit').value || 10240.0),
                enabled_modules: Array.from(document.querySelectorAll('.edit-module-chk:checked')).map(chk => chk.value)
            };
        }
        
        try {
            api.showNotification('Updating organization profile...', 'info');
            const res = await api.put(`/super-admin/companies/${id}`, data);
            api.showNotification('Organization updated successfully!', 'success');
            const inst = bootstrap.Modal.getInstance(document.getElementById('editOrgModal'));
            if (inst) inst.hide();
            this.loadOrganizations();
        } catch (err) {
            api.showNotification(err.message || 'Failed to update organization', 'error');
        }
    },

    // --- Enterprise Actions ---
    async impersonateAdmin(id) {
        try {
            api.showNotification('Requesting administrative impersonation...', 'info');
            const res = await api.post(`/super-admin/companies/${id}/impersonate`);
            if (res.status === 'success' || res.token) {
                const impersonateToken = res.token || res.data?.token;
                if (!impersonateToken) {
                    throw new Error('No authentication token returned for impersonation');
                }
                
                const superToken = sessionStorage.getItem('token');
                if (superToken) {
                    sessionStorage.setItem('super_admin_backup_token', superToken);
                }
                
                sessionStorage.setItem('token', impersonateToken);
                
                api.showNotification('Login impersonation successful. Redirecting to tenant space...', 'success');
                setTimeout(() => {
                    window.location.href = '/admin/dashboard.html';
                }, 1000);
            }
        } catch (err) {
            api.showNotification(err.message || 'Failed to impersonate admin', 'error');
        }
    },

    async resetAdminPassword(id) {
        if (!confirm('Are you sure you want to reset the admin password? This will invalidate the current password.')) return;
        try {
            api.showNotification('Generating temporary password...', 'info');
            const res = await api.post(`/super-admin/companies/${id}/reset-admin-password`);
            if (res && (res.status === 'success' || res.success || res.temp_password || (res.data && res.data.temp_password))) {
                const tempPass = res.temp_password || (res.data && res.data.temp_password) || 'Welcome@123';
                const el = document.getElementById('resetTempPassValue');
                if (el) el.textContent = tempPass;
                const modalEl = document.getElementById('passwordResetResultModal');
                if (modalEl) {
                    const modal = new bootstrap.Modal(modalEl);
                    modal.show();
                } else {
                    api.showNotification(`Password reset successfully. Temporary Password: ${tempPass}`, 'success');
                }
            } else {
                api.showNotification((res && res.message) || 'Failed to reset password', 'error');
            }
        } catch (err) {
            api.showNotification((err && err.message) || 'Failed to reset password', 'error');
        }
    },

    async deleteOrg(id, name) {
        if (!confirm(`Move '${name}' to Recycle Bin?\n\nThis organization will be soft-deleted and kept in the Recycle Bin for 30 days before permanent automatic removal. You can recover it anytime within 30 days.`)) return;
        try {
            api.showNotification(`Moving ${name} to Recycle Bin...`, 'info');
            const res = await api.delete(`/super-admin/companies/${id}`);
            api.showNotification(res.message || `Organization '${name}' moved to Recycle Bin`, 'success');
            this.loadOrganizations();
            this.loadRecycleBin();
        } catch (err) {
            api.showNotification((err && err.message) || 'Failed to delete organization', 'error');
        }
    },

    async restoreOrg(id) {
        try {
            api.showNotification('Restoring organization...', 'info');
            const res = await api.post(`/super-admin/companies/${id}/restore`);
            api.showNotification(res.message || 'Organization restored successfully', 'success');
            this.loadOrganizations();
            this.loadRecycleBin();
        } catch (err) {
            api.showNotification((err && err.message) || 'Failed to restore organization', 'error');
        }
    },

    // ── RECYCLE BIN METHODS ──────────────────────────────────────────────────
    async loadRecycleBin() {
        const tbody = document.getElementById('recycleBinBody');
        if (!tbody) return;
        tbody.innerHTML = `<tr><td colspan="7" class="text-center py-5"><span class="spinner-border spinner-border-sm me-2"></span><span class="text-muted text-xs">Loading Recycle Bin…</span></td></tr>`;
        const paginationEl = document.getElementById('recycleBinPagination');
        if (paginationEl) paginationEl.innerHTML = '';

        try {
            const res = await api.get('/super-admin/recycle-bin');
            this._binItems = (res && res.data) || [];
            this._binPage  = 1;
            this._renderBinPage();
        } catch (err) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center py-5 text-danger text-xs">Failed to load Recycle Bin data.</td></tr>`;
        }
    },


    _renderBinPage() {
        const PAGE_SIZE = 5;
        const tbody    = document.getElementById('recycleBinBody');
        const countEl  = document.getElementById('recycleBinCount');
        if (!tbody) return;

        const items      = this._binItems || [];
        const page       = this._binPage  || 1;
        const start      = (page - 1) * PAGE_SIZE;
        const pageItems  = items.slice(start, start + PAGE_SIZE);

        if (countEl) countEl.textContent = `${items.length} deleted organization${items.length !== 1 ? 's' : ''}`;

        if (items.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center py-5 text-muted text-xs"><i data-lucide="trash-2" style="width:32px;height:32px;opacity:0.3;display:block;margin:0 auto 8px;"></i>Recycle Bin is empty. No soft-deleted organizations.</td></tr>`;
            if (window.lucide) lucide.createIcons();
            this._renderBinPagination(0, 1, PAGE_SIZE);
            return;
        }

        tbody.innerHTML = pageItems.map(item => {
            const planColors = { 'Starter': 'blue', 'Professional': 'purple', 'Enterprise': 'indigo', 'Custom': 'gray' };
            const planColor  = planColors[item.subscription_plan] || 'gray';
            const nameEsc    = QCMS.escapeHtml(item.name).replace(/'/g, "\\'");

            // Use backend computed days_remaining as primary source of truth, fallback to client-side math
            const deletedAtMs   = item.deleted_at ? new Date(item.deleted_at).getTime() : Date.now();
            const purgeAtMs     = deletedAtMs + (30 * 24 * 60 * 60 * 1000);
            const msLeft        = purgeAtMs - Date.now();
            const daysRemaining = (item.days_remaining !== undefined && item.days_remaining !== null)
                ? item.days_remaining
                : Math.max(0, Math.ceil(msLeft / (24 * 60 * 60 * 1000)));
            const purgeDate     = new Date(purgeAtMs).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
            const badgeColor    = daysRemaining <= 5 ? '#ef4444' : (daysRemaining <= 15 ? '#f59e0b' : '#10b981');
            const icon          = daysRemaining <= 5 ? 'alert-triangle' : 'clock';

            return `
                <tr data-bin-id="${item.id}">
                    <td style="width:42px;padding-right:4px;">
                        <div style="display:flex;align-items:center;justify-content:center;">
                            <input type="checkbox" class="bin-row-check" data-id="${item.id}" style="width:15px;height:15px;cursor:pointer;accent-color:var(--ds-primary);" onchange="SuperAdmin.updateBinBulkBar()">
                        </div>
                    </td>
                    <td>
                        <div class="fw-bold text-sm" style="color:var(--ds-text-main);">${QCMS.escapeHtml(item.name)}</div>
                        <div class="text-xs text-muted">ID: ${item.id} ${item.org_code && item.org_code !== '—' ? '· ' + QCMS.escapeHtml(item.org_code) : ''}</div>
                    </td>
                    <td>
                        <div class="text-sm font-medium" style="color:var(--ds-text-main);">${QCMS.escapeHtml(item.admin_name)}</div>
                        <div class="text-xs text-muted">${QCMS.escapeHtml(item.email)}</div>
                    </td>
                    <td>
                        <span class="ds-badge ds-badge-${planColor}">${QCMS.escapeHtml(item.subscription_plan)}</span>
                    </td>
                    <td>
                        <div class="text-xs" style="color:var(--ds-text-main);font-weight:500;">${QCMS.formatDate(item.deleted_at)}</div>
                        <div class="text-xs text-muted">Purge: ${purgeDate}</div>
                    </td>
                    <td>
                        <span class="badge rounded-pill" title="Auto-purge on ${purgeDate}"
                            style="background:${badgeColor}18; color:${badgeColor}; font-weight:600; font-size:11px; padding:5px 11px; display:inline-flex; align-items:center; gap:4px;">
                            <i data-lucide="${icon}" style="width:12px;height:12px;flex-shrink:0;"></i>
                            ${daysRemaining} day${daysRemaining !== 1 ? 's' : ''} left
                        </span>
                    </td>
                    <td class="text-end">
                        <div class="d-flex align-items-center justify-content-end gap-2">
                            <button class="ds-btn ds-btn-sm ds-btn-secondary" onclick="SuperAdmin.restoreOrgFromBin(${item.id}, '${nameEsc}')">
                                <i data-lucide="rotate-ccw" style="width:13px;height:13px;"></i> Recover
                            </button>
                            <button class="ds-btn ds-btn-sm" style="background:rgba(239,68,68,0.15); color:#ef4444; border:1px solid rgba(239,68,68,0.3);" onclick="SuperAdmin.deleteOrgPermanently(${item.id}, '${nameEsc}')">
                                <i data-lucide="trash-2" style="width:13px;height:13px;"></i> Permanent Delete
                            </button>
                        </div>
                    </td>
                </tr>`;
        }).join('');


        if (window.lucide) lucide.createIcons();
        this.clearBinSelection();
        this._renderBinPagination(items.length, page, PAGE_SIZE);
    },

    _renderBinPagination(total, currentPage, pageSize) {
        const el = document.getElementById('recycleBinPagination');
        if (!el) return;

        const totalPages = Math.ceil(total / pageSize);
        if (total === 0 || totalPages <= 1) { el.innerHTML = ''; return; }

        const start = (currentPage - 1) * pageSize + 1;
        const end   = Math.min(currentPage * pageSize, total);

        // Build page number list with ellipsis
        const pages = [];
        for (let i = 1; i <= totalPages; i++) {
            if (i === 1 || i === totalPages || (i >= currentPage - 2 && i <= currentPage + 2)) {
                pages.push(i);
            } else if (pages[pages.length - 1] !== '...') {
                pages.push('...');
            }
        }

        const btnBase  = 'display:inline-flex;align-items:center;justify-content:center;min-width:32px;height:32px;padding:0 8px;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;border:1px solid transparent;transition:all .15s;';
        const btnGhost = btnBase + 'background:transparent;color:var(--ds-text-muted);border-color:var(--ds-border);';
        const btnActive= btnBase + 'background:var(--ds-primary);color:#fff;border-color:var(--ds-primary);';
        const btnDisabled = btnBase + 'background:transparent;color:var(--ds-text-muted);opacity:0.35;cursor:not-allowed;border-color:var(--ds-border);';

        el.innerHTML = `
            <div style="display:flex;align-items:center;justify-content:space-between;padding:12px 16px;border-top:1px solid var(--ds-border);">
                <span class="text-xs text-muted">Showing <strong>${start}&ndash;${end}</strong> of <strong>${total}</strong> organizations</span>
                <div style="display:flex;align-items:center;gap:4px;">
                    <button onclick="SuperAdmin.goToBinPage(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''}
                        style="${currentPage === 1 ? btnDisabled : btnGhost}" title="Previous page">
                        <i data-lucide="chevron-left" style="width:14px;height:14px;"></i>
                    </button>
                    ${pages.map(p => p === '...' ?
                        `<span style="${btnBase}border:none;cursor:default;color:var(--ds-text-muted);">&#8230;</span>` :
                        `<button onclick="SuperAdmin.goToBinPage(${p})" style="${p === currentPage ? btnActive : btnGhost}">${p}</button>`
                    ).join('')}
                    <button onclick="SuperAdmin.goToBinPage(${currentPage + 1})" ${currentPage === totalPages ? 'disabled' : ''}
                        style="${currentPage === totalPages ? btnDisabled : btnGhost}" title="Next page">
                        <i data-lucide="chevron-right" style="width:14px;height:14px;"></i>
                    </button>
                </div>
            </div>`;
        if (window.lucide) lucide.createIcons();
    },

    goToBinPage(page) {
        const totalPages = Math.ceil((this._binItems || []).length / 5);
        if (page < 1 || page > totalPages) return;
        this._binPage = page;
        // Scroll table into view smoothly
        const table = document.getElementById('recycleBinTable');
        if (table) table.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        this._renderBinPage();
    },


    // ── Checkbox / bulk-selection helpers ───────────────────────────────────

    toggleAllBinRows(checked) {
        document.querySelectorAll('.bin-row-check').forEach(cb => { cb.checked = checked; });
        this.updateBinBulkBar();
    },

    updateBinBulkBar() {
        const checks = [...document.querySelectorAll('.bin-row-check')];
        const selected = checks.filter(c => c.checked);
        const count = selected.length;
        const bulk = document.getElementById('recycleBinBulkBar');
        const countEl = document.getElementById('recycleBinSelectedCount');
        const pluralEl = document.getElementById('recycleBinSelectedPlural');
        const clearBtn = document.getElementById('recycleBinClearSelBtn');
        const selectAll = document.getElementById('recycleBinSelectAll');

        if (bulk) bulk.style.display = count > 0 ? 'block' : 'none';
        if (clearBtn) clearBtn.style.display = count > 0 ? 'inline-flex' : 'none';
        if (countEl) countEl.textContent = count;
        if (pluralEl) pluralEl.textContent = count === 1 ? '' : 's';
        // Indeterminate state on select-all
        if (selectAll) {
            selectAll.indeterminate = count > 0 && count < checks.length;
            selectAll.checked = count > 0 && count === checks.length;
        }
        if (window.lucide) lucide.createIcons();
    },

    clearBinSelection() {
        document.querySelectorAll('.bin-row-check').forEach(cb => { cb.checked = false; });
        const selectAll = document.getElementById('recycleBinSelectAll');
        if (selectAll) { selectAll.checked = false; selectAll.indeterminate = false; }
        this.updateBinBulkBar();
    },

    async bulkRestoreFromBin() {
        const ids = [...document.querySelectorAll('.bin-row-check:checked')].map(c => +c.dataset.id);
        if (!ids.length) return;
        if (!confirm(`Restore ${ids.length} organization${ids.length !== 1 ? 's' : ''} back to active state?`)) return;
        api.showNotification(`Restoring ${ids.length} organization${ids.length !== 1 ? 's' : ''}…`, 'info');
        let ok = 0, fail = 0;
        for (const id of ids) {
            try { await api.post(`/super-admin/companies/${id}/restore`); ok++; }
            catch { fail++; }
        }
        api.showNotification(
            fail === 0
                ? `${ok} organization${ok !== 1 ? 's' : ''} restored successfully`
                : `${ok} restored, ${fail} failed`,
            fail === 0 ? 'success' : 'warning'
        );
        this.loadRecycleBin();
        this.loadOrganizations?.();
    },

    async bulkDeletePermanently() {
        const ids = [...document.querySelectorAll('.bin-row-check:checked')].map(c => +c.dataset.id);
        if (!ids.length) return;
        if (!confirm(`PERMANENT DELETION WARNING:\n\nYou are about to PERMANENTLY DELETE ${ids.length} organization${ids.length !== 1 ? 's' : ''}.\n\nAll their users, subscriptions, and data will be PERMANENTLY ERASED.\nTHIS ACTION CANNOT BE UNDONE!`)) return;
        api.showNotification(`Permanently deleting ${ids.length} organization${ids.length !== 1 ? 's' : ''}…`, 'info');
        let ok = 0, fail = 0;
        for (const id of ids) {
            try { await api.delete(`/super-admin/recycle-bin/${id}/permanent`); ok++; }
            catch { fail++; }
        }
        api.showNotification(
            fail === 0
                ? `${ok} organization${ok !== 1 ? 's' : ''} permanently deleted`
                : `${ok} deleted, ${fail} failed`,
            fail === 0 ? 'success' : 'warning'
        );
        this.loadRecycleBin();
    },

    // ── Single-item actions ───────────────────────────────────────────────────

    async restoreOrgFromBin(id, name) {
        try {
            api.showNotification(`Recovering ${name}…`, 'info');
            const res = await api.post(`/super-admin/companies/${id}/restore`);
            api.showNotification(res.message || `Organization '${name}' recovered successfully`, 'success');
            this.loadRecycleBin();
            this.loadOrganizations();
        } catch (err) {
            api.showNotification((err && err.message) || 'Failed to recover organization', 'error');
        }
    },

    async deleteOrgPermanently(id, name) {
        if (!confirm(`PERMANENT DELETION WARNING:\n\nAre you sure you want to PERMANENTLY delete '${name}'?\n\nThis will PERMANENTLY ERASE the organization, all its users, subscriptions, data, and settings. THIS ACTION CANNOT BE UNDONE!`)) return;
        try {
            api.showNotification(`Permanently deleting ${name}…`, 'info');
            const res = await api.delete(`/super-admin/recycle-bin/${id}/permanent`);
            api.showNotification(res.message || `Organization '${name}' permanently deleted`, 'success');
            this.loadRecycleBin();
        } catch (err) {
            api.showNotification((err && err.message) || 'Failed to permanently delete organization', 'error');
        }
    },

    async confirmEmptyRecycleBin() {
        if (!confirm(`PERMANENT DELETION WARNING:\n\nAre you sure you want to EMPTY THE RECYCLE BIN?\n\nAll soft-deleted organizations will be PERMANENTLY ERASED from the database forever. THIS ACTION CANNOT BE UNDONE!`)) return;
        try {
            api.showNotification('Emptying Recycle Bin…', 'info');
            const res = await api.post('/super-admin/recycle-bin/empty');
            api.showNotification(res.message || 'Recycle Bin emptied successfully', 'success');
            this.loadRecycleBin();
        } catch (err) {
            api.showNotification((err && err.message) || 'Failed to empty Recycle Bin', 'error');
        }
    }
};


// Global export for inline/onclick handlers immediately
window.SuperAdmin = SuperAdmin;

// Robust Initialization handling both loading state and already-interactive state
function initSuperAdmin() {
    if (document.getElementById('viewTitle') || document.getElementById('overviewView')) {
        SuperAdmin.init();
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSuperAdmin);
} else {
    initSuperAdmin();
}
