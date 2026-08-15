const Stage8 = {
    projectData: null,

    renderHTML() {
        return `
            <!-- STAGE 8 FORM -->
            <div id="stage8Form">
                <!-- Section 1 - Standardization & SOP -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">8.1</span>
                                Standardization &amp; SOP
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Update the SOP and procedure steps to lock in the new standard.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary">Section 1 - Standardization &amp; SOP</h6>
                            <button type="button" class="ds-btn ds-btn-primary" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[8].previewSop()">
                                <i data-lucide="eye" style="width:12px;height:12px;color:white;"></i> Preview Formatted SOP
                            </button>
                        </div>

                        <!-- Embedded Inline SOP Form -->
                        <div id="projectSopInlineForm" class="p-4 mb-4 border rounded" style="background:rgba(var(--ds-primary-rgb), 0.01); border-color:var(--ds-border-color) !important; border-radius:var(--ds-radius-lg);">
                            <h6 class="fw-bold mb-3 d-flex align-items-center gap-2 text-sm" style="color:var(--ds-text-main);">
                                <i data-lucide="file-text" class="text-primary" style="width:16px;height:16px;"></i> Standard Operating Procedure (SOP) Details
                            </h6>
                            
                            <div class="row g-3">
                                <div class="col-md-6">
                                    <label class="ds-label" for="s8_sop_title">SOP Title *</label>
                                    <input type="text" id="s8_sop_title" class="ds-input" required placeholder="e.g., Boiler Temperature Calibration SOP">
                                </div>
                                <div class="col-md-3">
                                    <label class="ds-label" for="s8_sop_category">Category *</label>
                                    <select id="s8_sop_category" class="ds-input ds-select" required>
                                        <option value="Quality">Quality</option>
                                        <option value="Cost">Cost</option>
                                        <option value="Delivery">Delivery</option>
                                        <option value="Safety">Safety</option>
                                        <option value="Morale">Morale</option>
                                        <option value="Environment">Environment</option>
                                        <option value="Productivity">Productivity</option>
                                    </select>
                                </div>
                                <div class="col-md-3">
                                    <label class="ds-label" for="s8_sop_type">SOP Type *</label>
                                    <select id="s8_sop_type" class="ds-input ds-select" required>
                                        <option value="Operational">Operational</option>
                                        <option value="Safety Standard">Safety Standard</option>
                                        <option value="Quality Control">Quality Control</option>
                                        <option value="Maintenance">Maintenance</option>
                                        <option value="Administrative">Administrative</option>
                                    </select>
                                </div>
                                
                                <div class="col-md-6">
                                    <label class="ds-label" for="s8_sop_description">Description / Summary</label>
                                    <input type="text" id="s8_sop_description" class="ds-input" placeholder="e.g. Standard calibration routine for wire crimper pneumatic cylinder pressure" required>
                                </div>
                                <div class="col-md-6">
                                    <label class="ds-label" for="s8_sop_applicability">Applicability</label>
                                    <input type="text" id="s8_sop_applicability" class="ds-input" placeholder="e.g. Assembly Line A, crimping machines CT-400 & CT-401" required>
                                </div>
                                
                                <div class="col-md-6">
                                    <label class="ds-label" for="s8_sop_purpose">Section 1: Purpose *</label>
                                    <textarea id="s8_sop_purpose" class="ds-input ds-textarea" rows="2" required placeholder="e.g. To establish standard pressure settings and PM guidelines to eliminate wire crimping faults."></textarea>
                                </div>
                                <div class="col-md-6">
                                    <label class="ds-label" for="s8_sop_scope">Section 2: Scope *</label>
                                    <textarea id="s8_sop_scope" class="ds-input ds-textarea" rows="2" required placeholder="e.g. Applies to all production operators and maintenance engineers working on Line A."></textarea>
                                </div>
                                <div class="col-md-12">
                                    <label class="ds-label" for="s8_sop_responsibilities">Section 3: Responsibilities *</label>
                                    <textarea id="s8_sop_responsibilities" class="ds-input ds-textarea" rows="2" required placeholder="e.g. Line Operator: Performs weekly pressure checks. Shift Supervisor: Performs monthly torque verification audits."></textarea>
                                </div>
                            </div>
                            
                            <hr class="section-divider my-4">
                            
                            <!-- Procedure Steps Builder -->
                            <div class="d-flex justify-content-between align-items-center mb-3">
                                <label class="ds-label mb-0" style="font-size: 0.8rem; font-weight: 600;">Section 4: Procedure Steps</label>
                                <button type="button" class="ds-btn ds-btn-ghost ds-btn-sm" style="font-size:.72rem;padding:.2rem .5rem;" onclick="StageModules[8].addSopStepRow()">
                                    <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Step
                                </button>
                            </div>
                            
                            <div id="s8_sopStepsContainer" class="v-stack gap-2">
                                <!-- Dynamic rows of steps -->
                            </div>
                        </div>

                        <!-- Standardization Drawing / Document Reference Links List -->
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-muted small">Standardization Reference Documents &amp; Drawings</h6>
                            <button type="button" class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[8].addStdRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Document Link
                            </button>
                        </div>

                        <div id="s8_stdContainer" class="mb-0">
                            <div class="row text-muted small fw-bold mb-2 px-2">
                                <div class="col-4">Document Link / Reference</div>
                                <div class="col-3">Previous Version</div>
                                <div class="col-2">New Version</div>
                                <div class="col-2">Update Date</div>
                                <div class="col-1"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section 2 - Training & Adoption -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">8.2</span>
                                Training &amp; Adoption
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Roll out training so the new standard is adopted across the affected team.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary">Section 2 - Training &amp; Adoption</h6>
                            <button type="button" class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[8].addTrainingRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Training
                            </button>
                        </div>
                        <div id="s8_trainingContainer" class="mb-0">
                            <div class="row text-muted small fw-bold mb-2 px-2">
                                <div class="col-4">Target Group</div>
                                <div class="col-3">Training Date</div>
                                <div class="col-2">Attendance %</div>
                                <div class="col-2">Adoption Status</div>
                                <div class="col-1"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section 3 - Horizontal Deployment -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">8.3</span>
                                Horizontal Deployment
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Identify other lines or areas where this solution could be replicated.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary">Section 3 - Horizontal Deployment</h6>
                            <button type="button" class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[8].addDeployRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Deployment
                            </button>
                        </div>
                        <div id="s8_deployContainer" class="mb-0">
                            <div class="row text-muted small fw-bold mb-2 px-2">
                                <div class="col-4">Area/Plant</div>
                                <div class="col-2">Target Date</div>
                                <div class="col-2">Status</div>
                                <div class="col-3">Owner</div>
                                <div class="col-1"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section 4 - Lessons Learned -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">8.4</span>
                                Lessons Learned
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Document key learnings from the full project for the knowledge repository.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary">Section 4 - Lessons Learned</h6>
                            <button type="button" class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[8].addLessonRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Lesson
                            </button>
                        </div>
                        <div id="s8_lessonContainer" class="mb-0">
                            <div class="row text-muted small fw-bold mb-2 px-2">
                                <div class="col-3">Category</div>
                                <div class="col-4">Lesson</div>
                                <div class="col-4">Future Recommendation</div>
                                <div class="col-1"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section 5 - Benefits Summary -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">8.5</span>
                                Benefits Summary
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Summarize the overall quantified benefits achieved by the project.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary">Section 5 - Benefits Summary</h6>
                            <button type="button" class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[8].addBenefitRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Benefit
                            </button>
                        </div>
                        <div id="s8_benefitContainer" class="mb-0">
                            <div class="row text-muted small fw-bold mb-2 px-2">
                                <div class="col-3">Metric</div>
                                <div class="col-2">Baseline</div>
                                <div class="col-2">Final</div>
                                <div class="col-4">Total Savings/Benefit</div>
                                <div class="col-1"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section 6 - Remaining Opportunities -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">8.6</span>
                                Remaining Opportunities
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Note any residual gaps or follow-up opportunities not addressed by this project.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary">Section 6 - Remaining Opportunities</h6>
                            <button type="button" class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[8].addOppRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Opportunity
                            </button>
                        </div>
                        <div id="s8_oppContainer" class="mb-0">
                            <div class="row text-muted small fw-bold mb-2 px-2">
                                <div class="col-5">Identified Problem</div>
                                <div class="col-2">Priority</div>
                                <div class="col-4">Next Steps</div>
                                <div class="col-1"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section 7 - Knowledge Repository -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">8.7</span>
                                Knowledge Repository
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">File the completed project into the searchable knowledge base for future reference.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary">Section 7 - Knowledge Repository</h6>
                            <button type="button" class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[8].addRepoRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Asset
                            </button>
                        </div>
                        <div id="s8_repoContainer" class="mb-0">
                            <div class="row text-muted small fw-bold mb-2 px-2">
                                <div class="col-3">Keyword/Tag</div>
                                <div class="col-4">Summary</div>
                                <div class="col-4">Link to Asset</div>
                                <div class="col-1"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section 8 - Team Recognition -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">8.8</span>
                                Team Recognition
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Record recognition given to the QC Circle team for their contribution.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary">Section 8 - Team Recognition</h6>
                            <button type="button" class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[8].addTeamRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Member
                            </button>
                        </div>
                        <div id="s8_teamContainer" class="mb-0">
                            <div class="row text-muted small fw-bold mb-2 px-2">
                                <div class="col-3">Member</div>
                                <div class="col-5">Contribution</div>
                                <div class="col-3">Award/Recognition</div>
                                <div class="col-1"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section 9 - Project Closure & Sign-Off -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">8.9</span>
                                Closure Approval &amp; Quality Gate Sign-Off
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Get final reviewer sign-off to formally close the project.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <h6 class="fw-bold mb-3 text-primary">Section 9 - Project Closure</h6>
                        <div class="row g-3 mb-4">
                            <div class="col-md-2">
                                <label class="ds-label">Project ID</label>
                                <input type="text" id="s8_close_id" class="ds-input" readonly style="background:var(--ds-surface-raised)">
                            </div>
                            <div class="col-md-2">
                                <label class="ds-label">Start Date</label>
                                <input type="date" id="s8_close_start" class="ds-input" required>
                            </div>
                            <div class="col-md-2">
                                <label class="ds-label">End Date</label>
                                <input type="date" id="s8_close_end" class="ds-input" required>
                            </div>
                            <div class="col-md-3">
                                <label class="ds-label">Final Status</label>
                                <select id="s8_close_status" class="ds-input ds-select" required>
                                    <option>Completed Successfully</option>
                                    <option>Completed with Deviations</option>
                                    <option>Closed Incomplete</option>
                                </select>
                            </div>
                            <div class="col-md-3">
                                <label class="ds-label">Handover To</label>
                                <input type="text" id="s8_close_handover" class="ds-input" required>
                            </div>
                        </div>

                        <!-- 9. CLOSURE APPROVAL & QUALITY GATE SIGN-OFF TABLE -->
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary">Closure Approval & Quality Gate Sign-Off</h6>
                            <button type="button" class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[8].addSignoffRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Sign-off Role
                            </button>
                        </div>
                        <div class="table-responsive border rounded-3 p-0 mb-3" style="background:var(--ds-surface);">
                            <table class="table table-bordered table-hover align-middle mb-0 text-xs" id="s8_signoff_table">
                                <thead class="table-light text-secondary fw-bold" style="background: #f8fafc;">
                                    <tr>
                                        <th style="width: 22%;">Role</th>
                                        <th style="width: 25%;">Name</th>
                                        <th style="width: 25%;">Department / Section</th>
                                        <th style="width: 14%;">Signature</th>
                                        <th style="width: 10%;">Date</th>
                                        <th style="width: 4%;"></th>
                                    </tr>
                                </thead>
                                <tbody id="s8_signoff_tbody">
                                    <!-- Populated dynamically -->
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    init(projectData) {
        this.projectData = projectData;
        const wf = projectData.workflows || [];
        const d = wf.find(w => w.stage_id === 8)?.data || {};

        const s4 = wf.find(w => w.stage_id === 4)?.data || {};
        const s5 = wf.find(w => w.stage_id === 5)?.data || {};
        const s7 = wf.find(w => w.stage_id === 7)?.data || {};

        ['std', 'training', 'deploy', 'lesson', 'benefit', 'opp', 'repo', 'team'].forEach(key => {
            const arr = d[this.getMap(key)] || [];
            if (arr.length) {
                arr.forEach(r => this[`add${this.capitalize(key)}Row`](r));
            } else {
                // Auto-populate fallbacks from upstream stages if empty
                if (key === 'std') {
                    const mapping = s5.root_cause_mapping || [];
                    if (mapping.length) {
                        mapping.forEach(m => {
                            this.addStdRow({
                                document: "SOP standardization for: " + (m.proposed_solution || 'corrections'),
                                previous_version: "Root Cause: " + (m.root_cause || 'baseline'),
                                new_version: "Rev 1.0",
                                update_date: new Date().toISOString().split('T')[0]
                            });
                        });
                    } else {
                        this.addStdRow();
                    }
                } else if (key === 'deploy') {
                    const actionPlan = s5.action_plan_3w1h || [];
                    if (actionPlan.length) {
                        actionPlan.forEach(act => {
                            this.addDeployRow({
                                area_department: "Target Area",
                                applicability: "Deploy standard: " + act.what,
                                responsible_person: act.who,
                                status: "Implemented"
                            });
                        });
                    } else {
                        this.addDeployRow();
                    }
                } else if (key === 'lesson') {
                    const s7Lessons = s7.lessons_implementation || [];
                    if (s7Lessons.length) {
                        s7Lessons.forEach(l => {
                            this.addLessonRow({
                                stage: l.category || 'Verification',
                                problem_encountered: 'Process Variation / verification challenges',
                                solution_applied: l.actionable_insight,
                                lesson_learned: l.lesson
                            });
                        });
                    } else {
                        this.addLessonRow();
                    }
                } else if (key === 'benefit') {
                    const s7KPIs = s7.kpi_verification || [];
                    if (s7KPIs.length) {
                        s7KPIs.forEach(k => {
                            this.addBenefitRow({
                                category: k.metric,
                                before_metric: k.baseline,
                                after_metric: k.actual,
                                verified_by_facilitator: 'Yes (Verified in Stage 7)'
                            });
                        });
                    } else {
                        this.addBenefitRow();
                    }
                } else {
                    this[`add${this.capitalize(key)}Row`]();
                }
            }
        });

        const close = d.project_closure || {};
        this.setVal('s8_close_id', close.project_id || projectData.id);
        this.setVal('s8_close_start', close.start_date || projectData.start_date);
        this.setVal('s8_close_end', close.end_date);
        this.setVal('s8_close_status', close.final_status);
        this.setVal('s8_close_handover', close.handover_to);

        const gate = d.approval_gate || {};
        this.setVal('s8_gate_verified_by', gate.verified_by);
        this.setVal('s8_gate_role', gate.role);
        this.setVal('s8_gate_date', gate.date);
        this.setVal('s8_gate_status', gate.status);
        this.setVal('s8_gate_comments', gate.comments);

        // Load project SOP data
        this.loadSopData();

        // Load Closure Approval & Quality Gate Sign-Off Table
        const savedSignoff = d.signoff_table || [];
        this.renderSignoffTable(savedSignoff, projectData);

        if (window.lucide) lucide.createIcons();

        // Restrict Section 5 (Benefits Summary / Impact Review) to Facilitator & Admin only
        const user = QCMS.user || JSON.parse(sessionStorage.getItem('user') || '{}');
        const role = user.role ? (user.role.name || user.role) : 'Team Member';
        const roleNormalized = role.toLowerCase().trim().replace(/[^a-z0-9]/g, '');
        if (roleNormalized !== 'teammember') {
            this.disableBenefitSummarySection();
        }
    },

    async loadSopData() {
        const stepsContainer = document.getElementById('s8_sopStepsContainer');
        if (!stepsContainer) return;

        stepsContainer.innerHTML = `
            <div class="text-center py-3 text-muted">
                <div class="spinner-border spinner-border-sm text-primary opacity-50" role="status"></div>
                <p class="text-xs mt-2 mb-0">Loading SOP details...</p>
            </div>
        `;

        try {
            const sops = await api.get(`/sops?project_id=${this.projectData.id}`);
            if (sops && sops.length) {
                // Fetch the full details of the linked SOP
                const details = await api.get(`/sops/${sops[0].id}`);

                this.setVal('s8_sop_title', details.title);
                this.setVal('s8_sop_category', details.category);
                this.setVal('s8_sop_type', details.sop_type || 'Operational');
                this.setVal('s8_sop_description', details.description || '');
                this.setVal('s8_sop_applicability', details.applicability || '');
                this.setVal('s8_sop_purpose', details.purpose || '');
                this.setVal('s8_sop_scope', details.scope || '');
                this.setVal('s8_sop_responsibilities', details.responsibilities || '');

                stepsContainer.innerHTML = '';
                if (details.steps && details.steps.length) {
                    details.steps.forEach(st => this.addSopStepRow(st));
                } else {
                    this.addSopStepRow();
                }
            } else {
                const s4 = (this.projectData.workflows || []).find(w => w.stage_id === 4)?.data || {};
                const whyList = s4.why_why_analysis || [];
                const rootCause = whyList.length ? whyList[whyList.length - 1].root_cause : '';

                // Populate default pre-fills from project context
                this.setVal('s8_sop_title', this.projectData.title + ' SOP');
                this.setVal('s8_sop_category', this.projectData.category || 'Quality');
                this.setVal('s8_sop_type', 'Operational');
                this.setVal('s8_sop_description', "Standardization for Root Cause: " + rootCause);
                this.setVal('s8_sop_applicability', 'Applicable to sections affected by root cause: ' + rootCause);
                this.setVal('s8_sop_purpose', 'To standardize the corrections implemented to eliminate the root cause: ' + rootCause);
                this.setVal('s8_sop_scope', 'Applies to the departments and work areas specified in the project scope.');
                this.setVal('s8_sop_responsibilities', 'All operators and supervisors in the area are responsible for adhering to this standard.');

                stepsContainer.innerHTML = '';
                this.addSopStepRow();
            }
        } catch (e) {
            console.error('Failed to load SOP details', e);
            // Graceful fallback to default values
            this.setVal('s8_sop_title', this.projectData.title + ' SOP');
            this.setVal('s8_sop_category', this.projectData.category || 'Quality');
            this.setVal('s8_sop_type', 'Operational');

            stepsContainer.innerHTML = '';
            this.addSopStepRow();
        }
        const user = QCMS.user || JSON.parse(sessionStorage.getItem('user') || '{}');
        const role = user.role ? (user.role.name || user.role) : 'Team Member';
        const roleNormalized = role.toLowerCase().trim().replace(/[^a-z0-9]/g, '');
        if (roleNormalized !== 'teammember') {
            this.disableSopFields();
        }

        if (window.lucide) lucide.createIcons();
    },

    addSopStepRow(d = {}) {
        const c = document.getElementById('s8_sopStepsContainer');
        if (!c) return;
        const i = c.querySelectorAll('.w-step-row').length;
        const r = document.createElement('div');
        r.className = 'w-step-row p-3 mb-2 border rounded dyn-step-row';
        r.innerHTML = `
            <div class="d-flex justify-content-between align-items-center mb-2">
                <span class="fw-bold text-xs" style="color:var(--ds-text-tertiary);">Step ${i + 1}</span>
                <button type="button" class="ds-btn ds-btn-ghost text-danger p-1" onclick="this.closest('.w-step-row').remove(); StageModules[8].renumberSopSteps();" title="Remove Step">
                    <i data-lucide="trash-2" style="width:14px;height:14px;"></i>
                </button>
            </div>
            <div class="row g-2">
                <div class="col-md-12">
                    <label class="ds-label text-xs">Step Title *</label>
                    <input type="text" class="ds-input w-step-title" required placeholder="e.g. Set calibration pressure to 5.5 bar" value="${d.step_title || ''}">
                </div>
                <div class="col-md-12">
                    <label class="ds-label text-xs">Instructions *</label>
                    <textarea class="ds-input ds-textarea w-step-instructions" rows="2" required placeholder="e.g. 1. Access pneumatic control panel. 2. Verify pressure gauge reads 5.5 bar. 3. Adjust regulator knob if reading is outside 5.3-5.7 bar.">${d.instructions || ''}</textarea>
                </div>
                <div class="col-md-6">
                    <label class="ds-label text-xs">Safety Notes</label>
                    <input type="text" class="ds-input w-step-safety" placeholder="e.g. Wear safety glasses; isolate electric power before adjustment" value="${d.safety_notes || ''}" required>
                </div>
                <div class="col-md-6">
                    <label class="ds-label text-xs">Quality Checkpoints</label>
                    <input type="text" class="ds-input w-step-quality" placeholder="e.g. Pressure tolerance: 5.5 ±0.2 bar; check crimp jaws for alignment" value="${d.quality_checkpoints || ''}" required>
                </div>
            </div>
        `;
        c.appendChild(r);
        if (window.lucide) lucide.createIcons();
    },

    renumberSopSteps() {
        const rows = document.getElementById('s8_sopStepsContainer').querySelectorAll('.w-step-row');
        rows.forEach((r, idx) => {
            r.querySelector('.fw-bold').textContent = `Step ${idx + 1}`;
        });
    },

    collectSopSteps() {
        const container = document.getElementById('s8_sopStepsContainer');
        if (!container) return [];
        const rows = container.querySelectorAll('.w-step-row');
        return [...rows].map((r, idx) => ({
            step_number: idx + 1,
            step_title: r.querySelector('.w-step-title').value.trim(),
            instructions: r.querySelector('.w-step-instructions').value.trim(),
            safety_notes: r.querySelector('.w-step-safety').value.trim(),
            quality_checkpoints: r.querySelector('.w-step-quality').value.trim()
        }));
    },

    previewSop() {
        try {
            console.log("previewSop called");

            // Flexibly read form values across naming variants
            const getValFlex = (keys) => {
                for (let k of keys) {
                    const el = document.getElementById(k) || document.querySelector(`[name="${k}"]`) || document.querySelector(`[name*="${k}"]`);
                    if (el && el.value) return el.value.trim();
                }
                return '';
            };

            const title = getValFlex(['s8_sop_title', 'sop_title', 'title']);
            const category = getValFlex(['s8_sop_category', 'sop_category', 'category']);
            const type = getValFlex(['s8_sop_type', 'sop_type', 'type']);
            const purpose = getValFlex(['s8_sop_purpose', 'sop_purpose', 'purpose']);
            const scope = getValFlex(['s8_sop_scope', 'sop_scope', 'scope']);
            const applicability = getValFlex(['s8_sop_applicability', 'sop_applicability', 'applicability']);
            const responsibilities = getValFlex(['s8_sop_responsibilities', 'sop_responsibilities', 'responsibilities']);
            const steps = this.collectSopSteps();

            // Inject sopViewModal into DOM if not present
            let modalEl = document.getElementById('sopViewModal');
            if (!modalEl) {
                modalEl = document.createElement('div');
                modalEl.id = 'sopViewModal';
                modalEl.className = 'modal fade';
                modalEl.setAttribute('tabindex', '-1');
                modalEl.setAttribute('aria-hidden', 'true');
                modalEl.innerHTML = `
                    <div class="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable">
                        <div class="modal-content glass-card ds-card border-0" style="background:var(--ds-bg-card, #ffffff); color:var(--ds-text-primary, #1e293b);">
                            <div class="modal-header border-bottom p-4">
                                <div>
                                    <span class="badge bg-primary text-white mb-2" id="sop_v_status">Preview (Draft)</span>
                                    <h5 class="modal-title fw-bold" id="sop_v_title">SOP Details</h5>
                                    <p class="text-xs text-muted mb-0" id="sop_v_meta">SOP UID: Preview · Version: 1</p>
                                </div>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body p-4">
                                <div class="sop-document-view">
                                    <div class="mb-4">
                                        <h6 class="fw-bold text-primary border-bottom pb-2">1. Overview</h6>
                                        <div class="row g-3 text-sm">
                                            <div class="col-md-6"><strong>Process:</strong> <span id="sop_v_process">---</span></div>
                                            <div class="col-md-6"><strong>Type:</strong> <span id="sop_v_type">---</span></div>
                                            <div class="col-md-6"><strong>Category:</strong> <span id="sop_v_category">---</span></div>
                                            <div class="col-md-6"><strong>Version:</strong> <span id="sop_v_version">1</span></div>
                                        </div>
                                    </div>
                                    <div class="mb-4">
                                        <h6 class="fw-bold text-primary border-bottom pb-2">2. Purpose & Scope</h6>
                                        <div class="mb-3">
                                            <strong>Purpose:</strong>
                                            <p class="text-muted mt-1 text-sm bg-light p-2 rounded" id="sop_v_purpose" style="white-space:pre-wrap;">---</p>
                                        </div>
                                        <div class="mb-3">
                                            <strong>Scope:</strong>
                                            <p class="text-muted mt-1 text-sm bg-light p-2 rounded" id="sop_v_scope" style="white-space:pre-wrap;">---</p>
                                        </div>
                                        <div class="mb-3" id="sop_v_applicability_container">
                                            <strong>Applicability:</strong>
                                            <p class="text-muted mt-1 text-sm bg-light p-2 rounded" id="sop_v_applicability">---</p>
                                        </div>
                                    </div>
                                    <div class="mb-4">
                                        <h6 class="fw-bold text-primary border-bottom pb-2">3. Responsibilities</h6>
                                        <p class="text-muted text-sm bg-light p-2 rounded" id="sop_v_responsibilities" style="white-space:pre-wrap;">---</p>
                                    </div>
                                    <div class="mb-4">
                                        <h6 class="fw-bold text-primary border-bottom pb-2">4. Procedure Steps</h6>
                                        <div id="sop_v_steps_list" class="d-flex flex-column gap-3"></div>
                                    </div>
                                    <div class="mb-4">
                                        <h6 class="fw-bold text-primary border-bottom pb-2">5. Workflow Stakeholders</h6>
                                        <div class="row g-3 text-sm">
                                            <div class="col-md-4"><strong>Author / Owner:</strong> <span id="sop_v_author">---</span></div>
                                            <div class="col-md-4"><strong>Reviewer:</strong> <span id="sop_v_reviewer">---</span></div>
                                            <div class="col-md-4"><strong>Approver:</strong> <span id="sop_v_approver">---</span></div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div class="modal-footer border-top p-3">
                                <button type="button" class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Close Preview</button>
                            </div>
                        </div>
                    </div>
                `;
                document.body.appendChild(modalEl);
            }

            // Update modal preview fields
            const elTitle = document.getElementById('sop_v_title');
            const elProcess = document.getElementById('sop_v_process');
            const elType = document.getElementById('sop_v_type');
            const elCategory = document.getElementById('sop_v_category');
            const elPurpose = document.getElementById('sop_v_purpose');
            const elScope = document.getElementById('sop_v_scope');

            if (elTitle) elTitle.textContent = title || 'Standard Operating Procedure (SOP)';
            if (elProcess) elProcess.textContent = (this.projectData && this.projectData.title) ? this.projectData.title : (window.currentProject && window.currentProject.title ? window.currentProject.title : 'Operational');
            if (elType) elType.textContent = type || 'Operational';
            if (elCategory) elCategory.textContent = category || 'Quality';
            if (elPurpose) elPurpose.textContent = purpose || 'N/A';
            if (elScope) elScope.textContent = scope || 'N/A';

            const appContainer = document.getElementById('sop_v_applicability_container');
            const elApplicability = document.getElementById('sop_v_applicability');
            if (appContainer && elApplicability) {
                if (applicability) {
                    appContainer.style.display = 'block';
                    elApplicability.textContent = applicability;
                } else {
                    appContainer.style.display = 'none';
                }
            }

            const elResp = document.getElementById('sop_v_responsibilities');
            if (elResp) elResp.textContent = responsibilities || 'N/A';

            // Author, Reviewer, Approver displays
            const proj = this.projectData || window.currentProject || {};
            const author = proj.creator_name || proj.creator_username || 'Project Leader';
            const reviewer = proj.reviewer_name || 'Project Reviewer';
            const approver = proj.facilitator_name || 'Project Facilitator';

            const elAuth = document.getElementById('sop_v_author');
            const elRev = document.getElementById('sop_v_reviewer');
            const elApp = document.getElementById('sop_v_approver');

            if (elAuth) elAuth.textContent = author;
            if (elRev) elRev.textContent = reviewer;
            if (elApp) elApp.textContent = approver;

            // Steps preview
            const list = document.getElementById('sop_v_steps_list');
            if (list) {
                list.innerHTML = '';
                if (steps && steps.length) {
                    list.innerHTML = steps.map(s => `
                        <div class="p-3 border rounded bg-light">
                            <div class="fw-bold mb-2">Step ${s.step_number}: ${s.step_title || 'Untitled Step'}</div>
                            <p class="text-sm text-muted mb-2">${s.instructions || 'No instructions provided.'}</p>
                            ${s.safety_notes ? `<p class="text-xs mb-1"><span class="text-danger fw-bold"><i data-lucide="alert-triangle" style="width:12px;height:12px;vertical-align:text-bottom;"></i> Safety:</span> ${s.safety_notes}</p>` : ''}
                            ${s.quality_checkpoints ? `<p class="text-xs mb-0"><span class="text-success fw-bold"><i data-lucide="check" style="width:12px;height:12px;vertical-align:text-bottom;"></i> Quality Check:</span> ${s.quality_checkpoints}</p>` : ''}
                        </div>
                    `).join('');
                } else {
                    list.innerHTML = `<div class="text-muted text-center text-sm py-2">No procedure steps defined.</div>`;
                }
            }

            if (typeof bootstrap === 'undefined' || !bootstrap.Modal) {
                console.error("Bootstrap Modal library not loaded");
                if (window.QCMS && QCMS.toast) {
                    QCMS.toast("Bootstrap modal library is not loaded.", "error");
                } else {
                    alert("Bootstrap modal library is not loaded.");
                }
                return;
            }

            let modal = bootstrap.Modal.getInstance(modalEl);
            if (!modal) {
                modal = new bootstrap.Modal(modalEl);
            }
            modal.show();
            if (window.lucide) lucide.createIcons();
        } catch (err) {
            console.error('Error in previewSop:', err);
            if (window.QCMS && QCMS.toast) {
                QCMS.toast("Error opening SOP preview: " + err.message, "error");
            } else {
                alert("Error opening SOP preview: " + err.message);
            }
        }
    },

    validate() {
        const invalidFields = [];
        const reqs = [
            's8_sop_title', 's8_sop_category', 's8_sop_type',
            's8_sop_purpose', 's8_sop_scope', 's8_sop_responsibilities'
        ];

        reqs.forEach(id => {
            const val = this.getVal(id);
            if (!val || !val.trim()) {
                invalidFields.push(id);
            }
        });

        const steps = this.collectSopSteps();
        if (!steps.length) {
            invalidFields.push('s8_sopStepsContainer');
        } else {
            const container = document.getElementById('s8_sopStepsContainer');
            const stepRows = container.querySelectorAll('.w-step-row');
            stepRows.forEach(r => {
                const titleInput = r.querySelector('.w-step-title');
                const instText = r.querySelector('.w-step-instructions');

                if (!titleInput.value.trim()) {
                    titleInput.classList.add('is-invalid');
                    if (!invalidFields.includes('s8_sopStepsContainer')) {
                        invalidFields.push('s8_sopStepsContainer');
                    }
                } else {
                    titleInput.classList.remove('is-invalid');
                }

                if (!instText.value.trim()) {
                    instText.classList.add('is-invalid');
                    if (!invalidFields.includes('s8_sopStepsContainer')) {
                        invalidFields.push('s8_sopStepsContainer');
                    }
                } else {
                    instText.classList.remove('is-invalid');
                }
            });
        }

        return {
            valid: invalidFields.length === 0,
            invalidFields: invalidFields
        };
    },

    collectData() {
        return {
            standardization: this.collectRows('s8_stdContainer', ['.r-doc', '.r-prev', '.r-new', '.r-dt'], ['document', 'previous_version', 'new_version', 'update_date']),
            training_adoption: this.collectRows('s8_trainingContainer', ['.r-grp', '.r-dt', '.r-att', '.r-adp'], ['target_group', 'training_date', 'attendance_pct', 'adoption_status']),
            horizontal_deployment: this.collectRows('s8_deployContainer', ['.r-area', '.r-dt', '.r-stat', '.r-own'], ['area', 'target_date', 'status', 'owner']),
            lessons_learned: this.collectRows('s8_lessonContainer', ['.r-cat', '.r-les', '.r-rec'], ['category', 'lesson', 'future_recommendation']),
            benefits_summary: this.collectRows('s8_benefitContainer', ['.r-met', '.r-bas', '.r-fin', '.r-tot'], ['metric', 'baseline', 'final', 'total_savings']),
            remaining_opportunities: this.collectRows('s8_oppContainer', ['.r-prob', '.r-pri', '.r-nxt'], ['identified_problem', 'priority', 'next_steps']),
            knowledge_repository: this.collectRows('s8_repoContainer', ['.r-tag', '.r-sum', '.r-lnk'], ['keyword', 'summary', 'link']),
            team_recognition: this.collectRows('s8_teamContainer', ['.r-mem', '.r-con', '.r-awd'], ['member', 'contribution', 'award']),
            project_closure: {
                project_id: this.getVal('s8_close_id'),
                start_date: this.getVal('s8_close_start'),
                end_date: this.getVal('s8_close_end'),
                final_status: this.getVal('s8_close_status'),
                handover_to: this.getVal('s8_close_handover')
            },
            approval_gate: {
                verified_by: this.getVal('s8_gate_verified_by'),
                role: this.getVal('s8_gate_role'),
                date: this.getVal('s8_gate_date'),
                status: this.getVal('s8_gate_status'),
                comments: this.getVal('s8_gate_comments')
            },
            sop: {
                title: this.getVal('s8_sop_title'),
                category: this.getVal('s8_sop_category'),
                sop_type: this.getVal('s8_sop_type'),
                description: this.getVal('s8_sop_description'),
                applicability: this.getVal('s8_sop_applicability'),
                purpose: this.getVal('s8_sop_purpose'),
                scope: this.getVal('s8_sop_scope'),
                responsibilities: this.getVal('s8_sop_responsibilities'),
                steps: this.collectSopSteps()
            },
            signoff_table: this.collectSignoffTable()
        };
    },

    renderSignoffTable(savedList, projectData = {}) {
        const tbody = document.getElementById('s8_signoff_tbody');
        if (!tbody) return;

        tbody.innerHTML = '';
        let signoffRows = [];

        if (Array.isArray(savedList) && savedList.length > 0) {
            signoffRows = savedList;
        } else {
            const defaultDept = (projectData.department && projectData.department.name) ? projectData.department.name : (projectData.department || 'Quality Control');

            if (projectData.team_leader) {
                const tlName = projectData.team_leader.full_name || projectData.team_leader.username || '';
                if (tlName) {
                    signoffRows.push({
                        role: 'Team Leader',
                        name: tlName,
                        department: (projectData.team_leader.department && projectData.team_leader.department.name) ? projectData.team_leader.department.name : defaultDept,
                        signature: '',
                        date: ''
                    });
                }
            }

            if (projectData.facilitator) {
                const facName = projectData.facilitator.full_name || projectData.facilitator.username || '';
                if (facName) {
                    signoffRows.push({
                        role: 'QCC Facilitator',
                        name: facName,
                        department: (projectData.facilitator.department && projectData.facilitator.department.name) ? projectData.facilitator.department.name : defaultDept,
                        signature: '',
                        date: ''
                    });
                }
            }

            const revUser = projectData.reviewer || projectData.creator;
            if (revUser) {
                const revName = revUser.full_name || revUser.username || '';
                if (revName) {
                    signoffRows.push({
                        role: 'Reviewer',
                        name: revName,
                        department: (revUser.department && revUser.department.name) ? revUser.department.name : defaultDept,
                        signature: '',
                        date: ''
                    });
                }
            }

            const members = projectData.members || [];
            members.forEach((m, idx) => {
                const mName = m.full_name || m.username || '';
                if (mName) {
                    signoffRows.push({
                        role: `Team Member ${idx + 1}`,
                        name: mName,
                        department: (m.department && m.department.name) ? m.department.name : defaultDept,
                        signature: '',
                        date: ''
                    });
                }
            });

            if (signoffRows.length === 0) {
                signoffRows.push({
                    role: 'Team Leader',
                    name: '',
                    department: defaultDept,
                    signature: '',
                    date: ''
                });
            }
        }

        signoffRows.forEach(item => this.addSignoffRow(item));
    },

    addSignoffRow(d = {}) {
        const tbody = document.getElementById('s8_signoff_tbody');
        if (!tbody) return;

        const tr = document.createElement('tr');
        tr.className = 'dyn-signoff-row';
        tr.innerHTML = `
            <td class="py-1" style="width: 22%;">
                <input type="text" class="ds-input s8-signoff-role text-xs fw-bold" placeholder="e.g. Team Leader" value="${d.role || 'Team Member'}" required>
            </td>
            <td class="py-1" style="width: 25%;">
                <input type="text" class="ds-input s8-signoff-name text-xs" placeholder="Enter employee name..." value="${d.name || ''}" required>
            </td>
            <td class="py-1" style="width: 25%;">
                <input type="text" class="ds-input s8-signoff-dept text-xs" placeholder="Enter department/section..." value="${d.department || ''}" required>
            </td>
            <td class="py-1" style="width: 14%;">
                <input type="text" class="ds-input s8-signoff-sig text-xs" placeholder="Signature" value="${d.signature || ''}">
            </td>
            <td class="py-1" style="width: 10%;">
                <input type="date" class="ds-input s8-signoff-date text-xs" value="${d.date || ''}">
            </td>
            <td class="py-1 text-center" style="width: 4%;">
                <button type="button" class="ds-btn ds-btn-ghost text-danger p-1" onclick="this.closest('tr').remove()" title="Remove Role">
                    <i data-lucide="trash-2" style="width:14px;height:14px;"></i>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
        if (window.lucide) lucide.createIcons();
    },

    collectSignoffTable() {
        const tbody = document.getElementById('s8_signoff_tbody');
        if (!tbody) return [];
        const rows = tbody.querySelectorAll('.dyn-signoff-row');
        return [...rows].map(tr => ({
            role: (tr.querySelector('.s8-signoff-role')?.value || '').trim(),
            name: (tr.querySelector('.s8-signoff-name')?.value || '').trim(),
            department: (tr.querySelector('.s8-signoff-dept')?.value || '').trim(),
            signature: (tr.querySelector('.s8-signoff-sig')?.value || '').trim(),
            date: (tr.querySelector('.s8-signoff-date')?.value || '').trim()
        })).filter(x => x.role || x.name);
    },

    getMap(k) {
        return {
            'std': 'standardization', 'training': 'training_adoption', 'deploy': 'horizontal_deployment',
            'lesson': 'lessons_learned', 'benefit': 'benefits_summary', 'opp': 'remaining_opportunities',
            'repo': 'knowledge_repository', 'team': 'team_recognition'
        }[k];
    },
    capitalize(s) { return s.charAt(0).toUpperCase() + s.slice(1); },

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

    async handleFileChange(inputEl) {
        const file = inputEl.files[0];
        if (!file) return;

        // Find the input field relative to the file input element
        const container = inputEl.closest('.d-flex');
        if (!container) return;
        const docInput = container.querySelector('.r-doc') || container.querySelector('.r-lnk');
        if (!docInput) return;

        const originalVal = docInput.value;
        docInput.value = "Uploading...";
        docInput.disabled = true;

        try {
            const res = await api.uploadFile('/sop/upload', file);
            if (res && res.url) {
                docInput.value = window.location.origin + res.url;
                if (window.QCMS && QCMS.toast) {
                    QCMS.toast("File uploaded successfully", "success");
                }
            } else {
                throw new Error("Invalid response from server");
            }
        } catch (err) {
            console.error("Upload error:", err);
            docInput.value = originalVal;
            if (window.QCMS && QCMS.toast) {
                QCMS.toast("Upload failed: " + err.message, "error");
            } else {
                alert("Upload failed: " + err.message);
            }
        } finally {
            docInput.disabled = false;
        }
    },

    addRowTemplate(containerId, data, html) {
        const c = document.getElementById(containerId);
        const r = document.createElement('div');
        r.className = 'row g-2 mb-2 align-items-center dyn-row';
        r.innerHTML = html + '<div class="col-1"><button class="ds-btn ds-btn-ghost text-danger p-1" onclick="this.closest(\'.dyn-row\').remove()"><i data-lucide="trash-2" style="width:14px;"></i></button></div>';
        c.appendChild(r);
        if (window.lucide) lucide.createIcons();
    },

    addStdRow(d = {}) {
        this.addRowTemplate('s8_stdContainer', d, `
            <div class="col-4">
                <div class="d-flex gap-1">
                    <input type="text" class="ds-input r-doc" placeholder="e.g. Standard Document SOP-MFG-042" value="${d.document || ''}" style="flex-grow: 1;" required>
                    <label class="ds-btn ds-btn-ghost ds-btn-sm p-2 d-flex align-items-center justify-content-center" style="border: 1px solid var(--ds-input-border); min-width: 36px; border-radius: 10px; cursor: pointer; margin-bottom: 0;" title="Upload File">
                        <i data-lucide="upload" style="width:14px;height:14px;color:var(--ds-text-secondary);"></i>
                        <input type="file" style="display: none;" onchange="StageModules[8].handleFileChange(this)">
                    </label>
                </div>
            </div>
            <div class="col-3"><input type="text" class="ds-input r-prev" placeholder="e.g. v1.2" value="${d.previous_version || ''}" required></div>
            <div class="col-2"><input type="text" class="ds-input r-new" placeholder="e.g. v2.0" value="${d.new_version || ''}" required></div>
            <div class="col-2"><input type="date" class="ds-input r-dt" value="${d.update_date || ''}" required></div>`);
    },
    addTrainingRow(d = {}) {
        this.addRowTemplate('s8_trainingContainer', d, `
            <div class="col-4"><input type="text" class="ds-input r-grp" placeholder="e.g. Line A production operators" value="${d.target_group || ''}" required></div>
            <div class="col-3"><input type="date" class="ds-input r-dt" value="${d.training_date || ''}" required></div>
            <div class="col-2"><input type="number" class="ds-input r-att" placeholder="%" value="${d.attendance_pct || ''}" required></div>
            <div class="col-2"><input type="text" class="ds-input r-adp" placeholder="e.g. Completed" value="${d.adoption_status || ''}" required></div>`);
    },
    addDeployRow(d = {}) {
        this.addRowTemplate('s8_deployContainer', d, `
            <div class="col-4"><input type="text" class="ds-input r-area" placeholder="e.g. Welding Shop, Building 3" value="${d.area || ''}" required></div>
            <div class="col-2"><input type="date" class="ds-input r-dt" value="${d.target_date || ''}" required></div>
            <div class="col-2"><input type="text" class="ds-input r-stat" placeholder="e.g. Completed" value="${d.status || ''}" required></div>
            <div class="col-3"><input type="text" class="ds-input r-own" placeholder="e.g. Ravi Kumar" value="${d.owner || ''}" required></div>`);
    },
    addLessonRow(d = {}) {
        this.addRowTemplate('s8_lessonContainer', d, `
            <div class="col-3"><input type="text" class="ds-input r-cat" placeholder="e.g. Preventive Maintenance" value="${d.category || ''}" required></div>
            <div class="col-4"><input type="text" class="ds-input r-les" placeholder="e.g. Weekly lubrication extends crimp jaw life" value="${d.lesson || ''}" required></div>
            <div class="col-4"><input type="text" class="ds-input r-rec" placeholder="e.g. Schedule PM on Sunday morning shifts" value="${d.future_recommendation || ''}" required></div>`);
    },
    addBenefitRow(d = {}) {
        this.addRowTemplate('s8_benefitContainer', d, `
            <div class="col-3"><input type="text" class="ds-input r-met" placeholder="e.g. Scrap reduction" value="${d.metric || ''}" required></div>
            <div class="col-2"><input type="text" class="ds-input r-bas" placeholder="e.g. 4.2%" value="${d.baseline || ''}" required></div>
            <div class="col-2"><input type="text" class="ds-input r-fin" placeholder="e.g. 0.3%" value="${d.final || ''}" required></div>
            <div class="col-4"><input type="text" class="ds-input r-tot" placeholder="e.g. ₹1.2L per month" value="${d.total_savings || ''}" required></div>`);
    },
    addOppRow(d = {}) {
        this.addRowTemplate('s8_oppContainer', d, `
            <div class="col-5"><input type="text" class="ds-input r-prob" placeholder="e.g. Line B crimping defects" value="${d.identified_problem || ''}" required></div>
            <div class="col-2"><input type="text" class="ds-input r-pri" placeholder="e.g. High" value="${d.priority || ''}" required></div>
            <div class="col-4"><input type="text" class="ds-input r-nxt" placeholder="e.g. Replicate torque sensor setup" value="${d.next_steps || ''}" required></div>`);
    },
    addRepoRow(d = {}) {
        this.addRowTemplate('s8_repoContainer', d, `
            <div class="col-3"><input type="text" class="ds-input r-tag" placeholder="e.g. Pneumatic Crimping" value="${d.keyword || ''}" required></div>
            <div class="col-4"><input type="text" class="ds-input r-sum" placeholder="e.g. Project presentation and control charts" value="${d.summary || ''}" required></div>
            <div class="col-4">
                <div class="d-flex gap-1">
                    <input type="text" class="ds-input r-lnk" placeholder="e.g. https://sharepoint.corp/qc-projects/imfq-39.pdf" value="${d.link || ''}" style="flex-grow: 1;" required>
                    <label class="ds-btn ds-btn-ghost ds-btn-sm p-2 d-flex align-items-center justify-content-center" style="border: 1px solid var(--ds-input-border); min-width: 36px; border-radius: 10px; cursor: pointer; margin-bottom: 0;" title="Upload File">
                        <i data-lucide="upload" style="width:14px;height:14px;color:var(--ds-text-secondary);"></i>
                        <input type="file" style="display: none;" onchange="StageModules[8].handleFileChange(this)">
                    </label>
                </div>
            </div>`);
    },
    addTeamRow(d = {}) {
        this.addRowTemplate('s8_teamContainer', d, `
            <div class="col-3"><input type="text" class="ds-input r-mem" placeholder="e.g. Ravi Kumar" value="${d.member || ''}" required></div>
            <div class="col-5"><input type="text" class="ds-input r-con" placeholder="e.g. Identified root cause and designed torque sensor mount" value="${d.contribution || ''}" required></div>
            <div class="col-3"><input type="text" class="ds-input r-awd" placeholder="e.g. QC Champion Q2" value="${d.award || ''}" required></div>`);
    },

    disableSopFields() {
        const ids = [
            's8_sop_title', 's8_sop_category', 's8_sop_type',
            's8_sop_description', 's8_sop_applicability',
            's8_sop_purpose', 's8_sop_scope', 's8_sop_responsibilities'
        ];
        ids.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.disabled = true;
        });

        // Hide "Add Step" button
        const addStepBtns = document.querySelectorAll('#projectSopInlineForm button[onclick*="addSopStepRow"]');
        addStepBtns.forEach(btn => {
            btn.disabled = true;
            btn.style.display = 'none';
        });

        // Disable inputs inside steps container
        const stepsContainer = document.getElementById('s8_sopStepsContainer');
        if (stepsContainer) {
            stepsContainer.querySelectorAll('input, textarea, select, button').forEach(el => {
                el.disabled = true;
                if (el.tagName === 'BUTTON' || el.classList.contains('text-danger') || el.closest('button')) {
                    el.style.display = 'none';
                }
            });
        }
    },

    disableBenefitSummarySection() {
        // Hide the "Add Benefit" button
        const addBenefitBtn = document.querySelector('[onclick="StageModules[8].addBenefitRow()"]');
        if (addBenefitBtn) {
            addBenefitBtn.disabled = true;
            addBenefitBtn.style.display = 'none';
        }

        // Disable all inputs inside the benefit container
        const benefitContainer = document.getElementById('s8_benefitContainer');
        if (benefitContainer) {
            benefitContainer.querySelectorAll('input, textarea, select').forEach(el => {
                el.disabled = true;
                el.style.opacity = '0.6';
            });
            // Hide delete buttons on existing rows
            benefitContainer.querySelectorAll('button').forEach(btn => {
                btn.disabled = true;
                btn.style.display = 'none';
            });
        }

        // Add a role-restriction notice beneath the section heading
        const benefitSection = document.querySelector('[onclick="StageModules[8].addBenefitRow()"]')?.closest('.d-flex');
        if (benefitSection && !document.getElementById('benefitRoleNotice')) {
            const notice = document.createElement('div');
            notice.id = 'benefitRoleNotice';
            notice.className = 'alert alert-info text-xs mt-2 mb-0 py-2 px-3';
            notice.style.cssText = 'border-radius: var(--ds-radius-md); font-size: 0.75rem;';
            notice.innerHTML = '<i class="me-1">🔒</i><strong>Impact Review (Section 5)</strong> can only be filled in by the <strong>Team Member</strong>.';
            benefitSection.parentNode.insertBefore(notice, benefitSection.nextSibling);
        }
    },

    getVal(id) { return (document.getElementById(id) || {}).value || ''; },
    setVal(id, val) { const el = document.getElementById(id); if (el) el.value = val; }
};

window.StageModules = window.StageModules || {};
window.StageModules[8] = Stage8;
window.previewSop = function () {
    if (window.StageModules && window.StageModules[8] && window.StageModules[8].previewSop) {
        window.StageModules[8].previewSop();
    }
};
