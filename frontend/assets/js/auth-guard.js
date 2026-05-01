(function () {
    const token = localStorage.getItem('token');
    const userStr = localStorage.getItem('user');
    let userRole = null;

    if (token) {
        try {
            const user = JSON.parse(userStr);
            if (user && user.role) {
                userRole = user.role;
            } else {
                // Token exists but user data is missing or corrupt
                throw new Error('Invalid user data');
            }
        } catch (e) {
            console.warn('Auth state corrupt. Clearing session...');
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            window.location.replace('login.html');
            return;
        }
    }

    const path = window.location.pathname;
    const page = path.split('/').pop() || 'index.html';

    // Pages that DON'T need protection
    const publicPages = [
        'index.html',
        'login.html',
        'register.html',
        'register-org.html',
        'forgot-password.html',
        'reset-password.html'
    ];

    const isPublic = publicPages.includes(page) || path === '/' || path.endsWith('/');
    const isAuthPage = ['login.html', 'index.html', 'dashboard.html'].includes(page) || path === '/' || path.endsWith('/');

    if (!token && !isPublic) {
        console.log('Access denied. Redirecting to login...');
        window.location.replace('login.html');
        return;
    }

    if (token) {
        if (isAuthPage) {
            console.log('Already logged in. Redirecting to role dashboard...');
            redirectByRole(userRole);
        } else if (page.startsWith('dashboard-')) {
            validateDashboardAccess(userRole, page);
        }
    }

    function validateDashboardAccess(role, currentPage) {
        const dashboardMap = {
            'Admin': 'dashboard-admin.html',
            'Reviewer': 'dashboard-reviewer.html',
            'Facilitator': 'dashboard-facilitator.html',
            'Team Leader': 'dashboard-team-leader.html',
            'Team Member': 'dashboard-team-member.html'
        };

        const expectedDashboard = dashboardMap[role] || 'dashboard-team-member.html';
        if (currentPage !== expectedDashboard) {
            console.warn(`Role ${role} unauthorized for ${currentPage}. Redirecting to ${expectedDashboard}`);
            window.location.replace(expectedDashboard);
        }
    }

    function redirectByRole(role) {
        const dashboardMap = {
            'Admin': 'dashboard-admin.html',
            'Reviewer': 'dashboard-reviewer.html',
            'Facilitator': 'dashboard-facilitator.html',
            'Team Leader': 'dashboard-team-leader.html',
            'Team Member': 'dashboard-team-member.html'
        };
        const dashboard = dashboardMap[role] || 'dashboard-team-member.html';
        if (page !== dashboard) {
            window.location.replace(dashboard);
        }
    }

    // Export logout globally
    window.logout = function () {
        localStorage.clear();
        sessionStorage.clear();
        window.location.replace('login.html');
    };

    // Force check on back/forward navigation
    window.addEventListener('pageshow', (event) => {
        if (event.persisted) {
            window.location.reload();
        }
    });
})();
