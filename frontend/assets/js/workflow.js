let currentProject = null;
let currentStageId = 1;
const projectId = new URLSearchParams(window.location.search).get('id');

const stages = [
    { title: "Stage 1: Identification", description: "Define the problem and its scope." },
    { title: "Stage 2: Selection", description: "Select the project and set objectives." },
    { title: "Stage 3: Analysis", description: "Analyze the problem with data and charts." },
    { title: "Stage 4: Causes", description: "Identify potential causes (Fishbone/5-Why)." },
    { title: "Stage 5: Root Cause (RCA)", description: "Validate and confirm the root cause." },
    { title: "Stage 6: Data Analysis", description: "Verify root cause with data-driven analysis." },
    { title: "Stage 7: Development", description: "Develop and propose the solution." },
    { title: "Stage 8: Implementation", description: "Implement, measure impact, and close." }
];

async function initWorkspace() {
    if (!projectId) return window.location.href = 'projects.html';
    
    try {
        currentProject = await api.get(`/projects/${projectId}`);
        document.getElementById('wkTitle').textContent = currentProject.title;
        document.getElementById('wkUID').textContent = `Project UID: ${currentProject.project_uid}`;
        
        const statusEl = document.getElementById('wkStatus');
        statusEl.textContent = currentProject.status.toUpperCase();
        statusEl.className = 'status-pill ' + (currentProject.status === 'Closed' ? 'active' : 'warning');
        
        currentStageId = currentProject.current_stage;
        updateStepper();
        loadStageContent();
        checkReviewerAccess();
    } catch (err) {
        alert('Error loading project: ' + err.message);
    }
}

function updateStepper() {
    document.querySelectorAll('.step').forEach(step => {
        const sId = parseInt(step.dataset.step);
        step.classList.remove('active', 'completed');
        if (sId === currentStageId) {
            step.classList.add('active');
        } else if (sId < currentStageId) {
            step.classList.add('completed');
        }
    });
}

async function loadStageContent() {
    const stageData = await api.get(`/workflow/${projectId}/stage/${currentStageId}`);
    const data = stageData.data || {};
    
    const container = document.getElementById('stageBody');
    container.innerHTML = `
        <h2 style="margin-bottom: 0.5rem;">${stages[currentStageId-1].title}</h2>
        <p class="text-muted" style="margin-bottom: 2rem;">${stages[currentStageId-1].description}</p>
        
        <div id="stageForm">
            ${getStageFields(currentStageId, data)}
        </div>
    `;
    
    // Hide submit button if pending approval
    const submitBtn = document.getElementById('submitBtn');
    if (currentProject.status === 'Pending Approval') {
        submitBtn.disabled = true;
        submitBtn.innerHTML = 'Pending Review...';
    }
}

function getStageFields(step, data) {
    if (step === 1) {
        return `
            <div class="form-group">
                <label>Problem Statement</label>
                <textarea id="f_problem" placeholder="Describe the current issue and its impact..." rows="6">${data.problem || ''}</textarea>
            </div>
        `;
    }
    if (step === 3) {
        return `
            <div class="form-group">
                <label>Root Causes (Comma separated)</label>
                <input type="text" id="f_rca" value="${data.causes || ''}" placeholder="e.g., Equipment Malfunction, Training Gap, Material Defect">
            </div>
            <div style="margin-top:2rem; padding:3rem; border:2px dashed #E5E7EB; border-radius:12px; text-align:center; background: #F9FAFB;">
                <i data-lucide="network" style="color: var(--primary); margin-bottom: 1rem;"></i>
                <p class="text-muted" style="font-weight: 500;">Interactive Fishbone Diagram Tool</p>
                <span style="font-size: 0.75rem; color: #9CA3AF;">Visualizer loading in specialized analysis mode...</span>
            </div>
        `;
    }
    return `
        <div class="form-group">
            <label>Stage Notes & Supplemental Data</label>
            <textarea id="f_general" placeholder="Enter findings, data points, or progress notes..." rows="8">${data.notes || ''}</textarea>
        </div>
    `;
}

async function saveStageData() {
    const formData = {};
    if (document.getElementById('f_problem')) formData.problem = document.getElementById('f_problem').value;
    if (document.getElementById('f_rca')) formData.causes = document.getElementById('f_rca').value;
    if (document.getElementById('f_general')) formData.notes = document.getElementById('f_general').value;

    try {
        await api.post(`/workflow/${projectId}/stage/${currentStageId}`, formData);
        alert('Draft saved successfully');
    } catch (err) {
        alert(err.message);
    }
}

async function submitStage() {
    try {
        await api.post(`/workflow/${projectId}/submit`, {});
        window.location.reload();
    } catch (err) {
        alert(err.message);
    }
}

function checkReviewerAccess() {
    const user = JSON.parse(localStorage.getItem('user') || '{}');
    const panel = document.getElementById('reviewerControls');
    if ((user.role === 'Reviewer' || user.role === 'Admin') && currentProject.status === 'Pending Approval') {
        panel.style.display = 'block';
    }
}

async function handleReview(status) {
    const comments = document.getElementById('reviewComment').value;
    try {
        await api.post(`/workflow/${projectId}/approve`, { status, comments });
        window.location.reload();
    } catch (err) {
        alert(err.message);
    }
}

document.addEventListener('DOMContentLoaded', initWorkspace);
