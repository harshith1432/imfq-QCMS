/**
 * Project Details Controller for Team Leader
 */

const projectDetails = {
    projectId: new URLSearchParams(window.location.search).get('id'),

    init() {
        if (typeof QCMS !== 'undefined') QCMS.init();
        
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

            // Render Stepper
            const stepper = document.getElementById('stepperContainer');
            if (stepper && typeof QCMS !== 'undefined') {
                stepper.innerHTML = QCMS.stageStepper(data.stage);
            }

            const memberList = document.getElementById('memberList');
            memberList.innerHTML = '';
            if (!data.members || data.members.length === 0) {
                 memberList.innerHTML = '<div class="text-xs text-muted">No stakeholders assigned.</div>';
            } else {
                 data.members.forEach(m => {
                    const initials = m.name.substring(0, 2).toUpperCase();
                    memberList.innerHTML += `
                        <div class="h-stack gap-2 glass-panel px-2 py-1" style="border-radius: 8px; background: rgba(var(--ds-primary-rgb), 0.03); border: 1px solid var(--ds-border-color);">
                            <div class="ds-avatar ds-avatar-xs" style="width:20px; height:20px; font-size:9px;">${initials}</div>
                            <span class="text-xs fw-bold ds-text-main">${m.name}</span>
                        </div>
                    `;
                 });
            }

            this.setupStages(data.stage, data.proposal);
            if (window.lucide) lucide.createIcons();
        } catch (err) {
            console.error(err);
            QCMS.toast('Critical: Failed to synchronize project state.', 'error');
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
            QCMS.toast(`Operational stage ${currentStageValue} validated. Proceeding to next phase.`, 'success');
            this.loadDetails();
        } catch (err) {
            QCMS.toast('State transition failed: ' + err.message, 'error');
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
            QCMS.toast('Strategic proposal dispatched to Reviewer.', 'success');
            this.loadDetails();
        } catch (err) {
            QCMS.toast('Proposal submission failed: ' + err.message, 'error');
        }
    }
};

document.addEventListener('DOMContentLoaded', () => {
    projectDetails.init();
});
