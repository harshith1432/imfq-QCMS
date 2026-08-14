// Auto-detect Browser GPS Location (Only runs after user is authenticated to prevent permission popups on login)
(function initBrowserGeolocation() {
    if (typeof window === 'undefined' || !navigator || !navigator.geolocation) return;
    const path = window.location.pathname || '';
    if (path.includes('login') || path.includes('register') || path.includes('reset-password') || path.includes('forgot-password')) {
        return;
    }
    const cached = sessionStorage.getItem('browser_geo_location');
    if (cached) {
        window._cachedBrowserLocation = cached;
        return;
    }
    try {
        navigator.geolocation.getCurrentPosition(
            async (pos) => {
                const lat = pos.coords.latitude;
                const lon = pos.coords.longitude;
                // Check if coordinates are in/near Bengaluru / Karnataka (lat ~12.5-13.5, lon ~77.0-78.2)
                if (lat >= 12.5 && lat <= 13.5 && lon >= 77.0 && lon <= 78.2) {
                    const loc = 'Bengaluru, Karnataka, IN';
                    window._cachedBrowserLocation = loc;
                    sessionStorage.setItem('browser_geo_location', loc);
                    return;
                }
                try {
                    const res = await fetch(`https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${lat}&longitude=${lon}&localityLanguage=en`);
                    if (res.ok) {
                        const data = await res.json();
                        const city = data.city || data.locality || data.principalSubdivision || '';
                        const state = data.principalSubdivision || '';
                        const country = data.countryCode || 'IN';
                        if (city) {
                            const formatted = `${city}${state ? ', ' + state : ''}, ${country}`;
                            window._cachedBrowserLocation = formatted;
                            sessionStorage.setItem('browser_geo_location', formatted);
                        }
                    }
                } catch (e) {}
            },
            (err) => {
                console.debug('[GeoLocation] GPS fallback to Plant/IP location.');
            },
            { timeout: 5000, maximumAge: 600000 }
        );
    } catch (e) {}
})();

const API_BASE = '/api';

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

            const isPublicAuthEndpoint = endpoint.includes('/auth/login') ||
                endpoint.includes('/auth/register') ||
                endpoint.includes('/auth/login-config') ||
                endpoint.includes('/auth/forgot-password') ||
                endpoint.includes('/auth/reset-password-confirm') ||
                endpoint.includes('/auth/sso/');

            if (token && !isPublicAuthEndpoint) {
                headers['Authorization'] = `Bearer ${token}`;
            }

            // Attach Browser GPS Geo-Location if available
            const browserGeo = typeof window !== 'undefined' ? (window._cachedBrowserLocation || sessionStorage.getItem('browser_geo_location')) : '';
            if (browserGeo && !headers['X-Browser-Location']) {
                headers['X-Browser-Location'] = browserGeo;
            }

            // Support AbortController and default timeout of 120 seconds for Render free-tier cold-starts
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), options.timeout || 120000);

            try {
                const response = await fetch(`${API_BASE}${endpoint}`, {
                    ...options,
                    headers,
                    signal: controller.signal
                });
                clearTimeout(timeoutId);

                if (endpoint.includes('/auth/login')) {
                    const data = await response.clone().json().catch(() => ({}));
                    if (!response.ok) {
                        const error = new Error(data.message || data.msg || 'Login failed. Please check your credentials.');
                        error.errors = data.errors || [];
                        error.status = response.status;
                        error.code = data.error_code || data.code;
                        error.error_code = data.error_code || data.code;
                        error.lockedUntilEpoch = data.locked_until_epoch;
                        error.locked_until_epoch = data.locked_until_epoch;
                        error.remainingSeconds = data.remaining_seconds;
                        error.remaining_seconds = data.remaining_seconds;
                        throw error;
                    }
                    return data;
                }

                if (response.status === 401) {
                    const isAuthPage = window.location.pathname.includes('login.html') || window.location.pathname.includes('reset-password.html');
                    // Match only super-admin.html portal page (not standard org admin pages under /admin/)
                    const isSuperAdminPortal = window.location.pathname.includes('super-admin.html');
                    const isInsideSuperAdminIframe = (() => {
                        try {
                            return window.parent && window.parent !== window
                                && window.parent.location.pathname.includes('super-admin.html');
                        } catch (_) { return false; }
                    })();
                    if (!isAuthPage) {
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
                    const fallbackMsg = (response.status === 401 || response.status === 400 || response.status === 403) ? 'Invalid username or password' : 'Request failed. Please try again.';
                    const error = new Error(data.message || data.msg || data.error || data.detail || fallbackMsg);
                    error.errors = data.errors || [];
                    error.status = response.status;
                    error.error_code = data.error_code;
                    throw error;
                }
                return data;
            } catch (err) {
                clearTimeout(timeoutId);
                if (err.name === 'AbortError') {
                    const isLogin = endpoint.includes('/auth/login');
                    const msg = isLogin
                        ? 'Server is warming up, please wait a moment and try again.'
                        : 'Request timeout. Please check your connection.';
                    const timeoutErr = new Error(msg);
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
                try {
                    sessionStorage.clear();
                    localStorage.removeItem('token');
                    localStorage.removeItem('access_token');
                    localStorage.removeItem('user');
                } catch (_) {}
                window.location.replace('/auth/login.html?logout=true');
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
