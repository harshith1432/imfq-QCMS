(function () {
    const token = sessionStorage.getItem('token')
        || localStorage.getItem('token')
        || localStorage.getItem('access_token')
        || sessionStorage.getItem('access_token');
    const userStr = sessionStorage.getItem('user') || localStorage.getItem('user');

    function safeBase64Decode(str) {
        if (!str) return null;
        try {
            let output = str.replace(/-/g, '+').replace(/_/g, '/');
            switch (output.length % 4) {
                case 0: break;
                case 2: output += '=='; break;
                case 3: output += '='; break;
                default: break;
            }
            return decodeURIComponent(escape(atob(output)));
        } catch (_) {
            try {
                return atob(str);
            } catch (e) {
                return null;
            }
        }
    }

    function normalizeRole(role) {
        if (!role) return null;
        let roleStr = role;
        if (typeof role === 'object') {
            roleStr = role.name || role.role_name || role.role || '';
        }
        if (!roleStr || typeof roleStr !== 'string') return null;
        const r = roleStr.trim().toLowerCase();
        if (r === 'superadmin' || r === 'super admin' || r === 'super_admin') return 'SuperAdmin';
        if (r === 'admin') return 'Admin';
        if (r === 'team leader' || r === 'teamleader' || r === 'team_leader') return 'Team Leader';
        if (r === 'team member' || r === 'teammember' || r === 'team_member') return 'Team Member';
        if (r === 'facilitator') return 'Facilitator';
        if (r === 'reviewer') return 'Reviewer';
        if (r === 'ceo') return 'CEO';
        return roleStr;
    }

    let userRole = null;

    if (token) {
        try {
            if (userStr) {
                const user = JSON.parse(userStr);
                if (user) {
                    const rawRole = user.role || user.role_name || (typeof user.role === 'object' ? (user.role.name || user.role.role_name) : null);
                    if (rawRole) {
                        userRole = normalizeRole(rawRole);
                    }
                }
            }
            if (!userRole && token.includes('.')) {
                try {
                    const jsonStr = safeBase64Decode(token.split('.')[1]);
                    if (jsonStr) {
                        const payload = JSON.parse(jsonStr);
                        if (payload.role) userRole = normalizeRole(payload.role);
                        else if (payload.sa_sub_role || window.location.pathname.includes('super-admin.html')) userRole = 'SuperAdmin';
                    }
                } catch (_) {}
            }
        } catch (e) {
            console.warn('[AuthGuard] Non-fatal auth parse error:', e);
        }
    }

    const path = window.location.pathname;
    const rawPage = path.split('/').pop() || 'index.html';
    const page = rawPage.split('?')[0].split('#')[0];

    // Global Maintenance Mode check
    const isLandingPage = page === 'index.html' || path === '/' || path.endsWith('/');
    const isSuperAdminDashboard = page === 'super-admin.html';
    
    if (!isLandingPage && !isSuperAdminDashboard && page !== 'login.html') {
        fetch('/api/auth/maintenance-status')
            .then(res => res.json())
            .then(data => {
                if (data.maintenance_mode) {
                    let isSuperAdmin = false;
                    try {
                        const user = JSON.parse(sessionStorage.getItem('user') || localStorage.getItem('user') || '{}');
                        const role = normalizeRole(user?.role);
                        if (role === 'SuperAdmin') {
                            isSuperAdmin = true;
                        }
                    } catch (e) {}
                    
                    if (!isSuperAdmin) {
                        showMaintenanceScreen(data.message, data.eta);
                    }
                }
            })
            .catch(err => console.error('[Maintenance Mode] Check failed:', err));

        // Page-level Feature Module Gate Check
        fetch('/api/feature-engine/flags')
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success' && data.flags && window.QCMS_MODULE_MAP) {
                    const moduleCode = window.QCMS_MODULE_MAP.findByRoute(path);
                    if (moduleCode && data.flags[moduleCode] === false) {
                        let isSuperAdmin = false;
                        try {
                            const user = JSON.parse(sessionStorage.getItem('user') || localStorage.getItem('user') || '{}');
                            const role = normalizeRole(user?.role);
                            if (role === 'SuperAdmin' || role === 'Admin') isSuperAdmin = true;
                        } catch (e) {}

                        if (!isSuperAdmin) {
                            showModuleDisabledScreen(moduleCode);
                        }
                    }
                }
            })
    }

    // ── Active Session Termination Heartbeat ──────────────────────────────
    // Periodically verify session validity so if a Super Admin terminates this user's
    // active session, the user is immediately kicked back to the login page.
    if (token && !isLandingPage && page !== 'login.html') {
        let sessionCheckInProgress = false;
        const verifySessionStatus = async () => {
            if (sessionCheckInProgress) return;
            sessionCheckInProgress = true;
            try {
                const res = await fetch('/api/auth/me', {
                    headers: { 'Authorization': `Bearer ${token}` }
                });
                if (res.status === 401) {
                    const data = await res.json().catch(() => ({}));
                    console.warn('[AuthGuard] 401 received during session check:', data);
                    sessionStorage.clear();
                    localStorage.clear();
                    if (!window.location.pathname.includes('login.html')) {
                        if (data && (data.session_terminated || (data.message && (data.message.toLowerCase().includes('terminated') || data.message.toLowerCase().includes('deactivated'))))) {
                            window.location.href = '/auth/login.html?reason=session_terminated';
                        } else {
                            window.location.href = '/auth/login.html';
                        }
                    }
                }
            } catch (_) {
            } finally {
                sessionCheckInProgress = false;
            }
        };

        // Run initial check after 3s, repeat every 30s & on tab focus
        setTimeout(verifySessionStatus, 3000);
        setInterval(verifySessionStatus, 30000);
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') verifySessionStatus();
        });
    }

    // ── Self-Service Sign-Up Gate ───────────────────────────────────────────
    // When visiting register-org.html, immediately verify registration is open.
    // This fires from auth-guard.js (loaded in <head>) so it blocks before render.
    if (page === 'register-org.html') {
        // Hide body until status is confirmed to prevent form flash
        document.documentElement.style.visibility = 'hidden';
        fetch('/api/auth/registration-status')
            .then(r => r.json())
            .then(data => {
                if (data && data.registration_open === false) {
                    // Permanently hide everything and show blocked message
                    document.documentElement.style.visibility = 'visible';
                    // Wait for DOM then show the disabled banner
                    const doBlock = () => {
                        const card   = document.getElementById('onboardingCard');
                        const banner = document.getElementById('disabledSignupBanner');
                        const footer = document.querySelector('.onboarding-footer');
                        if (card)   card.style.display   = 'none';
                        if (footer) footer.style.display = 'none';
                        if (banner) {
                            banner.style.display = 'block';
                            if (window.lucide) lucide.createIcons();
                        }
                        const hdr = document.querySelector('.onboarding-header p');
                        if (hdr) hdr.textContent = 'Self-service registration is currently disabled.';
                    };
                    if (document.readyState === 'loading') {
                        document.addEventListener('DOMContentLoaded', doBlock);
                    } else {
                        doBlock();
                    }
                } else {
                    document.documentElement.style.visibility = 'visible';
                    const doUnblock = () => {
                        const card   = document.getElementById('onboardingCard');
                        const banner = document.getElementById('disabledSignupBanner');
                        const footer = document.querySelector('.onboarding-footer');
                        const errBanner = document.getElementById('errorMessage');
                        if (card)   card.style.display   = 'block';
                        if (footer) footer.style.display = 'block';
                        if (banner) banner.style.display = 'none';
                        if (errBanner) errBanner.style.display = 'none';
                        const hdr = document.querySelector('.onboarding-header p');
                        if (hdr) hdr.textContent = 'Create your organization account to get started.';
                    };
                    if (document.readyState === 'loading') {
                        document.addEventListener('DOMContentLoaded', doUnblock);
                    } else {
                        doUnblock();
                    }
                }
            })
            .catch(() => {
                // On error, reveal page (backend will still enforce on submit)
                document.documentElement.style.visibility = 'visible';
            });
    }

    function showModuleDisabledScreen(moduleCode) {
        document.addEventListener('DOMContentLoaded', () => {
            // 1. Show sleek top notification banner
            const banner = document.createElement('div');
            banner.id = 'module-maintenance-banner';
            banner.style.cssText = 'position:fixed; top:0; left:0; right:0; z-index:99999; background:#fff3cd; color:#856404; border-bottom:1px solid #ffeeba; padding:10px 16px; font-size:13px; font-weight:600; text-align:center; box-shadow:0 2px 8px rgba(0,0,0,0.08);';
            banner.innerHTML = '⚠️ Currently this feature is under maintenance. Please contact your system administrator.';
            document.body.prepend(banner);

            // Adjust main container top margin if banner present
            document.body.style.paddingTop = '40px';

            // 2. Trigger simple notification toast
            setTimeout(() => {
                if (window.QCMS && typeof window.QCMS.toast === 'function') {
                    window.QCMS.toast('Currently this feature is under maintenance.', 'warning');
                } else if (typeof window.api?.showNotification === 'function') {
                    window.api.showNotification('Currently this feature is under maintenance.', 'warning');
                }
            }, 300);

            // 3. Freeze/disable form submit buttons on disabled module page
            const actionBtns = document.querySelectorAll('button[type="submit"], .btn-primary, input[type="submit"]');
            actionBtns.forEach(btn => {
                btn.disabled = true;
                btn.title = 'Currently this feature is under maintenance';
            });
        });
    }

    function showMaintenanceScreen(message, eta) {
        // Halt any ongoing page script execution or requests
        try { window.stop(); } catch (e) {}

        // Clear all active intervals & timeouts to kill background chat/assistant widgets
        try {
            let maxId = setTimeout(function(){}, 0);
            for (let i = 0; i <= maxId; i++) {
                clearTimeout(i);
                clearInterval(i);
            }
        } catch (e) {}

        // ── Build optional ETA badge ────────────────────────────────────────
        let etaHtml = '';
        if (eta) {
            etaHtml =
                '<div class="maint-eta">' +
                    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">' +
                        '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>' +
                    '</svg>' +
                    'Estimated back online:&nbsp;<strong>' + eta + '</strong>' +
                '</div>';
        }

        // Wipe the document head and body completely to clear any loaded styles or widget containers
        document.documentElement.innerHTML =
            '<!DOCTYPE html><html lang="en"><head>' +
            '<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">' +
            '<title>System Under Maintenance — QCMS Enterprise</title>' +
            '<link rel="preconnect" href="https://fonts.googleapis.com">' +
            '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">' +
            '<style>' +
            '*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}' +
            'html,body{width:100%;height:100%;min-height:100vh;margin:0;padding:0;overflow-x:hidden;background:#f8fafc;font-family:"Inter",system-ui,-apple-system,sans-serif;-webkit-font-smoothing:antialiased}' +
            
            /* Hide any background widgets appended by residual scripts */
            'iframe, [id*="chat"], [class*="chat"], [id*="helpdesk"], [class*="helpdesk"], [id*="assistant"], [class*="assistant"] { display: none !important; }' +

            '#q-maint-wrapper {' +
                'min-height:100vh;width:100%;display:flex;flex-direction:column;justify-content:space-between;' +
                'background:#f8fafc;color:#0f172a;position:relative;' +
            '}' +
            '#q-maint-wrapper::before {' +
                'content:"";position:fixed;inset:0;pointer-events:none;z-index:0;' +
                'background:radial-gradient(circle at 70% 20%,rgba(219,234,254,0.55) 0%,transparent 45%),' +
                           'radial-gradient(circle at 10% 80%,rgba(240,249,255,0.55) 0%,transparent 40%);' +
            '}' +
            '.lp-nav {' +
                'position:sticky;top:0;z-index:1000;' +
                'background:rgba(248,250,252,0.85);backdrop-filter:blur(16px);-webkit-backdrop-filter:blur(16px);' +
                'border-bottom:1px solid rgba(15,23,42,0.08);box-shadow:0 1px 3px rgba(15,23,42,0.08);width:100%;' +
            '}' +
            '.lp-nav-inner {' +
                'max-width:1200px;margin:0 auto;display:flex;' +
                'align-items:center;justify-content:space-between;' +
                'padding:0 1.5rem;height:68px;' +
            '}' +
            '.nav-brand { display:flex; align-items:center; gap:10px; text-decoration:none; }' +
            '.nav-brand-icon {' +
                'width:36px;height:36px;border-radius:8px;' +
                'background:#0f172a;display:flex;align-items:center;justify-content:center;' +
            '}' +
            '.nav-brand-text { font-size:1.2rem; font-weight:800; color:#0f172a; letter-spacing:-0.02em; }' +
            '.nav-brand-text span { font-weight:400; color:#475569; }' +
            '.nav-status-badge {' +
                'display:inline-flex;align-items:center;gap:6px;' +
                'padding:6px 14px;background:#fef3c7;border:1px solid #fde68a;' +
                'border-radius:999px;font-size:0.72rem;font-weight:700;' +
                'color:#92400e;letter-spacing:0.04em;text-transform:uppercase;' +
            '}' +
            '.nav-status-dot {' +
                'width:6px;height:6px;border-radius:50%;background:#d97706;' +
                'animation:qblink 1.4s ease-in-out infinite;' +
            '}' +
            '.maint-body {' +
                'flex:1;display:flex;align-items:center;justify-content:center;' +
                'padding:3rem 1.25rem;position:relative;z-index:1;' +
            '}' +
            '.maint-card {' +
                'width:min(580px,100%);background:#ffffff;border:1px solid rgba(15,23,42,0.08);' +
                'border-radius:24px;box-shadow:0 1px 3px rgba(15,23,42,0.08),0 20px 40px -8px rgba(15,23,42,0.1);' +
                'overflow:hidden;animation:qslideUp 0.55s cubic-bezier(0.16,1,0.3,1) both;' +
            '}' +
            '.maint-card-topbar {' +
                'height:4px;background:linear-gradient(90deg,#0f172a 0%,#2563eb 50%,#60a5fa 100%);' +
            '}' +
            '.maint-card-body { padding:2.75rem 2.5rem 2.25rem; text-align:center; }' +
            '.maint-icon-box {' +
                'width:72px;height:72px;border-radius:18px;background:#0f172a;' +
                'display:flex;align-items:center;justify-content:center;' +
                'margin:0 auto 2rem;box-shadow:0 8px 24px rgba(15,23,42,0.2);' +
                'animation:qiconFloat 4s ease-in-out infinite;' +
            '}' +
            '.maint-title {' +
                'font-size:clamp(1.7rem,4vw,2.2rem);font-weight:800;letter-spacing:-0.04em;' +
                'line-height:1.15;color:#0f172a;margin-bottom:0.875rem;' +
            '}' +
            '.maint-title span { color:#2563eb; }' +
            '.maint-desc {' +
                'font-size:1rem;color:#475569;line-height:1.7;' +
                'max-width:400px;margin:0 auto 2rem;' +
            '}' +
            '.maint-eta {' +
                'display:inline-flex;align-items:center;gap:8px;padding:0.55rem 1.1rem;' +
                'background:#f0fdf4;border:1px solid #bbf7d0;border-radius:10px;' +
                'font-size:0.85rem;font-weight:500;color:#16a34a;margin-bottom:2rem;' +
            '}' +
            '.maint-progress-wrap {' +
                'height:4px;background:rgba(15,23,42,0.06);border-radius:99px;' +
                'overflow:hidden;max-width:340px;margin:0 auto 2rem;' +
            '}' +
            '.maint-progress-bar {' +
                'height:100%;width:100%;border-radius:99px;' +
                'background:linear-gradient(90deg,#0f172a,#2563eb,#60a5fa,#2563eb,#0f172a);' +
                'background-size:200% 100%;animation:qprogressShimmer 2.2s linear infinite;' +
            '}' +
            '.maint-status-row { display:flex; align-items:center; justify-content:center; gap:8px; flex-wrap:wrap; margin-bottom:2rem; }' +
            '.status-chip {' +
                'display:inline-flex;align-items:center;gap:5px;padding:5px 12px;' +
                'background:rgba(15,23,42,0.04);border:1px solid rgba(15,23,42,0.08);' +
                'border-radius:999px;font-size:0.7rem;font-weight:600;' +
                'color:#475569;font-family:ui-monospace,monospace;' +
            '}' +
            '.sdot { width:6px; height:6px; border-radius:50%; flex-shrink:0; }' +
            '.sdot-red { background:#ef4444; box-shadow:0 0 5px rgba(239,68,68,0.5); }' +
            '.sdot-amber { background:#f59e0b; box-shadow:0 0 5px rgba(245,158,11,0.4); }' +
            '.sdot-green { background:#22c55e; box-shadow:0 0 5px rgba(34,197,94,0.4); }' +
            '.maint-divider { height:1px; background:rgba(15,23,42,0.08); margin:0 -2.5rem 1.5rem; }' +
            '.maint-footer { display:flex; align-items:center; justify-content:center; gap:6px; font-size:0.7rem; color:#64748b; }' +
            '.fdot { width:3px; height:3px; border-radius:50%; background:rgba(15,23,42,0.08); }' +
            '.page-footer {' +
                'text-align:center;padding:1.5rem;font-size:0.7rem;color:#64748b;' +
                'border-top:1px solid rgba(15,23,42,0.08);background:rgba(15,23,42,0.02);' +
            '}' +
            '@keyframes qslideUp { from{opacity:0;transform:translateY(24px)} to{opacity:1;transform:translateY(0)} }' +
            '@keyframes qiconFloat { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-5px)} }' +
            '@keyframes qprogressShimmer { 0%{background-position:100% 0} 100%{background-position:-100% 0} }' +
            '@keyframes qblink { 0%,100%{opacity:1} 50%{opacity:0.3} }' +
            '</style>' +
            '</head><body>' +

            '<div id="q-maint-wrapper">' +
                '<nav class="lp-nav">' +
                    '<div class="lp-nav-inner">' +
                        '<a class="nav-brand" href="#">' +
                            '<div class="nav-brand-icon">' +
                                '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#f8fafc" stroke-width="2.25" stroke-linecap="round" stroke-linejoin="round">' +
                                    '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>' +
                                    '<polyline points="9 12 11 14 15 10"/>' +
                                '</svg>' +
                            '</div>' +
                            '<span class="nav-brand-text">QCMS&nbsp;<span>Enterprise</span></span>' +
                        '</a>' +
                        '<div class="nav-status-badge">' +
                            '<span class="nav-status-dot"></span>' +
                            'Under Maintenance' +
                        '</div>' +
                    '</div>' +
                '</nav>' +

                '<div class="maint-body">' +
                    '<div class="maint-card">' +
                        '<div class="maint-card-topbar"></div>' +
                        '<div class="maint-card-body">' +
                            '<div class="maint-icon-box">' +
                                '<svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="#f8fafc" stroke-width="1.85" stroke-linecap="round" stroke-linejoin="round">' +
                                    '<path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>' +
                                '</svg>' +
                            '</div>' +
                            '<h1 class="maint-title">System <span>Under Maintenance</span></h1>' +
                            '<p class="maint-desc">' +
                                (message || 'The platform is currently undergoing scheduled maintenance. We\'ll be back online shortly.') +
                            '</p>' +
                            (etaHtml || '') +
                            '<div class="maint-progress-wrap"><div class="maint-progress-bar"></div></div>' +
                            '<div class="maint-status-row">' +
                                '<span class="status-chip"><span class="sdot sdot-red"></span>Database: Offline</span>' +
                                '<span class="status-chip"><span class="sdot sdot-amber"></span>API: Standby</span>' +
                                '<span class="status-chip"><span class="sdot sdot-green"></span>CDN: Operational</span>' +
                            '</div>' +
                            '<div class="maint-divider"></div>' +
                            '<div class="maint-footer">' +
                                'QCMS Enterprise OS' +
                                '<span class="fdot"></span>' +
                                'Secured &amp; Isolated Cloud Instance' +
                                '<span class="fdot"></span>' +
                                'v1.0.0' +
                            '</div>' +
                        '</div>' +
                    '</div>' +
                '</div>' +

                '<footer class="page-footer">' +
                    '© ' + new Date().getFullYear() + ' QCMS Enterprise · All rights reserved' +
                '</footer>' +
            '</div>' +
            '</body></html>';
    }
    // Pages that DON'T need protection
    const publicPages = [
        'index.html',
        'login.html',
        'register.html',
        'register-org.html',
        'forgot-password.html',
        'reset-password.html',
        'page.html'
    ];

    const isPublic = publicPages.includes(page) || path === '/' || path.endsWith('/');
    const isAuthPage = page === 'login.html';

    if (!token && !isPublic) {
        console.log('Access denied. Redirecting to login...');
        window.location.replace('/auth/login.html');
        return;
    }

    // Check token expiration if JWT format
    if (token && token.includes('.')) {
        try {
            const jsonStr = safeBase64Decode(token.split('.')[1]);
            if (jsonStr) {
                const payload = JSON.parse(jsonStr);
                if (payload.exp && payload.exp * 1000 < Date.now()) {
                    console.warn('[AuthGuard] Token expired. Clearing session and redirecting to login...');
                    sessionStorage.clear();
                    localStorage.removeItem('token');
                    localStorage.removeItem('access_token');
                    localStorage.removeItem('user');
                    if (!isPublic) {
                        window.location.replace('/auth/login.html');
                        return;
                    }
                }
            }
        } catch (e) {}
    }

    // ── Role-to-Dashboard mapping ──────────────────────────────────
    const dashboardMap = {
        'SuperAdmin': '/admin/super-admin.html',
        'Admin': '/dashboard/dashboard-admin.html',
        'Reviewer': '/dashboard/dashboard-reviewer.html',
        'Facilitator': '/dashboard/dashboard-facilitator.html',
        'Team Leader': '/dashboard/dashboard-team-member.html',
        'Team Member': '/dashboard/dashboard-team-member.html',
        'CEO': '/dashboard/dashboard-ceo.html'
    };

    // ── Module mapping for Organization pages ────────
    const pageModuleMap = {
        'repository.html': 'knowledge_base',
        'projects-repository.html': 'project_repo',
        'analytics.html': 'analytics',
        'users.html': 'user_management',
        'user-management.html': 'user_management',
        'plants.html': 'plants',
        'departments.html': 'departments',
        'audit-logs.html': 'audit_logs',
        'audit-queue.html': 'audit_logs',
        'stage-template.html': 'stage_template',
        'leaderboard.html': 'leaderboard',
        'additional-sources.html': 'additional_sources',
        'settings.html': 'settings'
    };

    const isSuperAdminUser = (userRole === 'SuperAdmin' || userRole === 'Super Admin');

    if (isAuthPage) {
        const urlParams = new URLSearchParams(window.location.search);
        // Clear session on explicit logout, administrative session termination, or default direct landing without auto flag
        if (urlParams.get('logout') === 'true' || urlParams.get('reason') === 'session_terminated') {
            try {
                sessionStorage.clear();
                localStorage.removeItem('token');
                localStorage.removeItem('access_token');
                localStorage.removeItem('user');
                localStorage.removeItem('role_permissions');
                sessionStorage.removeItem('role_permissions');
            } catch (_) {}
        } else if (urlParams.get('auto') === 'true' && token && userRole) {
            console.log('Auto-login requested on login page. Redirecting to role dashboard...');
            redirectByRole(userRole);
            return;
        }
    } else if (token && !isSuperAdminUser) {
        let isDenied = false;

        // Block non-SuperAdmin from super-admin portal pages
        if (page === 'super-admin.html' || window.location.pathname.includes('super-admin')) {
            isDenied = true;
        }

        // Check Organization Role Access Control (RBAC) permissions dynamically
        const modKey = pageModuleMap[page];
        if (modKey) {
            try {
                const userObj = JSON.parse(sessionStorage.getItem('user') || localStorage.getItem('user') || '{}');
                const rolePerms = userObj.role_permissions || JSON.parse(sessionStorage.getItem('role_permissions') || localStorage.getItem('role_permissions') || 'null');
                let targetRole = userRole || userObj.role || 'Team Member';
                if (targetRole === 'Team Leader' || targetRole === 'teamleader' || targetRole === 'team_leader') targetRole = 'Team Member';
                
                if (rolePerms && rolePerms[targetRole] && typeof rolePerms[targetRole][modKey] === 'boolean') {
                    if (rolePerms[targetRole][modKey] === false) {
                        console.warn(`[RBAC] Module "${modKey}" is disabled for role "${targetRole}". Access denied to "${page}".`);
                        isDenied = true;
                    }
                }
            } catch (e) {
                console.warn('Error reading role_permissions in auth-guard:', e);
            }
        }

        if (isDenied) {
            console.warn(`[RBAC] Redirecting role "${userRole}" away from restricted page "${page}".`);
            redirectByRole(userRole);
        }
    }

    function redirectByRole(role) {
        const normRole = normalizeRole(role);
        const dashboard = dashboardMap[normRole] || dashboardMap[role] || '/dashboard/dashboard-team-member.html';
        const targetPage = dashboard.split('/').pop().toLowerCase();
        const currentPage = page.toLowerCase();
        if (currentPage !== targetPage) {
            console.warn(`[AuthGuard] Redirecting from "${currentPage}" to role dashboard "${targetPage}" for role:`, role);
            window.location.replace(dashboard);
        }
    }

    // ── Check real-time user active status and organization suspension ─────
    if (token && !isPublic) {
        fetch('/api/auth/me', {
            headers: { 'Authorization': `Bearer ${token}` }
        })
        .then(res => {
            if (res.status === 401) {
                console.warn('[Auth Check] 401 Unauthorized session. Clearing token and redirecting to login...');
                sessionStorage.clear();
                localStorage.removeItem('token');
                localStorage.removeItem('access_token');
                localStorage.removeItem('user');
                window.location.replace('/auth/login.html');
                return null;
            }
            if (!res.ok) {
                console.warn('[Auth Check] Server responded with status:', res.status);
                return null;
            }
            return res.json();
        })
        .then(profile => {
            if (profile) {
                if (profile.role_permissions) {
                    sessionStorage.setItem('role_permissions', JSON.stringify(profile.role_permissions));
                    localStorage.setItem('role_permissions', JSON.stringify(profile.role_permissions));
                    try {
                        const cachedUser = JSON.parse(sessionStorage.getItem('user') || localStorage.getItem('user') || '{}');
                        cachedUser.role_permissions = profile.role_permissions;
                        sessionStorage.setItem('user', JSON.stringify(cachedUser));
                        localStorage.setItem('user', JSON.stringify(cachedUser));
                    } catch (_) {}
                }

                const normRole = normalizeRole(profile.role_name || profile.role || userRole);
                const isSuperAdmin = normRole === 'SuperAdmin'
                    || profile.role_name === 'SuperAdmin'
                    || profile.role === 'SuperAdmin'
                    || userRole === 'SuperAdmin'
                    || page === 'super-admin.html'
                    || window.location.pathname.includes('super-admin');

                if (!isSuperAdmin) {
                    if (profile.is_active === false) {
                        if (document.readyState === 'loading') {
                            document.addEventListener('DOMContentLoaded', () => showDeactivatedAccountScreen(profile));
                        } else {
                            showDeactivatedAccountScreen(profile);
                        }
                    } else if (profile.subscription_status === 'Suspended') {
                        if (document.readyState === 'loading') {
                            document.addEventListener('DOMContentLoaded', () => showSuspendedOrganizationScreen(profile));
                        } else {
                            showSuspendedOrganizationScreen(profile);
                        }
                    }
                }
            }
        })
        .catch(err => console.debug('[Auth Check] Skipped:', err.message));
    }

    function showSuspendedOrganizationScreen(profile) {
        const normRole = normalizeRole(profile?.role_name || profile?.role || userRole);
        if (normRole === 'SuperAdmin' || profile?.role_name === 'SuperAdmin' || userRole === 'SuperAdmin' || page === 'super-admin.html' || window.location.pathname.includes('super-admin')) {
            return;
        }
        if (document.getElementById('q-suspended-wrapper')) return;

        // Freeze background body scrolling
        document.body.style.overflow = 'hidden';

        // Clear active background intervals
        try {
            let maxId = setTimeout(function(){}, 0);
            for (let i = 0; i <= maxId; i++) {
                clearTimeout(i);
                clearInterval(i);
            }
        } catch(e) {}

        const overlay = document.createElement('div');
        overlay.id = 'q-suspended-wrapper';
        overlay.innerHTML = `
            <style>
                #q-suspended-wrapper {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100vw;
                    height: 100vh;
                    z-index: 999999;
                    background: rgba(15, 23, 42, 0.88);
                    backdrop-filter: blur(14px);
                    -webkit-backdrop-filter: blur(14px);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 1.5rem;
                    font-family: 'Inter', system-ui, -apple-system, sans-serif;
                    animation: qSuspFade 0.35s cubic-bezier(0.16, 1, 0.3, 1) both;
                }
                .susp-card {
                    width: min(620px, 95vw);
                    background: #ffffff;
                    border-radius: 24px;
                    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.35);
                    overflow: hidden;
                    border: 1px solid rgba(226, 232, 240, 0.8);
                }
                .susp-top-bar {
                    height: 5px;
                    background: linear-gradient(90deg, #ef4444 0%, #dc2626 50%, #b91c1c 100%);
                }
                .susp-body {
                    padding: 2.75rem 2.25rem 2.25rem;
                    text-align: center;
                }
                .susp-icon-box {
                    width: 72px;
                    height: 72px;
                    border-radius: 50%;
                    background: #fef2f2;
                    color: #ef4444;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin: 0 auto 1.5rem;
                    border: 1px solid #fecaca;
                }
                .susp-title {
                    font-size: 1.85rem;
                    font-weight: 800;
                    letter-spacing: -0.03em;
                    color: #dc2626;
                    margin-bottom: 0.75rem;
                    line-height: 1.2;
                }
                .susp-desc {
                    font-size: 0.95rem;
                    color: #475569;
                    line-height: 1.6;
                    max-width: 480px;
                    margin: 0 auto 2rem;
                }
                .susp-form-card {
                    background: #f8fafc;
                    border: 1px solid #e2e8f0;
                    border-radius: 16px;
                    padding: 1.5rem;
                    text-align: left;
                    margin-bottom: 1.75rem;
                }
                .susp-form-label {
                    font-size: 0.82rem;
                    font-weight: 700;
                    color: #1e293b;
                    margin-bottom: 0.65rem;
                    display: block;
                }
                .susp-textarea {
                    width: 100%;
                    border: 1px solid #cbd5e1;
                    border-radius: 10px;
                    padding: 0.75rem;
                    font-size: 0.875rem;
                    color: #0f172a;
                    background: #ffffff;
                    outline: none;
                    resize: vertical;
                    min-height: 100px;
                    font-family: inherit;
                    transition: border-color 0.15s ease;
                }
                .susp-textarea:focus {
                    border-color: #0f172a;
                    box-shadow: 0 0 0 3px rgba(15, 23, 42, 0.1);
                }
                .susp-submit-btn {
                    width: 100%;
                    margin-top: 1rem;
                    background: #0f172a;
                    color: #ffffff;
                    border: none;
                    border-radius: 10px;
                    padding: 0.75rem 1.25rem;
                    font-size: 0.875rem;
                    font-weight: 700;
                    cursor: pointer;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    gap: 0.5rem;
                    transition: background 0.15s ease, transform 0.1s ease;
                }
                .susp-submit-btn:hover {
                    background: #1e293b;
                }
                .susp-submit-btn:active {
                    transform: scale(0.99);
                }
                .susp-footer-note {
                    font-size: 0.78rem;
                    color: #64748b;
                    line-height: 1.5;
                }
                .susp-footer-note a {
                    color: #dc2626;
                    text-decoration: underline;
                    font-weight: 600;
                }
                .susp-logout-btn {
                    margin-top: 1rem;
                    display: inline-flex;
                    align-items: center;
                    gap: 0.35rem;
                    font-size: 0.8rem;
                    color: #64748b;
                    background: transparent;
                    border: none;
                    cursor: pointer;
                    text-decoration: underline;
                }
                .susp-logout-btn:hover {
                    color: #0f172a;
                }
                @keyframes qSuspFade {
                    from { opacity: 0; transform: scale(0.97); }
                    to { opacity: 1; transform: scale(1); }
                }
            </style>

            <div class="susp-card">
                <div class="susp-top-bar"></div>
                <div class="susp-body">
                    <div class="susp-icon-box">
                        <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                            <path d="M12 8v4"/>
                            <path d="M12 16h.01"/>
                        </svg>
                    </div>
                    <h1 class="susp-title">Organization Account Suspended</h1>
                    <p class="susp-desc">
                        Your organization's access to the QCMS platform has been suspended. Please contact the QCMS support team to reactivate your account.
                    </p>

                    <div class="susp-form-card">
                        <label class="susp-form-label">Request Account Reactivation</label>
                        <textarea id="suspendedReactivationReason" class="susp-textarea" placeholder="Describe the reason for requesting reactivation..."></textarea>
                        <button type="button" id="btnSubmitSuspendedReactivation" class="susp-submit-btn" onclick="window.submitSuspendedReactivationRequest()">
                            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                                <line x1="22" y1="2" x2="11" y2="13"/>
                                <polygon points="22 2 15 22 11 13 2 9 22 2"/>
                            </svg>
                            Submit Request
                        </button>
                        <div id="suspendedReactivationStatus" class="text-xs mt-2 text-center font-bold"></div>
                    </div>

                    <div class="susp-footer-note">
                        If you believe this is an error, please reach out directly to your assigned supervisor or mail us at <a href="mailto:support@ifqm.org.in">support@ifqm.org.in</a>.
                    </div>
                    <div>
                        <button type="button" class="susp-logout-btn" onclick="sessionStorage.clear(); localStorage.clear(); window.location.href='/auth/login.html';">
                            Sign Out / Log In with Another Account
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.body.appendChild(overlay);
    }

    window.showSuspendedOrganizationScreen = showSuspendedOrganizationScreen;

    window.submitSuspendedReactivationRequest = async function() {
        const textarea = document.getElementById('suspendedReactivationReason');
        const statusDiv = document.getElementById('suspendedReactivationStatus');
        const btn = document.getElementById('btnSubmitSuspendedReactivation');
        const msg = textarea ? textarea.value.trim() : '';

        if (!msg) {
            if (statusDiv) {
                statusDiv.style.color = '#ef4444';
                statusDiv.textContent = 'Please enter a reason for your reactivation request.';
            }
            if (textarea) textarea.focus();
            return;
        }

        if (btn) {
            btn.disabled = true;
            btn.innerHTML = 'Submitting...';
        }

        try {
            const token = sessionStorage.getItem('token') || localStorage.getItem('token');
            const res = await fetch('/api/auth/request-reactivation', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ message: msg })
            });
            const data = await res.json();
            if (res.ok && data.status === 'success') {
                if (statusDiv) {
                    statusDiv.style.color = '#16a34a';
                    statusDiv.textContent = '✓ Your reactivation request has been submitted successfully to SuperAdmin!';
                }
                if (textarea) textarea.value = '';
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = 'Submit Another Request';
                }
            } else {
                if (statusDiv) {
                    statusDiv.style.color = '#ef4444';
                    statusDiv.textContent = data.msg || data.message || 'Failed to submit request. Please try again.';
                }
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = 'Submit Request';
                }
            }
        } catch (err) {
            if (statusDiv) {
                statusDiv.style.color = '#ef4444';
                statusDiv.textContent = 'Error: ' + err.message;
            }
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = 'Submit Request';
            }
        }
    };

    function showDeactivatedAccountScreen(profile) {
        const normRole = normalizeRole(profile?.role_name || profile?.role || userRole);
        if (normRole === 'SuperAdmin' || profile?.role_name === 'SuperAdmin' || userRole === 'SuperAdmin' || page === 'super-admin.html' || window.location.pathname.includes('super-admin')) {
            return;
        }
        if (document.getElementById('q-deactivated-wrapper')) return;

        // Freeze background body scrolling & pointer events
        document.body.style.overflow = 'hidden';

        // Clear active background intervals
        try {
            let maxId = setTimeout(function(){}, 0);
            for (let i = 0; i <= maxId; i++) {
                clearTimeout(i);
                clearInterval(i);
            }
        } catch(e) {}

        const overlay = document.createElement('div');
        overlay.id = 'q-deactivated-wrapper';
        overlay.innerHTML = `
            <style>
                #q-deactivated-wrapper {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100vw;
                    height: 100vh;
                    z-index: 999999;
                    background: rgba(15, 23, 42, 0.82);
                    backdrop-filter: blur(14px);
                    -webkit-backdrop-filter: blur(14px);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 1.5rem;
                    font-family: 'Inter', system-ui, -apple-system, sans-serif;
                    animation: qDeactFade 0.35s cubic-bezier(0.16, 1, 0.3, 1) both;
                }
                .deact-card {
                    width: min(580px, 95vw);
                    background: #ffffff;
                    border-radius: 20px;
                    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.35), 0 0 0 1px rgba(255, 255, 255, 0.2);
                    overflow: hidden;
                }
                .deact-header-stripe {
                    height: 5px;
                    background: linear-gradient(90deg, #ef4444 0%, #dc2626 50%, #f97316 100%);
                }
                .deact-body {
                    padding: 2.5rem 2.25rem 2rem;
                    text-align: center;
                }
                .deact-icon-box {
                    width: 68px;
                    height: 68px;
                    border-radius: 18px;
                    background: #fef2f2;
                    border: 1px solid #fee2e2;
                    color: #ef4444;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    margin: 0 auto 1.5rem;
                    box-shadow: 0 10px 20px -5px rgba(239, 68, 68, 0.25);
                }
                .deact-title {
                    font-size: 1.65rem;
                    font-weight: 800;
                    color: #0f172a;
                    margin-bottom: 0.5rem;
                    letter-spacing: -0.02em;
                }
                .deact-badge {
                    display: inline-flex;
                    align-items: center;
                    gap: 6px;
                    padding: 5px 14px;
                    background: #fef2f2;
                    border: 1px solid #fca5a5;
                    color: #991b1b;
                    border-radius: 999px;
                    font-size: 0.72rem;
                    font-weight: 700;
                    text-transform: uppercase;
                    letter-spacing: 0.04em;
                    margin-bottom: 1.25rem;
                }
                .deact-badge-dot {
                    width: 6px;
                    height: 6px;
                    border-radius: 50%;
                    background: #ef4444;
                    animation: qDeactPulse 1.5s infinite;
                }
                .deact-desc {
                    color: #475569;
                    font-size: 0.95rem;
                    line-height: 1.6;
                    margin-bottom: 1.75rem;
                }
                .deact-box {
                    background: #f8fafc;
                    border: 1px solid #e2e8f0;
                    border-radius: 14px;
                    padding: 1.25rem;
                    text-align: left;
                    margin-bottom: 1.5rem;
                }
                .deact-box label {
                    font-size: 0.825rem;
                    font-weight: 700;
                    color: #334155;
                    margin-bottom: 0.5rem;
                    display: block;
                }
                .deact-textarea {
                    width: 100%;
                    border: 1px solid #cbd5e1;
                    border-radius: 10px;
                    padding: 0.75rem 0.875rem;
                    font-size: 0.9rem;
                    color: #0f172a;
                    outline: none;
                    transition: border-color 0.2s, box-shadow 0.2s;
                    resize: vertical;
                    min-height: 95px;
                    background: #ffffff;
                    font-family: inherit;
                }
                .deact-textarea:focus {
                    border-color: #2563eb;
                    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
                }
                .deact-actions {
                    display: flex;
                    gap: 0.75rem;
                    justify-content: flex-end;
                    margin-top: 1rem;
                }
                .deact-btn-submit {
                    background: #2563eb;
                    color: #ffffff;
                    border: none;
                    border-radius: 10px;
                    padding: 0.65rem 1.25rem;
                    font-size: 0.875rem;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.2s;
                    display: inline-flex;
                    align-items: center;
                    gap: 6px;
                }
                .deact-btn-submit:hover {
                    background: #1d4ed8;
                }
                .deact-btn-logout {
                    background: #f1f5f9;
                    color: #475569;
                    border: 1px solid #cbd5e1;
                    border-radius: 10px;
                    padding: 0.65rem 1.25rem;
                    font-size: 0.875rem;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.2s;
                }
                .deact-btn-logout:hover {
                    background: #e2e8f0;
                    color: #0f172a;
                }
                @keyframes qDeactFade { from { opacity: 0; transform: scale(0.97); } to { opacity: 1; transform: scale(1); } }
                @keyframes qDeactPulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
            </style>
            <div class="deact-card">
                <div class="deact-header-stripe"></div>
                <div class="deact-body">
                    <div class="deact-icon-box">
                        <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
                            <circle cx="8.5" cy="7" r="4"></circle>
                            <line x1="18" y1="8" x2="23" y2="13"></line>
                            <line x1="23" y1="8" x2="18" y2="13"></line>
                        </svg>
                    </div>
                    <div class="deact-badge"><span class="deact-badge-dot"></span> Account Deactivated</div>
                    <h2 class="deact-title">Dashboard Frozen</h2>
                    <p class="deact-desc">
                        Hello <strong>${profile.full_name || profile.username}</strong>, your account has been deactivated by your organization administrator. All dashboard access and actions are currently frozen. Please submit a request below to notify your administrator.
                    </p>

                    <div class="deact-box">
                        <label for="q-deact-msg">Submit Reactivation Request</label>
                        <textarea id="q-deact-msg" class="deact-textarea" placeholder="State your request or reason for account reactivation (e.g. Need access to project workflows)..."></textarea>
                        <div id="q-deact-feedback"></div>
                        <div class="deact-actions">
                            <button type="button" class="deact-btn-logout" onclick="window.logout()">Log Out</button>
                            <button type="button" id="q-deact-submit-btn" class="deact-btn-submit" onclick="window.submitUserReactivationRequest()">
                                Send Request to Administrator
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(overlay);
    }

    window.submitUserReactivationRequest = async function () {
        const msgInput = document.getElementById('q-deact-msg');
        const btn = document.getElementById('q-deact-submit-btn');
        const feedback = document.getElementById('q-deact-feedback');
        const msg = msgInput ? msgInput.value.trim() : '';

        if (!msg) {
            feedback.innerHTML = '<div style="color:#ef4444; font-size:0.85rem; margin-top:8px; font-weight:600;">⚠️ Please enter a message for your administrator.</div>';
            return;
        }

        if (btn) {
            btn.disabled = true;
            btn.innerText = 'Submitting Request...';
        }

        try {
            const token = sessionStorage.getItem('token') || localStorage.getItem('token');
            const res = await fetch('/api/auth/user-reactivation-request', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ message: msg })
            });
            const data = await res.json();
            if (res.ok) {
                feedback.innerHTML = '<div style="color:#059669; background:#ecfdf5; border:1px solid #a7f3d0; padding:12px 14px; border-radius:10px; font-size:0.85rem; margin-top:12px; font-weight:600;">✓ ' + (data.message || 'Your reactivation request has been sent to your administrator successfully.') + '</div>';
                if (msgInput) msgInput.disabled = true;
                if (btn) btn.style.display = 'none';
            } else {
                feedback.innerHTML = '<div style="color:#ef4444; font-size:0.85rem; margin-top:8px; font-weight:600;">⚠️ ' + (data.msg || data.message || 'Failed to submit request.') + '</div>';
                if (btn) {
                    btn.disabled = false;
                    btn.innerText = 'Send Request to Administrator';
                }
            }
        } catch (err) {
            feedback.innerHTML = '<div style="color:#ef4444; font-size:0.85rem; margin-top:8px; font-weight:600;">⚠️ Connection error. Please try again.</div>';
            if (btn) {
                btn.disabled = false;
                btn.innerText = 'Send Request to Administrator';
            }
        }
    };

    // Export logout globally
    window.logout = function () {
        try {
            sessionStorage.clear();
            localStorage.removeItem('token');
            localStorage.removeItem('access_token');
            localStorage.removeItem('user');
            localStorage.removeItem('role_permissions');
            sessionStorage.removeItem('role_permissions');
        } catch (_) {}
        window.location.replace('/auth/login.html?logout=true');
    };

    // Force check on back/forward navigation
    window.addEventListener('pageshow', (event) => {
        if (event.persisted) {
            window.location.reload();
        }
    });
})();

