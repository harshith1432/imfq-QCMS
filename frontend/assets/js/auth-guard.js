(function () {
    const token = localStorage.getItem('token');
    let userRole = null;
    try {
        const user = JSON.parse(localStorage.getItem('user'));
        userRole = user ? user.role : null;
    } catch (e) {
        console.error('Error parsing user data:', e);
    }

    const path = window.location.pathname;

    // pages that DON'T need protection
    const publicPages = [
        'index.html',
        'login.html',
        'register.html',
        'register-org.html',
        'forgot-password.html',
        'reset-password.html'
    ];

    const isPublic = publicPages.some(page => path.includes(page)) || path === '/' || path.endsWith('/');
    const isAuthPage = path.includes('login.html') || path.includes('index.html') || path.includes('dashboard.html') || path === '/' || path.endsWith('/');

    if (!token && !isPublic) {
        // Not logged in and trying to access protected page
        console.log('Access denied. Redirecting to login...');
        window.location.replace('login.html');
        return;
    }

    if (token) {
        if (isAuthPage) {
            // Already logged in and trying to access login/index/dashboard
            console.log('Already logged in or on landing. Redirecting to role dashboard...');
            redirectByRole(userRole);
        } else if (path.includes('dashboard-')) {
            // Strict role-dashboard check
            validateDashboardAccess(userRole, path);
        }
    }

    function validateDashboardAccess(role, currentPath) {
        const dashboardMap = {
            'Admin': 'dashboard-admin.html',
            'Reviewer': 'dashboard-reviewer.html',
            'Facilitator': 'dashboard-facilitator.html',
            'Team Leader': 'dashboard-team-leader.html',
            'Team Member': 'dashboard-team-member.html'
        };

        const expectedDashboard = dashboardMap[role] || 'dashboard-team-member.html';
        if (!currentPath.includes(expectedDashboard)) {
            console.warn(`Role ${role} unauthorized for ${currentPath}. Redirecting to ${expectedDashboard}`);
            window.location.replace(expectedDashboard);
        }
    }

    function redirectByRole(role) {
        let dashboard = 'dashboard-team-member.html';
        switch (role) {
            case 'Admin': dashboard = 'dashboard-admin.html'; break;
            case 'Facilitator': dashboard = 'dashboard-facilitator.html'; break;
            case 'Reviewer': dashboard = 'dashboard-reviewer.html'; break;
            case 'Team Leader': dashboard = 'dashboard-team-leader.html'; break;
            case 'Team Member': dashboard = 'dashboard-team-member.html'; break;
        }

        if (!path.includes(dashboard)) {
            window.location.replace(dashboard);
        }
    }

    // Export logout globally
    window.logout = function () {
        localStorage.clear();
        sessionStorage.clear();
        window.location.replace('login.html');
    };
    // Force check on back/forward navigation (bfcache)
    window.addEventListener('pageshow', (event) => {
        if (event.persisted) {
            window.location.reload();
        }
    });
})();
