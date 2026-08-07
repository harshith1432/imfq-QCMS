/**
 * Workspace Controller — Unified project workspace for all roles.
 * Uses the centralized api.js helper (api.get/api.post).
 */
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    lucide.createIcons();

    const user = JSON.parse(sessionStorage.getItem('user'));
    
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
                "1. S0/S1 Plan & Establish Team",
                "2. S2 Define Problem",
                "3. S3 Interim Containment",
                "4. S4 Determine Root Causes",
                "5. S5 Choose Permanent Corrections",
                "6. S6 Implement Corrective Actions",
                "7. S7 Take Preventive Measures",
                "8. S8 Congratulate Team & Closure"
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
            
            const role = (user.role || '').toLowerCase().replace(/[^a-z0-9]/g, '');

            const isProjectRejected = (project && project.status && (project.status === 'Rejected' || project.status.includes('Rejected')));

            if (stageNumber < currentStage && !isProjectRejected) {
                isReadOnly = true;
                lockReason = "This stage is already completed and is now read-only.";
            } else if (stageNumber === 1 && !['admin', 'superadmin', 'teamleader', 'teammember'].includes(role)) {
                isReadOnly = true;
                lockReason = "Only Admin, Team Leader and Team Members can add/edit Stage 1 details.";
            } else if (stageNumber >= 2 && stageNumber <= 8 && !['teammember', 'teamleader', 'admin', 'superadmin'].includes(role)) {
                isReadOnly = true;
                lockReason = "Only Team Members, Team Leader and Admin can add/edit details for this stage.";
            } else if (stageNumber === 5 && role === 'teammember' && !isProjectRejected) {
                isReadOnly = true;
                lockReason = "Stage 5 (Approval) is strictly for Reviewing Officers.";
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
        },

        openQCTools() {
            const modal = new bootstrap.Modal(document.getElementById('qcToolsModal'));
            modal.show();
            this.switchQCTool('checksheet');
        },

        switchQCTool(toolId, event) {
            if (event) event.preventDefault();
            
            // Update active state in sidebar
            const navLinks = document.querySelectorAll('#qcToolsNav .nav-link');
            navLinks.forEach(link => link.classList.remove('active', 'bg-light', 'text-primary'));
            const activeLink = document.querySelector(`#qcToolsNav .nav-link[data-tool="${toolId}"]`);
            if (activeLink) {
                activeLink.classList.add('active', 'bg-light', 'text-primary');
            }

            const contentArea = document.getElementById('qcToolContent');
            
            // Basic templates for each tool (simulated integration)
            const templates = {
                'checksheet': `
                    <h5>Check Sheet</h5>
                    <p class="text-muted text-sm mb-4">Structured data collection grid for tracking defects, events, or occurrences.</p>
                    <table class="table table-sm table-bordered">
                        <thead class="bg-light">
                            <tr><th>Defect Type</th><th>Monday</th><th>Tuesday</th><th>Wednesday</th><th>Thursday</th><th>Friday</th><th>Total</th></tr>
                        </thead>
                        <tbody>
                            <tr><td>Surface Scratches</td><td>|||</td><td>||</td><td>|</td><td>||||</td><td>||</td><td>12</td></tr>
                            <tr><td>Dimensional Error</td><td>|</td><td></td><td>||</td><td>|</td><td>|</td><td>5</td></tr>
                            <tr><td>Contamination</td><td></td><td>|</td><td></td><td></td><td></td><td>1</td></tr>
                        </tbody>
                    </table>
                    <div class="mt-3"><button class="btn btn-sm btn-primary">Add Row</button></div>
                `,
                'histogram': `
                    <h5>Histogram</h5>
                    <p class="text-muted text-sm mb-4">Frequency distribution of continuous data to visualize process capability.</p>
                    <div style="height: 300px; width: 100%;"><canvas id="qcHistogram"></canvas></div>
                `,
                'pareto': `
                    <h5>Pareto Chart</h5>
                    <p class="text-muted text-sm mb-4">80/20 rule visualization to identify the most significant factors.</p>
                    <div style="height: 300px; width: 100%;"><canvas id="qcPareto"></canvas></div>
                `,
                'fishbone': `
                    <h5>Cause & Effect (Fishbone) Diagram</h5>
                    <p class="text-muted text-sm mb-4">Structured brainstorming for root causes grouped by categories (Man, Machine, Material, Method, Measurement, Mother Nature).</p>
                    <div class="border rounded p-4 text-center bg-light" style="min-height: 250px; display: flex; align-items: center; justify-content: center;">
                        <span class="text-muted"><i data-lucide="git-merge" class="mb-2" style="width:32px;height:32px;"></i><br>Interactive Fishbone UI Module</span>
                    </div>
                `,
                'controlchart': `
                    <h5>Control Chart</h5>
                    <p class="text-muted text-sm mb-4">Time-series plot with Upper and Lower Control Limits (UCL/LCL) to track process stability.</p>
                    <div style="height: 300px; width: 100%;"><canvas id="qcControlChart"></canvas></div>
                `,
                'scatter': `
                    <h5>Scatter Diagram</h5>
                    <p class="text-muted text-sm mb-4">Plots paired data points to visualize correlation between two variables.</p>
                    <div style="height: 300px; width: 100%;"><canvas id="qcScatter"></canvas></div>
                `,
                'stratification': `
                    <h5>Stratification</h5>
                    <p class="text-muted text-sm mb-4">Separating data gathered from a variety of sources to see patterns.</p>
                    <div style="height: 300px; width: 100%;"><canvas id="qcStratification"></canvas></div>
                `
            };

            contentArea.innerHTML = templates[toolId] || '<p>Tool not found.</p>';
            if (window.lucide) lucide.createIcons();

            // Render Charts if applicable
            setTimeout(() => this.renderQCChart(toolId), 100);
        },

        renderQCChart(toolId) {
            if (!window.Chart) return;
            
            // Clean up previous charts if they exist
            if (this.currentQCChart) {
                this.currentQCChart.destroy();
                this.currentQCChart = null;
            }
            
            if (toolId === 'histogram') {
                const ctx = document.getElementById('qcHistogram');
                if (!ctx) return;
                this.currentQCChart = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: ['10-20', '20-30', '30-40', '40-50', '50-60', '60-70'],
                        datasets: [{ label: 'Frequency', data: [5, 12, 25, 18, 8, 2], backgroundColor: 'rgba(59, 130, 246, 0.7)', borderWidth: 1, borderColor: 'rgb(59, 130, 246)' }]
                    },
                    options: { maintainAspectRatio: false, scales: { x: { display: false, barPercentage: 1.0, categoryPercentage: 1.0 } } }
                });
            } else if (toolId === 'pareto') {
                const ctx = document.getElementById('qcPareto');
                if (!ctx) return;
                this.currentQCChart = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: ['Scratches', 'Dimensions', 'Dents', 'Contamination', 'Other'],
                        datasets: [
                            { type: 'line', label: 'Cumulative %', data: [45, 75, 90, 96, 100], borderColor: 'rgb(245, 158, 11)', yAxisID: 'y1', tension: 0.1 },
                            { type: 'bar', label: 'Defects', data: [45, 30, 15, 6, 4], backgroundColor: 'rgba(59, 130, 246, 0.7)' }
                        ]
                    },
                    options: { maintainAspectRatio: false, scales: { y1: { type: 'linear', position: 'right', min: 0, max: 100 } } }
                });
            } else if (toolId === 'controlchart') {
                const ctx = document.getElementById('qcControlChart');
                if (!ctx) return;
                this.currentQCChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: ['1','2','3','4','5','6','7','8','9','10'],
                        datasets: [
                            { label: 'Sample Mean', data: [10.1, 9.8, 10.3, 10.0, 9.9, 10.2, 10.5, 9.7, 10.1, 10.0], borderColor: 'rgb(59, 130, 246)', tension: 0 },
                            { label: 'UCL (10.6)', data: [10.6,10.6,10.6,10.6,10.6,10.6,10.6,10.6,10.6,10.6], borderColor: 'rgba(239, 68, 68, 0.5)', borderDash: [5, 5], pointRadius: 0, fill: false },
                            { label: 'LCL (9.4)', data: [9.4,9.4,9.4,9.4,9.4,9.4,9.4,9.4,9.4,9.4], borderColor: 'rgba(239, 68, 68, 0.5)', borderDash: [5, 5], pointRadius: 0, fill: false }
                        ]
                    },
                    options: { maintainAspectRatio: false }
                });
            } else if (toolId === 'scatter') {
                const ctx = document.getElementById('qcScatter');
                if (!ctx) return;
                this.currentQCChart = new Chart(ctx, {
                    type: 'scatter',
                    data: {
                        datasets: [{
                            label: 'Speed vs Error Rate',
                            data: [{x: 100, y: 2}, {x: 110, y: 2.5}, {x: 120, y: 3.1}, {x: 130, y: 4.8}, {x: 140, y: 5.5}, {x: 150, y: 8.2}],
                            backgroundColor: 'rgba(59, 130, 246, 0.7)'
                        }]
                    },
                    options: { maintainAspectRatio: false, scales: { x: { title: { display: true, text: 'Machine Speed (RPM)' } }, y: { title: { display: true, text: 'Error Rate (%)' } } } }
                });
            } else if (toolId === 'stratification') {
                const ctx = document.getElementById('qcStratification');
                if (!ctx) return;
                this.currentQCChart = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: ['Shift 1', 'Shift 2', 'Shift 3'],
                        datasets: [
                            { label: 'Machine A', data: [12, 19, 8], backgroundColor: 'rgba(59, 130, 246, 0.7)' },
                            { label: 'Machine B', data: [5, 15, 20], backgroundColor: 'rgba(245, 158, 11, 0.7)' }
                        ]
                    },
                    options: { maintainAspectRatio: false, scales: { x: { stacked: true }, y: { stacked: true } } }
                });
            }
        }
    };

    window.workspace = workspace;
    workspace.init();
});
