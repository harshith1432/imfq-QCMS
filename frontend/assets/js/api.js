const API_BASE = '/api';

// Auto-load action locking engine if not present
if (typeof window !== 'undefined' && !window.ActionLock && typeof document !== 'undefined') {
    const s = document.createElement('script');
    s.src = '/assets/js/action-lock.js';
    document.head.appendChild(s);
}

const api = {
    baseUrl: API_BASE,
    inFlightRequests: new Map(), // Deduplication map for active HTTP requests

    get token() {
        const t = sessionStorage.getItem('token')
            || localStorage.getItem('token')
            || localStorage.getItem('access_token')
            || sessionStorage.getItem('access_token')
            || '';
        if (t) return t;
        // Fallback: if running inside an iframe, try to read token from parent window (same origin)
        try {
            if (window.parent && window.parent !== window) {
                return window.parent.sessionStorage.getItem('token')
                    || window.parent.localStorage.getItem('token')
                    || window.parent.localStorage.getItem('access_token')
                    || window.parent.sessionStorage.getItem('access_token')
                    || '';
            }
        } catch (_) {}
        return '';
    },

    generateIdempotencyKey() {
        return 'idempotency-' + Date.now() + '-' + Math.random().toString(36).substring(2, 11);
    },

    async request(endpoint, options = {}) {
        const method = (options.method || 'GET').toUpperCase();
        const isWriteMethod = ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method);

        // Global Feature Engine Module Access Check across all 144 modules
        if (window.QCMS_MODULE_MAP && window.FeatureEngine && !endpoint.includes('/feature-engine/')) {
            const moduleCode = window.QCMS_MODULE_MAP.findByRoute(endpoint);
            if (moduleCode && FeatureEngine.isEnabled(moduleCode) === false) {
                console.warn(`[API Guard] Blocking request to disabled module: ${moduleCode}`);
                FeatureEngine.showDisabledModuleNotice(moduleCode);
                const err = new Error(`Module '${moduleCode}' is disabled for your organization.`);
                err.isModuleDisabled = true;
                throw err;
            }
        }

        // 1. Compute Request Key for deduplication
        let bodyKey = '';
        if (options.body) {
            try {
                bodyKey = typeof options.body === 'string' ? options.body : JSON.stringify(options.body);
            } catch (_) {}
        }
        const requestKey = `${method}:${endpoint}:${bodyKey}`;

        // 2. Client-Side Request Deduplication (Return pending promise if identical request is in flight)
        if (isWriteMethod && this.inFlightRequests.has(requestKey)) {
            console.warn(`[API Deduplication] Blocking duplicate write request: ${requestKey}`);
            return this.inFlightRequests.get(requestKey);
        }

        // 3. Lock associated button if provided
        const targetBtn = options.button || options.lockElement;
        if (targetBtn && window.ActionLock) {
            if (!window.ActionLock.isLocked(targetBtn)) {
                window.ActionLock.lockButton(targetBtn, options.loadingText);
            }
        }

        const requestPromise = (async () => {
            const token = this.token;
            const headers = { ...options.headers };

            // Attach Idempotency-Key for write operations
            if (isWriteMethod && !headers['X-Idempotency-Key']) {
                headers['X-Idempotency-Key'] = options.idempotencyKey || this.generateIdempotencyKey();
            }

            // Only set Content-Type if not provided and not FormData
            if (!headers['Content-Type'] && !(options.body instanceof FormData)) {
                headers['Content-Type'] = 'application/json';
            }

            if (token) {
                headers['Authorization'] = `Bearer ${token}`;
            }

            // Support AbortController and default timeout of 60 seconds (60000ms) for cloud serverless cold-starts
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), options.timeout || 60000);

            try {
                const response = await fetch(`${API_BASE}${endpoint}`, {
                    ...options,
                    headers,
                    signal: controller.signal
                });
                clearTimeout(timeoutId);

                if (response.status === 401) {
                    const isLogin = endpoint.includes('/auth/login') || window.location.pathname.includes('login.html');
                    // Match only super-admin.html portal page (not standard org admin pages under /admin/)
                    const isSuperAdminPortal = window.location.pathname.includes('super-admin.html');
                    const isInsideSuperAdminIframe = (() => {
                        try {
                            return window.parent && window.parent !== window
                                && window.parent.location.pathname.includes('super-admin.html');
                        } catch (_) { return false; }
                    })();
                    if (!isLogin) {
                        if (isSuperAdminPortal || isInsideSuperAdminIframe) {
                            console.warn('[API] 401 on super-admin portal for:', endpoint);
                            return null;
                        }
                        console.warn('[API] 401 Unauthorized for:', endpoint, '— redirecting to login.');
                        sessionStorage.removeItem('token');
                        localStorage.removeItem('token');
                        if (!window.location.pathname.includes('login.html')) {
                            window.location.href = '/auth/login.html';
                        }
                        return null;
                    }
                    if (isLogin) {
                        const data = await response.json().catch(() => ({}));
                        throw new Error(data.msg || data.message || 'Invalid credentials');
                    }
                }

                const data = await response.json().catch(() => ({}));

                if (response.status === 403 && (data.error_code === 'ORGANIZATION_SUSPENDED' || data.status === 'suspended')) {
                    if (typeof window.showSuspendedOrganizationScreen === 'function') {
                        window.showSuspendedOrganizationScreen();
                    }
                }

                if ((response.status === 403 || response.status === 503) && (data.code === 'MODULE_UNDER_MAINTENANCE' || (data.message && data.message.includes('under maintenance')))) {
                    if (window.QCMS && typeof window.QCMS.toast === 'function') {
                        window.QCMS.toast('Currently this feature is under maintenance.', 'warning');
                    } else if (typeof window.api?.showNotification === 'function') {
                        window.api.showNotification('Currently this feature is under maintenance.', 'warning');
                    }
                }

                if (!response.ok) {
                    const error = new Error(data.message || data.msg || data.error || 'API Error');
                    error.errors = data.errors || [];
                    error.status = response.status;
                    error.error_code = data.error_code;
                    throw error;
                }
                return data;
            } catch (err) {
                clearTimeout(timeoutId);
                if (err.name === 'AbortError') {
                    const timeoutErr = new Error('Request timeout. Please check your connection.');
                    timeoutErr.isTimeout = true;
                    throw timeoutErr;
                }
                throw err;
            } finally {
                if (isWriteMethod) {
                    this.inFlightRequests.delete(requestKey);
                }
                if (targetBtn && window.ActionLock) {
                    window.ActionLock.unlockButton(targetBtn);
                }
                const loginBtn = document.getElementById('loginBtn');
                if (loginBtn && window.ActionLock && window.ActionLock.isLocked(loginBtn)) {
                    window.ActionLock.unlockButton(loginBtn);
                }
            }
        })();

        if (isWriteMethod) {
            this.inFlightRequests.set(requestKey, requestPromise);
        }

        return requestPromise;
    },

    get(endpoint, options = {}) { return this.request(endpoint, { ...options, method: 'GET' }); },
    post(endpoint, body, options = {}) { 
        return this.request(endpoint, { 
            ...options,
            method: 'POST', 
            body: body instanceof FormData ? body : JSON.stringify(body) 
        }); 
    },
    put(endpoint, body, options = {}) { 
        return this.request(endpoint, { 
            ...options,
            method: 'PUT', 
            body: body instanceof FormData ? body : JSON.stringify(body) 
        }); 
    },
    patch(endpoint, body, options = {}) { 
        return this.request(endpoint, { 
            ...options,
            method: 'PATCH', 
            body: body instanceof FormData ? body : JSON.stringify(body) 
        }); 
    },
    delete(endpoint, options = {}) { return this.request(endpoint, { ...options, method: 'DELETE' }); },
    
    // Custom helpers
    getPotentialMembers: function(deptId, role = '') {
        let url = `/projects/potential-members?dept_id=${deptId}`;
        if (role) url += `&role=${role}`;
        return this.get(url);
    },

    getRepositoryProjects: function(filters = {}) {
        const params = new URLSearchParams();
        Object.entries(filters).forEach(([k, v]) => {
            if (v) params.append(k, v);
        });
        return this.get(`/repository/list?${params.toString()}`);
    },

    uploadFile: function(endpoint, file) {
        const formData = new FormData();
        formData.append('file', file);
        return this.post(endpoint, formData);
    },

    downloadFile: async function(endpoint, filename) {
        // Global PDF Module Access Check
        if (window.FeatureEngine) {
            const isPdf = endpoint.includes('/reports/export/pdf') || (filename && filename.toLowerCase().endsWith('.pdf'));
            if (isPdf) {
                const isPdfEnabled = FeatureEngine.isEnabled('reports.pdf');
                if (!isPdfEnabled) {
                    FeatureEngine.showDisabledModuleNotice('reports.pdf');
                    throw new Error('PDF Export downloader is disabled for your organization.');
                }
            }
        }

        const token = this.token;
        const headers = {};
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        const response = await fetch(`${API_BASE}${endpoint}`, {
            method: 'GET',
            headers: headers
        });
        if (response.status === 401) {
            if (typeof window.logout === 'function') {
                window.logout();
            } else {
                sessionStorage.removeItem('token');
                localStorage.removeItem('token');
                window.location.href = '/auth/login.html';
            }
            throw new Error('Unauthorized - please log in again');
        }
        if (!response.ok) {
            let errMsg = `Download failed (HTTP ${response.status})`;
            try {
                const errData = await response.json();
                errMsg = errData.message || errData.error || errMsg;
            } catch (_) {}
            throw new Error(errMsg);
        }
        const blob = await response.blob();
        if (!blob || blob.size === 0) {
            throw new Error('Received empty file from server');
        }
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    },

    getPlants: function() { return this.get('/admin/plants'); },
    createPlant: function(data) { return this.post('/admin/plants', data); },
    updatePlant: function(id, data) { return this.put(`/admin/plants/${id}`, data); },
    deletePlant: function(id) { return this.delete(`/admin/plants/${id}`); },

    showNotification: function(message, type = 'info') {
        if (window.QCMS && QCMS.toast) {
            QCMS.toast(message, type);
        } else {
            console.log(`[Notification] ${type}: ${message}`);
            // Fallback for pages without components.js
            alert(message);
        }
    }
};

