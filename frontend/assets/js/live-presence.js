/**
 * Live Collaborative Presence Manager (SSE / Heartbeat)
 * Tracks and visualizes real-time active users, reviewers, and facilitators on project stages.
 */
class LivePresenceManager {
    constructor() {
        this.currentProjectId = null;
        this.currentStageId = null;
        this.eventSource = null;
        this.heartbeatTimer = null;
        this.fallbackPollingTimer = null;
        this.isEditing = false;
        this.editingTimeout = null;
        this.activeCollaborators = [];
        this.currentUserId = null;

        // Register unload hook to leave presence cleanly
        window.addEventListener('beforeunload', () => this.leaveCurrentStageSync());

        // Listen for typing activity to flag active editing
        document.addEventListener('input', (e) => this.handleUserActivity(e), true);
        document.addEventListener('change', (e) => this.handleUserActivity(e), true);
    }

    _getCurrentUser() {
        try {
            if (typeof api !== 'undefined' && api.getUser) {
                return api.getUser();
            }
            const raw = localStorage.getItem('user');
            return raw ? JSON.parse(raw) : null;
        } catch (e) {
            return null;
        }
    }

    _getToken() {
        try {
            if (typeof api !== 'undefined' && api.token) {
                return api.token;
            }
            return '';
        } catch (e) {
            return '';
        }
    }

    handleUserActivity(e) {
        if (!this.currentProjectId || !this.currentStageId) return;
        const target = e.target;
        if (!target) return;
        const tag = target.tagName ? target.tagName.toLowerCase() : '';
        if (tag === 'input' || tag === 'textarea' || tag === 'select' || target.isContentEditable) {
            this.isEditing = true;
            clearTimeout(this.editingTimeout);
            this.editingTimeout = setTimeout(() => {
                this.isEditing = false;
                this.sendHeartbeat();
            }, 8000);
        }
    }

    startStagePresence(projectId, stageId) {
        if (!projectId || !stageId) return;

        // If same stage already active, skip
        if (this.currentProjectId === Number(projectId) && this.currentStageId === Number(stageId)) {
            return;
        }

        // Leave previous stage if any
        this.leaveCurrentStage();

        this.currentProjectId = Number(projectId);
        this.currentStageId = Number(stageId);
        const user = this._getCurrentUser();
        this.currentUserId = user ? user.id : null;

        // Initial heartbeat
        this.sendHeartbeat();

        // Connect SSE Stream
        this.connectEventSource();

        // Heartbeat interval every 6 seconds
        this.heartbeatTimer = setInterval(() => {
            this.sendHeartbeat();
        }, 6000);
    }

    connectEventSource() {
        if (this.eventSource) {
            try { this.eventSource.close(); } catch (e) {}
            this.eventSource = null;
        }

        const token = this._getToken();
        if (!token) return;

        const sseUrl = `/api/workflow/${this.currentProjectId}/stage/${this.currentStageId}/presence-stream?token=${encodeURIComponent(token)}`;

        try {
            this.eventSource = new EventSource(sseUrl);

            this.eventSource.onmessage = (event) => {
                try {
                    const users = JSON.parse(event.data) || [];
                    this.activeCollaborators = users;
                    this.renderPresence(users);
                } catch (err) {
                    console.warn('[OctaQube Presence] Failed to parse SSE message:', err);
                }
            };

            this.eventSource.onerror = () => {
                // If SSE fails (proxy / browser restriction), fall back to lightweight polling
                if (this.eventSource) {
                    try { this.eventSource.close(); } catch (e) {}
                    this.eventSource = null;
                }
                this.startFallbackPolling();
            };
        } catch (err) {
            this.startFallbackPolling();
        }
    }

    startFallbackPolling() {
        if (this.fallbackPollingTimer) return;
        this.fallbackPollingTimer = setInterval(async () => {
            if (!this.currentProjectId || !this.currentStageId) return;
            await this.sendHeartbeat();
        }, 5000);
    }

