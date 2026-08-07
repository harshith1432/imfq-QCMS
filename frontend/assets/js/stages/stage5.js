const Stage5 = {
    projectData: null,

    renderHTML() {
        return `
            <!-- STAGE 5 FORM -->
            <div id="stage5Form">
                
                <!-- Verified Root Cause Banner -->
                <div class="p-3 mb-4 rounded border d-flex align-items-center justify-content-between shadow-sm bg-danger-soft text-danger" id="s5VerifiedRootCauseBanner" style="border-color: rgba(239, 68, 68, 0.25) !important;">
                    <div class="d-flex align-items-center gap-2">
                        <i data-lucide="shield-alert" style="width:20px;height:20px;color:rgb(239, 68, 68);"></i>
                        <div>
                            <div class="fw-bold text-xs" style="text-transform: uppercase; letter-spacing: 0.05em; color:rgb(185, 28, 28);">Verified Root Cause (from Stage 4)</div>
                            <div class="fw-bold fs-6 mt-0.5" id="s5VerifiedRootCauseDisplay">Loading verified root cause...</div>
                        </div>
                    </div>
                    <span class="badge bg-danger" style="font-size: 0.72rem;">Stage 4 Verified</span>
                </div>

                <!-- Section 1 - Root Cause Mapping -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                            <span class="ds-icon-circle bg-primary-soft text-primary" style="width:28px;height:28px;font-size:.7rem;">1</span>
                            Root Cause Mapping
                        </h5>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary">Section 1 - Root Cause Mapping</h6>
                            <button class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[5].addMappingRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Mapping
                            </button>
                        </div>
                        <div id="s5_mappingContainer" class="mb-0">
                            <div class="row text-muted small fw-bold mb-2 px-2">
                                <div class="col-5">Root Cause</div>
                                <div class="col-6">Proposed Solution(s)</div>
                                <div class="col-1"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section 2 - Solution Brainstorming -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                            <span class="ds-icon-circle bg-primary-soft text-primary" style="width:28px;height:28px;font-size:.7rem;">2</span>
                            Solution Brainstorming
                        </h5>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary">Section 2 - Solution Brainstorming</h6>
                            <button type="button" class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[5].addBrainstormingRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Idea
                            </button>
                        </div>
                        <div id="s5_bsContainer" class="mb-0">
                            <div class="row text-muted small fw-bold mb-2 px-2">
                                <div class="col-5">Idea</div>
                                <div class="col-3">Contributor</div>
                                <div class="col-3">Feasibility</div>
                                <div class="col-1"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section 3 - Solution Evaluation Matrix -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                            <span class="ds-icon-circle bg-primary-soft text-primary" style="width:28px;height:28px;font-size:.7rem;">3</span>
                            Solution Evaluation Matrix
                        </h5>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary">Section 3 - Solution Evaluation Matrix</h6>
                            <button class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[5].addEvalRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Solution
                            </button>
                        </div>
                        <div class="table-responsive">
                            <div id="s5_evalContainer" class="mb-0" style="min-width: 650px;">
                                <div class="row text-muted small fw-bold mb-2 px-2 align-items-center">
                                    <div class="col-3">Solution</div>
                                    <div class="col text-center">Effectiveness (1-10)</div>
                                    <div class="col text-center">Cost (1-10)</div>
                                    <div class="col text-center">Feasibility (1-10)</div>
                                    <div class="col text-center">Time (1-10)</div>
                                    <div class="col text-center">Total</div>
                                    <div class="col-1"></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section 4 - Cost Benefit Analysis -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                            <span class="ds-icon-circle bg-primary-soft text-primary" style="width:28px;height:28px;font-size:.7rem;">4</span>
                            Cost Benefit Analysis
                        </h5>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary">Section 4 - Cost Benefit Analysis</h6>
                            <button type="button" class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[5].addCBARow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Analysis
                            </button>
                        </div>
                        <div class="table-responsive">
                            <div id="s5_cbaContainer" class="mb-0" style="min-width: 650px;">
                                <div class="row text-muted small fw-bold mb-2 px-2">
                                    <div class="col-4">Solution</div>
                                    <div class="col-2">Estimated Cost</div>
                                    <div class="col-3">Expected Benefit/Savings</div>
                                    <div class="col-2">ROI</div>
                                    <div class="col-1"></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section 5 - Side Effect Analysis -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                            <span class="ds-icon-circle bg-primary-soft text-primary" style="width:28px;height:28px;font-size:.7rem;">5</span>
                            Side Effect Analysis
                        </h5>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary">Section 5 - Side Effect Analysis</h6>
                            <button type="button" class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[5].addSideEffectRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Risk
                            </button>
                        </div>
                        <div class="table-responsive">
                            <div id="s5_seContainer" class="mb-0" style="min-width: 650px;">
                                <div class="row text-muted small fw-bold mb-2 px-2">
                                    <div class="col-3">Solution</div>
                                    <div class="col-4">Potential Risk</div>
                                    <div class="col-4">Mitigation Plan</div>
                                    <div class="col-1"></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section 6 - Pilot Solution Verification -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                            <span class="ds-icon-circle bg-primary-soft text-primary" style="width:28px;height:28px;font-size:.7rem;">6</span>
                            Pilot Solution Verification
                        </h5>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary">Section 6 - Pilot Solution Verification</h6>
                            <button class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[5].addPilotRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Pilot Run
                            </button>
                        </div>
                        <div id="s5_pilotContainer" class="mb-0">
                            <div class="row text-muted small fw-bold mb-2 px-2">
                                <div class="col-3">Solution</div>
                                <div class="col-2">Location</div>
                                <div class="col-2">Duration</div>
                                <div class="col-2">Result</div>
                                <div class="col-2">Decision</div>
                                <div class="col-1"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section 7 - Action Plan (3W1H) -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                            <span class="ds-icon-circle bg-primary-soft text-primary" style="width:28px;height:28px;font-size:.7rem;">7</span>
                            Action Plan (3W1H)
                        </h5>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary">Section 7 - Action Plan (3W1H)</h6>
                            <button class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[5].addActionRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Action Item
                            </button>
                        </div>
                        <div id="s5_actionContainer" class="mb-0">
                            <div class="row text-muted small fw-bold mb-2 px-2">
                                <div class="col-4">What (Action)</div>
                                <div class="col-2">Who (Owner)</div>
                                <div class="col-2">When (Due Date)</div>
                                <div class="col-3">How (Implementation Steps)</div>
                                <div class="col-1"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section 8 - Resource Planning -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                            <span class="ds-icon-circle bg-primary-soft text-primary" style="width:28px;height:28px;font-size:.7rem;">8</span>
                            Resource Planning
                        </h5>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary">Section 8 - Resource Planning</h6>
                            <button class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[5].addResourceRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Resource
                            </button>
                        </div>
                        <div id="s5_resourceContainer" class="mb-0">
                            <div class="row text-muted small fw-bold mb-2 px-2">
                                <div class="col-4">Resource Required</div>
                                <div class="col-2">Budget Allocation</div>
                                <div class="col-3">Source</div>
                                <div class="col-2">Status</div>
                                <div class="col-1"></div>
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
        const d = wf.find(w => w.stage_id === 5)?.data || {};

        // Display Verified Root Cause(s) at the top of the page
        const rcs = this.getStage4RootCauses();
        const display = rcs.length ? rcs.join(' • ') : 'No verified root cause found from Stage 4. Please complete Stage 4 Why-Why Analysis first.';
        
        const displayEl = document.getElementById('s5VerifiedRootCauseDisplay');
        if (displayEl) {
            displayEl.innerText = display;
        }

        // Fill containers
        const containers = ['mapping', 'bs', 'eval', 'cba', 'se', 'pilot', 'action', 'resource'];
        containers.forEach(key => {
            const arr = d[this.getMap(key)] || [];
            const containerEl = document.getElementById(`s5_${key}Container`);
            if (containerEl) {
                // Clear dyn-rows except headers
                const firstRow = containerEl.querySelector('.row');
                containerEl.innerHTML = '';
                if (firstRow) containerEl.appendChild(firstRow);
            }

            if (arr.length) {
                arr.forEach(r => this[`add${this.capitalize(key)}Row`](r));
            } else {
                this[`add${this.capitalize(key)}Row`]();
            }
        });

        this.updateSolutionDropdowns();

        const gate = d.approval_gate || {};
        this.setVal('s5_gate_verified_by', gate.verified_by);
        this.setVal('s5_gate_date', gate.date);
        this.setVal('s5_gate_status', gate.status);
        this.setVal('s5_gate_comments', gate.comments);

        if (window.lucide) lucide.createIcons();
    },

    getStage4RootCauses() {
        const wf = this.projectData?.workflows || [];
        const s4 = wf.find(w => w.stage_id === 4)?.data || {};
        const whyList = s4.why_why_analysis || [];
        let rcs = [];
        if (whyList.length) {
            rcs = whyList.map(item => item.root_cause || item.why5 || '').filter(Boolean);
        }
        if (!rcs.length && s4.root_cause_register) {
            rcs = s4.root_cause_register.map(x => x.root_cause || x.cause || '').filter(Boolean);
        }
        return [...new Set(rcs)];
    },

    getVerifiedRootCause() {
        const rcs = this.getStage4RootCauses();
        return rcs.length ? rcs[0] : '';
    },

    collectData() {
        return {
            root_cause_mapping: this.collectRows('s5_mappingContainer', ['.r-root', '.r-sol'], ['root_cause', 'proposed_solution']),
            solution_brainstorming: this.collectRows('s5_bsContainer', ['.r-idea', '.r-cont', '.r-feas'], ['idea', 'contributor', 'feasibility']),
            solution_evaluation: this.collectRows('s5_evalContainer', ['.r-sol', '.r-eff', '.r-cst', '.r-fea', '.r-tim', '.r-tot'], ['solution', 'effectiveness', 'cost', 'feasibility', 'time', 'total_score']),
            cost_benefit_analysis: this.collectRows('s5_cbaContainer', ['.r-sol', '.r-cost', '.r-ben', '.r-roi'], ['solution', 'estimated_cost', 'expected_benefit', 'roi']),
            side_effect_analysis: this.collectRows('s5_seContainer', ['.r-sol', '.r-risk', '.r-plan'], ['solution', 'potential_risk', 'mitigation_plan']),
            pilot_solution_verification: this.collectRows('s5_pilotContainer', ['.r-sol', '.r-loc', '.r-dur', '.r-res', '.r-dec'], ['solution', 'location', 'duration', 'result', 'decision']),
            action_plan_3w1h: this.collectRows('s5_actionContainer', ['.r-act', '.r-own', '.r-due', '.r-how'], ['what', 'who', 'when', 'how']),
            resource_planning: this.collectRows('s5_resourceContainer', ['.r-res', '.r-bud', '.r-src', '.r-stat'], ['resource', 'budget', 'source', 'status']),
            approval_gate: {
                verified_by: this.getVal('s5_gate_verified_by'),
                date: this.getVal('s5_gate_date'),
                status: this.getVal('s5_gate_status'),
                comments: this.getVal('s5_gate_comments')
            }
        };
    },

    getMap(k) {
        return {
            'mapping': 'root_cause_mapping', 'bs': 'solution_brainstorming', 'eval': 'solution_evaluation',
            'cba': 'cost_benefit_analysis', 'se': 'side_effect_analysis', 'pilot': 'pilot_solution_verification',
            'action': 'action_plan_3w1h', 'resource': 'resource_planning'
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

    getProposedSolutions() {
        const container = document.getElementById('s5_mappingContainer');
        let sols = [];
        if (container) {
            sols = [...container.querySelectorAll('.r-sol')].map(inp => (inp.value || inp.dataset.savedVal || inp.getAttribute('data-saved-val') || '').trim()).filter(Boolean);
        }
        return [...new Set(sols)];
    },

    buildSolutionOptions(selectedVal = '') {
        const list = this.getProposedSolutions();
        let opts = '';
        let hasSelected = false;

        if (list.length) {
            opts += list.map(s => {
                const isSel = (s === selectedVal);
                if (isSel) hasSelected = true;
                return `<option value="${s.replace(/"/g, '&quot;')}" ${isSel ? 'selected' : ''}>${s}</option>`;
            }).join('');
        }

        if (selectedVal && !hasSelected) {
            opts = `<option value="${selectedVal.replace(/"/g, '&quot;')}" selected>${selectedVal}</option>` + opts;
            hasSelected = true;
        }

        if (!list.length && !hasSelected) {
            opts = `<option value="" disabled selected>No proposed solutions defined in Section 1</option>` + opts;
        } else if (!hasSelected) {
            opts = `<option value="" disabled selected>Select proposed solution...</option>` + opts;
        } else {
            opts = `<option value="" disabled>Select proposed solution...</option>` + opts;
        }

        return opts;
    },

    updateSolutionDropdowns() {
        const dropdownConfigs = [
            { container: 's5_bsContainer', class: 'r-idea' },
            { container: 's5_evalContainer', class: 'r-sol' },
            { container: 's5_cbaContainer', class: 'r-sol' },
            { container: 's5_seContainer', class: 'r-sol' },
            { container: 's5_pilotContainer', class: 'r-sol' }
        ];

        dropdownConfigs.forEach(cfg => {
            const container = document.getElementById(cfg.container);
            if (container) {
                container.querySelectorAll(`.${cfg.class}`).forEach(selectEl => {
                    if (selectEl.tagName === 'SELECT') {
                        const targetVal = selectEl.dataset.savedVal || selectEl.value || selectEl.getAttribute('data-saved-val') || '';
                        selectEl.innerHTML = this.buildSolutionOptions(targetVal);
                        if (targetVal) {
                            selectEl.value = targetVal;
                            selectEl.dataset.savedVal = targetVal;
                        }
                        if (!selectEl.hasAttribute('data-has-listener')) {
                            selectEl.setAttribute('data-has-listener', 'true');
                            selectEl.addEventListener('change', function() {
                                this.dataset.savedVal = this.value;
                            });
                        }
                    }
                });
            }
        });
    },

    addRowTemplate(containerId, data, html, isMapping = false) {
        const c = document.getElementById(containerId);
        const r = document.createElement('div');
        r.className = 'row g-2 mb-2 align-items-center dyn-row';
        r.style.minWidth = '650px';
        const deleteClick = isMapping 
            ? "this.closest('.dyn-row').remove(); StageModules[5].updateSolutionDropdowns();" 
            : "this.closest('.dyn-row').remove();";
        r.innerHTML = html + `<div class="col-1"><button type="button" class="ds-btn ds-btn-ghost text-danger p-1" onclick="${deleteClick}"><i data-lucide="trash-2" style="width:14px;height:14px;"></i></button></div>`;
        c.appendChild(r);
        if (window.lucide) lucide.createIcons();
    },

    buildRootCauseOptions(selectedVal = '') {
        const list = this.getStage4RootCauses();
        let opts = list.map(rc => `<option value="${rc.replace(/"/g, '&quot;')}" ${rc === selectedVal ? 'selected' : ''}>${rc}</option>`).join('');
        if (selectedVal && !list.includes(selectedVal)) {
            opts = `<option value="${selectedVal.replace(/"/g, '&quot;')}" selected>${selectedVal}</option>` + opts;
        }
        if (!opts) {
            opts = `<option value="" disabled selected>No verified root causes found in Stage 4</option>`;
        } else if (!selectedVal) {
            opts = `<option value="" disabled selected>Select root cause...</option>` + opts;
        }
        return opts;
    },

    addMappingRow(d = {}) {
        const selectedRC = d.root_cause || '';
        const rcOpts = this.buildRootCauseOptions(selectedRC);
        this.addRowTemplate('s5_mappingContainer', d, `
            <div class="col-5">
                <select class="ds-input ds-select r-root" required>
                    ${rcOpts}
                </select>
            </div>
            <div class="col-6"><input type="text" class="ds-input r-sol" placeholder="e.g. Replace seal and add weekly PM check" value="${d.proposed_solution || ''}" oninput="StageModules[5].updateSolutionDropdowns()" required></div>`, true);
        this.updateSolutionDropdowns();
    },
    addBsRow(d = {}) {
        const val = d.idea || '';
        const opts = this.buildSolutionOptions(val);
        this.addRowTemplate('s5_bsContainer', d, `
            <div class="col-5">
                <select class="ds-input ds-select r-idea" data-saved-val="${val.replace(/"/g, '&quot;')}" required>
                    ${opts}
                </select>
            </div>
            <div class="col-3"><input type="text" class="ds-input r-cont" placeholder="e.g. Ravi Kumar" value="${d.contributor || ''}" required></div>
            <div class="col-3"><input type="text" class="ds-input r-feas" placeholder="e.g. High - standard mold exists" value="${d.feasibility || ''}" required></div>`);
    },
    addBrainstormingRow(d = {}) { this.addBsRow(d); },
    addEvalRow(d = {}) {
        const val = d.solution || '';
        const opts = this.buildSolutionOptions(val);
        const calc = "const p=this.closest('.dyn-row'); p.querySelector('.r-tot').value = (parseInt(p.querySelector('.r-eff').value)||0)+(parseInt(p.querySelector('.r-cst').value)||0)+(parseInt(p.querySelector('.r-fea').value)||0)+(parseInt(p.querySelector('.r-tim').value)||0);";
        this.addRowTemplate('s5_evalContainer', d, `
            <div class="col-3">
                <select class="ds-input ds-select r-sol" data-saved-val="${val.replace(/"/g, '&quot;')}" required>
                    ${opts}
                </select>
            </div>
            <div class="col"><input type="number" class="ds-input r-eff text-center" placeholder="1-10" min="1" max="10" value="${d.effectiveness || ''}" onchange="${calc}" oninput="${calc}" required></div>
            <div class="col"><input type="number" class="ds-input r-cst text-center" placeholder="1-10" min="1" max="10" value="${d.cost || ''}" onchange="${calc}" oninput="${calc}" required></div>
            <div class="col"><input type="number" class="ds-input r-fea text-center" placeholder="1-10" min="1" max="10" value="${d.feasibility || ''}" onchange="${calc}" oninput="${calc}" required></div>
            <div class="col"><input type="number" class="ds-input r-tim text-center" placeholder="1-10" min="1" max="10" value="${d.time || ''}" onchange="${calc}" oninput="${calc}" required></div>
            <div class="col"><input type="number" class="ds-input r-tot text-center fw-bold" readonly style="background:var(--ds-surface-raised);color:var(--ds-text-main);" value="${d.total_score || ''}"></div>`);
    },
    addCbaRow(d = {}) {
        const val = d.solution || '';
        const opts = this.buildSolutionOptions(val);
        this.addRowTemplate('s5_cbaContainer', d, `
            <div class="col-4">
                <select class="ds-input ds-select r-sol" data-saved-val="${val.replace(/"/g, '&quot;')}" required>
                    ${opts}
                </select>
            </div>
            <div class="col-2"><input type="text" class="ds-input r-cost" placeholder="e.g. ₹20,000" value="${d.estimated_cost || ''}" required></div>
            <div class="col-3"><input type="text" class="ds-input r-ben" placeholder="e.g. Save ₹1.2L/month in rework" value="${d.expected_benefit || ''}" required></div>
            <div class="col-2"><input type="text" class="ds-input r-roi" placeholder="e.g. 600% in first year" value="${d.roi || ''}" required></div>`);
    },
    addCBARow(d = {}) { this.addCbaRow(d); },
    addSeRow(d = {}) {
        const val = d.solution || '';
        const opts = this.buildSolutionOptions(val);
        this.addRowTemplate('s5_seContainer', d, `
            <div class="col-3">
                <select class="ds-input ds-select r-sol" data-saved-val="${val.replace(/"/g, '&quot;')}" required>
                    ${opts}
                </select>
            </div>
            <div class="col-4"><input type="text" class="ds-input r-risk" placeholder="e.g. Production line downtime during replacement" value="${d.potential_risk || ''}" required></div>
            <div class="col-4"><input type="text" class="ds-input r-plan" placeholder="e.g. Schedule during Sunday maintenance shift" value="${d.mitigation_plan || ''}" required></div>`);
    },
    addSideEffectRow(d = {}) { this.addSeRow(d); },
    addPilotRow(d = {}) {
        const val = d.solution || '';
        const opts = this.buildSolutionOptions(val);
        this.addRowTemplate('s5_pilotContainer', d, `
            <div class="col-3">
                <select class="ds-input ds-select r-sol" data-saved-val="${val.replace(/"/g, '&quot;')}" required>
                    ${opts}
                </select>
            </div>
            <div class="col-2"><input type="text" class="ds-input r-loc" placeholder="e.g. Assembly Line A" value="${d.location || ''}" required></div>
            <div class="col-2"><input type="text" class="ds-input r-dur" placeholder="e.g. 5 days" value="${d.duration || ''}" required></div>
            <div class="col-2"><input type="text" class="ds-input r-res" placeholder="e.g. 0 defects in pilot run" value="${d.result || ''}" required></div>
            <div class="col-2"><input type="text" class="ds-input r-dec" placeholder="e.g. Adopt" value="${d.decision || ''}" required></div>`);
    },
    addActionRow(d = {}) {
        this.addRowTemplate('s5_actionContainer', d, `
            <div class="col-4"><input type="text" class="ds-input r-act" placeholder="e.g. Order new crimp die CD-4421" value="${d.what || ''}" required></div>
            <div class="col-2"><input type="text" class="ds-input r-own" placeholder="e.g. Rajesh Kumar" value="${d.who || ''}" required></div>
            <div class="col-2"><input type="date" class="ds-input r-due" value="${d.when || ''}" required></div>
            <div class="col-3"><input type="text" class="ds-input r-how" placeholder="e.g. Issue purchase order via SAP" value="${d.how || ''}" required></div>`);
    },
    addResourceRow(d = {}) {
        this.addRowTemplate('s5_resourceContainer', d, `
            <div class="col-4"><input type="text" class="ds-input r-res" placeholder="e.g. Torque wrench calibration rig" value="${d.resource || ''}" required></div>
            <div class="col-2"><input type="text" class="ds-input r-bud" placeholder="e.g. ₹15,000" value="${d.budget || ''}" required></div>
            <div class="col-3"><input type="text" class="ds-input r-src" placeholder="e.g. Vendor ABC Ltd" value="${d.source || ''}" required></div>
            <div class="col-2"><input type="text" class="ds-input r-stat" placeholder="e.g. Approved" value="${d.status || ''}" required></div>`);
    },

    getVal(id) { return (document.getElementById(id) || {}).value || ''; },
    setVal(id, val) { const el = document.getElementById(id); if (el) el.value = (val !== undefined && val !== null) ? val : ''; }
};

window.StageModules = window.StageModules || {};
window.StageModules[5] = Stage5;
