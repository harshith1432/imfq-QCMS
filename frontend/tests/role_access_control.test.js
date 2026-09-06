const test = require('node:test');
const assert = require('node:assert/strict');

test('Role-Based Access Control & User Manual Action Button Suite', async (t) => {
    // 1. Test User Manual Action Button Rule
    function canShowUserManualAction(userRoleKey, currentRoleKey, hasActionUrl) {
        if (!hasActionUrl) return false;
        return (
            (userRoleKey === 'super-admin' && currentRoleKey === 'super-admin') ||
            (userRoleKey === 'admin' && currentRoleKey === 'admin')
        );
    }

    await t.test('SuperAdmin only sees action buttons when viewing SuperAdmin manual', () => {
        assert.strictEqual(canShowUserManualAction('super-admin', 'super-admin', true), true);
        assert.strictEqual(canShowUserManualAction('super-admin', 'super-admin', false), false);

        assert.strictEqual(canShowUserManualAction('super-admin', 'admin', true), false);
        assert.strictEqual(canShowUserManualAction('super-admin', 'ceo', true), false);
        assert.strictEqual(canShowUserManualAction('super-admin', 'reviewer', true), false);
        assert.strictEqual(canShowUserManualAction('super-admin', 'facilitator', true), false);
        assert.strictEqual(canShowUserManualAction('super-admin', 'team-leader', true), false);
        assert.strictEqual(canShowUserManualAction('super-admin', 'team-member', true), false);
    });

    await t.test('Organization Admin only sees action buttons when viewing Admin manual', () => {
        assert.strictEqual(canShowUserManualAction('admin', 'admin', true), true);
        assert.strictEqual(canShowUserManualAction('admin', 'admin', false), false);

        assert.strictEqual(canShowUserManualAction('admin', 'super-admin', true), false);
        assert.strictEqual(canShowUserManualAction('admin', 'ceo', true), false);
        assert.strictEqual(canShowUserManualAction('admin', 'reviewer', true), false);
        assert.strictEqual(canShowUserManualAction('admin', 'facilitator', true), false);
        assert.strictEqual(canShowUserManualAction('admin', 'team-leader', true), false);
        assert.strictEqual(canShowUserManualAction('admin', 'team-member', true), false);
    });

    await t.test('All other roles NEVER see any action buttons on any manual', () => {
        const otherRoles = ['ceo', 'reviewer', 'facilitator', 'team-leader', 'team-member', 'viewer', 'guest'];
        const allManualTabs = ['super-admin', 'admin', 'ceo', 'reviewer', 'facilitator', 'team-leader', 'team-member'];

        for (const role of otherRoles) {
            for (const tab of allManualTabs) {
                assert.strictEqual(
                    canShowUserManualAction(role, tab, true),
                    false,
                    'Role ' + role + ' viewing tab ' + tab + ' should NOT see action button'
                );
            }
        }
    });

    // 2. Test Role Normalization
    function normalizeRole(role) {
        if (!role) return null;
        let roleStr = role;
        if (typeof role === 'object') {
            roleStr = role.name || role.role_name || role.role || '';
        }
        if (!roleStr || typeof roleStr !== 'string') return null;
        const r = roleStr.trim().toLowerCase();
        if (r.includes('super')) return 'SuperAdmin';
        if (r === 'admin' || r.includes('organization admin') || r.includes('org admin') || r.includes('organization_admin') || r === 'owner') return 'Admin';
        if (r.includes('leader')) return 'Team Leader';
        if (r.includes('member')) return 'Team Member';
        if (r.includes('facilitator')) return 'Facilitator';
        if (r.includes('reviewer')) return 'Reviewer';
        if (r.includes('ceo') || r.includes('exec')) return 'CEO';
        return roleStr;
    }

    await t.test('normalizeRole maps all role variations correctly', () => {
        assert.strictEqual(normalizeRole('SuperAdmin'), 'SuperAdmin');
        assert.strictEqual(normalizeRole('super admin'), 'SuperAdmin');
        assert.strictEqual(normalizeRole('super_admin'), 'SuperAdmin');
        assert.strictEqual(normalizeRole('super-admin'), 'SuperAdmin');

        assert.strictEqual(normalizeRole('Admin'), 'Admin');
        assert.strictEqual(normalizeRole('admin'), 'Admin');
        assert.strictEqual(normalizeRole('org admin'), 'Admin');
        assert.strictEqual(normalizeRole('organization admin'), 'Admin');
        assert.strictEqual(normalizeRole('owner'), 'Admin');

        assert.strictEqual(normalizeRole('Team Leader'), 'Team Leader');
        assert.strictEqual(normalizeRole('teamleader'), 'Team Leader');
        assert.strictEqual(normalizeRole('team_leader'), 'Team Leader');

        assert.strictEqual(normalizeRole('Team Member'), 'Team Member');
        assert.strictEqual(normalizeRole('teammember'), 'Team Member');
        assert.strictEqual(normalizeRole('team_member'), 'Team Member');

        assert.strictEqual(normalizeRole('Reviewer'), 'Reviewer');
        assert.strictEqual(normalizeRole('reviewer'), 'Reviewer');

        assert.strictEqual(normalizeRole('Facilitator'), 'Facilitator');
        assert.strictEqual(normalizeRole('facilitator'), 'Facilitator');

        assert.strictEqual(normalizeRole('CEO'), 'CEO');
        assert.strictEqual(normalizeRole('ceo'), 'CEO');
        assert.strictEqual(normalizeRole('Executive'), 'CEO');

        assert.strictEqual(normalizeRole({ name: 'SuperAdmin' }), 'SuperAdmin');
        assert.strictEqual(normalizeRole({ role_name: 'admin' }), 'Admin');
    });

    // 3. Test RBAC Route Protection Matrix
    const dashboardPermissions = {
        'dashboard-admin.html': ['Admin'],
        'dashboard-ceo.html': ['CEO', 'Admin'],
        'dashboard-reviewer.html': ['Reviewer', 'Admin'],
        'dashboard-facilitator.html': ['Facilitator', 'Admin'],
        'dashboard-team-leader.html': ['Team Leader', 'Admin'],
        'dashboard-team-member.html': ['Team Member', 'Team Leader', 'Admin']
    };

    const adminOnlyPages = [
        'plants.html',
        'departments.html',
        'stage-template.html',
        'sop-masters.html',
        'subscriptions.html',
        'users.html',
        'user-management.html'
    ];

    function checkAccess(userRole, page) {
        const normRole = normalizeRole(userRole) || 'Team Member';
        const isSuperAdmin = (normRole === 'SuperAdmin');

        if (isSuperAdmin) {
            if (page === 'dashboard.html' || dashboardPermissions[page]) return { allowed: false, redirect: '/admin/super-admin.html' };
            if (page === 'stage-template.html') return { allowed: false, redirect: '/admin/super-admin-stage-template.html' };
            if (['plants.html', 'departments.html', 'sop-masters.html', 'subscriptions.html'].includes(page)) {
                return { allowed: false, redirect: '/admin/super-admin.html' };
            }
            return { allowed: true };
        }

        if (page.includes('super-admin')) {
            return { allowed: false, redirect: 'role-dashboard' };
        }

        if (dashboardPermissions[page]) {
            if (!dashboardPermissions[page].includes(normRole)) {
                return { allowed: false, redirect: 'role-dashboard' };
            }
        }

        if (adminOnlyPages.includes(page) && normRole !== 'Admin') {
            return { allowed: false, redirect: 'role-dashboard' };
        }

        return { allowed: true };
    }

    await t.test('Route access rules strictly isolate roles', () => {
        assert.strictEqual(checkAccess('SuperAdmin', 'dashboard-admin.html').allowed, false);
        assert.strictEqual(checkAccess('SuperAdmin', 'dashboard-team-member.html').allowed, false);
        assert.strictEqual(checkAccess('SuperAdmin', 'plants.html').allowed, false);
        assert.strictEqual(checkAccess('SuperAdmin', 'super-admin.html').allowed, true);

        assert.strictEqual(checkAccess('Admin', 'super-admin.html').allowed, false);
        assert.strictEqual(checkAccess('Team Member', 'super-admin.html').allowed, false);
        assert.strictEqual(checkAccess('CEO', 'super-admin.html').allowed, false);

        assert.strictEqual(checkAccess('Team Member', 'dashboard-admin.html').allowed, false);
        assert.strictEqual(checkAccess('Team Leader', 'dashboard-admin.html').allowed, false);
        assert.strictEqual(checkAccess('Reviewer', 'dashboard-admin.html').allowed, false);
        assert.strictEqual(checkAccess('Facilitator', 'dashboard-admin.html').allowed, false);
        assert.strictEqual(checkAccess('CEO', 'dashboard-admin.html').allowed, false);
        assert.strictEqual(checkAccess('Admin', 'dashboard-admin.html').allowed, true);

        for (const adminPage of adminOnlyPages) {
            assert.strictEqual(checkAccess('Team Member', adminPage).allowed, false, 'Team Member should not access ' + adminPage);
            assert.strictEqual(checkAccess('Reviewer', adminPage).allowed, false, 'Reviewer should not access ' + adminPage);
            assert.strictEqual(checkAccess('Admin', adminPage).allowed, true, 'Admin should access ' + adminPage);
        }
    });
});
