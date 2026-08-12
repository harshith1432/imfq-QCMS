// Login Logic
document.getElementById('loginForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = (document.getElementById('username')?.value || '').trim();
    const password = document.getElementById('password')?.value || '';
    const errorMsg = document.getElementById('errorMsg');

    try {
        const loginBtn = document.getElementById('loginBtn');
        const data = await api.post('/auth/login', { username, password }, { button: loginBtn });
        if (!data || !data.access_token) {
            throw new Error(data?.msg || data?.message || "Invalid username or password");
        }
        sessionStorage.setItem('token', data.access_token);
        localStorage.setItem('token', data.access_token);

        const userPayload = JSON.stringify({
            username: data.username,
            email: data.email,
            role: data.role,
            org_id: data.org_id,
            org_name: data.org_name,
            dept_id: data.dept_id,
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
        
        // Sync global language
        if (data.language) {
            localStorage.setItem('qcms-language', data.language);
            if (window.i18n) window.i18n.setLanguage(data.language);
        }

        if (data.is_temp_password) {
            window.location.href = '/auth/reset-password.html';
            return;
        }

        // Role-based redirection
        const role = data.role;
        if (role === 'SuperAdmin') window.location.href = '/admin/super-admin.html';
        else if (role === 'Admin') window.location.href = '/dashboard/dashboard-admin.html';
        else if (role === 'Reviewer') window.location.href = '/dashboard/dashboard-reviewer.html';
        else if (role === 'Facilitator') window.location.href = '/dashboard/dashboard-facilitator.html';
        else if (role === 'Team Leader') window.location.href = '/dashboard/dashboard-team-member.html';
        else if (role === 'CEO') window.location.href = '/dashboard/dashboard-ceo.html';
        else window.location.href = '/dashboard/dashboard-team-member.html';
    } catch (err) {
        if (errorMsg) {
            const span = errorMsg.querySelector('span');
            if (span) span.textContent = err.message;
            else errorMsg.textContent = err.message;
            errorMsg.style.setProperty('display', 'flex', 'important');
        }
    } finally {
        const loginBtn = document.getElementById('loginBtn');
        if (loginBtn) {
            if (window.ActionLock) {
                window.ActionLock.unlockButton(loginBtn);
            }
            loginBtn.disabled = false;
            loginBtn.style.pointerEvents = '';
            loginBtn.style.cursor = '';
            loginBtn.innerHTML = 'Sign In';
        }
    }
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
    sessionStorage.clear();
    window.location.href = '/auth/login.html';
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
