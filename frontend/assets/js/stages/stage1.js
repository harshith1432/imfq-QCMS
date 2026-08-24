const Stage1 = {
    renderHTML() {
        return `
            <!-- STAGE 1 FORM -->
            <div id="stage1Form">
                <!-- ─── SECTION 1: PROJECT TEAM ─── -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">1.1</span>
                                Project Team <span class="text-danger">*</span>
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Register the QC Circle members, their roles, and department for this project.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="row g-3">
                            <div class="col-md-4">
                                <div class="ds-field">
                                    <label class="ds-label ds-tooltip-trigger" title="QC Circle Name: Frontline quality control circle group name">QC Circle Name</label>
                                    <input type="text" class="ds-input" id="s1_circle_name" placeholder="e.g. Quality Warriors" required>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="ds-field">
                                    <label class="ds-label ds-tooltip-trigger" title="Work Area: Operational shop floor line, plant area, or department">Work Area</label>
                                    <input type="text" class="ds-input" id="s1_work_area" readonly>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="ds-field">
                                    <label class="ds-label ds-tooltip-trigger" title="Sponsor: Executive sponsor providing project oversight and resources">Sponsor</label>
                                    <input type="text" class="ds-input" id="s1_sponsor" placeholder="e.g. Plant Manager" required>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="ds-field">
                                    <label class="ds-label ds-tooltip-trigger" title="Facilitator: Quality/Lean Coach guiding project methodology execution">Facilitator</label>
                                    <input type="text" class="ds-input" id="s1_facilitator" readonly>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="ds-field">
                                    <label class="ds-label ds-tooltip-trigger" title="Team Leader: Lead employee driving daily circle activities and stage completion">Team Leader</label>
                                    <input type="text" class="ds-input" id="s1_team_leader" readonly>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="ds-field">
                                    <label class="ds-label ds-tooltip-trigger" title="Reviewer: Quality Manager reviewing stage gate submission">Reviewer</label>
                                    <input type="text" class="ds-input" id="s1_reviewer" readonly>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="ds-field">
                                    <label class="ds-label ds-tooltip-trigger" title="Duration: Total project schedule duration calculated from start to target completion date">Duration</label>
                                    <input type="text" class="ds-input" id="s1_duration" readonly placeholder="Calculated from dates">
                                </div>
                            </div>
                        </div>

                        <hr class="section-divider">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <label class="ds-label mb-0">Team Members</label>
                        </div>
                        <div class="team-member-row mb-2" style="display:grid;grid-template-columns:2fr 1fr;gap:.5rem;">
                            <small class="ds-label fw-bold">Team Member</small>
                            <small class="ds-label fw-bold">Role</small>
                        </div>
                        <div id="teamMembersContainer"></div>
                    </div>
                </div>

                <!-- ─── SECTION 2: PROBLEM BACKGROUND (5W2H) ─── -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">1.2</span>
                                <span class="ds-tooltip-trigger" title="5W2H Framework: What, Why, When, Where, Who, How, How Much - Standard structured problem definition tool">Problem Background (5W2H)</span> <span class="text-danger">*</span>
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Define the problem using What, Why, When, Where, Who, and How Much before analysis begins.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="row g-3">
                            <div class="col-md-6">
                                <div class="ds-field">
                                    <label class="ds-label ds-tooltip-trigger" title="What Happened? Describe the specific defect, symptom, or failure mode encountered">What Happened?</label>
                                    <textarea class="ds-input ds-textarea" id="s1_5w2h_what" rows="2" placeholder="e.g. Defect rate on Line A exceeds 4% causing rework and customer returns" required></textarea>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="ds-field">
                                    <label class="ds-label ds-tooltip-trigger" title="Where Did It Happen? Specify exact physical location, line, machine, or process step">Where Did It Happen?</label>
                                    <textarea class="ds-input ds-textarea" id="s1_5w2h_where" rows="2" placeholder="e.g. Assembly Line A, Weld Shop, Building 3" required></textarea>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="ds-field">
                                    <label class="ds-label ds-tooltip-trigger" title="When Did It Happen? Specify time frame, shift, start date, or recurrence pattern">When Did It Happen?</label>
                                    <textarea class="ds-input ds-textarea" id="s1_5w2h_when" rows="2" placeholder="e.g. Since January 2025; recurring every Monday morning shift" required></textarea>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="ds-field">
                                    <label class="ds-label ds-tooltip-trigger" title="Who Is Complaining? Name internal or external customers or stakeholders affected">Who Is Complaining?</label>
                                    <textarea class="ds-input ds-textarea" id="s1_5w2h_who" rows="2" placeholder="e.g. Key customer ABC Ltd. raised 23 complaints in Q1 2025" required></textarea>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="ds-field">
                                    <label class="ds-label ds-tooltip-trigger" title="Why Is The Customer Complaining? Customer perspective on why this defect is unacceptable">Why Is The Customer Complaining?</label>
                                    <textarea class="ds-input ds-textarea" id="s1_5w2h_why" rows="2" placeholder="e.g. Products delivered with surface scratches, failing their inspection criteria" required></textarea>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="ds-field">
                                    <label class="ds-label ds-tooltip-trigger" title="How Was It Discovered? Inspection method, audit, customer complaint, or testing device">How Was It Discovered?</label>
                                    <textarea class="ds-input ds-textarea" id="s1_5w2h_how_discovered" rows="2" placeholder="e.g. Detected during final QC inspection and flagged in customer returns" required></textarea>
                                </div>
                            </div>
                            <div class="col-12">
                                <div class="ds-field">
                                    <label class="ds-label ds-tooltip-trigger" title="How Big Is The Problem? Quantifiable magnitude (defect %, complaint count, financial loss)">How Big Is The Problem?</label>
                                    <textarea class="ds-input ds-textarea" id="s1_5w2h_how_big" rows="2" placeholder="e.g. 4.2% defect rate, 23 complaints in Q1, costing ₹1,20,000 per month" required></textarea>
                                </div>
                            </div>
                            <div class="col-12">
                                <div class="ds-field">
                                    <label class="ds-label ds-tooltip-trigger" title="Problem Definition: Concise problem summary combining 5W2H facts into a clear baseline statement">Problem Definition</label>
                                    <textarea class="ds-input ds-textarea" id="s1_5w2h_problem_definition" rows="3" placeholder="e.g. Reject rate of crimping defects has increased to 4.2% since Jan 2025, causing 23 customer complaints in Q1 and ₹1.2L monthly rework loss." required></textarea>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- ─── SECTION 3: CURRENT PERFORMANCE ─── -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">1.3</span>
                                <span class="ds-tooltip-trigger" title="Current Performance Baseline: Measured starting level of key metrics prior to improvement">Current Performance</span> <span class="text-danger">*</span>
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Record the baseline metric and current performance level the project aims to improve.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="row g-3">
                            <div class="col-md-4">
                                <div class="ds-field"><label class="ds-label ds-tooltip-trigger" title="Current KPI: Primary quantifiable metric baseline level before improvement">Current KPI</label><input type="text" class="ds-input" id="s1_cp_kpi" placeholder="e.g. 4.2% defect rate" required></div>
                            </div>
                            <div class="col-md-4">
                                <div class="ds-field"><label class="ds-label ds-tooltip-trigger" title="Current Defect Rate: Baseline percentage of non-conforming parts or process errors">Current Defect Rate</label><input type="text" class="ds-input" id="s1_cp_defect_rate" placeholder="e.g. 4.2%" required></div>
                            </div>
                            <div class="col-md-4">
                                <div class="ds-field"><label class="ds-label ds-tooltip-trigger" title="Current Complaint Count: Total customer or internal quality complaints logged per period">Current Complaint Count</label><input type="number" class="ds-input" id="s1_cp_complaints" placeholder="e.g. 23 complaints in Q1" required></div>
                            </div>
                            <div class="col-md-4">
                                <div class="ds-field"><label class="ds-label ds-tooltip-trigger" title="Current Cost Impact: Baseline monthly or annual financial loss caused by defect">Current Cost Impact</label><input type="text" class="ds-input" id="s1_cp_cost_impact" placeholder="e.g. ₹1,20,000 per month" required></div>
                            </div>
                            <div class="col-md-4">
                                <div class="ds-field"><label class="ds-label ds-tooltip-trigger" title="Current Downtime: Equipment or process stoppage time caused by defect">Current Downtime</label><input type="text" class="ds-input" id="s1_cp_downtime" placeholder="e.g. 45 minutes per shift" required></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- ─── SECTION 4: JUSTIFICATION ─── -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">1.4</span>
                                <span class="ds-tooltip-trigger" title="Justification: Financial, customer, quality, safety, delivery, and regulatory business case for project selection">Justification</span> <span class="text-danger">*</span>
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">State the business case for why this problem was selected over other opportunities.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="row g-3">
                            <div class="col-md-6"><div class="ds-field"><label class="ds-label ds-tooltip-trigger" title="Financial Impact: Monthly or annual monetary loss due to rework, scrap, and warranty claims">Financial Impact</label><textarea class="ds-input ds-textarea" id="s1_j_financial" rows="2" placeholder="e.g. Rework and scrap costs ₹1,20,000 per month, impacting margins by 8%" required></textarea></div></div>
                            <div class="col-md-6"><div class="ds-field"><label class="ds-label ds-tooltip-trigger" title="Customer Impact: Risk to customer satisfaction, account retention, and delivery metrics">Customer Impact</label><textarea class="ds-input ds-textarea" id="s1_j_customer" rows="2" placeholder="e.g. 23 customer complaints in Q1; risk of losing key account ABC Ltd." required></textarea></div></div>
                            <div class="col-md-6"><div class="ds-field"><label class="ds-label ds-tooltip-trigger" title="Quality Impact: Defect rate or process error level exceeding acceptable quality limits">Quality Impact</label><textarea class="ds-input ds-textarea" id="s1_j_quality" rows="2" placeholder="e.g. Defect rate of 4.2% exceeds the 1% acceptable quality limit" required></textarea></div></div>
                            <div class="col-md-6"><div class="ds-field"><label class="ds-label ds-tooltip-trigger" title="Safety Impact: Occupational safety risks, hazard exposure, or near-miss incidents">Safety Impact</label><textarea class="ds-input ds-textarea" id="s1_j_safety" rows="2" placeholder="e.g. Faulty components pose risk of injury during handling; 2 near-miss incidents recorded" required></textarea></div></div>
                            <div class="col-md-6"><div class="ds-field"><label class="ds-label ds-tooltip-trigger" title="Delivery Impact: Dispatch delays, bottlenecking, or schedule non-conformance caused by defect">Delivery Impact</label><textarea class="ds-input ds-textarea" id="s1_j_delivery" rows="2" placeholder="e.g. Rework delays dispatch by 2 days, causing late deliveries on 15% of orders" required></textarea></div></div>
                            <div class="col-md-6"><div class="ds-field"><label class="ds-label ds-tooltip-trigger" title="Regulatory Impact: ISO/IATF quality standard non-conformance or compliance audit risk">Regulatory Impact</label><textarea class="ds-input ds-textarea" id="s1_j_regulatory" rows="2" placeholder="e.g. Non-compliance with ISO 9001 Clause 8.7; risk of audit non-conformance" required></textarea></div></div>
                            <div class="col-12"><div class="ds-field"><label class="ds-label ds-tooltip-trigger" title="Why Should Organization Work On This Problem?: Strategic rationale explaining organizational value of solving this problem">Why Should The Organization Work On This Problem?</label><textarea class="ds-input ds-textarea" id="s1_j_why" rows="3" placeholder="e.g. Addressing this defect will save ₹1,20,000/month, restore customer trust, and ensure ISO compliance" required></textarea></div></div>
                        </div>
                    </div>
                </div>

                <!-- ─── SECTION 5: EMERGENCY RESPONSE ─── -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">1.5</span>
                                <span class="ds-tooltip-trigger" title="Emergency Response: Immediate containment actions taken to protect customers before root cause elimination">Emergency Response</span> <span class="text-danger">*</span>
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Log any immediate containment action taken before formal countermeasures are in place.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="ds-field mb-3">
                            <label class="ds-label ds-tooltip-trigger" title="Is Emergency Response Required?: Flag whether temporary quarantine or containment controls were put in place">Is Emergency Response Required?</label>
                            <div class="h-stack gap-3">
                                <label class="h-stack gap-2 cursor-pointer"><input type="radio" name="emergencyRequired" value="yes" onchange="StageModules[1].toggleEmergency(true)"> Yes</label>
                                <label class="h-stack gap-2 cursor-pointer"><input type="radio" name="emergencyRequired" value="no" checked onchange="StageModules[1].toggleEmergency(false)"> No</label>
                            </div>
                        </div>
                        <div id="emergencyFields" class="d-none">
                            <div class="row g-3">
                                <div class="col-md-12"><div class="ds-field"><label class="ds-label ds-tooltip-trigger" title="Containment Action: Description of temporary quarantine, 100% inspection, or segregation controls">Containment Action</label><textarea class="ds-input ds-textarea" id="s1_er_action" rows="2" placeholder="e.g. Segregate all WIP stock; 100% visual inspection before dispatch until further notice" required></textarea></div></div>
                                <div class="col-md-4"><div class="ds-field"><label class="ds-label ds-tooltip-trigger" title="Responsible Person: Person in charge of overseeing the emergency containment action">Responsible Person</label><input type="text" class="ds-input" id="s1_er_responsible" placeholder="e.g. Rajesh Kumar (QC Engineer)" required></div></div>
                                <div class="col-md-3"><div class="ds-field"><label class="ds-label ds-tooltip-trigger" title="Start Date: Date containment response was initiated">Start Date</label><input type="date" class="ds-input" id="s1_er_start_date" required></div></div>
                                <div class="col-md-3"><div class="ds-field"><label class="ds-label ds-tooltip-trigger" title="Completion Date: Date containment response ends">Completion Date</label><input type="date" class="ds-input" id="s1_er_completion_date" required></div></div>
                                <div class="col-md-2"><div class="ds-field"><label class="ds-label ds-tooltip-trigger" title="Status: Current execution status of emergency response">Status</label><select class="ds-input ds-select" id="s1_er_status" required><option>Planned</option><option>In Progress</option><option>Completed</option></select></div></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- ─── SECTION 6: THEME, TARGET & SCHEDULE ─── -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">1.6</span>
                                <span class="ds-tooltip-trigger" title="Theme, Target & Schedule: Project title, SMART measurable goal, and stage-wise completion timeline">Theme, Target &amp; Schedule</span> <span class="text-danger">*</span>
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Set the project theme, the measurable target, and the stage-wise timeline/milestones.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="row g-3 mb-4">
                            <div class="col-md-12"><div class="ds-field"><label class="ds-label ds-tooltip-trigger" title="Improvement Theme: Official project title describing problem & target outcome">Improvement Theme</label><input type="text" class="ds-input" id="s1_tts_theme" placeholder="e.g. Reduction of Defect Rate on Line A from 4.2% to below 1%" required></div></div>
                            <div class="col-md-3"><div class="ds-field"><label class="ds-label ds-tooltip-trigger" title="Current Level: Baseline starting performance measurement">Current Level</label><input type="text" class="ds-input" id="s1_tts_current" placeholder="e.g. 4.2% defect rate" required></div></div>
                            <div class="col-md-3"><div class="ds-field"><label class="ds-label ds-tooltip-trigger" title="Target Level: Desired performance goal level post-improvement">Target Level</label><input type="text" class="ds-input" id="s1_tts_target" placeholder="e.g. Below 1% defect rate" required></div></div>
                            <div class="col-md-3"><div class="ds-field"><label class="ds-label ds-tooltip-trigger" title="Expected Benefit: Qualitative and quantitative improvement outcomes">Expected Benefit</label><input type="text" class="ds-input" id="s1_tts_benefit" placeholder="e.g. Reduce customer complaints by 80%" required></div></div>
                            <div class="col-md-3"><div class="ds-field"><label class="ds-label ds-tooltip-trigger" title="Expected Savings: Projected monetary savings per month or year">Expected Savings</label><input type="text" class="ds-input" id="s1_tts_savings" placeholder="e.g. ₹96,000 per month" required></div></div>
                        </div>
                        <hr class="section-divider">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <label class="ds-label mb-0 ds-tooltip-trigger" title="Stage-wise Timeline / Milestones: Target completion dates for Stages 1 through 8">Stage-wise Timeline / Milestones</label>
                            <button class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[1].addMilestoneRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Row
                            </button>
                        </div>
                        <div id="milestonesContainer">
                            <div class="milestone-row mb-1" style="display:grid;grid-template-columns:1fr 1fr auto;gap:.5rem;"><small class="ds-label ds-tooltip-trigger" title="Stage / Milestone: Name of QC Circle Stage (Stages 1 to 8)">Stage / Milestone</small><small class="ds-label ds-tooltip-trigger" title="Planned Date: Target completion date for the stage">Planned Date</small><span style="width:32px;"></span></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    init(projectData) {
        this.projectData = projectData;
        this.prefillSection1(projectData);
        this.prefillAllSections(projectData.stage1_data || {});
        if (window.lucide) lucide.createIcons();
    },

    prefillSection1(data) {
        if (!data) return;
        const init = (data.stage1_data || {}).init || {};
        
        // 1. Work Area
        const workAreaDefault = (init.work_area && init.work_area.trim()) || 
                                (data.work_area && data.work_area.trim()) || 
                                (data.plant_name ? `${data.plant_name} - ${data.department || 'Shop Floor'}` : (data.department || 'Shop Floor'));
        this.setVal('s1_work_area', workAreaDefault);
        
        // 2. Sponsor
        const sponsorDefault = (init.sponsor && init.sponsor.trim()) || 
                               (data.sponsor && data.sponsor.trim()) || 
                               `${data.department || 'Plant'} Head / Operations Manager`;
        this.setVal('s1_sponsor', sponsorDefault);
        
        // 3. Facilitator: Always prioritize live project governance facilitator
        let facName = '';
        if (data.facilitator_name && data.facilitator_name.trim()) {
            facName = data.facilitator_name;
        } else if (init.facilitator && init.facilitator.trim()) {
            facName = init.facilitator;
        } else if (data.facilitator && typeof data.facilitator === 'object') {
            facName = data.facilitator.full_name || data.facilitator.username || '';
        } else if (typeof data.facilitator === 'string' && data.facilitator.trim()) {
            facName = data.facilitator;
        } else if (data.facilitator_id) {
            const fUser = (window.orgUsers || []).find(u => u.id == data.facilitator_id);
            if (fUser) facName = fUser.full_name || fUser.username;
        }
        if (!facName) facName = 'Assigned Facilitator';
        this.setVal('s1_facilitator', facName);

        // 4. Team Leader: Always prioritize live project governance team leader
        let tlName = '';
        if (data.team_leader_name && data.team_leader_name.trim()) {
            tlName = data.team_leader_name;
        } else if (init.team_leader && init.team_leader.trim()) {
            tlName = init.team_leader;
        } else if (data.team_leader && typeof data.team_leader === 'object') {
            tlName = data.team_leader.full_name || data.team_leader.username || '';
        } else if (typeof data.team_leader === 'string' && data.team_leader.trim()) {
            tlName = data.team_leader;
        } else if (data.team_leader_id) {
            const tlUser = (window.orgUsers || []).find(u => u.id == data.team_leader_id);
            if (tlUser) tlName = tlUser.full_name || tlUser.username;
        }
        if (!tlName && data.creator) {
            tlName = typeof data.creator === 'object' ? (data.creator.full_name || data.creator.username) : data.creator;
        }
        if (!tlName) tlName = 'Team Leader';
        this.setVal('s1_team_leader', tlName);

        // 5. Reviewer: Always prioritize live project governance reviewer
        let revName = '';
        if (data.reviewer_name && data.reviewer_name.trim()) {
            revName = data.reviewer_name;
        } else if (init.reviewer && init.reviewer.trim()) {
            revName = init.reviewer;
        } else if (data.reviewer && typeof data.reviewer === 'object') {
            revName = data.reviewer.full_name || data.reviewer.username || '';
        } else if (typeof data.reviewer === 'string' && data.reviewer.trim()) {
            revName = data.reviewer;
        } else if (data.reviewer_id) {
            const revUser = (window.orgUsers || []).find(u => u.id == data.reviewer_id);
            if (revUser) revName = revUser.full_name || revUser.username;
        }
        if (!revName) revName = 'Quality Reviewer';
        this.setVal('s1_reviewer', revName);

        // 6. Duration: Calculation from start_date/created_at to end_date/deadline
        const start = (init.planned_start_date && init.planned_start_date.trim()) || data.start_date || data.created_at;
        const end = (init.planned_end_date && init.planned_end_date.trim()) || data.end_date || data.deadline;
        let durationStr = (init.duration && init.duration.trim()) || '';
        if (!durationStr && start && end) {
            const sDate = new Date(start);
            const eDate = new Date(end);
            const diffTime = eDate.getTime() - sDate.getTime();
            const days = Math.max(1, Math.round(Math.abs(diffTime) / (1000 * 60 * 60 * 24)));
            const sStr = isNaN(sDate.getTime()) ? String(start).split('T')[0] : sDate.toISOString().split('T')[0];
            const eStr = isNaN(eDate.getTime()) ? String(end).split('T')[0] : eDate.toISOString().split('T')[0];
            durationStr = `${days} days (${sStr} → ${eStr})`;
        }
        if (!durationStr) durationStr = '90 days (Standard 8D Lifecycle)';
        this.setVal('s1_duration', durationStr);
    },

    prefillAllSections(d) {
        if (!d) d = {};
        const team = d.team || {};
        const circleDefault = (team.circle_name && team.circle_name.trim()) || 
                              (this.projectData && this.projectData.title ? `${this.projectData.title} Circle` : `${(this.projectData && this.projectData.department) || 'Quality'} Circle`);
        this.setVal('s1_circle_name', circleDefault);
        
        // Load team members from all available sources (excluding the Team Leader)
        const container = document.getElementById('teamMembersContainer');
        if (container) container.innerHTML = '';

        const membersList = [];
        const seenUserIds = new Set();
        const tlId = (this.projectData && this.projectData.team_leader_id) || null;

        // Source A: Saved team members in workflow data
        (team.team_members || []).forEach(m => {
            if (m && m.user_id && m.user_id != tlId && !seenUserIds.has(m.user_id)) {
                seenUserIds.add(m.user_id);
                membersList.push({
                    user_id: m.user_id,
                    name: m.name || `User #${m.user_id}`,
                    role: m.role || 'Team Member'
                });
            }
        });

        // Source B: projectData.members (direct user objects from API)
        ((this.projectData && this.projectData.members) || []).forEach(m => {
            if (m && m.id && m.id != tlId && !seenUserIds.has(m.id)) {
                seenUserIds.add(m.id);
                membersList.push({
                    user_id: m.id,
                    name: m.full_name || m.username || `User #${m.id}`,
                    role: m.role || 'Team Member'
                });
            }
        });

        // Source C: projectData.member_ids
        ((this.projectData && this.projectData.member_ids) || []).forEach(id => {
            if (id && id != tlId && !seenUserIds.has(id)) {
                seenUserIds.add(id);
                const orgUser = (window.orgUsers || []).find(u => u.id == id);
                membersList.push({
                    user_id: id,
                    name: orgUser ? (orgUser.full_name || orgUser.username) : `User #${id}`,
                    role: orgUser ? ((orgUser.role && orgUser.role.name) ? orgUser.role.name : (typeof orgUser.role === 'string' ? orgUser.role : 'Team Member')) : 'Team Member'
                });
            }
        });

        membersList.forEach(m => this.addTeamMemberRow(m));

        const w = d.background_5w2h || {};
        this.setVal('s1_5w2h_what', w.what || '');
        this.setVal('s1_5w2h_where', w.where || '');
        this.setVal('s1_5w2h_when', w.when || '');
        this.setVal('s1_5w2h_who', w.who || '');
        this.setVal('s1_5w2h_why', w.why || '');
        this.setVal('s1_5w2h_how_discovered', w.how_discovered || '');
        this.setVal('s1_5w2h_how_big', w.how_big || '');
        this.setVal('s1_5w2h_problem_definition', w.problem_definition || '');

        const cp = d.current_performance || {};
        this.setVal('s1_cp_kpi', cp.current_kpi || '');
        this.setVal('s1_cp_defect_rate', cp.defect_rate || '');
        this.setVal('s1_cp_complaints', cp.complaint_count || '');
        this.setVal('s1_cp_cost_impact', cp.cost_impact || '');
        this.setVal('s1_cp_downtime', cp.downtime || '');

        const j = d.justification || {};
        this.setVal('s1_j_financial', j.financial || '');
        this.setVal('s1_j_customer', j.customer || '');
        this.setVal('s1_j_quality', j.quality || '');
        this.setVal('s1_j_safety', j.safety || '');
        this.setVal('s1_j_delivery', j.delivery || '');
        this.setVal('s1_j_regulatory', j.regulatory || '');
        this.setVal('s1_j_why', j.why_work_on_this || '');

        const er = d.emergency_response || {};
        if (er.required === 'yes') {
            const r = document.querySelector('[name=emergencyRequired][value=yes]');
            if(r) r.checked = true;
            this.toggleEmergency(true);
            this.setVal('s1_er_action', er.action || '');
            this.setVal('s1_er_responsible', er.responsible || '');
            this.setVal('s1_er_start_date', er.start_date || '');
            this.setVal('s1_er_completion_date', er.completion_date || '');
            this.setVal('s1_er_status', er.status || 'Planned');
        }

        const tts = d.theme_target_schedule || {};
        this.setVal('s1_tts_theme', tts.improvement_theme || '');
        this.setVal('s1_tts_current', tts.current_level || '');
        this.setVal('s1_tts_target', tts.target_level || '');
        this.setVal('s1_tts_benefit', tts.expected_benefit || '');
        this.setVal('s1_tts_savings', tts.expected_savings || '');

        if (tts.milestones && tts.milestones.length) {
            tts.milestones.forEach(m => this.addMilestoneRow(m));
        } else {
            this.addDefaultMilestones();
        }
    },

    collectData() {
        const getRadio = (name) => (document.querySelector(`[name=${name}]:checked`) || {}).value || 'no';
        const existingInit = (this.projectData && this.projectData.stage1_data && this.projectData.stage1_data.init) ? this.projectData.stage1_data.init : {};
        return {
            init: {
                ...existingInit,
                sponsor: this.getVal('s1_sponsor'),
                work_area: this.getVal('s1_work_area'),
                facilitator: this.getVal('s1_facilitator'),
                team_leader: this.getVal('s1_team_leader'),
                reviewer: this.getVal('s1_reviewer'),
                duration: this.getVal('s1_duration')
            },
            team: {
                circle_name: this.getVal('s1_circle_name'),
                team_members: this.collectTeamMembers()
            },
            background_5w2h: {
                what: this.getVal('s1_5w2h_what'),
                where: this.getVal('s1_5w2h_where'),
                when: this.getVal('s1_5w2h_when'),
                who: this.getVal('s1_5w2h_who'),
                why: this.getVal('s1_5w2h_why'),
                how_discovered: this.getVal('s1_5w2h_how_discovered'),
                how_big: this.getVal('s1_5w2h_how_big'),
                problem_definition: this.getVal('s1_5w2h_problem_definition')
            },
            current_performance: {
                current_kpi: this.getVal('s1_cp_kpi'),
                defect_rate: this.getVal('s1_cp_defect_rate'),
                complaint_count: this.getVal('s1_cp_complaints'),
                cost_impact: this.getVal('s1_cp_cost_impact'),
                downtime: this.getVal('s1_cp_downtime')
            },
            justification: {
                financial: this.getVal('s1_j_financial'),
                customer: this.getVal('s1_j_customer'),
                quality: this.getVal('s1_j_quality'),
                safety: this.getVal('s1_j_safety'),
                delivery: this.getVal('s1_j_delivery'),
                regulatory: this.getVal('s1_j_regulatory'),
                why_work_on_this: this.getVal('s1_j_why')
            },
            emergency_response: {
                required: getRadio('emergencyRequired'),
                action: this.getVal('s1_er_action'),
                responsible: this.getVal('s1_er_responsible'),
                start_date: this.getVal('s1_er_start_date'),
                completion_date: this.getVal('s1_er_completion_date'),
                status: this.getVal('s1_er_status')
            },
            theme_target_schedule: {
                improvement_theme: this.getVal('s1_tts_theme'),
                current_level: this.getVal('s1_tts_current'),
                target_level: this.getVal('s1_tts_target'),
                expected_benefit: this.getVal('s1_tts_benefit'),
                expected_savings: this.getVal('s1_tts_savings'),
                milestones: this.collectMilestones()
            }
        };
    },

    toggleEmergency(show) {
        document.getElementById('emergencyFields').classList.toggle('d-none', !show);
    },

    addTeamMemberRow(data = {}) {
        const container = document.getElementById('teamMembersContainer');
        const row = document.createElement('div');
        row.className = 'team-member-row dyn-row mb-2';
        row.style.cssText = 'display:grid;grid-template-columns:2fr 1fr;gap:.5rem;align-items:center;';
        row.innerHTML = `
            <input type="text" class="ds-input tm-user-name" readonly 
                style="font-weight:500;" 
                value="${data.name || ''}" data-user-id="${data.user_id || ''}">
            <input type="text" class="ds-input tm-role" placeholder="Role" readonly
                style="font-size:.8rem;"
                value="${data.role || ''}">`;
        container.appendChild(row);
    },

    collectTeamMembers() {
        return [...document.querySelectorAll('#teamMembersContainer > div')].map(row => {
            const nameInput = row.querySelector('.tm-user-name');
            const userId = nameInput ? nameInput.getAttribute('data-user-id') : null;
            const name = nameInput ? nameInput.value : '';
            return {
                user_id: userId ? parseInt(userId) : null,
                name: name,
                role: row.querySelector('.tm-role')?.value || ''
            };
        }).filter(m => m.user_id);
    },

    addMilestoneRow(data = {}) {
        const container = document.getElementById('milestonesContainer');
        const row = document.createElement('div');
        row.className = 'milestone-row mb-2';
        row.style.cssText = 'display:grid;grid-template-columns:1fr 1fr auto;gap:.5rem;align-items:end;';
        row.innerHTML = `
            <input type="text" class="ds-input ms-stage" placeholder="e.g. Observation" value="${data.stage || ''}">
            <input type="date" class="ds-input ms-date" value="${data.planned_date || ''}">
            <button class="ds-btn ds-btn-ghost" style="padding:.25rem .5rem;color:var(--ds-danger)" onclick="this.closest('.milestone-row').remove()">
                <i data-lucide="trash-2" style="width:14px;height:14px;"></i>
            </button>`;
        container.appendChild(row);
        if (window.lucide) lucide.createIcons();
    },

    addDefaultMilestones() {
        const container = document.getElementById('milestonesContainer');
        if (!container || container.children.length > 1) return;
        const stages = ['Observation','Analysis','Countermeasures','Validation','Standardization','Closure'];
        stages.forEach(s => this.addMilestoneRow({ stage: s }));
    },

    collectMilestones() {
        return [...document.querySelectorAll('.milestone-row:not(:first-child)')].map(row => ({
            stage: row.querySelector('.ms-stage').value,
            planned_date: row.querySelector('.ms-date').value,
            status: (row.querySelector('.ms-status') || {}).value || 'Planned'
        })).filter(m => m.stage);
    },

    getVal(id) { return (document.getElementById(id) || {}).value || ''; },
    setVal(id, val) { const el = document.getElementById(id); if (el) el.value = (val !== undefined && val !== null) ? val : ''; },

    validate() {
        const errors = [];
        const invalidFields = [];

        if (!this.getVal('s1_circle_name')) {
            errors.push("QC Circle Name is required.");
            invalidFields.push('s1_circle_name');
        }

        if (!this.getVal('s1_sponsor')) {
            errors.push("Sponsor is required.");
            invalidFields.push('s1_sponsor');
        }

        const teamMembers = this.collectTeamMembers();
        if (!teamMembers || teamMembers.length === 0) {
            errors.push("At least one team member must be assigned.");
            invalidFields.push('teamMembersContainer');
        }

        const fields_5w2h = {
            s1_5w2h_what: "5W2H: What Happened",
            s1_5w2h_where: "5W2H: Where Did It Happen",
            s1_5w2h_when: "5W2H: When Did It Happen",
            s1_5w2h_who: "5W2H: Who Is Complaining",
            s1_5w2h_why: "5W2H: Why Is Customer Complaining",
            s1_5w2h_how_discovered: "5W2H: How Discovered",
            s1_5w2h_how_big: "5W2H: How Big",
            s1_5w2h_problem_definition: "5W2H: Problem Definition"
        };
        for (const [id, label] of Object.entries(fields_5w2h)) {
            if (!this.getVal(id)) {
                errors.push(`${label} is required.`);
                invalidFields.push(id);
            }
        }

        if (!this.getVal('s1_cp_kpi')) {
            errors.push("Current Performance KPI is required.");
            invalidFields.push('s1_cp_kpi');
        }

        if (!this.getVal('s1_j_why')) {
            errors.push("Organization Work Justification is required.");
            invalidFields.push('s1_j_why');
        }

        if (!this.getVal('s1_tts_theme')) {
            errors.push("Improvement Theme is required.");
            invalidFields.push('s1_tts_theme');
        }

        if (!this.getVal('s1_tts_current')) {
            errors.push("Current Level is required.");
            invalidFields.push('s1_tts_current');
        }

        if (!this.getVal('s1_tts_target')) {
            errors.push("Target Level is required.");
            invalidFields.push('s1_tts_target');
        }

        const milestones = this.collectMilestones();
        if (!milestones || milestones.length === 0) {
            errors.push("At least one milestone timeline must be defined.");
            invalidFields.push('milestonesContainer');
        }

        return {
            valid: errors.length === 0,
            errors,
            invalidFields
        };
    }
};

window.StageModules = window.StageModules || {};
window.StageModules[1] = Stage1;
