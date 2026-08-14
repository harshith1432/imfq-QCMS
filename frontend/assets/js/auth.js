// Login Logic

// ── Lockout countdown helpers ─────────────────────────────────────────────────
let _lockoutTimer = null;

function _startLockoutCountdown(remainingSeconds, errorMsgEl, loginBtnEl) {
    // Clear any previous timer
    if (_lockoutTimer) clearInterval(_lockoutTimer);

    let secondsLeft = remainingSeconds;

    function _fmt(s) {
        const m = Math.floor(s / 60);
        const sec = s % 60;
        return `${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
    }

    function _render() {
        if (!errorMsgEl) return;
        const span = errorMsgEl.querySelector('span');
        const timeStr = _fmt(secondsLeft);
        const msg = secondsLeft > 0
            ? `Account locked due to too many failed attempts. Try again in ${timeStr}.`
            : 'Lockout expired. You can now try signing in.';
        if (span) span.innerHTML = msg;
        else errorMsgEl.textContent = msg;
        errorMsgEl.style.setProperty('display', 'flex', 'important');
    }

    // Disable the button
    if (loginBtnEl) {
        loginBtnEl.disabled = true;
        loginBtnEl.innerHTML = '<span style="display:flex;align-items:center;justify-content:center;gap:8px"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>Locked</span>';
    }

    _render();

    _lockoutTimer = setInterval(() => {
        secondsLeft -= 1;
        _render();
        if (secondsLeft <= 0) {
            clearInterval(_lockoutTimer);
            _lockoutTimer = null;
            // Re-enable the button
            if (loginBtnEl) {
                loginBtnEl.disabled = false;
                loginBtnEl.innerHTML = 'Sign In';
            }
            // Clear the error after 2s
            setTimeout(() => {
                if (errorMsgEl) errorMsgEl.style.setProperty('display', 'none', 'important');
            }, 2000);
        }
    }, 1000);
}
// ──────────────────────────────────────────────────────────────────────────────

document.getElementById('loginForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    // Block submission if account is still locked (countdown active)
    if (_lockoutTimer) return;

    const username = (document.getElementById('username')?.value || '').trim();
    const password = document.getElementById('password')?.value || '';
    const errorMsg = document.getElementById('errorMsg');

    let isLoggingIn = false;
    const attemptLogin = async (isRetry = false) => {
        if (isLoggingIn && !isRetry) return;
        isLoggingIn = true;
        let isTimeout = false;
        let loginSuccess = false;
        const loginBtn = document.getElementById('loginBtn');

        try {
            if (isRetry) {
                if (loginBtn) loginBtn.innerHTML = '<span style="display:flex;align-items:center;justify-content:center;gap:8px"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="animation:spin 1s linear infinite"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>Retrying...</span>';
                if (errorMsg) {
                    const span = errorMsg.querySelector('span');
                    const msg = 'Server is warming up, retrying now...';
                    if (span) span.textContent = msg;
                    else errorMsg.textContent = msg;
                    errorMsg.style.setProperty('display', 'flex', 'important');
                }
            } else if (loginBtn) {
                loginBtn.disabled = true;
                loginBtn.innerHTML = '<span style="display:flex;align-items:center;justify-content:center;gap:8px"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="animation:spin 1s linear infinite"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>Authenticating...</span>';
            }

            const data = await api.post('/auth/login', { username, password }, { button: null });
            if (!data || !data.access_token) {
                throw new Error(data?.msg || data?.message || "Invalid username or password");
            }
            sessionStorage.setItem('token', data.access_token);
            localStorage.setItem('token', data.access_token);

            const userPayload = JSON.stringify({
                username: data.username,
                email: data.email,
                role: data.role,
                role_name: data.role_name || data.role,
                role_permissions: data.role_permissions || null,
                org_id: data.org_id,
                org_name: data.org_name,
                dept_id: data.department_id || data.dept_id,
                department_id: data.department_id || data.dept_id,
                department: data.department || data.department_name,
                department_name: data.department_name || data.department,
                plant_id: data.plant_id,
                plant_name: data.plant_name || data.location,
                location: data.location || data.plant_name,
                custom_fields: data.custom_fields || {},
                subscription_plan: data.subscription_plan,
                subscription_status: data.subscription_status,
                is_temp_password: data.is_temp_password,
                id: data.id,
                language: data.language,
                org_timezone: data.org_timezone,
                org_primary_color: data.org_primary_color || null,
                org_logo_url: data.org_logo_url || null,
                org_favicon_url: data.org_favicon_url || null
            });

            sessionStorage.setItem('user', userPayload);
            localStorage.setItem('user', userPayload);
            if (data.role_permissions) {
                sessionStorage.setItem('role_permissions', JSON.stringify(data.role_permissions));
                localStorage.setItem('role_permissions', JSON.stringify(data.role_permissions));
            }
            
            // Sync global language
            if (data.language) {
                localStorage.setItem('qcms-language', data.language);
                if (window.i18n) window.i18n.setLanguage(data.language);
            }

            loginSuccess = true;
            if (loginBtn) {
                loginBtn.disabled = true;
                loginBtn.innerHTML = '<span style="display:flex;align-items:center;justify-content:center;gap:8px"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="animation:spin 1s linear infinite"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>Redirecting to dashboard...</span>';
            }

            if (data.is_temp_password) {
                window.location.replace('/auth/reset-password.html');
                return;
            }

            // Role-based redirection
            const role = data.role;
            let targetDashboard = '/dashboard/dashboard-team-member.html';
            if (role === 'SuperAdmin') targetDashboard = '/admin/super-admin.html';
            else if (role === 'Admin') targetDashboard = '/dashboard/dashboard-admin.html';
            else if (role === 'Reviewer') targetDashboard = '/dashboard/dashboard-reviewer.html';
            else if (role === 'Facilitator') targetDashboard = '/dashboard/dashboard-facilitator.html';
            else if (role === 'Team Leader') targetDashboard = '/dashboard/dashboard-team-member.html';
            else if (role === 'CEO') targetDashboard = '/dashboard/dashboard-ceo.html';
            
            window.location.replace(targetDashboard);
        } catch (err) {
            isLoggingIn = false;
            if (err.isTimeout) {
                isTimeout = true;
            }
            // On first timeout, auto-retry once after 15 seconds
            if (err.isTimeout && !isRetry) {
                if (errorMsg) {
                    const span = errorMsg.querySelector('span');
                    const msg = '⏳ Server is warming up. Auto-retrying in 15 seconds...';
                    if (span) span.textContent = msg;
                    else errorMsg.textContent = msg;
                    errorMsg.style.setProperty('display', 'flex', 'important');
                }
                if (loginBtn) loginBtn.innerHTML = '<span style="display:flex;align-items:center;justify-content:center;gap:8px"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="animation:spin 1s linear infinite"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>Warming up...</span>';
                setTimeout(() => attemptLogin(true), 15000);
                return;
            }

            // ── ACCOUNT_LOCKED: show countdown ───────────────────────────────
            if (err.error_code === 'ACCOUNT_LOCKED' || (err.status === 429 && err.message && err.message.toLowerCase().includes('locked'))) {
                const remaining = err.remaining_seconds || 900; // fallback 15 min
                _startLockoutCountdown(remaining, errorMsg, loginBtn);
                return; // Don't fall through to the generic handler
            }
            // ────────────────────────────────────────────────────────────────

            if (errorMsg) {
                const span = errorMsg.querySelector('span');
                const displayTxt = (err.message && err.message !== 'API Error' && err.message !== 'Request failed. Please try again.') ? err.message : 'Invalid username or password';
                if (span) span.textContent = displayTxt;
                else errorMsg.textContent = displayTxt;
                errorMsg.style.setProperty('display', 'flex', 'important');
            }
        } finally {
            if (!loginSuccess && (!isTimeout || isRetry) && !_lockoutTimer) {
                isLoggingIn = false;
                if (loginBtn) {
                    if (window.ActionLock) window.ActionLock.unlockButton(loginBtn);
                    loginBtn.disabled = false;
                    loginBtn.style.pointerEvents = '';
                    loginBtn.style.cursor = '';
                    loginBtn.innerHTML = 'Sign In';
                }
            }
        }
    };

    await attemptLogin();
});


// Registration Logic
document.getElementById('registerForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('username').value;
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const confirm_password = document.getElementById('confirm_password').value;
    const errorMsg = document.getElementById('errorMsg');
    const successMsg = document.getElementById('successMsg');

    if (password !== confirm_password) {
        errorMsg.textContent = "Passwords do not match";
        errorMsg.style.display = 'block';
        return;
    }

    errorMsg.style.display = 'none';
    if (successMsg) successMsg.style.display = 'none';

    try {
        await api.post('/auth/register', {
            username,
            email,
            password,
            role: 'Team Member' // Default role for self-registration
        });
        if (successMsg) {
            successMsg.textContent = 'Registration successful! Redirecting to login...';
            successMsg.style.display = 'block';
        } else {
            alert('Registration successful! Redirecting to login...');
        }
        setTimeout(() => {
            window.location.href = '/auth/login.html';
        }, 2000);
    } catch (err) {
        errorMsg.textContent = err.message;
        errorMsg.style.display = 'block';
    }
});

function logout() {
    try {
        sessionStorage.clear();
        localStorage.removeItem('token');
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
        localStorage.removeItem('role_permissions');
        sessionStorage.removeItem('role_permissions');
    } catch (_) {}
    window.location.replace('/auth/login.html?logout=true');
}

function checkAuth() {
    const token = sessionStorage.getItem('token');
    const path = window.location.pathname;

    // Improved detection including extensionless paths
    const isAuthPage = path.includes('login') ||
        path.includes('register') ||
        path.includes('reset-password');

    if (!token && !isAuthPage && !path.endsWith('/') && !path.includes('index.html')) {
        window.location.href = '/auth/login.html';
        return;
    }

    // Force password reset if flagged
    if (token && !path.includes('reset-password.html')) {
        try {
            const user = JSON.parse(sessionStorage.getItem('user'));
            if (user && user.is_temp_password) {
                window.location.href = '/auth/reset-password.html';
            }
        } catch (e) {
            console.error('Auth state error:', e);
        }
    }
}

// Redirect if already logged in on login/register page
function handleStaticRedirects() {
    const token = sessionStorage.getItem('token');
    const path = window.location.pathname;
    const isLoginPage = path.includes('login.html') || (path.endsWith('/login'));
    const isRegisterPage = path.includes('register.html') || (path.endsWith('/register'));

    if ((isLoginPage || isRegisterPage) && token) {
        try {
            const user = JSON.parse(sessionStorage.getItem('user'));
            if (user && user.role) {
                const role = user.role;
                if (role === 'SuperAdmin') window.location.href = '/admin/super-admin.html';
                else if (role === 'Admin') window.location.href = '/dashboard/dashboard-admin.html';
                else if (role === 'Reviewer') window.location.href = '/dashboard/dashboard-reviewer.html';
                else if (role === 'Facilitator') window.location.href = '/dashboard/dashboard-facilitator.html';
                else if (role === 'Team Leader') window.location.href = '/dashboard/dashboard-team-member.html';
                else if (role === 'CEO') window.location.href = '/dashboard/dashboard-ceo.html';
                else window.location.href = '/dashboard/dashboard-team-member.html';
            } else {
                // Token exists but user object is corrupt/missing — clear it
                sessionStorage.removeItem('token');
                sessionStorage.removeItem('user');
            }
        } catch (e) {
            sessionStorage.clear();
        }
    }
}

// Run checks — Now handled primarily by auth-guard.js
// checkAuth();
// handleStaticRedirects();

function togglePassword(inputId, icon) {
    const input = document.getElementById(inputId);
    if (input.type === 'password') {
        input.type = 'text';
        icon.classList.remove('fa-eye');
        icon.classList.add('fa-eye-slash');
    } else {
        input.type = 'password';
        icon.classList.remove('fa-eye-slash');
        icon.classList.add('fa-eye');
    }
}