window.printElementContent = function(elementId, title = 'Document') {
    const area = document.getElementById(elementId);
    if (!area) return;

    const iframe = document.createElement('iframe');
    iframe.name = "printIframe_" + elementId;
    iframe.style.position = "absolute";
    iframe.style.width = "0px";
    iframe.style.height = "0px";
    iframe.style.border = "none";
    document.body.appendChild(iframe);

    const doc = iframe.contentWindow.document;

    // Copy styles
    let styles = "";
    document.querySelectorAll("link[rel='stylesheet']").forEach(link => {
        styles += `<link rel="stylesheet" href="${link.href}">`;
    });
    document.querySelectorAll("style").forEach(style => {
        styles += style.outerHTML;
    });

    doc.open();
    doc.write(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>${title}</title>
            ${styles}
            <style>
                body {
                    background: white !important;
                    color: black !important;
                    padding: 30px !important;
                    font-family: Arial, sans-serif !important;
                }
                .inv-doc, .invoice-card {
                    box-shadow: none !important;
                    border: none !important;
                    background: white !important;
                    width: 100% !important;
                    max-width: 100% !important;
                    margin: 0 !important;
                    padding: 0 !important;
                    color: #1a1a2e !important;
                }
                .inv-doc .inv-hdr, .invoice-card .inv-hdr {
                    display: flex !important;
                    justify-content: space-between !important;
                    margin-bottom: 1.5rem !important;
                }
                .inv-doc table, .invoice-card table {
                    width: 100% !important;
                    border-collapse: collapse !important;
                    margin-top: 1rem !important;
                }
                .inv-doc th, .invoice-card th {
                    background: #f0f4f8 !important;
                    padding: 7px 10px !important;
                    font-size: 11px !important;
                    text-align: left !important;
                }
                .inv-doc td, .invoice-card td {
                    border-bottom: 1px solid #e5e7eb !important;
                    padding: 7px 10px !important;
                    font-size: 12px !important;
                }
                @page {
                    size: auto;
                    margin: 10mm 15mm;
                }
            </style>
        </head>
        <body>
            ${area.innerHTML}
            <script>
                window.onload = function() {
                    window.focus();
                    window.print();
                    setTimeout(() => {
                        window.parent.document.body.removeChild(window.frameElement);
                    }, 500);
                };
            <\/script>
        </body>
        </html>
    `);
    doc.close();
};
