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
                                <span class="ds-tooltip-trigger" title="Countermeasure Task Assignments: Task execution tracking, owner assignment, due dates, and completion status">Countermeasure Task Assignments</span>
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Team members can view and update completion.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <div>
                                <h6 class="fw-bold mb-0 text-primary ds-tooltip-trigger" title="Section 6.1 - Countermeasure Task Assignments: Execution tracking matrix">Section 6.1 - Countermeasure Task Assignments</h6>
                            </div>
                            <button type="button" class="ds-btn ds-btn-ghost ds-tooltip-trigger" title="+ Add Task: Add a new execution task item" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[6].addTaskRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Task
                            </button>
                        </div>
                        <div class="row text-muted small fw-bold mb-2 px-2">
                            <div class="col-3 ds-tooltip-trigger" title="Countermeasure: Specific action item being executed">Countermeasure</div>
                            <div class="col-2 ds-tooltip-trigger" title="Owner: Assigned person responsible for task execution">Owner</div>
                            <div class="col-2 ds-tooltip-trigger" title="Task: Task description or milestone step">Task</div>
                            <div class="col-2 ds-tooltip-trigger" title="Due Date: Target completion deadline">Due Date</div>
                            <div class="col-2 ds-tooltip-trigger" title="Comp %: Completion percentage progress (0-100%)">Comp %</div>
                            <div class="col-1"></div>
                        </div>
                        <div id="s6_taskContainer" class="mb-0">
                        </div>
                    </div>
                </div>

                <!-- Section 2 - Resource Planning & Deployment -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">6.2</span>
                                <span class="ds-tooltip-trigger" title="Resource Planning & Deployment: Identify and track the budget, manpower, and materials needed to implement the solution">Resource Planning & Deployment</span>
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Identify the budget, manpower, and materials needed to implement the solution and track deployment status.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary ds-tooltip-trigger" title="Section 6.2 - Resource Planning & Deployment: Resource allocation and deployment tracking">Section 6.2 - Resource Planning & Deployment</h6>
                            <button type="button" class="ds-btn ds-btn-ghost ds-tooltip-trigger" title="+ Add Resource: Log resource allocation and status" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[6].addResourceRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Resource
                            </button>
                        </div>
                        <div class="row text-muted small fw-bold mb-2 px-2">
                            <div class="col-3 ds-tooltip-trigger" title="Resource Required: Description of equipment, tool, material, or manpower">Resource Required</div>
                            <div class="col-2 ds-tooltip-trigger" title="Budget Allocation: Allocated financial budget or cost">Budget Allocation</div>
                            <div class="col-2 ds-tooltip-trigger" title="Source: Internal department, vendor, or supplier">Source</div>
                            <div class="col-2 ds-tooltip-trigger" title="Due Date: Target date for procurement/allocation">Due Date</div>
                            <div class="col-2 ds-tooltip-trigger" title="Status: Current allocation/deployment status">Status</div>
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
                                <span class="ds-tooltip-trigger" title="Change Management: Updating Standard Operating Procedures (SOP) and issuing Engineering Change Notices (ECN)">Change Management</span>
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Executed once all countermeasures are completed. Used for implementing approved changes.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary ds-tooltip-trigger" title="Section 6.3 - Change Management: Official SOP and document updates">Section 6.3 - Change Management</h6>
                            <button type="button" id="s6_addChangeBtn" class="ds-btn ds-btn-ghost ds-tooltip-trigger" title="+ Add Change: Record an official SOP/work instruction update" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[6].addChangeRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Change
                            </button>
                        </div>

                        <div class="row text-muted small fw-bold mb-2 px-2">
                            <div class="col-5 ds-tooltip-trigger" title="Change Description: Description of standard procedure or work instruction change">Change Description</div>
                            <div class="col-2 ds-tooltip-trigger" title="Owner: Person or role responsible for executing and standardizing this change">Owner</div>
                            <div class="col-2 ds-tooltip-trigger" title="SOP Updated (Y/N): Confirmation whether formal SOP documentation was revised">SOP Updated (Y/N)</div>
                            <div class="col-2 ds-tooltip-trigger" title="Date: Implementation date of standard revision">Date</div>
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
                                <span class="ds-tooltip-trigger" title="Risk & Resistance Management: Identifying implementation risks, user resistance, and executed engagement strategies">Risk &amp; Resistance Management</span>
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Identify implementation risks and organizational resistance, and how each was addressed.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary ds-tooltip-trigger" title="Section 6.4 - Risk & Resistance Management: Mitigation strategy tracking">Section 6.4 - Risk &amp; Resistance Management</h6>
                            <button type="button" class="ds-btn ds-btn-ghost ds-tooltip-trigger" title="+ Add Risk: Record identified resistance or operational risk" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[6].addRiskRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Risk
                            </button>
                        </div>
                        <div class="row text-muted small fw-bold mb-2 px-2">
                            <div class="col-5 ds-tooltip-trigger" title="Anticipated Risk/Resistance: Potential hurdle or user resistance factor">Anticipated Risk/Resistance</div>
                            <div class="col-4 ds-tooltip-trigger" title="Strategy Executed: Action taken to overcome risk or resistance">Strategy Executed</div>
                            <div class="col-2 ds-tooltip-trigger" title="Status: Current resolution status">Status</div>
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
                                <span class="ds-tooltip-trigger" title="Side Effect Analysis: Live monitoring tracking real-time implementation for unintended negative side effects">Side Effect Analysis</span>
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Analyze potential negative side effects of the solutions. Modifications to the plan may be needed.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary ds-tooltip-trigger" title="Section 6.5 - Side Effect Analysis: Live side effect monitoring and mitigation tracking">Section 6.5 - Side Effect Analysis</h6>
                            <button type="button" class="ds-btn ds-btn-ghost ds-tooltip-trigger" title="+ Add Side Effect: Log an observed secondary impact" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[6].addSideEffectRow()">
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
                            <div class="col-4 ds-tooltip-trigger" title="Side Effect Description: Description of secondary issue or negative operational outcome">Side Effect Description</div>
                            <div class="col-2 ds-tooltip-trigger" title="Impact Level: Severity rating of side effect (Low, Medium, High, Critical)">Impact Level</div>
                            <div class="col-3 ds-tooltip-trigger" title="Mitigation Strategy: Corrective action taken to mitigate secondary impact">Mitigation Strategy</div>
                            <div class="col-2 ds-tooltip-trigger" title="Plan Modification: Flag whether countermeasure action plan requires modification">Plan Modification</div>
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
                                <span class="ds-tooltip-trigger" title="Implementation Evidence: Photos, log sheets, and audit documents verifying physical execution">Implementation Evidence</span>
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Attach photos, logs, or documents proving the countermeasure was actually implemented.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary ds-tooltip-trigger" title="Section 6.6 - Implementation Evidence: Documented proof of completed countermeasures">Section 6.6 - Implementation Evidence</h6>
                            <button type="button" class="ds-btn ds-btn-ghost ds-tooltip-trigger" title="+ Add Evidence: Upload implementation photo or document" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[6].addEvidenceRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Evidence
                            </button>
                        </div>
                        <div class="row text-muted small fw-bold mb-2 px-2 align-items-center">
                            <div class="col-3 ds-tooltip-trigger" title="Document/Photo Name: Title of verification file or photo evidence">Document/Photo Name</div>
                            <div class="col-3 ds-tooltip-trigger" title="Link/Reference: External drive link or document reference ID">Link/Reference</div>
                            <div class="col-2 ds-tooltip-trigger" title="Uploaded By: Team member uploading proof">Uploaded By</div>
                            <div class="col-3 ds-tooltip-trigger" title="Attachment (Max 2MB): Uploaded image or PDF file">Attachment (Max 2MB)</div>
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
                                <span class="ds-tooltip-trigger" title="Communication Log: Recording how and when process changes were communicated to affected stakeholders">Communication Log</span>
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Record how and when the change was communicated to affected stakeholders.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-end mb-3">
                            <button type="button" class="ds-btn ds-btn-ghost text-xs ds-tooltip-trigger" title="+ Add Comm: Log a stakeholder communication event" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[6].addCommRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Comm
                            </button>
                        </div>
                        <div class="row text-muted small fw-bold mb-2 px-2">
                            <div class="col-3 ds-tooltip-trigger" title="Stakeholder: Target audience or team receiving communication">Stakeholder</div>
                            <div class="col-4 ds-tooltip-trigger" title="Message: Summary of communication brief or shift announcement">Message</div>
                            <div class="col-2 ds-tooltip-trigger" title="Date: Communication date">Date</div>
                            <div class="col-2 ds-tooltip-trigger" title="Channel: Delivery channel (Meeting, Email, Noticeboard)">Channel</div>
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
                                <span class="ds-tooltip-trigger" title="Training & Awareness: Logging operator training sessions, attendance rates, and training materials">Training &amp; Awareness</span>
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Log training sessions conducted so staff are aware of the new standard.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-end mb-3">
                            <button type="button" class="ds-btn ds-btn-ghost text-xs ds-tooltip-trigger" title="+ Add Training: Record an operator training session" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[6].addTrainingRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Training
                            </button>
                        </div>
                        <div class="row text-muted small fw-bold mb-2 px-2">
                            <div class="col-3 ds-tooltip-trigger" title="Target Group: Audience or department receiving training (e.g. Line A Operators)">Target Group</div>
                            <div class="col-2 ds-tooltip-trigger" title="Training Module: Course title or skill module name">Training Module</div>
                            <div class="col-2 ds-tooltip-trigger" title="Date: Training completion date">Date</div>
                            <div class="col-2 ds-tooltip-trigger" title="Attend %: Attendance percentage of target operators">Attend %</div>
                            <div class="col-2 ds-tooltip-trigger" title="Attachment (Max 2MB): Attendance sheet or training slide upload">Attachment (Max 2MB)</div>
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
                                <span class="ds-tooltip-trigger" title="Readiness Verification: Pre-launch audit confirming process and personnel readiness before full go-live">Readiness Verification</span>
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Confirm the process and people are ready before the change goes fully live.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary ds-tooltip-trigger" title="Readiness Verification: Final pre-flight verification sign-off">Section 6.10 - Readiness Verification</h6>
                            <button type="button" class="ds-btn ds-btn-ghost ds-tooltip-trigger" title="+ Add Check: Add a readiness audit checklist item" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[6].addReadinessRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Check
                            </button>
                        </div>
                        <div class="row text-muted small fw-bold mb-2 px-2">
                            <div class="col-6 ds-tooltip-trigger" title="Item: Specific readiness condition being verified">Item</div>
                            <div class="col-3 ds-tooltip-trigger" title="Verified By: Auditor or supervisor conducting verification">Verified By</div>
                            <div class="col-2 ds-tooltip-trigger" title="Status: Readiness status (Ready, Pending, Failed)">Status</div>
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

        // Resources (Section 2: Resource Planning & Deployment)
        const s5Wf = wf.find(w => w.stage_id === 5)?.data || {};
        const resourcesArr = (d.resource_planning_deployment && d.resource_planning_deployment.length)
            ? d.resource_planning_deployment
            : ((d.resource_deployment && d.resource_deployment.length)
                ? d.resource_deployment
                : (d.resource_planning || s5Wf.resource_planning || []));
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
        const resRows = this.collectRows('s6_resourceContainer', ['.r-res', '.r-bud', '.r-src', '.r-date', '.r-stat'], ['resource', 'budget', 'source', 'due_date', 'status']);
        return {
            countermeasures: tasks.map(t => ({ countermeasure: t.countermeasure, owner: t.owner, status: parseInt(t.completion_pct, 10) >= 100 ? 'Completed' : 'In Progress' })),
            countermeasure_task_assignments: tasks,
            resource_planning_deployment: resRows,
            resource_deployment: resRows,
            change_management: this.collectRows('s6_changeContainer', ['.r-desc', '.r-own', '.r-sop', '.r-dt'], ['change_description', 'owner', 'sop_updated', 'date']),
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
        const currentStat = d.status || 'Planned';
        const defaultOptions = ['Planned', 'Approved', 'In Progress', 'Procured / Allocated', 'Completed', 'On Hold / Rejected'];
        const allOptions = defaultOptions.includes(currentStat) ? defaultOptions : [currentStat, ...defaultOptions];
        const selectHtml = `
            <select class="ds-input ds-select r-stat text-center" style="text-align: center; text-align-last: center; font-weight: 600; cursor: pointer;" required>
                ${allOptions.map(opt => `<option value="${opt}" ${currentStat === opt ? 'selected' : ''}>${opt}</option>`).join('')}
            </select>`;

        const resVal = d.resource || d.resource_required || '';
        const budVal = d.budget || d.budget_allocation || (d.planned_cost !== undefined && d.planned_cost !== '' ? `₹${d.planned_cost}` : '');
        const srcVal = d.source || '';
        const dateVal = d.due_date || d.when || d.date || '';

        this.addRowTemplate('s6_resourceContainer', d, `
            <div class="col-3"><input type="text" class="ds-input r-res" placeholder="e.g. Torque wrench calibration rig" value="${resVal}" required></div>
            <div class="col-2"><input type="text" class="ds-input r-bud" placeholder="e.g. ₹15,000" value="${budVal}" required></div>
            <div class="col-2"><input type="text" class="ds-input r-src" placeholder="e.g. Vendor ABC Ltd" value="${srcVal}" required></div>
            <div class="col-2"><input type="date" class="ds-input r-date" value="${dateVal}" required></div>
            <div class="col-2">${selectHtml}</div>`);
    },

    addChangeRow(d = {}) {
        this.addRowTemplate('s6_changeContainer', d, `
            <div class="col-5"><input type="text" class="ds-input r-desc" placeholder="e.g. Torque standard updated from 4.5 to 5.5 bar" value="${d.change_description || ''}" required></div>
            <div class="col-2"><input type="text" class="ds-input r-own" placeholder="e.g. Rahul Sharma" value="${d.owner || d.responsible || ''}" required></div>
            <div class="col-2">
                <select class="ds-input ds-select r-sop" required>
                    <option ${d.sop_updated==='Y'?'selected':''}>Y</option>
                    <option ${d.sop_updated==='N'?'selected':''}>N</option>
                </select>
            </div>
            <div class="col-2"><input type="date" class="ds-input r-dt" value="${d.date || ''}" required></div>`);
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
            <div class="col-3"><input type="text" class="ds-input r-lnk" placeholder="e.g. /uploads/... or URL" value="${d.link || ''}"></div>
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