// ─────────────────────────────────────────────────────────────────────────────
// Enterprise Feature Flag & Module Runtime Evaluator
// ─────────────────────────────────────────────────────────────────────────────
window.QCMSFeatures = {
    flags: {},
    loaded: false,
    async init() {
        const token = sessionStorage.getItem('token') || localStorage.getItem('token') || localStorage.getItem('access_token');
        try {
            const headers = {};
            if (token) headers['Authorization'] = `Bearer ${token}`;
            const res = await fetch('/api/feature-engine/flags', { headers });
            if (res.ok) {
                const json = await res.json();
                this.flags = json.flags || json.data || {};
                this.loaded = true;
                this.applyDOMVisibility();
            }
        } catch (e) {
            console.warn('[QCMSFeatures] Failed to load feature flags', e);
        }
    },
    isEnabled(code) {
        if (!code) return true;
        if (this.flags && this.flags[code] === false) return false;
        return true;
    },
    applyDOMVisibility() {
        if (!this.flags || Object.keys(this.flags).length === 0) return;
        
        // Super Admin control panel must NOT hide or disable Super Admin interface elements!
        if (window.location.pathname.includes('/admin/super-admin.html')) return;

        // 1. Tagged elements with [data-feature]
        document.querySelectorAll('[data-feature]').forEach(el => {
            const code = el.getAttribute('data-feature');
            if (code && !this.isEnabled(code)) {
                el.style.display = 'none !important';
                el.classList.add('d-none');
                el.setAttribute('disabled', 'true');
            }
        });

        // 2. Selectors from QCMS_MODULE_MAP for disabled modules
        if (window.QCMS_MODULE_MAP) {
            Object.keys(this.flags).forEach(code => {
                if (this.flags[code] === false) {
                    const mod = window.QCMS_MODULE_MAP[code];
                    if (mod && mod.selectors) {
                        mod.selectors.forEach(sel => {
                            try {
                                document.querySelectorAll(sel).forEach(el => {
                                    el.style.display = 'none';
                                    el.classList.add('d-none', 'feature-deactivated');
                                    el.setAttribute('disabled', 'true');
                                    if (el.tagName === 'BUTTON' || el.tagName === 'A') {
                                        el.style.pointerEvents = 'none';
                                        el.style.opacity = '0.4';
                                    }
                                });
                            } catch(e) {}
                        });
                    }
                }
            });
        }
    }
};

document.addEventListener('DOMContentLoaded', () => {
    window.QCMSFeatures.init();
});


