/**
 * Workspace Controller — Unified project workspace for all roles.
 * Uses the centralized api.js helper (api.get/api.post).
 */
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    lucide.createIcons();

    const user = JSON.parse(localStorage.getItem('user'));
    
    // Set up Back button based on role
    const backBtn = document.getElementById('backToDashBtn');
    if (user.role === 'Admin') backBtn.href = 'dashboard-admin.html';
    else if (user.role === 'Team Leader') backBtn.href = 'dashboard-team-leader.html';
    else if (user.role === 'Reviewer') backBtn.href = 'dashboard-reviewer.html';
    else if (user.role === 'Facilitator') backBtn.href = 'dashboard-facilitator.html';
    else backBtn.href = 'dashboard-team-member.html';

    document.getElementById('wkRoleTag').textContent = `Role: ${user.role}`;

    const urlParams = new URLSearchParams(window.location.search);
    const projectId = urlParams.get('id');

    if (!projectId) {
        alert("No Project ID specified!");
        window.location.href = backBtn.href;
        return;
    }

    const workspace = {
        project: null,
        currentViewStage: 1,
        paretoChartInstance: null,

        init() {
            this.loadProjectDetails();
            this.setupFormListener();
        },

        async loadProjectDetails() {
            try {
                const data = await api.get(`/projects/${projectId}`);
                
                this.project = data;
                
                document.getElementById('wkTitle').textContent = this.project.title;
                document.getElementById('wkUID').textContent = `UID: ${this.project.uid || this.project.project_uid || ''} | Status: ${this.project.status}`;
                document.getElementById('wkCurrentStageBadge').textContent = `Current Stage: ${this.project.current_stage || this.project.stage}`;
                
                this.renderTabs();
                this.loadStageData(this.project.current_stage || this.project.stage || 1);
                
            } catch (error) {
                console.error("Error loading workspace data:", error);
                alert("Failed to load project or unauthorized access: " + (error.message || ''));
            }
        },

        renderTabs() {
            const tabsContainer = document.getElementById('stageTabs');
            tabsContainer.innerHTML = '';
            
            const stageNames = [
                "1. Identification",
                "2. Selection",
                "3. Analysis",
                "4. Causes",
                "5. Root Cause",
                "6. Data Analysis",
                "7. Development",
                "8. Implementation"
            ];

            const currentStage = this.project.current_stage || this.project.stage || 1;

            for (let i = 1; i <= 8; i++) {
                const btn = document.createElement('button');
                btn.className = `nav-link ${i === currentStage ? 'active' : ''}`;
                if (i > currentStage) {
                    btn.classList.add('locked');
                }
                btn.textContent = stageNames[i - 1];
                btn.onclick = (e) => {
                    e.preventDefault();
                    if (i <= currentStage) {
                        document.querySelectorAll('.nav-link').forEach(el => el.classList.remove('active'));
                        btn.classList.add('active');
                        this.loadStageData(i);
                    } else {
                        alert("This stage is locked until previous stages are completed.");
                    }
                };
                tabsContainer.appendChild(btn);
            }
        },

        async loadStageData(stageNumber) {
            this.currentViewStage = stageNumber;
            const currentStage = this.project.current_stage || this.project.stage || 1;
            
            // Switch UI Panes
            document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('show', 'active'));
            const targetPane = document.getElementById(`stage${stageNumber}`);
            if (targetPane) targetPane.classList.add('show', 'active');

            // Apply read-only / role-locking logic
            const lockedMsg = document.getElementById('lockedMessage');
            const submitBtn = document.querySelector('#formActions button[type="submit"]');

            let isReadOnly = false;
            let lockReason = "";

            if (stageNumber < currentStage) {
                isReadOnly = true;
                lockReason = "This stage is already completed and is now read-only.";
            } else if (stageNumber === 5 && user.role === 'Team Member') {
                isReadOnly = true;
                lockReason = "Stage 5 (Approval) is strictly for Reviewing Officers.";
            } else if (currentStage === 5 && stageNumber === 5 && user.role !== 'Reviewer') {
                 isReadOnly = true;
                 lockReason = "Awaiting Reviewer Approval.";
            }
            
            // Populate form with existing stage data from backend
            try {
                const stageData = await api.get(`/projects/${projectId}/stage/${stageNumber}`);
                const form = document.getElementById('stageForm');
                form.reset();
                
                if (stageData && typeof stageData === 'object') {
                    for (const key in stageData) {
                        const input = form.elements[key];
                        if (input) {
                            // Check if it's a date or textarea or input
                            input.value = stageData[key] || '';
                        }
                    }
                }
            } catch (err) {
                console.error("Error fetching stage details:", err);
            }

            if (isReadOnly) {
                document.getElementById('stageContentArea').classList.add('readonly-mode');
                lockedMsg.classList.remove('d-none');
                lockedMsg.innerHTML = `<i data-lucide="lock" class="me-2"></i> ${lockReason}`;
                if (submitBtn) submitBtn.disabled = true;
            } else {
                document.getElementById('stageContentArea').classList.remove('readonly-mode');
                lockedMsg.classList.add('d-none');
                if (submitBtn) submitBtn.disabled = false;
            }

            if (stageNumber === 3) {
                this.renderPareto();
            }
            
            lucide.createIcons();
        },

        renderPareto() {
            const jsonText = document.getElementById('paretoDataInput')?.value;
            if (!jsonText) return;
            
            try {
                const data = JSON.parse(jsonText);
                if (!Array.isArray(data)) throw new Error("Format must be an array of objects");
                
                // Sort descending by frequency
                data.sort((a,b) => b.freq - a.freq);
                
                const labels = data.map(d => d.cause);
                const frequencies = data.map(d => d.freq);
                
                // Calculate cumulative percentages
                const total = frequencies.reduce((a,b) => a+b, 0);
                let runningSum = 0;
                const cumulativePercents = frequencies.map(f => {
                    runningSum += f;
                    return (runningSum / total) * 100;
                });

                const ctx = document.getElementById('paretoChart')?.getContext('2d');
                if (!ctx) return;
                
                if (this.paretoChartInstance) {
                    this.paretoChartInstance.destroy();
                }

                this.paretoChartInstance = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: labels,
                        datasets: [
                            {
                                type: 'line',
                                label: 'Cumulative %',
                                data: cumulativePercents,
                                borderColor: '#ef4444',
                                backgroundColor: '#ef4444',
                                borderWidth: 2,
                                yAxisID: 'y1',
                                tension: 0.1
                            },
                            {
                                type: 'bar',
                                label: 'Frequency',
                                data: frequencies,
                                backgroundColor: '#0061ff',
                                yAxisID: 'y'
                            }
                        ]
                    },
                    options: {
                        responsive: true,
                        scales: {
                            y: {
                                beginAtZero: true,
                                position: 'left',
                                title: { display: true, text: 'Frequency' }
                            },
                            y1: {
                                beginAtZero: true,
                                max: 100,
                                position: 'right',
                                title: { display: true, text: 'Cumulative %' },
                                grid: { drawOnChartArea: false }
                            }
                        }
                    }
                });

            } catch (e) {
                console.warn("Pareto data not ready or invalid JSON.");
            }
        },

        setupFormListener() {
            document.getElementById('stageForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const formData = new FormData(e.target);
                const dataPayload = {};
                
                for (let [key, value] of formData.entries()) {
                    if (value.trim() !== '') {
                        dataPayload[key] = value;
                    }
                }

                const submitBtn = e.target.querySelector('button[type="submit"]');
                const originalText = submitBtn.innerHTML;
                submitBtn.innerHTML = 'Saving...';
                submitBtn.disabled = true;

                try {
                    const result = await api.post(`/projects/${projectId}/stage/${this.currentViewStage}`, dataPayload);
                    
                    alert(result.msg || `Stage ${this.currentViewStage} data saved successfully!`);
                    this.loadProjectDetails();
                    
                } catch (error) {
                    console.error("Save error:", error);
                    alert(error.message || "Failed to save data. Please try again.");
                } finally {
                    submitBtn.innerHTML = originalText;
                    submitBtn.disabled = false;
                }
            });
        }
    };

    window.workspace = workspace;
    workspace.init();
});
