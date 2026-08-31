/**
 * OctaQube Enterprise OS — Integration Hub Module
 * Author: UI/UX Architect & Senior Product Manager
 */

(function () {
    // Custom date-time formatter helper
    function formatDateTime(dateStr) {
        if (!dateStr || dateStr === '—') return '—';
        if (window.OctaQube && typeof OctaQube.formatDate === 'function' && typeof OctaQube.formatTime === 'function') {
            return OctaQube.formatDate(dateStr) + ' ' + OctaQube.formatTime(dateStr);
        }
        const d = new Date(dateStr);
        if (isNaN(d.getTime())) return '—';
        return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) + ' ' +
               d.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: true });
    }

    // Fail-safe helper to cleanup modal backdrops and restore page scrolling
    function cleanupModalBackdrops() {
        document.querySelectorAll('.modal-backdrop').forEach(backdrop => backdrop.remove());
        document.body.classList.remove('modal-open');
        document.body.style.overflow = '';
        document.body.style.paddingRight = '';
    }

    const IntegrationsModule = {
        activeCategory: 'All',
        integrations: [],
        dashboardData: {},
        selectedIntegration: null,
        apiKeys: [],
        webhooks: [],
        logsData: { audit_logs: [], webhook_deliveries: [], request_logs: [] },
         categories: [
            { id: 'All', name: 'All Categories', icon: 'grid' },
            { id: 'Communication', name: 'Communication', icon: 'message-square' },
            { id: 'Security', name: 'Security', icon: 'key-round' },
            { id: 'Database', name: 'Database', icon: 'database' },
            { id: 'Payments', name: 'Payments', icon: 'credit-card' },
            { id: 'Logging', name: 'Logging', icon: 'activity' },
            { id: 'Monitoring', name: 'Monitoring', icon: 'heart' }
        ],

        async init() {
            cleanupModalBackdrops();
            this.ensureModalInDOM();
            this.activeCategory = 'All';
            this.selectedIntegration = null;
            await this.loadData();
            this.render();
        },

        ensureModalInDOM() {
            let modalEl = document.getElementById('integrationDetailModal');
            if (!modalEl) {
                modalEl = document.createElement('div');
                modalEl.id = 'integrationDetailModal';
                modalEl.className = 'modal fade';
                modalEl.setAttribute('tabindex', '-1');
                modalEl.setAttribute('aria-hidden', 'true');
                modalEl.style.zIndex = '1060';
                modalEl.innerHTML = `
                    <div class="modal-dialog modal-xl modal-dialog-centered">
                        <div class="modal-content text-start border-0 shadow-lg" style="background:var(--ds-bg-card); border: 1px solid var(--ds-border-color); border-radius: var(--ds-radius-lg); overflow:hidden;">
                            <div class="modal-header px-4 py-3 align-items-center" style="border-bottom: 1px solid var(--ds-border-color); background: rgba(255,255,255,0.01);">
                                <div class="d-flex align-items-center gap-3">
                                    <div class="rounded-3 p-2 bg-primary bg-opacity-10 d-flex align-items-center justify-content-center" id="detailIconContainer">
                                        <i data-lucide="cpu" class="text-primary" style="width:22px; height:22px;"></i>
                                    </div>
                                    <div>
                                        <h5 class="modal-title fw-bold text-main" id="detailTitle">Integration Details</h5>
                                        <div class="text-xxs text-muted d-flex align-items-center gap-2 mt-0.5">
                                            <span id="detailVersion">v1.0.0</span> · 
                                            <span id="detailCategory">AI Providers</span> · 
                                            <span class="ds-badge" id="detailStatusBadge" style="font-size: 9px; padding: 1px 5px;">Status</span>
                                        </div>
                                    </div>
                                </div>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body p-0">
                                <!-- Tab contents -->
                                <div class="p-4" id="modalTabContent" style="max-height: 60vh; overflow-y: auto;">
                                    <!-- Dynamic -->
                                </div>
                            </div>
                            <div class="modal-footer px-4 py-3" style="border-top: 1px solid var(--ds-border-color);" id="modalFooterActions">
                                <!-- Dynamic -->
                            </div>
                        </div>
                    </div>
                `;
                document.body.appendChild(modalEl);
            }
        },

        async loadData() {
            const safeGet = async (url, fallback) => {
                try {
                    const res = await api.get(url);
                    return res ?? fallback;
                } catch (e) {
                    console.warn(`[IntegrationsModule] Failed to load ${url}:`, e.message || e);
                    return fallback;
                }
            };

            // Fetch all data sources in parallel with individual fallbacks
            const [cfgRes, dashRes, keysRes, whRes, logsRes] = await Promise.all([
                safeGet('/super-admin/integrations',           []),
                safeGet('/super-admin/integrations/dashboard', {}),
                safeGet('/super-admin/integrations/apikeys',   []),
                safeGet('/super-admin/integrations/webhooks',  []),
                safeGet('/super-admin/integrations/logs',      { audit_logs: [], webhook_deliveries: [], request_logs: [] }),
            ]);

            this.integrations  = Array.isArray(cfgRes)  ? cfgRes  : [];
            this.dashboardData = dashRes || {};
            this.apiKeys       = Array.isArray(keysRes) ? keysRes : [];
            this.webhooks      = Array.isArray(whRes)   ? whRes   : [];
            this.logsData      = logsRes || { audit_logs: [], webhook_deliveries: [], request_logs: [] };
        },

        render() {
            cleanupModalBackdrops();
            const container = document.getElementById('superAdminIntegrationsContainer');
            if (!container) return;

            const visibleCategories = this.categories.filter(c => {
                if (c.id === 'All') return true;
                return this.integrations.some(i => i.category === c.id);
            });

            container.innerHTML = `
                <!-- SCROLLABLE SUB-HEADER AND CONTENT LAYOUT -->
                <div class="row g-4 mt-0 align-items-stretch">
                    <!-- Left sidebar menu -->
                    <div class="col-lg-3">
                        <div class="glass-card p-3 h-100 d-flex flex-column gap-1" style="background: rgba(255,255,255,0.02);">
                            <h6 class="text-xxs text-uppercase fw-bold tracking-wider text-muted px-2 mb-3">Categories</h6>
                            ${visibleCategories.map(c => `
                                <button class="ds-btn w-100 text-start d-flex align-items-center justify-content-between px-3 py-2 border-0 rounded-3 ${this.activeCategory === c.id ? 'bg-primary text-white' : 'ds-btn-outline text-main'}" 
                                        style="font-size:12.5px; height:auto; transition: all 0.2s;" 
                                        onclick="window.IntegrationsModule.switchCategory('${c.id}')">
                                    <div class="d-flex align-items-center gap-2">
                                        <i data-lucide="${c.icon}" style="width:14px; height:14px;"></i>
                                        <span>${c.name}</span>
                                    </div>
                                    ${this.getCategoryCountBadge(c.id)}
                                </button>
                            `).join('')}
                        </div>
                    </div>

                    <!-- Main Viewport -->
                    <div class="col-lg-9">
                        <!-- Dashboard section -->
                        ${this.activeCategory === 'All' ? this.renderDashboardMarkup() : ''}

                        <!-- Category Viewport -->
                        <div class="mt-2" id="integrationsViewport">
                            ${this.renderViewportContent()}
                        </div>
                    </div>
                </div>

                </div>
            `;

            if (window.lucide) {
                window.lucide.createIcons({ container: container });
            }
        },

        getCategoryCountBadge(catId) {
            if (catId === 'All') return '';
            if (catId === 'Developer Center') {
                return `<span class="badge bg-secondary bg-opacity-10 text-main rounded-pill text-xxs px-1.5 py-0.5">${this.apiKeys.length}</span>`;
            }
            const count = this.integrations.filter(i => i.category === catId).length;
            if (count === 0) return '';
            return `<span class="badge bg-primary bg-opacity-10 text-primary rounded-pill text-xxs px-1.5 py-0.5">${count}</span>`;
        },

        renderDashboardMarkup() {
            const list = this.integrations || [];
            const totalCount = list.length;
            const activeCount = list.filter(i => i.status === 'Connected').length;
            const failedCount = list.filter(i => i.status === 'Error' || i.status === 'Failed').length;

            const stats = this.dashboardData || {};
            const apiCallsToday = stats.api_requests_today || 0;
            const webhookDeliveriesToday = stats.webhook_deliveries_today !== undefined ? stats.webhook_deliveries_today : (this.logsData?.webhook_deliveries?.length || 0);
            const activeDevKeys = (this.apiKeys || []).filter(k => k.status === 'Active' || k.status === 'active').length;
            const activeApiKeys = (stats.active_api_keys !== undefined && stats.active_api_keys > 0)
                ? stats.active_api_keys
                : (activeCount + activeDevKeys);

            return `
                <!-- EXECUTIVE DASHBOARD KPI METRICS -->
                <div class="anc-kpi-grid" style="grid-template-columns: repeat(2, 1fr) !important;">
                    <div class="anc-kpi-card">
                        <div class="kpi-icon" style="background: rgba(var(--ds-primary-rgb), 0.08);">
                            <i data-lucide="blocks" style="width:11px; height:11px; color:var(--ds-primary);"></i>
                        </div>
                        <div class="kpi-label">Total Integrations</div>
                        <div class="kpi-value">${totalCount}</div>
                        <div class="kpi-accent" style="background:var(--ds-primary);"></div>
                    </div>
                    <div class="anc-kpi-card">
                        <div class="kpi-icon" style="background: rgba(16, 185, 129, 0.08);">
                            <i data-lucide="check-circle" style="width:11px; height:11px; color:#10b981;"></i>
                        </div>
                        <div class="kpi-label">Active Connections</div>
                        <div class="kpi-value">${activeCount}</div>
                        <div class="kpi-accent" style="background:#10b981;"></div>
                    </div>
                </div>
            `;
        },

        renderViewportContent() {
            if (this.activeCategory === 'Developer Center') {
                return this.renderDeveloperCenter();
            }

            // Filters integrations by category
            const list = this.activeCategory === 'All' 
                ? this.integrations 
                : this.integrations.filter(i => i.category === this.activeCategory);

            if (list.length === 0) {
                return `
                    <div class="glass-card text-center py-5">
                        <i data-lucide="blocks" class="text-muted mb-3" style="width:40px; height:40px;"></i>
                        <h6 class="text-main fw-bold">No integrations found</h6>
                        <p class="text-xs text-muted mb-0">No active connector is configured in this category.</p>
                    </div>
                `;
            }

            return `
                <div class="row g-3">
                    ${list.map(i => {
                        const scoreColor = i.health_score > 90 ? 'text-success' : (i.health_score > 70 ? 'text-warning' : 'text-danger');
                        const isConnected = i.status === 'Connected';
                        const statusBadgeClass = isConnected ? 'green' : (i.status === 'Disconnected' ? 'gray' : (i.status === 'Disabled' ? 'orange' : 'red'));
                        const providerIcon = this.getProviderIconName(i.provider_id);
                        
                        return `
                            <div class="col-md-6 col-xl-4 d-flex">
                                <div class="glass-card w-100 p-4 d-flex flex-column justify-content-between transition clickable hover-shadow" 
                                     style="border-color: var(--ds-border-color); cursor:pointer; overflow: hidden;" 
                                     onclick="window.IntegrationsModule.openDetails('${i.provider_id}')">
                                    
                                    <div>
                                        <div class="d-flex justify-content-between align-items-start mb-3 gap-2">
                                            <div class="min-w-0" style="min-width: 0;">
                                                <h6 class="fw-bold text-main mb-1 text-truncate" style="font-size:13.5px;" title="${i.provider_name}">${i.provider_name}</h6>
                                                <div class="d-flex align-items-center gap-1.5 flex-wrap">
                                                    <span class="text-xxs text-secondary">v${i.version || '1.0'}</span>
                                                    <span class="ds-badge ${statusBadgeClass}" style="font-size:9px; padding:2px 6px;">${i.status}</span>
                                                </div>
                                            </div>
                                            <div class="d-flex align-items-center flex-shrink-0 ms-1" onclick="event.stopPropagation();">
                                                <label class="integration-toggle-switch m-0 position-relative d-inline-block" style="width:38px; height:20px; flex-shrink:0; cursor:pointer;" title="Toggle integration status">
                                                    <input type="checkbox" 
                                                           style="opacity:0; width:0; height:0; position:absolute;" 
                                                           ${isConnected ? 'checked' : ''} 
                                                           onchange="event.stopPropagation(); window.IntegrationsModule.toggleIntegrationStatus('${i.provider_id}', this.checked)">
                                                    <span class="position-absolute top-0 start-0 end-0 bottom-0 rounded-pill transition" 
                                                          style="background:${isConnected ? 'var(--ds-primary, #2563eb)' : 'rgba(148, 163, 184, 0.4)'}; transition: 0.25s ease;">
                                                        <span class="position-absolute rounded-circle bg-white shadow-sm transition" 
                                                              style="width:14px; height:14px; top:3px; left:${isConnected ? '21px' : '3px'}; transition: 0.25s ease;"></span>
                                                    </span>
                                                </label>
                                            </div>
                                        </div>

                                        <div class="mb-1">
                                            ${this.getProviderUsageTag(i.provider_id)}
                                        </div>
                                    </div>

                                    <div class="mt-4 pt-3 border-top" style="border-color:var(--ds-border-color)!important;">
                                        <button class="ds-btn ds-btn-outline ds-btn-sm w-100 d-flex align-items-center justify-content-center gap-1.5 py-1.5" 
                                                onclick="event.stopPropagation(); window.IntegrationsModule.openDetails('${i.provider_id}')"
                                                style="border-radius: 8px; font-size:11.5px; height:auto; font-weight:600;">
                                            <i data-lucide="settings" style="width:13px; height:13px; margin-top:-1px;"></i> Configure
                                        </button>
                                    </div>
                                </div>
                            </div>
                        `;
                    }).join('')}
                </div>
            `;
        },

        getProviderUsageTag(id) {
            const tags = {
                jio_dlt: '<span class="badge rounded-pill text-xxs px-2 py-1" style="background: rgba(59, 130, 246, 0.12); color: #3b82f6; border: 1px solid rgba(59, 130, 246, 0.2);"><i data-lucide="smartphone" class="me-1" style="width:11px; height:11px; vertical-align:-1px;"></i> Used for SMS & Phone OTP</span>',
                zeptomail: '<span class="badge rounded-pill text-xxs px-2 py-1" style="background: rgba(139, 92, 246, 0.12); color: #8b5cf6; border: 1px solid rgba(139, 92, 246, 0.2);"><i data-lucide="mail" class="me-1" style="width:11px; height:11px; vertical-align:-1px;"></i> Used for Email OTP Service</span>',
                resend: '<span class="badge rounded-pill text-xxs px-2 py-1" style="background: rgba(16, 185, 129, 0.12); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.2);"><i data-lucide="send" class="me-1" style="width:11px; height:11px; vertical-align:-1px;"></i> Used for Transactional Emails</span>',
                razorpay: '<span class="badge rounded-pill text-xxs px-2 py-1" style="background: rgba(14, 165, 233, 0.12); color: #0ea5e9; border: 1px solid rgba(14, 165, 233, 0.2);"><i data-lucide="credit-card" class="me-1" style="width:11px; height:11px; vertical-align:-1px;"></i> Used for Online Card & UPI Gateway</span>',
                dynamic_qr: '<span class="badge rounded-pill text-xxs px-2 py-1" style="background: rgba(245, 158, 11, 0.12); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.2);"><i data-lucide="qr-code" class="me-1" style="width:11px; height:11px; vertical-align:-1px;"></i> Used for Dynamic UPI QR Payment</span>'
            };
            return tags[id] || '<span class="badge bg-secondary bg-opacity-10 text-muted rounded-pill text-xxs px-2 py-1"><i data-lucide="cpu" class="me-1" style="width:11px; height:11px; vertical-align:-1px;"></i> Custom Integration</span>';
        },

        async toggleIntegrationStatus(providerId, isConnected) {
            const newStatus = isConnected ? 'Connected' : 'Disconnected';
            const item = this.integrations.find(i => i.provider_id === providerId);
            const providerName = item ? item.provider_name : providerId;

            try {
                await api.post(`/super-admin/integrations/${providerId}/config`, {
                    status: newStatus
                });
                
                if (window.OctaQube && typeof OctaQube.toast === 'function') {
                    OctaQube.toast(`${providerName} status updated to ${newStatus}`, isConnected ? 'success' : 'info');
                }
                await this.loadData();
                this.render();
            } catch (e) {
                console.error("Failed to toggle integration status:", e);
                if (window.OctaQube && typeof OctaQube.toast === 'function') {
                    OctaQube.toast(`Failed to update ${providerName} status`, 'error');
                }
                await this.loadData();
                this.render();
            }
        },

        getProviderIconName(id) {
            const icons = {
                resend: 'mail',
                jio_dlt: 'smartphone',
                zeptomail: 'send',
                twilio_sms: 'message-square',
                meta_whatsapp: 'phone-call',
                google_oauth: 'log-in',
                firebase_auth: 'users',
                api_keys: 'key',
                webhooks_mgr: 'webhook',
                openai: 'sparkles',
                google_gemini: 'sparkles',
                aws_s3: 'hard-drive',
                postgresql: 'database',
                stripe: 'credit-card',
                google_analytics: 'line-chart',
                sentry: 'activity',
                google_maps: 'map-pin',
                health_checks: 'heart'
            };
            return icons[id] || 'cpu';
        },

        switchCategory(catId) {
            this.activeCategory = catId;
            this.render();
        },

        // ── DETAILED MODAL VIEWS ──────────────────────────────────────────────────

        openDetails(providerId) {
            this.ensureModalInDOM();
            const item = this.integrations.find(i => i.provider_id === providerId);
            if (!item) return;

            this.selectedIntegration = item;
            
            // Build modal header fields
            document.getElementById('detailTitle').textContent = item.provider_name;
            document.getElementById('detailVersion').textContent = item.version;
            document.getElementById('detailCategory').textContent = item.category;

            const statusBadge = document.getElementById('detailStatusBadge');
            statusBadge.textContent = item.status;
            statusBadge.className = `ds-badge ${item.status === 'Connected' ? 'green' : (item.status === 'Disconnected' ? 'gray' : (item.status === 'Disabled' ? 'orange' : 'red'))}`;

            const iconContainer = document.getElementById('detailIconContainer');
            const iconName = this.getProviderIconName(item.provider_id);
            iconContainer.innerHTML = `<i data-lucide="${iconName}" class="text-primary" style="width:22px; height:22px;"></i>`;

            // Open directly on Configuration tab
            this.switchModalTab('Config');

            const modalEl = document.getElementById('integrationDetailModal');
            let modal = bootstrap.Modal.getInstance(modalEl);
            if (!modal) {
                modal = new bootstrap.Modal(modalEl);
            }
            modal.show();
        },

        switchModalTab(tabId) {
            const contentArea = document.getElementById('modalTabContent');
            const footerArea = document.getElementById('modalFooterActions');
            const item = this.selectedIntegration;

            // Only Configuration tab is supported
            contentArea.innerHTML = this.renderModalConfig(item);
            footerArea.innerHTML = `
                <button class="ds-btn ds-btn-secondary me-auto" data-bs-dismiss="modal">Close</button>
                <button class="ds-btn ds-btn-primary" type="button" onclick="window.IntegrationsModule.saveIntegrationConfig('${item.provider_id}')">Save Changes</button>
            `;

            if (window.lucide) {
                window.lucide.createIcons({ container: contentArea });
                window.lucide.createIcons({ container: footerArea });
            }
        },

        renderModalOverview(item) {
            const settings = item.settings || {};
            const displaySettings = Object.entries(settings).map(([key, val]) => {
                const isMasked = key.includes('key') || key.includes('token') || key.includes('secret') || key.includes('password');
                const displayVal = isMasked 
                    ? (val ? `${val.substring(0, 6)}••••••••••••` : '••••••••••••••••')
                    : val;
                
                return `
                    <div class="d-flex align-items-center justify-content-between p-3 rounded-3 mb-2 border" 
                         style="background: rgba(255,255,255,0.02); border-color: var(--ds-border-color); transition: all 0.2s;">
                        <div class="d-flex align-items-center gap-2">
                            <i data-lucide="${isMasked ? 'shield-check' : 'file-text'}" class="${isMasked ? 'text-primary' : 'text-secondary'}" style="width:15px; height:15px;"></i>
                            <div>
                                <span class="text-xxs text-secondary text-uppercase fw-bold d-block" style="font-size: 8px; letter-spacing:0.5px; opacity:0.8;">${key.replace(/_/g, ' ')}</span>
                                <code class="text-xs text-main fw-semibold">${displayVal || '—'}</code>
                            </div>
                        </div>
                        ${val ? `
                            <button class="btn btn-link btn-sm p-1 text-secondary hover-text-main transition" 
                                    onclick="navigator.clipboard.writeText('${val}'); if(window.OctaQube && typeof OctaQube.toast === 'function') { OctaQube.toast('Copied to clipboard', 'success'); } else { alert('Copied to clipboard'); }" 
                                    title="Copy Value" type="button">
                                <i data-lucide="copy" style="width:13px; height:13px;"></i>
                            </button>
                        ` : ''}
                    </div>
                `;
            }).join('');

            const scoreColor = item.health_score > 90 ? 'text-success' : (item.health_score > 70 ? 'text-warning' : 'text-danger');
            const scoreGlow = item.health_score > 90 ? 'rgba(16, 185, 129, 0.05)' : (item.health_score > 70 ? 'rgba(245, 158, 11, 0.05)' : 'rgba(239, 68, 68, 0.05)');
            const errorGlow = item.error_count > 0 ? 'rgba(239, 68, 68, 0.05)' : 'rgba(255, 255, 255, 0.01)';
            
            return `
                <div class="row g-4">
                    <!-- Left: Metrics Grid -->
                    <div class="col-lg-6">
                        <div class="d-flex align-items-center justify-content-between mb-3">
                            <h6 class="fw-bold text-main mb-0 d-flex align-items-center gap-2">
                                <i data-lucide="gauge" class="text-primary" style="width:16px; height:16px;"></i> Performance Metrics
                            </h6>
                            <span class="text-xxs text-secondary">Updated 1m ago</span>
                        </div>
                        <div class="row g-3">
                            <!-- API Request Volume -->
                            <div class="col-sm-6">
                                <div class="glass-card p-3 d-flex align-items-start gap-3 h-100" style="background: rgba(255,255,255,0.01); border-color: var(--ds-border-color);">
                                    <div class="rounded-3 p-2 bg-primary bg-opacity-10 text-primary">
                                        <i data-lucide="activity" style="width:18px; height:18px;"></i>
                                    </div>
                                    <div>
                                        <h4 class="fw-bold text-main mb-0.5">${item.usage_count.toLocaleString()}</h4>
                                        <span class="text-xxs text-secondary text-uppercase fw-bold" style="font-size: 8px; letter-spacing:0.5px;">API VOLUME</span>
                                    </div>
                                </div>
                            </div>
                            <!-- Logged Failures -->
                            <div class="col-sm-6">
                                <div class="glass-card p-3 d-flex align-items-start gap-3 h-100" style="background: ${errorGlow}; border-color: var(--ds-border-color);">
                                    <div class="rounded-3 p-2 ${item.error_count > 0 ? 'bg-danger text-danger' : 'bg-secondary text-secondary'} bg-opacity-10">
                                        <i data-lucide="alert-octagon" style="width:18px; height:18px;"></i>
                                    </div>
                                    <div>
                                        <h4 class="fw-bold ${item.error_count > 0 ? 'text-danger' : 'text-main'} mb-0.5">${item.error_count.toLocaleString()}</h4>
                                        <span class="text-xxs text-secondary text-uppercase fw-bold" style="font-size: 8px; letter-spacing:0.5px;">LOGGED FAILURES</span>
                                    </div>
                                </div>
                            </div>
                            <!-- Latency Health Score -->
                            <div class="col-sm-6">
                                <div class="glass-card p-3 d-flex align-items-start gap-3 h-100" style="background: ${scoreGlow}; border-color: var(--ds-border-color);">
                                    <div class="rounded-3 p-2 ${item.health_score > 70 ? 'bg-success text-success' : 'bg-danger text-danger'} bg-opacity-10">
                                        <i data-lucide="shield-check" style="width:18px; height:18px;"></i>
                                    </div>
                                    <div>
                                        <h4 class="fw-bold ${scoreColor} mb-0.5">${item.health_score}%</h4>
                                        <span class="text-xxs text-secondary text-uppercase fw-bold" style="font-size: 8px; letter-spacing:0.5px;">HEALTH INDEX</span>
                                    </div>
                                </div>
                            </div>
                            <!-- Average Response Time -->
                            <div class="col-sm-6">
                                <div class="glass-card p-3 d-flex align-items-start gap-3 h-100" style="background: rgba(255,255,255,0.01); border-color: var(--ds-border-color);">
                                    <div class="rounded-3 p-2 bg-info bg-opacity-10 text-info">
                                        <i data-lucide="clock" style="width:18px; height:18px;"></i>
                                    </div>
                                    <div>
                                        <h4 class="fw-bold text-main mb-0.5">35 ms</h4>
                                        <span class="text-xxs text-secondary text-uppercase fw-bold" style="font-size: 8px; letter-spacing:0.5px;">AVG LATENCY</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Right: Secure Key Vault Card -->
                    <div class="col-lg-6">
                        <div class="d-flex align-items-center justify-content-between mb-3">
                            <h6 class="fw-bold text-main mb-0 d-flex align-items-center gap-2">
                                <i data-lucide="key-round" class="text-primary" style="width:16px; height:16px;"></i> Vault Configuration
                            </h6>
                            <span class="badge bg-primary bg-opacity-10 text-primary text-xxs px-2 border border-primary border-opacity-20 d-flex align-items-center gap-1">
                                <i data-lucide="lock" style="width:10px; height:10px;"></i> AES-256 Encrypted
                            </span>
                        </div>
                        <div class="p-3.5 rounded-4 shadow-sm border position-relative overflow-hidden" 
                             style="background: linear-gradient(135deg, rgba(30, 41, 59, 0.04) 0%, rgba(15, 23, 42, 0.08) 100%); border-color: var(--ds-border-color);">
                            
                            <div class="position-relative z-1">
                                ${displaySettings || '<div class="text-center text-xs text-muted py-4">No active credentials configured. Open "Configuration" to set up API keys.</div>'}
                            </div>
                        </div>
                    </div>
                </div>
            `;
        },

        renderModalConfig(item) {
            const settings = item.settings || {};
            const statusToggleChecked = item.status === 'Connected' ? 'checked' : '';
            
            let formFields = '';
            let schemaFields = [];
            if (item.provider_id === 'openai') {
                schemaFields = [
                    { key: 'api_key', label: 'OpenAI API Key (sk-...)', type: 'password', placeholder: 'Enter sk-... API Key' },
                    { key: 'default_model', label: 'Default LLM Model', type: 'text', placeholder: 'e.g. gpt-4o' },
                    { key: 'temperature', label: 'Temperature (0.0 - 1.0)', type: 'number', placeholder: 'e.g. 0.7' }
                ];
            } else if (item.provider_id === 'resend') {
                schemaFields = [
                    { key: 'api_key', label: 'Resend API Token (re_...)', type: 'password', placeholder: 'Enter re_... API Token' },
                    { key: 'sender_email', label: 'Default Sender Email Address', type: 'text', placeholder: 'e.g. notifications@yourdomain.com' }
                ];
            } else if (item.provider_id === 'jio_dlt') {
                schemaFields = [
                    { key: 'entity_id', label: 'Jio DLT Principal Entity ID (PE ID)', type: 'text', placeholder: 'e.g. 1201174858303838784' },
                    { key: 'sender_id', label: 'Approved Header / Sender ID (6 Chars)', type: 'text', placeholder: 'e.g. IFQMSK' },
                    { key: 'account_sid', label: 'Kaleyra Account SID (Optional for Kaleyra)', type: 'text', placeholder: 'e.g. HXIN17xxxxxxxxIN' },
                    { key: 'api_key', label: 'Jio DLT / Kaleyra API Auth Key', type: 'password', placeholder: 'Enter API Key' },
                    { key: 'api_url', label: 'SMS API Gateway Endpoint URL', type: 'text', placeholder: 'https://api.kaleyra.io/' }
                ];
            } else if (item.provider_id === 'zeptomail') {
                schemaFields = [
                    { key: 'api_key', label: 'ZeptoMail Send Mail Token (Zoho-enczapikey...)', type: 'password', placeholder: 'Enter Zoho-enczapikey ...' },
                    { key: 'sender_email', label: 'Verified Sender Email Address', type: 'text', placeholder: 'e.g. otp@yourdomain.com' },
                    { key: 'api_url', label: 'ZeptoMail API Endpoint URL', type: 'text', placeholder: 'https://api.zeptomail.in/v1.1/email' }
                ];
            } else if (item.provider_id === 'razorpay') {
                schemaFields = [
                    { key: 'key_id', label: 'Razorpay Key ID (rzp_live_... / rzp_test_...)', type: 'text', placeholder: 'Enter Key ID (e.g. rzp_live_xxxx)' },
                    { key: 'key_secret', label: 'Razorpay Key Secret', type: 'password', placeholder: 'Enter Key Secret' },
                    { key: 'webhook_secret', label: 'Razorpay Webhook Secret', type: 'password', placeholder: 'Enter Webhook Secret' },
                    { key: 'currency', label: 'Currency Code', type: 'text', placeholder: 'INR' }
                ];
            } else if (item.provider_id === 'dynamic_qr') {
                schemaFields = [
                    { key: 'upi_id', label: 'Organization UPI ID (VPA)', type: 'text', placeholder: 'e.g. octaqube@upi' },
                    { key: 'account_name', label: 'Beneficiary Account Name', type: 'text', placeholder: 'e.g. OctaQube Enterprise Solutions Pvt Ltd' },
                    { key: 'qr_code_url', label: 'QR Code Image URL', type: 'text', placeholder: 'https://api.qrserver.com/v1/create-qr-code/?data=...' },
                    { key: 'instructions', label: 'Payment Instructions', type: 'text', placeholder: 'Scan using GPay, PhonePe, Paytm...' }
                ];
            } else if (item.provider_id === 'stripe') {
                schemaFields = [
                    { key: 'public_key', label: 'Stripe Publishable Key (pk_...)', type: 'text', placeholder: 'Enter pk_live_...' },
                    { key: 'secret_key', label: 'Stripe Secret Key (sk_...)', type: 'password', placeholder: 'Enter sk_live_...' },
                    { key: 'webhook_secret', label: 'Stripe Webhook Signing Secret', type: 'password', placeholder: 'Enter whsec_...' }
                ];
            } else if (item.provider_id === 'aws_s3') {
                schemaFields = [
                    { key: 'bucket_name', label: 'S3 Bucket Name', type: 'text', placeholder: 'e.g. user-uploads-bucket' },
                    { key: 'region', label: 'S3 Region Code', type: 'text', placeholder: 'e.g. us-east-1' },
                    { key: 'access_key_id', label: 'AWS Access Key ID', type: 'text', placeholder: 'e.g. AKIA...' },
                    { key: 'secret_access_key', label: 'AWS Secret Access Key', type: 'password', placeholder: 'Enter AWS Secret' }
                ];
            } else if (item.provider_id === 'postgresql') {
                schemaFields = [
                    { key: 'host', label: 'Database Host Server', type: 'text', placeholder: 'e.g. 127.0.0.1 or db.internal' },
                    { key: 'port', label: 'Logical Port', type: 'number', placeholder: '5432' },
                    { key: 'database', label: 'Logical Database Name', type: 'text', placeholder: 'e.g. production_db' },
                    { key: 'username', label: 'Username', type: 'text', placeholder: 'e.g. postgres' },
                    { key: 'password', label: 'Password', type: 'password', placeholder: 'Database Password' }
                ];
            } else {
                schemaFields = Object.keys(settings).map(k => {
                    const isSec = k.includes('key') || k.includes('secret') || k.includes('token') || k.includes('password');
                    return { key: k, label: k.replace(/_/g, ' ').toUpperCase(), type: isSec ? 'password' : 'text', placeholder: `Enter ${k.replace(/_/g, ' ')}` };
                });
            }

            formFields = schemaFields.map(f => {
                const val = settings[f.key] || '';
                return `
                    <div class="col-md-6 mb-3">
                        <label class="ds-label text-xxs text-uppercase fw-bold text-secondary mb-1" style="font-size:8px; letter-spacing:0.5px; opacity:0.8;">${f.label}</label>
                        <div class="position-relative">
                            <input type="${f.type}" class="ds-input py-2" id="cfg_${f.key}" value="${val}" placeholder="${f.placeholder || ''}" style="font-size:12.5px; height:40px; border-radius:8px; padding-right: 36px;">
                            ${f.type === 'password' ? `
                                <button type="button" class="btn btn-link btn-sm position-absolute top-50 end-0 translate-middle-y p-2 text-secondary hover-text-main transition" 
                                        onclick="const inp = document.getElementById('cfg_${f.key}'); inp.type = inp.type === 'password' ? 'text' : 'password'; this.querySelector('i').setAttribute('data-lucide', inp.type === 'password' ? 'eye' : 'eye-off'); if(window.lucide) window.lucide.createIcons({container:this});"
                                        style="border:none; background:none;">
                                    <i data-lucide="eye" style="width:14px; height:14px;"></i>
                                </button>
                            ` : ''}
                        </div>
                    </div>
                `;
            }).join('');

            return `
                <form id="integrationConfigForm" class="p-1">
                    <div class="d-flex align-items-center gap-2 mb-3">
                        <i data-lucide="sliders" class="text-primary" style="width:16px; height:16px;"></i>
                        <h6 class="fw-bold text-main mb-0">Configuration Parameters</h6>
                    </div>
                    <div class="row g-3">
                        ${formFields || '<div class="col-12 text-center text-xs text-muted py-4">No configuration inputs required.</div>'}
                    ${item.provider_id === 'razorpay' ? `
                        <div class="mt-3 p-3 rounded-3 bg-primary bg-opacity-10 border border-primary border-opacity-20 text-xs">
                            <div class="d-flex align-items-center justify-content-between flex-wrap gap-2">
                                <div>
                                    <strong class="text-primary d-block mb-1"><i data-lucide="help-circle" class="me-1"></i> How to get Razorpay API Keys?</strong>
                                    <span class="text-secondary text-xxs">1. Log in to Razorpay Dashboard &nbsp; 2. Go to Settings &gt; API Keys &nbsp; 3. Generate Key ID & Key Secret</span>
                                </div>
                                <a href="https://dashboard.razorpay.com/app/keys" target="_blank" class="ds-btn ds-btn-primary ds-btn-sm text-decoration-none py-1.5 px-3">
                                    Razorpay Portal <i data-lucide="external-link" style="width:12px;height:12px;" class="ms-1"></i>
                                </a>
                            </div>
                        </div>
                    ` : ''}

                    ${item.provider_id === 'jio_dlt' ? `
                        <div class="mt-3 p-3 rounded-3 bg-primary bg-opacity-10 border border-primary border-opacity-20 text-xs">
                            <div class="d-flex align-items-center justify-content-between flex-wrap gap-2">
                                <div>
                                    <strong class="text-primary d-block mb-1"><i data-lucide="help-circle" class="me-1"></i> How to get Jio DLT API Credentials?</strong>
                                    <span class="text-secondary text-xxs">1. Log in to Jio DLT Portal (trueconnect.jio.com) &nbsp; 2. Copy Principal Entity ID & Header ID &nbsp; 3. Configure Template IDs under Set SMS Notifications</span>
                                </div>
                                <a href="https://trueconnect.jio.com" target="_blank" class="ds-btn ds-btn-primary ds-btn-sm text-decoration-none py-1.5 px-3">
                                    Jio DLT Portal <i data-lucide="external-link" style="width:12px;height:12px;" class="ms-1"></i>
                                </a>
                            </div>
                        </div>
                    ` : ''}

                    ${item.provider_id === 'zeptomail' ? `
                        <div class="mt-3 p-3 rounded-3 bg-primary bg-opacity-10 border border-primary border-opacity-20 text-xs">
                            <div class="d-flex align-items-center justify-content-between flex-wrap gap-2">
                                <div>
                                    <strong class="text-primary d-block mb-1"><i data-lucide="help-circle" class="me-1"></i> How to get ZeptoMail API Credentials?</strong>
                                    <span class="text-secondary text-xxs">1. Log in to ZeptoMail Console (zeptomail.zoho.in) &nbsp; 2. Create Mail Agent & Verify Domain &nbsp; 3. Copy Send Mail Token (Zoho-enczapikey)</span>
                                </div>
                                <a href="https://www.zoho.com/zeptomail/" target="_blank" class="ds-btn ds-btn-primary ds-btn-sm text-decoration-none py-1.5 px-3">
                                    ZeptoMail Portal <i data-lucide="external-link" style="width:12px;height:12px;" class="ms-1"></i>
                                </a>
                            </div>
                        </div>
                    ` : ''}

                    ${settings.webhook_secret ? `
                        <div class="mt-4 p-3.5 rounded-4 border border-warning border-opacity-20 bg-warning bg-opacity-5 d-flex align-items-center justify-content-between gap-3">
                            <div class="d-flex align-items-start gap-3">
                                <div class="rounded-3 p-2 bg-warning bg-opacity-10 text-warning">
                                    <i data-lucide="shield-alert" style="width:18px; height:18px;"></i>
                                </div>
                                <div>
                                    <strong class="text-xs text-main d-block mb-0.5">Webhook Security Secret Key</strong>
                                    <span class="text-xxs text-secondary">Rotate this key if you suspect credentials have been leaked or compromised.</span>
                                </div>
                            </div>
                            <button type="button" class="ds-btn ds-btn-secondary btn-sm d-flex align-items-center gap-1.5" onclick="window.IntegrationsModule.rotateSecretKey('${item.provider_id}')" style="border-radius:8px;">
                                <i data-lucide="rotate-cw" style="width:13px; height:13px;"></i> Rotate Secret
                            </button>
                        </div>
                    ` : ''}
                </form>
            `;
        },

        renderModalLogs(item) {
            const audits = this.logsData.audit_logs.filter(l => l.provider_id === item.provider_id || l.provider_id === 'system');
            
            const auditRows = audits.map(l => {
                let badgeColor = 'blue';
                if (l.action.toLowerCase().includes('fail') || l.action.toLowerCase().includes('revok')) badgeColor = 'red';
                else if (l.action.toLowerCase().includes('creat') || l.action.toLowerCase().includes('sav') || l.action.toLowerCase().includes('rotat')) badgeColor = 'orange';
                else if (l.action.toLowerCase().includes('test') || l.action.toLowerCase().includes('success') || l.action.toLowerCase().includes('connect')) badgeColor = 'green';
                
                const detailsObj = l.details || {};
                const detailsStr = Object.entries(detailsObj).map(([k, v]) => {
                    const displayV = typeof v === 'object' ? JSON.stringify(v) : v;
                    return `<span class="badge bg-secondary bg-opacity-10 text-secondary me-1.5 mb-1 text-xxs border border-opacity-10 px-1.5 py-0.5"><strong class="text-main">${k}:</strong> ${displayV}</span>`;
                }).join('') || '<span class="text-muted">—</span>';
                
                return `
                    <tr style="border-color: var(--ds-border-color)!important;">
                        <td class="align-middle py-3">
                            <span class="ds-badge ${badgeColor}" style="font-size:9.5px; padding:2px 6px;">${l.action}</span>
                        </td>
                        <td class="align-middle py-3">
                            <div class="d-flex flex-wrap align-items-center">
                                ${detailsStr}
                            </div>
                        </td>
                        <td class="align-middle py-3 text-secondary">
                            <div class="d-flex align-items-center gap-1.5">
                                <i data-lucide="clock" class="text-muted" style="width:12px; height:12px;"></i>
                                <span>${formatDateTime(l.created_at)}</span>
                            </div>
                        </td>
                    </tr>
                `;
            }).join('');

            return `
                <div class="p-1">
                    <div class="d-flex align-items-center gap-2 mb-3">
                        <i data-lucide="shield-check" class="text-primary" style="width:16px; height:16px;"></i>
                        <h6 class="fw-bold text-main mb-0">Security and Event Audit Trail</h6>
                    </div>
                    <div class="table-responsive rounded-3 border" style="border-color: var(--ds-border-color)!important;">
                        <table class="ds-table mb-0" style="font-size:11.5px; background: rgba(0,0,0,0.01);">
                            <thead style="background: rgba(255,255,255,0.01);">
                                <tr style="border-color: var(--ds-border-color)!important;">
                                    <th class="py-2.5">Event Action</th>
                                    <th class="py-2.5">Audit Details</th>
                                    <th class="py-2.5">Logged At</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${auditRows || '<tr><td colspan="3" class="text-center text-secondary py-4">No audit logs found for this integration.</td></tr>'}
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
        },

        // ── SAVE AND CONNECTION OPERATIONS ────────────────────────────────────────

        async saveIntegrationConfig(providerId) {
            const form = document.getElementById('integrationConfigForm');
            if (!form) return;

            const toggleEl = document.getElementById('cfg_status_toggle');
            const status = toggleEl ? (toggleEl.checked ? 'Connected' : 'Disconnected') : 'Connected';
            
            const settings = {};
            // Scrapes all input, textarea, and select elements
            form.querySelectorAll('[id^="cfg_"]').forEach(inp => {
                if (inp.id === 'cfg_status_toggle') return;
                const key = inp.id.replace('cfg_', '');
                settings[key] = (inp.value || '').trim();
            });

            try {
                const res = await api.post(`/super-admin/integrations/${providerId}/config`, {
                    status: status,
                    settings: settings
                });
                
                if (window.OctaQube && typeof OctaQube.toast === 'function') {
                    OctaQube.toast(`Configuration saved for ${providerId}`, 'success');
                }
                
                // Hide modal and refresh data
                const modalEl = document.getElementById('integrationDetailModal');
                const modal = bootstrap.Modal.getInstance(modalEl);
                if (modal) {
                    modal.hide();
                } else {
                    const closeBtn = modalEl.querySelector('[data-bs-dismiss="modal"]');
                    if (closeBtn) closeBtn.click();
                }
                await this.init();
            } catch (e) {
                console.error("Save config failed", e);
                if (window.OctaQube && typeof OctaQube.toast === 'function') {
                    OctaQube.toast('Failed to save configuration settings', 'error');
                } else {
                    alert('Failed to save configuration settings');
                }
            }
        },

        async testIntegration(providerId) {
            OctaQube.toast(`Testing connection to ${providerId}...`, 'info');
            try {
                const res = await api.post(`/super-admin/integrations/${providerId}/test`, {});
                if (res.success) {
                    OctaQube.toast(`Connection OK! Latency: ${res.latency_ms}ms`, 'success');
                } else {
                    OctaQube.toast(`Connection failed: ${res.message}`, 'error');
                }
                
                // Refresh modal and view data
                await this.loadData();
                const updatedItem = this.integrations.find(i => i.provider_id === providerId);
                this.selectedIntegration = updatedItem;
                this.switchModalTab('Overview');
                
                // Update badge in modal header
                const statusBadge = document.getElementById('detailStatusBadge');
                statusBadge.textContent = updatedItem.status;
                statusBadge.className = `ds-badge ${updatedItem.status === 'Connected' ? 'green' : 'red'}`;
            } catch (e) {
                console.error("Test failed", e);
                OctaQube.toast('Error dispatching test connection request', 'error');
            }
        },

        async rotateSecretKey(providerId) {
            if (!confirm("Are you sure you want to rotate the webhook secret token?")) return;
            try {
                const res = await api.post(`/super-admin/integrations/${providerId}/rotate`, {});
                OctaQube.toast("Webhook secret rotated successfully", "success");
                
                // Reload configuration tab
                await this.loadData();
                this.selectedIntegration = this.integrations.find(i => i.provider_id === providerId);
                this.switchModalTab('Config');
            } catch (e) {
                console.error("Rotate secret failed", e);
                OctaQube.toast('Failed to rotate webhook token secret', 'error');
            }
        },

        // ── DEVELOPER CENTER SUB-MODULE ───────────────────────────────────────────

        renderDeveloperCenter() {
            return `
                <div class="row g-4">
                    <!-- Left: Keys & Webhooks manager -->
                    <div class="col-lg-7">
                        <!-- REST API Keys card -->
                        <div class="glass-card p-4 mb-4">
                            <div class="d-flex justify-content-between align-items-center mb-3">
                                <div>
                                    <h6 class="fw-bold text-main mb-0.5">REST API Developer Keys</h6>
                                    <span class="text-xxs text-secondary">Platform access tokens for REST API endpoints and CLI clients.</span>
                                </div>
                                <button class="ds-btn ds-btn-primary btn-sm" onclick="window.IntegrationsModule.openCreateApiKeyModal()">+ Generate Key</button>
                            </div>
                            
                            <div class="table-responsive">
                                <table class="ds-table" style="font-size:11.5px;">
                                    <thead>
                                        <tr>
                                            <th>Key Name</th>
                                            <th>Secret Token</th>
                                            <th>Allowed Scopes</th>
                                            <th>Created At</th>
                                            <th>Status</th>
                                            <th></th>
                                        </tr>
                                    </thead>
                                    <tbody id="apiKeysTableBody">
                                        ${this.apiKeys.map(k => `
                                            <tr id="apikey-row-${k.id}">
                                                <td><span class="fw-semibold text-main">${k.name}</span></td>
                                                <td><code class="text-xs text-primary">${k.secret_key_masked}</code></td>
                                                <td><span class="text-muted">${(k.scopes || []).join(', ')}</span></td>
                                                <td><span class="text-muted">${formatDateTime(k.created_at)}</span></td>
                                                <td>
                                                    <span class="ds-badge ${k.status === 'Active' ? 'green' : 'gray'}" style="font-size: 9px; padding:1px 5px;">${k.status}</span>
                                                </td>
                                                <td class="text-end">
                                                    ${k.status === 'Active' ? `
                                                        <button class="btn btn-link btn-sm p-0 text-danger text-xs text-decoration-none" onclick="window.IntegrationsModule.revokeApiKey(${k.id})">Revoke</button>
                                                    ` : '—'}
                                                </td>
                                            </tr>
                                        `).join('') || '<tr><td colspan="6" class="text-center text-muted py-3">No API Keys generated yet.</td></tr>'}
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        <!-- Webhooks subscription card -->
                        <div class="glass-card p-4">
                            <div class="d-flex justify-content-between align-items-center mb-3">
                                <div>
                                    <h6 class="fw-bold text-main mb-0.5">Outgoing Webhook Endpoints</h6>
                                    <span class="text-xxs text-secondary">Register URLs to receive HTTP payloads on system updates.</span>
                                </div>
                                <button class="ds-btn ds-btn-primary btn-sm" onclick="window.IntegrationsModule.openCreateWebhookModal()">+ Create Webhook</button>
                            </div>
                            
                            <div class="table-responsive">
                                <table class="ds-table" style="font-size:11.5px;">
                                    <thead>
                                        <tr>
                                            <th>Endpoint Name</th>
                                            <th>Target URL</th>
                                            <th>Events</th>
                                            <th>Status</th>
                                            <th></th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${this.webhooks.map(w => `
                                            <tr id="webhook-row-${w.id}">
                                                <td><span class="fw-semibold text-main">${w.name}</span></td>
                                                <td><span class="text-secondary text-truncate d-inline-block" style="max-width: 180px;">${w.url}</span></td>
                                                <td><span class="text-muted">${(w.events || []).join(', ')}</span></td>
                                                <td>
                                                    <span class="ds-badge ${w.status === 'Active' ? 'green' : 'gray'}" style="font-size:9px; padding:1px 5px;">${w.status}</span>
                                                </td>
                                                <td class="text-end">
                                                    <button class="btn btn-link btn-sm p-0 text-danger text-xs text-decoration-none" onclick="window.IntegrationsModule.deleteWebhook(${w.id})">Delete</button>
                                                </td>
                                            </tr>
                                        `).join('') || '<tr><td colspan="5" class="text-center text-muted py-3">No webhooks registered yet.</td></tr>'}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>

                    <!-- Right: Playground and Swagger references -->
                    <div class="col-lg-5">
                        <!-- Playground Console -->
                        <div class="card border-0 p-4 mb-4 shadow-sm" style="background: #0f172a !important; color: #ffffff !important; border-radius: 16px; border: 1px solid #1e293b !important;">
                            <div class="d-flex align-items-center justify-content-between mb-3 border-bottom pb-2" style="border-color: rgba(255,255,255,0.12)!important;">
                                <div class="d-flex align-items-center gap-2">
                                    <i data-lucide="terminal" class="text-primary" style="width:18px; height:18px;"></i>
                                    <h6 class="fw-bold mb-0" style="color: #ffffff !important; font-size: 0.95rem;">REST API Sandbox Playground</h6>
                                </div>
                                <span class="badge px-2 py-1" style="background-color: #059669 !important; color: #ffffff !important; font-weight: 600; font-size: 0.7rem;">Local Sandbox</span>
                            </div>
                            
                            <div class="d-flex gap-2 mb-3">
                                <select class="ds-input py-1" id="play_method" style="max-width:85px; font-size:12px; height:34px; color:#ffffff !important; background:#1e293b !important; border:1px solid #334155 !important;">
                                    <option value="GET" style="background:#1e293b; color:#ffffff;">GET</option>
                                    <option value="POST" style="background:#1e293b; color:#ffffff;">POST</option>
                                </select>
                                <input type="text" class="ds-input py-1 flex-grow-1" id="play_endpoint" value="/api/v1/licenses" style="font-size:12px; height:34px; color:#ffffff !important; background:#1e293b !important; border:1px solid #334155 !important;">
                            </div>

                            <div class="mb-3">
                                <label class="text-xxs text-uppercase fw-bold mb-1" style="color: #94a3b8 !important;">DEVELOPER API KEY</label>
                                <select class="ds-input" id="play_apikey" style="height:34px; font-size:12px; color:#ffffff !important; background:#1e293b !important; border:1px solid #334155 !important; padding:0 30px 0 12px;">
                                    <option value="qc_live_demotok12345" style="background:#1e293b; color:#ffffff;">qc_live_demotok12345 (Demo token)</option>
                                    ${this.apiKeys.filter(k => k.status === 'Active').map(k => `
                                        <option value="${k.name}" style="background:#1e293b; color:#ffffff;">${k.name} (Hashed)</option>
                                    `).join('')}
                                </select>
                            </div>

                            <div class="mb-3" id="playPayloadBlock" style="display:none;">
                                <label class="text-xxs text-uppercase fw-bold mb-1" style="color: #94a3b8 !important;">Request JSON Body</label>
                                <textarea class="ds-input" id="play_payload" rows="3" style="font-family:monospace; font-size:11px; color:#10b981 !important; background:#070a12 !important; border:1px solid #334155 !important;">{ "plan": "Professional", "organization_id": 3 }</textarea>
                            </div>

                            <button class="ds-btn ds-btn-primary btn-sm w-100 py-2 d-flex align-items-center justify-content-center gap-1" onclick="window.IntegrationsModule.runPlaygroundRequest()">
                                <i data-lucide="play" style="width:13px; height:13px;"></i> Send REST Request
                            </button>

                            <!-- Sandbox Response area -->
                            <div class="mt-4 border-top pt-3" style="border-color: rgba(255,255,255,0.12)!important;">
                                <div class="d-flex justify-content-between text-xxs mb-2" style="color: #94a3b8 !important;">
                                    <span>Response Console</span>
                                    <span id="playResponseMeta" style="color: #94a3b8 !important;">—</span>
                                </div>
                                <pre class="p-3 rounded mb-0" id="playResponseConsole" style="background:#070a12 !important; color:#10b981 !important; font-family:monospace; font-size:11px; max-height:220px; overflow-y:auto; border:1px solid #1e293b !important;">{ "message": "Console initialized. Waiting for trigger..." }</pre>
                            </div>
                        </div>

                        <!-- Documentation reference cards -->
                        <div class="glass-card p-4">
                            <h6 class="fw-bold text-main mb-1">Developer Assets</h6>
                            <p class="text-xxs text-secondary mb-3">Integrate OctaQube platform capabilities into your client applications, build boards, and fetch telemetry logs.</p>
                            
                            <div class="d-flex flex-column gap-2.5">
                                <a href="javascript:void(0)" class="border p-2.5 rounded-3 d-flex align-items-center justify-content-between text-decoration-none hover-bg" style="border-color:var(--ds-border-color); background:rgba(255,255,255,0.01);" onclick="OctaQube.toast('Downloaded Swagger API Spec (JSON)','info')">
                                    <div class="d-flex align-items-center gap-2">
                                        <i data-lucide="file-json" class="text-primary" style="width:15px; height:15px;"></i>
                                        <div>
                                            <span class="text-xs text-main fw-semibold d-block">Swagger API Spec v1.0.0</span>
                                            <span class="text-xxs text-secondary">JSON OpenAPI declaration format</span>
                                        </div>
                                    </div>
                                    <i data-lucide="download" class="text-muted" style="width:13px; height:13px;"></i>
                                </a>
                                
                                <a href="javascript:void(0)" class="border p-2.5 rounded-3 d-flex align-items-center justify-content-between text-decoration-none hover-bg" style="border-color:var(--ds-border-color); background:rgba(255,255,255,0.01);" onclick="OctaQube.toast('Downloaded Postman Collection','info')">
                                    <div class="d-flex align-items-center gap-2">
                                        <i data-lucide="archive" class="text-warning" style="width:15px; height:15px;"></i>
                                        <div>
                                            <span class="text-xs text-main fw-semibold d-block">Postman Collection</span>
                                            <span class="text-xxs text-secondary">Endpoints payload examples catalog</span>
                                        </div>
                                    </div>
                                    <i data-lucide="download" class="text-muted" style="width:13px; height:13px;"></i>
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        },

        async runPlaygroundRequest() {
            const method = document.getElementById('play_method').value;
            const endpoint = document.getElementById('play_endpoint').value;
            const apiKey = document.getElementById('play_apikey').value;
            let payload = {};
            
            try {
                if (method === 'POST') {
                    payload = JSON.parse(document.getElementById('play_payload').value);
                }
            } catch (e) {
                OctaQube.toast('Invalid JSON format in payload body', 'error');
                return;
            }

            document.getElementById('playResponseConsole').textContent = '// Dispatching sandbox payload...';
            document.getElementById('playResponseMeta').textContent = 'Loading...';

            try {
                const res = await api.post('/super-admin/integrations/playground', {
                    method: method,
                    endpoint: endpoint,
                    api_key: apiKey,
                    payload: payload
                });

                document.getElementById('playResponseMeta').textContent = `STATUS: ${res.status_code} · LATENCY: ${res.latency_ms}ms`;
                document.getElementById('playResponseConsole').textContent = JSON.stringify(res.response, null, 2);
            } catch (e) {
                document.getElementById('playResponseConsole').textContent = '// Execution error: Request failed.';
                document.getElementById('playResponseMeta').textContent = 'Error';
            }
        },

        openCreateApiKeyModal() {
            const name = prompt("Enter a description label for the new API Key:", "REST API integration");
            if (!name) return;
            
            OctaQube.toast("Generating live API token...", "info");
            api.post('/super-admin/integrations/apikeys', { name: name })
                .then(res => {
                    OctaQube.toast("API Key generated successfully!", "success");
                    alert(`IMPORTANT: Copy and save this API key securely. It will NOT be shown again:\n\n${res.api_key}`);
                    this.init();
                })
                .catch(e => {
                    console.error(e);
                    OctaQube.toast("Failed to generate API key", "error");
                });
        },

        revokeApiKey(keyId) {
            if (!confirm("Are you sure you want to revoke this API Key? Clients using this token will lose access immediately.")) return;
            api.post(`/super-admin/integrations/apikeys/${keyId}/status`, { status: 'Revoked' })
                .then(() => {
                    OctaQube.toast("API Key revoked", "success");
                    this.init();
                })
                .catch(e => {
                    console.error(e);
                    OctaQube.toast("Failed to revoke API key", "error");
                });
        },

        openCreateWebhookModal() {
            const name = prompt("Enter a label name for the Webhook endpoint:", "Globex updates listener");
            if (!name) return;
            const url = prompt("Enter the recipient HTTP url endpoint:");
            if (!url) return;

            OctaQube.toast("Registering webhook listener...", "info");
            api.post('/super-admin/integrations/webhooks', { name: name, url: url })
                .then(res => {
                    OctaQube.toast("Webhook registered successfully!", "success");
                    this.init();
                })
                .catch(e => {
                    console.error(e);
                    OctaQube.toast("Failed to register webhook", "error");
                });
        },

        deleteWebhook(webhookId) {
            if (!confirm("Are you sure you want to delete this Webhook endpoint?")) return;
            api.delete(`/super-admin/integrations/webhooks/${webhookId}`)
                .then(() => {
                    OctaQube.toast("Webhook deleted successfully", "success");
                    this.init();
                })
                .catch(e => {
                    console.error(e);
                    OctaQube.toast("Failed to delete webhook", "error");
                });
        }
    };

    // Export module globally
    window.IntegrationsModule = IntegrationsModule;

    // Hook playground method select to toggle payload display
    document.addEventListener('change', function(e) {
        if (e.target && e.target.id === 'play_method') {
            const block = document.getElementById('playPayloadBlock');
            if (block) {
                block.style.display = e.target.value === 'POST' ? 'block' : 'none';
            }
        }
    });

})();
