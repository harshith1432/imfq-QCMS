const API_BASE = '/api';

const api = {
    async request(endpoint, options = {}) {
        const token = localStorage.getItem('token');
        const headers = { ...options.headers };
        
        // Only set Content-Type if not provided and not FormData
        if (!headers['Content-Type'] && !(options.body instanceof FormData)) {
            headers['Content-Type'] = 'application/json';
        }

        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const response = await fetch(`${API_BASE}${endpoint}`, {
            ...options,
            headers
        });

        if (response.status === 401) {
            if (typeof window.logout === 'function') {
                window.logout();
            } else {
                localStorage.removeItem('token');
                if (!window.location.pathname.includes('login.html')) {
                    window.location.href = 'login.html';
                }
            }
            return;
        }

        const data = await response.json();
        if (!response.ok) throw new Error(data.message || data.msg || 'API Error');
        return data;
    },

    get(endpoint) { return this.request(endpoint, { method: 'GET' }); },
    post(endpoint, body) { 
        return this.request(endpoint, { 
            method: 'POST', 
            body: body instanceof FormData ? body : JSON.stringify(body) 
        }); 
    },
    put(endpoint, body) { 
        return this.request(endpoint, { 
            method: 'PUT', 
            body: body instanceof FormData ? body : JSON.stringify(body) 
        }); 
    },
    patch(endpoint, body) { 
        return this.request(endpoint, { 
            method: 'PATCH', 
            body: body instanceof FormData ? body : JSON.stringify(body) 
        }); 
    },
    delete(endpoint) { return this.request(endpoint, { method: 'DELETE' }); },
    
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