    async sendHeartbeat() {
        if (!this.currentProjectId || !this.currentStageId) return;
        try {
            if (typeof api === 'undefined') return;
            const res = await api.post(`/workflow/${this.currentProjectId}/stage/${this.currentStageId}/presence-heartbeat`, {
                is_editing: this.isEditing
            });
            if (res && res.active_users) {
                this.activeCollaborators = res.active_users;
                this.renderPresence(res.active_users);
            }
        } catch (e) {
            // Heartbeat non-fatal failure
        }
    }

    leaveCurrentStage() {
        if (this.currentProjectId && this.currentStageId) {
            const pId = this.currentProjectId;
            const sId = this.currentStageId;
            try {
                if (typeof api !== 'undefined') {
                    api.post(`/workflow/${pId}/stage/${sId}/presence-leave`, {}).catch(() => {});
                }
            } catch (e) {}
        }

        if (this.eventSource) {
            try { this.eventSource.close(); } catch (e) {}
            this.eventSource = null;
        }
        if (this.heartbeatTimer) {
            clearInterval(this.heartbeatTimer);
            this.heartbeatTimer = null;
        }
        if (this.fallbackPollingTimer) {
            clearInterval(this.fallbackPollingTimer);
            this.fallbackPollingTimer = null;
        }
        this.currentProjectId = null;
        this.currentStageId = null;
        this.activeCollaborators = [];
        this.renderPresence([]);
    }

    leaveCurrentStageSync() {
        if (this.currentProjectId && this.currentStageId) {
            const token = this._getToken();
            const url = `/api/workflow/${this.currentProjectId}/stage/${this.currentStageId}/presence-leave`;
            if (navigator.sendBeacon) {
                const blob = new Blob([JSON.stringify({})], { type: 'application/json' });
                navigator.sendBeacon(url, blob);
            }
        }
    }

    renderPresence(allUsers = []) {
        // Filter out current logged-in user so we show OTHER active collaborators
        const otherUsers = (allUsers || []).filter(u => u.user_id !== this.currentUserId);
        
        this._renderBanner(otherUsers);
        this._renderAvatarStack(otherUsers, allUsers);
    }

    _renderBanner(otherUsers) {
        let bannerEl = document.getElementById('stageLivePresenceBanner');
        if (!bannerEl) {
            // Mount before stage content container or project header if not already in DOM
            const stageContainer = document.getElementById('stageContentContainer') || document.getElementById('stepperContainer');
            if (stageContainer && stageContainer.parentNode) {
                bannerEl = document.createElement('div');
                bannerEl.id = 'stageLivePresenceBanner';
                bannerEl.className = 'fade-in mb-3';
                stageContainer.parentNode.insertBefore(bannerEl, stageContainer);
            }
        }
        if (!bannerEl) return;

        if (!otherUsers || otherUsers.length === 0) {
            bannerEl.innerHTML = '';
            bannerEl.style.display = 'none';
            return;
        }

        const editor = otherUsers.find(u => u.is_editing);
        const stageNum = this.currentStageId || 'this';

        let messageHtml = '';
        let bgStyle = '';
        let borderStyle = '';
        let iconHtml = '';

        if (editor) {
            // Active typing / editing
            bgStyle = 'background: rgba(245, 158, 11, 0.08);';
            borderStyle = 'border: 1px solid rgba(245, 158, 11, 0.35);';
            iconHtml = '<i data-lucide="edit-3" style="width:16px;height:16px;color:#d97706;animation:pulse 1.5s infinite;"></i>';
            messageHtml = `<strong>${this._escape(editor.name)}</strong> <span class="badge bg-warning-subtle text-warning-emphasis border" style="font-size:0.65rem;padding:2px 6px;">${this._escape(editor.role)}</span> is currently editing Stage ${stageNum}.`;
        } else if (otherUsers.length === 1) {
            const u = otherUsers[0];
            bgStyle = 'background: rgba(var(--ds-primary-rgb), 0.06);';
            borderStyle = 'border: 1px solid rgba(var(--ds-primary-rgb), 0.2);';
            iconHtml = '<i data-lucide="eye" style="width:16px;height:16px;color:var(--ds-primary);"></i>';
            messageHtml = `<strong>${this._escape(u.name)}</strong> <span class="badge bg-primary-subtle text-primary border" style="font-size:0.65rem;padding:2px 6px;">${this._escape(u.role)}</span> is currently viewing Stage ${stageNum}.`;
        } else {
            bgStyle = 'background: rgba(var(--ds-primary-rgb), 0.06);';
            borderStyle = 'border: 1px solid rgba(var(--ds-primary-rgb), 0.2);';
            iconHtml = '<i data-lucide="users" style="width:16px;height:16px;color:var(--ds-primary);"></i>';
            
            const namesFormatted = otherUsers.map((u, i) => {
                const isLast = i === otherUsers.length - 1;
                const prefix = (i > 0 && isLast) ? ' and ' : (i > 0 ? ', ' : '');
                return `${prefix}<strong>${this._escape(u.name)}</strong> <span class="badge bg-primary-subtle text-primary border" style="font-size:0.65rem;padding:2px 6px;">${this._escape(u.role)}</span>`;
            }).join('');

            messageHtml = `${namesFormatted} are currently active in Stage ${stageNum}.`;
        }

        bannerEl.style.display = 'block';
        bannerEl.innerHTML = `
            <div class="d-flex align-items-center justify-content-between p-2.5 px-3 rounded-3 text-xs" style="${bgStyle} ${borderStyle} border-radius: 10px; transition: all 0.3s ease;">
                <div class="d-flex align-items-center gap-2 flex-wrap">
                    ${iconHtml}
                    <span class="ds-text-main" style="font-size:0.82rem;">${messageHtml}</span>
                </div>
                <div class="d-flex align-items-center gap-1.5 ms-2 flex-shrink-0">
                    <span class="badge bg-success-subtle text-success border border-success-subtle d-inline-flex align-items-center gap-1" style="font-size:0.68rem; padding: 3px 8px; border-radius: 999px;">
                        <span class="spinner-grow spinner-grow-sm" style="width:6px; height:6px;" role="status"></span> Live Presence
                    </span>
                </div>
            </div>
        `;

        if (window.lucide) lucide.createIcons();
    }

