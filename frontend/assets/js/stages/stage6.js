const Stage6 = {
    renderHTML() {
        return `
            <!-- STAGE 6 FORM -->
            <div id="stage6Form">
                <!-- Section 1 - Countermeasure Task Assignments -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">6.1</span>
                                Countermeasure Task Assignments
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Team members can view and update completion.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <div>
                                <h6 class="fw-bold mb-0 text-primary">Section 6.1 - Countermeasure Task Assignments</h6>
                            </div>
                            <button type="button" class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[6].addTaskRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Task
                            </button>
                        </div>
                        <div class="row text-muted small fw-bold mb-2 px-2">
                            <div class="col-3">Countermeasure</div>
                            <div class="col-2">Owner</div>
                            <div class="col-2">Task</div>
                            <div class="col-2">Due Date</div>
                            <div class="col-2" title="Completion percentage" style="cursor:help;">Comp %</div>
                            <div class="col-1"></div>
                        </div>
                        <div id="s6_taskContainer" class="mb-0">
                        </div>
                    </div>
                </div>

                <!-- Section 2 - Resource Deployment -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">6.2</span>
                                Resource Deployment
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Track the actual deployment of the budget, manpower, and materials planned in Stage 5.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary">Section 6.2 - Resource Deployment</h6>
                            <button type="button" class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[6].addResourceRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Resource
                            </button>
                        </div>
                        <div class="row text-muted small fw-bold mb-2 px-2">
                            <div class="col-4">Resource</div>
                            <div class="col-2">Planned Cost</div>
                            <div class="col-2">Actual Cost</div>
                            <div class="col-3">Variance</div>
                            <div class="col-1"></div>
                        </div>
                        <div id="s6_resourceContainer" class="mb-0">
                        </div>
                    </div>
                </div>

                <!-- Section 3 - Change Management -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">6.3</span>
                                Change Management
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Executed once all countermeasures are completed. Used for implementing approved changes.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <div>
                                <h6 class="fw-bold mb-0 text-primary">Section 6.3 - Change Management</h6>
                                <small class="text-muted">Executed once all countermeasures are completed. Used for implementing approved changes.</small>
                            </div>
                            <button type="button" id="s6_addChangeBtn" class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[6].addChangeRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Change
                            </button>
                        </div>

                        <div class="row text-muted small fw-bold mb-2 px-2">
                            <div class="col-6">Change Description</div>
                            <div class="col-2">SOP Updated (Y/N)</div>
                            <div class="col-3">Date</div>
                            <div class="col-1"></div>
                        </div>
                        <div id="s6_changeContainer" class="mb-0">
                        </div>
                    </div>
                </div>

                <!-- Section 4 - Risk & Resistance Management -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">6.4</span>
                                Risk &amp; Resistance Management
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Identify implementation risks and organizational resistance, and how each was addressed.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary">Section 6.4 - Risk &amp; Resistance Management</h6>
                            <button type="button" class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[6].addRiskRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Risk
                            </button>
                        </div>
                        <div class="row text-muted small fw-bold mb-2 px-2">
                            <div class="col-5">Anticipated Risk/Resistance</div>
                            <div class="col-4">Strategy Executed</div>
                            <div class="col-2">Status</div>
                            <div class="col-1"></div>
                        </div>
                        <div id="s6_riskContainer" class="mb-0">
                        </div>
                    </div>
                </div>

                <!-- Section 5 - Side Effect Analysis -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">6.5</span>
                                Side Effect Analysis
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Analyze potential negative side effects of the solutions. Modifications to the plan may be needed.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <div>
                                <h6 class="fw-bold mb-0 text-primary">Section 6.5 - Side Effect Analysis</h6>
                                <small class="text-muted">Analyze potential negative side effects of the solutions. Modifications to the plan may be needed.</small>
                            </div>
                            <button type="button" class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[6].addSideEffectRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Side Effect
                            </button>
                        </div>

                        <!-- Side Effect Warning Alert -->
                        <div id="s6_plan_mod_warning" class="alert alert-danger py-2 px-3 text-xs mb-3 shadow-sm d-none" style="border-left: 4px solid var(--ds-red); background: rgba(var(--ds-red-rgb), 0.05); color: var(--ds-red);">
                            <div class="d-flex align-items-center gap-2">
                                <i data-lucide="alert-triangle" style="width: 14px; height: 14px;"></i>
                                <span><strong>Plan Modification Required</strong>: A side effect has been marked as requiring plan modification. Please review and update countermeasures / task assignments.</span>
                            </div>
                        </div>

                        <div class="row text-muted small fw-bold mb-2 px-2">
                            <div class="col-4">Side Effect Description</div>
                            <div class="col-2">Impact Level</div>
                            <div class="col-3">Mitigation Strategy</div>
                            <div class="col-2">Plan Modification</div>
                            <div class="col-1"></div>
                        </div>
                        <div id="s6_sideEffectContainer" class="mb-0">
                        </div>
                    </div>
                </div>

                <!-- Section 6 - Implementation Evidence -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">6.6</span>
                                Implementation Evidence
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Attach photos, logs, or documents proving the countermeasure was actually implemented.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary">Section 6.6 - Implementation Evidence</h6>
                            <button type="button" class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[6].addEvidenceRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Evidence
                            </button>
                        </div>
                        <div class="row text-muted small fw-bold mb-2 px-2 align-items-center">
                            <div class="col-3">Document/Photo Name</div>
                            <div class="col-3">Link/Reference</div>
                            <div class="col-2">Uploaded By</div>
                            <div class="col-3">Attachment (Max 2MB)</div>
                            <div class="col-1"></div>
                        </div>
                        <div id="s6_evidenceContainer" class="mb-0">
                        </div>
                    </div>
                </div>

                <!-- Section 7 - Communication Log -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">6.7</span>
                                Communication Log
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Record how and when the change was communicated to affected stakeholders.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-end mb-3">
                            <button type="button" class="ds-btn ds-btn-ghost text-xs" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[6].addCommRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Comm
                            </button>
                        </div>
                        <div class="row text-muted small fw-bold mb-2 px-2">
                            <div class="col-3">Stakeholder</div>
                            <div class="col-4">Message</div>
                            <div class="col-2">Date</div>
                            <div class="col-2">Channel</div>
                            <div class="col-1"></div>
                        </div>
                        <div id="s6_commContainer" class="mb-0">
                        </div>
                    </div>
                </div>

                <!-- Section 8 - Training & Awareness -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">6.8</span>
                                Training &amp; Awareness
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Log training sessions conducted so staff are aware of the new standard.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-end mb-3">
                            <button type="button" class="ds-btn ds-btn-ghost text-xs" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[6].addTrainingRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Training
                            </button>
                        </div>
                        <div class="row text-muted small fw-bold mb-2 px-2">
                            <div class="col-3">Target Group</div>
                            <div class="col-2">Training Module</div>
                            <div class="col-2">Date</div>
                            <div class="col-2">Attend %</div>
                            <div class="col-2">Attachment (Max 2MB)</div>
                            <div class="col-1"></div>
                        </div>
                        <div id="s6_trainingContainer" class="mb-0">
                        </div>
                    </div>
                </div>

                <!-- Section 9 - Readiness Verification -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">6.9</span>
                                Readiness Verification
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Confirm the process and people are ready before the change goes fully live.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary">Section 6.10 - Readiness Verification</h6>
                            <button type="button" class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[6].addReadinessRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Check
                            </button>
                        </div>
                        <div class="row text-muted small fw-bold mb-2 px-2">
                            <div class="col-6">Item</div>
                            <div class="col-3">Verified By</div>
                            <div class="col-2">Status</div>
                            <div class="col-1"></div>
                        </div>
                        <div id="s6_readinessContainer" class="mb-0">
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    init(projectData) {
        this.projectData = projectData;
        const wf = projectData.workflows || [];
        const d = wf.find(w => w.stage_id === 6)?.data || {};
        
        // Countermeasure Task Assignments (Merged Section 1)
        const tasksArr = (d.countermeasure_task_assignments && d.countermeasure_task_assignments.length) ? d.countermeasure_task_assignments : (d.countermeasures || d.task_management || []);
        const taskContainer = document.getElementById('s6_taskContainer');
        if (taskContainer) {
            taskContainer.innerHTML = '';
            if (tasksArr.length) {
                tasksArr.forEach(r => this.addTaskRow(r));
            } else {
                this.addTaskRow();
            }
        }

        // Resources (Section 2)
        const resourcesArr = d.resource_deployment || [];
        const resourceContainer = document.getElementById('s6_resourceContainer');
        if (resourceContainer) {
            resourceContainer.innerHTML = '';
            if (resourcesArr.length) {
                resourcesArr.forEach(r => this.addResourceRow(r));
            } else {
                this.addResourceRow();
            }
        }

        // Changes (Section 3)
        const changesArr = d.change_management || [];
        const changeContainer = document.getElementById('s6_changeContainer');
        if (changeContainer) {
            changeContainer.innerHTML = '';
            if (changesArr.length) {
                changesArr.forEach(r => this.addChangeRow(r));
            } else {
                this.addChangeRow();
            }
        }

        // Risks (Section 4)
        const risksArr = d.risk_resistance || [];
        const riskContainer = document.getElementById('s6_riskContainer');
        if (riskContainer) {
            riskContainer.innerHTML = '';
            if (risksArr.length) {
                risksArr.forEach(r => this.addRiskRow(r));
            } else {
                this.addRiskRow();
            }
        }

        // Side Effects (Section 5)
        const sideEffectsArr = d.side_effect_analysis || [];
        const sideEffectContainer = document.getElementById('s6_sideEffectContainer');
        if (sideEffectContainer) {
            sideEffectContainer.innerHTML = '';
            if (sideEffectsArr.length) {
                sideEffectsArr.forEach(r => this.addSideEffectRow(r));
            } else {
                this.addSideEffectRow();
            }
        }

        // Evidence (Section 6)
        const evidenceArr = d.implementation_evidence || [];
        const evidenceContainer = document.getElementById('s6_evidenceContainer');
        if (evidenceContainer) {
            evidenceContainer.innerHTML = '';
            if (evidenceArr.length) {
                evidenceArr.forEach(r => this.addEvidenceRow(r));
            } else {
                this.addEvidenceRow();
            }
        }

        // Comm & Training (Section 7)
        const commTraining = d.communication_training || {};
        const commArr = commTraining.communication_log || d.communication_log || [];
        const trainingArr = commTraining.training_awareness || d.training_awareness || [];

        const commContainer = document.getElementById('s6_commContainer');
        if (commContainer) {
            commContainer.innerHTML = '';
            if (commArr.length) {
                commArr.forEach(r => this.addCommRow(r));
            } else {
                this.addCommRow();
            }
        }

        const trainingContainer = document.getElementById('s6_trainingContainer');
        if (trainingContainer) {
            trainingContainer.innerHTML = '';
            if (trainingArr.length) {
                trainingArr.forEach(r => this.addTrainingRow(r));
            } else {
                this.addTrainingRow();
            }
        }

        // Readiness (Section 8)
        const readinessArr = d.readiness_verification || [];
        const readinessContainer = document.getElementById('s6_readinessContainer');
        if (readinessContainer) {
            readinessContainer.innerHTML = '';
            if (readinessArr.length) {
                readinessArr.forEach(r => this.addReadinessRow(r));
            } else {
                this.addReadinessRow();
            }
        }

        const gate = d.approval_gate || {};
        this.setVal('s6_gate_verified_by', gate.verified_by);
        this.setVal('s6_gate_date', gate.date);
        this.setVal('s6_gate_status', gate.status);
        this.setVal('s6_gate_comments', gate.comments);

        // Run verification checks
        this.checkCountermeasureStatus();
        this.checkSideEffects();

        if (window.lucide) lucide.createIcons();
    },

    collectData() {
        const tasks = this.collectRows('s6_taskContainer', ['.r-act', '.r-own', '.r-tsk', '.r-due', '.r-pct'], ['countermeasure', 'owner', 'task', 'due_date', 'completion_pct']);
        return {
            countermeasures: tasks.map(t => ({ countermeasure: t.countermeasure, owner: t.owner, status: parseInt(t.completion_pct, 10) >= 100 ? 'Completed' : 'In Progress' })),
            countermeasure_task_assignments: tasks,
            resource_deployment: this.collectRows('s6_resourceContainer', ['.r-res', '.r-plan', '.r-act', '.r-var'], ['resource', 'planned_cost', 'actual_cost', 'variance']),
            change_management: this.collectRows('s6_changeContainer', ['.r-desc', '.r-sop', '.r-dt'], ['change_description', 'sop_updated', 'date']),
            risk_resistance: this.collectRows('s6_riskContainer', ['.r-rsk', '.r-str', '.r-stat'], ['anticipated_risk', 'strategy_executed', 'status']),
            side_effect_analysis: this.collectRows('s6_sideEffectContainer', ['.r-desc', '.r-impact', '.r-mit', '.r-mod'], ['description', 'impact_level', 'mitigation', 'plan_modification_required']),
            implementation_evidence: this.collectRows('s6_evidenceContainer', ['.r-nam', '.r-lnk', '.r-upb'], ['document_name', 'link', 'uploaded_by']),
            communication_training: {
                communication_log: this.collectRows('s6_commContainer', ['.r-stk', '.r-msg', '.r-dt', '.r-chn'], ['stakeholder', 'message', 'date', 'channel']),
                training_awareness: this.collectTrainingRows()
            },
            readiness_verification: this.collectRows('s6_readinessContainer', ['.r-itm', '.r-ver', '.r-stat'], ['item', 'verified_by', 'status']),
            approval_gate: {
                verified_by: this.getVal('s6_gate_verified_by'),
                date: this.getVal('s6_gate_date'),
                status: this.getVal('s6_gate_status'),
                comments: this.getVal('s6_gate_comments')
            }
        };
    },

    collectRows(containerId, selectors, keys) {
        const container = document.getElementById(containerId);
        if (!container) return [];
        return [...container.querySelectorAll('.dyn-row')].map(r => {
            let obj = {};
            selectors.forEach((sel, i) => { 
                const el = r.querySelector(sel);
                if (el) {
                    const val = el.value || el.dataset.savedVal || el.getAttribute('data-saved-val') || '';
                    obj[keys[i]] = (val || '').trim();
                } else {
                    obj[keys[i]] = '';
                }
            });
            return obj;
        }).filter(x => Object.values(x).some(v => v !== '')); 
    },

    collectTrainingRows() {
        const container = document.getElementById('s6_trainingContainer');
        if (!container) return [];
        return [...container.querySelectorAll('.dyn-row')].map(r => {
            const tgt = r.querySelector('.r-tgt');
            const mod = r.querySelector('.r-mod');
            const dt  = r.querySelector('.r-dt');
            const att = r.querySelector('.r-att');
            const docName = r.querySelector('.r-doc-name');
            const docUrl  = r.querySelector('.r-doc-url');
            return {
                target_group:    (tgt?.value || '').trim(),
                training_module: (mod?.value || '').trim(),
                date:            (dt?.value  || '').trim(),
                attendance_pct:  (att?.value || '').trim(),
                document_name:   (docName?.value || '').trim(),
                document_url:    (docUrl?.value  || '').trim()
            };
        }).filter(x => x.target_group || x.training_module || x.date || x.attendance_pct || x.document_name);
    },



    addRowTemplate(containerId, data, html, onDeleteCallback) {
        const c = document.getElementById(containerId);
        if (!c) return null;
        const r = document.createElement('div');
        r.className = 'row g-2 mb-2 align-items-center dyn-row';
        r.innerHTML = html + `<div class="col-1"><button type="button" class="ds-btn ds-btn-ghost text-danger p-1" onclick="this.closest('.dyn-row').remove(); if('${onDeleteCallback || ''}') { eval('${onDeleteCallback || ''}')(); }"><i data-lucide="trash-2" style="width:14px;"></i></button></div>`;
        c.appendChild(r);
        if (window.lucide) lucide.createIcons();
        return r;
    },

    addTaskRow(d = {}) {
        this.addRowTemplate('s6_taskContainer', d, `
            <div class="col-3"><input type="text" class="ds-input r-act" placeholder="e.g. Install torque sensors" value="${d.countermeasure || d.countermeasure_ref || d.action || ''}" required></div>
            <div class="col-2"><input type="text" class="ds-input r-own" placeholder="e.g. Ravi Kumar" value="${d.owner || d.assignee || ''}" required></div>
            <div class="col-2"><input type="text" class="ds-input r-tsk" placeholder="e.g. Mount sensors" value="${d.task || ''}" required></div>
            <div class="col-2"><input type="date" class="ds-input r-due" value="${d.due_date || d.target_date || d.end_date || ''}" required></div>
            <div class="col-2"><input type="number" class="ds-input r-pct" placeholder="%" title="Completion percentage" min="0" max="100" style="min-width: 90px;" value="${d.completion_pct !== undefined ? d.completion_pct : (d.status==='Completed'?'100':'')}" oninput="StageModules[6].checkCountermeasureStatus()" required></div>`, 'StageModules[6].onCountermeasureDelete');

        this.checkCountermeasureStatus();
    },

    addResourceRow(d = {}) {
        const calc = "const p=this.closest('.dyn-row'); p.querySelector('.r-var').value = (parseFloat(p.querySelector('.r-plan').value)||0) - (parseFloat(p.querySelector('.r-act').value)||0);";
        this.addRowTemplate('s6_resourceContainer', d, `
            <div class="col-4"><input type="text" class="ds-input r-res" placeholder="e.g. Calibration sensors kit" value="${d.resource || ''}" required></div>
            <div class="col-2"><input type="number" class="ds-input r-plan" placeholder="e.g. 15000" value="${d.planned_cost || ''}" onchange="${calc}" required></div>
            <div class="col-2"><input type="number" class="ds-input r-act" placeholder="e.g. 14200" value="${d.actual_cost || ''}" onchange="${calc}" required></div>
            <div class="col-3"><input type="number" class="ds-input r-var" readonly style="background:var(--ds-surface-raised)" value="${d.variance || ''}"></div>`);
    },

    addChangeRow(d = {}) {
        this.addRowTemplate('s6_changeContainer', d, `
            <div class="col-6"><input type="text" class="ds-input r-desc" placeholder="e.g. Torque standard updated from 4.5 to 5.5 bar" value="${d.change_description || ''}" required></div>
            <div class="col-2">
                <select class="ds-input ds-select r-sop" required>
                    <option ${d.sop_updated==='Y'?'selected':''}>Y</option>
                    <option ${d.sop_updated==='N'?'selected':''}>N</option>
                </select>
            </div>
            <div class="col-3"><input type="date" class="ds-input r-dt" value="${d.date || ''}" required></div>`);
    },

    addRiskRow(d = {}) {
        this.addRowTemplate('s6_riskContainer', d, `
            <div class="col-5"><input type="text" class="ds-input r-rsk" placeholder="e.g. Operator unfamiliar with sensor alerts" value="${d.anticipated_risk || ''}" required></div>
            <div class="col-4"><input type="text" class="ds-input r-str" placeholder="e.g. Hands-on shift training session" value="${d.strategy_executed || ''}" required></div>
            <div class="col-2">
                <select class="ds-input ds-select r-stat" required>
                    <option value="" ${!d.status ? 'selected' : ''} disabled>Select Status</option>
                    <option value="Planned" ${d.status === 'Planned' ? 'selected' : ''}>Planned</option>
                    <option value="In Progress" ${d.status === 'In Progress' ? 'selected' : ''}>In Progress</option>
                    <option value="Completed" ${d.status === 'Completed' ? 'selected' : ''}>Completed</option>
                </select>
            </div>`);
    },

    addSideEffectRow(d = {}) {
        const impactVal = d.impact_level || 'Low';
        const modVal = d.plan_modification_required || 'N';
        this.addRowTemplate('s6_sideEffectContainer', d, `
            <div class="col-4"><input type="text" class="ds-input r-desc" placeholder="e.g. Slight initial cycle time increase" value="${d.description || ''}" required></div>
            <div class="col-2">
                <select class="ds-input ds-select r-impact" required>
                    <option value="Low" ${impactVal==='Low'?'selected':''}>Low</option>
                    <option value="Medium" ${impactVal==='Medium'?'selected':''}>Medium</option>
                    <option value="High" ${impactVal==='High'?'selected':''}>High</option>
                </select>
            </div>
            <div class="col-3"><input type="text" class="ds-input r-mit" placeholder="e.g. Adjust sensor response timer" value="${d.mitigation || ''}" required></div>
            <div class="col-2">
                <select class="ds-input ds-select r-mod" onchange="StageModules[6].checkSideEffects()" required>
                    <option value="N" ${modVal==='N'?'selected':''}>No</option>
                    <option value="Y" ${modVal==='Y'?'selected':''}>Yes</option>
                </select>
            </div>`, 'StageModules[6].onSideEffectDelete');
        this.checkSideEffects();
    },

    addEvidenceRow(d = {}) {
        const rowEl = this.addRowTemplate('s6_evidenceContainer', d, `
            <div class="col-3"><input type="text" class="ds-input r-nam" placeholder="e.g. Calibration Report #CR-2025" value="${d.document_name || ''}" required></div>
            <div class="col-3"><input type="text" class="ds-input r-lnk" placeholder="e.g. /uploads/... or URL" value="${d.link || ''}" required></div>
            <div class="col-2"><input type="text" class="ds-input r-upb" placeholder="e.g. Rajesh Kumar" value="${d.uploaded_by || ''}" required></div>
            <div class="col-2 d-flex align-items-center">
                <button type="button" class="btn btn-outline-primary text-xs w-100 d-flex align-items-center justify-content-center gap-1 btn-upload-ev py-2 px-2" style="height:38px; border-style:dashed; border-width:1.5px; border-radius:8px; font-weight:600; white-space:nowrap;" title="Upload PDF, PPT, Photo, Document (Max 2MB)">
                    <i data-lucide="upload-cloud" style="width:15px;height:15px;"></i>
                    <span>Upload (Max 2MB)</span>
                </button>
                <input type="file" class="d-none r-file-input" accept=".pdf,.ppt,.pptx,.png,.jpg,.jpeg,.webp,.doc,.docx,.txt">
            </div>
            <div class="col-auto d-flex align-items-center">
                <a href="${d.link || '#'}" target="_blank" class="btn btn-primary text-xs d-flex align-items-center justify-content-center gap-1 btn-view-ev ${d.link ? '' : 'd-none'} py-2 px-3" style="height:38px; border-radius:8px; text-decoration:none; font-weight:600; white-space:nowrap;" title="View Uploaded Document">
                    <i data-lucide="external-link" style="width:14px;height:14px;"></i> View
                </a>
            </div>`);


        if (!rowEl) return;
        rowEl.classList.add('flex-nowrap'); // prevent delete button from wrapping to next line

        const btnUpload = rowEl.querySelector('.btn-upload-ev');
        const fileInput = rowEl.querySelector('.r-file-input');
        const linkInput = rowEl.querySelector('.r-lnk');
        const nameInput = rowEl.querySelector('.r-nam');
        const btnView = rowEl.querySelector('.btn-view-ev');

        if (btnUpload && fileInput) {
            btnUpload.addEventListener('click', () => fileInput.click());
            fileInput.addEventListener('change', async (e) => {
                const file = e.target.files[0];
                if (!file) return;

                // File size limit: Under 2MB (2 * 1024 * 1024 bytes)
                if (file.size > 2 * 1024 * 1024) {
                    const errorMsg = `File "${file.name}" exceeds the 2MB size limit (${(file.size / (1024*1024)).toFixed(2)}MB). Please upload a document or photo under 2MB.`;
                    if (window.QCMS && QCMS.toast) {
                        QCMS.toast(errorMsg, 'error');
                    } else {
                        alert(errorMsg);
                    }
                    fileInput.value = '';
                    return;
                }

                try {
                    btnUpload.disabled = true;
                    btnUpload.innerHTML = '<span class="spinner-border spinner-border-sm me-1" style="width:12px;height:12px;"></span> Uploading...';

                    const res = await api.uploadFile('/projects/upload-evidence', file);
                    const fileUrl = res.url || res.file_url;

                    if (fileUrl) {
                        if (linkInput) linkInput.value = fileUrl;
                        if (nameInput && !nameInput.value.trim()) nameInput.value = file.name;
                        if (btnView) {
                            btnView.href = fileUrl;
                            btnView.classList.remove('d-none');
                        }
                        if (window.QCMS && QCMS.toast) {
                            QCMS.toast(`File "${file.name}" uploaded successfully!`, 'success');
                        }
                    }
                } catch (err) {
                    const failMsg = 'Upload failed: ' + (err.message || err);
                    if (window.QCMS && QCMS.toast) {
                        QCMS.toast(failMsg, 'error');
                    } else {
                        alert(failMsg);
                    }
                } finally {
                    btnUpload.disabled = false;
                    btnUpload.innerHTML = '<i data-lucide="upload-cloud" style="width:16px;height:16px;"></i> <span>Upload (Max 2MB)</span>';
                    if (window.lucide) lucide.createIcons();
                }
            });
        }

        if (linkInput && btnView) {
            linkInput.addEventListener('input', (e) => {
                const val = e.target.value.trim();
                if (val) {
                    btnView.href = val;
                    btnView.classList.remove('d-none');
                } else {
                    btnView.classList.add('d-none');
                }
            });
        }

        if (window.lucide) lucide.createIcons();
    },

    addCommRow(d = {}) {
        this.addRowTemplate('s6_commContainer', d, `
            <div class="col-3"><input type="text" class="ds-input r-stk" placeholder="e.g. Production Manager" value="${d.stakeholder || ''}" required></div>
            <div class="col-4"><input type="text" class="ds-input r-msg" placeholder="e.g. Countermeasure successfully tested on Line A" value="${d.message || ''}" required></div>
            <div class="col-2"><input type="date" class="ds-input r-dt" value="${d.date || ''}" required></div>
            <div class="col-2"><input type="text" class="ds-input r-chn" placeholder="e.g. Email / MS Teams" value="${d.channel || ''}" required></div>`);
    },

    addTrainingRow(d = {}) {
        const fileUrl = d.document_url || d.link || '';
        const fileName = d.document_name || '';

        const rowEl = this.addRowTemplate('s6_trainingContainer', d, `
            <div class="col-3"><input type="text" class="ds-input r-tgt" placeholder="e.g. Line A operators (Shifts A & B)" value="${d.target_group || ''}" required></div>
            <div class="col-2"><input type="text" class="ds-input r-mod" placeholder="e.g. Torque Sensor Operation & Alerts" value="${d.training_module || ''}" required></div>
            <div class="col-2"><input type="date" class="ds-input r-dt" value="${d.date || ''}" required></div>
            <div class="col-2"><input type="number" class="ds-input r-att" placeholder="%" min="0" max="100" value="${d.attendance_pct || ''}" required></div>
            <div class="col-2 d-flex flex-column justify-content-center gap-1">
                <button type="button" class="btn btn-outline-primary text-xs w-100 d-flex align-items-center justify-content-center gap-1 btn-upload-tr py-1 px-1" style="height:32px; border-style:dashed; border-width:1.5px; border-radius:6px; font-weight:600; white-space:nowrap; font-size:0.7rem;" title="Upload PDF, PPT, Photo, Document (Max 2MB)">
                    <i data-lucide="upload-cloud" style="width:13px;height:13px;"></i>
                    <span>Upload (Max 2MB)</span>
                </button>
                <a href="${fileUrl || '#'}" target="_blank" class="btn btn-primary text-xs w-100 d-flex align-items-center justify-content-center gap-1 btn-view-tr ${fileUrl ? '' : 'd-none'} py-1 px-1" style="height:28px; border-radius:6px; text-decoration:none; font-weight:600; white-space:nowrap; font-size:0.7rem;" title="${fileName || 'View Document'}">
                    <i data-lucide="external-link" style="width:12px;height:12px;"></i> View File
                </a>
                <input type="file" class="d-none r-doc-file" accept=".pdf,.ppt,.pptx,.png,.jpg,.jpeg,.webp,.doc,.docx,.txt">
                <input type="hidden" class="r-doc-name" value="${fileName}">
                <input type="hidden" class="r-doc-url" value="${fileUrl}">
            </div>`);

        if (!rowEl) return;

        const btnUpload = rowEl.querySelector('.btn-upload-tr');
        const fileInput = rowEl.querySelector('.r-doc-file');
        const nameInput = rowEl.querySelector('.r-doc-name');
        const urlInput = rowEl.querySelector('.r-doc-url');
        const btnView = rowEl.querySelector('.btn-view-tr');

        if (btnUpload && fileInput) {
            btnUpload.addEventListener('click', () => fileInput.click());
            fileInput.addEventListener('change', async (e) => {
                const file = e.target.files[0];
                if (!file) return;

                if (file.size > 2 * 1024 * 1024) {
                    const errorMsg = `File "${file.name}" exceeds the 2MB size limit (${(file.size / (1024*1024)).toFixed(2)}MB). Please upload a file under 2MB.`;
                    if (window.QCMS && QCMS.toast) QCMS.toast(errorMsg, 'warning');
                    else alert(errorMsg);
                    fileInput.value = '';
                    return;
                }

                try {
                    btnUpload.disabled = true;
                    btnUpload.innerHTML = '<span class="spinner-border spinner-border-sm me-1" style="width:12px;height:12px;"></span> Uploading...';

                    let uploadedUrl = '';
                    try {
                        const res = await api.uploadFile('/projects/upload-evidence', file);
                        uploadedUrl = res.url || res.file_url;
                    } catch (apiErr) {
                        uploadedUrl = URL.createObjectURL(file);
                    }

                    if (uploadedUrl) {
                        if (urlInput) urlInput.value = uploadedUrl;
                        if (nameInput) nameInput.value = file.name;
                        if (btnView) {
                            btnView.href = uploadedUrl;
                            btnView.title = file.name;
                            btnView.classList.remove('d-none');
                        }
                        if (window.QCMS && QCMS.toast) {
                            QCMS.toast(`File "${file.name}" attached successfully!`, 'success');
                        }
                    }
                } catch (err) {
                    if (window.QCMS && QCMS.toast) QCMS.toast('Upload failed: ' + (err.message || err), 'error');
                } finally {
                    btnUpload.disabled = false;
                    btnUpload.innerHTML = '<i data-lucide="upload-cloud" style="width:14px;height:14px;"></i> <span>Upload (Max 2MB)</span>';
                    if (window.lucide) lucide.createIcons();
                }
            });
        }

        if (window.lucide) lucide.createIcons();
    },

    addReadinessRow(d = {}) {
        this.addRowTemplate('s6_readinessContainer', d, `
            <div class="col-6"><input type="text" class="ds-input r-itm" placeholder="e.g. Standard tools & calibration kits verified" value="${d.item || ''}" required></div>
            <div class="col-3"><input type="text" class="ds-input r-ver" placeholder="e.g. Rajesh Kumar" value="${d.verified_by || ''}" required></div>
            <div class="col-2"><input type="text" class="ds-input r-stat" placeholder="e.g. Ready" value="${d.status || ''}" required></div>`);
    },

    // Check callbacks and helpers
    onCountermeasureDelete() {
        this.updateCountermeasureDropdowns();
        this.checkCountermeasureStatus();
    },

    onSideEffectDelete() {
        this.checkSideEffects();
    },

    updateCountermeasureDropdowns() {
        const cms = [...document.querySelectorAll('#s6_countermeasuresContainer .r-act')].map(el => el.value.trim()).filter(x => x);
        document.querySelectorAll('#s6_taskContainer .r-ref').forEach(selectEl => {
            const currentVal = selectEl.value || selectEl.getAttribute('data-val') || '';
            selectEl.innerHTML = '';
            
            const defaultOpt = document.createElement('option');
            defaultOpt.value = '';
            defaultOpt.textContent = '-- Select Countermeasure --';
            selectEl.appendChild(defaultOpt);
            
            cms.forEach(cm => {
                const opt = document.createElement('option');
                opt.value = cm;
                opt.textContent = cm;
                if (cm === currentVal) {
                    opt.selected = true;
                }
                selectEl.appendChild(opt);
            });
            
            if (cms.includes(currentVal)) {
                selectEl.value = currentVal;
            }
        });
    },

    checkCountermeasureStatus() {
        const lockAlert = document.getElementById('s6_change_lock_alert');
        if (lockAlert) lockAlert.style.display = 'none';
        const container = document.getElementById('s6_changeContainer');
        if (container) {
            container.querySelectorAll('input, select, button').forEach(el => el.disabled = false);
        }
        const addBtn = document.getElementById('s6_addChangeBtn');
        if (addBtn) addBtn.disabled = false;
    },

    checkSideEffects() {
        const mods = [...document.querySelectorAll('#s6_sideEffectContainer .r-mod')].map(el => el.value);
        const warning = document.getElementById('s6_plan_mod_warning');
        let needsMod = mods.some(m => m === 'Y');
        
        if (warning) {
            if (needsMod) {
                warning.classList.remove('d-none');
            } else {
                warning.classList.add('d-none');
            }
        }
    },

    getVal(id) { return (document.getElementById(id) || {}).value || ''; },
    setVal(id, val) { const el = document.getElementById(id); if (el) el.value = val; }
};

window.StageModules = window.StageModules || {};
window.StageModules[6] = Stage6;
