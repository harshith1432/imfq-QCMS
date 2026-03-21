/**
 * Project Details Controller for Team Leader
 */

const projectDetails = {
    projectId: new URLSearchParams(window.location.search).get('id'),

    init() {
        console.log("Team Leader Project Details Initialized");
        if (!this.projectId) {
            window.location.href = 'dashboard-team-leader.html';
            return;
        }
        this.loadDetails();
        this.bindEvents();
    },

    bindEvents() {
        document.getElementById('proposalForm')?.addEventListener('submit', (e) => this.submitProposal(e));
    },

    async loadDetails() {
        try {
            const data = await api.get(`/team-leader/projects/${this.projectId}`);
            document.getElementById('projectTitleDisplay').textContent = data.title;
            document.getElementById('projectUidDisplay').textContent = `UID: ${data.uid}`;
            document.getElementById('stageBadge').textContent = `Stage ${data.stage}`;
            document.getElementById('projectDesc').textContent = data.description;
            document.getElementById('projectStatus').textContent = data.status;

            const memberList = document.getElementById('memberList');
            memberList.innerHTML = '';
            if (data.members.length === 0) {
                 memberList.innerHTML = '<li>No members assigned</li>';
            } else {
                 data.members.forEach(m => {
                    memberList.innerHTML += `<li>${m.name}</li>`;
                 });
            }

            this.setupStages(data.stage, data.proposal);
        } catch (err) {
            console.error(err);
            alert('Failed to load project details: ' + err.message);
        }
    },

    setupStages(currentStage, proposal) {
        // Reset dynamic areas
        document.getElementById('stage2Action')?.classList.add('d-none');
        document.getElementById('proposalForm')?.classList.add('d-none');
        document.getElementById('proposalReadonly')?.classList.add('d-none');
        document.getElementById('stage7Action')?.classList.add('d-none');

        // Logic for Stage 2
        if (currentStage === 2) {
            document.getElementById('stage2Action')?.classList.remove('d-none');
        }

        // Logic for Stage 4
        if (currentStage === 4) {
            document.getElementById('proposalForm')?.classList.remove('d-none');
        } else if (currentStage > 4 && proposal) {
            document.getElementById('proposalReadonly')?.classList.remove('d-none');
        }

        // Logic for Stage 7
        if (currentStage === 7) {
            document.getElementById('stage7Action')?.classList.remove('d-none');
        }

        // Expand corresponding accordion panel
        const targetTarget = `#stage${currentStage}`;
        const targetBtn = document.querySelector(`[data-bs-target="${targetTarget}"]`);
        
        if (targetBtn && targetBtn.classList.contains('collapsed')) {
            targetBtn.click();
        }
    },

    async proceedStage(currentStageValue) {
        if (!confirm(`Confirm validation and proceed from Stage ${currentStageValue}?`)) return;

        try {
            await api.post(`/team-leader/action/${this.projectId}/proceed`, {
                stage: currentStageValue
            });
            alert('Project successfully advanced to the next stage.');
            this.loadDetails(); // Reload to reflect new stage
        } catch (err) {
            alert('Failed to proceed: ' + err.message);
        }
    },

    async submitProposal(e) {
        e.preventDefault();
        const form = e.target;
        
        try {
            let kpiData = {};
            try {
                kpiData = JSON.parse(form.kpis.value);
            } catch (jsonErr) {
                 alert('Invalid JSON format for KPI targets.');
                 return;
            }

            const payload = {
                budget_required: parseFloat(form.budget.value),
                estimated_roi: parseFloat(form.roi.value),
                resource_plan: form.resources.value,
                kpi_targets: kpiData
            };

            await api.post(`/team-leader/submit-proposal/${this.projectId}`, payload);
            alert('Proposal submitted successfully! It is now with the Reviewer.');
            this.loadDetails();
        } catch (err) {
            alert('Failed to submit proposal: ' + err.message);
        }
    }
};

document.addEventListener('DOMContentLoaded', () => {
    projectDetails.init();
});