    _renderAvatarStack(otherUsers, allUsers) {
        const stackContainers = document.querySelectorAll('.live-presence-avatar-stack, #projectPresenceAvatars');
        if (!stackContainers.length) return;

        stackContainers.forEach(container => {
            if (!allUsers || allUsers.length === 0) {
                container.innerHTML = '';
                return;
            }

            const avatarChips = allUsers.map(u => {
                const isMe = u.user_id === this.currentUserId;
                const initials = (u.name || 'U').split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
                const statusColor = u.is_editing ? '#f59e0b' : '#22c55e';
                const statusTitle = u.is_editing ? 'Actively Editing' : 'Viewing Stage';

                const avatarContent = u.avatar 
                    ? `<img src="${this._escape(u.avatar)}" style="width:28px;height:28px;border-radius:50%;object-fit:cover;" alt="${this._escape(u.name)}">`
                    : `<div style="width:28px;height:28px;border-radius:50%;background:rgba(var(--ds-primary-rgb),0.15);color:var(--ds-primary);font-size:0.68rem;font-weight:700;display:flex;align-items:center;justify-content:center;">${initials}</div>`;

                return `
                    <div class="position-relative" style="cursor:help;" title="${this._escape(u.name)} (${this._escape(u.role)})${isMe ? ' - You' : ''} • ${statusTitle}" data-bs-toggle="tooltip">
                        <div style="border: 2px solid #ffffff; border-radius: 50%; box-shadow: 0 2px 4px rgba(0,0,0,0.08); overflow: hidden;">
                            ${avatarContent}
                        </div>
                        <span style="position:absolute; bottom:0; right:0; width:8px; height:8px; border-radius:50%; background:${statusColor}; border:1.5px solid #ffffff;"></span>
                    </div>
                `;
            }).join('');

            container.innerHTML = `
                <div class="d-flex align-items-center gap-1">
                    <div class="d-flex align-items-center" style="display:flex; margin-left: 6px;">
                        ${avatarChips}
                    </div>
                </div>
            `;
        });
    }

    _escape(str) {
        if (!str) return '';
        return String(str).replace(/[&<>"']/g, function(m) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[m];
        });
    }
}

// Global Singleton
window.LivePresence = new LivePresenceManager();
