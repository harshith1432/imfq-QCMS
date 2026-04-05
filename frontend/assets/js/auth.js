// Login Logic
document.getElementById('loginForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const errorMsg = document.getElementById('errorMsg');

    try {
        const data = await api.post('/auth/login', { username, password });
        localStorage.setItem('token', data.access_token);
        localStorage.setItem('user', JSON.stringify({
            username: data.username,
            role: data.role,
            org_id: data.org_id,
            dept_id: data.dept_id,
            is_temp_password: data.is_temp_password
        }));

        if (data.is_temp_password) {
            window.location.href = 'reset-password.html';
            return;
        }

        // Role-based redirection
        const role = data.role;
        if (role === 'Admin') window.location.href = 'dashboard-admin.html';
        else if (role === 'Reviewer') window.location.href = 'dashboard-reviewer.html';
        else if (role === 'Facilitator') window.location.href = 'dashboard-facilitator.html';
        else if (role === 'Team Leader') window.location.href = 'dashboard-team-leader.html';
        else window.location.href = 'dashboard-team-member.html';
    } catch (err) {
        errorMsg.textContent = err.message;
        errorMsg.style.display = 'block';
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
            window.location.href = 'login.html';
        }, 2000);
    } catch (err) {
        errorMsg.textContent = err.message;
        errorMsg.style.display = 'block';
    }
});

function logout() {
    localStorage.clear();
    window.location.href = 'login.html';
}

function checkAuth() {
    const token = localStorage.getItem('token');
    const path = window.location.pathname;

    // Improved detection including extensionless paths
    const isAuthPage = path.includes('login') ||
        path.includes('register') ||
        path.includes('reset-password');

    if (!token && !isAuthPage && !path.endsWith('/') && !path.includes('index.html')) {
        window.location.href = 'login.html';
        return;
    }

    // Force password reset if flagged
    if (token && !path.includes('reset-password.html')) {
        try {
            const user = JSON.parse(localStorage.getItem('user'));
            if (user && user.is_temp_password) {
                window.location.href = 'reset-password.html';
            }
        } catch (e) {
            console.error('Auth state error:', e);
        }
    }
}

// Redirect if already logged in on login/register page
function handleStaticRedirects() {
    const token = localStorage.getItem('token');
    const path = window.location.pathname;
    const isLoginPage = path.includes('login.html') || (path.endsWith('/login'));
    const isRegisterPage = path.includes('register.html') || (path.endsWith('/register'));

    if ((isLoginPage || isRegisterPage) && token) {
        try {
            const user = JSON.parse(localStorage.getItem('user'));
            if (user && user.role) {
                const role = user.role;
                if (role === 'Admin') window.location.href = 'dashboard-admin.html';
                else if (role === 'Reviewer') window.location.href = 'dashboard-reviewer.html';
                else if (role === 'Facilitator') window.location.href = 'dashboard-facilitator.html';
                else if (role === 'Team Leader') window.location.href = 'dashboard-team-leader.html';
                else window.location.href = 'dashboard-team-member.html';
            } else {
                // Token exists but user object is corrupt/missing — clear it
                localStorage.removeItem('token');
                localStorage.removeItem('user');
            }
        } catch (e) {
            localStorage.clear();
        }
    }
}

// Run checks
checkAuth();
handleStaticRedirects();

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
