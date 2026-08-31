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
                                <span class="ds-tooltip-trigger" title="Standardization & SOP: Formally documented step-by-step procedures locking in new process standard">Standardization &amp; SOP</span> <span class="text-danger">*</span>
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Update the SOP and procedure steps to lock in the new standard.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary ds-tooltip-trigger" title="Section 1 - Standardization & SOP: Full SOP document control & procedure definition">Section 1 - Standardization &amp; SOP</h6>
                            <button type="button" class="ds-btn ds-btn-primary" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[8].previewSop()">
                                <i data-lucide="eye" style="width:12px;height:12px;color:white;"></i> Preview Formatted SOP
                            </button>
                        </div>

                        <!-- Embedded Inline SOP Form -->
                        <div id="projectSopInlineForm" class="p-4 mb-4 border rounded" style="background:rgba(var(--ds-primary-rgb), 0.01); border-color:var(--ds-border-color) !important; border-radius:var(--ds-radius-lg);">
                            <h6 class="fw-bold mb-3 d-flex align-items-center gap-2 text-sm ds-tooltip-trigger" title="Standard Operating Procedure Details: Document header metadata" style="color:var(--ds-text-main);">
                                <i data-lucide="file-text" class="text-primary" style="width:16px;height:16px;"></i> Standard Operating Procedure (SOP) Details
                            </h6>
                            
                            <div class="row g-3">
                                <div class="col-md-6">
                                    <label class="ds-label ds-tooltip-trigger" title="SOP Title: Formal title of Standard Operating Procedure" for="s8_sop_title">SOP Title</label>
                                    <input type="text" id="s8_sop_title" class="ds-input" required placeholder="e.g., Boiler Temperature Calibration SOP">
                                </div>
                                <div class="col-md-3">
                                    <label class="ds-label ds-tooltip-trigger" title="Category: Process domain (Quality, Safety, Cost, Delivery)" for="s8_sop_category">Category</label>
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
                                    <label class="ds-label ds-tooltip-trigger" title="SOP Type: Document type classification" for="s8_sop_type">SOP Type</label>
                                    <select id="s8_sop_type" class="ds-input ds-select" required>
                                        <option value="Operational">Operational</option>
                                        <option value="Safety Standard">Safety Standard</option>
                                        <option value="Quality Control">Quality Control</option>
                                        <option value="Maintenance">Maintenance</option>
                                        <option value="Administrative">Administrative</option>
                                    </select>
                                </div>
                                
                                <div class="col-md-6">
                                    <label class="ds-label ds-tooltip-trigger" title="Description / Summary: Concise summary of standard operational procedure" for="s8_sop_description">Description / Summary</label>
                                    <input type="text" id="s8_sop_description" class="ds-input" placeholder="e.g. Standard calibration routine for wire crimper pneumatic cylinder pressure" required>
                                </div>
                                <div class="col-md-6">
                                    <label class="ds-label ds-tooltip-trigger" title="Applicability: Shop floor lines, equipment, or products covered by SOP" for="s8_sop_applicability">Applicability</label>
                                    <input type="text" id="s8_sop_applicability" class="ds-input" placeholder="e.g. Assembly Line A, crimping machines CT-400 & CT-401" required>
                                </div>
                                
                                <div class="col-md-6">
                                    <label class="ds-label ds-tooltip-trigger" title="SOP Owner / Author: Process owner responsible for drafting standard" for="s8_sop_owner">SOP Owner / Author</label>
                                    <input type="text" id="s8_sop_owner" class="ds-input" placeholder="e.g. Rajesh Kumar (Process Owner)" required>
                                </div>
                                <div class="col-md-6">
                                    <label class="ds-label ds-tooltip-trigger" title="SOP Approver: Authority responsible for approving and releasing this SOP" for="s8_sop_approver">SOP Approver Name</label>
                                    <input type="text" id="s8_sop_approver" class="ds-input" placeholder="e.g. Amit Sharma (Quality Head / Plant Manager)" required>
                                </div>

                                <div class="col-md-12">
                                    <label class="ds-label ds-tooltip-trigger" title="Attach Annexure or Supporting SOP Document (PDF, DOCX, XLSX, max 2MB)" for="s8_sop_attachment">SOP Attachment / Annexure Document</label>
                                    <div class="d-flex gap-2 align-items-center">
                                        <input type="text" id="s8_sop_attachment" class="ds-input" placeholder="Attach document link or upload file (Max 2MB)" style="flex-grow:1;">
                                        <label class="ds-btn ds-btn-outline ds-btn-sm d-flex align-items-center gap-1 py-2 px-3 mb-0" style="cursor:pointer; white-space:nowrap; border-radius:10px;" title="Upload Annexure / SOP Document (Max 2MB)">
                                            <i data-lucide="upload" style="width:14px;height:14px;"></i>
                                            <span>Upload Annexure</span>
                                            <input type="file" style="display: none;" accept=".pdf,.docx,.xlsx,.xls,.png,.jpg,.jpeg" onchange="StageModules[8].handleAnnexureUpload(this)">
                                        </label>
                                        <a id="s8_sop_attachment_view" href="#" target="_blank" class="ds-btn ds-btn-ghost text-primary p-2 d-none" title="Open Attached Document">
                                            <i data-lucide="external-link" style="width:15px;height:15px;"></i>
                                        </a>
                                    </div>
                                    <div class="form-text text-muted mt-1" style="font-size:0.75rem;">Upload documents size is 2MB (PDF, DOCX, XLSX, JPG, PNG)</div>
                                </div>
                                
                                <div class="col-md-6">
                                    <label class="ds-label ds-tooltip-trigger" title="Purpose: Core objective of implementing this standard procedure" for="s8_sop_purpose">Section 8.1.1: Purpose</label>
                                    <textarea id="s8_sop_purpose" class="ds-input ds-textarea" rows="2" required placeholder="e.g. To establish standard pressure settings and PM guidelines to eliminate wire crimping faults."></textarea>
                                </div>
                                <div class="col-md-6">
                                    <label class="ds-label ds-tooltip-trigger" title="Scope: Boundaries and operational areas covered by procedure" for="s8_sop_scope">Section 8.1.2: Scope</label>
                                    <textarea id="s8_sop_scope" class="ds-input ds-textarea" rows="2" required placeholder="e.g. Applies to all production operators and maintenance engineers working on Line A."></textarea>
                                </div>
                                <div class="col-md-12">
                                    <label class="ds-label ds-tooltip-trigger" title="Responsibilities: Specific roles responsible for executing and auditing procedure" for="s8_sop_responsibilities">Section 8.1.3: Responsibilities</label>
                                    <textarea id="s8_sop_responsibilities" class="ds-input ds-textarea" rows="2" required placeholder="e.g. Line Operator: Performs weekly pressure checks. Shift Supervisor: Performs monthly torque verification audits."></textarea>
                                </div>
                            </div>
                            
                            <hr class="section-divider my-4">
                            
                            <!-- Procedure Steps Builder -->
                            <div class="d-flex justify-content-between align-items-center mb-3">
                                <label class="ds-label mb-0 ds-tooltip-trigger" title="Procedure Steps: Sequential operational steps for execution" style="font-size: 0.8rem; font-weight: 600;">Section 8.1.4: Procedure Steps</label>
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

                        <div class="table-responsive" style="overflow-x: auto; -webkit-overflow-scrolling: touch;">
                            <div id="s8_stdContainer" class="mb-0" style="min-width: 680px;">
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
                        <div class="table-responsive" style="overflow-x: auto; -webkit-overflow-scrolling: touch;">
                            <div id="s8_trainingContainer" class="mb-0" style="min-width: 680px;">
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
                        <div class="table-responsive" style="overflow-x: auto; -webkit-overflow-scrolling: touch;">
                            <div id="s8_deployContainer" class="mb-0" style="min-width: 680px;">
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
                        <div class="table-responsive" style="overflow-x: auto; -webkit-overflow-scrolling: touch;">
                            <div id="s8_lessonContainer" class="mb-0" style="min-width: 680px;">
                                <div class="row text-muted small fw-bold mb-2 px-2">
                                    <div class="col-3">Category</div>
                                    <div class="col-4">Lesson</div>
                                    <div class="col-4">Future Recommendation</div>
                                    <div class="col-1"></div>
                                </div>
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
                        <div class="table-responsive" style="overflow-x: auto; -webkit-overflow-scrolling: touch;">
                            <div id="s8_benefitContainer" class="mb-0" style="min-width: 680px;">
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
                        <div class="table-responsive" style="overflow-x: auto; -webkit-overflow-scrolling: touch;">
                            <div id="s8_oppContainer" class="mb-0" style="min-width: 680px;">
                                <div class="row text-muted small fw-bold mb-2 px-2">
                                    <div class="col-5">Identified Problem</div>
                                    <div class="col-2">Priority</div>
                                    <div class="col-4">Next Steps</div>
                                    <div class="col-1"></div>
                                </div>
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
                        <div class="table-responsive" style="overflow-x: auto; -webkit-overflow-scrolling: touch;">
                            <div id="s8_repoContainer" class="mb-0" style="min-width: 680px;">
                                <div class="row text-muted small fw-bold mb-2 px-2">
                                    <div class="col-3">Keyword/Tag</div>
                                    <div class="col-4">Summary</div>
                                    <div class="col-4">Link to Asset</div>
                                    <div class="col-1"></div>
                                </div>
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
                        <div class="table-responsive" style="overflow-x: auto; -webkit-overflow-scrolling: touch;">
                            <div id="s8_teamContainer" class="mb-0" style="min-width: 680px;">
                                <div class="row text-muted small fw-bold mb-2 px-2">
                                    <div class="col-4">Member</div>
                                    <div class="col-7">Member Contribution</div>
                                    <div class="col-1"></div>
                                </div>
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
                                <label class="ds-label ds-tooltip-trigger" title="Project ID: Generated project identification code">Project ID</label>
                                <input type="text" id="s8_close_id" class="ds-input" readonly style="background:var(--ds-surface-raised); cursor:not-allowed;">
                            </div>
                            <div class="col-md-2">
                                <label class="ds-label">Start Date</label>
                                <input type="date" id="s8_close_start" class="ds-input" required>
                            </div>
                            <div class="col-md-2">
                                <label class="ds-label ds-tooltip-trigger" title="End Date: Today's system completion date (automatically fixed)">End Date</label>
                                <input type="date" id="s8_close_end" class="ds-input" readonly style="background:var(--ds-surface-raised); cursor:not-allowed;" required>
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

                <!-- Section 10 - Patentability, Technical Publications & Achievements -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">8.10</span>
                                Patentability, Technical Publications &amp; Achievements
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Document intellectual property (IP) potential, published research papers, convention presentations, and quality awards.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <!-- Part A: IP & Patentability -->
                        <div class="d-flex align-items-center gap-2 mb-3">
                            <span class="badge bg-primary-soft text-primary px-2 py-1" style="font-size:0.75rem; font-weight:600;"><i data-lucide="award" style="width:12px;height:12px;display:inline-block;vertical-align:middle;margin-right:4px;"></i> Part A: Intellectual Property (IP) &amp; Patentability</span>
                        </div>
                        <div class="row g-3 mb-4">
                            <div class="col-md-4">
                                <label class="ds-label ds-tooltip-trigger" title="Patentability Status: Determine whether the developed fixture, tooling, or algorithm qualifies for patenting" for="s8_ip_status">Patentability Status</label>
                                <select id="s8_ip_status" class="ds-input ds-select">
                                    <option value="Non-Patentable">Not Applicable / Standard Process Improvement (Non-Patentable)</option>
                                    <option value="Under Evaluation">Under IP Evaluation / Novel Tooling or Mechanism</option>
                                    <option value="Patent Application Filed">Provisional / Formal Patent Application Filed</option>
                                    <option value="Patent Granted">Patent Granted / Registered Industrial Design</option>
                                    <option value="Trade Secret">Trade Secret / Proprietary Know-How</option>
                                </select>
                            </div>
                            <div class="col-md-4">
                                <label class="ds-label ds-tooltip-trigger" title="Patent / IP Ref Number: Formal filing or docket identification number" for="s8_ip_ref_no">Patent / Filing Ref. Number</label>
                                <input type="text" id="s8_ip_ref_no" class="ds-input" placeholder="e.g. IN-2026-PAT-00452 or Pending">
                            </div>
                            <div class="col-md-4">
                                <label class="ds-label ds-tooltip-trigger" title="Patent / Invention Title: Official title of the invention or industrial design" for="s8_ip_title">Patent / Invention Title</label>
                                <input type="text" id="s8_ip_title" class="ds-input" placeholder="e.g. Automated Burr Trimming Mechanism">
                            </div>
                            <div class="col-12">
                                <label class="ds-label ds-tooltip-trigger" title="Key Novelty & Inventive Step: Describe what makes this mechanism or method inventive and technically superior" for="s8_ip_novelty">Key Novelty &amp; Innovative Features</label>
                                <textarea id="s8_ip_novelty" class="ds-textarea" rows="2" placeholder="Describe the innovative mechanism, tooling design, or algorithm that constitutes novel intellectual property..."></textarea>
                            </div>
                        </div>

                        <!-- Part B: Publications & Conventions -->
                        <div class="d-flex align-items-center gap-2 mb-3 pt-2 border-top">
                            <span class="badge bg-info-soft text-info px-2 py-1" style="font-size:0.75rem; font-weight:600;"><i data-lucide="book-open" style="width:12px;height:12px;display:inline-block;vertical-align:middle;margin-right:4px;"></i> Part B: Research Publications &amp; Convention Presentations</span>
                        </div>
                        <div class="row g-3 mb-4">
                            <div class="col-md-4">
                                <label class="ds-label ds-tooltip-trigger" title="Publication / Presentation Status: Type of public or industry forum where findings were presented" for="s8_pub_status">Publication / Forum Status</label>
                                <select id="s8_pub_status" class="ds-input ds-select">
                                    <option value="None">None / Confidential Internal Project</option>
                                    <option value="Journal Publication">Published in Peer-Reviewed Technical Journal</option>
                                    <option value="Quality Circle Convention">Presented at Quality Circle Convention (CCQC / NCQC / ICQCC)</option>
                                    <option value="Industry Conference">Presented at Industry Conference (ASQ / CII / Six Sigma Summit)</option>
                                    <option value="Internal Whitepaper">Internal Technical Whitepaper / Best Practice Case Study</option>
                                </select>
                            </div>
                            <div class="col-md-4">
                                <label class="ds-label ds-tooltip-trigger" title="Journal / Forum / Convention Name: Name of the journal, conference, or convention" for="s8_pub_forum">Journal / Forum / Convention Name</label>
                                <input type="text" id="s8_pub_forum" class="ds-input" placeholder="e.g. NCQC 2026 Mumbai / Int. Journal of Lean Six Sigma">
                            </div>
                            <div class="col-md-4">
                                <label class="ds-label ds-tooltip-trigger" title="Paper Title, DOI or Link: Title of published paper or citation URL" for="s8_pub_title_link">Paper Title / DOI / Citation Link</label>
                                <input type="text" id="s8_pub_title_link" class="ds-input" placeholder="e.g. Reduction of Trim Burr in Automotive Stamping (DOI/URL)">
                            </div>
                        </div>

                        <!-- Part C: Awards & Recognitions -->
                        <div class="d-flex align-items-center gap-2 mb-3 pt-2 border-top">
                            <span class="badge bg-success-soft text-success px-2 py-1" style="font-size:0.75rem; font-weight:600;"><i data-lucide="trophy" style="width:12px;height:12px;display:inline-block;vertical-align:middle;margin-right:4px;"></i> Part C: Honors, Awards &amp; Enterprise Scalability</span>
                        </div>
                        <div class="row g-3">
                            <div class="col-md-6">
                                <label class="ds-label ds-tooltip-trigger" title="Awards & Recognitions Won: Any internal or external competition awards won by this project" for="s8_awards_won">Awards &amp; Competitions Won</label>
                                <input type="text" id="s8_awards_won" class="ds-input" placeholder="e.g. Gold Trophy - NCQC 2026, Best Plant Kaizen Award">
                            </div>
                            <div class="col-md-6">
                                <label class="ds-label ds-tooltip-trigger" title="Enterprise Scalability Remarks: Commercial value, patent licensing, or replication potential across other facilities" for="s8_commercial_notes">Enterprise Replication &amp; Commercial Notes</label>
                                <textarea id="s8_commercial_notes" class="ds-textarea" rows="2" placeholder="Notes on cross-plant replication potential, ROI benefits for sister manufacturing units, or commercial licensing..."></textarea>
                            </div>
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
                } else if (key === 'team') {
                    const teamList = this.getProjectTeamList();
                    if (teamList.length) {
                        teamList.forEach(item => {
                            this.addTeamRow({ member: item.name, contribution: '' });
                        });
                    } else {
                        this.addTeamRow();
                    }
                } else {
                    this[`add${this.capitalize(key)}Row`]();
                }
            }
        });

        const close = d.project_closure || {};

        // 1. Display generated Project UID/Code (e.g. PRJ-EZPZ or PRJ-0035) instead of database integer ID
        const genProjectId = projectData.project_uid || projectData.uid || projectData.project_code || projectData.code || projectData.reference_number || (projectData.id ? `PRJ-${String(projectData.id).padStart(4, '0')}` : '---');
        this.setVal('s8_close_id', (close.project_id && close.project_id !== 'undefined' && isNaN(Number(close.project_id))) ? close.project_id : genProjectId);

        // 2. Start Date
        this.setVal('s8_close_start', close.start_date || projectData.start_date || new Date().toISOString().split('T')[0]);

        // 3. End Date: Automatically set to today's system date and enforce readonly
        const todayStr = new Date().toISOString().split('T')[0];
        const endDateVal = (close.end_date && close.end_date !== 'undefined') ? close.end_date : todayStr;
        this.setVal('s8_close_end', endDateVal);

        const endInput = document.getElementById('s8_close_end');
        if (endInput) {
            endInput.value = endDateVal;
            endInput.readOnly = true;
            endInput.disabled = true;
            endInput.style.cssText = 'background:var(--ds-surface-raised); cursor:not-allowed;';
        }

        // 4. Final Status
        this.setVal('s8_close_status', close.final_status || 'Completed Successfully');

        // 5. Handover To: Clean fallback if undefined
        const defaultHandover = projectData.reviewer_name || (projectData.reviewer ? (projectData.reviewer.full_name || projectData.reviewer.username) : '') || 'Process Owner / Plant Operations';
        const handoverVal = (close.handover_to && close.handover_to !== 'undefined') ? close.handover_to : defaultHandover;
        this.setVal('s8_close_handover', handoverVal);

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

        // Load Section 8.10 - Patentability, Publications & Achievements
        const ipPub = d.ip_patent_publication || {};
        this.setVal('s8_ip_status', ipPub.patentability_status || 'Non-Patentable');
        this.setVal('s8_ip_ref_no', ipPub.patent_ref_no || '');
        this.setVal('s8_ip_title', ipPub.patent_title || '');
        this.setVal('s8_ip_novelty', ipPub.novelty_description || '');
        this.setVal('s8_pub_status', ipPub.publication_status || 'None');
        this.setVal('s8_pub_forum', ipPub.forum_name || '');
        this.setVal('s8_pub_title_link', ipPub.paper_title_link || '');
        this.setVal('s8_awards_won', ipPub.awards_won || '');
        this.setVal('s8_commercial_notes', ipPub.commercial_notes || '');

        if (window.lucide) lucide.createIcons();

        // Restrict Section 5 (Benefits Summary / Impact Review) to Facilitator & Admin only
        const user = OctaQube.user || JSON.parse(sessionStorage.getItem('user') || '{}');
        const role = user.role ? (user.role.name || user.role) : 'Team Member';
        const roleNormalized = role.toLowerCase().trim().replace(/[^a-z0-9]/g, '');
        if (roleNormalized !== 'teammember') {
            this.disableBenefitSummarySection();
        }
    },

    async loadSopMasterOptions(savedCategory, savedType) {
        const selCat = document.getElementById('s8_sop_category');
        const selType = document.getElementById('s8_sop_type');
        if (!selCat && !selType) return;

        try {
            const res = await api.get('/sop/masters');
            const categories = res.categories || [];
            const types = res.types || [];

            if (selCat && categories.length) {
                selCat.innerHTML = categories.map(c => `<option value="${OctaQube.escapeHtml(c.name)}">${OctaQube.escapeHtml(c.name)}</option>`).join('');
                if (savedCategory) selCat.value = savedCategory;
            }

            if (selType && types.length) {
                selType.innerHTML = types.map(t => `<option value="${OctaQube.escapeHtml(t.name)}">${OctaQube.escapeHtml(t.name)}</option>`).join('');
                if (savedType) selType.value = savedType;
            }
        } catch (e) {
            console.warn('Using default SOP options:', e);
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

                await this.loadSopMasterOptions(details.category, details.sop_type || 'Operational');
                this.setVal('s8_sop_title', details.title);
                this.setVal('s8_sop_category', details.category);
                this.setVal('s8_sop_type', details.sop_type || 'Operational');
                this.setVal('s8_sop_description', details.description || '');
                this.setVal('s8_sop_applicability', details.applicability || '');
                this.setVal('s8_sop_owner', details.owner || details.author || details.created_by || this.projectData.team_leader_name || this.projectData.creator_name || '');
                this.setVal('s8_sop_approver', details.approver || details.approved_by || this.projectData.facilitator_name || this.projectData.reviewer_name || '');
                this.setVal('s8_sop_attachment', details.attachment_url || details.annexure_url || details.attachment || '');
                const attachView = document.getElementById('s8_sop_attachment_view');
                if (attachView) {
                    const url = details.attachment_url || details.annexure_url || details.attachment || '';
                    if (url) {
                        attachView.href = url;
                        attachView.classList.remove('d-none');
                    } else {
                        attachView.classList.add('d-none');
                    }
                }
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
                const d = (this.projectData.workflows || []).find(w => w.stage_id === 8)?.data || {};
                const savedSop = d.sop || {};

                await this.loadSopMasterOptions(savedSop.category || this.projectData.category || 'Quality', savedSop.sop_type || 'Operational');
                // Populate default pre-fills from project context or workflow data
                const proj = this.projectData || window.currentProject || {};
                this.setVal('s8_sop_title', savedSop.title || ((proj.title || 'Project') + ' SOP'));
                this.setVal('s8_sop_category', savedSop.category || proj.category || 'Quality');
                this.setVal('s8_sop_type', savedSop.sop_type || 'Operational');
                this.setVal('s8_sop_description', savedSop.description || ("Standardization for Root Cause: " + rootCause));
                this.setVal('s8_sop_applicability', savedSop.applicability || ('Applicable to sections affected by root cause: ' + rootCause));
                this.setVal('s8_sop_owner', savedSop.owner || proj.team_leader_name || proj.creator_name || 'Project Leader');
                this.setVal('s8_sop_approver', savedSop.approver || proj.facilitator_name || proj.reviewer_name || 'Plant Quality Head / Manager');
                this.setVal('s8_sop_attachment', savedSop.attachment_url || savedSop.attachment || '');
                const attachView = document.getElementById('s8_sop_attachment_view');
                if (attachView) {
                    const url = savedSop.attachment_url || savedSop.attachment || '';
                    if (url) {
                        attachView.href = url;
                        attachView.classList.remove('d-none');
                    } else {
                        attachView.classList.add('d-none');
                    }
                }
                this.setVal('s8_sop_purpose', savedSop.purpose || ('To standardize the corrections implemented to eliminate the root cause: ' + rootCause));
                this.setVal('s8_sop_scope', savedSop.scope || 'Applies to the departments and work areas specified in the project scope.');
                this.setVal('s8_sop_responsibilities', savedSop.responsibilities || 'All operators and supervisors in the area are responsible for adhering to this standard.');

                stepsContainer.innerHTML = '';
                if (savedSop.steps && savedSop.steps.length) {
                    savedSop.steps.forEach(st => this.addSopStepRow(st));
                } else {
                    this.addSopStepRow();
                }
            }
        } catch (e) {
            console.error('Failed to load SOP details', e);
            // Graceful fallback to default values
            const proj = this.projectData || window.currentProject || {};
            this.setVal('s8_sop_title', (proj.title || 'Project') + ' SOP');
            this.setVal('s8_sop_category', proj.category || 'Quality');
            this.setVal('s8_sop_type', 'Operational');
            this.setVal('s8_sop_owner', proj.team_leader_name || proj.creator_name || 'Project Leader');
            this.setVal('s8_sop_approver', proj.facilitator_name || proj.reviewer_name || 'Plant Quality Head / Manager');

            stepsContainer.innerHTML = '';
            this.addSopStepRow();
        }
        const user = OctaQube.user || JSON.parse(sessionStorage.getItem('user') || '{}');
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

        const cleanVal = (v) => (v === undefined || v === null || v === 'undefined' || v === 'null') ? '' : v;
        const stepTitle = cleanVal(d.step_title || d.title || d.name);
        const instructions = cleanVal(d.instructions || d.instruction || d.desc || d.description);
        const safetyNotes = cleanVal(d.safety_notes || d.safety);
        const qualityCheckpoints = cleanVal(d.quality_checkpoints || d.quality);
        const esc = (s) => (window.OctaQube && OctaQube.escapeHtml) ? OctaQube.escapeHtml(String(s)) : String(s).replace(/"/g, '&quot;');

        r.innerHTML = `
            <div class="d-flex justify-content-between align-items-center mb-2">
                <span class="fw-bold text-xs" style="color:var(--ds-text-tertiary);">Step ${i + 1}</span>
                <button type="button" class="ds-btn ds-btn-ghost text-danger p-1" onclick="this.closest('.w-step-row').remove(); StageModules[8].renumberSopSteps();" title="Remove Step">
                    <i data-lucide="trash-2" style="width:14px;height:14px;"></i>
                </button>
            </div>
            <div class="row g-2">
                <div class="col-md-12">
                    <label class="ds-label text-xs">Step Title <span class="text-danger" style="color: #ef4444 !important; font-weight: bold;">*</span></label>
                    <input type="text" class="ds-input w-step-title" required placeholder="e.g. Set calibration pressure to 5.5 bar" value="${esc(stepTitle)}">
                </div>
                <div class="col-md-12">
                    <label class="ds-label text-xs">Instructions <span class="text-danger" style="color: #ef4444 !important; font-weight: bold;">*</span></label>
                    <textarea class="ds-input ds-textarea w-step-instructions" rows="2" required placeholder="e.g. 1. Access pneumatic control panel. 2. Verify pressure gauge reads 5.5 bar. 3. Adjust regulator knob if reading is outside 5.3-5.7 bar.">${esc(instructions)}</textarea>
                </div>
                <div class="col-md-6">
                    <label class="ds-label text-xs">Safety Notes</label>
                    <input type="text" class="ds-input w-step-safety" placeholder="e.g. Wear safety glasses; isolate electric power before adjustment" value="${esc(safetyNotes)}">
                </div>
                <div class="col-md-6">
                    <label class="ds-label text-xs">Quality Checkpoints</label>
                    <input type="text" class="ds-input w-step-quality" placeholder="e.g. Pressure tolerance: 5.5 ±0.2 bar; check crimp jaws for alignment" value="${esc(qualityCheckpoints)}">
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
                                    <div class="mb-4" id="sop_v_attachment_container">
                                        <h6 class="fw-bold text-primary border-bottom pb-2">6. Annexure / Attached Document</h6>
                                        <div id="sop_v_attachment_content" class="text-sm">---</div>
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
            const owner = getValFlex(['s8_sop_owner', 'sop_owner', 'owner']) || proj.creator_name || proj.creator_username || 'Project Leader';
            const reviewer = proj.reviewer_name || 'Project Reviewer';
            const approver = getValFlex(['s8_sop_approver', 'sop_approver', 'approver']) || proj.facilitator_name || 'Project Facilitator';
            const attachmentUrl = getValFlex(['s8_sop_attachment', 'sop_attachment', 'attachment_url']);

            const elAuth = document.getElementById('sop_v_author');
            const elRev = document.getElementById('sop_v_reviewer');
            const elApp = document.getElementById('sop_v_approver');

            if (elAuth) elAuth.textContent = owner;
            if (elRev) elRev.textContent = reviewer;
            if (elApp) elApp.textContent = approver;

            const attachContainer = document.getElementById('sop_v_attachment_container');
            const attachContent = document.getElementById('sop_v_attachment_content');
            if (attachContainer && attachContent) {
                if (attachmentUrl) {
                    attachContainer.style.display = 'block';
                    attachContent.innerHTML = `<a href="${attachmentUrl}" target="_blank" class="ds-btn ds-btn-outline ds-btn-sm text-primary"><i data-lucide="external-link" style="width:13px;height:13px;margin-right:4px;"></i> View Attached Annexure / Document</a>`;
                } else {
                    attachContainer.style.display = 'none';
                }
            }

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
                if (window.OctaQube && OctaQube.toast) {
                    OctaQube.toast("Bootstrap modal library is not loaded.", "error");
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
            if (window.OctaQube && OctaQube.toast) {
                OctaQube.toast("Error opening SOP preview: " + err.message, "error");
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
                owner: this.getVal('s8_sop_owner'),
                approver: this.getVal('s8_sop_approver'),
                attachment_url: this.getVal('s8_sop_attachment'),
                purpose: this.getVal('s8_sop_purpose'),
                scope: this.getVal('s8_sop_scope'),
                responsibilities: this.getVal('s8_sop_responsibilities'),
                steps: this.collectSopSteps()
            },
            signoff_table: this.collectSignoffTable(),
            ip_patent_publication: {
                patentability_status: this.getVal('s8_ip_status'),
                patent_ref_no: this.getVal('s8_ip_ref_no'),
                patent_title: this.getVal('s8_ip_title'),
                novelty_description: this.getVal('s8_ip_novelty'),
                publication_status: this.getVal('s8_pub_status'),
                forum_name: this.getVal('s8_pub_forum'),
                paper_title_link: this.getVal('s8_pub_title_link'),
                awards_won: this.getVal('s8_awards_won'),
                commercial_notes: this.getVal('s8_commercial_notes')
            }
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

    async handleAnnexureUpload(inputEl) {
        const file = inputEl.files[0];
        if (!file) return;

        // Strict 2MB Limitation (2 * 1024 * 1024 bytes)
        const MAX_SIZE_BYTES = 2 * 1024 * 1024;
        if (file.size > MAX_SIZE_BYTES) {
            const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
            const msg = `File size exceeds 2MB limit (Selected: ${sizeMB} MB). Please upload a document up to 2MB.`;
            if (window.OctaQube && OctaQube.toast) OctaQube.toast(msg, "warning");
            else alert(msg);
            inputEl.value = '';
            return;
        }

        const attachInput = document.getElementById('s8_sop_attachment');
        const viewLink = document.getElementById('s8_sop_attachment_view');
        if (!attachInput) return;

        const originalVal = attachInput.value;
        attachInput.value = "Uploading...";
        attachInput.disabled = true;

        try {
            const res = await api.uploadFile('/sop/upload', file);
            if (res && res.url) {
                const fullUrl = window.location.origin + res.url;
                attachInput.value = fullUrl;
                if (viewLink) {
                    viewLink.href = fullUrl;
                    viewLink.classList.remove('d-none');
                }
                if (window.OctaQube && OctaQube.toast) {
                    OctaQube.toast("Annexure / SOP uploaded successfully (Under 2MB limit)", "success");
                }
            } else {
                throw new Error("Invalid response from server");
            }
        } catch (err) {
            console.error("Upload error:", err);
            attachInput.value = originalVal;
            if (window.OctaQube && OctaQube.toast) {
                OctaQube.toast("Upload failed: " + (err.message || 'File upload error'), "error");
            } else {
                alert("Upload failed: " + (err.message || 'File upload error'));
            }
        } finally {
            attachInput.disabled = false;
            inputEl.value = '';
        }
    },

    async handleFileChange(inputEl) {
        const file = inputEl.files[0];
        if (!file) return;

        // Strict 2MB Limitation (2 * 1024 * 1024 bytes)
        const MAX_SIZE_BYTES = 2 * 1024 * 1024;
        if (file.size > MAX_SIZE_BYTES) {
            const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
            const msg = `File size exceeds 2MB limit (Selected: ${sizeMB} MB). Please upload a document up to 2MB.`;
            if (window.OctaQube && OctaQube.toast) {
                OctaQube.toast(msg, "warning");
            } else {
                alert(msg);
            }
            inputEl.value = '';
            return;
        }

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
                if (window.OctaQube && OctaQube.toast) {
                    OctaQube.toast("File uploaded successfully (Under 2MB limit)", "success");
                }
            } else {
                throw new Error("Invalid response from server");
            }
        } catch (err) {
            console.error("Upload error:", err);
            docInput.value = originalVal;
            if (window.OctaQube && OctaQube.toast) {
                OctaQube.toast("Upload failed: " + (err.message || 'File upload error'), "error");
            } else {
                alert("Upload failed: " + (err.message || 'File upload error'));
            }
        } finally {
            docInput.disabled = false;
            inputEl.value = '';
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
                    <label class="ds-btn ds-btn-ghost ds-btn-sm p-2 d-flex align-items-center justify-content-center" style="border: 1px solid var(--ds-input-border); min-width: 36px; border-radius: 10px; cursor: pointer; margin-bottom: 0;" title="Upload Document (Max 2MB)">
                        <i data-lucide="upload" style="width:14px;height:14px;color:var(--ds-text-secondary);"></i>
                        <input type="file" style="display: none;" accept=".pdf,.docx,.xlsx,.xls,.png,.jpg,.jpeg" onchange="StageModules[8].handleFileChange(this)">
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
                    <input type="text" class="ds-input r-lnk" placeholder="e.g. https://sharepoint.corp/qc-projects/imfq-39.pdf" value="${d.link || ''}" style="flex-grow: 1;">
                    <label class="ds-btn ds-btn-ghost ds-btn-sm p-2 d-flex align-items-center justify-content-center" style="border: 1px solid var(--ds-input-border); min-width: 36px; border-radius: 10px; cursor: pointer; margin-bottom: 0;" title="Upload Document (Max 2MB)">
                        <i data-lucide="upload" style="width:14px;height:14px;color:var(--ds-text-secondary);"></i>
                        <input type="file" style="display: none;" accept=".pdf,.docx,.xlsx,.xls,.png,.jpg,.jpeg" onchange="StageModules[8].handleFileChange(this)">
                    </label>
                </div>
            </div>`);
    },
    getProjectTeamList() {
        const list = [];
        const p = this.projectData || window.currentProject || {};

        // 1. Add Team Leader
        let tlName = '';
        if (p.team_leader) {
            tlName = (typeof p.team_leader === 'object') ? (p.team_leader.full_name || p.team_leader.username) : p.team_leader;
        }
        if (!tlName && p.team_leader_name) {
            tlName = p.team_leader_name;
        }
        if (!tlName && p.team_leader_id) {
            const orgUser = (window.orgUsers || []).find(u => u.id == p.team_leader_id);
            if (orgUser) tlName = orgUser.full_name || orgUser.username;
        }
        if (tlName && typeof tlName === 'string' && tlName.trim()) {
            const cleanLeader = tlName.trim();
            list.push({ name: cleanLeader, label: `${cleanLeader} (Team Leader)`, isLeader: true });
        }

        // 2. Add Members from p.members / p.team_members
        const rawMembers = p.members || p.team_members || [];
        if (Array.isArray(rawMembers)) {
            rawMembers.forEach(m => {
                const mName = (typeof m === 'object') ? (m.full_name || m.name || m.username) : m;
                if (mName && typeof mName === 'string' && mName.trim()) {
                    const cleanName = mName.trim();
                    if (!list.some(item => item.name === cleanName)) {
                        list.push({ name: cleanName, label: cleanName, isLeader: false });
                    }
                }
            });
        }

        // 3. Add Members from p.member_ids using window.orgUsers
        if (Array.isArray(p.member_ids)) {
            p.member_ids.forEach(id => {
                if (p.team_leader_id && id == p.team_leader_id) return;
                const orgUser = (window.orgUsers || []).find(u => u.id == id);
                if (orgUser) {
                    const uName = orgUser.full_name || orgUser.username;
                    if (uName && typeof uName === 'string' && uName.trim()) {
                        const cleanName = uName.trim();
                        if (!list.some(item => item.name === cleanName)) {
                            list.push({ name: cleanName, label: cleanName, isLeader: false });
                        }
                    }
                }
            });
        }

        // 4. Fallback to Stage 1 team data if available
        const wf = p.workflows || [];
        const s1 = wf.find(w => w.stage_id === 1)?.data || {};
        const s1Members = (s1.team && s1.team.team_members) ? s1.team.team_members : [];
        if (Array.isArray(s1Members)) {
            s1Members.forEach(m => {
                const mName = m.name || m.full_name || m.username;
                if (mName && typeof mName === 'string' && mName.trim()) {
                    const cleanName = mName.trim();
                    if (!list.some(item => item.name === cleanName)) {
                        list.push({ name: cleanName, label: cleanName, isLeader: false });
                    }
                }
            });
        }

        return list;
    },

    addTeamRow(d = {}) {
        const teamList = this.getProjectTeamList();
        const savedMember = (d.member || '').trim();

        let optionsHtml = `<option value="">Select Team Member...</option>`;
        let foundSaved = false;

        teamList.forEach(item => {
            const isSelected = (savedMember === item.name || savedMember === item.label) ? 'selected' : '';
            if (isSelected) foundSaved = true;
            optionsHtml += `<option value="${OctaQube.escapeHtml(item.name)}" ${isSelected}>${OctaQube.escapeHtml(item.label)}</option>`;
        });

        if (savedMember && !foundSaved) {
            optionsHtml += `<option value="${OctaQube.escapeHtml(savedMember)}" selected>${OctaQube.escapeHtml(savedMember)}</option>`;
        }

        const awardBadge = d.award ? `
            <div class="mt-1 d-flex align-items-center gap-1">
                <span class="badge bg-success-subtle text-success border border-success-subtle" style="font-size: 0.72rem; padding: 2px 6px;">
                    <i data-lucide="award" style="width:11px;height:11px;vertical-align:text-bottom;"></i> Award Granted by Reviewer: <strong>${OctaQube.escapeHtml(d.award)}</strong>
                </span>
            </div>` : '';

        this.addRowTemplate('s8_teamContainer', d, `
            <div class="col-4">
                <select class="ds-input ds-select r-mem ds-tooltip-trigger" title="Project Member: Select Team Leader or Team Member assigned to this project" required>
                    ${optionsHtml}
                </select>
            </div>
            <div class="col-7">
                <input type="text" class="ds-input r-con ds-tooltip-trigger" title="Contribution: Enter member specific contributions and achievements for reviewer evaluation" placeholder="Enter specific member contribution (e.g. Root cause analysis, Tooling design)..." value="${d.contribution || ''}" required>
                ${awardBadge}
                <input type="hidden" class="r-awd" value="${d.award || ''}">
            </div>`);
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
