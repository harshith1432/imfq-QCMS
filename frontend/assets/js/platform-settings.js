/**
 * OctaQube Enterprise OS — Platform Settings Manager
 * Handles all Super Admin platform-level settings categories.
 * Integrates with /api/super-admin/settings/* endpoints.
 */

const PlatformSettings = {
    _data: {},          // Live settings data
    _pendingCategory: null, // Last category edited
    _keyModalResolve: null,

    PROVIDER_META: {
        'openai': { name: 'OpenAI', desc: 'Used for GPT-4/GPT-3.5 AI integrations.', url: 'https://platform.openai.com/api-keys', steps: ['Login to OpenAI Platform.', 'Go to API Keys.', 'Create new secret key.'], fields: [{id: 'api_key', label: 'Secret API Key', type: 'password'}] },
        'gemini': { name: 'Google Gemini', desc: 'Used for Google Gemini AI models.', url: 'https://aistudio.google.com/app/apikey', steps: ['Go to Google AI Studio.', 'Click Get API key.', 'Create API key in a new project.'], fields: [{id: 'api_key', label: 'Secret API Key', type: 'password'}] },
        'anthropic': { name: 'Anthropic Claude', desc: 'Used for Claude AI models.', url: 'https://console.anthropic.com/settings/keys', steps: ['Go to Anthropic Console.', 'Navigate to API Keys.', 'Create Key.'], fields: [{id: 'api_key', label: 'Secret API Key', type: 'password'}] },
        'openrouter': { name: 'OpenRouter.ai', desc: 'Unified API for multiple AI models.', url: 'https://openrouter.ai/keys', steps: ['Go to OpenRouter.', 'Navigate to Keys.', 'Create Key.'], fields: [{id: 'api_key', label: 'Secret API Key', type: 'password'}] },
        'deepseek': { name: 'DeepSeek AI', desc: 'Used for DeepSeek models.', url: 'https://platform.deepseek.com/api_keys', steps: ['Login to DeepSeek Platform.', 'Go to API Keys.', 'Create new API key.'], fields: [{id: 'api_key', label: 'Secret API Key', type: 'password'}] },
        'groq': { name: 'Groq', desc: 'Used for fast LPU inference.', url: 'https://console.groq.com/keys', steps: ['Go to Groq Console.', 'Navigate to API Keys.', 'Create Key.'], fields: [{id: 'api_key', label: 'Secret API Key', type: 'password'}] },
        'azure': { name: 'Azure OpenAI', desc: 'Used for Azure OpenAI service.', url: 'https://portal.azure.com/', steps: ['Login to Azure Portal.', 'Go to OpenAI Service.', 'Get Keys and Endpoint.'], fields: [{id: 'subscription_id', label: 'Subscription ID', type: 'text'}, {id: 'tenant_id', label: 'Tenant ID', type: 'text'}] },
        'ollama': { name: 'Ollama', desc: 'Used for local models.', url: 'https://github.com/ollama/ollama', steps: ['Host Ollama locally.', 'No external API key needed.'], fields: [] },
        'twilio': { name: 'Twilio', desc: 'Used for SMS gateways.', url: 'https://console.twilio.com/', steps: ['Login to Twilio.', 'Go to Auth Tokens & API Keys.', 'Create API Key.'], fields: [{id: 'api_key', label: 'Auth Token / Secret', type: 'password'}] },
        'msg91': { name: 'MSG91', desc: 'Used for SMS in India.', url: 'https://msg91.com/help/how-to-generate-the-auth-key', steps: ['Login to MSG91.', 'Go to Auth Keys.', 'Create Key.'], fields: [{id: 'api_key', label: 'Auth Key', type: 'password'}] },
        'textlocal': { name: 'TextLocal', desc: 'Used for Global SMS.', url: 'https://control.textlocal.in/docs/', steps: ['Login to TextLocal.', 'Go to Settings > API Keys.', 'Create Key.'], fields: [{id: 'api_key', label: 'API Key', type: 'password'}] },
        'stripe': { name: 'Stripe', desc: 'Used for Payments.', url: 'https://dashboard.stripe.com/apikeys', steps: ['Login to Stripe.', 'Go to Developers > API keys.', 'Reveal Secret Key.'], fields: [{id: 'public_key', label: 'Publishable Key', type: 'text'}, {id: 'secret_key', label: 'Secret Key', type: 'password'}] },
        'razorpay': { name: 'Razorpay', desc: 'Used for Indian Payments.', url: 'https://dashboard.razorpay.com/app/keys', steps: ['Login to Razorpay.', 'Go to Settings > API Keys.', 'Generate Key.'], fields: [{id: 'key_id', label: 'Key ID', type: 'text'}, {id: 'key_secret', label: 'Key Secret', type: 'password'}] },
        'upi': { name: 'UPI Dynamic QR', desc: 'Used for zero-fee Indian bank transfers.', url: '#', steps: ['Enter your UPI ID / VPA.', 'Optionally enter Merchant Name.', 'Users will scan the generated QR to pay.'], fields: [{id: 'upi_id', label: 'UPI ID / VPA', type: 'text'}, {id: 'merchant_name', label: 'Merchant Name', type: 'text'}] },
        'slack': { name: 'Slack', desc: 'Used for Notifications.', url: 'https://api.slack.com/apps', steps: ['Create Slack App.', 'Add Webhook feature.', 'Copy Webhook URL.'], fields: [{id: 'webhook_url', label: 'Webhook URL', type: 'text'}] },
        'teams': { name: 'MS Teams', desc: 'Used for Notifications.', url: 'https://learn.microsoft.com/en-us/microsoftteams/platform/webhooks-and-connectors/how-to/add-incoming-webhook', steps: ['Go to Teams Channel.', 'Add Incoming Webhook Connector.', 'Copy URL.'], fields: [{id: 'webhook_url', label: 'Webhook URL', type: 'text'}] },
        'zapier': { name: 'Zapier', desc: 'Used for workflow automation.', url: 'https://zapier.com/app/settings/api', steps: ['Login to Zapier.', 'Go to API settings.', 'Generate Key.'], fields: [{id: 'api_key', label: 'API Key', type: 'password'}] },
        'firebase': { name: 'Firebase', desc: 'Used for Cloud functions & Push.', url: 'https://console.firebase.google.com/', steps: ['Go to Firebase Console.', 'Project Settings > Service Accounts.', 'Generate private key.'], fields: [{id: 'service_account_json', label: 'Service Account JSON', type: 'textarea'}] },
        'google_workspace': { name: 'Google Workspace', desc: 'Used for G-Suite Integration.', url: 'https://console.cloud.google.com/apis/credentials', steps: ['Go to Google Cloud Console.', 'Create Service Account.', 'Generate Key.'], fields: [{id: 'service_account_json', label: 'Service Account JSON', type: 'textarea'}] },
        'microsoft_365': { name: 'Microsoft 365', desc: 'Used for Office Integration.', url: 'https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade', steps: ['Go to Azure App Registrations.', 'Create App.', 'Generate Secret.'], fields: [{id: 'client_id', label: 'Client ID', type: 'text'}, {id: 'client_secret', label: 'Client Secret', type: 'password'}, {id: 'tenant_id', label: 'Tenant ID', type: 'text'}] },
        'aws': { name: 'Amazon AWS', desc: 'Used for S3 Storage.', url: 'https://console.aws.amazon.com/iam/home#/security_credentials', steps: ['Go to AWS IAM.', 'Select User.', 'Create Access Key.'], fields: [{id: 'access_key', label: 'Access Key ID', type: 'text'}, {id: 'secret_key', label: 'Secret Access Key', type: 'password'}, {id: 'region', label: 'AWS Region', type: 'text'}] },
        'smtp': { name: 'SMTP Service', desc: 'Used for Email Delivery. Enter your SMTP password or API key from your email provider.', url: 'https://app.sendgrid.com/settings/api_keys', steps: ['Login to your Email Provider (SendGrid, Mailgun, Brevo, etc.).', 'Go to Settings → API Keys.', 'Create a new API Key with Mail Send permission.', 'Copy the key and paste it below.'], fields: [{id: 'api_key', label: 'SMTP Password / API Key', type: 'password'}] }
    },

    // ──────────────────────────────────────────────────────────
    // INIT
    // ──────────────────────────────────────────────────────────

    _activeTab: 'general',

    async init() {
        const user = JSON.parse(sessionStorage.getItem('user') || localStorage.getItem('user') || '{}');
        const role = window.OctaQube && window.OctaQube.normalizeRole ? window.OctaQube.normalizeRole(user.role) : user.role;
        const isSuperAdmin = role === 'SuperAdmin';
        if (!isSuperAdmin) return;

        // Show the Platform Admin nav group
        const navGroup = document.getElementById('platform-admin-group');
        if (navGroup) navGroup.style.display = 'block';

        // Check for tab query parameter in URL
        const params = new URLSearchParams(window.location.search);
        const tabParam = params.get('tab');
        if (tabParam) {
            this.switchTab(tabParam);
        }

        // Load dashboard KPIs + full settings
        await this.loadDashboard();
        await this.loadAllSettings();
        this.bindBrandingListeners();
        this.restoreSavedBranding();

        // Listen for mode switches to synchronize color pickers with active mode palette
        window.addEventListener('octaqube-theme-change', () => {
            this.syncBrandingInputs();
        });

        // Initialize FormManager for transactional editing (Explicit Save/Cancel, NO Auto-Save)
        if (window.FormManager) {
            this._formManager = new window.FormManager({
                container: '#settingsView',
                saveBtn: '#ps-save-btn, #saveChangesBtn',
                cancelBtn: '#ps-cancel-btn, #cancelBtn',
                badge: '#unsavedChangesBadge, .unsaved-badge',
                onSave: async (payload, pendingFiles, editableData) => {
                    await this.saveCurrentTab();
                    return true;
                },
                onCancel: () => {
                    this.loadAllSettings();
                }
            });
            if (window.NavigationGuard) {
                window.NavigationGuard.register(this._formManager);
            }
        }
    },

    // ──────────────────────────────────────────────────────────
    // TAB SWITCHING & EXPORT / IMPORT
    // ──────────────────────────────────────────────────────────

    switchTab(tabId, btn) {
        if (!tabId) return;
        this._activeTab = tabId;

        // Update navigation active state — remove 'active' from all items across all settings nav lists
        document.querySelectorAll('.ps-nav-item, .sidebar-link, #ps-settings-nav .ps-nav-item, #settings-tabs .ps-nav-item, #settings-tabs .sidebar-link').forEach(el => el.classList.remove('active'));
        
        const targetBtn = (btn ? (btn.closest ? (btn.closest('.ps-nav-item, .sidebar-link') || btn) : btn) : null) ||
                          document.querySelector(`#ps-settings-nav .ps-nav-item[data-tab="${tabId}"], .ps-nav-item[data-tab="${tabId}"], #settings-tabs .sidebar-link[data-target="${tabId}"], .sidebar-link[data-tab="${tabId}"]`);
        
        if (targetBtn) {
            targetBtn.classList.add('active');
        }

        // Hide all panes, show active pane
        document.querySelectorAll('.ps-tab-pane').forEach(el => el.classList.remove('active'));
        const pane = document.getElementById(`ps-pane-${tabId}`);
        if (pane) {
            pane.classList.add('active');
            const contentCard = document.querySelector('.ps-content-card');
            if (contentCard) contentCard.scrollTop = 0;
        }

        // Update URL parameter without reload
        try {
            const newUrl = `${window.location.pathname}?view=settings&tab=${tabId}`;
            window.history.replaceState({ path: newUrl }, '', newUrl);
        } catch (e) {}

        try {
            if (window.lucide && typeof window.lucide.createIcons === 'function') {
                window.lucide.createIcons();
            }
        } catch (e) {}

        // Load live KPIs when entering specific settings panes
        if (tabId === 'security') {
            setTimeout(() => this.loadSecurityKPIs(), 100);
        } else if (tabId === 'auth') {
            setTimeout(() => this.loadAuthKPIs(), 100);
        } else if (tabId === 'admin-logins') {
            setTimeout(() => this.loadAdminLogins(), 100);
        } else if (tabId === 'system-health') {
            setTimeout(() => this.loadSystemHealth(), 100);
        }
    },

    async saveCurrentTab() {
        if (window.SuperAdmin && SuperAdmin.saSubRole && SuperAdmin.saSubRole !== 'Owner' && SuperAdmin.saSubRole !== 'Platform Operations') {
            if (window.OctaQube && OctaQube.toast) {
                OctaQube.toast(`Your sub-role '${SuperAdmin.saSubRole}' does not have permission to modify platform settings.`, 'warning');
            }
            return;
        }

        switch (this._activeTab) {
            case 'general': await this.saveGeneral(); break;
            case 'branding': await this.saveBranding(); break;
            case 'auth': await this.saveAuth(); break;
            case 'organizations': await this.saveOrganizations(); break;
            case 'billing': await this.saveBilling(); break;
            case 'modules': await this.saveModules(); break;
            case 'security': await this.saveSecurity(); break;
            case 'compliance': await this.saveCompliance(); break;
            case 'notifications': await this.saveNotifications(); break;
            case 'email': await this.saveEmail(); break;
            case 'sms': await this.saveSMS(); break;
            case 'ai': await this.saveAI(); break;
            case 'integrations': await this.saveIntegrations(); break;
            case 'storage': await this.saveStorage(); break;
            case 'backup': await this.saveBackup(); break;
            case 'api': await this.saveApiSettings(); break;
            case 'feature-flags': await this.saveFeatureFlags(); break;
            case 'developer': await this.saveDeveloper(); break;
            case 'audit-logs': await this.saveAuditLogs(); break;
            case 'system-health': await this.saveSystemHealth(); break;
            case 'about': await this.saveAbout(); break;
            case 'landing-cms': await this.saveLandingCMS(); break;
            default:
                OctaQube.toast(`Configuration for "${this._activeTab}" saved successfully.`, 'success');
                break;
        }
    },

    exportSettingsJSON() {
        try {
            const jsonStr = JSON.stringify(this._data || {}, null, 2);
            const blob = new Blob([jsonStr], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `octaqube_system_config_${new Date().toISOString().slice(0, 10)}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            OctaQube.toast('System configuration exported to JSON file.', 'success');
        } catch (e) {
            OctaQube.toast('Export failed.', 'error');
        }
    },

    importSettingsJSON() {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = 'application/json';
        input.onchange = async (e) => {
            const file = e.target.files[0];
            if (!file) return;
            try {
                const text = await file.text();
                const json = JSON.parse(text);
                await this._put('/settings', json);
                OctaQube.toast('Settings imported and updated!', 'success');
                await this.loadAllSettings();
            } catch (err) {
                OctaQube.toast('Invalid JSON settings file.', 'error');
            }
        };
        input.click();
    },

    // ──────────────────────────────────────────────────────────
    // API HELPERS
    // ──────────────────────────────────────────────────────────

    async _get(path) {
        return await api.get(`/super-admin${path}`);
    },

    async _put(path, body) {
        return await api.put(`/super-admin${path}`, body);
    },

    async _post(path, body) {
        return await api.post(`/super-admin${path}`, body);
    },

    async _delete(path) {
        return await api.delete(`/super-admin${path}`);
    },

    // ──────────────────────────────────────────────────────────
    // DASHBOARD
    // ──────────────────────────────────────────────────────────

    async loadDashboard() {
        try {
            const res = await this._get('/settings/dashboard');
            const d = res.data;
            const k = d.kpis;
            const ai = d.ai_insights;

            // KPI cards (from settings dashboard)
            this._setInner('ps-version', k.platform_version);
            this._setInner('ps-integrations', `${k.active_integrations} / ${k.total_integrations} Active`);
            this._setInner('ps-auth-providers', k.active_auth_providers);
            this._setInner('ps-notif-channels', k.active_notification_channels);
            this._setInner('ps-backup-jobs', k.active_backup_jobs);
            this._setInner('ps-security-score', `${k.security_score} / 100`);
            this._setInner('ps-retention-days', `${k.audit_retention_days} days`);

            // Fetch and set Global KPI stats
            try {
                const statsRes = await this._get('/stats');
                const s = statsRes.data;
                this._setInner('ps-kpi-orgs', s.total_companies.toLocaleString());
                this._setInner('ps-kpi-users', s.total_users.toLocaleString());
                this._setInner('ps-kpi-mrr', '₹' + (s.total_revenue > 100000 ? (s.total_revenue / 100000).toFixed(1) + 'L' : s.total_revenue.toLocaleString()));
                this._setInner('ps-kpi-storage', s.storage_used_gb >= 1024 ? (s.storage_used_gb / 1024).toFixed(1) + ' TB' : s.storage_used_gb + ' GB');
                this._setInner('ps-kpi-uptime', s.platform_uptime);
                this._setInner('ps-kpi-api-health', s.api_health_ms + 'ms');
                this._setInner('ps-kpi-tickets', s.open_tickets.toLocaleString());

                // Organization Governance KPI Cards
                this._setInner('ps-org-kpi-total', (s.total_companies || 0).toLocaleString());
                this._setInner('ps-org-kpi-pending', (s.pending_companies || 0).toLocaleString());
                this._setInner('ps-org-kpi-active', (s.active_companies || 0).toLocaleString());
                this._setInner('ps-org-kpi-suspended', (s.suspended_companies || 0).toLocaleString());
            } catch (e) { console.error('Failed to load global stats', e); }

            // Storage donut
            const storageUsedEl = document.getElementById('ps-storage-used');
            const storagePctEl = document.getElementById('ps-storage-pct');
            if (storageUsedEl) storageUsedEl.innerText = `${k.storage_used_gb} GB / ${k.storage_total_gb} GB`;
            if (storagePctEl) {
                storagePctEl.style.width = `${k.storage_percent}%`;
                storagePctEl.classList.toggle('bg-danger', k.storage_percent > 85);
                storagePctEl.classList.toggle('bg-warning', k.storage_percent > 70 && k.storage_percent <= 85);
            }

            // Security score ring
            const scoreRing = document.getElementById('ps-score-ring');
            if (scoreRing) {
                const pct = k.security_score;
                const color = pct >= 80 ? '#22c55e' : pct >= 60 ? '#f59e0b' : '#ef4444';
                scoreRing.style.background = `conic-gradient(${color} ${pct * 3.6}deg, var(--ds-surface-raised) 0deg)`;
            }

            // AI Insights
            const secList = document.getElementById('ps-security-improvements');
            if (secList && ai.recommended_security_improvements) {
                secList.innerHTML = ai.recommended_security_improvements.slice(0, 5).map(item =>
                    `<li class="py-1 border-bottom last:border-0"><i data-lucide="alert-triangle" class="text-warning me-2" style="width:14px;"></i>${item}</li>`
                ).join('') || '<li class="text-muted py-2">No issues found — great work!</li>';
            }

            const perfList = document.getElementById('ps-perf-improvements');
            if (perfList && ai.recommended_performance_improvements) {
                perfList.innerHTML = ai.recommended_performance_improvements.slice(0, 5).map(item =>
                    `<li class="py-1 border-bottom"><i data-lucide="info" class="text-info me-2" style="width:14px;"></i>${item}</li>`
                ).join('') || '<li class="text-muted py-2">No performance issues detected.</li>';
            }

            this._setInner('ps-backup-health', ai.backup_health);
            this._setInner('ps-storage-forecast', ai.storage_forecast);
            this._setInner('ps-config-health', `${ai.config_health_score}%`);

            if (window.lucide) lucide.createIcons();
        } catch (e) {
            console.error('Failed to load settings dashboard', e);
        }
    },

    // ──────────────────────────────────────────────────────────
    // LOAD ALL SETTINGS
    // ──────────────────────────────────────────────────────────

    async loadAllSettings() {
        try {
            const res = await this._get('/settings');
            const d = res.data;
            this._data = d;

            // General
            this._val('ps-site-name', d.site_name);
            this._val('ps-support-email', d.support_email);
            this._val('ps-support-phone', d.support_phone);
            this._val('ps-support-website', d.support_website);
            this._val('ps-company-address', d.company_address);
            this._val('ps-timezone', d.timezone);
            this._val('ps-default-language', d.default_language);
            this._val('ps-date-format', d.date_format);
            this._val('ps-time-format', d.time_format);
            this._val('ps-currency', d.currency);
            this._val('ps-default-plan', d.default_plan);
            this._val('ps-trial-days', d.trial_period_days);
            this._val('ps-default-trial-days', d.trial_period_days || 14);
            this._val('ps-max-auto-trial-extensions', d.max_auto_trial_extensions !== undefined ? d.max_auto_trial_extensions : 2);
            this._chk('ps-registration-open', d.registration_open);
            this._chk('ps-require-email-otp', d.require_email_otp !== false);
            this._chk('ps-require-phone-otp', !!d.require_phone_otp);
            this._val('ps-global-notification', d.global_notification);

            // Branding (Dual-Mode Theme Management)
            this._initBrandingData(d.branding_settings || {});
            this.syncBrandingInputs();

            // Email
            const email = d.email_settings || {};
            this._val('ps-smtp-provider', email.smtp_provider);
            this._val('ps-smtp-host', email.smtp_host);
            this._val('ps-smtp-port', email.smtp_port);
            this._val('ps-smtp-username', email.smtp_username);
            this._val('ps-smtp-encryption', email.smtp_encryption);
            this._val('ps-from-name', email.from_name);
            this._val('ps-from-email', email.from_email);
            // smtp_password shown as placeholder (••••••••) if set

            // Authentication
            const auth = d.authentication_settings || {};
            this._val('ps-jwt-expiry', auth.jwt_expiry_hours);
            this._chk('ps-email-auth', auth.native_email_enabled !== false);
            this._chk('ps-google-oauth', auth.oauth_google_enabled);
            this._val('ps-google-client-id', auth.oauth_google_client_id);
            this._chk('ps-microsoft-oauth', auth.oauth_microsoft_enabled);
            this._val('ps-microsoft-client-id', auth.oauth_microsoft_client_id);
            this._chk('ps-github-oauth', auth.oauth_github_enabled);
            this._val('ps-github-client-id', auth.oauth_github_client_id);
            this._chk('ps-ldap-enabled', auth.ldap_enabled);
            this._val('ps-ldap-server', auth.ldap_server);
            this._chk('ps-saml-auth', auth.saml_enabled);
            this._val('ps-saml-url', auth.saml_metadata_url);
            this._chk('ps-azure-ad', auth.azure_ad_enabled);
            this._chk('ps-mfa-enabled', auth.mfa_enabled);
            this._val('ps-session-timeout', auth.session_timeout_minutes);
            this._val('ps-max-login-attempts', auth.max_login_attempts);
            this._val('ps-pw-expiry-days', auth.password_expiry_days);
            this.loadAuthKPIs();

            // Security
            const sec = d.security_settings || {};
            this._val('ps-pw-min-length', sec.password_min_length);
            this._chk('ps-pw-uppercase', sec.password_uppercase);
            this._chk('ps-pw-lowercase', sec.password_lowercase);
            this._chk('ps-pw-numbers', sec.password_numbers);
            this._chk('ps-pw-special', sec.password_special);
            this._val('ps-pw-history', sec.password_history_limit);
            this._val('ps-lockout-duration', sec.lockout_duration_mins);
            this._chk('ps-brute-force', sec.brute_force_protection);
            this._val('ps-ip-whitelist', sec.ip_whitelist);
            this._val('ps-ip-blacklist', sec.ip_blacklist);
            this._val('ps-allowed-domains', sec.allowed_domains);
            this._val('ps-api-rate-limit', sec.api_rate_limit_per_minute);
            // New security fields
            this._sel('ps-waf-mode', sec.waf_mode);
            this._sel('ps-download-restriction', sec.download_restriction);
            this._chk('ps-db-encryption', sec.db_encryption_enabled);

            // Notifications
            const notif = d.notification_settings || {};
            this._chk('ps-notif-email', notif.email_notifications);
            this._chk('ps-notif-sms', notif.sms_notifications);
            this._chk('ps-notif-push', notif.push_notifications);
            this._chk('ps-notif-inapp', notif.in_app_notifications);
            this._chk('ps-notif-slack', notif.slack_enabled);
            this._val('ps-notif-slack-url', notif.slack_webhook_url);
            this._chk('ps-notif-teams', notif.teams_enabled);
            this._val('ps-notif-teams-url', notif.teams_webhook_url);
            this._val('ps-notif-summary', notif.summary_preference);

            // Storage
            const storage = d.storage_settings || {};
            this._val('ps-storage-provider', storage.storage_provider || 'local');
            this._val('ps-s3-bucket', storage.s3_bucket || '');
            this._val('ps-max-upload-mb', storage.max_upload_limit_mb || 100);
            this._val('ps-storage-alert-pct', storage.storage_alerts_percent || 80);
            this.toggleStorageProviderGuide(storage.storage_provider || 'local');

            // Compute KPI values
            const totalGB = parseFloat(storage.total_capacity_gb || 1000.0);
            const usedGB = parseFloat(storage.storage_used_gb || 0.0);
            const remainingGB = Math.max(0, totalGB - usedGB);
            const usedPct = totalGB > 0 ? ((usedGB / totalGB) * 100).toFixed(2) : 0;

            const providerLabel = {
                's3': 'AWS S3',
                'azure': 'Azure Blob',
                'gcs': 'Google Cloud',
                'local': 'Local Volume'
            }[storage.storage_provider || 'local'] || 'Local Volume';

            const targetDisplay = storage.storage_provider === 's3' && storage.s3_bucket 
                ? `AWS S3 (${storage.s3_bucket})` 
                : providerLabel;

            const totalEl = document.getElementById('ps-storage-total-display');
            const usedEl = document.getElementById('ps-storage-used-display');
            const remainingEl = document.getElementById('ps-storage-remaining-display');
            const targetEl = document.getElementById('ps-storage-target-display');

            if (totalEl) totalEl.textContent = `${totalGB.toLocaleString()} GB`;
            if (usedEl) usedEl.textContent = `${usedGB.toFixed(4)} GB (${usedPct}%)`;
            if (remainingEl) remainingEl.textContent = `${remainingGB.toFixed(4)} GB Free`;
            if (targetEl) targetEl.textContent = targetDisplay;

            // Backup
            const backup = d.backup_settings || {};
            this._chk('ps-backup-auto', backup.auto_backup_enabled);
            this._val('ps-backup-schedule', backup.backup_schedule);
            this._val('ps-backup-dest', backup.backup_destination);
            this._val('ps-backup-s3-bucket', backup.s3_bucket);
            this._val('ps-backup-s3-region', backup.s3_region);
            this._val('ps-backup-s3-key', backup.s3_access_key);
            this.toggleBackupDestInputs(backup.backup_destination || 'local');
            this.loadBackupHistory(backup.backup_history || []);

            // Compliance
            const comp = d.compliance_settings || {};
            this._val('ps-retention-period', comp.retention_period_days);
            this._chk('ps-log-encryption', comp.log_encryption_enabled);
            this._chk('ps-gdpr', comp.gdpr_enabled);
            this._chk('ps-soc2', comp.soc2_enabled);
            this._chk('ps-iso27001', comp.iso27001_enabled);
            this._chk('ps-legal-hold', comp.legal_hold_enabled);

            // API Settings
            const apiS = d.api_settings || {};
            this._val('ps-api-rate-limit-cfg', apiS.api_rate_limit);
            this._val('ps-api-token-expiry', apiS.api_token_expiry_hours);
            this._chk('ps-api-monitoring', apiS.api_monitoring_enabled);
            this.loadApiKeys(apiS.api_keys_active || []);

            // Webhooks
            const webh = d.webhook_settings || {};
            this._val('ps-webhook-retry', webh.default_retry_attempts);
            this._val('ps-webhook-timeout', webh.timeout_seconds);
            this.loadWebhookConfigs(webh.webhook_configs || []);

            // AI Settings
            const aiS = d.ai_settings || {};
            this._val('ps-ai-provider', aiS.ai_provider || 'openrouter');
            this.onAIProviderChange();
            if (aiS.api_key) this._val('ps-ai-api-key', aiS.api_key);
            this._val('ps-ai-model', aiS.default_model || 'openai/gpt-4o');
            this._val('ps-ai-temperature', aiS.temperature || 0.4);
            this._val('ps-ai-max-tokens', aiS.max_tokens || 2048);
            this._val('ps-ai-usage-limit', aiS.ai_usage_limit_usd || 100);
            this._val('ps-ai-openrouter-site', aiS.openrouter_site_url || 'https://imfq.io');
            this._val('ps-ai-openrouter-app', aiS.openrouter_app_name || 'OctaQube Enterprise OS');
            this._val('ps-ai-fallbacks', aiS.model_fallbacks || 'anthropic/claude-3.5-sonnet, google/gemini-2.0-flash-001, deepseek/deepseek-r1');
            this._chk('ps-ai-logging', aiS.ai_logging !== false);

            // Feature Flags
            this.renderFeatureFlags(d.feature_flags || {});

            // Maintenance
            const maint = d.maintenance_settings || {};
            this._chk('ps-maintenance-mode', d.maintenance_mode);
            this._val('ps-maintenance-msg', maint.maintenance_message);
            this._val('ps-maintenance-eta', maint.estimated_completion);

            // System Info
            const sysS = d.system_settings || {};
            this._setInner('ps-sys-platform-ver', sysS.platform_version || d.system_version || 'N/A');
            this._setInner('ps-sys-framework', sysS.framework_version || 'N/A');
            this._setInner('ps-sys-db', sysS.db_version || 'N/A');
            this._setInner('ps-sys-server', sysS.server_version || 'N/A');
            this._setInner('ps-sys-cache', sysS.cache_provider || 'N/A');
            this._setInner('ps-sys-queue', sysS.queue_provider || 'N/A');

            // Integrations
            this.renderIntegrations(d.integrations_settings || {});

            // Landing CMS
            this.loadLandingCMS(d.landing_cms_settings || {});

            if (window.lucide) lucide.createIcons();
        } catch (e) {
            console.error('Failed to load platform settings', e);
        }
    },

    loadLandingCMS(lCms = {}) {
        this.currentLandingCMS = lCms;
        
        // Enable / Disable Landing Page
        const isLandingEnabled = lCms.enable_landing_page !== false;
        const toggleEl = document.getElementById('ps-cms-enable-landing');
        if (toggleEl) {
            toggleEl.checked = isLandingEnabled;
            this.toggleLandingPageStatus(isLandingEnabled, true);
        }

        // Hero
        this._val('ps-cms-hero-badge', lCms.hero_badge || 'Version 3.0 Now Live');
        this._val('ps-cms-hero-title', lCms.hero_title || 'Precision Quality <br><span class="text-primary">Management</span> at Scale.');
        this._val('ps-cms-hero-subtitle', lCms.hero_subtitle || 'Optimize your organizational efficiency with our structured 8-stage workflow engine. Built for enterprise excellence, designed for modern teams.');
        this._val('ps-cms-cta-primary', lCms.cta_primary_text || 'Start Free Trial');
        this._val('ps-cms-cta-primary-url', lCms.cta_primary_url || '/auth/register-org.html');
        this._val('ps-cms-cta-secondary', lCms.cta_secondary_text || 'Watch Demo');
        this._val('ps-cms-cta-secondary-url', lCms.cta_secondary_url || '#features');
        this._val('ps-cms-hero-stat1-val', lCms.hero_stat_1_val || '98.2%');
        this._val('ps-cms-hero-stat1-lbl', lCms.hero_stat_1_lbl || 'Quality Score');
        this._val('ps-cms-hero-stat2-val', lCms.hero_stat_2_val || 'A+');
        this._val('ps-cms-hero-stat2-lbl', lCms.hero_stat_2_lbl || 'Active Nodes');
        this._val('ps-cms-hero-stat3-val', lCms.hero_stat_3_val || '1,204');
        this._val('ps-cms-hero-stat3-lbl', lCms.hero_stat_3_lbl || '+12 this hour');
        this._val('ps-cms-hero-feature1', lCms.hero_feature_1 || 'Enterprise Secure');
        this._val('ps-cms-hero-feature2', lCms.hero_feature_2 || 'Global Scale');
        this._val('ps-cms-hero-feature3', lCms.hero_feature_3 || 'High Precision');

        // Trust Ticker
        this._val('ps-cms-ticker-1', lCms.ticker_1 || '99.9% Uptime');
        this._val('ps-cms-ticker-2', lCms.ticker_2 || 'ISO 9001 Ready');
        this._val('ps-cms-ticker-3', lCms.ticker_3 || 'Enterprise Grade');
        this._val('ps-cms-ticker-4', lCms.ticker_4 || 'Audit Secure');
        this._val('ps-cms-ticker-5', lCms.ticker_5 || '24/7 Support');

        // Trust Badges
        this._val('ps-cms-badge-1-icon',  lCms.badge_1_icon  || 'award');
        this._val('ps-cms-badge-1-label', lCms.badge_1_label || 'ISO 9001 Compliant');
        this._val('ps-cms-badge-2-icon',  lCms.badge_2_icon  || 'shield-check');
        this._val('ps-cms-badge-2-label', lCms.badge_2_label || 'Bank-Grade Security');
        this._val('ps-cms-badge-3-icon',  lCms.badge_3_icon  || 'clock');
        this._val('ps-cms-badge-3-label', lCms.badge_3_label || '99.9% Platform Uptime');
        this._val('ps-cms-badge-4-icon',  lCms.badge_4_icon  || 'headset');
        this._val('ps-cms-badge-4-label', lCms.badge_4_label || '24/7 Priority Support');

        // Features
        this._val('ps-cms-features-title', lCms.features_title || 'Engineered for Quality');
        this._val('ps-cms-features-subtitle', lCms.features_subtitle || 'Every tool you need to maintain the highest standards across your industrial operations.');
        const defaultFeatures = [
            { icon: 'git-branch', title: '8-Stage Workflow', desc: 'Structured project lifecycle from problem identification to standardization.' },
            { icon: 'layers', title: 'Role-Based Dashboards', desc: 'Custom workspaces for Admins, Reviewers, Facilitators, and Team members.' },
            { icon: 'database', title: 'Knowledge Repo', desc: 'Centralized repository for SOPs, lessons learned, and project history.' },
            { icon: 'bar-chart-3', title: 'Real-time Analytics', desc: 'Live KPI tracking with automated reporting and visual data insights.' },
            { icon: 'shield-check', title: 'Automated Compliance', desc: 'Stay ISO ready with automated audit logs and version-controlled documents.' },
            { icon: 'smartphone', title: 'Mobile Readiness', desc: 'Access your quality management engine from anywhere, on any device.' }
        ];
        this.renderFeatures((lCms.features_list && lCms.features_list.length) ? lCms.features_list : defaultFeatures);

        // Steps
        this._val('ps-cms-steps-badge', lCms.steps_badge || 'Onboarding Flow');
        this._val('ps-cms-steps-title', lCms.steps_title || 'How It Works');
        this._val('ps-cms-steps-subtitle', lCms.steps_subtitle || 'Deploy your enterprise-grade QMS in four simple steps.');
        const defaultSteps = [
            { num: '1', title: 'Register Company', desc: 'Set up your unique organizational instance and security parameters.' },
            { num: '2', title: 'Setup Team', desc: 'Configure departments and assign role-based access to your workforce.' },
            { num: '3', title: 'Launch Projects', desc: 'Initiate quality improvement projects using our 8-stage engine.' },
            { num: '4', title: 'Track KPI', desc: 'Monitor real-time improvements in efficiency, cost, and safety.' }
        ];
        this.renderSteps((lCms.steps_list && lCms.steps_list.length) ? lCms.steps_list : defaultSteps);

        // Pricing Plans
        this._val('ps-cms-pricing-badge', lCms.pricing_badge || 'Simple Pricing');
        this._val('ps-cms-pricing-title', lCms.pricing_title || 'Flexible Plans for Every Stage');
        this._val('ps-cms-pricing-subtitle', lCms.pricing_subtitle || 'Scale your quality operations without complexity.');
        const defaultPricing = [
            { name: 'Starter', badge: '', price: '₹0', period: '/month (14d Trial)', desc: 'For small focused teams', features: ['50 Users Max', 'Basic QC Workflow', 'Limited Reports', '14 Days Free Trial'], cta: 'Start Free Trial', cta_url: '/auth/register-org.html?plan=Starter' },
            { name: 'Professional', badge: 'MOST POPULAR', price: '₹199', period: '/month', desc: 'Complete enterprise engine', features: ['500 Users', 'Full Workflow Engine', 'Analytics Dashboard', 'Repository + AI Assistant', 'Reports + Audit Logs'], cta: 'Start Free Trial', cta_url: '/auth/register-org.html?plan=Professional' },
            { name: 'Enterprise', badge: '', price: 'Custom', period: '', desc: 'For global scale manufacturing', features: ['Unlimited Users', 'Multi Plant Support', 'White Label Branding', 'API Integration', 'Dedicated Support'], cta: 'Contact Sales', cta_url: 'openTalkToSalesModal()' }
        ];
        this.renderPricingPlans((lCms.pricing_plans && lCms.pricing_plans.length) ? lCms.pricing_plans : defaultPricing);

        // FAQs
        this._val('ps-cms-faq-title', lCms.faq_title || 'Frequently Asked Questions');
        this._val('ps-cms-faq-subtitle', lCms.faq_subtitle || 'Everything you need to know about OctaQube Enterprise.');
        const defaultFaqs = [
            { q: 'How does the 14-day free trial work?', a: 'You get full access to all Enterprise features for 14 days. No credit card required.' },
            { q: 'Can we upgrade plans later?', a: 'Yes, you can upgrade your plan at any time from the billing dashboard.' },
            { q: 'Do you support multiple factories?', a: 'Absolutely. OctaQube is built for multi-site enterprise deployments.' },
            { q: 'Is white label branding available?', a: 'Yes, on the Enterprise tier you can fully customize logos, colors, and domains.' },
            { q: 'Can we integrate with ERP/SAP?', a: 'Yes, we offer two-way sync with SAP S/4HANA, Oracle, and Microsoft Dynamics.' }
        ];
        this.renderFAQs((lCms.faqs && lCms.faqs.length) ? lCms.faqs : defaultFaqs);

        // CTA Offer Banner
        this._val('ps-cms-cta-banner-badge', lCms.cta_banner_badge || 'Limited Time Offer');
        this._val('ps-cms-cta-banner-title', lCms.cta_banner_title || 'Start Your 14-Day Free Trial');
        this._val('ps-cms-cta-banner-subtitle', lCms.cta_banner_subtitle || 'No Credit Card Required. Get instant access to admin dashboard, workflow engine, and analytics.');
        this._val('ps-cms-cta-feature-1', lCms.cta_feature_1 || 'Instant Setup');
        this._val('ps-cms-cta-feature-2', lCms.cta_feature_2 || 'Full Workflow');
        this._val('ps-cms-cta-feature-3', lCms.cta_feature_3 || 'AI Assistant');
        this._val('ps-cms-cta-banner-btn1', lCms.cta_banner_btn1 || 'Launch Your Instance');
        this._val('ps-cms-cta-banner-btn1-url', lCms.cta_banner_btn1_url || '/auth/register-org.html');
        this._val('ps-cms-cta-banner-btn2', lCms.cta_banner_btn2 || 'Talk to Sales');
        this._val('ps-cms-cta-banner-btn2-url', lCms.cta_banner_btn2_url || 'openTalkToSalesModal()');

        // Footer
        this._val('ps-cms-footer-desc', lCms.footer_description || "The world's most advanced quality management system for modern manufacturing and enterprise excellence. Built for scale, security, and precision.");
        this._val('ps-cms-footer-copy', lCms.footer_copyright || '© 2026 OctaQube Precision Core. Engineered for Excellence.');
        this._val('ps-cms-footer-lang', lCms.footer_lang || 'English (US)');
        this._val('ps-cms-footer-status', lCms.footer_status || 'Operational');

        this.loadFooterPages(lCms.footer_pages);

        if (window.lucide) lucide.createIcons();
    },

    toggleCMSView(mode) {
        const editor = document.getElementById('ps-cms-editor-panel');
        const preview = document.getElementById('ps-cms-preview-panel');
        const tabEdit = document.getElementById('ps-cms-tab-editor');
        const tabPrev = document.getElementById('ps-cms-tab-preview');
        if (mode === 'preview') {
            if (editor) editor.style.display = 'none';
            if (preview) preview.style.display = 'block';
            if (tabEdit) tabEdit.className = 'btn btn-sm text-sm fw-bold border-0 px-3 py-2 text-muted';
            if (tabPrev) tabPrev.className = 'btn btn-sm text-sm fw-bold border-0 border-bottom border-primary border-2 px-3 py-2 text-primary';
            const iframe = document.getElementById('ps-cms-iframe');
            if (iframe) iframe.src = '/index.html?t=' + Date.now();
        } else {
            if (editor) editor.style.display = 'block';
            if (preview) preview.style.display = 'none';
            if (tabEdit) tabEdit.className = 'btn btn-sm text-sm fw-bold border-0 border-bottom border-primary border-2 px-3 py-2 text-primary';
            if (tabPrev) tabPrev.className = 'btn btn-sm text-sm fw-bold border-0 px-3 py-2 text-muted';
        }
    },

    async resetLandingCMSDefaults() {
        if (!confirm('Are you sure you want to reset all landing page content to the system default template? All custom modifications will be replaced with system defaults.')) return;
        
        // 1. Populate all inputs with system defaults
        this.loadLandingCMS({});
        
        // 2. Automatically save & publish the default template to the backend
        try {
            await this.saveLandingCMS();
            if (window.OctaQube) OctaQube.toast('Landing page successfully reset to default system template and published!', 'success');
        } catch (err) {
            console.error('Error saving default landing CMS:', err);
            if (window.OctaQube) OctaQube.toast('Reset to default values in form. Click "Publish Landing Page" to save.', 'info');
        }
    },

    renderFeatures(features) {
        const container = document.getElementById('ps-features-container');
        if (!container) return;
        container.innerHTML = '';
        features.forEach((f, i) => {
            const div = document.createElement('div');
            div.className = 'd-flex gap-2 align-items-center p-2.5 rounded-3 border feature-item';
            div.style.background = 'var(--ds-bg-card)';
            div.style.borderColor = 'var(--ds-border-color)';
            div.innerHTML = `
                <div class="row g-2 flex-grow-1">
                    <div class="col-md-3">
                        <input type="text" class="form-control form-control-sm feat-icon" placeholder="Lucide Icon" value="${f.icon || 'star'}">
                    </div>
                    <div class="col-md-4">
                        <input type="text" class="form-control form-control-sm feat-title" placeholder="Feature Title" value="${(f.title||'').replace(/"/g, '&quot;')}">
                    </div>
                    <div class="col-md-5">
                        <input type="text" class="form-control form-control-sm feat-desc" placeholder="Feature Description" value="${(f.desc||'').replace(/"/g, '&quot;')}">
                    </div>
                </div>
                <button type="button" class="ds-btn ds-btn-outline ds-btn-sm text-danger" onclick="this.parentElement.remove()">
                    <i data-lucide="trash-2"></i>
                </button>
            `;
            container.appendChild(div);
        });
        if (window.lucide) lucide.createIcons();
    },

    addFeatureCard() {
        const items = Array.from(document.querySelectorAll('.feature-item')).map(el => ({
            icon: el.querySelector('.feat-icon').value,
            title: el.querySelector('.feat-title').value,
            desc: el.querySelector('.feat-desc').value
        }));
        items.push({ icon: 'star', title: 'New Capability', desc: 'Description of the new feature capability.' });
        this.renderFeatures(items);
    },

    renderSteps(steps) {
        const container = document.getElementById('ps-steps-container');
        if (!container) return;
        container.innerHTML = '';
        steps.forEach((s, i) => {
            const div = document.createElement('div');
            div.className = 'd-flex gap-2 align-items-center p-2.5 rounded-3 border step-item';
            div.style.background = 'var(--ds-bg-card)';
            div.style.borderColor = 'var(--ds-border-color)';
            div.innerHTML = `
                <div class="row g-2 flex-grow-1">
                    <div class="col-md-2">
                        <input type="text" class="form-control form-control-sm step-num" placeholder="Step #" value="${s.num || (i+1)}">
                    </div>
                    <div class="col-md-4">
                        <input type="text" class="form-control form-control-sm step-title" placeholder="Step Title" value="${(s.title||'').replace(/"/g, '&quot;')}">
                    </div>
                    <div class="col-md-6">
                        <input type="text" class="form-control form-control-sm step-desc" placeholder="Step Description" value="${(s.desc||'').replace(/"/g, '&quot;')}">
                    </div>
                </div>
                <button type="button" class="ds-btn ds-btn-outline ds-btn-sm text-danger" onclick="this.parentElement.remove()">
                    <i data-lucide="trash-2"></i>
                </button>
            `;
            container.appendChild(div);
        });
        if (window.lucide) lucide.createIcons();
    },

    addStepCard() {
        const items = Array.from(document.querySelectorAll('.step-item')).map((el, i) => ({
            num: el.querySelector('.step-num').value,
            title: el.querySelector('.step-title').value,
            desc: el.querySelector('.step-desc').value
        }));
        items.push({ num: (items.length + 1).toString(), title: 'New Step', desc: 'Step instructions and details.' });
        this.renderSteps(items);
    },

    renderPricingPlans(plans) {
        const container = document.getElementById('ps-pricing-container');
        if (!container) return;
        container.innerHTML = '';
        plans.forEach((p, i) => {
            const div = document.createElement('div');
            div.className = 'p-3 rounded-3 border pricing-item mb-2';
            div.style.background = 'var(--ds-bg-card)';
            div.style.borderColor = 'var(--ds-border-color)';
            div.innerHTML = `
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <span class="fw-bold text-sm">Plan #${i+1}: ${(p.name||'').replace(/"/g, '&quot;')}</span>
                    <button type="button" class="ds-btn ds-btn-outline ds-btn-sm text-danger" onclick="this.closest('.pricing-item').remove()">
                        <i data-lucide="trash-2"></i> Delete Plan
                    </button>
                </div>
                <div class="row g-2 mb-2">
                    <div class="col-md-3">
                        <label class="form-label text-xxs uppercase">Plan Name</label>
                        <input type="text" class="form-control form-control-sm plan-name" value="${(p.name||'').replace(/"/g, '&quot;')}">
                    </div>
                    <div class="col-md-3">
                        <label class="form-label text-xxs uppercase">Badge Text</label>
                        <input type="text" class="form-control form-control-sm plan-badge" value="${(p.badge||'').replace(/"/g, '&quot;')}" placeholder="e.g. MOST POPULAR">
                    </div>
                    <div class="col-md-3">
                        <label class="form-label text-xxs uppercase">Price</label>
                        <input type="text" class="form-control form-control-sm plan-price" value="${(p.price||'').replace(/"/g, '&quot;')}" placeholder="e.g. ₹199">
                    </div>
                    <div class="col-md-3">
                        <label class="form-label text-xxs uppercase">Billing Period</label>
                        <input type="text" class="form-control form-control-sm plan-period" value="${(p.period||'').replace(/"/g, '&quot;')}" placeholder="e.g. /month">
                    </div>
                    <div class="col-md-6">
                        <label class="form-label text-xxs uppercase">Plan Description</label>
                        <input type="text" class="form-control form-control-sm plan-desc" value="${(p.desc||'').replace(/"/g, '&quot;')}">
                    </div>
                    <div class="col-md-3">
                        <label class="form-label text-xxs uppercase">CTA Button Text</label>
                        <input type="text" class="form-control form-control-sm plan-cta" value="${(p.cta||'').replace(/"/g, '&quot;')}" placeholder="Start Free Trial">
                    </div>
                    <div class="col-md-3">
                        <label class="form-label text-xxs uppercase">CTA Link / Action</label>
                        <input type="text" class="form-control form-control-sm plan-cta-url" value="${(p.cta_url||'').replace(/"/g, '&quot;')}" placeholder="e.g. register-org.html?plan=Starter or openTalkToSalesModal()">
                    </div>
                    <div class="col-md-12">
                        <label class="form-label text-xxs uppercase">Features (Comma separated)</label>
                        <input type="text" class="form-control form-control-sm plan-features" value="${Array.isArray(p.features) ? p.features.join(', ') : (p.features||'')}">
                    </div>
                </div>
            `;
            container.appendChild(div);
        });
        if (window.lucide) lucide.createIcons();
    },

    addPricingPlan() {
        const plans = Array.from(document.querySelectorAll('.pricing-item')).map(el => ({
            name: el.querySelector('.plan-name').value,
            badge: el.querySelector('.plan-badge').value,
            price: el.querySelector('.plan-price').value,
            period: el.querySelector('.plan-period').value,
            desc: el.querySelector('.plan-desc').value,
            cta: el.querySelector('.plan-cta').value,
            cta_url: el.querySelector('.plan-cta-url') ? el.querySelector('.plan-cta-url').value : '',
            features: el.querySelector('.plan-features').value.split(',').map(s => s.trim()).filter(Boolean)
        }));
        plans.push({ name: 'Custom Tier', badge: '', price: '₹999', period: '/month', desc: 'Custom enterprise features', features: ['Feature 1', 'Feature 2'], cta: 'Choose Plan', cta_url: 'register-org.html?plan=Custom' });
        this.renderPricingPlans(plans);
    },

    // ──────────────────────────────────────────────────────────
    // SAVE FUNCTIONS (per-category)
    // ──────────────────────────────────────────────────────────

    async saveLandingCMS() {
        try {
            const container = document.getElementById('ps-tab-landing-cms') || document;
            
            // Gather FAQs
            const faqs = [];
            const qInputs = container.querySelectorAll('.faq-q');
            const aInputs = container.querySelectorAll('.faq-a');
            for(let i=0; i<qInputs.length; i++) {
                if(qInputs[i].value && qInputs[i].value.trim()) {
                    faqs.push({ q: qInputs[i].value.trim(), a: aInputs[i] ? aInputs[i].value.trim() : '' });
                }
            }

            // Gather Features
            const features_list = Array.from(container.querySelectorAll('.feature-item')).map(el => ({
                icon: el.querySelector('.feat-icon') ? el.querySelector('.feat-icon').value.trim() : 'star',
                title: el.querySelector('.feat-title') ? el.querySelector('.feat-title').value.trim() : '',
                desc: el.querySelector('.feat-desc') ? el.querySelector('.feat-desc').value.trim() : ''
            })).filter(f => f.title);

            // Gather Steps
            const steps_list = Array.from(container.querySelectorAll('.step-item')).map(el => ({
                num: el.querySelector('.step-num') ? el.querySelector('.step-num').value.trim() : '1',
                title: el.querySelector('.step-title') ? el.querySelector('.step-title').value.trim() : '',
                desc: el.querySelector('.step-desc') ? el.querySelector('.step-desc').value.trim() : ''
            })).filter(s => s.title);

            // Gather Pricing Plans
            const pricing_plans = Array.from(container.querySelectorAll('.pricing-item')).map(el => ({
                name: el.querySelector('.plan-name') ? el.querySelector('.plan-name').value.trim() : '',
                badge: el.querySelector('.plan-badge') ? el.querySelector('.plan-badge').value.trim() : '',
                price: el.querySelector('.plan-price') ? el.querySelector('.plan-price').value.trim() : '',
                period: el.querySelector('.plan-period') ? el.querySelector('.plan-period').value.trim() : '',
                desc: el.querySelector('.plan-desc') ? el.querySelector('.plan-desc').value.trim() : '',
                cta: el.querySelector('.plan-cta') ? el.querySelector('.plan-cta').value.trim() : '',
                cta_url: el.querySelector('.plan-cta-url') ? el.querySelector('.plan-cta-url').value.trim() : '',
                features: el.querySelector('.plan-features') ? el.querySelector('.plan-features').value.split(',').map(s => s.trim()).filter(Boolean) : []
            })).filter(p => p.name);

            const payload = {
                _category: 'Landing Page CMS Settings',
                landing_cms_settings: {
                    enable_landing_page: document.getElementById('ps-cms-enable-landing') ? document.getElementById('ps-cms-enable-landing').checked : true,
                    hero_badge: this._getVal('ps-cms-hero-badge'),
                    hero_title: this._getVal('ps-cms-hero-title'),
                    hero_subtitle: this._getVal('ps-cms-hero-subtitle'),
                    cta_primary_text: this._getVal('ps-cms-cta-primary'),
                    cta_primary_url: this._getVal('ps-cms-cta-primary-url') || '/auth/register-org.html',
                    cta_secondary_text: this._getVal('ps-cms-cta-secondary'),
                    cta_secondary_url: this._getVal('ps-cms-cta-secondary-url') || '#features',
                    hero_stat_1_val: this._getVal('ps-cms-hero-stat1-val'),
                    hero_stat_1_lbl: this._getVal('ps-cms-hero-stat1-lbl'),
                    hero_stat_2_val: this._getVal('ps-cms-hero-stat2-val'),
                    hero_stat_2_lbl: this._getVal('ps-cms-hero-stat2-lbl'),
                    hero_stat_3_val: this._getVal('ps-cms-hero-stat3-val'),
                    hero_stat_3_lbl: this._getVal('ps-cms-hero-stat3-lbl'),
                    hero_feature_1: this._getVal('ps-cms-hero-feature1') || 'Enterprise Secure',
                    hero_feature_2: this._getVal('ps-cms-hero-feature2') || 'Global Scale',
                    hero_feature_3: this._getVal('ps-cms-hero-feature3') || 'High Precision',

                    ticker_1: this._getVal('ps-cms-ticker-1'),
                    ticker_2: this._getVal('ps-cms-ticker-2'),
                    ticker_3: this._getVal('ps-cms-ticker-3'),
                    ticker_4: this._getVal('ps-cms-ticker-4'),
                    ticker_5: this._getVal('ps-cms-ticker-5'),

                    badge_1_icon:  this._getVal('ps-cms-badge-1-icon'),
                    badge_1_label: this._getVal('ps-cms-badge-1-label'),
                    badge_2_icon:  this._getVal('ps-cms-badge-2-icon'),
                    badge_2_label: this._getVal('ps-cms-badge-2-label'),
                    badge_3_icon:  this._getVal('ps-cms-badge-3-icon'),
                    badge_3_label: this._getVal('ps-cms-badge-3-label'),
                    badge_4_icon:  this._getVal('ps-cms-badge-4-icon'),
                    badge_4_label: this._getVal('ps-cms-badge-4-label'),

                    features_title: this._getVal('ps-cms-features-title'),
                    features_subtitle: this._getVal('ps-cms-features-subtitle'),
                    features_list: features_list,

                    steps_badge: this._getVal('ps-cms-steps-badge') || 'Onboarding Flow',
                    steps_title: this._getVal('ps-cms-steps-title'),
                    steps_subtitle: this._getVal('ps-cms-steps-subtitle'),
                    steps_list: steps_list,

                    pricing_badge: this._getVal('ps-cms-pricing-badge') || 'Simple Pricing',
                    pricing_title: this._getVal('ps-cms-pricing-title'),
                    pricing_subtitle: this._getVal('ps-cms-pricing-subtitle'),
                    pricing_plans: pricing_plans,

                    faq_title: this._getVal('ps-cms-faq-title'),
                    faq_subtitle: this._getVal('ps-cms-faq-subtitle'),
                    faqs: faqs,

                    cta_banner_badge: this._getVal('ps-cms-cta-banner-badge') || 'Limited Time Offer',
                    cta_banner_title: this._getVal('ps-cms-cta-banner-title'),
                    cta_banner_subtitle: this._getVal('ps-cms-cta-banner-subtitle'),
                    cta_feature_1: this._getVal('ps-cms-cta-feature-1') || 'Instant Setup',
                    cta_feature_2: this._getVal('ps-cms-cta-feature-2') || 'Full Workflow',
                    cta_feature_3: this._getVal('ps-cms-cta-feature-3') || 'AI Assistant',
                    cta_banner_btn1: this._getVal('ps-cms-cta-banner-btn1') || 'Launch Your Instance',
                    cta_banner_btn1_url: this._getVal('ps-cms-cta-banner-btn1-url') || '/auth/register-org.html',
                    cta_banner_btn2: this._getVal('ps-cms-cta-banner-btn2') || 'Talk to Sales',
                    cta_banner_btn2_url: this._getVal('ps-cms-cta-banner-btn2-url') || 'openTalkToSalesModal()',

                    footer_description: this._getVal('ps-cms-footer-desc'),
                    footer_copyright: this._getVal('ps-cms-footer-copy'),
                    footer_lang: this._getVal('ps-cms-footer-lang') || 'English (US)',
                    footer_status: this._getVal('ps-cms-footer-status'),
                    footer_pages: this.footerPagesData || {}
                }
            };
            await this._put('/settings', payload);
            if (window.OctaQube) OctaQube.toast('Landing CMS settings saved and published successfully!', 'success');
            
            // Refresh preview if open
            const iframe = document.getElementById('ps-cms-iframe');
            if(iframe) iframe.src = '/index.html?t=' + Date.now();
        } catch (e) { if (window.OctaQube) OctaQube.toast(e.message || 'Save failed.', 'error'); }
    },

    async toggleLandingPageStatus(enabled, skipSave = false) {
        const badge = document.getElementById('ps-cms-enable-landing-badge');
        if (badge) {
            if (enabled) {
                badge.textContent = 'ENABLED';
                badge.className = 'badge bg-success-subtle text-success border border-success-subtle ms-2 px-2 py-1';
            } else {
                badge.textContent = 'DISABLED (DIRECT TO LOGIN)';
                badge.className = 'badge bg-danger-subtle text-danger border border-danger-subtle ms-2 px-2 py-1';
            }
        }
        if (skipSave) return;
        try {
            await this.saveLandingCMS();
        } catch (e) {
            console.error('Auto-save of landing page status failed:', e);
        }
    },

    renderFAQs(faqs) {
        const container = document.getElementById('ps-faq-container');
        if (!container) return;
        container.innerHTML = '';
        faqs.forEach(f => {
            const div = document.createElement('div');
            div.className = 'd-flex gap-2 align-items-start p-2.5 rounded-3 border mb-2';
            div.style.background = 'var(--ds-bg-card)';
            div.style.borderColor = 'var(--ds-border-color)';
            div.innerHTML = `
                <div class="flex-grow-1">
                    <input type="text" class="form-control form-control-sm mb-1 faq-q" placeholder="Question" value="${f.q.replace(/"/g, '&quot;')}">
                    <textarea class="form-control form-control-sm faq-a" rows="2" placeholder="Answer">${f.a}</textarea>
                </div>
                <button type="button" class="ds-btn ds-btn-outline ds-btn-sm text-danger" onclick="this.parentElement.remove()">
                    <i data-lucide="trash-2"></i>
                </button>
            `;
            container.appendChild(div);
        });
        if (window.lucide) lucide.createIcons();
    },

    addFAQ() {
        this.renderFAQs([...Array.from(document.querySelectorAll('.faq-q')).map((q, i) => ({ q: q.value, a: document.querySelectorAll('.faq-a')[i].value })), { q: '', a: '' }]);
    },

    async saveGeneral() {
        try {
            const payload = {
                _category: 'Platform General Settings',
                site_name: this._getVal('ps-site-name'),
                support_email: this._getVal('ps-support-email'),
                support_phone: this._getVal('ps-support-phone'),
                support_website: this._getVal('ps-support-website'),
                company_address: this._getVal('ps-company-address'),
                timezone: this._getVal('ps-timezone'),
                default_language: this._getVal('ps-default-language'),
                date_format: this._getVal('ps-date-format'),
                time_format: this._getVal('ps-time-format'),
                currency: this._getVal('ps-currency'),
                default_plan: this._getVal('ps-default-plan'),
                trial_period_days: parseInt(this._getVal('ps-default-trial-days') || this._getVal('ps-trial-days') || 14),
                max_auto_trial_extensions: parseInt(this._getVal('ps-max-auto-trial-extensions') || 2),
                registration_open: this._getChk('ps-registration-open'),
                require_email_otp: this._getChk('ps-require-email-otp'),
                require_phone_otp: this._getChk('ps-require-phone-otp'),
                global_notification: this._getVal('ps-global-notification')
            };
            await this._put('/settings', payload);
            OctaQube.toast('General settings saved.', 'success');
        } catch (e) { OctaQube.toast(e.message || 'Save failed.', 'error'); }
    },

    async saveOtpSettings() {
        try {
            const reqEmail = !!document.getElementById('ps-require-email-otp')?.checked;
            const reqPhone = !!document.getElementById('ps-require-phone-otp')?.checked;
            await this._put('/settings', { require_email_otp: reqEmail, require_phone_otp: reqPhone });
            OctaQube.toast('Registration OTP settings updated successfully.', 'success');
        } catch (e) {
            OctaQube.toast(e.message || 'Failed to update OTP settings.', 'error');
        }
    },

    async saveRegistrationOpenImmediate(inputEl) {
        try {
            const isOpen = !!inputEl.checked;
            await this._put('/settings', { registration_open: isOpen });
            OctaQube.toast(`Self-service sign-up ${isOpen ? 'enabled' : 'disabled'} successfully.`, isOpen ? 'success' : 'info');
        } catch (e) {
            OctaQube.toast(e.message || 'Failed to update sign-up status.', 'error');
        }
    },

    async saveTrialFieldImmediate(fieldKey, inputEl) {
        const statusElId = inputEl.id + '-status';
        const statusEl = document.getElementById(statusElId);
        const val = parseInt(inputEl.value);

        // Validate range
        const min = parseInt(inputEl.min);
        const max = parseInt(inputEl.max);
        if (isNaN(val) || val < min || val > max) {
            inputEl.classList.add('is-invalid');
            if (statusEl) statusEl.textContent = `Range: ${min}–${max}`;
            return;
        }
        inputEl.classList.remove('is-invalid');

        // Show saving indicator
        if (statusEl) {
            statusEl.textContent = 'Saving...';
            statusEl.style.color = 'var(--ds-accent, #3b82f6)';
        }

        try {
            await this._put('/settings', { [fieldKey]: val });

            // Update in-memory data cache
            if (this._data) this._data[fieldKey] = val;

            if (statusEl) {
                statusEl.textContent = '✓ Saved';
                statusEl.style.color = 'var(--ds-success, #22c55e)';
                setTimeout(() => {
                    if (statusEl) { statusEl.textContent = ''; statusEl.style.color = ''; }
                }, 2500);
            }
        } catch (e) {
            if (statusEl) {
                statusEl.textContent = '✗ Error';
                statusEl.style.color = 'var(--ds-danger, #ef4444)';
                setTimeout(() => {
                    if (statusEl) { statusEl.textContent = ''; statusEl.style.color = ''; }
                }, 3000);
            }
            OctaQube.toast(e.message || 'Failed to save setting.', 'error');
        }
    },

    async saveEmail() {
        try {
            const smtpPass = this._getVal('ps-smtp-password');
            const payload = {
                _category: 'Email / SMTP Settings',
                email_settings: {
                    smtp_provider: this._getVal('ps-smtp-provider'),
                    smtp_host: this._getVal('ps-smtp-host'),
                    smtp_port: parseInt(this._getVal('ps-smtp-port') || 587),
                    smtp_username: this._getVal('ps-smtp-username'),
                    smtp_password: smtpPass || '••••••••', // placeholder preserves existing
                    smtp_encryption: this._getVal('ps-smtp-encryption'),
                    from_name: this._getVal('ps-from-name'),
                    from_email: this._getVal('ps-from-email')
                }
            };
            await this._put('/settings', payload);
            OctaQube.toast('Email settings saved.', 'success');
        } catch (e) { OctaQube.toast(e.message || 'Save failed.', 'error'); }
    },

    async testEmail() {
        const toEmail = this._getVal('ps-test-email-to') || '';
        if (!toEmail) { OctaQube.toast('Enter a test recipient email.', 'warning'); return; }
        try {
            const btn = document.getElementById('ps-test-email-btn');
            if (btn) { btn.disabled = true; btn.innerText = 'Sending...'; }
            const res = await this._post('/settings/test-email', { to_email: toEmail });
            OctaQube.toast(res.message || 'Test email sent!', 'success');
        } catch (e) {
            OctaQube.toast(e.message || 'Test email failed.', 'error');
        } finally {
            const btn = document.getElementById('ps-test-email-btn');
            if (btn) { btn.disabled = false; btn.innerText = 'Send Test Email'; }
        }
    },

    async saveAuth() {
        try {
            const payload = {
                _category: 'Authentication Settings',
                authentication_settings: {
                    jwt_expiry_hours: parseInt(this._getVal('ps-jwt-expiry') || 24),
                    native_email_enabled: this._getChk('ps-email-auth'),
                    oauth_google_enabled: this._getChk('ps-google-oauth'),
                    oauth_google_client_id: this._getVal('ps-google-client-id'),
                    oauth_google_client_secret: this._getVal('ps-google-client-secret') || '••••••••',
                    oauth_microsoft_enabled: this._getChk('ps-microsoft-oauth'),
                    oauth_microsoft_client_id: this._getVal('ps-microsoft-client-id'),
                    oauth_microsoft_client_secret: this._getVal('ps-microsoft-client-secret') || '••••••••',
                    oauth_github_enabled: this._getChk('ps-github-oauth'),
                    oauth_github_client_id: this._getVal('ps-github-client-id'),
                    oauth_github_client_secret: this._getVal('ps-github-client-secret') || '••••••••',
                    ldap_enabled: this._getChk('ps-ldap-enabled'),
                    ldap_server: this._getVal('ps-ldap-server'),
                    saml_enabled: this._getChk('ps-saml-auth'),
                    saml_metadata_url: this._getVal('ps-saml-url'),
                    azure_ad_enabled: this._getChk('ps-azure-ad'),
                    mfa_enabled: this._getChk('ps-mfa-enabled'),
                    session_timeout_minutes: parseInt(this._getVal('ps-session-timeout') || 30),
                    max_login_attempts: parseInt(this._getVal('ps-max-login-attempts') || 5),
                    password_expiry_days: parseInt(this._getVal('ps-pw-expiry-days') || 90)
                }
            };
            await this._put('/settings', payload);
            OctaQube.toast('Authentication settings saved.', 'success');
        } catch (e) { OctaQube.toast(e.message || 'Save failed.', 'error'); }
    },

    async saveSecurity() {
        try {
            const payload = {
                _category: 'Security Policy Settings',
                security_settings: {
                    password_min_length: parseInt(this._getVal('ps-pw-min-length') || 8),
                    password_uppercase: this._getChk('ps-pw-uppercase'),
                    password_lowercase: this._getChk('ps-pw-lowercase'),
                    password_numbers: this._getChk('ps-pw-numbers'),
                    password_special: this._getChk('ps-pw-special'),
                    password_history_limit: parseInt(this._getVal('ps-pw-history') || 3),
                    lockout_duration_mins: parseInt(this._getVal('ps-lockout-duration') || 15),
                    brute_force_protection: this._getChk('ps-brute-force'),
                    ip_whitelist: this._getVal('ps-ip-whitelist'),
                    ip_blacklist: this._getVal('ps-ip-blacklist'),
                    allowed_domains: this._getVal('ps-allowed-domains'),
                    api_rate_limit_per_minute: parseInt(this._getVal('ps-api-rate-limit') || 60),
                    waf_mode: this._getSel('ps-waf-mode'),
                    download_restriction: this._getSel('ps-download-restriction'),
                    db_encryption_enabled: this._getChk('ps-db-encryption')
                }
            };
            await this._put('/settings', payload);
            OctaQube.toast('Security policies saved successfully.', 'success');
            // Refresh KPIs after save
            this.loadSecurityKPIs();
        } catch (e) { OctaQube.toast(e.message || 'Save failed.', 'error'); }
    },

    async loadSecurityKPIs() {
        try {
            const API_BASE = window.OctaQube_API_BASE || '/api/super-admin';
            // Cookie authentication handled via credentials: 'include'
            const r = await fetch(`${API_BASE}/settings/security-kpis`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!r.ok) return;
            const json = await r.json();
            const d = json.data || {};
            const score = d.security_score || 0;
            let grade = 'F';
            if (score >= 90) grade = 'A+';
            else if (score >= 80) grade = 'A';
            else if (score >= 70) grade = 'B';
            else if (score >= 60) grade = 'C';
            else if (score >= 50) grade = 'D';

            const scoreEl = document.getElementById('sec-kpi-score');
            if (scoreEl) scoreEl.textContent = `${score} / 100 (${grade})`;

            const blockedEl = document.getElementById('sec-kpi-blocked');
            if (blockedEl) blockedEl.textContent = `${d.blocked_ips_24h ?? 0} IPs`;

            const threatEl = document.getElementById('sec-kpi-threats');
            if (threatEl) {
                const cnt = d.critical_threat_alerts ?? 0;
                threatEl.textContent = `${cnt} Critical`;
                threatEl.className = `text-xs fw-bold ${cnt > 0 ? 'text-danger' : 'text-success'}`;
            }

            const encEl = document.getElementById('sec-kpi-encryption');
            if (encEl) encEl.textContent = d.encryption_status || 'TLS 1.3 Only';
        } catch (e) {
            // Silently fail — KPI cards will keep their last values
        }
    },

    async loadAuthKPIs() {
        try {
            const API_BASE = window.OctaQube_API_BASE || '/api/super-admin';
            // Cookie authentication handled via credentials: 'include'
            const r = await fetch(`${API_BASE}/settings/auth-kpis`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!r.ok) return;
            const json = await r.json();
            const d = json.data || {};

            const loginsEl = document.getElementById('ps-auth-kpi-logins');
            if (loginsEl) loginsEl.textContent = (d.login_attempts ?? 0).toLocaleString();

            const sessionsEl = document.getElementById('ps-auth-kpi-sessions');
            if (sessionsEl) sessionsEl.textContent = (d.active_sessions ?? 0).toLocaleString();

            const failedEl = document.getElementById('ps-auth-kpi-failed');
            if (failedEl) failedEl.textContent = (d.failed_logins_24h ?? 0).toLocaleString();

            const lockedEl = document.getElementById('ps-auth-kpi-locked');
            if (lockedEl) lockedEl.textContent = (d.locked_accounts ?? 0).toLocaleString();
        } catch (e) {
            console.warn('[PlatformSettings] loadAuthKPIs error:', e);
        }
    },

    // ─── Utility: get selected value of a <select> element ──────────────────
    _getSel(id) {
        const el = document.getElementById(id);
        return el ? el.value : '';
    },

    // ─── Utility: set selected value of a <select> element ──────────────────
    _sel(id, val) {
        const el = document.getElementById(id);
        if (el && val !== undefined && val !== null) el.value = String(val);
    },


    async saveNotifications() {
        try {
            const payload = {
                _category: 'Notification Settings',
                notification_settings: {
                    email_notifications: this._getChk('ps-notif-email'),
                    sms_notifications: this._getChk('ps-notif-sms'),
                    push_notifications: this._getChk('ps-notif-push'),
                    in_app_notifications: this._getChk('ps-notif-inapp'),
                    slack_enabled: this._getChk('ps-notif-slack'),
                    slack_webhook_url: this._getVal('ps-notif-slack-url'),
                    teams_enabled: this._getChk('ps-notif-teams'),
                    teams_webhook_url: this._getVal('ps-notif-teams-url'),
                    summary_preference: this._getVal('ps-notif-summary')
                }
            };
            await this._put('/settings', payload);
            OctaQube.toast('Notification settings saved.', 'success');
        } catch (e) { OctaQube.toast(e.message || 'Save failed.', 'error'); }
    },

    async saveStorage() {
        try {
            const current = (this._data && this._data.storage_settings) || {};
            const payload = {
                _category: 'Storage Settings',
                storage_settings: {
                    total_capacity_gb: parseFloat(current.total_capacity_gb || 1000.0),
                    storage_provider: this._getVal('ps-storage-provider') || 'local',
                    s3_bucket: this._getVal('ps-s3-bucket') || '',
                    max_upload_limit_mb: parseInt(this._getVal('ps-max-upload-mb') || 100),
                    storage_alerts_percent: parseInt(this._getVal('ps-storage-alert-pct') || 80),
                    storage_used_gb: parseFloat(current.storage_used_gb || 0.0)
                }
            };
            await this._put('/settings', payload);
            OctaQube.toast('Storage settings saved.', 'success');
            await this.loadAllSettings();
        } catch (e) { OctaQube.toast(e.message || 'Save failed.', 'error'); }
    },

    toggleStorageProviderGuide(value) {
        ['local', 's3', 'azure', 'gcs'].forEach(id => {
            const el = document.getElementById(`ps-guide-${id}`);
            if (el) el.style.display = 'none';
        });
        const activeEl = document.getElementById(`ps-guide-${value}`);
        if (activeEl) activeEl.style.display = 'block';
    },

    async saveBackup() {
        try {
            const s3Secret = this._getVal('ps-backup-s3-secret');
            const payload = {
                _category: 'Backup Settings',
                backup_settings: {
                    auto_backup_enabled: this._getChk('ps-backup-auto'),
                    backup_schedule: this._getVal('ps-backup-schedule'),
                    backup_destination: this._getVal('ps-backup-dest'),
                    s3_bucket: this._getVal('ps-backup-s3-bucket'),
                    s3_region: this._getVal('ps-backup-s3-region'),
                    s3_access_key: this._getVal('ps-backup-s3-key'),
                    s3_secret_key: s3Secret || '••••••••'
                }
            };
            await this._put('/settings', payload);
            OctaQube.toast('Backup settings saved.', 'success');
        } catch (e) { OctaQube.toast(e.message || 'Save failed.', 'error'); }
    },

    toggleBackupDestInputs(value) {
        const fields = document.getElementById('ps-backup-s3-fields');
        if (fields) {
            fields.style.display = value === 's3' ? 'flex' : 'none';
        }
    },

    async triggerManualBackup() {
        try {
            const btn = document.getElementById('ps-trigger-backup-btn');
            if (btn) { btn.disabled = true; btn.innerText = 'Running Backup...'; }
            const res = await this._post('/settings/backup', {});
            OctaQube.toast(res.message || 'Backup completed!', 'success');
            // Refresh history
            await this.loadAllSettings();
        } catch (e) {
            OctaQube.toast(e.message || 'Backup failed.', 'error');
        } finally {
            const btn = document.getElementById('ps-trigger-backup-btn');
            if (btn) { btn.disabled = false; btn.innerText = 'Run Manual Backup'; }
        }
    },

    loadBackupHistory(history) {
        const tbody = document.getElementById('ps-backup-history');
        if (!tbody) return;
        if (!history.length) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center py-3 ds-text-secondary">No backups recorded yet.</td></tr>';
            return;
        }
        tbody.innerHTML = history.slice(0, 20).map(b => `
            <tr>
                <td><span class="badge bg-${b.status === 'Completed' ? 'success' : 'danger'}-subtle text-${b.status === 'Completed' ? 'success' : 'danger'}">${b.status}</span></td>
                <td>${b.type}</td>
                <td>${new Date(b.created_at).toLocaleString()}</td>
                <td>${b.size_mb} MB</td>
                <td>${b.destination}</td>
            </tr>
        `).join('');
    },

    async saveApiSettings() {
        try {
            const payload = {
                _category: 'API Settings',
                api_settings: {
                    api_rate_limit: parseInt(this._getVal('ps-api-rate-limit-cfg') || 60),
                    api_token_expiry_hours: parseInt(this._getVal('ps-api-token-expiry') || 24),
                    api_monitoring_enabled: this._getChk('ps-api-monitoring')
                }
            };
            await this._put('/settings', payload);
            OctaQube.toast('API settings saved.', 'success');
        } catch (e) { OctaQube.toast(e.message || 'Save failed.', 'error'); }
    },

    async generateApiKey() {
        const label = this._getVal('ps-new-api-key-label') || 'Platform API Key';
        const scopesEl = document.querySelectorAll('.ps-api-scope-cb:checked');
        const scopes = Array.from(scopesEl).map(el => el.value);
        if (!scopes.length) scopes.push('read');
        try {
            const res = await this._post('/settings/api-keys', { label, scopes, rate_limit: 60 });
            const keyData = res.data;
            // Show the secret once in a modal
            this._showApiKeyModal(keyData.secret, label);
            await this.loadAllSettings();
        } catch (e) { OctaQube.toast(e.message || 'Failed to generate API key.', 'error'); }
    },

    _showApiKeyModal(secret, label) {
        const modal = document.getElementById('ps-api-key-modal');
        if (!modal) { alert(`New API Key for "${label}":\n\n${secret}\n\nStore this securely — it won't be shown again.`); return; }
        document.getElementById('ps-api-key-secret-display').value = secret;
        document.getElementById('ps-api-key-modal-label').innerText = label;
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
    },

    copyApiKeyFromModal() {
        const val = document.getElementById('ps-api-key-secret-display')?.value;
        if (val) { navigator.clipboard.writeText(val); OctaQube.toast('API key copied to clipboard.', 'success'); }
    },

    loadApiKeys(keys) {
        const tbody = document.getElementById('ps-api-keys-table');
        if (!tbody) return;
        if (!keys.length) {
            tbody.innerHTML = '<tr><td colspan="5" class="text-center py-3 ds-text-secondary">No API keys generated yet.</td></tr>';
            return;
        }
        tbody.innerHTML = keys.map(k => `
            <tr>
                <td><code class="text-primary">${k.prefix}.*</code></td>
                <td>${k.label}</td>
                <td>${(k.scopes || []).map(s => `<span class="badge bg-primary-subtle text-primary me-1">${s}</span>`).join('')}</td>
                <td>${new Date(k.expires_at).toLocaleDateString()}</td>
                <td>
                    <button class="ds-btn ds-btn-sm ds-btn-outline-danger" onclick="PlatformSettings.revokeApiKey('${k.id}')">
                        <i data-lucide="trash-2" style="width:14px;"></i> Revoke
                    </button>
                </td>
            </tr>
        `).join('');
        if (window.lucide) lucide.createIcons();
    },

    async revokeApiKey(keyId) {
        if (!confirm('Revoking this key will immediately break any integrations using it. Proceed?')) return;
        try {
            await this._delete(`/settings/api-keys/${keyId}`);
            OctaQube.toast('API key revoked.', 'success');
            await this.loadAllSettings();
        } catch (e) { OctaQube.toast(e.message || 'Failed to revoke key.', 'error'); }
    },

    async saveWebhooks() {
        const url = this._getVal('ps-new-webhook-url');
        const events = Array.from(document.querySelectorAll('.ps-webhook-event-cb:checked')).map(el => el.value);
        if (!url) { OctaQube.toast('Webhook URL is required.', 'warning'); return; }
        try {
            const existing = this._data?.webhook_settings?.webhook_configs || [];
            existing.push({
                id: Date.now().toString(),
                url,
                events,
                enabled: true,
                created_at: new Date().toISOString()
            });
            const payload = {
                _category: 'Webhook Settings',
                webhook_settings: {
                    webhook_configs: existing,
                    default_retry_attempts: parseInt(this._getVal('ps-webhook-retry') || 3),
                    timeout_seconds: parseInt(this._getVal('ps-webhook-timeout') || 30)
                }
            };
            await this._put('/settings', payload);
            OctaQube.toast('Webhook saved.', 'success');
            await this.loadAllSettings();
        } catch (e) { OctaQube.toast(e.message || 'Save failed.', 'error'); }
    },

    async testWebhook(url) {
        const target = url || this._getVal('ps-new-webhook-url');
        if (!target) { OctaQube.toast('Enter a webhook URL to test.', 'warning'); return; }
        try {
            const res = await this._post('/settings/test-webhook', { url: target });
            OctaQube.toast(res.message || 'Webhook test sent.', 'success');
        } catch (e) { OctaQube.toast(e.message || 'Webhook test failed.', 'error'); }
    },

    loadWebhookConfigs(configs) {
        const tbody = document.getElementById('ps-webhooks-table');
        if (!tbody) return;
        if (!configs.length) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center py-3 ds-text-secondary">No webhooks configured.</td></tr>';
            return;
        }
        tbody.innerHTML = configs.map(c => `
            <tr>
                <td><code class="small">${c.url}</code></td>
                <td>${(c.events || []).map(e => `<span class="badge bg-info-subtle text-info me-1">${e}</span>`).join('') || 'All'}</td>
                <td><span class="badge bg-${c.enabled ? 'success' : 'secondary'}-subtle text-${c.enabled ? 'success' : 'secondary'}">${c.enabled ? 'Active' : 'Disabled'}</span></td>
                <td>
                    <button class="ds-btn ds-btn-sm ds-btn-outline me-1" onclick="PlatformSettings.testWebhook('${c.url}')">Test</button>
                    <button class="ds-btn ds-btn-sm ds-btn-outline-danger" onclick="PlatformSettings.removeWebhook('${c.id}')">Remove</button>
                </td>
            </tr>
        `).join('');
    },

    async removeWebhook(webhookId) {
        try {
            const existing = (this._data?.webhook_settings?.webhook_configs || []).filter(w => w.id !== webhookId);
            const payload = {
                _category: 'Webhook Settings',
                webhook_settings: { ...(this._data?.webhook_settings || {}), webhook_configs: existing }
            };
            await this._put('/settings', payload);
            OctaQube.toast('Webhook removed.', 'success');
            await this.loadAllSettings();
        } catch (e) { OctaQube.toast(e.message || 'Remove failed.', 'error'); }
    },

    renderIntegrations(integrations) {
        const grid = document.getElementById('ps-integrations-grid');
        if (!grid) return;
        const icons = {
            google_workspace: '🌐', microsoft_365: '🔷', slack: '💬', teams: '🔷',
            zapier: '⚡', twilio: '📱', firebase: '🔥', stripe: '💳',
            razorpay: '💳', openai: '🤖', anthropic: '🤖', aws: '☁️', azure: '☁️',
            upi: '📱'
        };
        const names = {
            google_workspace: 'Google Workspace', microsoft_365: 'Microsoft 365',
            slack: 'Slack', teams: 'MS Teams', zapier: 'Zapier', twilio: 'Twilio',
            firebase: 'Firebase', stripe: 'Stripe', razorpay: 'Razorpay',
            openai: 'OpenAI', anthropic: 'Anthropic', aws: 'Amazon AWS', azure: 'Microsoft Azure',
            upi: 'UPI Dynamic QR'
        };
        grid.innerHTML = Object.entries(integrations).map(([key, cfg]) => `
            <div class="col-md-6 col-lg-4">
                <div class="glass-card p-2.5 h-100 d-flex flex-column justify-content-between" style="min-width:0; overflow:hidden;">
                    <div class="d-flex align-items-start justify-content-between mb-2 gap-2">
                        <div class="d-flex align-items-center gap-2" style="min-width:0; flex:1;">
                            <span style="font-size:1.5rem; flex-shrink:0;">${icons[key] || '🔌'}</span>
                            <div class="d-flex flex-column" style="min-width:0; flex:1;">
                                <span class="fw-bold ds-text-main text-truncate" style="font-size:13px;" title="${names[key] || key}">${names[key] || key}</span>
                                <div>
                                    <span class="badge bg-${cfg.enabled ? 'success' : 'secondary'}-subtle text-${cfg.enabled ? 'success' : 'secondary'} mt-0.5" style="font-size:10px; padding: 2px 6px; font-weight:600;">
                                        ${cfg.status || (cfg.enabled ? 'Connected' : 'Disconnected')}
                                    </span>
                                </div>
                            </div>
                        </div>
                        <div class="form-check form-switch mb-0 flex-shrink-0 ms-1">
                            <input class="form-check-input" type="checkbox" id="int-${key}" ${cfg.enabled ? 'checked' : ''} onchange="PlatformSettings.toggleIntegration('${key}', this.checked)">
                        </div>
                    </div>
                    <div class="d-flex gap-1.5 mt-2 pt-2 border-top" style="border-color:var(--ds-border-color)!important;">
                        <button class="ds-btn ds-btn-sm ds-btn-secondary flex-grow-1 text-truncate" style="font-size:11px; padding:4px 8px;" onclick="PlatformSettings.configureIntegration('${key}')">Configure</button>
                        ${cfg.enabled ? `<button class="ds-btn ds-btn-sm ds-btn-outline flex-shrink-0" style="font-size:11px; padding:4px 8px;" onclick="PlatformSettings.healthCheck('${key}')">Health</button>` : ''}
                    </div>
                </div>
            </div>
        `).join('');
    },

    async toggleIntegration(key, enabled) {
        try {
            const integrations = this._data?.integrations_settings || {};
            if (!integrations[key]) integrations[key] = {};
            integrations[key].enabled = enabled;
            integrations[key].status = enabled ? 'Connected' : 'Disconnected';
            const payload = {
                _category: 'Integration Settings',
                integrations_settings: integrations
            };
            await this._put('/settings', payload);
            this._data.integrations_settings = integrations;
            OctaQube.toast(`${key} ${enabled ? 'enabled' : 'disabled'}.`, 'success');
        } catch (e) { OctaQube.toast(e.message || 'Toggle failed.', 'error'); }
    },

    configureIntegration(key) {
        this.openAPIKeyModal('integrations_settings', key);
    },

    openAPIKeyModal(category, providerKey, additionalUpdatesCallback) {
        const meta = this.PROVIDER_META[providerKey] || { 
            name: providerKey, desc: `Configure ${providerKey} API Access.`, url: '#', steps: ['Consult provider documentation.', 'Generate API Key.'], fields: [{id: 'api_key', label: 'API Key', type: 'password'}] 
        };
        
        document.getElementById('apiKeyModalTitle').innerHTML = `<i data-lucide="key" class="text-primary me-2"></i> ${meta.name} Configuration`;
        document.getElementById('apiKeyModalDesc').innerText = meta.desc;
        
        const stepsHtml = meta.steps.map(s => `<li>${s}</li>`).join('');
        document.getElementById('apiKeyModalSteps').innerHTML = stepsHtml;
        
        const linkBtn = document.getElementById('apiKeyModalLink');
        if (providerKey === 'smtp') {
            // For SMTP, show multiple provider shortcut buttons
            linkBtn.style.display = 'none';
            const stepsBox = document.getElementById('apiKeyModalSteps').parentElement;
            let smtpLinksEl = stepsBox.querySelector('.smtp-provider-links');
            if (!smtpLinksEl) {
                smtpLinksEl = document.createElement('div');
                smtpLinksEl.className = 'smtp-provider-links d-flex flex-wrap gap-2 mt-2';
                stepsBox.appendChild(smtpLinksEl);
            }
            smtpLinksEl.innerHTML = [
                { label: 'SendGrid', url: 'https://app.sendgrid.com/settings/api_keys', icon: '📧' },
                { label: 'Mailgun',  url: 'https://app.mailgun.com/settings/api_security', icon: '📨' },
                { label: 'Brevo',    url: 'https://app.brevo.com/settings/keys/api', icon: '✉️' },
                { label: 'Postmark', url: 'https://account.postmarkapp.com/api_tokens', icon: '📮' },
            ].map(p => `<a href="${p.url}" target="_blank" rel="noopener" class="ds-btn ds-btn-outline ds-btn-sm d-inline-flex align-items-center gap-1" style="font-size:11px;">${p.icon} ${p.label} <i data-lucide="external-link" style="width:10px;height:10px;"></i></a>`).join('');
            if (window.lucide) lucide.createIcons();
        } else {
            // Remove smtp-specific links if switching provider
            const stepsBox = document.getElementById('apiKeyModalSteps').parentElement;
            const smtpLinksEl = stepsBox.querySelector('.smtp-provider-links');
            if (smtpLinksEl) smtpLinksEl.remove();
            if (meta.url && meta.url !== '#') {
                linkBtn.href = meta.url;
                linkBtn.style.display = 'flex';
            } else {
                linkBtn.style.display = 'none';
            }
        }

        document.getElementById('ak-category').value = category;
        document.getElementById('ak-provider-key').value = providerKey;
        
        const dynamicInputsContainer = document.getElementById('ak-dynamic-inputs');
        dynamicInputsContainer.innerHTML = ''; // clear existing
        
        const categoryData = this._data[category] || {};
        const existingConfig = category === 'integrations_settings' ? (categoryData[providerKey] || {}) : categoryData;
        
        meta.fields.forEach(field => {
            // Check if there is an existing value to pre-fill
            let val = '';
            if (category === 'email_settings' && field.id === 'api_key') val = categoryData.smtp_password || '';
            else val = existingConfig[field.id] || '';

            let inputHtml = '';
            if (field.type === 'textarea') {
                inputHtml = `<textarea class="ds-input font-monospace" id="ak-input-${field.id}" data-key="${field.id}" rows="4" required placeholder="Paste ${field.label} here">${val}</textarea>`;
            } else {
                inputHtml = `<input type="${field.type}" class="ds-input font-monospace" id="ak-input-${field.id}" data-key="${field.id}" required placeholder="Enter ${field.label}" value="${val}">`;
            }

            const colDiv = document.createElement('div');
            colDiv.className = 'col-12';
            colDiv.innerHTML = `
                <div class="ds-field mb-0">
                    <label class="ds-label text-uppercase tracking-wider">${field.label}</label>
                    ${inputHtml}
                </div>
            `;
            dynamicInputsContainer.appendChild(colDiv);
        });

        if (window.lucide && typeof window.lucide.createIcons === 'function') {
            window.lucide.createIcons();
        }

        this._keyModalCallback = additionalUpdatesCallback;

        const modalEl = document.getElementById('apiKeyModal');
        const bsModal = new bootstrap.Modal(modalEl);
        bsModal.show();
    },

    async saveAPIKeyFromModal() {
        const category = document.getElementById('ak-category').value;
        const key = document.getElementById('ak-provider-key').value;
        
        const meta = this.PROVIDER_META[key] || { fields: [{id: 'api_key'}] };
        const extractedData = {};
        
        // Grab all data from dynamic inputs
        for (const field of meta.fields) {
            const el = document.getElementById(`ak-input-${field.id}`);
            if (el) {
                if (!el.value && field.type !== 'textarea') { // allow empty JSON for now? Actually let's require it.
                    OctaQube.toast(`Please enter ${field.label}.`, 'warning');
                    return;
                }
                extractedData[field.id] = el.value;
            }
        }

        try {
            const btn = document.querySelector('#apiKeyModal .ds-btn-primary');
            const ogText = btn.innerHTML;
            btn.innerHTML = 'Saving...';
            btn.disabled = true;

            const categoryData = this._data[category] || {};
            
            // Handle different data structures based on category
            if (category === 'integrations_settings') {
                if (!categoryData[key]) categoryData[key] = {};
                // Merge all extracted fields into the provider config
                Object.assign(categoryData[key], extractedData);
            } else if (category === 'ai_settings' || category === 'sms_settings') {
                if (extractedData.api_key) categoryData.api_key = extractedData.api_key;
            } else if (category === 'email_settings') {
                if (extractedData.api_key) categoryData.smtp_password = extractedData.api_key;
            }

            const payload = {
                _category: 'API Key Update',
                [category]: categoryData
            };
            
            await this._put('/settings', payload);
            this._data[category] = categoryData;
            
            if (this._keyModalCallback) {
                // Return the first key for UI backwards compatibility (like setting readonly input)
                const firstVal = Object.values(extractedData)[0] || '';
                this._keyModalCallback(firstVal);
            }

            const modalEl = document.getElementById('apiKeyModal');
            const bsModal = bootstrap.Modal.getInstance(modalEl);
            if (bsModal) bsModal.hide();

            OctaQube.toast(`${this.PROVIDER_META[key]?.name || key} API Key configured successfully.`, 'success');
        } catch (e) {
            OctaQube.toast(e.message || 'Failed to save API Key.', 'error');
        } finally {
            const btn = document.querySelector('#apiKeyModal .ds-btn-primary');
            if(btn) {
                btn.innerHTML = 'Save & Connect';
                btn.disabled = false;
            }
        }
    },

    async healthCheck(key) {
        try {
            const res = await this._post('/settings/integration-health', { integration: key });
            OctaQube.toast(res.message, res.status === 'success' ? 'success' : 'error');
        } catch (e) { OctaQube.toast(e.message || 'Health check failed.', 'error'); }
    },

    aiModelPresets: {
        openrouter: [
            { id: 'openrouter/auto', name: 'OpenRouter Auto (Smart Best Model Router)' },
            { id: 'openai/gpt-4o', name: 'OpenAI GPT-4o (via OpenRouter)' },
            { id: 'openai/gpt-4o-mini', name: 'OpenAI GPT-4o Mini (Ultra Fast)' },
            { id: 'anthropic/claude-3.5-sonnet', name: 'Anthropic Claude 3.5 Sonnet' },
            { id: 'deepseek/deepseek-r1', name: 'DeepSeek R1 Reasoning (DeepSeek)' },
            { id: 'google/gemini-2.0-flash-001', name: 'Google Gemini 2.0 Flash' },
            { id: 'meta-llama/llama-3.3-70b-instruct', name: 'Meta Llama 3.3 70B Instruct' },
            { id: 'mistralai/mistral-large-2411', name: 'Mistral Large 2 (2411)' },
            { id: 'qwen/qwen-2.5-72b-instruct', name: 'Qwen 2.5 72B Instruct' }
        ],
        openai: [
            { id: 'gpt-4o', name: 'GPT-4o (Flagship Multimodal)' },
            { id: 'gpt-4o-mini', name: 'GPT-4o Mini (Fast & Cost Effective)' },
            { id: 'gpt-4-turbo', name: 'GPT-4 Turbo' },
            { id: 'o1', name: 'o1 Reasoning Model' },
            { id: 'o3-mini', name: 'o3-mini STEM Reasoning' }
        ],
        gemini: [
            { id: 'gemini-2.0-flash', name: 'Gemini 2.0 Flash (Latest)' },
            { id: 'gemini-1.5-pro', name: 'Gemini 1.5 Pro (2M Context Window)' },
            { id: 'gemini-1.5-flash', name: 'Gemini 1.5 Flash' }
        ],
        claude: [
            { id: 'claude-3-5-sonnet-20241022', name: 'Claude 3.5 Sonnet (Latest)' },
            { id: 'claude-3-5-haiku-20241022', name: 'Claude 3.5 Haiku' },
            { id: 'claude-3-opus-20240229', name: 'Claude 3 Opus' }
        ],
        deepseek: [
            { id: 'deepseek-r1', name: 'DeepSeek-R1 (Chain-of-Thought Reasoning)' },
            { id: 'deepseek-chat', name: 'DeepSeek-V3 (General Chat/Code)' },
            { id: 'deepseek-coder', name: 'DeepSeek-Coder V2' }
        ],
        groq: [
            { id: 'llama-3.3-70b-versatile', name: 'Groq Llama 3.3 70B Versatile' },
            { id: 'mixtral-8x7b-32768', name: 'Groq Mixtral 8x7B' }
        ],
        azure: [
            { id: 'azure-gpt-4o', name: 'Azure OpenAI GPT-4o Deployment' },
            { id: 'azure-gpt-35-turbo', name: 'Azure OpenAI GPT-3.5 Turbo' }
        ],
        ollama: [
            { id: 'llama3.1', name: 'Local Ollama Llama 3.1 8B' },
            { id: 'qwen2.5-coder', name: 'Local Ollama Qwen 2.5 Coder' },
            { id: 'mistral', name: 'Local Ollama Mistral 7B' }
        ]
    },

    onAIProviderChange() {
        const provider = this._getVal('ps-ai-provider') || 'openrouter';
        const presetSelect = document.getElementById('ps-ai-model-preset');
        const openrouterBox = document.getElementById('ps-openrouter-config-box');
        const apiKeyInput = document.getElementById('ps-ai-api-key');

        if (openrouterBox) {
            openrouterBox.style.display = (provider === 'openrouter') ? 'block' : 'none';
        }

        if (apiKeyInput) {
            const placeholders = {
                openrouter: 'sk-or-v1-••••••••',
                openai: 'sk-proj-••••••••',
                gemini: 'AIzaSy••••••••',
                claude: 'sk-ant-api03-••••••••',
                deepseek: 'sk-deepseek-••••••••',
                groq: 'gsk_••••••••',
                azure: 'azure-api-key-••••••••',
                ollama: 'http://localhost:11434 (Local Endpoint)'
            };
            apiKeyInput.placeholder = placeholders[provider] || 'API Key / Token';
        }

        if (presetSelect) {
            presetSelect.innerHTML = '';
            const presets = this.aiModelPresets[provider] || [];
            presets.forEach(p => {
                const opt = document.createElement('option');
                opt.value = p.id;
                opt.textContent = p.name;
                presetSelect.appendChild(opt);
            });
            const customOpt = document.createElement('option');
            customOpt.value = 'custom';
            customOpt.textContent = 'Custom Model String...';
            presetSelect.appendChild(customOpt);

            if (presets.length > 0) {
                presetSelect.value = presets[0].id;
                this._val('ps-ai-model', presets[0].id);
            }
        }

        // Update KPI label
        const kpiGateway = document.getElementById('ps-ai-kpi-gateway');
        if (kpiGateway) {
            const providerNames = {
                openrouter: 'OpenRouter / Unified',
                openai: 'OpenAI Direct',
                gemini: 'Google Gemini',
                claude: 'Anthropic Claude',
                deepseek: 'DeepSeek AI',
                groq: 'Groq LPU',
                azure: 'Azure OpenAI',
                ollama: 'Ollama Local'
            };
            kpiGateway.textContent = providerNames[provider] || provider;
        }
    },

    onAIModelPresetChange() {
        const presetVal = this._getVal('ps-ai-model-preset');
        if (presetVal && presetVal !== 'custom') {
            this._val('ps-ai-model', presetVal);
        }
    },

    async testAIConnection() {
        const provider = this._getVal('ps-ai-provider');
        const apiKey = this._getVal('ps-ai-api-key');
        const model = this._getVal('ps-ai-model');

        try {
            OctaQube.toast(`Testing connection to ${provider.toUpperCase()} (${model})...`, 'info');
            const res = await this._post('/settings/test-ai', {
                provider: provider,
                api_key: apiKey,
                model: model,
                openrouter_site_url: this._getVal('ps-ai-openrouter-site'),
                openrouter_app_name: this._getVal('ps-ai-openrouter-app')
            });
            if (res.status === 'success') {
                OctaQube.toast(res.message || `Connected to ${provider} API successfully!`, 'success');
            } else {
                OctaQube.toast(res.message || 'AI API connection failed.', 'error');
            }
        } catch (e) {
            OctaQube.toast(e.message || `Failed to connect to ${provider} API.`, 'error');
        }
    },

    async saveAI() {
        try {
            const payload = {
                _category: 'AI Configuration Settings',
                ai_settings: {
                    ai_provider: this._getVal('ps-ai-provider'),
                    api_key: this._getVal('ps-ai-api-key'),
                    default_model: this._getVal('ps-ai-model'),
                    temperature: parseFloat(this._getVal('ps-ai-temperature') || 0.4),
                    max_tokens: parseInt(this._getVal('ps-ai-max-tokens') || 2048),
                    ai_usage_limit_usd: parseFloat(this._getVal('ps-ai-usage-limit') || 100),
                    openrouter_site_url: this._getVal('ps-ai-openrouter-site'),
                    openrouter_app_name: this._getVal('ps-ai-openrouter-app'),
                    model_fallbacks: this._getVal('ps-ai-fallbacks'),
                    ai_logging: this._getChk('ps-ai-logging')
                }
            };
            await this._put('/settings', payload);
            OctaQube.toast('AI configuration saved successfully.', 'success');
        } catch (e) { OctaQube.toast(e.message || 'Save failed.', 'error'); }
    },

    // ──────────────────────────────────────────────────────────
    // REAL-TIME BRANDING ENGINE
    // ──────────────────────────────────────────────────────────

    _hexToRgb(hex) {
        if (!hex || typeof hex !== 'string') return '37, 99, 235';
        let c = hex.replace('#', '');
        if (c.length === 3) c = c.split('').map(x => x + x).join('');
        const num = parseInt(c, 16);
        return isNaN(num) ? '37, 99, 235' : `${(num >> 16) & 255}, ${(num >> 8) & 255}, ${num & 255}`;
    },

    _brandingData: null,

    _initBrandingData(backendBrand = {}) {
        let brand = backendBrand || {};
        const lightDefaults = window.DEFAULT_PALETTES?.light || {
            primary_color: '#2563eb', secondary_color: '#64748b', accent_color: '#10b981',
            success_color: '#16a34a', warning_color: '#f59e0b', danger_color: '#ef4444'
        };
        const darkDefaults = window.DEFAULT_PALETTES?.dark || {
            primary_color: '#3b82f6', secondary_color: '#94a3b8', accent_color: '#34d399',
            success_color: '#22c55e', warning_color: '#fbbf24', danger_color: '#f87171'
        };

        if (!brand.light || !brand.dark) {
            const existingLight = brand.light || {
                primary_color: brand.primary_color || lightDefaults.primary_color,
                secondary_color: brand.secondary_color || lightDefaults.secondary_color,
                accent_color: brand.accent_color || lightDefaults.accent_color,
                success_color: brand.success_color || lightDefaults.success_color,
                warning_color: brand.warning_color || lightDefaults.warning_color,
                danger_color: brand.danger_color || lightDefaults.danger_color,
            };
            const existingDark = brand.dark || {
                primary_color: brand.dark_primary_color || darkDefaults.primary_color,
                secondary_color: brand.dark_secondary_color || darkDefaults.secondary_color,
                accent_color: brand.dark_accent_color || darkDefaults.accent_color,
                success_color: brand.dark_success_color || darkDefaults.success_color,
                warning_color: brand.dark_warning_color || darkDefaults.warning_color,
                danger_color: brand.dark_danger_color || darkDefaults.danger_color,
            };

            brand = {
                ...brand,
                light: existingLight,
                dark: existingDark,
                font_family: brand.font_family || 'Inter',
                font_size: brand.font_size || '14px',
                border_radius: brand.border_radius || '10px',
                card_style: brand.card_style || 'glass',
                button_style: brand.button_style || 'rounded',
                assets: brand.assets || JSON.parse(localStorage.getItem('octaqube_brand_assets') || '{}')
            };
        }
        this._brandingData = brand;
        localStorage.setItem('octaqube_branding_config', JSON.stringify(brand));
        return brand;
    },

    syncBrandingInputs() {
        const currentMode = document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
        const badge = document.getElementById('ps-palette-mode-badge');
        if (badge) {
            if (currentMode === 'dark') {
                badge.innerHTML = `<i data-lucide="moon" style="width:12px;height:12px;" class="me-1"></i> Active: Dark Mode Palette`;
                badge.className = 'badge bg-purple bg-opacity-10 text-purple border border-purple border-opacity-25 rounded-pill px-2.5 py-1 text-xs fw-semibold d-flex align-items-center gap-1';
            } else {
                badge.innerHTML = `<i data-lucide="sun" style="width:12px;height:12px;" class="me-1"></i> Active: Light Mode Palette`;
                badge.className = 'badge bg-primary bg-opacity-10 text-primary border border-primary border-opacity-25 rounded-pill px-2.5 py-1 text-xs fw-semibold d-flex align-items-center gap-1';
            }
            if (window.lucide) lucide.createIcons();
        }

        const brand = this._brandingData || this._initBrandingData(JSON.parse(localStorage.getItem('octaqube_branding_config') || '{}'));
        const modePalette = (brand && brand[currentMode]) ? brand[currentMode] : (window.DEFAULT_PALETTES?.[currentMode] || {});

        const colorMap = [
            { id: 'ps-primary-color', txt: 'ps-primary-color-text', val: modePalette.primary_color || (currentMode === 'dark' ? '#3b82f6' : '#2563eb') },
            { id: 'ps-secondary-color', txt: 'ps-secondary-color-text', val: modePalette.secondary_color || (currentMode === 'dark' ? '#94a3b8' : '#6b7280') },
            { id: 'ps-accent-color', txt: 'ps-accent-color-text', val: modePalette.accent_color || (currentMode === 'dark' ? '#34d399' : '#10b981') },
            { id: 'ps-success-color', txt: 'ps-success-color-text', val: modePalette.success_color || (currentMode === 'dark' ? '#22c55e' : '#16a34a') },
            { id: 'ps-warning-color', txt: 'ps-warning-color-text', val: modePalette.warning_color || (currentMode === 'dark' ? '#fbbf24' : '#f59e0b') },
            { id: 'ps-danger-color', txt: 'ps-danger-color-text', val: modePalette.danger_color || (currentMode === 'dark' ? '#f87171' : '#ef4444') }
        ];

        colorMap.forEach(item => {
            const picker = document.getElementById(item.id);
            const txt = document.getElementById(item.txt);
            if (picker) picker.value = item.val;
            if (txt) txt.value = item.val;
        });

        if (brand.font_family) this._val('ps-font-family', brand.font_family);
        if (brand.font_size) this._val('ps-font-size', brand.font_size);
        if (brand.border_radius) this._val('ps-border-radius', brand.border_radius);
        if (brand.card_style) this._val('ps-card-style', brand.card_style);
        if (brand.button_style) this._val('ps-button-style', brand.button_style);
    },

    bindBrandingListeners() {
        const colorInputs = [
            { id: 'ps-primary-color', txtId: 'ps-primary-color-text' },
            { id: 'ps-secondary-color', txtId: 'ps-secondary-color-text' },
            { id: 'ps-accent-color', txtId: 'ps-accent-color-text' },
            { id: 'ps-success-color', txtId: 'ps-success-color-text' },
            { id: 'ps-warning-color', txtId: 'ps-warning-color-text' },
            { id: 'ps-danger-color', txtId: 'ps-danger-color-text' }
        ];

        colorInputs.forEach(item => {
            const picker = document.getElementById(item.id);
            const txt = document.getElementById(item.txtId);
            if (picker) {
                const handler = (e) => {
                    const val = e.target.value;
                    if (txt) txt.value = val;
                    this.applyLiveBranding(item.id, val);
                };
                picker.addEventListener('input', handler);
                picker.addEventListener('change', handler);
            }
        });

        ['ps-font-family', 'ps-font-size', 'ps-border-radius', 'ps-card-style', 'ps-button-style'].forEach(id => {
            const el = document.getElementById(id);
            if (el) {
                el.addEventListener('change', (e) => this.applyLiveBranding(id, e.target.value));
            }
        });
    },

    applyLiveBranding(key, val) {
        if (!key || !val) return;
        const currentMode = document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
        const brand = this._brandingData || this._initBrandingData(JSON.parse(localStorage.getItem('octaqube_branding_config') || '{}'));
        if (!brand[currentMode]) brand[currentMode] = { ...(window.DEFAULT_PALETTES?.[currentMode] || {}) };

        const colorKeyMap = {
            'ps-primary-color': 'primary_color',
            'ps-secondary-color': 'secondary_color',
            'ps-accent-color': 'accent_color',
            'ps-success-color': 'success_color',
            'ps-warning-color': 'warning_color',
            'ps-danger-color': 'danger_color'
        };

        if (colorKeyMap[key]) {
            brand[currentMode][colorKeyMap[key]] = val;
        } else {
            const globalKeyMap = {
                'ps-font-family': 'font_family',
                'ps-font-size': 'font_size',
                'ps-border-radius': 'border_radius',
                'ps-card-style': 'card_style',
                'ps-button-style': 'button_style'
            };
            if (globalKeyMap[key]) {
                brand[globalKeyMap[key]] = val;
            }
        }

        this._brandingData = brand;
        localStorage.setItem('octaqube_branding_config', JSON.stringify(brand));

        if (window.themeManager) {
            window.themeManager.applyModePalette(currentMode);
        }
    },

    resetCurrentModePalette() {
        const currentMode = document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
        const defaults = window.DEFAULT_PALETTES?.[currentMode] || {};
        const brand = this._brandingData || this._initBrandingData(JSON.parse(localStorage.getItem('octaqube_branding_config') || '{}'));
        brand[currentMode] = { ...defaults };
        this._brandingData = brand;
        localStorage.setItem('octaqube_branding_config', JSON.stringify(brand));

        if (window.themeManager) {
            window.themeManager.applyModePalette(currentMode);
        }
        this.syncBrandingInputs();
        OctaQube.toast(`Reset ${currentMode === 'dark' ? 'Dark' : 'Light'} Mode palette to system defaults!`, 'info');
    },

    uploadAsset(type) {
        const fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.accept = 'image/*';
        fileInput.onchange = (e) => {
            const file = e.target.files[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = (event) => {
                const dataUrl = event.target.result;
                const containerId = `ps-preview-${type}`;
                const container = document.getElementById(containerId);
                if (container) {
                    container.innerHTML = `<img src="${dataUrl}" style="max-height:60px; max-width:100%; object-fit:contain;" alt="${type}">`;
                }

                if (type === 'main-logo' || type === 'dark-logo') {
                    document.querySelectorAll('.sidebar-brand img, .navbar-brand img, .brand-logo img').forEach(img => {
                        img.src = dataUrl;
                    });
                } else if (type === 'favicon') {
                    let link = document.querySelector("link[rel*='icon']");
                    if (!link) {
                        link = document.createElement('link');
                        link.rel = 'shortcut icon';
                        document.getElementsByTagName('head')[0].appendChild(link);
                    }
                    link.href = dataUrl;
                }

                const assets = JSON.parse(localStorage.getItem('octaqube_brand_assets') || '{}');
                assets[type] = dataUrl;
                localStorage.setItem('octaqube_brand_assets', JSON.stringify(assets));

                OctaQube.toast(`Uploaded and updated ${type.replace('-', ' ')} in real time!`, 'success');
            };
            reader.readAsDataURL(file);
        };
        fileInput.click();
    },

    restoreSavedBranding() {
        const currentMode = document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
        const brand = this._brandingData || this._initBrandingData(JSON.parse(localStorage.getItem('octaqube_branding_config') || '{}'));
        if (window.themeManager) {
            window.themeManager.applyModePalette(currentMode);
        }
        this.syncBrandingInputs();

        const assets = JSON.parse(localStorage.getItem('octaqube_brand_assets') || '{}');
        Object.keys(assets).forEach(type => {
            const containerId = `ps-preview-${type}`;
            const container = document.getElementById(containerId);
            if (container) {
                container.innerHTML = `<img src="${assets[type]}" style="max-height:60px; max-width:100%; object-fit:contain;" alt="${type}">`;
            }
        });
    },

    async saveBranding() {
        try {
            const currentMode = document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
            const brand = this._brandingData || this._initBrandingData(JSON.parse(localStorage.getItem('octaqube_branding_config') || '{}'));
            if (!brand[currentMode]) brand[currentMode] = {};

            brand[currentMode].primary_color = this._getVal('ps-primary-color') || brand[currentMode].primary_color;
            brand[currentMode].secondary_color = this._getVal('ps-secondary-color') || brand[currentMode].secondary_color;
            brand[currentMode].accent_color = this._getVal('ps-accent-color') || brand[currentMode].accent_color;
            brand[currentMode].success_color = this._getVal('ps-success-color') || brand[currentMode].success_color;
            brand[currentMode].warning_color = this._getVal('ps-warning-color') || brand[currentMode].warning_color;
            brand[currentMode].danger_color = this._getVal('ps-danger-color') || brand[currentMode].danger_color;

            brand.font_family = this._getVal('ps-font-family') || brand.font_family;
            brand.font_size = this._getVal('ps-font-size') || brand.font_size;
            brand.border_radius = this._getVal('ps-border-radius') || brand.border_radius;
            brand.card_style = this._getVal('ps-card-style') || brand.card_style;
            brand.button_style = this._getVal('ps-button-style') || brand.button_style;
            brand.assets = JSON.parse(localStorage.getItem('octaqube_brand_assets') || '{}');

            this._brandingData = brand;
            localStorage.setItem('octaqube_branding_config', JSON.stringify(brand));

            if (window.themeManager) {
                window.themeManager.applyModePalette(currentMode);
            }

            // Save to backend
            const payload = {
                _category: 'Branding Settings',
                branding_settings: brand
            };
            await this._put('/settings', payload);

            OctaQube.toast(`Branding customizations saved for ${currentMode === 'dark' ? 'Dark' : 'Light'} Mode & applied live!`, 'success');
        } catch (e) { OctaQube.toast(e.message || 'Save failed.', 'error'); }
    },

    async saveOrganizations() {
        try {
            const payload = {
                _category: 'Organization & Tenant Settings',
                default_plan: this._getVal('ps-default-plan'),
                trial_period_days: parseInt(this._getVal('ps-trial-days') || 14),
                organizations_settings: {
                    default_plan: this._getVal('ps-default-plan'),
                    default_storage_limit: parseInt(this._getVal('ps-default-storage-limit') || 50),
                    max_organizations: parseInt(this._getVal('ps-max-organizations') || 500),
                    trial_days: parseInt(this._getVal('ps-trial-days') || 14)
                }
            };
            await this._put('/settings', payload);
            OctaQube.toast('Organization tenant governance settings saved.', 'success');
        } catch (e) { OctaQube.toast(e.message || 'Save failed.', 'error'); }
    },

    async saveBilling() {
        try {
            const payload = {
                _category: 'Plans & Billing Settings',
                billing_settings: {
                    razorpay_key: this._getVal('ps-razorpay-key'),
                    stripe_key: this._getVal('ps-stripe-key'),
                    tax_percent: parseFloat(this._getVal('ps-tax-percent') || 18),
                    grace_period: parseInt(this._getVal('ps-grace-period') || 7),
                    trial_period: parseInt(this._getVal('ps-trial-period') || 14),
                    coupon_code: this._getVal('ps-coupon-code'),
                    invoice_prefix: this._getVal('ps-invoice-prefix')
                }
            };
            await this._put('/settings', payload);
            OctaQube.toast('Plans & Billing rules saved.', 'success');
        } catch (e) { OctaQube.toast(e.message || 'Save failed.', 'error'); }
    },

    async saveModules() {
        try {
            const payload = {
                _category: 'Platform Module Licensing',
                modules_settings: {
                    updated_at: new Date().toISOString()
                }
            };
            await this._put('/settings', payload);
            OctaQube.toast('Module licenses updated.', 'success');
        } catch (e) { OctaQube.toast(e.message || 'Save failed.', 'error'); }
    },

    async saveCompliance() {
        try {
            const payload = {
                _category: 'Compliance & Standards Settings',
                compliance_settings: {
                    retention_period_days: parseInt(this._getVal('ps-retention-period') || 90),
                    log_encryption_enabled: true
                }
            };
            await this._put('/settings', payload);
            OctaQube.toast('Compliance standards saved.', 'success');
        } catch (e) { OctaQube.toast(e.message || 'Save failed.', 'error'); }
    },

    async saveSMS() {
        try {
            const payload = {
                _category: 'SMS Gateway Settings',
                sms_settings: {
                    provider: this._getVal('ps-sms-provider'),
                    sender_id: this._getVal('ps-sms-sender-id'),
                    account_sid: this._getVal('ps-sms-sid')
                }
            };
            await this._put('/settings', payload);
            OctaQube.toast('SMS gateway settings saved.', 'success');
        } catch (e) { OctaQube.toast(e.message || 'Save failed.', 'error'); }
    },

    async saveIntegrations() {
        try {
            const payload = {
                _category: 'Integrations Settings',
                integrations_settings: {
                    updated_at: new Date().toISOString()
                }
            };
            await this._put('/settings', payload);
            OctaQube.toast('Integrations configuration saved.', 'success');
        } catch (e) { OctaQube.toast(e.message || 'Save failed.', 'error'); }
    },

    async saveFeatureFlags() {
        try {
            if (this._data && this._data.feature_flags) {
                Object.keys(this._data.feature_flags).forEach(key => {
                    const el = document.getElementById(`ff-${key}`);
                    if (el) {
                        this._data.feature_flags[key].enabled = el.checked;
                    }
                });
            }
            const payload = {
                _category: 'Feature Flags Settings',
                feature_flags: this._data.feature_flags || {}
            };
            await this._put('/settings', payload);
            OctaQube.toast('Feature flags saved.', 'success');
        } catch (e) { OctaQube.toast(e.message || 'Save failed.', 'error'); }
    },

    async saveDeveloper() {
        try {
            const payload = {
                _category: 'Developer Settings',
                developer_settings: {
                    log_level: 'INFO',
                    query_monitor: true
                }
            };
            await this._put('/settings', payload);
            OctaQube.toast('Developer diagnostics saved.', 'success');
        } catch (e) { OctaQube.toast(e.message || 'Save failed.', 'error'); }
    },

    async saveAuditLogs() {
        try {
            const payload = {
                _category: 'Audit Logs Policy',
                audit_logs_settings: {
                    retention_days: parseInt(this._getVal('ps-retention-period') || 90)
                }
            };
            await this._put('/settings', payload);
            OctaQube.toast('Audit log policy saved.', 'success');
        } catch (e) { OctaQube.toast(e.message || 'Save failed.', 'error'); }
    },

    async loadSystemHealth() {
        try {
            const res = await this._get('/health');
            if (res && res.status === 'success' && res.data) {
                const h = res.data;
                this._setInner('ps-sys-health-db', `<i data-lucide="check-circle" class="me-1 text-success" style="width:15px;"></i> ${h.db_status} (${h.db_version})`);
                this._setInner('ps-sys-health-redis', `<i data-lucide="check-circle" class="me-1 text-success" style="width:15px;"></i> ${h.redis_status} (${h.redis_version})`);
                this._setInner('ps-sys-health-workers', `<i data-lucide="check-circle" class="me-1 text-success" style="width:15px;"></i> ${h.worker_status}`);
                this._setInner('ps-sys-health-cpu', `${h.cpu_load}`);
                this._setInner('ps-sys-health-ram', `${h.ram_memory}`);
                this._setInner('ps-sys-health-disk', `${h.disk_usage}`);

                // Top dashboard KPI cards
                if (h.uptime) this._setInner('ps-kpi-uptime', h.uptime);
                if (h.api_latency) this._setInner('ps-kpi-api-health', h.api_latency);
                if (h.disk_used_gb) this._setInner('ps-kpi-storage', `${h.disk_used_gb} GB`);

                if (window.lucide && typeof window.lucide.createIcons === 'function') {
                    window.lucide.createIcons();
                }
            }
            if (window.OctaQube) OctaQube.toast('Real-time infrastructure metrics refreshed.', 'success');
        } catch (e) {
            console.error('Failed to load system health', e);
            if (window.OctaQube) OctaQube.toast('Failed to refresh system health.', 'error');
        }
    },

    async saveSystemHealth() {
        try {
            await this.loadSystemHealth();
        } catch (e) { OctaQube.toast(e.message || 'Refresh failed.', 'error'); }
    },

    async saveAbout() {
        try {
            OctaQube.toast('About OctaQube Enterprise OS specifications up to date.', 'info');
        } catch (e) { OctaQube.toast(e.message || 'Save failed.', 'error'); }
    },

    renderFeatureFlags(flags) {
        const container = document.getElementById('ps-feature-flags-list');
        if (!container) return;
        container.innerHTML = Object.entries(flags).map(([key, flag]) => `
            <div class="h-stack justify-content-between p-3 glass-card mb-2">
                <div class="h-stack gap-3 align-items-center">
                    <div class="v-stack">
                        <div class="h-stack gap-2 align-items-center">
                            <span class="fw-bold ds-text-main">${flag.name}</span>
                            ${flag.is_beta ? '<span class="badge bg-warning-subtle text-warning">BETA</span>' : ''}
                            ${flag.is_experimental ? '<span class="badge bg-danger-subtle text-danger">EXPERIMENTAL</span>' : ''}
                        </div>
                        <span class="text-xs ds-text-secondary">${key}</span>
                    </div>
                </div>
                <div class="h-stack gap-3 align-items-center">
                    <div class="form-check form-switch mb-0">
                        <input class="form-check-input" type="checkbox" id="ff-${key}" ${flag.enabled ? 'checked' : ''}
                               onchange="PlatformSettings.toggleFlag('${key}', this.checked)">
                    </div>
                </div>
            </div>
        `).join('');
    },

    async toggleFlag(key, enabled) {
        try {
            const res = await this._put(`/settings/feature-flags/${key}`, { enabled });
            OctaQube.toast(res.message || `Feature flag '${key}' updated successfully.`, 'success');
            if (this._data && this._data.feature_flags && this._data.feature_flags[key]) {
                this._data.feature_flags[key].enabled = enabled;
            }
        } catch (e) {
            OctaQube.toast(e.message || 'Toggle failed.', 'error');
            const el = document.getElementById(`ff-${key}`);
            if (el) el.checked = !enabled; // revert state
        }
    },

    async saveMaintenance() {
        try {
            const enabled = this._getChk('ps-maintenance-mode');
            const payload = {
                _category: 'Maintenance Mode Settings',
                maintenance_mode: enabled,
                maintenance_settings: {
                    maintenance_message: this._getVal('ps-maintenance-msg'),
                    estimated_completion: this._getVal('ps-maintenance-eta'),
                    enabled
                }
            };
            await this._put('/settings', payload);
            OctaQube.toast(enabled ? '⚠️ Maintenance mode is now ACTIVE.' : 'Maintenance mode disabled.', enabled ? 'warning' : 'success');
        } catch (e) { OctaQube.toast(e.message || 'Save failed.', 'error'); }
    },

    // ──────────────────────────────────────────────────────────
    // DOM HELPERS
    // ──────────────────────────────────────────────────────────
    // DOM HELPERS WITH FALLBACK LOOKUPS
    // ──────────────────────────────────────────────────────────

    _find(id) {
        if (!id) return null;
        let el = document.getElementById(id);
        if (!el && id.startsWith('ps-')) el = document.getElementById(id.replace('ps-', ''));
        if (!el && !id.startsWith('ps-')) el = document.getElementById(`ps-${id}`);
        return el;
    },

    _val(id, val) {
        const el = this._find(id);
        if (el && val !== undefined && val !== null) el.value = val;
    },

    _getVal(id) {
        const el = this._find(id);
        return el ? el.value : '';
    },

    _chk(id, val) {
        const el = this._find(id);
        if (el && val !== undefined) el.checked = !!val;
    },

    _getChk(id) {
        const el = this._find(id);
        return el ? el.checked : false;
    },

    _setInner(id, val) {
        const el = this._find(id);
        if (el) el.innerHTML = val ?? '—';
    },

    // === Footer Pages CMS Methods ===
    loadFooterPages: function(savedPages) {
        const stored = localStorage.getItem('ps-landing-cms-pages');
        let data = (savedPages && Object.keys(savedPages).length > 0)
            ? savedPages
            : (stored ? JSON.parse(stored) : {
            product: [
                { id: 'features', title: 'Features', link: '#features', content: '' },
                { id: 'pricing', title: 'Pricing', link: '#pricing', content: '' },
                { id: 'workflows', title: 'Workflows', link: '#how-it-works', content: '' },
                { id: 'free-trial', title: 'Free Trial', link: 'register-org.html', content: '' }
            ],
            resources: [
                { id: 'documentation', title: 'Documentation', link: 'page.html?id=documentation', content: '<h1>Documentation</h1><p>Comprehensive guide to OctaQube Enterprise platform API, setup, and governance.</p>' },
                { id: 'api-reference', title: 'API Reference', link: 'page.html?id=api-reference', content: '<h1>API Reference</h1><p>Explore REST endpoints, JWT headers, rate-limiting, and webhook payloads.</p>' },
                { id: 'support-center', title: 'Support Center', link: 'page.html?id=support-center', content: '<h1>Support Center</h1><p>Contact 24/7 technical support, submit tickets, and browse knowledgebase.</p>' },
                { id: 'community', title: 'Community', link: 'page.html?id=community', content: '<h1>Community</h1><p>Join the OctaQube developer and quality management community.</p>' }
            ],
            company: [
                { id: 'about-us', title: 'About Us', link: 'page.html?id=about-us', content: '<h1>About Us</h1><p>Learn about our mission to standardize enterprise quality control globally.</p>' },
                { id: 'careers', title: 'Careers', link: 'page.html?id=careers', content: '<h1>Careers</h1><p>We are hiring! Join our distributed engineering and customer success teams.</p>' },
                { id: 'contact-sales', title: 'Contact Sales', link: 'page.html?id=contact-sales', content: '<h1>Contact Sales</h1><p>Reach out for custom SLA enterprise contracts, deployment on-premise, or SOC2 reports.</p>' },
                { id: 'global-partners', title: 'Global Partners', link: 'page.html?id=global-partners', content: '<h1>Global Partners</h1><p>Discover authorized consulting and implementation partners worldwide.</p>' }
            ],
            legal: [
                { id: 'privacy-policy', title: 'Privacy Policy', link: 'page.html?id=privacy-policy', content: '<h1>Privacy Policy</h1><p>Your privacy is important to us. Learn about data collection and protection.</p>' },
                { id: 'terms-of-service', title: 'Terms of Service', link: 'page.html?id=terms-of-service', content: '<h1>Terms of Service</h1><p>Read the terms and conditions governing the use of OctaQube Enterprise OS.</p>' },
                { id: 'security', title: 'Security', link: 'page.html?id=security', content: '<h1>Security</h1><p>Detailed breakdown of SOC2 Type II, ISO 27001, AES-256 encryption, and TLS 1.3 standards.</p>' },
                { id: 'gdpr', title: 'GDPR', link: 'page.html?id=gdpr', content: '<h1>GDPR Compliance</h1><p>Information on EU data protection rights, data processor agreements, and DPO contacts.</p>' }
            ]
        });
        this.footerPagesData = data;
        localStorage.setItem('ps-landing-cms-pages', JSON.stringify(this.footerPagesData));
        this.renderFooterPagesList();
    },

    renderFooterPagesList: function() {
        const columns = ['product', 'resources', 'company', 'legal'];
        columns.forEach(col => {
            const container = document.getElementById('ps-cms-pages-' + col);
            if (!container) return;
            container.innerHTML = '';
            
            const pages = this.footerPagesData[col] || [];
            pages.forEach((page, index) => {
                const el = document.createElement('div');
                el.className = 'd-flex align-items-center justify-content-between p-2 rounded border';
                el.style.backgroundColor = 'var(--ds-bg-surface)';
                el.style.borderColor = 'var(--ds-border-color)!important';
                
                el.innerHTML = `
                    <span class="text-xs fw-semibold text-main text-truncate" style="max-width: 120px;">${page.title}</span>
                    <div class="d-flex gap-1">
                        <button type="button" class="btn btn-sm btn-light p-1" onclick="PlatformSettings.editFooterPage('${col}', ${index})" title="Edit Content">
                            <i data-lucide="edit-3" style="width:12px; height:12px;"></i>
                        </button>
                        <button type="button" class="btn btn-sm btn-light p-1 text-danger" onclick="PlatformSettings.deleteFooterPage('${col}', ${index})" title="Delete">
                            <i data-lucide="trash-2" style="width:12px; height:12px;"></i>
                        </button>
                    </div>
                `;
                container.appendChild(el);
            });
        });
        if (window.lucide) {
            lucide.createIcons();
        }
    },

    openFooterPageModal: function() {
        document.getElementById('footer-page-form').reset();
        document.getElementById('fp-id').value = '';
        const modalEl = document.getElementById('footerPageModal');
        const modal = new bootstrap.Modal(modalEl);
        modal.show();
    },

    editFooterPage: function(col, index) {
        const page = this.footerPagesData[col][index];
        document.getElementById('fp-id').value = `${col}:${index}`;
        document.getElementById('fp-title').value = page.title;
        document.getElementById('fp-column').value = col;
        document.getElementById('fp-link').value = (page.link && page.link.startsWith('page.html')) ? '' : (page.link || '');
        document.getElementById('fp-content').value = page.content || '';
        
        const modalEl = document.getElementById('footerPageModal');
        const modal = new bootstrap.Modal(modalEl);
        modal.show();
    },

    deleteFooterPage: function(col, index) {
        if (confirm('Are you sure you want to delete this footer link?')) {
            this.footerPagesData[col].splice(index, 1);
            localStorage.setItem('ps-landing-cms-pages', JSON.stringify(this.footerPagesData));
            this.renderFooterPagesList();
            this.saveLandingCMS();
            if (window.OctaQube) OctaQube.toast('Link deleted successfully.', 'success');
        }
    },

    saveFooterPage: async function() {
        const idVal = document.getElementById('fp-id').value;
        const title = document.getElementById('fp-title').value.trim();
        const col = document.getElementById('fp-column').value;
        const linkOverride = document.getElementById('fp-link').value.trim();
        const content = document.getElementById('fp-content').value.trim();
        
        if (!title) {
            alert('Please enter a link title.');
            return;
        }

        const linkId = title.toLowerCase().replace(/[^a-z0-9]+/g, '-');
        let finalLink = `page.html?id=${linkId}`;

        if (linkOverride) {
            if (/^(https?:\/\/|\/|#)/i.test(linkOverride)) {
                finalLink = linkOverride;
            } else {
                finalLink = `https://${linkOverride}`;
            }
        }

        const newPage = {
            id: linkId,
            title: title,
            link: finalLink,
            content: content
        };

        if (idVal) {
            // Editing existing
            const parts = idVal.split(':');
            const oldCol = parts[0];
            const oldIndex = parseInt(parts[1], 10);
            
            if (oldCol === col) {
                this.footerPagesData[col][oldIndex] = newPage;
            } else {
                this.footerPagesData[oldCol].splice(oldIndex, 1);
                this.footerPagesData[col].push(newPage);
            }
        } else {
            // Creating new
            if (!this.footerPagesData[col]) this.footerPagesData[col] = [];
            this.footerPagesData[col].push(newPage);
        }

        localStorage.setItem('ps-landing-cms-pages', JSON.stringify(this.footerPagesData));
        this.renderFooterPagesList();
        await this.saveLandingCMS();
        
        const modalEl = document.getElementById('footerPageModal');
        const modal = bootstrap.Modal.getInstance(modalEl);
        if (modal) modal.hide();
        
        if (window.OctaQube) OctaQube.toast('Footer link & page content saved successfully.', 'success');
    },

    // ──────────────────────────────────────────────────────────
    // SUPER ADMIN LOGINS & CREDENTIALS
    // ──────────────────────────────────────────────────────────

    _adminLoginsPage: 1,
    _adminLoginsPerPage: 5,
    _adminLoginsAll: [],

    async loadAdminLogins() {
        try {
            const res = await api.get('/super-admin/admin-logins');
            if (res.status === 'success') {
                this._adminLoginsAll = res.data || [];
                this.renderAdminLogins();
            }
        } catch (e) { console.error('Failed to load super admin logins:', e); }
    },

    renderAdminLogins() {
        const tbody = document.getElementById('adminLoginsTableBody');
        const ownEmailInput = document.getElementById('ownAdminNewEmail');
        const countBadge = document.getElementById('adminAccountsCountBadge');
        const infoEl = document.getElementById('adminLoginsPaginationInfo');
        const controlsEl = document.getElementById('adminLoginsPaginationControls');

        const admins = this._adminLoginsAll || [];
        if (countBadge) countBadge.textContent = `${admins.length} Account${admins.length === 1 ? '' : 's'}`;

        const me = JSON.parse(sessionStorage.getItem('user') || '{}');
        const activeAdmin = admins.find(a => String(a.id) === String(me.id));
        if (ownEmailInput && activeAdmin) {
            ownEmailInput.value = activeAdmin.email;
        } else if (ownEmailInput && me.email) {
            ownEmailInput.value = me.email;
        } else if (ownEmailInput && admins.length > 0) {
            ownEmailInput.value = admins[0].email;
        }

        if (!tbody) return;

        if (admins.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" class="text-center py-4 text-muted">No Super Admin accounts found.</td></tr>`;
            if (infoEl) infoEl.textContent = 'Showing 0 of 0 accounts';
            if (controlsEl) controlsEl.innerHTML = '';
            return;
        }

        const perPage = this._adminLoginsPerPage || 5;
        const totalPages = Math.max(1, Math.ceil(admins.length / perPage));
        this._adminLoginsPage = Math.min(Math.max(1, this._adminLoginsPage || 1), totalPages);
        const currentPage = this._adminLoginsPage;

        const start = (currentPage - 1) * perPage;
        const pageAdmins = admins.slice(start, start + perPage);

        tbody.innerHTML = pageAdmins.map(a => {
            const isMe = me.id == a.id || me.email === a.email;
            const badgeClass = a.sub_role === 'Owner' ? 'bg-primary-subtle text-primary' : 'bg-info-subtle text-info';

            return `
                <tr>
                    <td>
                        <div class="d-flex align-items-center gap-2">
                            <div class="rounded-circle bg-primary-subtle text-primary fw-bold d-flex align-items-center justify-content-center" style="width:28px;height:28px;font-size:11px;">
                                ${(a.username || 'A').charAt(0).toUpperCase()}
                            </div>
                            <div>
                                <div class="fw-semibold text-main">${a.username} ${isMe ? '<span class="badge bg-success-subtle text-success ms-1" style="font-size:9px;">You</span>' : ''}</div>
                                <div class="text-xxs text-secondary">ID #${a.id}</div>
                            </div>
                        </div>
                    </td>
                    <td class="font-monospace text-xs">${a.email}</td>
                    <td><span class="badge ${badgeClass} text-xxs">${a.sub_role || 'Owner'}</span></td>
                    <td><span class="badge bg-success-subtle text-success text-xxs">${a.status}</span></td>
                    <td class="text-secondary text-xxs">${a.created_at ? a.created_at.slice(0, 10) : '—'}</td>
                    <td class="text-end">
                        <div class="dropdown d-inline-block">
                            <button class="ds-btn ds-btn-secondary ds-btn-xs px-2 py-1" type="button" data-bs-toggle="dropdown" aria-expanded="false" title="Actions">
                                <i data-lucide="more-vertical" style="width:14px;height:14px;"></i>
                            </button>
                            <ul class="dropdown-menu dropdown-menu-end shadow-sm border-0 text-xs" style="border-radius:10px; min-width: 170px;">
                                <li>
                                    <a class="dropdown-item d-flex align-items-center gap-2 py-2 text-primary" href="javascript:void(0)" onclick="PlatformSettings.openEditAdminModal(${a.id}, '${(a.username || '').replace(/'/g, "\\'")}', '${(a.email || '').replace(/'/g, "\\'")}', '${(a.sub_role || 'Owner').replace(/'/g, "\\'")}')">
                                        <i data-lucide="edit-3" style="width:13px;height:13px;"></i> Edit Role & Account
                                    </a>
                                </li>
                                ${!isMe ? `
                                    <li><hr class="dropdown-divider my-1"></li>
                                    <li>
                                        <a class="dropdown-item d-flex align-items-center gap-2 py-2 text-danger" href="javascript:void(0)" onclick="PlatformSettings.deleteAdminAccount(${a.id}, '${(a.username || '').replace(/'/g, "\\'")}')">
                                            <i data-lucide="trash-2" style="width:13px;height:13px;"></i> Remove Account
                                        </a>
                                    </li>
                                ` : `
                                    <li><hr class="dropdown-divider my-1"></li>
                                    <li><span class="dropdown-item-text text-xxs text-muted py-1"><i data-lucide="user-check" class="me-1" style="width:12px;"></i> Active Session (You)</span></li>
                                `}
                            </ul>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');

        if (window.lucide) lucide.createIcons();

        // Render pagination info and controls
        const endDisplay = Math.min(start + perPage, admins.length);
        const startDisplay = admins.length > 0 ? start + 1 : 0;
        if (infoEl) infoEl.textContent = `Showing ${startDisplay} to ${endDisplay} of ${admins.length} accounts`;

        if (controlsEl) {
            if (window.SuperAdmin && typeof window.SuperAdmin.buildFourPagePagination === 'function') {
                controlsEl.innerHTML = window.SuperAdmin.buildFourPagePagination(currentPage, totalPages, 'PlatformSettings.changeAdminLoginsPage');
            } else {
                let btnHtml = '';
                btnHtml += `<button class="ds-btn ds-btn-secondary ds-btn-sm ${currentPage <= 1 ? 'disabled' : ''}" ${currentPage <= 1 ? 'disabled' : ''} onclick="PlatformSettings.changeAdminLoginsPage(${currentPage - 1})">Prev</button>`;
                for (let i = 1; i <= totalPages; i++) {
                    const isAct = i === currentPage ? 'ds-btn-primary' : 'ds-btn-secondary';
                    btnHtml += `<button class="ds-btn ${isAct} ds-btn-sm px-3" onclick="PlatformSettings.changeAdminLoginsPage(${i})">${i}</button>`;
                }
                btnHtml += `<button class="ds-btn ds-btn-secondary ds-btn-sm ${currentPage >= totalPages ? 'disabled' : ''}" ${currentPage >= totalPages ? 'disabled' : ''} onclick="PlatformSettings.changeAdminLoginsPage(${currentPage + 1})">Next</button>`;
                controlsEl.innerHTML = btnHtml;
            }
        }
    },

    changeAdminLoginsPage(p) {
        this._adminLoginsPage = p;
        this.renderAdminLogins();
    },

    adminLoginsSetPerPage(val) {
        this._adminLoginsPerPage = parseInt(val) || 5;
        this._adminLoginsPage = 1;
        this.renderAdminLogins();
    },

    async updateOwnCredentials() {
        const form = document.getElementById('ownCredentialsForm');
        const submitBtn = form ? form.querySelector('button[type="submit"]') : null;

        const newEmail = document.getElementById('ownAdminNewEmail')?.value?.trim();
        const currentPassword = document.getElementById('ownAdminCurrentPassword')?.value?.trim();
        const newPassword = document.getElementById('ownAdminNewPassword')?.value?.trim();
        const confirmPassword = document.getElementById('ownAdminConfirmPassword')?.value?.trim();

        try {
            if (!currentPassword) {
                OctaQube.toast('Current password is required to confirm changes.', 'warning');
                return;
            }

            if (newEmail && !this.validateEmail(newEmail)) {
                OctaQube.toast('Please enter a valid email address in format username@domain.extension (e.g. name@domain.com).', 'warning');
                const emailInput = document.getElementById('ownAdminNewEmail');
                if (emailInput) {
                    emailInput.classList.add('is-invalid');
                    emailInput.focus();
                }
                return;
            }

            if (newPassword) {
                if (newPassword.length < 6) {
                    OctaQube.toast('New password must be at least 6 characters long.', 'warning');
                    return;
                }
                if (newPassword !== confirmPassword) {
                    OctaQube.toast('New password and confirm password do not match.', 'error');
                    return;
                }
            }

            const res = await api.put('/super-admin/admin-logins/update-credentials', {
                new_email: newEmail,
                current_password: currentPassword,
                new_password: newPassword || undefined
            }, { button: submitBtn });

            if (res && res.status === 'success') {
                OctaQube.toast(res.message || 'Super Admin credentials updated successfully!', 'success');
                
                // Update session memory
                const userObj = JSON.parse(sessionStorage.getItem('user') || '{}');
                if (newEmail) userObj.email = newEmail;
                sessionStorage.setItem('user', JSON.stringify(userObj));

                // Clear password fields
                document.getElementById('ownAdminCurrentPassword').value = '';
                document.getElementById('ownAdminNewPassword').value = '';
                document.getElementById('ownAdminConfirmPassword').value = '';

                this.loadAdminLogins();
            }
        } catch (e) {
            OctaQube.toast(e.message || 'Failed to update credentials.', 'error');
        } finally {
            if (submitBtn && window.ActionLock) {
                window.ActionLock.unlockButton(submitBtn);
            }
        }
    },

    openAddAdminModal() {
        document.getElementById('addAdminForm')?.reset();
        const modalEl = document.getElementById('addSuperAdminModal');
        if (modalEl) {
            const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
            modal.show();
        }
    },

    togglePasswordVisibility(inputId, btn) {
        const input = document.getElementById(inputId);
        if (!input) return;
        if (input.type === 'password') {
            input.type = 'text';
            btn.innerHTML = '<i data-lucide="eye-off" style="width:15px;height:15px;"></i>';
        } else {
            input.type = 'password';
            btn.innerHTML = '<i data-lucide="eye" style="width:15px;height:15px;"></i>';
        }
        if (window.lucide) lucide.createIcons({ container: btn });
    },

    validateEmail(email) {
        if (!email) return false;
        const re = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/;
        return re.test(String(email).trim());
    },

    validateEmailInput(inputEl) {
        if (!inputEl) return;
        const val = inputEl.value.trim();
        const errElId = inputEl.id === 'newAdminEmail' ? 'newAdminEmailError' : (inputEl.id === 'editAdminEmail' ? 'editAdminEmailError' : inputEl.id + 'Error');
        const errEl = document.getElementById(errElId);

        if (!val) {
            inputEl.classList.remove('is-invalid', 'is-valid');
            if (errEl) errEl.style.display = 'none';
            return;
        }

        const isValid = this.validateEmail(val);
        if (!isValid) {
            inputEl.classList.add('is-invalid');
            inputEl.classList.remove('is-valid');
            if (errEl) {
                errEl.textContent = 'Please enter a valid email address in format username@domain.extension (e.g. admin@octaqube.com)';
                errEl.style.display = 'block';
            }
        } else {
            inputEl.classList.remove('is-invalid');
            inputEl.classList.add('is-valid');
            if (errEl) errEl.style.display = 'none';
        }
    },

    async createAdminAccount() {
        const username = document.getElementById('newAdminUsername')?.value?.trim();
        const email = document.getElementById('newAdminEmail')?.value?.trim();
        const password = document.getElementById('newAdminPassword')?.value?.trim();
        const confirmPassword = document.getElementById('newAdminConfirmPassword')?.value?.trim();
        const subRole = document.getElementById('newAdminSubRole')?.value;

        if (!username || !email || !password) {
            OctaQube.toast('Username, email, and password are required.', 'warning');
            return;
        }

        if (!this.validateEmail(email)) {
            OctaQube.toast('Please enter a valid email address in format username@domain.extension (e.g. name@domain.com).', 'warning');
            const emailInput = document.getElementById('newAdminEmail');
            if (emailInput) {
                emailInput.classList.add('is-invalid');
                emailInput.focus();
            }
            return;
        }

        if (password.length < 6) {
            OctaQube.toast('Password must be at least 6 characters.', 'warning');
            return;
        }

        if (password !== confirmPassword) {
            OctaQube.toast('Passwords do not match.', 'error');
            return;
        }

        try {
            const res = await api.post('/super-admin/admin-logins', {
                username,
                email,
                password,
                sub_role: subRole
            });

            if (res.status === 'success') {
                OctaQube.toast(res.message || 'New Super Admin created successfully!', 'success');

                const modalEl = document.getElementById('addSuperAdminModal');
                const modal = bootstrap.Modal.getInstance(modalEl);
                if (modal) modal.hide();

                this.loadAdminLogins();
            }
        } catch (e) {
            OctaQube.toast(e.message || 'Failed to create Super Admin account.', 'error');
        }
    },

    async deleteAdminAccount(adminId, username) {
        if (!confirm(`Are you sure you want to remove Super Admin account "${username}"?`)) return;

        try {
            const res = await api.delete(`/super-admin/admin-logins/${adminId}`);
            if (res.status === 'success') {
                OctaQube.toast(res.message || 'Admin account removed.', 'success');
                this.loadAdminLogins();
            }
        } catch (e) {
            OctaQube.toast(e.message || 'Failed to remove admin account.', 'error');
        }
    },

    openEditAdminModal(adminId, username, email, subRole) {
        if (document.getElementById('editAdminId')) document.getElementById('editAdminId').value = adminId;
        if (document.getElementById('editAdminUsername')) document.getElementById('editAdminUsername').value = username;
        if (document.getElementById('editAdminEmail')) document.getElementById('editAdminEmail').value = email;
        if (document.getElementById('editAdminSubRole')) document.getElementById('editAdminSubRole').value = subRole;
        if (document.getElementById('editAdminPassword')) document.getElementById('editAdminPassword').value = '';

        const modalEl = document.getElementById('editSuperAdminModal');
        if (modalEl) {
            const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
            modal.show();
        }
    },

    async saveAdminAccount() {
        const adminId = document.getElementById('editAdminId')?.value;
        const email = document.getElementById('editAdminEmail')?.value?.trim();
        const subRole = document.getElementById('editAdminSubRole')?.value;
        const password = document.getElementById('editAdminPassword')?.value?.trim();

        if (!adminId) {
            OctaQube.toast('Invalid admin account selected.', 'error');
            return;
        }

        if (email && !this.validateEmail(email)) {
            OctaQube.toast('Please enter a valid email address in format username@domain.extension (e.g. name@domain.com).', 'warning');
            const emailInput = document.getElementById('editAdminEmail');
            if (emailInput) {
                emailInput.classList.add('is-invalid');
                emailInput.focus();
            }
            return;
        }

        if (password && password.length < 6) {
            OctaQube.toast('Password must be at least 6 characters.', 'warning');
            return;
        }

        try {
            const payload = { sub_role: subRole };
            if (email) payload.email = email;
            if (password) payload.password = password;

            const res = await api.put(`/super-admin/admin-logins/${adminId}`, payload);
            if (res.status === 'success') {
                OctaQube.toast(res.message || 'Super Admin account updated successfully!', 'success');

                const modalEl = document.getElementById('editSuperAdminModal');
                const modal = bootstrap.Modal.getInstance(modalEl);
                if (modal) modal.hide();

                this.loadAdminLogins();
            }
        } catch (e) {
            OctaQube.toast(e.message || 'Failed to update Super Admin account.', 'error');
        }
    }
};
window.PlatformSettings = PlatformSettings;

document.addEventListener('DOMContentLoaded', () => {
    try {
        if (typeof settingsManager !== 'undefined' && settingsManager && settingsManager.init) {
            const origFn = settingsManager.init.bind(settingsManager);
            settingsManager.init = async function () {
                await origFn();
                await PlatformSettings.init();
            };
        } else if (window.location.pathname.includes('super-admin.html')) {
            PlatformSettings.init();
        }
    } catch (err) {
        console.warn('[PlatformSettings] Init fallback:', err);
    }
});
