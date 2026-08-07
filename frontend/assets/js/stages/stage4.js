const Stage4 = {
    projectData: null,

    renderHTML() {
        return `
            <!-- STAGE 4 FORM -->
            <div id="stage4Form">
                
                <div class="alert alert-info mb-4 shadow-sm" style="background:rgba(var(--ds-primary-rgb),.06); border-left:4px solid var(--ds-primary); border-radius: var(--radius-md);">
                    <h6 class="fw-bold mb-1 d-flex align-items-center gap-2" style="color:var(--ds-primary)">
                        <i data-lucide="info" style="width:16px;height:16px;"></i>Stage Purpose
                    </h6>
                    <p class="mb-0" style="font-size:0.85rem; color:var(--ds-text-secondary);">Perform detailed root cause analysis using Good vs Bad comparisons, statistical testing, Scatter Diagrams to verify influence, and Control Charts to verify process instability. Complete with a 5-Why verification.</p>
                </div>

                <!-- Section 1 - Suspect Causes -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                            <span class="ds-icon-circle bg-primary-soft text-primary" style="width:28px;height:28px;font-size:.7rem;">1</span>
                            Root Causes
                        </h5>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary">Section 1 - Root Causes (from Stage 3)</h6>
                            <button class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[4].addVerifiedCauseRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Cause
                            </button>
                        </div>
                        <div id="s4_verifiedContainer" class="mb-0">
                            <div class="row text-muted small fw-bold mb-2 px-2">
                                <div class="col-4">Cause</div>
                                <div class="col-4">Method</div>
                                <div class="col-3">Status</div>
                                <div class="col-1"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section 2 - Why-Why Analysis -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                            <span class="ds-icon-circle bg-primary-soft text-primary" style="width:28px;height:28px;font-size:.7rem;">2</span>
                            Why-Why Analysis (5-Why)
                        </h5>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary">Section 2 - Why-Why Analysis (5-Why Verification)</h6>
                            <button class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[4].addWhyRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add 5-Why Sequence
                            </button>
                        </div>
                        <div id="s4_whyContainer" class="mb-0"></div>
                    </div>
                </div>

                <!-- Section 3 - Hypothesis Testing -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                            <span class="ds-icon-circle bg-primary-soft text-primary" style="width:28px;height:28px;font-size:.7rem;">3</span>
                            Hypothesis Testing
                        </h5>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary">Section 3 - Hypothesis Testing</h6>
                            <button class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[4].addHypothesisRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Hypothesis
                            </button>
                        </div>
                        <div id="s4_hypothesisContainer" class="mb-0">
                            <div class="row text-muted small fw-bold mb-2 px-2">
                                <div class="col-3">Hypothesis</div>
                                <div class="col-3">Null Hyp (H0)</div>
                                <div class="col-3">Alt Hyp (H1)</div>
                                <div class="col-2">Test Used</div>
                                <div class="col-1"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section 4 - Good vs Bad Comparison -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                            <span class="ds-icon-circle bg-primary-soft text-primary" style="width:28px;height:28px;font-size:.7rem;">4</span>
                            Good vs Bad Comparison
                        </h5>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary">Section 4 - Good vs Bad Comparison</h6>
                            <button class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[4].addGoodBadRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Factor
                            </button>
                        </div>
                        <div id="s4_goodBadContainer" class="mb-0">
                            <div class="row text-muted small fw-bold mb-2 px-2">
                                <div class="col-3">Factor</div>
                                <div class="col-3">Good Condition</div>
                                <div class="col-3">Bad Condition</div>
                                <div class="col-2">Difference</div>
                                <div class="col-1"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section 5 - Statistical Validation -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                            <span class="ds-icon-circle bg-primary-soft text-primary" style="width:28px;height:28px;font-size:.7rem;">5</span>
                            Statistical Validation
                        </h5>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary">Section 5 - Statistical Validation</h6>
                            <button class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[4].addValidationRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Validation
                            </button>
                        </div>
                        <div id="s4_validationContainer" class="mb-4">
                            <div class="row text-muted small fw-bold mb-2 px-2">
                                <div class="col-3">Test Type</div>
                                <div class="col-2">p-Value</div>
                                <div class="col-3">Confidence Level</div>
                                <div class="col-3">Conclusion</div>
                                <div class="col-1"></div>
                            </div>
                        </div>

                        <!-- QC Tool 6: Scatter Diagram -->
                        <div class="p-3 border rounded bg-white mb-0 shadow-sm" style="border-radius: var(--radius-md);">
                            <h6 class="fw-bold text-primary mb-3 d-flex align-items-center gap-2">
                                <i data-lucide="dot-chart" style="width:16px;height:16px;"></i> QC Tool 6: Scatter Correlation Diagram
                            </h6>
                            <div class="row g-3">
                                <div class="col-md-5">
                                    <div class="row g-2 mb-3">
                                        <div class="col-6">
                                            <label class="ds-label text-xs">X Cause Variable</label>
                                            <input type="text" id="s4_scatter_x_label" class="ds-input py-1 px-2 text-xs" value="Temperature (°C)" oninput="StageModules[4].calcScatter()" required>
                                        </div>
                                        <div class="col-6">
                                            <label class="ds-label text-xs">Y Effect Variable</label>
                                            <input type="text" id="s4_scatter_y_label" class="ds-input py-1 px-2 text-xs" value="Defect Rate (%)" oninput="StageModules[4].calcScatter()" required>
                                        </div>
                                    </div>
                                    <div class="d-flex justify-content-between align-items-center mb-2">
                                        <small class="fw-bold">Observation Data Points</small>
                                        <button type="button" class="ds-btn ds-btn-ghost ds-btn-sm py-0 text-xs px-2" onclick="StageModules[4].addScatterRow()">+ Add Point</button>
                                    </div>
                                    <div id="s4ScatterPointsContainer" style="max-height: 180px; overflow-y: auto;">
                                        <div class="row text-muted text-xs mb-1">
                                            <div class="col-5">X Value</div>
                                            <div class="col-5">Y Value</div>
                                            <div class="col-2"></div>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-7 border-start text-center">
                                    <div class="p-2 border rounded bg-light mb-3 text-start">
                                        <h6 class="fw-bold text-xs mb-1">Correlation Summary:</h6>
                                        <div class="row g-2 text-xs">
                                            <div class="col-6">Coefficient (r): <span class="fw-bold" id="s4_scatter_r_display">---</span><input type="hidden" id="s4_scatter_r"></div>
                                            <div class="col-6">Strength: <span class="fw-bold text-primary" id="s4_scatter_strength_display">---</span><input type="hidden" id="s4_scatter_strength"></div>
                                            <div class="col-12">Trend Line: <span class="fw-bold text-secondary" id="s4_scatter_trend_display">y = mx + c</span><input type="hidden" id="s4_scatter_m"><input type="hidden" id="s4_scatter_c"></div>
                                        </div>
                                    </div>
                                    <div class="mx-auto" style="max-width: 380px;">
                                        <canvas id="s4ScatterCanvas" style="max-height: 180px; width: 100%;"></canvas>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section 6 - Data Reconfirmation -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                            <span class="ds-icon-circle bg-primary-soft text-primary" style="width:28px;height:28px;font-size:.7rem;">6</span>
                            Data Reconfirmation
                        </h5>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary">Section 6 - Data Reconfirmation</h6>
                            <button class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[4].addReconfirmRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Data Set
                            </button>
                        </div>
                        <div id="s4_reconfirmContainer" class="mb-4">
                            <div class="row text-muted small fw-bold mb-2 px-2">
                                <div class="col-3">Data Set</div>
                                <div class="col-2">Sample Size</div>
                                <div class="col-3">Result</div>
                                <div class="col-3">Validated (Yes/No)</div>
                                <div class="col-1"></div>
                            </div>
                        </div>

                        <!-- QC Tool 7: Control Chart -->
                        <div class="p-3 border rounded bg-white mb-0 shadow-sm" style="border-radius: var(--radius-md);">
                            <h6 class="fw-bold text-primary mb-3 d-flex align-items-center gap-2">
                                <i data-lucide="line-chart" style="width:16px;height:16px;"></i> QC Tool 7: Control Chart (Time-based Process Stability)
                            </h6>
                            <div class="row g-3">
                                <div class="col-md-5">
                                    <div class="d-flex justify-content-between align-items-center mb-2">
                                        <small class="fw-bold">Time-based Data Observations</small>
                                        <button type="button" class="ds-btn ds-btn-ghost ds-btn-sm py-0 text-xs px-2" onclick="StageModules[4].addControlRow()">+ Add Reading</button>
                                    </div>
                                    <div id="s4ControlPointsContainer" style="max-height: 180px; overflow-y: auto;">
                                        <div class="row text-muted text-xs mb-1">
                                            <div class="col-5">Time/Date Label</div>
                                            <div class="col-5">Measured Value</div>
                                            <div class="col-2"></div>
                                        </div>
                                    </div>
                                </div>
                                <div class="col-md-7 border-start text-center">
                                    <div class="p-2 border rounded bg-light mb-3 text-start">
                                        <h6 class="fw-bold text-xs mb-1">Statistical Control Limits:</h6>
                                        <div class="row g-2 text-xs">
                                            <div class="col-4">UCL: <span class="fw-bold text-danger" id="s4_control_ucl_display">---</span><input type="hidden" id="s4_control_ucl"></div>
                                            <div class="col-4">CL (Mean): <span class="fw-bold text-primary" id="s4_control_cl_display">---</span><input type="hidden" id="s4_control_cl"></div>
                                            <div class="col-4">LCL: <span class="fw-bold text-danger" id="s4_control_lcl_display">---</span><input type="hidden" id="s4_control_lcl"></div>
                                            <div class="col-12 mt-1 border-top pt-1 text-danger" id="s4_control_warnings">No out-of-control points.</div>
                                        </div>
                                    </div>
                                    <div class="mx-auto" style="max-width: 380px;">
                                        <canvas id="s4ControlCanvas" style="max-height: 180px; width: 100%;"></canvas>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section 7 - Root Cause Register -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                            <span class="ds-icon-circle bg-primary-soft text-primary" style="width:28px;height:28px;font-size:.7rem;">7</span>
                            Root Cause Register
                        </h5>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary">Section 7 - Root Cause Register</h6>
                            <button class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[4].addRootRegisterRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Root Cause
                            </button>
                        </div>
                        <div id="s4_rootRegisterContainer" class="mb-0">
                            <div class="row text-muted small fw-bold mb-2 px-2">
                                <div class="col-2">ID</div>
                                <div class="col-6">Root Cause</div>
                                <div class="col-3">Source (Stats/Why-Why)</div>
                                <div class="col-1"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section 8 - Root Cause Ranking -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                            <span class="ds-icon-circle bg-primary-soft text-primary" style="width:28px;height:28px;font-size:.7rem;">8</span>
                            Root Cause Ranking
                        </h5>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary">Section 8 - Root Cause Ranking</h6>
                            <button class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[4].addRankingRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Ranking
                            </button>
                        </div>
                        <div id="s4_rankingContainer" class="mb-0">
                            <div class="row text-muted small fw-bold mb-2 px-2">
                                <div class="col-5">Root Cause</div>
                                <div class="col-2">Impact (1-10)</div>
                                <div class="col-2">Ease of Fix (1-10)</div>
                                <div class="col-2">Score</div>
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
        const d = wf.find(w => w.stage_id === 4)?.data || {};
        
        let ver = d.verified_causes || [];
        if (!ver.length) {
            const s3Data = wf.find(w => w.stage_id === 3)?.data || {};
            const s3DiagramData = s3Data.fishbone_l3?.diagram_data || [];
            const selectedCauses = s3DiagramData.filter(r => r.status === 'Selected');
            if (selectedCauses.length) {
                ver = selectedCauses.map(sc => ({
                    cause: sc.level1 + (sc.level2 ? ` - ${sc.level2}` : ''),
                    method: '',
                    status: 'Awaiting Verification'
                }));
            }
        }

        const verContainer = document.getElementById('s4_verifiedContainer');
        verContainer.innerHTML = `
            <div class="row text-muted small fw-bold mb-2 px-2">
                <div class="col-4">Cause</div>
                <div class="col-4">Method</div>
                <div class="col-3">Status</div>
                <div class="col-1"></div>
            </div>
        `;
        if (ver.length) ver.forEach(r => this.addVerifiedCauseRow(r));
        else this.addVerifiedCauseRow();

        const hyp = d.hypothesis_testing || [];
        const hypContainer = document.getElementById('s4_hypothesisContainer');
        hypContainer.innerHTML = `
            <div class="row text-muted small fw-bold mb-2 px-2">
                <div class="col-3">Hypothesis</div>
                <div class="col-3">Null Hyp (H0)</div>
                <div class="col-3">Alt Hyp (H1)</div>
                <div class="col-2">Test Used</div>
                <div class="col-1"></div>
            </div>
        `;
        if (hyp.length) hyp.forEach(r => this.addHypothesisRow(r));
        else this.addHypothesisRow();

        const gb = d.good_vs_bad || [];
        const gbContainer = document.getElementById('s4_goodBadContainer');
        gbContainer.innerHTML = `
            <div class="row text-muted small fw-bold mb-2 px-2">
                <div class="col-3">Factor</div>
                <div class="col-3">Good Condition</div>
                <div class="col-3">Bad Condition</div>
                <div class="col-2">Difference</div>
                <div class="col-1"></div>
            </div>
        `;
        if (gb.length) gb.forEach(r => this.addGoodBadRow(r));
        else this.addGoodBadRow();

        // Statistical validation table & Scatter Diagram
        const stat = d.statistical_validation || {};
        const statTable = Array.isArray(stat) ? stat : (stat.table || []);
        const statContainer = document.getElementById('s4_validationContainer');
        statContainer.innerHTML = `
            <div class="row text-muted small fw-bold mb-2 px-2">
                <div class="col-3">Test Type</div>
                <div class="col-2">p-Value</div>
                <div class="col-3">Confidence Level</div>
                <div class="col-3">Conclusion</div>
                <div class="col-1"></div>
            </div>
        `;
        if (statTable.length) statTable.forEach(r => this.addValidationRow(r));
        else this.addValidationRow();

        // Load Scatter Points
        const scatter = stat.scatter || {};
        this.setVal('s4_scatter_x_label', scatter.x_label || 'Temperature (°C)');
        this.setVal('s4_scatter_y_label', scatter.y_label || 'Defect Rate (%)');
        
        const scatterContainer = document.getElementById('s4ScatterPointsContainer');
        scatterContainer.innerHTML = `
            <div class="row text-muted text-xs mb-1">
                <div class="col-5">X Value</div>
                <div class="col-5">Y Value</div>
                <div class="col-2"></div>
            </div>
        `;
        const points = scatter.points || [];
        if (points.length) {
            points.forEach(pt => this.addScatterRow(pt));
        } else {
            // Default baseline dataset
            const defaults = [{x:10, y:5}, {x:12, y:8}, {x:15, y:12}, {x:18, y:15}, {x:20, y:22}, {x:22, y:26}, {x:25, y:35}];
            defaults.forEach(pt => this.addScatterRow(pt));
        }
        this.calcScatter();

        // Data reconfirmation table & Control Chart
        const recon = d.data_reconfirmation || {};
        const reconTable = Array.isArray(recon) ? recon : (recon.table || []);
        const reconContainer = document.getElementById('s4_reconfirmContainer');
        reconContainer.innerHTML = `
            <div class="row text-muted small fw-bold mb-2 px-2">
                <div class="col-3">Data Set</div>
                <div class="col-2">Sample Size</div>
                <div class="col-3">Result</div>
                <div class="col-3">Validated (Yes/No)</div>
                <div class="col-1"></div>
            </div>
        `;
        if (reconTable.length) reconTable.forEach(r => this.addReconfirmRow(r));
        else this.addReconfirmRow();

        // Control readings
        const controlChart = recon.control_chart || {};
        const ctrlContainer = document.getElementById('s4ControlPointsContainer');
        ctrlContainer.innerHTML = `
            <div class="row text-muted text-xs mb-1">
                <div class="col-5">Time/Date Label</div>
                <div class="col-5">Measured Value</div>
                <div class="col-2"></div>
            </div>
        `;
        const ctrlPoints = controlChart.points || [];
        if (ctrlPoints.length) {
            ctrlPoints.forEach(pt => this.addControlRow(pt));
        } else {
            // Default time series dataset
            const defaults = [
                {label:'Day 1', val:14.2}, {label:'Day 2', val:15.1}, {label:'Day 3', val:13.9},
                {label:'Day 4', val:19.8}, {label:'Day 5', val:14.5}, {label:'Day 6', val:15.2},
                {label:'Day 7', val:13.8}, {label:'Day 8', val:22.5}, {label:'Day 9', val:14.9},
                {label:'Day 10', val:14.1}
            ];
            defaults.forEach(pt => this.addControlRow(pt));
        }
        this.calcControlChart();

        // Why-Why Analysis
        const why = d.why_why_analysis || [];
        const whyContainer = document.getElementById('s4_whyContainer');
        whyContainer.innerHTML = '';
        if (why.length) why.forEach(r => this.addWhyRow(r));
        else this.addWhyRow();
        this.updateWhyCauseDropdowns();

        // Root cause register
        const rootReg = d.root_cause_register || [];
        const rootRegContainer = document.getElementById('s4_rootRegisterContainer');
        rootRegContainer.innerHTML = `
            <div class="row text-muted small fw-bold mb-2 px-2">
                <div class="col-2">ID</div>
                <div class="col-6">Root Cause</div>
                <div class="col-3">Source (Stats/Why-Why)</div>
                <div class="col-1"></div>
            </div>
        `;
        if (rootReg.length) rootReg.forEach(r => this.addRootRegisterRow(r));
        else this.addRootRegisterRow();

        // Root ranking
        const rank = d.root_cause_ranking || [];
        const rankContainer = document.getElementById('s4_rankingContainer');
        rankContainer.innerHTML = `
            <div class="row text-muted small fw-bold mb-2 px-2">
                <div class="col-5">Root Cause</div>
                <div class="col-2">Impact (1-10)</div>
                <div class="col-2">Ease of Fix (1-10)</div>
                <div class="col-2">Score</div>
                <div class="col-1"></div>
            </div>
        `;
        if (rank.length) rank.forEach(r => this.addRankingRow(r));
        else this.addRankingRow();

        const gate = d.approval_gate || {};
        this.setVal('s4_gate_verified_by', gate.verified_by);
        this.setVal('s4_gate_date', gate.date);
        this.setVal('s4_gate_status', gate.status);
        this.setVal('s4_gate_comments', gate.comments);

        if (window.lucide) lucide.createIcons();
    },

    collectData() {
        return {
            verified_causes: this.collectRows('s4_verifiedContainer', ['.r-cause', '.r-meth', '.r-stat'], ['cause', 'method', 'status']),
            hypothesis_testing: this.collectRows('s4_hypothesisContainer', ['.r-hyp', '.r-h0', '.r-h1', '.r-test'], ['hypothesis', 'null_hyp', 'alt_hyp', 'test_used']),
            good_vs_bad: this.collectRows('s4_goodBadContainer', ['.r-fact', '.r-good', '.r-bad', '.r-diff'], ['factor', 'good_condition', 'bad_condition', 'difference']),
            statistical_validation: {
                table: this.collectRows('s4_validationContainer', ['.r-test', '.r-pval', '.r-conf', '.r-conc'], ['test_type', 'p_value', 'confidence_level', 'conclusion']),
                scatter: {
                    x_label: this.getVal('s4_scatter_x_label'),
                    y_label: this.getVal('s4_scatter_y_label'),
                    points: this.collectScatterPoints(),
                    r: this.getVal('s4_scatter_r'),
                    m: this.getVal('s4_scatter_m'),
                    c: this.getVal('s4_scatter_c'),
                    strength: this.getVal('s4_scatter_strength')
                }
            },
            data_reconfirmation: {
                table: this.collectRows('s4_reconfirmContainer', ['.r-set', '.r-size', '.r-res', '.r-val'], ['data_set', 'sample_size', 'result', 'validated']),
                control_chart: {
                    points: this.collectControlPoints(),
                    ucl: this.getVal('s4_control_ucl'),
                    lcl: this.getVal('s4_control_lcl'),
                    cl: this.getVal('s4_control_cl')
                }
            },
            why_why_analysis: this.collectWhyRows(),
            root_cause_register: this.collectRows('s4_rootRegisterContainer', ['.r-id', '.r-cause', '.r-src'], ['id', 'root_cause', 'source']),
            root_cause_ranking: this.collectRows('s4_rankingContainer', ['.r-cause', '.r-imp', '.r-ease', '.r-sco'], ['root_cause', 'impact', 'ease_of_fix', 'score']),
            approval_gate: {
                verified_by: this.getVal('s4_gate_verified_by'),
                date: this.getVal('s4_gate_date'),
                status: this.getVal('s4_gate_status'),
                comments: this.getVal('s4_gate_comments')
            }
        };
    },

    // Scatter Calculations
    addScatterRow(data = {}) {
        const c = document.getElementById('s4ScatterPointsContainer');
        const r = document.createElement('div');
        r.className = 'row g-1 mb-1 align-items-center scatter-row dyn-sub-row';
        r.innerHTML = `
            <div class="col-5"><input type="number" step="any" class="ds-input py-1 px-2 text-xs sc-x" value="${data.x !== undefined ? data.x : ''}" onchange="StageModules[4].calcScatter()" required></div>
            <div class="col-5"><input type="number" step="any" class="ds-input py-1 px-2 text-xs sc-y" value="${data.y !== undefined ? data.y : ''}" onchange="StageModules[4].calcScatter()" required></div>
            <div class="col-2"><button type="button" class="ds-btn ds-btn-ghost text-danger p-1" onclick="this.closest('.scatter-row').remove(); StageModules[4].calcScatter()"><i data-lucide="trash-2" style="width:12px;"></i></button></div>
        `;
        c.appendChild(r);
        if (window.lucide) lucide.createIcons();
    },
    collectScatterPoints() {
        return [...document.querySelectorAll('.scatter-row')].map(r => ({
            x: parseFloat(r.querySelector('.sc-x').value),
            y: parseFloat(r.querySelector('.sc-y').value)
        })).filter(pt => !isNaN(pt.x) && !isNaN(pt.y));
    },
    calcScatter() {
        const pts = this.collectScatterPoints();
        const setLabelText = (id, text) => {
            const el = document.getElementById(id);
            if (el) el.innerText = text;
        };

        let r = 0, m = 0, c = 0, strength = 'No Correlation';
        let linePoints = [];

        if (pts.length < 3) {
            setLabelText('s4_scatter_r_display', '---');
            setLabelText('s4_scatter_strength_display', 'Need min 3 points');
            setLabelText('s4_scatter_trend_display', 'y = mx + c');
            
            this.setVal('s4_scatter_r', '');
            this.setVal('s4_scatter_m', '');
            this.setVal('s4_scatter_c', '');
            this.setVal('s4_scatter_strength', '');
        } else {
            const n = pts.length;
            let sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0, sumY2 = 0;
            pts.forEach(p => {
                sumX += p.x;
                sumY += p.y;
                sumXY += (p.x * p.y);
                sumX2 += (p.x * p.x);
                sumY2 += (p.y * p.y);
            });

            // Pearson r
            const num = (n * sumXY) - (sumX * sumY);
            const den = Math.sqrt(((n * sumX2) - (sumX * sumX)) * ((n * sumY2) - (sumY * sumY)));
            r = den === 0 ? 0 : num / den;

            // Linear regression
            m = ((n * sumX2) - (sumX * sumX)) === 0 ? 0 : ((n * sumXY) - (sumX * sumY)) / ((n * sumX2) - (sumX * sumX));
            c = (sumY - (m * sumX)) / n;

            const absR = Math.abs(r);
            if (absR >= 0.8) strength = r > 0 ? 'Strong Positive' : 'Strong Negative';
            else if (absR >= 0.5) strength = r > 0 ? 'Moderate Positive' : 'Moderate Negative';
            else if (absR >= 0.2) strength = r > 0 ? 'Weak Positive' : 'Weak Negative';

            setLabelText('s4_scatter_r_display', r.toFixed(3));
            setLabelText('s4_scatter_strength_display', strength);
            setLabelText('s4_scatter_trend_display', `y = ${m.toFixed(3)}x + (${c.toFixed(3)})`);

            this.setVal('s4_scatter_r', r.toFixed(4));
            this.setVal('s4_scatter_m', m.toFixed(4));
            this.setVal('s4_scatter_c', c.toFixed(4));
            this.setVal('s4_scatter_strength', strength);

            // Trend line coordinates
            const xVals = pts.map(p => p.x);
            const minX = Math.min(...xVals);
            const maxX = Math.max(...xVals);
            linePoints = [
                { x: minX, y: m * minX + c },
                { x: maxX, y: m * maxX + c }
            ];
        }

        // Chart.js Scatter Diagram
        const canvas = document.getElementById('s4ScatterCanvas');
        if (canvas) {
            if (window.s4ScatterChart) window.s4ScatterChart.destroy();

            const datasets = [
                {
                    label: 'Observations',
                    data: pts,
                    backgroundColor: 'rgb(59, 130, 246)'
                }
            ];

            if (linePoints.length > 0) {
                datasets.push({
                    label: 'Trend Line',
                    data: linePoints,
                    type: 'line',
                    borderColor: 'rgba(239, 68, 68, 0.75)',
                    borderWidth: 1.5,
                    fill: false,
                    pointRadius: 0
                });
            }

            const ctx = canvas.getContext('2d');
            window.s4ScatterChart = new Chart(ctx, {
                type: 'scatter',
                data: { datasets: datasets },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { title: { display: true, text: this.getVal('s4_scatter_x_label') || 'X Value', font: { size: 9 } }, ticks: { font: { size: 8 } } },
                        y: { title: { display: true, text: this.getVal('s4_scatter_y_label') || 'Y Value', font: { size: 9 } }, ticks: { font: { size: 8 } } }
                    }
                }
            });
        }
    },

    // Control Chart Calculations
    addControlRow(data = {}) {
        const c = document.getElementById('s4ControlPointsContainer');
        const r = document.createElement('div');
        r.className = 'row g-1 mb-1 align-items-center control-row dyn-sub-row';
        r.innerHTML = `
            <div class="col-5"><input type="text" class="ds-input py-1 px-2 text-xs ctrl-lbl" value="${data.label || ''}" placeholder="e.g. Day 1" onchange="StageModules[4].calcControlChart()" required></div>
            <div class="col-5"><input type="number" step="any" class="ds-input py-1 px-2 text-xs ctrl-val" value="${data.val !== undefined ? data.val : ''}" onchange="StageModules[4].calcControlChart()" required></div>
            <div class="col-2"><button type="button" class="ds-btn ds-btn-ghost text-danger p-1" onclick="this.closest('.control-row').remove(); StageModules[4].calcControlChart()"><i data-lucide="trash-2" style="width:12px;"></i></button></div>
        `;
        c.appendChild(r);
        if (window.lucide) lucide.createIcons();
    },
    collectControlPoints() {
        const c = document.getElementById('s4ControlPointsContainer');
        if (!c) return [];
        return [...c.querySelectorAll('.control-row')].map(r => ({
            label: r.querySelector('.ctrl-lbl').value || 'Pt',
            val: parseFloat(r.querySelector('.ctrl-val').value)
        })).filter(pt => !isNaN(pt.val));
    },
    calcControlChart() {
        const pts = this.collectControlPoints();
        const setLabelText = (id, text) => {
            const el = document.getElementById(id);
            if (el) el.innerText = text;
        };

        if (pts.length < 3) {
            setLabelText('s4_control_ucl_display', '---');
            setLabelText('s4_control_cl_display', '---');
            setLabelText('s4_control_lcl_display', '---');
            setLabelText('s4_control_warnings', 'Need min 3 points.');
            return;
        }

        const vals = pts.map(p => p.val);
        const sortedVals = [...vals].sort((a,b) => a - b);
        const median = sortedVals[Math.floor(sortedVals.length / 2)];
        
        // Median Absolute Deviation (MAD) for outlier detection
        const absDeviations = vals.map(v => Math.abs(v - median));
        const sortedDeviations = [...absDeviations].sort((a,b) => a - b);
        const mad = sortedDeviations[Math.floor(sortedDeviations.length / 2)];
        const robustSd = mad * 1.4826;

        // Filter out outliers (points beyond 3 robust standard deviations from the median)
        const threshold = robustSd > 0 ? 3 * robustSd : 1;
        const cleanVals = vals.filter(v => Math.abs(v - median) <= threshold);

        let mean = vals.reduce((a,b) => a + b, 0) / vals.length;
        let sd = Math.sqrt(vals.reduce((sum, v) => sum + Math.pow(v - mean, 2), 0) / (vals.length - 1));

        // If we have a good set of clean values, calculate robust limits from them
        if (cleanVals.length >= 3) {
            mean = cleanVals.reduce((a,b) => a + b, 0) / cleanVals.length;
            sd = Math.sqrt(cleanVals.reduce((sum, v) => sum + Math.pow(v - mean, 2), 0) / (cleanVals.length - 1));
            if (sd < 0.0001) sd = 0.01;
        }

        const ucl = mean + 3 * sd;
        const lcl = Math.max(0, mean - 3 * sd); // clamp at 0 for positive physical measurements

        setLabelText('s4_control_cl_display', mean.toFixed(2));
        setLabelText('s4_control_ucl_display', ucl.toFixed(2));
        setLabelText('s4_control_lcl_display', lcl.toFixed(2));

        this.setVal('s4_control_cl', mean.toFixed(4));
        this.setVal('s4_control_ucl', ucl.toFixed(4));
        this.setVal('s4_control_lcl', lcl.toFixed(4));

        // Highlight out-of-control
        let violations = 0;
        pts.forEach(p => {
            if (p.val > ucl || p.val < lcl) violations++;
        });

        const warningEl = document.getElementById('s4_control_warnings');
        if (warningEl) {
            if (violations > 0) {
                warningEl.className = "col-12 mt-1 border-top pt-1 text-danger fw-bold";
                warningEl.innerHTML = `<i data-lucide="alert-octagon" class="d-inline-block me-1" style="width:12px;height:12px;vertical-align:text-bottom;"></i> Warning: ${violations} out-of-control point(s) detected!`;
            } else {
                warningEl.className = "col-12 mt-1 border-top pt-1 text-success";
                warningEl.innerHTML = `Process is stable. No out-of-control points.`;
            }
            if (window.lucide) lucide.createIcons();
        }

        // Render Control Chart
        const canvas = document.getElementById('s4ControlCanvas');
        if (canvas) {
            if (window.s4ControlChart) window.s4ControlChart.destroy();

            const labels = pts.map(p => p.label);
            const uclLine = Array(pts.length).fill(ucl);
            const clLine = Array(pts.length).fill(mean);
            const lclLine = Array(pts.length).fill(lcl);

            const pointColors = pts.map(p => (p.val > ucl || p.val < lcl) ? 'rgb(239, 68, 68)' : 'rgb(59, 130, 246)');
            const pointRadii = pts.map(p => (p.val > ucl || p.val < lcl) ? 6 : 4);

            const ctx = canvas.getContext('2d');
            window.s4ControlChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Process Reading',
                            data: vals,
                            borderColor: 'rgba(59, 130, 246, 0.7)',
                            borderWidth: 1.5,
                            pointBackgroundColor: pointColors,
                            pointBorderColor: pointColors,
                            pointRadius: pointRadii,
                            fill: false,
                            tension: 0.1
                        },
                        {
                            label: 'UCL (Upper Limit)',
                            data: uclLine,
                            borderColor: 'rgb(239, 68, 68)',
                            borderWidth: 1,
                            borderDash: [5, 5],
                            pointRadius: 0,
                            fill: false
                        },
                        {
                            label: 'Center Line (Mean)',
                            data: clLine,
                            borderColor: 'rgb(16, 185, 129)',
                            borderWidth: 1,
                            pointRadius: 0,
                            fill: false
                        },
                        {
                            label: 'LCL (Lower Limit)',
                            data: lclLine,
                            borderColor: 'rgb(239, 68, 68)',
                            borderWidth: 1,
                            borderDash: [5, 5],
                            pointRadius: 0,
                            fill: false
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        x: { ticks: { font: { size: 8 } } },
                        y: { ticks: { font: { size: 8 } } }
                    }
                }
            });
        }
    },

    getStage4Causes() {
        // 1. Prioritize Stage 4 Section 1 Causes (.r-cause inputs in #s4_verifiedContainer)
        const verContainer = document.getElementById('s4_verifiedContainer');
        if (verContainer) {
            const verInputs = [...verContainer.querySelectorAll('.r-cause')].map(inp => (inp.value || '').trim()).filter(Boolean);
            if (verInputs.length > 0) {
                return [...new Set(verInputs)];
            }
        }

        // 2. Only if Section 1 has no causes yet, load Stage 3 Verified / Selected Causes
        let causes = [];
        const s3 = (this.projectData?.workflows || []).find(w => w.stage_id === 3)?.data || {};
        const s3DiagramData = s3.fishbone_l3?.diagram_data || [];
        const selectedCauses = s3DiagramData.filter(r => r.status === 'Selected' || r.status === 'Verified');
        if (selectedCauses.length) {
            causes.push(...selectedCauses.map(sc => (sc.level1 || sc.cause || '') + (sc.level2 ? ` - ${sc.level2}` : '')).filter(Boolean));
        }

        if (!causes.length && s3DiagramData.length) {
            causes.push(...s3DiagramData.map(sc => (sc.level1 || sc.cause || '') + (sc.level2 ? ` - ${sc.level2}` : '')).filter(Boolean));
        }

        if (!causes.length && s3.fishbone_l2 && Array.isArray(s3.fishbone_l2)) {
            causes.push(...s3.fishbone_l2.map(x => x.level1 || x.cause || '').filter(Boolean));
        }

        if (!causes.length && s3.cause_verification && Array.isArray(s3.cause_verification)) {
            causes.push(...s3.cause_verification.map(x => x.cause || x.level1 || '').filter(Boolean));
        }

        return [...new Set(causes)];
    },

    buildWhyCauseOptions(selectedVal = '') {
        const list = this.getStage4Causes();
        let opts = '';
        let hasSelected = false;

        if (list.length) {
            opts += list.map(c => {
                const isSel = (c === selectedVal);
                if (isSel) hasSelected = true;
                return `<option value="${c.replace(/"/g, '&quot;')}" ${isSel ? 'selected' : ''}>${c}</option>`;
            }).join('');
        }

        if (selectedVal && !hasSelected) {
            opts = `<option value="${selectedVal.replace(/"/g, '&quot;')}" selected>${selectedVal}</option>` + opts;
            hasSelected = true;
        }

        if (!list.length && !hasSelected) {
            opts = `<option value="" disabled selected>No suspect causes found</option>` + opts;
        } else if (!hasSelected) {
            opts = `<option value="" disabled selected>Select cause...</option>` + opts;
        } else {
            opts = `<option value="" disabled>Select cause...</option>` + opts;
        }
        return opts;
    },

    updateWhyCauseDropdowns() {
        const container = document.getElementById('s4_whyContainer');
        if (container) {
            container.querySelectorAll('.r-prob').forEach(selectEl => {
                if (selectEl.tagName === 'SELECT') {
                    const targetVal = selectEl.dataset.savedVal || selectEl.value || selectEl.getAttribute('data-saved-val') || '';
                    selectEl.innerHTML = this.buildWhyCauseOptions(targetVal);
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
    },

    // 5 Why Sequence Logic
    addWhyRow(d = {}) {
        const c = document.getElementById('s4_whyContainer');
        const r = document.createElement('div');
        r.className = 'p-3 mb-3 dyn-why-row';
        r.style.cssText = 'background:var(--ds-surface-raised); border-radius:var(--radius-lg); position:relative;';
        
        const causeOptions = this.buildWhyCauseOptions(d.problem || '');

        r.innerHTML = `
            <button class="ds-btn ds-btn-ghost text-danger p-1" style="position:absolute; top:.5rem; right:.5rem;" onclick="this.closest('.dyn-why-row').remove()"><i data-lucide="trash-2" style="width:14px;"></i></button>
            <div class="row g-2 mb-2">
                <div class="col-12">
                    <label class="ds-label">Select Suspect Cause (from Stage 3 Fishbone)</label>
                    <select class="ds-input ds-select r-prob" required>
                        ${causeOptions}
                    </select>
                </div>
            </div>
            <div class="row g-2 mb-2">
                <div class="col-md-2"><label class="ds-label">Why 1</label><input type="text" class="ds-input r-w1" value="${d.why1 || ''}" placeholder="Why 1 statement" required></div>
                <div class="col-md-2"><label class="ds-label">Why 2</label><input type="text" class="ds-input r-w2" value="${d.why2 || ''}" placeholder="Why 2 statement" required></div>
                <div class="col-md-2"><label class="ds-label">Why 3</label><input type="text" class="ds-input r-w3" value="${d.why3 || ''}" placeholder="Why 3 statement" required></div>
                <div class="col-md-2"><label class="ds-label">Why 4</label><input type="text" class="ds-input r-w4" value="${d.why4 || ''}" placeholder="Why 4 statement" required></div>
                <div class="col-md-2"><label class="ds-label">Why 5</label><input type="text" class="ds-input r-w5" value="${d.why5 || ''}" placeholder="Why 5 statement" required></div>
                <div class="col-md-2"><label class="ds-label text-danger">Root Cause</label><input type="text" class="ds-input r-root fw-bold" value="${d.root_cause || ''}" placeholder="Why 5 output" readonly style="background:var(--ds-surface-raised)"></div>
            </div>
            <div class="row g-2 mb-1">
                <div class="col-md-2"><label class="ds-label text-muted" style="font-size:0.7rem;">Why 1 Validation Method</label><input type="text" class="ds-input r-v1" value="${d.val1 || d.validation_method1 || ''}" placeholder="e.g. Visual / Leak test" required></div>
                <div class="col-md-2"><label class="ds-label text-muted" style="font-size:0.7rem;">Why 2 Validation Method</label><input type="text" class="ds-input r-v2" value="${d.val2 || d.validation_method2 || ''}" placeholder="e.g. Process walk audit" required></div>
                <div class="col-md-2"><label class="ds-label text-muted" style="font-size:0.7rem;">Why 3 Validation Method</label><input type="text" class="ds-input r-v3" value="${d.val3 || d.validation_method3 || ''}" placeholder="e.g. Parameter measurement" required></div>
                <div class="col-md-2"><label class="ds-label text-muted" style="font-size:0.7rem;">Why 4 Validation Method</label><input type="text" class="ds-input r-v4" value="${d.val4 || d.validation_method4 || ''}" placeholder="e.g. Maintenance log check" required></div>
                <div class="col-md-4"><label class="ds-label text-muted" style="font-size:0.7rem;">Why 5 / Root Cause Validation Method & Result</label><input type="text" class="ds-input r-v5" value="${d.val5 || d.validation || d.validation_method5 || ''}" placeholder="e.g. Micrometer check & QMS audit (Proven)" required></div>
            </div>`;
        c.appendChild(r);
        
        // Auto sync Why 5 value to the Root Cause input
        const why5 = r.querySelector('.r-w5');
        const root = r.querySelector('.r-root');
        if (why5 && root) {
            why5.addEventListener('input', () => {
                root.value = why5.value;
            });
        }

        if (window.lucide) lucide.createIcons();
    },
    collectWhyRows() {
        const container = document.getElementById('s4_whyContainer');
        if (!container) return [];
        return [...container.querySelectorAll('.dyn-why-row')].map(r => ({
            problem: r.querySelector('.r-prob').value,
            why1: r.querySelector('.r-w1').value, 
            why2: r.querySelector('.r-w2').value,
            why3: r.querySelector('.r-w3').value, 
            why4: r.querySelector('.r-w4').value,
            why5: r.querySelector('.r-w5').value, 
            root_cause: r.querySelector('.r-root').value,
            val1: r.querySelector('.r-v1') ? r.querySelector('.r-v1').value : '',
            val2: r.querySelector('.r-v2') ? r.querySelector('.r-v2').value : '',
            val3: r.querySelector('.r-v3') ? r.querySelector('.r-v3').value : '',
            val4: r.querySelector('.r-v4') ? r.querySelector('.r-v4').value : '',
            val5: r.querySelector('.r-v5') ? r.querySelector('.r-v5').value : ''
        })).filter(x => x.problem || x.root_cause);
    },

    // Standard Grid utilities
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
    addRowTemplate(containerId, data, html, isVerifiedCause = false) {
        const c = document.getElementById(containerId);
        const r = document.createElement('div');
        r.className = 'row g-2 mb-2 align-items-center dyn-row';
        const deleteAction = isVerifiedCause 
            ? "this.closest('.dyn-row').remove(); StageModules[4].updateWhyCauseDropdowns();" 
            : "this.closest('.dyn-row').remove();";
        r.innerHTML = html + `<div class="col-1"><button class="ds-btn ds-btn-ghost text-danger p-1" onclick="${deleteAction}"><i data-lucide="trash-2" style="width:14px;"></i></button></div>`;
        c.appendChild(r);
        if (window.lucide) lucide.createIcons();
    },

    addVerifiedCauseRow(d = {}) {
        this.addRowTemplate('s4_verifiedContainer', d, `
            <div class="col-4"><input type="text" class="ds-input r-cause" placeholder="e.g. Inadequate pressure" value="${d.cause || ''}" oninput="StageModules[4].updateWhyCauseDropdowns()" required></div>
            <div class="col-4"><input type="text" class="ds-input r-meth" placeholder="e.g. Review gauge history" value="${d.method || ''}" required></div>
            <div class="col-3"><input type="text" class="ds-input r-stat" placeholder="e.g. In Progress" value="${d.status || ''}" required></div>`, true);
        this.updateWhyCauseDropdowns();
    },
    addHypothesisRow(d = {}) {
        this.addRowTemplate('s4_hypothesisContainer', d, `
            <div class="col-3"><input type="text" class="ds-input r-hyp" placeholder="e.g. Defect rate correlates with shift timing" value="${d.hypothesis || ''}" required></div>
            <div class="col-3"><input type="text" class="ds-input r-h0" placeholder="e.g. H0: Shift A rate = Shift B rate" value="${d.null_hyp || ''}" required></div>
            <div class="col-3"><input type="text" class="ds-input r-h1" placeholder="e.g. H1: Shift A rate != Shift B rate" value="${d.alt_hyp || ''}" required></div>
            <div class="col-2"><input type="text" class="ds-input r-test" placeholder="e.g. Two-Sample t-Test" value="${d.test_used || ''}" required></div>`);
    },
    addGoodBadRow(d = {}) {
        this.addRowTemplate('s4_goodBadContainer', d, `
            <div class="col-3"><input type="text" class="ds-input r-fact" placeholder="e.g. Wire crimp pressure" value="${d.factor || ''}" required></div>
            <div class="col-3"><input type="text" class="ds-input r-good" placeholder="e.g. Stable at 5.5 bar" value="${d.good_condition || ''}" required></div>
            <div class="col-3"><input type="text" class="ds-input r-bad" placeholder="e.g. Fluctuation below 4.5 bar" value="${d.bad_condition || ''}" required></div>
            <div class="col-2"><input type="text" class="ds-input r-diff" placeholder="e.g. 1.0 bar drop" value="${d.difference || ''}" required></div>`);
    },
    addValidationRow(d = {}) {
        this.addRowTemplate('s4_validationContainer', d, `
            <div class="col-3"><input type="text" class="ds-input r-test" placeholder="e.g. Chi-Square Test" value="${d.test_type || ''}" required></div>
            <div class="col-2"><input type="text" class="ds-input r-pval" placeholder="e.g. 0.034" value="${d.p_value || ''}" required></div>
            <div class="col-3"><input type="text" class="ds-input r-conf" placeholder="e.g. 95%" value="${d.confidence_level || ''}" required></div>
            <div class="col-3"><input type="text" class="ds-input r-conc" placeholder="e.g. Statistically Significant" value="${d.conclusion || ''}" required></div>`);
    },
    addReconfirmRow(d = {}) {
        this.addRowTemplate('s4_reconfirmContainer', d, `
            <div class="col-3"><input type="text" class="ds-input r-set" placeholder="e.g. Trial Batch #3" value="${d.data_set || ''}" required></div>
            <div class="col-2"><input type="number" class="ds-input r-size" placeholder="e.g. 100" value="${d.sample_size || ''}" required></div>
            <div class="col-3"><input type="text" class="ds-input r-res" placeholder="e.g. 0 defects" value="${d.result || ''}" required></div>
            <div class="col-3"><input type="text" class="ds-input r-val" placeholder="e.g. Yes" value="${d.validated || ''}" required></div>`);
    },
    addRootRegisterRow(d = {}) {
        this.addRowTemplate('s4_rootRegisterContainer', d, `
            <div class="col-2"><input type="text" class="ds-input r-id" placeholder="e.g. RC-1" value="${d.id || ''}" required></div>
            <div class="col-6"><input type="text" class="ds-input r-cause" placeholder="e.g. Wire crimper cylinder seal leak" value="${d.root_cause || ''}" required></div>
            <div class="col-3"><input type="text" class="ds-input r-src" placeholder="e.g. 5-Why analysis" value="${d.source || ''}" required></div>`);
    },
    addRankingRow(d = {}) {
        const calc = "const p=this.closest('.dyn-row'); p.querySelector('.r-sco').value = (parseInt(p.querySelector('.r-imp').value)||0)*(parseInt(p.querySelector('.r-ease').value)||0);";
        this.addRowTemplate('s4_rankingContainer', d, `
            <div class="col-5"><input type="text" class="ds-input r-cause" placeholder="e.g. Wire crimper cylinder seal leak" value="${d.root_cause || ''}" required></div>
            <div class="col-2"><input type="number" class="ds-input r-imp" placeholder="1-10" value="${d.impact || ''}" onchange="${calc}" required></div>
            <div class="col-2"><input type="number" class="ds-input r-ease" placeholder="1-10" value="${d.ease_of_fix || ''}" onchange="${calc}" required></div>
            <div class="col-2"><input type="number" class="ds-input r-sco" readonly style="background:var(--ds-surface-raised)" value="${d.score || ''}"></div>`);
    },

    getVal(id) { return (document.getElementById(id) || {}).value || ''; },
    setVal(id, val) { const el = document.getElementById(id); if (el) el.value = (val !== undefined && val !== null) ? val : ''; }
};

window.StageModules = window.StageModules || {};
window.StageModules[4] = Stage4;
