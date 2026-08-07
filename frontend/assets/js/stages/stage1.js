const Stage1 = {
    renderHTML() {
        return `
            <!-- STAGE 1 FORM -->
            <div id="stage1Form">
                <!-- ─── SECTION 1: PROJECT TEAM ─── -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                            <span class="ds-icon-circle bg-primary-soft text-primary" style="width:28px;height:28px;font-size:.7rem;">1</span>
                            Project Team
                        </h5>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="row g-3">
                            <div class="col-md-4">
                                <div class="ds-field">
                                    <label class="ds-label">QC Circle Name</label>
                                    <input type="text" class="ds-input" id="s1_circle_name" placeholder="e.g. Quality Warriors" required>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="ds-field">
                                    <label class="ds-label">Work Area</label>
                                    <input type="text" class="ds-input" id="s1_work_area" readonly>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="ds-field">
                                    <label class="ds-label">Sponsor</label>
                                    <input type="text" class="ds-input" id="s1_sponsor" placeholder="e.g. Plant Manager" required>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="ds-field">
                                    <label class="ds-label">Facilitator</label>
                                    <input type="text" class="ds-input" id="s1_facilitator" readonly>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="ds-field">
                                    <label class="ds-label">Team Leader</label>
                                    <input type="text" class="ds-input" id="s1_team_leader" readonly>
                                </div>
                            </div>
                            <div class="col-md-4">
                                <div class="ds-field">
                                    <label class="ds-label">Duration</label>
                                    <input type="text" class="ds-input" id="s1_duration" readonly placeholder="Calculated from dates">
                                </div>
                            </div>
                        </div>

                        <hr class="section-divider">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <label class="ds-label mb-0">Team Members <span class="text-danger">*</span></label>
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
                        <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                            <span class="ds-icon-circle bg-primary-soft text-primary" style="width:28px;height:28px;font-size:.7rem;">2</span>
                            Problem Background (5W2H)
                        </h5>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="row g-3">
                            <div class="col-md-6">
                                <div class="ds-field">
                                    <label class="ds-label">What Happened? *</label>
                                    <textarea class="ds-input ds-textarea" id="s1_5w2h_what" rows="2" placeholder="e.g. Defect rate on Line A exceeds 4% causing rework and customer returns" required></textarea>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="ds-field">
                                    <label class="ds-label">Where Did It Happen? *</label>
                                    <textarea class="ds-input ds-textarea" id="s1_5w2h_where" rows="2" placeholder="e.g. Assembly Line A, Weld Shop, Building 3" required></textarea>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="ds-field">
                                    <label class="ds-label">When Did It Happen? *</label>
                                    <textarea class="ds-input ds-textarea" id="s1_5w2h_when" rows="2" placeholder="e.g. Since January 2025; recurring every Monday morning shift" required></textarea>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="ds-field">
                                    <label class="ds-label">Who Is Complaining? *</label>
                                    <textarea class="ds-input ds-textarea" id="s1_5w2h_who" rows="2" placeholder="e.g. Key customer ABC Ltd. raised 23 complaints in Q1 2025" required></textarea>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="ds-field">
                                    <label class="ds-label">Why Is The Customer Complaining? *</label>
                                    <textarea class="ds-input ds-textarea" id="s1_5w2h_why" rows="2" placeholder="e.g. Products delivered with surface scratches, failing their inspection criteria" required></textarea>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="ds-field">
                                    <label class="ds-label">How Was It Discovered? *</label>
                                    <textarea class="ds-input ds-textarea" id="s1_5w2h_how_discovered" rows="2" placeholder="e.g. Detected during final QC inspection and flagged in customer returns" required></textarea>
                                </div>
                            </div>
                            <div class="col-12">
                                <div class="ds-field">
                                    <label class="ds-label">How Big Is The Problem? *</label>
                                    <textarea class="ds-input ds-textarea" id="s1_5w2h_how_big" rows="2" placeholder="e.g. 4.2% defect rate, 23 complaints in Q1, costing ₹1,20,000 per month" required></textarea>
                                </div>
                            </div>
                            <div class="col-12">
                                <div class="ds-field">
                                    <label class="ds-label">Problem Definition *</label>
                                    <textarea class="ds-input ds-textarea" id="s1_5w2h_problem_definition" rows="3" placeholder="e.g. Reject rate of crimping defects has increased to 4.2% since Jan 2025, causing 23 customer complaints in Q1 and ₹1.2L monthly rework loss." required></textarea>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- ─── SECTION 3: CURRENT PERFORMANCE ─── -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                            <span class="ds-icon-circle bg-primary-soft text-primary" style="width:28px;height:28px;font-size:.7rem;">3</span>
                            Current Performance
                        </h5>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="row g-3">
                            <div class="col-md-4">
                                <div class="ds-field"><label class="ds-label">Current KPI *</label><input type="text" class="ds-input" id="s1_cp_kpi" placeholder="e.g. 4.2% defect rate" required></div>
                            </div>
                            <div class="col-md-4">
                                <div class="ds-field"><label class="ds-label">Current Defect Rate</label><input type="text" class="ds-input" id="s1_cp_defect_rate" placeholder="e.g. 4.2%" required></div>
                            </div>
                            <div class="col-md-4">
                                <div class="ds-field"><label class="ds-label">Current Complaint Count</label><input type="number" class="ds-input" id="s1_cp_complaints" placeholder="e.g. 23 complaints in Q1" required></div>
                            </div>
                            <div class="col-md-4">
                                <div class="ds-field"><label class="ds-label">Current Cost Impact</label><input type="text" class="ds-input" id="s1_cp_cost_impact" placeholder="e.g. ₹1,20,000 per month" required></div>
                            </div>
                            <div class="col-md-4">
                                <div class="ds-field"><label class="ds-label">Current Downtime</label><input type="text" class="ds-input" id="s1_cp_downtime" placeholder="e.g. 45 minutes per shift" required></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- ─── SECTION 4: JUSTIFICATION ─── -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                            <span class="ds-icon-circle bg-primary-soft text-primary" style="width:28px;height:28px;font-size:.7rem;">4</span>
                            Justification
                        </h5>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="row g-3">
                            <div class="col-md-6"><div class="ds-field"><label class="ds-label">Financial Impact</label><textarea class="ds-input ds-textarea" id="s1_j_financial" rows="2" placeholder="e.g. Rework and scrap costs ₹1,20,000 per month, impacting margins by 8%" required></textarea></div></div>
                            <div class="col-md-6"><div class="ds-field"><label class="ds-label">Customer Impact</label><textarea class="ds-input ds-textarea" id="s1_j_customer" rows="2" placeholder="e.g. 23 customer complaints in Q1; risk of losing key account ABC Ltd." required></textarea></div></div>
                            <div class="col-md-6"><div class="ds-field"><label class="ds-label">Quality Impact</label><textarea class="ds-input ds-textarea" id="s1_j_quality" rows="2" placeholder="e.g. Defect rate of 4.2% exceeds the 1% acceptable quality limit" required></textarea></div></div>
                            <div class="col-md-6"><div class="ds-field"><label class="ds-label">Safety Impact</label><textarea class="ds-input ds-textarea" id="s1_j_safety" rows="2" placeholder="e.g. Faulty components pose risk of injury during handling; 2 near-miss incidents recorded" required></textarea></div></div>
                            <div class="col-md-6"><div class="ds-field"><label class="ds-label">Delivery Impact</label><textarea class="ds-input ds-textarea" id="s1_j_delivery" rows="2" placeholder="e.g. Rework delays dispatch by 2 days, causing late deliveries on 15% of orders" required></textarea></div></div>
                            <div class="col-md-6"><div class="ds-field"><label class="ds-label">Regulatory Impact</label><textarea class="ds-input ds-textarea" id="s1_j_regulatory" rows="2" placeholder="e.g. Non-compliance with ISO 9001 Clause 8.7; risk of audit non-conformance" required></textarea></div></div>
                            <div class="col-12"><div class="ds-field"><label class="ds-label">Why Should The Organization Work On This Problem? *</label><textarea class="ds-input ds-textarea" id="s1_j_why" rows="3" placeholder="e.g. Addressing this defect will save ₹1,20,000/month, restore customer trust, and ensure ISO compliance" required></textarea></div></div>
                        </div>
                    </div>
                </div>

                <!-- ─── SECTION 5: EMERGENCY RESPONSE ─── -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom"><h5 class="mb-0 fw-bold d-flex align-items-center gap-2"><span class="ds-icon-circle bg-primary-soft text-primary" style="width:28px;height:28px;font-size:.7rem;">5</span> Emergency Response</h5></div>
                    <div class="ds-card-body p-4">
                        <div class="ds-field mb-3">
                            <label class="ds-label">Is Emergency Response Required? *</label>
                            <div class="h-stack gap-3">
                                <label class="h-stack gap-2 cursor-pointer"><input type="radio" name="emergencyRequired" value="yes" onchange="StageModules[1].toggleEmergency(true)"> Yes</label>
                                <label class="h-stack gap-2 cursor-pointer"><input type="radio" name="emergencyRequired" value="no" checked onchange="StageModules[1].toggleEmergency(false)"> No</label>
                            </div>
                        </div>
                        <div id="emergencyFields" class="d-none">
                            <div class="row g-3">
                                <div class="col-md-12"><div class="ds-field"><label class="ds-label">Containment Action</label><textarea class="ds-input ds-textarea" id="s1_er_action" rows="2" placeholder="e.g. Segregate all WIP stock; 100% visual inspection before dispatch until further notice" required></textarea></div></div>
                                <div class="col-md-4"><div class="ds-field"><label class="ds-label">Responsible Person</label><input type="text" class="ds-input" id="s1_er_responsible" placeholder="e.g. Rajesh Kumar (QC Engineer)" required></div></div>
                                <div class="col-md-3"><div class="ds-field"><label class="ds-label">Start Date</label><input type="date" class="ds-input" id="s1_er_start_date" required></div></div>
                                <div class="col-md-3"><div class="ds-field"><label class="ds-label">Completion Date</label><input type="date" class="ds-input" id="s1_er_completion_date" required></div></div>
                                <div class="col-md-2"><div class="ds-field"><label class="ds-label">Status</label><select class="ds-input ds-select" id="s1_er_status" required><option>Planned</option><option>In Progress</option><option>Completed</option></select></div></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- ─── SECTION 6: THEME, TARGET & SCHEDULE ─── -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom"><h5 class="mb-0 fw-bold d-flex align-items-center gap-2"><span class="ds-icon-circle bg-primary-soft text-primary" style="width:28px;height:28px;font-size:.7rem;">6</span> Theme, Target & Schedule</h5></div>
                    <div class="ds-card-body p-4">
                        <div class="row g-3 mb-4">
                            <div class="col-md-12"><div class="ds-field"><label class="ds-label">Improvement Theme *</label><input type="text" class="ds-input" id="s1_tts_theme" placeholder="e.g. Reduction of Defect Rate on Line A from 4.2% to below 1%" required></div></div>
                            <div class="col-md-3"><div class="ds-field"><label class="ds-label">Current Level *</label><input type="text" class="ds-input" id="s1_tts_current" placeholder="e.g. 4.2% defect rate" required></div></div>
                            <div class="col-md-3"><div class="ds-field"><label class="ds-label">Target Level *</label><input type="text" class="ds-input" id="s1_tts_target" placeholder="e.g. Below 1% defect rate" required></div></div>
                            <div class="col-md-3"><div class="ds-field"><label class="ds-label">Expected Benefit</label><input type="text" class="ds-input" id="s1_tts_benefit" placeholder="e.g. Reduce customer complaints by 80%" required></div></div>
                            <div class="col-md-3"><div class="ds-field"><label class="ds-label">Expected Savings</label><input type="text" class="ds-input" id="s1_tts_savings" placeholder="e.g. ₹96,000 per month" required></div></div>
                        </div>
                        <hr class="section-divider">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <label class="ds-label mb-0">Stage-wise Timeline / Milestones *</label>
                            <button class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[1].addMilestoneRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Row
                            </button>
                        </div>
                        <div id="milestonesContainer">
                            <div class="milestone-row mb-1"><small class="ds-label">Stage / Milestone</small><small class="ds-label">Planned Date</small><span></span></div>
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
        const init = (data.stage1_data || {}).init || {};
        this.setVal('s1_work_area', init.work_area || data.description || '');
        this.setVal('s1_sponsor', init.sponsor || '');
        this.setVal('s1_facilitator', init.facilitator || data.facilitator_name || '');
        this.setVal('s1_team_leader', init.team_leader || data.team_leader_name || '');
        const start = init.planned_start_date || data.start_date;
        const end = init.planned_end_date || data.end_date;
        if (start && end) {
            const days = Math.round((new Date(end) - new Date(start)) / (1000*60*60*24));
            this.setVal('s1_duration', `${days} days (${start} → ${end})`);
        }
    },

    prefillAllSections(d) {
        const team = d.team || {};
        this.setVal('s1_circle_name', team.circle_name || '');
        
        // Load team members from the project's member_ids (excluding the Team Leader)
        const teamMembersIds = (this.projectData.member_ids || []).filter(id => id != this.projectData.team_leader_id);
        
        const container = document.getElementById('teamMembersContainer');
        if (container) container.innerHTML = '';

        teamMembersIds.forEach(id => {
            const orgUser = (window.orgUsers || []).find(u => u.id == id);
            const savedMember = (team.team_members || []).find(m => m.user_id == id);
            
            const memberData = {
                user_id: id,
                name: orgUser ? (orgUser.full_name || orgUser.username) : (savedMember ? savedMember.name : `User #${id}`),
                role: orgUser ? orgUser.role : (savedMember ? savedMember.role : 'Team Member'),
                designation: savedMember ? savedMember.designation : ''
            };
            this.addTeamMemberRow(memberData);
        });

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
        row.className = 'mb-2';
        row.style.cssText = 'display:grid;grid-template-columns:2fr 1fr;gap:.5rem;align-items:center;';
        row.innerHTML = `
            <input type="text" class="ds-input tm-user-name" readonly 
                style="background:var(--ds-surface-raised);color:var(--ds-text-main);font-weight:500;" 
                value="${data.name || ''}" data-user-id="${data.user_id || ''}">
            <input type="text" class="ds-input tm-role" placeholder="Role" readonly
                style="background:var(--ds-surface-raised);color:var(--ds-text-secondary);font-size:.8rem;"
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
