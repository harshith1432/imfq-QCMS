async function loadProjects() {
    try {
        const projects = await api.get('/projects');
        const list = document.getElementById('projectsList');
        list.innerHTML = projects.map(p => `
            <tr>
                <td class="uid-pill">#${p.project_uid}</td>
                <td class="font-medium text-main">${p.title}</td>
                <td>
                    <div class="progress-container">
                        <div class="progress-bar" style="width: ${(p.current_stage/8)*100}%"></div>
                    </div>
                    <span class="text-muted" style="font-size: 0.75rem;">Stage D${p.current_stage} Validation</span>
                </td>
                <td>
                    <span class="status-pill ${p.status === 'Closed' ? 'active' : 'warning'}">
                        ${p.status}
                    </span>
                </td>
                <td class="text-right">
                    <button class="btn btn-outline-sm" onclick="window.location.href='workspace.html?id=${p.id}'">
                        Manage
                    </button>
                </td>
            </tr>
        `).join('');
        lucide.createIcons();
    } catch (err) {
        console.error('Fetch error:', err);
    }
}

function showCreateModal() {
    document.getElementById('createModal').style.display = 'flex';
}

function hideCreateModal() {
    document.getElementById('createModal').style.display = 'none';
}

document.getElementById('createProjectForm')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const title = document.getElementById('projectTitle').value;
    const description = document.getElementById('projectDesc').value;

    try {
        await api.post('/projects', { title, description });
        hideCreateModal();
        loadProjects();
    } catch (err) {
        alert(err.message);
    }
});

document.addEventListener('DOMContentLoaded', loadProjects);
