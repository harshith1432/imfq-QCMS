const admin = {
    currentSection: 'overview',
    charts: {},

    init: async function() {
        console.log("Admin module initializing...");
        this.showSection('overview');
        this.loadStats();
        
        // Initialize Lucide icons
        if (window.lucide) {
            window.lucide.createIcons();
        }
    },

    showSection: function(sectionId) {
        this.currentSection = sectionId;
        
        // Update tabs
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.innerText.toLowerCase().includes(sectionId));
        });

        // Update views
        document.querySelectorAll('.admin-view').forEach(view => {
            view.classList.toggle('active', view.id === sectionId + 'Section');
        });

        // Load data based on section
        if (sectionId === 'users') this.loadUsers();
        if (sectionId === 'audit') this.loadAuditLogs();
        if (sectionId === 'overview') this.loadStats();
    },

    loadStats: async function() {
        try {
            const stats = await api.get('/admin/stats');
            
            document.getElementById('adminUserCount').innerText = stats.users;
            document.getElementById('adminProjectCount').innerText = stats.projects;
            document.getElementById('adminActiveCount').innerText = stats.active_projects;
            
            this.renderStageChart(stats.stage_distribution);
        } catch (error) {
            console.error("Failed to load admin stats:", error);
        }
    },

    renderStageChart: function(distribution) {
        const ctx = document.getElementById('stageDistributionChart').getContext('2d');
        if (this.charts.stage) this.charts.stage.destroy();

        const labels = Object.keys(distribution).map(s => `Stage ${s}`);
        const data = Object.values(distribution);

        this.charts.stage = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: ['#8B5CF6', '#3B82F6', '#10B981', '#F59E0B', '#EF4444', '#6366F1', '#EC4899', '#14B8A6']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'right' } }
            }
        });
    },

    loadUsers: async function() {
        try {
            const users = await api.get('/admin/users');
            const tbody = document.getElementById('usersTableBody');
            tbody.innerHTML = '';

            users.forEach(user => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>
                        <div class="user-info">
                            <span class="font-bold">${user.username}</span>
                        </div>
                    </td>
                    <td>${user.email}</td>
                    <td><span class="role-badge ${user.role.toLowerCase().replace(' ', '-')}">${user.role}</span></td>
                    <td>${user.department}</td>
                    <td>
                        <span class="status-pill ${user.is_active ? 'active' : 'inactive'}">
                            ${user.is_active ? 'Active' : 'Inactive'}
                        </span>
                    </td>
                    <td>
                        <div class="action-btns">
                            <button class="action-btn" onclick="admin.editUser(${user.id})" title="Edit">
                                <i data-lucide="edit-3" style="width: 14px"></i>
                            </button>
                            <button class="action-btn" onclick="admin.resetPassword(${user.id})" title="Reset Password">
                                <i data-lucide="key" style="width: 14px"></i>
                            </button>
                            <button class="action-btn" onclick="admin.toggleUserStatus(${user.id}, ${user.is_active})" title="${user.is_active ? 'Deactivate' : 'Activate'}">
                                <i data-lucide="${user.is_active ? 'user-x' : 'user-check'}" style="width: 14px"></i>
                            </button>
                        </div>
                    </td>
                `;
                tbody.appendChild(tr);
            });
            
            lucide.createIcons();
        } catch (error) {
            console.error("Failed to load users:", error);
        }
    },

    loadAuditLogs: async function() {
        try {
            const logs = await api.get('/admin/audit-logs');
            const tbody = document.getElementById('auditTableBody');
            tbody.innerHTML = '';

            logs.forEach(log => {
                const tr = document.createElement('tr');
                const time = new Date(log.timestamp).toLocaleString();
                tr.innerHTML = `
                    <td class="text-xs">${time}</td>
                    <td><span class="font-semibold">${log.user}</span></td>
                    <td><span class="uid-pill">${log.action}</span></td>
                    <td>${log.target}</td>
                    <td class="text-xs text-muted">${JSON.stringify(log.details)}</td>
                `;
                tbody.appendChild(tr);
            });
        } catch (error) {
            console.error("Failed to load audit logs:", error);
        }
    },

    openUserModal: function() {
        // Implementation for user creation modal
        alert("User creation modal will be implemented next.");
    },

    toggleUserStatus: async function(userId, currentStatus) {
        if (!confirm(`Are you sure you want to ${currentStatus ? 'deactivate' : 'activate'} this user?`)) return;
        
        try {
            await api.put(`/admin/users/${userId}`, { is_active: !currentStatus });
            this.loadUsers();
        } catch (error) {
            alert("Action failed: " + (error.message || "Unknown error"));
        }
    }
};

document.addEventListener('DOMContentLoaded', () => {
    if (window.location.pathname.includes('dashboard-admin.html')) {
        admin.init();
    }
});
