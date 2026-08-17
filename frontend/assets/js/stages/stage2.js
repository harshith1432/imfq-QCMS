const Stage2 = {
    renderHTML() {
        return `
            <style>
                /* Style all responsive tables in Stage 2 with visible scrollbars */
                #stage2Form .table-responsive::-webkit-scrollbar {
                    width: 6px !important;
                    height: 6px !important;
                }
                #stage2Form .table-responsive::-webkit-scrollbar-track {
                    background: rgba(0, 0, 0, 0.03) !important;
                    border-radius: 4px !important;
                }
                #stage2Form .table-responsive::-webkit-scrollbar-thumb {
                    background: rgba(var(--ds-primary-rgb), 0.3) !important;
                    border-radius: 4px !important;
                }
                #stage2Form .table-responsive::-webkit-scrollbar-thumb:hover {
                    background: rgba(var(--ds-primary-rgb), 0.5) !important;
                }
                #stage2Form .table-responsive {
                    scrollbar-width: thin !important;
                    scrollbar-color: rgba(var(--ds-primary-rgb), 0.3) rgba(0, 0, 0, 0.03) !important;
                }
                /* Specific check sheet table constraints */
                .checks-tally-container {
                    max-height: 180px !important;
                    overflow-y: auto !important;
                }
            </style>
            <!-- STAGE 2 FORM -->
            <div id="stage2Form">
                
                <div class="alert alert-info mb-4 shadow-sm" style="background:rgba(var(--ds-primary-rgb),.06); border-left:4px solid var(--ds-primary); border-radius: var(--radius-md);">
                    <h6 class="fw-bold mb-1 d-flex align-items-center gap-2" style="color:var(--ds-primary)">
                        <i data-lucide="info" style="width:16px;height:16px;"></i>Stage Purpose
                    </h6>
                    <p class="mb-0" style="font-size:0.85rem; color:var(--ds-text-secondary);">The purpose of this stage is to understand the problem thoroughly through process observation, standard verification, factual data collection, stratification, prioritization, and on-site validation before entering Cause Identification.</p>
                </div>

                <!-- ─── SECTION 1: PROCESS OBSERVATION ─── -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">2.1</span>
                                <span class="ds-tooltip-trigger" title="Process Observation: On-site Gemba walkthrough observation of actual process operations">Process Observation</span>
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Walk the actual process, upload the flow diagram, and log on-site findings before touching the data.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <h6 class="fw-bold mb-3 text-primary ds-tooltip-trigger" title="Process Flow Diagram: Documented operational workflow map">Process Flow Diagram</h6>
                        <div class="row g-3 mb-4">
                            <div class="col-md-6">
                                <label class="ds-label ds-tooltip-trigger" title="Upload Diagram: Upload process flow diagram file (PNG, SVG, PDF)">Upload Diagram</label>
                                <input type="file" class="ds-input" id="s2_flow_upload">
                            </div>
                            <div class="col-md-6">
                                <label class="ds-label ds-tooltip-trigger" title="Version: Document control revision number for process flow map">Version</label>
                                <input type="text" class="ds-input" id="s2_flow_version" placeholder="e.g. v1.2" required>
                            </div>
                        </div>

                        <h6 class="fw-bold mb-3 text-primary ds-tooltip-trigger" title="Process Walkthrough: On-site physical Gemba observation details">Process Walkthrough</h6>
                        <div class="row g-3 mb-4">
                            <div class="col-md-3"><label class="ds-label ds-tooltip-trigger" title="Observation Date: Date Gemba walkthrough observation was performed">Observation Date</label><input type="date" class="ds-input" id="s2_pw_date" onclick="if(this.showPicker) this.showPicker()" required></div>
                            <div class="col-md-3"><label class="ds-label ds-tooltip-trigger" title="Observer Name: Team member conducting process walkthrough">Observer Name</label><input type="text" class="ds-input" id="s2_pw_observer" required></div>
                            <div class="col-md-3"><label class="ds-label ds-tooltip-trigger" title="Area Observed: Specific shop floor workstation or plant line observed">Area Observed</label><input type="text" class="ds-input" id="s2_pw_area" required></div>
                            <div class="col-md-3"><label class="ds-label ds-tooltip-trigger" title="Process Step: Operation step observed during Gemba walk">Process Step</label><input type="text" class="ds-input" id="s2_pw_step" required></div>
                            <div class="col-12"><label class="ds-label ds-tooltip-trigger" title="Observation Notes: Detailed factual notes logged during process walkthrough">Observation Notes</label><textarea class="ds-input ds-textarea" rows="2" id="s2_pw_notes" required></textarea></div>
                        </div>

                        <h6 class="fw-bold mb-3 text-primary ds-tooltip-trigger" title="Observation Findings: Deviations, inefficiencies, or safety hazards observed">Observation Findings</h6>
                        <div class="row g-3">
                            <div class="col-md-3">
                                <label class="ds-label ds-tooltip-trigger" title="Type: Category of observation finding (Deviation, Inefficiency, Safety Hazard)">Type</label>
                                <select class="ds-input ds-select" id="s2_pf_type" required>
                                    <option>Deviation</option><option>Inefficiency</option><option>Safety Hazard</option><option>Other</option>
                                </select>
                            </div>
                            <div class="col-md-3">
                                <label class="ds-label ds-tooltip-trigger" title="Severity: Impact rating of finding (Low, Medium, High, Critical)">Severity</label>
                                <select class="ds-input ds-select" id="s2_pf_sev" required>
                                    <option>Low</option><option>Medium</option><option>High</option><option>Critical</option>
                                </select>
                            </div>
                            <div class="col-md-6"><label class="ds-label ds-tooltip-trigger" title="Description: Summary description of observation finding">Description</label><input type="text" class="ds-input" id="s2_pf_desc" required></div>
                            <div class="col-12"><label class="ds-label ds-tooltip-trigger" title="Evidence Upload: Photos, video clips, or audit logs supporting finding">Evidence Upload (Images/Videos/Docs)</label><input type="file" multiple class="ds-input" id="s2_pf_evidence"></div>
                        </div>
                    </div>
                </div>

                <!-- ─── SECTION 2: STANDARD VERIFICATION ─── -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">2.2</span>
                                <span class="ds-tooltip-trigger" title="Standard Verification: Auditing whether current SOPs, Control Plans, and specs are documented and followed">Standard Verification</span>
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Confirm whether the current SOP/work standard is actually being followed.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="w-100" style="overflow: visible;">
                            <table class="table table-bordered align-middle text-sm mb-0 w-100">
                                <thead style="background:var(--ds-surface-raised)">
                                    <tr>
                                        <th class="ds-tooltip-trigger" title="Standard Type: SOP, Quality Specification, Control Plan, or PFMEA">Standard Type</th>
                                        <th class="ds-tooltip-trigger" title="Available?: Confirm whether documented standard exists at workstation">Available?</th>
                                        <th class="ds-tooltip-trigger" title="Followed?: Confirm whether operators follow standard in daily work">Followed?</th>
                                        <th class="ds-tooltip-trigger" title="Deviation Found?: Flag whether deviation from standard was observed">Deviation Found?</th>
                                        <th class="ds-tooltip-trigger" title="Details / Findings: Audit findings and deviation gap details">Details / Findings</th>
                                    </tr>
                                    <tr>
                                        <td class="fw-bold"><span title="Standard Operating Procedure (SOP)" style="cursor: help; border-bottom: 1px dotted var(--ds-primary);" data-bs-toggle="tooltip">SOP</span></td>
                                        <td><input type="checkbox" id="sv_sop_avail"></td>
                                        <td><input type="checkbox" id="sv_sop_follow" onchange="StageModules[2].onStandardChange('sop')"></td>
                                        <td><input type="checkbox" id="sv_sop_dev" onchange="StageModules[2].onStandardChange('sop'); StageModules[2].onDeviationChange();"></td>
                                        <td>
                                            <div class="d-flex align-items-center gap-2">
                                                <input type="text" class="ds-input" id="sv_sop_details" placeholder="Describe deviation..." required>
                                                <button type="button" id="btn_analyze_sop_dev" class="ds-btn ds-btn-primary ds-btn-sm" style="white-space:nowrap;" onclick="StageModules[2].openDeviationPage('sop')">
                                                    Analyze Deviation
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td class="fw-bold"><span title="Technical Work & Quality Specifications" style="cursor: help; border-bottom: 1px dotted var(--ds-primary);" data-bs-toggle="tooltip">Specification</span></td>
                                        <td><input type="checkbox" id="sv_spec_avail"></td>
                                        <td><input type="checkbox" id="sv_spec_follow" onchange="StageModules[2].onStandardChange('spec')"></td>
                                        <td><input type="checkbox" id="sv_spec_dev" onchange="StageModules[2].onStandardChange('spec'); StageModules[2].onDeviationChange();"></td>
                                        <td>
                                            <div class="d-flex align-items-center gap-2">
                                                <input type="text" class="ds-input" id="sv_spec_details" placeholder="Describe deviation..." required>
                                                <button type="button" id="btn_analyze_spec_dev" class="ds-btn ds-btn-primary ds-btn-sm" style="white-space:nowrap;" onclick="StageModules[2].openDeviationPage('spec')">
                                                    Analyze Deviation
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td class="fw-bold"><span title="Quality Control & Process Monitoring Plan (CP)" style="cursor: help; border-bottom: 1px dotted var(--ds-primary);" data-bs-toggle="tooltip">Control Plan</span></td>
                                        <td><input type="checkbox" id="sv_cp_avail"></td>
                                        <td><input type="checkbox" id="sv_cp_follow" onchange="StageModules[2].onStandardChange('cp')"></td>
                                        <td><input type="checkbox" id="sv_cp_dev" onchange="StageModules[2].onStandardChange('cp'); StageModules[2].onDeviationChange();"></td>
                                        <td>
                                            <div class="d-flex align-items-center gap-2">
                                                <input type="text" class="ds-input" id="sv_cp_details" placeholder="Describe deviation..." required>
                                                <button type="button" id="btn_analyze_cp_dev" class="ds-btn ds-btn-primary ds-btn-sm" style="white-space:nowrap;" onclick="StageModules[2].openDeviationPage('cp')">
                                                    Analyze Deviation
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td class="fw-bold"><span title="Process Failure Mode and Effects Analysis (PFMEA)" style="cursor: help; border-bottom: 1px dotted var(--ds-primary);" data-bs-toggle="tooltip">PFMEA</span></td>
                                        <td><input type="checkbox" id="sv_pfmea_avail"></td>
                                        <td><input type="checkbox" id="sv_pfmea_review" onchange="StageModules[2].onStandardChange('pfmea')"></td>
                                        <td>-</td>
                                        <td>
                                            <div class="d-flex align-items-center gap-2">
                                                <input type="text" class="ds-input" id="sv_pfmea_details" placeholder="Findings..." required>
                                                <button type="button" id="btn_analyze_pfmea_dev" class="ds-btn ds-btn-primary ds-btn-sm" style="white-space:nowrap;" onclick="StageModules[2].openDeviationPage('pfmea')">
                                                    Analyze Deviation
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                            </table>
                        </div>
                    </div>
                </div>

                <!-- ─── SECTION 3: DATA COLLECTION & QC TOOLS ─── -->
                <div class="glass-card ds-card mb-4" id="s2_section_3" style="transition: opacity 0.3s ease;">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">2.3</span>
                                Data Collection &amp; QC Tools
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Upload the raw observation log; the system auto-generates Trend, Check Sheet, Pareto, Stratification, and Histogram views from it.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="row g-3 mb-4">
                            <div class="col-12">
                                <label class="ds-label">Upload Raw Data (Excel/CSV/PDF) <span class="text-xs text-muted fw-normal">(Optional - Or enter observations manually in table below)</span></label>
                                <div class="d-flex align-items-center gap-2 mb-2">
                                    <input type="file" class="ds-input py-1" id="dc_upload" accept=".csv" style="flex-grow:1;" onchange="StageModules[2].handleCSVUpload(this)">
                                    <button type="button" class="ds-btn ds-btn-ghost text-primary py-1 px-2" style="font-size:0.75rem; white-space:nowrap; border:1px solid var(--ds-primary);" onclick="StageModules[2].downloadTemplate()">
                                        <i data-lucide="download" style="width:13px;height:13px;margin-right:4px;vertical-align:text-bottom;"></i> Download CSV Template
                                    </button>
                                </div>
                                <div class="alert p-2 mb-0 mt-2 text-xs" style="background:rgba(var(--ds-primary-rgb),.05); border:1px solid rgba(var(--ds-primary-rgb),.15); border-radius:6px; line-height:1.4;">
                                    <div class="fw-bold text-primary mb-1 d-flex align-items-center gap-1">
                                        <i data-lucide="info" style="width:12px;height:12px;"></i> Where is this data used?
                                    </div>
                                    Uploaded CSV observations will automatically populate the <strong>Raw Observations & Data Log</strong> table below. 
                                    This log dynamically generates:
                                    <ul class="mb-0 ps-3 mt-1 text-secondary">
                                        <li><strong>Trend Analysis</strong> (distribution over Time/Location/Shift)</li>
                                        <li><strong>Check Sheet & Pareto Chart</strong> (defect frequency and prioritization)</li>
                                        <li><strong>Stratification Analysis</strong> (defect distribution by Shift/Location)</li>
                                        <li><strong>Histogram Analysis</strong> (statistical count and standard deviation)</li>
                                    </ul>
                                </div>
                            </div>
                        </div>

                        <!-- DATA COLLECTION TABLE -->
                        <div class="mt-4 border-top pt-4">
                            <div class="d-flex justify-content-between align-items-center mb-3">
                                <h6 class="fw-bold mb-0 text-primary d-flex align-items-center gap-2">
                                    <i data-lucide="list-todo" style="width:16px;height:16px;"></i> Raw Observations & Data Log
                                </h6>
                                <div class="d-flex gap-2">
                                    <button type="button" class="ds-btn ds-btn-ghost text-primary" style="font-size:.75rem;padding:.25rem .75rem;border:1px dashed var(--ds-primary);" onclick="StageModules[2].loadSampleData()">
                                        <i data-lucide="sparkles" style="width:12px;height:12px;margin-right:2px;"></i> Load Sample Data
                                    </button>
                                    <button type="button" class="ds-btn ds-btn-ghost text-primary" style="font-size:.75rem;padding:.25rem .75rem;border:1px solid var(--ds-primary);" onclick="StageModules[2].addObservationRow()">
                                        <i data-lucide="plus" style="width:12px;height:12px;margin-right:2px;"></i> Add Row
                                    </button>
                                </div>
                            </div>
                            
                            <div class="qc-table-scroll-container mb-3" style="border-radius:var(--radius-md); border:1px solid var(--ds-border-color); max-height: 480px; overflow-y: auto !important; overflow-x: auto !important;">
                                <table class="table table-sm align-middle text-sm mb-0" id="obsTable">
                                    <thead style="background: var(--ds-bg-surface, #f8fafc) !important; position: sticky; top: 0; z-index: 10;">
                                        <tr>
                                            <th style="min-width:190px; position: sticky; top: 0; background: var(--ds-bg-surface, #f8fafc) !important; z-index: 10; border-bottom: 2px solid var(--ds-border-color);">Category / Defect</th>
                                            <th style="min-width:110px; position: sticky; top: 0; background: var(--ds-bg-surface, #f8fafc) !important; z-index: 10; border-bottom: 2px solid var(--ds-border-color);">Value / Count</th>
                                            <th style="min-width:220px; position: sticky; top: 0; background: var(--ds-bg-surface, #f8fafc) !important; z-index: 10; border-bottom: 2px solid var(--ds-border-color);">Time</th>
                                            <th style="min-width:140px; position: sticky; top: 0; background: var(--ds-bg-surface, #f8fafc) !important; z-index: 10; border-bottom: 2px solid var(--ds-border-color);">Where (Location)</th>
                                            <th style="min-width:130px; position: sticky; top: 0; background: var(--ds-bg-surface, #f8fafc) !important; z-index: 10; border-bottom: 2px solid var(--ds-border-color);">Shift</th>
                                            <th style="min-width:140px; position: sticky; top: 0; background: var(--ds-bg-surface, #f8fafc) !important; z-index: 10; border-bottom: 2px solid var(--ds-border-color);">How</th>
                                            <th style="min-width:150px; position: sticky; top: 0; background: var(--ds-bg-surface, #f8fafc) !important; z-index: 10; border-bottom: 2px solid var(--ds-border-color);">Other Dimension</th>
                                            <th style="width:40px; position: sticky; top: 0; background: var(--ds-bg-surface, #f8fafc) !important; z-index: 10; border-bottom: 2px solid var(--ds-border-color);"></th>
                                        </tr>
                                    </thead>
                                    <tbody id="observationLogContainer">
                                        <!-- Dynamic Rows -->
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        <!-- ─── QC TOOLS & INSTANT VISUALIZATIONS ─── -->
                        <div class="mt-4 border-top pt-4">
                            <h5 class="fw-bold mb-4 text-primary d-flex align-items-center gap-2">
                                <i data-lucide="bar-chart-3" style="width:20px;height:20px;"></i> QC Tools & Instant Visualizations
                            </h5>
                            
                            <!-- 1. TREND ANALYSIS (FIRST) -->
                            <div class="glass-card ds-card p-4 mb-4 border shadow-sm">
                                <div class="d-flex justify-content-between align-items-center mb-3 flex-wrap gap-2">
                                    <h6 class="fw-bold mb-0 text-primary d-flex align-items-center gap-2">
                                        <i data-lucide="trending-up" style="width:16px;height:16px;"></i> QC Tool: Trend Analysis
                                    </h6>
                                    <div class="d-flex align-items-center gap-3 flex-wrap">
                                        <div class="d-flex align-items-center gap-2">
                                            <small class="ds-text-secondary text-xs fw-bold">Chart View:</small>
                                            <select class="ds-input ds-select text-xs" id="trend_chart_type_selector" style="width:170px; height:32px; padding: 2px 30px 2px 10px !important;" onchange="StageModules[2].updateTrendChart()" required>
                                                <option value="line" selected>Line Chart (Default)</option>
                                                <option value="bar">Bar Chart</option>
                                                <option value="doughnut">Doughnut Chart</option>
                                                <option value="pareto">Pareto Chart</option>
                                                <option value="spc">Control Chart (SPC)</option>
                                                <option value="scatter">Scatter Plot</option>
                                                <option value="heatmap">Heatmap / Stratified</option>
                                                <option value="gauge">Gauge Chart</option>
                                            </select>
                                        </div>
                                        <div class="d-flex align-items-center gap-2">
                                            <small class="ds-text-secondary text-xs fw-bold">Trend Dimension:</small>
                                            <select class="ds-input ds-select text-xs" id="trend_dimension_selector" style="width:160px; height:32px; padding: 2px 30px 2px 10px !important;" onchange="StageModules[2].updateTrendChart()" required>
                                                <option value="time">Time (Date)</option>
                                                <option value="location">Location (Where)</option>
                                                <option value="shift">Shift</option>
                                                <option value="how">How (Method)</option>
                                                <option value="other">Other Dimension</option>
                                            </select>
                                        </div>
                                    </div>
                                </div>
                                <div class="border p-3 rounded shadow-xs w-100 qc-tool-card" style="min-height: 280px; position: relative; background: var(--ds-bg-card, #ffffff);">
                                    <canvas id="s2TrendCanvas" style="max-height: 280px; width: 100%;"></canvas>
                                </div>
                            </div>

                            <div class="row g-4">
                                <!-- 2. PROCESS HISTOGRAM -->
                                <div class="col-md-6">
                                    <div class="glass-card ds-card p-4 border shadow-sm h-100">
                                        <h6 class="fw-bold mb-3 text-primary d-flex align-items-center gap-2">
                                            <i data-lucide="bar-chart-2" style="width:16px;height:16px;"></i> QC Tool: Process Histogram
                                        </h6>
                                        <div class="row g-2 mb-3">
                                            <div class="col-6">
                                                <div class="p-2 border rounded text-center qc-stat-box" style="background: var(--ds-bg-subtle, #f8fafc);">
                                                    <small class="ds-text-secondary text-xs">Mean (Average)</small>
                                                    <div class="fw-bold text-sm text-main" id="s2_hist_mean_display">---</div>
                                                </div>
                                            </div>
                                            <div class="col-6">
                                                <div class="p-2 border rounded text-center qc-stat-box" style="background: var(--ds-bg-subtle, #f8fafc);">
                                                    <small class="ds-text-secondary text-xs">Median</small>
                                                    <div class="fw-bold text-sm text-main" id="s2_hist_median_display">---</div>
                                                </div>
                                            </div>
                                            <div class="col-6">
                                                <div class="p-2 border rounded text-center qc-stat-box" style="background: var(--ds-bg-subtle, #f8fafc);">
                                                    <small class="ds-text-secondary text-xs">Std Dev (SD)</small>
                                                    <div class="fw-bold text-sm text-main" id="s2_hist_sd_display">---</div>
                                                </div>
                                            </div>
                                            <div class="col-6">
                                                <div class="p-2 border rounded text-center qc-stat-box" style="background: var(--ds-bg-subtle, #f8fafc);">
                                                    <small class="ds-text-secondary text-xs">Distribution Pattern</small>
                                                    <div class="fw-bold text-xs text-main" id="s2_hist_pattern_display">---</div>
                                                </div>
                                            </div>
                                        </div>
                                        <div class="mx-auto border p-2 rounded qc-tool-card" style="height: 180px; position: relative; background: var(--ds-bg-card, #ffffff);">
                                            <canvas id="s2HistogramCanvas" style="max-height: 160px; width: 100%;"></canvas>
                                        </div>
                                    </div>
                                </div>
                                
                                <!-- 3. CHECK SHEET SUMMARY -->
                                <div class="col-md-6">
                                    <div class="glass-card ds-card p-4 border shadow-sm h-100">
                                        <h6 class="fw-bold mb-3 text-primary d-flex align-items-center gap-2">
                                            <i data-lucide="table" style="width:16px;height:16px;"></i> QC Tool: Check Sheet Summary (tallies)
                                        </h6>
                                        <div class="table-responsive checks-tally-container">
                                            <table class="table table-sm table-bordered text-xs mb-0 align-middle">
                                                <thead style="background:var(--ds-surface-raised)">
                                                    <tr>
                                                        <th>Category (Defect Type)</th>
                                                        <th class="text-end" style="width:80px;">Tally Count</th>
                                                        <th>How / Where (Sample)</th>
                                                    </tr>
                                                </thead>
                                                <tbody id="checkSheetSummaryTableBody">
                                                    <tr><td colspan="3" class="text-center text-muted py-3">No data logged yet</td></tr>
                                                </tbody>
                                            </table>
                                        </div>
                                        <div class="p-2 border rounded bg-light mt-3 d-flex justify-content-between align-items-center" style="border-radius: var(--radius-sm);">
                                            <span class="fw-bold text-xs">Total Tally Count:</span>
                                            <span class="badge bg-primary fs-7" id="checkSheetTotal">0</span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                    </div>
                </div>

                <!-- ─── SECTION 4: STRATIFICATION ANALYSIS ─── -->
                <div class="glass-card ds-card mb-4" id="s2_section_4" style="transition: opacity 0.3s ease;">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">2.4</span>
                                <span class="ds-tooltip-trigger" title="Stratification Analysis: Breaking raw observation data down by shift, machine, or location to isolate problem concentration">Stratification Analysis</span>
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Break the raw data down by shift, machine, or operator to isolate where the problem concentrates.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <label class="ds-label mb-0 ds-tooltip-trigger" title="Stratification Categories: Break down problem by operational factors (Shift, Location, Machine, Operator)">Break down problem by categories (Auto-generated from logs or manually input)</label>
                        </div>
                        <div id="stratContainer" class="mb-3">
                            <div class="strat-row mb-1" style="display:grid;grid-template-columns:1fr 2fr 1fr 32px;gap:.5rem;align-items:end;">
                                <small class="ds-label fw-bold ds-tooltip-trigger" title="Type: Dimension type (e.g. By Shift, By Location, By Machine)">Type</small>
                                <small class="ds-label fw-bold ds-tooltip-trigger" title="Category Segment: Specific segment factor under observation">Category Segment</small>
                                <small class="ds-label fw-bold ds-tooltip-trigger" title="Value / Quantity: Defect count or metric value logged for this category segment">Value / Quantity</small>
                                <span></span>
                            </div>
                        </div>

                        <!-- Dynamic Grouped Stratification Summary Tables -->
                        <div id="stratificationSummaryContainer" class="mt-4"></div>
                    </div>
                </div>

                <!-- ─── SECTION 5: PARETO PRIORITIZATION ─── -->
                <div class="glass-card ds-card mb-4" id="s2_section_5" style="transition: opacity 0.3s ease;">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">2.5</span>
                                <span class="ds-tooltip-trigger" title="Pareto Prioritization (80/20 Rule): Rank defect categories by frequency to identify the 20% vital causes driving 80% of defects">Pareto Prioritization (80/20)</span>
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Rank the stratified factors by frequency to identify the vital few driving most of the problem.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="row g-4">
                            <div class="col-md-6 border-end">
                                <div class="d-flex justify-content-between align-items-center mb-3">
                                    <label class="ds-label mb-0 fw-bold ds-tooltip-trigger" title="Defect/Failure Categories: Categorized defect frequency tally derived from raw data log">Defect/Failure Categories (Auto-derived from logs)</label>
                                </div>
                                <div id="paretoContainer" class="mb-3" style="max-height: 250px; overflow-y: auto;">
                                    <div class="pareto-row mb-1" style="display:grid;grid-template-columns:2fr 1fr 1fr 32px;gap:.5rem;align-items:end;">
                                        <small class="ds-label fw-bold ds-tooltip-trigger" title="Category Name: Name of defect or problem category">Category Name</small>
                                        <small class="ds-label fw-bold ds-tooltip-trigger" title="Count / Value: Number of defect occurrences logged">Count / Value</small>
                                        <small class="ds-label fw-bold ds-tooltip-trigger" title="Cum. %: Cumulative percentage contribution to total defects">Cum. %</small>
                                        <span></span>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <label class="ds-label fw-bold mb-2 ds-tooltip-trigger" title="QC Tool: Pareto Chart (80/20 Rule): Visual bar and cumulative line chart ranking defect priority">QC Tool: Pareto Chart (80/20 Rule)</label>
                                <div class="mx-auto border p-2 rounded shadow-xs qc-tool-card" style="height: 250px; position: relative; background: var(--ds-bg-card, #ffffff);">
                                    <canvas id="s2ParetoCanvas" style="max-height: 230px; width: 100%;"></canvas>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- ─── SECTION 6: 5G VERIFICATION ─── -->
                <div class="glass-card ds-card mb-4" id="s2_section_6" style="transition: opacity 0.3s ease;">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">2.6</span>
                                5G Verification
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Verify findings on-site using actual data, actual part, actual place, actual time, and actual condition.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="row g-4">
                            <div class="col-md-6 border-end">
                                <h6 class="fw-bold mb-2 text-primary">Gemba (Actual Place)</h6>
                                <textarea class="ds-input ds-textarea mb-2" id="g5_gemba_notes" rows="2" placeholder="e.g. Visited welding bay 3 during night shift. Noticed workspace clutter and poor lighting." required></textarea>
                                <input type="file" class="ds-input mb-4" id="g5_gemba_ev">
                                
                                <h6 class="fw-bold mb-2 text-primary">Gembutsu (Actual Item)</h6>
                                <input type="text" class="ds-input mb-2" id="g5_gembutsu_item" placeholder="e.g. Crimping tool model CT-400, serial #9921" required>
                                <input type="file" class="ds-input mb-4" id="g5_gembutsu_ev">
 
                                <h6 class="fw-bold mb-2 text-primary">Genjitsu (Actual Facts)</h6>
                                <textarea class="ds-input ds-textarea mb-2" id="g5_genjitsu_facts" rows="2" placeholder="e.g. Shift production logs show 15 defective assemblies were discarded in the scrap bin on 2025-06-25." required></textarea>
                            </div>
                            <div class="col-md-6">
                                <h6 class="fw-bold mb-2 text-primary">Genri (Principles)</h6>
                                <input type="text" class="ds-input mb-2" id="g5_genri_prin" placeholder="e.g. Force pressure must equal 5.5 bar for standard wire thickness" required>
                                <select class="ds-input ds-select mb-4" id="g5_genri_status" required>
                                    <option>Compliant</option><option>Non-Compliant</option>
                                </select>
 
                                <h6 class="fw-bold mb-2 text-primary">Gensoku (Standards)</h6>
                                <textarea class="ds-input ds-textarea mb-2" id="g5_gensoku_std" rows="2" placeholder="e.g. SOP-MFG-WLD-12: Actual pressure was 4.2 bar vs the standard 5.5±0.2 bar." required></textarea>
                                <select class="ds-input ds-select mb-2" id="g5_gensoku_status" required>
                                    <option>Compliant</option><option>Non-Compliant</option>
                                </select>
                            </div>
                        </div>
                    </div>
                </div>
 
                <!-- ─── SECTION 7: CURRENT STATE EVIDENCE ─── -->
                <div class="glass-card ds-card mb-4" id="s2_section_7" style="transition: opacity 0.3s ease;">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">2.7</span>
                                Current State Evidence
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Attach supporting photos, charts, or logs documenting the current (before) state.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="row g-3">
                            <div class="col-md-6">
                                <label class="ds-label">Before KPI Snapshot / Metrics</label>
                                <textarea class="ds-input ds-textarea" id="cs_metrics" rows="5" placeholder="e.g. Defect rate: 4.2%, Scrap rate: 3.5%, Downtime: 45 min/shift, Monthly loss: ₹1,20,000" required></textarea>
                            </div>
                            <div class="col-md-6">
                                <div class="ds-field mb-3">
                                    <label class="ds-label">Upload Before Images/Videos/Docs</label>
                                    <input type="file" multiple class="ds-input" id="cs_media" onchange="StageModules[2].uploadEvidenceFiles(this)">
                                    <div id="cs_uploaded_files_list" class="mt-2 v-stack gap-2"></div>
                                </div>
                                <div class="row g-2">
                                    <div class="col-6">
                                        <div class="ds-field">
                                            <label class="ds-label">Video Link (e.g. MS Stream/YouTube)</label>
                                            <input type="url" class="ds-input text-xs" id="cs_video_link" placeholder="https://..." style="height: 32px;" oninput="StageModules[2].updateLinks()">
                                        </div>
                                    </div>
                                    <div class="col-6">
                                        <div class="ds-field">
                                            <label class="ds-label">Google Drive / Shared Link</label>
                                            <input type="url" class="ds-input text-xs" id="cs_drive_link" placeholder="https://drive.google.com/..." style="height: 32px;" oninput="StageModules[2].updateLinks()">
                                        </div>
                                    </div>
                                </div>
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
        const stage2Data = wf.find(w => w.stage_id === 2)?.data || {};
        
        this.prefill(stage2Data);
        if (window.lucide) lucide.createIcons();
    },

    prefill(d) {
        const po = d.process_observation || {};
        this.setVal('s2_flow_version', po.flow_version || '');
        this.setVal('s2_pw_date', po.date || '');
        this.setVal('s2_pw_observer', po.observer || '');
        this.setVal('s2_pw_area', po.area || '');
        this.setVal('s2_pw_step', po.step || '');
        this.setVal('s2_pw_notes', po.notes || '');
        this.setVal('s2_pf_type', po.finding_type || '');
        this.setVal('s2_pf_sev', po.finding_severity || '');
        this.setVal('s2_pf_desc', po.finding_desc || '');

        const sv = d.standard_verification || {};
        ['sop', 'spec', 'cp'].forEach(k => {
            this.setCheck('sv_'+k+'_avail', sv[k+'_avail'] || false);
            this.setCheck('sv_'+k+'_follow', sv[k+'_follow'] || false);
            this.setCheck('sv_'+k+'_dev', sv[k+'_dev'] || false);
            this.setVal('sv_'+k+'_details', sv[k+'_details'] || '');
            this.onStandardChange(k);
        });
        this.setCheck('sv_pfmea_avail', sv.pfmea_avail || false);
        this.setCheck('sv_pfmea_review', sv.pfmea_review || false);
        this.setVal('sv_pfmea_details', sv.pfmea_details || '');
        this.onStandardChange('pfmea');

        const dc = d.data_collection || {};
        const observations = dc.observations || [];

        // Prefill Observations Log
        const container = document.getElementById('observationLogContainer');
        if (container) {
            container.innerHTML = '';
            if (observations.length) {
                observations.forEach(o => this.addObservationRow(o));
            } else {
                // If legacy data exists but no observations, try to convert check_sheet / histogram data into observations
                const legacyCheckSheet = dc.check_sheet || [];
                const legacyHistValues = (dc.histogram_values || '').split(',').map(x => parseFloat(x.trim())).filter(x => !isNaN(x));
                
                if (legacyCheckSheet.length) {
                    legacyCheckSheet.forEach((row, i) => {
                        const val = legacyHistValues[i] !== undefined ? legacyHistValues[i] : (row.count || 1);
                        this.addObservationRow({
                            category: row.category,
                            value: val,
                            time: new Date().toISOString().substring(0, 16),
                            location: row.notes || 'Line A',
                            shift: 'Shift A',
                            how: 'Visual',
                            other: 'Legacy Import'
                        });
                    });
                } else if (legacyHistValues.length) {
                    legacyHistValues.forEach(val => {
                        this.addObservationRow({
                            category: 'Observation',
                            value: val,
                            time: new Date().toISOString().substring(0, 16),
                            location: 'Line A',
                            shift: 'Shift A',
                            how: 'Measurement',
                            other: 'Legacy Import'
                        });
                    });
                } else {
                    // Default empty row
                    this.addObservationRow();
                }
            }
        }

        // Initialize stratification and pareto manually entered containers just in case
        const strat = d.stratification || [];
        const stratContainer = document.getElementById('stratContainer');
        if (stratContainer) {
            stratContainer.innerHTML = `
                <div class="strat-row mb-1" style="display:grid;grid-template-columns:1fr 2fr 1fr 32px;gap:.5rem;align-items:end;">
                    <small class="ds-label fw-bold">Type</small>
                    <small class="ds-label fw-bold">Category Segment</small>
                    <small class="ds-label fw-bold">Value / Quantity</small>
                    <span></span>
                </div>
            `;
            if (strat.length) {
                strat.forEach(s => this.addStratRow(s));
            } else {
                this.addStratRow();
            }
        }

        const pareto = d.pareto || [];
        const paretoContainer = document.getElementById('paretoContainer');
        if (paretoContainer) {
            paretoContainer.innerHTML = `
                <div class="pareto-row mb-1" style="display:grid;grid-template-columns:2fr 1fr 1fr 32px;gap:.5rem;align-items:end;">
                    <small class="ds-label fw-bold">Category Name</small>
                    <small class="ds-label fw-bold">Count / Value</small>
                    <small class="ds-label fw-bold">Cum. %</small>
                    <span></span>
                </div>
            `;
            if (pareto.length) {
                pareto.forEach(p => this.addParetoRow(p));
            } else {
                this.addParetoRow();
            }
        }

        const fg = d.five_g || {};
        this.setVal('g5_gemba_notes', fg.gemba_notes || '');
        this.setVal('g5_gembutsu_item', fg.gembutsu_item || '');
        this.setVal('g5_genjitsu_src', fg.genjitsu_src || '');
        this.setVal('g5_genjitsu_facts', fg.genjitsu_facts || '');
        this.setVal('g5_genri_prin', fg.genri_prin || '');
        this.setVal('g5_genri_status', fg.genri_status || 'Compliant');
        this.setVal('g5_gensoku_std', fg.gensoku_std || '');
        this.setVal('g5_gensoku_status', fg.gensoku_status || 'Compliant');
        this.setVal('g5_gensoku_dev', fg.gensoku_dev || '');

        const cs = d.current_state || {};
        this.setVal('cs_metrics', cs.metrics || '');
        this.setVal('cs_video_link', cs.video_link || '');
        this.setVal('cs_drive_link', cs.drive_link || '');
        this.uploadedFiles = cs.media_files || [];
        this.renderUploadedFiles();

        // Generate visualizations from observations
        this.updateAllVisualizations();
        this.toggleDeviationSections();
    },

    collectData() {
        const obs = this.collectObservations();
        const sources = [...new Set(obs.map(o => o.category).filter(Boolean))];

        const currentWf = this.projectData?.workflows?.find(w => w.stage_id === 2)?.data || {};
        const currentSv = currentWf.standard_verification || {};

        // Standard derived formats for backward compatibility
        const aggregatedCheckSheet = {};
        const aggregatedStrat = [];
        const aggregatedPareto = [];
        const histValues = [];

        obs.forEach(o => {
            // Check Sheet
            if (!aggregatedCheckSheet[o.category]) {
                aggregatedCheckSheet[o.category] = { count: 0, notes: [] };
            }
            aggregatedCheckSheet[o.category].count += o.value;
            if (o.location && !aggregatedCheckSheet[o.category].notes.includes(o.location)) {
                aggregatedCheckSheet[o.category].notes.push(o.location);
            }

            // Hist Values
            if (!isNaN(o.value)) {
                histValues.push(o.value);
            }
        });

        // Convert aggregated Check Sheet to expected array format
        const checkSheetRows = Object.entries(aggregatedCheckSheet).map(([cat, info]) => ({
            category: cat,
            count: info.count,
            notes: info.notes.join(', ')
        }));

        // Convert Check Sheet to Pareto rows
        const sortedCats = [...checkSheetRows].sort((a, b) => b.count - a.count);
        let totalVal = sortedCats.reduce((sum, c) => sum + c.count, 0);
        let cumSum = 0;
        sortedCats.forEach(c => {
            cumSum += c.count;
            aggregatedPareto.push({
                category: c.category,
                count: c.count,
                cum_perc: totalVal > 0 ? ((cumSum / totalVal) * 100).toFixed(1) + '%' : '0%'
            });
        });

        // Auto-derived Stratification rows
        const shifts = {};
        const locations = {};
        obs.forEach(o => {
            shifts[o.shift] = (shifts[o.shift] || 0) + o.value;
            locations[o.location] = (locations[o.location] || 0) + o.value;
        });
        Object.entries(shifts).forEach(([s, v]) => aggregatedStrat.push({ type: 'By Shift', category: s, value: v }));
        Object.entries(locations).forEach(([l, v]) => aggregatedStrat.push({ type: 'By Location', category: l, value: v }));

        return {
            process_observation: {
                flow_version: this.getVal('s2_flow_version'),
                date: this.getVal('s2_pw_date'),
                observer: this.getVal('s2_pw_observer'),
                area: this.getVal('s2_pw_area'),
                step: this.getVal('s2_pw_step'),
                notes: this.getVal('s2_pw_notes'),
                finding_type: this.getVal('s2_pf_type'),
                finding_severity: this.getVal('s2_pf_sev'),
                finding_desc: this.getVal('s2_pf_desc')
            },
            standard_verification: {
                ...currentSv,
                sop_avail: this.getCheck('sv_sop_avail'), sop_follow: this.getCheck('sv_sop_follow'), sop_dev: this.getCheck('sv_sop_dev'), sop_details: this.getVal('sv_sop_details'),
                spec_avail: this.getCheck('sv_spec_avail'), spec_follow: this.getCheck('sv_spec_follow'), spec_dev: this.getCheck('sv_spec_dev'), spec_details: this.getVal('sv_spec_details'),
                cp_avail: this.getCheck('sv_cp_avail'), cp_follow: this.getCheck('sv_cp_follow'), cp_dev: this.getCheck('sv_cp_dev'), cp_details: this.getVal('sv_cp_details'),
                pfmea_avail: this.getCheck('sv_pfmea_avail'), pfmea_review: this.getCheck('sv_pfmea_review'), pfmea_details: this.getVal('sv_pfmea_details')
            },
            data_collection: {
                sources: sources,
                observations: obs,
                trend: this.getVal('trend_dimension_selector'),
                check_sheet: checkSheetRows,
                histogram_values: histValues.join(', '),
                histogram_stats: {
                    mean: document.getElementById('s2_hist_mean_display')?.innerText || '',
                    median: document.getElementById('s2_hist_median_display')?.innerText || '',
                    sd: document.getElementById('s2_hist_sd_display')?.innerText || '',
                    pattern: document.getElementById('s2_hist_pattern_display')?.innerText || ''
                }
            },
            stratification: aggregatedStrat.length ? aggregatedStrat : this.collectStratRow(),
            pareto: aggregatedPareto.length ? aggregatedPareto : this.collectParetoRow(),
            five_g: {
                gemba_notes: this.getVal('g5_gemba_notes'),
                gembutsu_item: this.getVal('g5_gembutsu_item'),
                genjitsu_src: this.getVal('g5_genjitsu_src'),
                genjitsu_facts: this.getVal('g5_genjitsu_facts'),
                genri_prin: this.getVal('g5_genri_prin'),
                genri_status: this.getVal('g5_genri_status'),
                gensoku_std: this.getVal('g5_gensoku_std'),
                gensoku_status: this.getVal('g5_gensoku_status'),
                gensoku_dev: this.getVal('g5_gensoku_dev')
            },
            current_state: {
                metrics: this.getVal('cs_metrics'),
                media_files: this.uploadedFiles || [],
                video_link: this.getVal('cs_video_link'),
                drive_link: this.getVal('cs_drive_link')
            }
        };
    },

    // Helper to format any date string into YYYY-MM-DDTHH:mm required by <input type="datetime-local">
    formatDateTimeForInput(rawVal) {
        if (!rawVal) return new Date().toISOString().substring(0, 16);
        let str = String(rawVal).trim();
        if (!str) return new Date().toISOString().substring(0, 16);

        // Replace space with T
        str = str.replace(' ', 'T');

        // Check if matching YYYY-MM-DDTHH:mm
        if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(str)) {
            return str.substring(0, 16);
        }

        // Check if YYYY-MM-DD
        if (/^\d{4}-\d{2}-\d{2}$/.test(str)) {
            return `${str}T00:00`;
        }

        // DD/MM/YYYY or MM/DD/YYYY or DD-MM-YYYY
        const ddmmyyyy = str.match(/^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})(?:\s+|T)?(\d{1,2})?:?(\d{1,2})?/);
        if (ddmmyyyy) {
            let p1 = parseInt(ddmmyyyy[1], 10);
            let p2 = parseInt(ddmmyyyy[2], 10);
            let year = parseInt(ddmmyyyy[3], 10);
            let hh = ddmmyyyy[4] ? String(ddmmyyyy[4]).padStart(2, '0') : '00';
            let mm = ddmmyyyy[5] ? String(ddmmyyyy[5]).padStart(2, '0') : '00';

            let month = p2;
            let day = p1;
            if (p1 <= 12 && p2 > 12) {
                month = p1;
                day = p2;
            }
            const mStr = String(month).padStart(2, '0');
            const dStr = String(day).padStart(2, '0');
            return `${year}-${mStr}-${dStr}T${hh}:${mm}`;
        }

        // JS Date fallback
        const d = new Date(str);
        if (!isNaN(d.getTime())) {
            const year = d.getFullYear();
            const month = String(d.getMonth() + 1).padStart(2, '0');
            const day = String(d.getDate()).padStart(2, '0');
            const hours = String(d.getHours()).padStart(2, '0');
            const mins = String(d.getMinutes()).padStart(2, '0');
            return `${year}-${month}-${day}T${hours}:${mins}`;
        }

        return new Date().toISOString().substring(0, 16);
    },

    // Observation Rows Management
    addObservationRow(data = {}) {
        const container = document.getElementById('observationLogContainer');
        if (!container) return;

        const row = document.createElement('tr');
        row.className = 'obs-row';
        
        const timeVal = this.formatDateTimeForInput(data.time);
        const catVal = data.category || '';
        const valueVal = data.value !== undefined ? data.value : 1;
        const locVal = data.location || '';
        const shiftVal = data.shift || 'Shift A';
        const howVal = data.how || '';
        const otherVal = data.other || '';

        row.innerHTML = `
            <td><input type="text" class="ds-input py-1 text-sm obs-cat" placeholder="e.g. Scratch" value="${catVal}" oninput="StageModules[2].updateAllVisualizations()" required></td>
            <td><input type="number" step="any" class="ds-input py-1 text-sm obs-val" placeholder="Value/Count" value="${valueVal}" oninput="StageModules[2].updateAllVisualizations()" required></td>
            <td><input type="datetime-local" class="ds-input py-1 text-sm obs-time" value="${timeVal}" onclick="if(this.showPicker) this.showPicker()" onchange="StageModules[2].updateAllVisualizations()" required></td>
            <td><input type="text" class="ds-input py-1 text-sm obs-loc" placeholder="e.g. Line A" value="${locVal}" oninput="StageModules[2].updateAllVisualizations()" required></td>
            <td>
                <select class="ds-input ds-select py-1 text-sm obs-shift" onchange="StageModules[2].updateAllVisualizations()" required>
                    <option ${shiftVal === 'Shift A' ? 'selected' : ''}>Shift A</option>
                    <option ${shiftVal === 'Shift B' ? 'selected' : ''}>Shift B</option>
                    <option ${shiftVal === 'Shift C' ? 'selected' : ''}>Shift C</option>
                </select>
            </td>
            <td><input type="text" class="ds-input py-1 text-sm obs-how" placeholder="e.g. Visual Check" value="${howVal}" oninput="StageModules[2].updateAllVisualizations()" required></td>
            <td><input type="text" class="ds-input py-1 text-sm obs-other" placeholder="e.g. Operator A" value="${otherVal}" oninput="StageModules[2].updateAllVisualizations()" required></td>
            <td class="text-center">
                <button type="button" class="ds-btn ds-btn-ghost text-danger p-1" style="height:28px; width:28px;" onclick="this.closest('.obs-row').remove(); StageModules[2].updateAllVisualizations();">
                    <i data-lucide="trash-2" style="width:14px;height:14px;"></i>
                </button>
            </td>
        `;
        container.appendChild(row);
        if (window.lucide) lucide.createIcons();
    },

    loadSampleData() {
        const sampleObservations = [
            { category: "Scratch", value: 12, time: "2026-06-26T08:30", location: "Line A", shift: "Shift A", how: "Visual", other: "Op 1" },
            { category: "Dent", value: 5, time: "2026-06-26T09:15", location: "Line B", shift: "Shift A", how: "Visual", other: "Op 2" },
            { category: "Leak", value: 2, time: "2026-06-26T10:00", location: "Line A", shift: "Shift A", how: "Sensor", other: "Op 1" },
            { category: "Scratch", value: 15, time: "2026-06-26T13:45", location: "Line A", shift: "Shift B", how: "Visual", other: "Op 3" },
            { category: "Dent", value: 8, time: "2026-06-26T14:20", location: "Line C", shift: "Shift B", how: "Visual", other: "Op 4" },
            { category: "Scratch", value: 10, time: "2026-06-26T15:00", location: "Line B", shift: "Shift B", how: "Visual", other: "Op 2" },
            { category: "Leak", value: 1, time: "2026-06-26T18:30", location: "Line A", shift: "Shift C", how: "Sensor", other: "Op 5" },
            { category: "Dent", value: 4, time: "2026-06-26T19:10", location: "Line B", shift: "Shift C", how: "Visual", other: "Op 6" },
        ];

        const container = document.getElementById('observationLogContainer');
        if (container) {
            container.innerHTML = '';
            sampleObservations.forEach(o => this.addObservationRow(o));
            this.updateAllVisualizations();
            QCMS.toast("Sample observations loaded successfully", "success");
        }
    },

    collectObservations() {
        const rows = [...document.querySelectorAll('.obs-row')];
        return rows.map(r => ({
            category: r.querySelector('.obs-cat').value.trim(),
            value: parseFloat(r.querySelector('.obs-val').value) || 0,
            time: r.querySelector('.obs-time').value,
            location: r.querySelector('.obs-loc').value.trim(),
            shift: r.querySelector('.obs-shift').value,
            how: r.querySelector('.obs-how').value.trim(),
            other: r.querySelector('.obs-other').value.trim()
        })).filter(o => o.category);
    },

    updateAllVisualizations() {
        const obs = this.collectObservations();

        // 1. Update Check Sheet & Summaries
        const checkSheetBody = document.getElementById('checkSheetSummaryTableBody');
        const checkSheetTotal = document.getElementById('checkSheetTotal');
        const categoriesMap = {};
        let totalTally = 0;

        obs.forEach(o => {
            const count = o.value || 1;
            categoriesMap[o.category] = (categoriesMap[o.category] || 0) + count;
            totalTally += count;
        });

        if (checkSheetBody) {
            if (obs.length === 0) {
                checkSheetBody.innerHTML = '<tr><td colspan="3" class="text-center text-muted py-3">No data logged yet</td></tr>';
            } else {
                checkSheetBody.innerHTML = Object.entries(categoriesMap).map(([cat, count]) => {
                    const matchedObs = obs.filter(o => o.category === cat);
                    const locations = [...new Set(matchedObs.map(o => o.location).filter(Boolean))].join(', ');
                    const methods = [...new Set(matchedObs.map(o => o.how).filter(Boolean))].join(', ');
                    return `
                        <tr>
                            <td class="fw-semibold">${cat}</td>
                            <td class="text-end fw-bold">${count}</td>
                            <td><span class="text-muted">${methods || 'N/A'}</span> @ <span class="fw-semibold">${locations || 'N/A'}</span></td>
                        </tr>
                    `;
                }).join('');
            }
        }
        if (checkSheetTotal) checkSheetTotal.innerText = totalTally;

        // 2. Update Trend Chart
        this.updateTrendChart(obs);

        // 3. Update Histogram
        this.updateHistogramChart(obs);

        // 4. Update Pareto Prioritization
        this.updateParetoChart(obs);

        // 5. Update Stratification Breakdown
        this.updateStratificationFromObs(obs);
    },

    updateTrendChart(obs = null) {
        if (!obs) obs = this.collectObservations();
        const canvas = document.getElementById('s2TrendCanvas');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        if (window.s2TrendChart) {
            window.s2TrendChart.destroy();
            window.s2TrendChart = null;
        }

        if (obs.length === 0) {
            return;
        }

        const dimension = document.getElementById('trend_dimension_selector')?.value || 'time';
        const selectedChartType = document.getElementById('trend_chart_type_selector')?.value || 'line';

        const groups = {};
        obs.forEach(o => {
            let key = 'Unknown';
            if (dimension === 'time') {
                key = o.time ? o.time.split('T')[0] : 'Unknown';
            } else if (dimension === 'location') {
                key = o.location || 'Unknown';
            } else if (dimension === 'shift') {
                key = o.shift || 'Unknown';
            } else if (dimension === 'how') {
                key = o.how || 'Unknown';
            } else if (dimension === 'other') {
                key = o.other || 'Unknown';
            }
            groups[key] = (groups[key] || 0) + (o.value || 1);
        });

        let labels = [];
        let data = [];

        if (dimension === 'time') {
            labels = Object.keys(groups).sort();
            data = labels.map(l => groups[l]);
        } else {
            labels = Object.keys(groups).sort((a, b) => groups[b] - groups[a]);
            data = labels.map(l => groups[l]);
        }

        const palette = [
            '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', 
            '#06b6d4', '#f97316', '#64748b', '#14b8a6', '#a855f7'
        ];

        let chartConfig = {};

        switch (selectedChartType) {
            case 'bar':
                chartConfig = {
                    type: 'bar',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: `Total (${dimension})`,
                            data: data,
                            backgroundColor: labels.map((_, i) => palette[i % palette.length]),
                            borderRadius: 6,
                            borderWidth: 0
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false } },
                        scales: {
                            x: { ticks: { font: { size: 10 } }, grid: { display: false } },
                            y: { beginAtZero: true, ticks: { font: { size: 10 }, precision: 0 } }
                        }
                    }
                };
                break;

            case 'doughnut':
                chartConfig = {
                    type: 'doughnut',
                    data: {
                        labels: labels,
                        datasets: [{
                            data: data,
                            backgroundColor: labels.map((_, i) => palette[i % palette.length]),
                            borderWidth: 2,
                            borderColor: '#ffffff'
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { display: true, position: 'right', labels: { font: { size: 11 } } }
                        },
                        cutout: '65%'
                    }
                };
                break;

            case 'pareto':
                {
                    const paired = labels.map((l, i) => ({ label: l, val: data[i] }))
                                         .sort((a, b) => b.val - a.val);
                    const paretoLabels = paired.map(p => p.label);
                    const paretoVals = paired.map(p => p.val);
                    const total = paretoVals.reduce((acc, v) => acc + v, 0) || 1;

                    let cumSum = 0;
                    const cumPercents = paretoVals.map(v => {
                        cumSum += v;
                        return Math.min(100, Math.round((cumSum / total) * 1000) / 10);
                    });

                    chartConfig = {
                        type: 'bar',
                        data: {
                            labels: paretoLabels,
                            datasets: [
                                {
                                    type: 'bar',
                                    label: 'Frequency / Count',
                                    data: paretoVals,
                                    backgroundColor: 'rgba(59, 130, 246, 0.75)',
                                    borderColor: '#3b82f6',
                                    borderWidth: 1,
                                    borderRadius: 4,
                                    yAxisID: 'y'
                                },
                                {
                                    type: 'line',
                                    label: 'Cumulative %',
                                    data: cumPercents,
                                    borderColor: '#ef4444',
                                    backgroundColor: '#ef4444',
                                    pointBackgroundColor: '#ef4444',
                                    pointRadius: 4,
                                    borderWidth: 2,
                                    yAxisID: 'y1'
                                }
                            ]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: { legend: { display: true, position: 'top' } },
                            scales: {
                                x: { ticks: { font: { size: 10 } }, grid: { display: false } },
                                y: { type: 'linear', position: 'left', beginAtZero: true, ticks: { font: { size: 10 } } },
                                y1: {
                                    type: 'linear',
                                    position: 'right',
                                    beginAtZero: true,
                                    max: 100,
                                    grid: { drawOnChartArea: false },
                                    ticks: { font: { size: 10 }, callback: v => v + '%' }
                                }
                            }
                        }
                    };
                }
                break;

            case 'spc':
                {
                    const numVals = data.map(v => Number(v) || 0);
                    const n = numVals.length || 1;
                    const mean = numVals.reduce((a, b) => a + b, 0) / n;
                    const variance = numVals.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / n;
                    const stdDev = Math.sqrt(variance);

                    const ucl = Number((mean + 3 * stdDev).toFixed(2));
                    const lcl = Number(Math.max(0, mean - 3 * stdDev).toFixed(2));
                    const cl = Number(mean.toFixed(2));

                    chartConfig = {
                        type: 'line',
                        data: {
                            labels: labels,
                            datasets: [
                                {
                                    label: 'Observation Count',
                                    data: numVals,
                                    borderColor: '#3b82f6',
                                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                                    pointBackgroundColor: '#3b82f6',
                                    pointRadius: 5,
                                    tension: 0.15,
                                    fill: false
                                },
                                {
                                    label: `CL (Mean: ${cl})`,
                                    data: Array(n).fill(cl),
                                    borderColor: '#10b981',
                                    borderDash: [6, 6],
                                    pointRadius: 0,
                                    fill: false
                                },
                                {
                                    label: `UCL (+3σ: ${ucl})`,
                                    data: Array(n).fill(ucl),
                                    borderColor: '#ef4444',
                                    borderDash: [4, 4],
                                    pointRadius: 0,
                                    fill: false
                                },
                                {
                                    label: `LCL (-3σ: ${lcl})`,
                                    data: Array(n).fill(lcl),
                                    borderColor: '#f59e0b',
                                    borderDash: [4, 4],
                                    pointRadius: 0,
                                    fill: false
                                }
                            ]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: { legend: { display: true, position: 'top', labels: { font: { size: 10 } } } },
                            scales: {
                                x: { ticks: { font: { size: 10 } }, grid: { display: false } },
                                y: { beginAtZero: true, ticks: { font: { size: 10 } } }
                            }
                        }
                    };
                }
                break;

            case 'scatter':
                {
                    const scatterPoints = obs.map((o, idx) => ({
                        x: idx + 1,
                        y: o.value || 1,
                        label: o.category || `Obs #${idx + 1}`
                    }));

                    chartConfig = {
                        type: 'scatter',
                        data: {
                            datasets: [{
                                label: 'Observation Values',
                                data: scatterPoints,
                                backgroundColor: 'rgba(59, 130, 246, 0.75)',
                                borderColor: '#3b82f6',
                                pointRadius: 6,
                                pointHoverRadius: 8
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: { display: false },
                                tooltip: {
                                    callbacks: {
                                        label: (ctx) => {
                                            const raw = ctx.raw || {};
                                            return `${raw.label || 'Obs'}: (${raw.x}, ${raw.y})`;
                                        }
                                    }
                                }
                            },
                            scales: {
                                x: {
                                    type: 'linear',
                                    position: 'bottom',
                                    title: { display: true, text: 'Observation Index #', font: { size: 11 } },
                                    ticks: { precision: 0 }
                                },
                                y: {
                                    beginAtZero: true,
                                    title: { display: true, text: 'Value / Count', font: { size: 11 } }
                                }
                            }
                        }
                    };
                }
                break;

            case 'heatmap':
                {
                    const categories = [...new Set(obs.map(o => o.category || 'Other'))];
                    const catDatasets = categories.map((cat, idx) => {
                        const catData = labels.map(lbl => {
                            return obs.filter(o => {
                                let key = 'Unknown';
                                if (dimension === 'time') key = o.time ? o.time.split('T')[0] : 'Unknown';
                                else if (dimension === 'location') key = o.location || 'Unknown';
                                else if (dimension === 'shift') key = o.shift || 'Unknown';
                                else if (dimension === 'how') key = o.how || 'Unknown';
                                else if (dimension === 'other') key = o.other || 'Unknown';
                                return key === lbl && (o.category || 'Other') === cat;
                            }).reduce((acc, item) => acc + (item.value || 1), 0);
                        });

                        return {
                            label: cat,
                            data: catData,
                            backgroundColor: palette[idx % palette.length],
                            borderRadius: 4
                        };
                    });

                    chartConfig = {
                        type: 'bar',
                        data: {
                            labels: labels,
                            datasets: catDatasets
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: { legend: { display: true, position: 'top', labels: { font: { size: 10 } } } },
                            scales: {
                                x: { stacked: true, ticks: { font: { size: 10 } }, grid: { display: false } },
                                y: { stacked: true, beginAtZero: true, ticks: { font: { size: 10 } } }
                            }
                        }
                    };
                }
                break;

            case 'gauge':
                {
                    const totalVal = data.reduce((a, b) => a + b, 0);
                    const maxTarget = Math.max(100, Math.ceil(totalVal * 1.25));
                    const remaining = Math.max(0, maxTarget - totalVal);

                    chartConfig = {
                        type: 'doughnut',
                        data: {
                            labels: ['Total Observations', 'Target Scale Buffer'],
                            datasets: [{
                                data: [totalVal, remaining],
                                backgroundColor: ['#3b82f6', '#e2e8f0'],
                                borderWidth: 0
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            rotation: 270,
                            circumference: 180,
                            cutout: '75%',
                            plugins: {
                                legend: { display: true, position: 'bottom' },
                                tooltip: {
                                    callbacks: {
                                        label: (ctx) => `${ctx.label}: ${ctx.raw}`
                                    }
                                }
                            }
                        }
                    };
                }
                break;

            case 'line':
            default:
                chartConfig = {
                    type: 'line',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: `Total (${dimension})`,
                            data: data,
                            backgroundColor: 'rgba(59, 130, 246, 0.15)',
                            borderColor: '#3b82f6',
                            borderWidth: 2,
                            pointBackgroundColor: '#3b82f6',
                            pointRadius: 4,
                            fill: true,
                            tension: 0.15
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: { legend: { display: false } },
                        scales: {
                            x: { ticks: { font: { size: 10 } }, grid: { display: false } },
                            y: { beginAtZero: true, ticks: { font: { size: 10 }, precision: 0 } }
                        }
                    }
                };
                break;
        }

        window.s2TrendChart = new Chart(ctx, chartConfig);
    },

    updateHistogramChart(obs) {
        const canvas = document.getElementById('s2HistogramCanvas');
        if (!canvas) return;

        const setStatText = (id, text) => {
            const el = document.getElementById(id);
            if (el) el.innerText = text;
        };

        const vals = obs.map(o => parseFloat(o.value)).filter(v => !isNaN(v));

        if (vals.length < 5) {
            setStatText('s2_hist_mean_display', '---');
            setStatText('s2_hist_median_display', '---');
            setStatText('s2_hist_sd_display', '---');
            setStatText('s2_hist_pattern_display', 'Need min 5 values');
            if (window.s2HistogramChart) {
                window.s2HistogramChart.destroy();
                window.s2HistogramChart = null;
            }
            return;
        }

        // Calculations
        const mean = vals.reduce((a, b) => a + b, 0) / vals.length;
        const sorted = [...vals].sort((a, b) => a - b);
        const mid = Math.floor(sorted.length / 2);
        const median = sorted.length % 2 !== 0 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
        const variance = vals.length > 1 ? vals.reduce((sum, v) => sum + Math.pow(v - mean, 2), 0) / (vals.length - 1) : 0;
        const sd = Math.sqrt(variance);

        let skewness = 0;
        if (sd > 0 && vals.length > 2) {
            const n = vals.length;
            let sumCubedDiff = 0;
            for (let i = 0; i < n; i++) {
                sumCubedDiff += Math.pow((vals[i] - mean) / sd, 3);
            }
            skewness = (n / ((n - 1) * (n - 2))) * sumCubedDiff;
        }

        let pattern = "Symmetrical";
        if (skewness > 0.5) pattern = "Skewed Right";
        else if (skewness < -0.5) pattern = "Skewed Left";
        else if (sd === 0) pattern = "Uniform";

        setStatText('s2_hist_mean_display', mean.toFixed(2));
        setStatText('s2_hist_median_display', median.toFixed(2));
        setStatText('s2_hist_sd_display', sd.toFixed(2));
        setStatText('s2_hist_pattern_display', pattern);

        // Bins
        const min = Math.min(...vals);
        const max = Math.max(...vals);
        const range = max - min;
        const numBins = Math.max(5, Math.ceil(1 + 3.322 * Math.log10(vals.length)));
        const binWidth = range === 0 ? 1 : range / numBins;

        const bins = Array(numBins).fill(0);
        const binLabels = [];
        for (let i = 0; i < numBins; i++) {
            const start = min + i * binWidth;
            const end = min + (i + 1) * binWidth;
            binLabels.push(`${start.toFixed(1)}-${end.toFixed(1)}`);
        }

        vals.forEach(v => {
            let idx = Math.floor((v - min) / binWidth);
            if (idx >= numBins) idx = numBins - 1;
            if (idx < 0) idx = 0;
            bins[idx]++;
        });

        if (window.s2HistogramChart) {
            window.s2HistogramChart.destroy();
        }

        const ctx = canvas.getContext('2d');
        window.s2HistogramChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: binLabels,
                datasets: [{
                    label: 'Readings Count',
                    data: bins,
                    backgroundColor: 'rgba(99, 102, 241, 0.6)',
                    borderColor: 'rgb(99, 102, 241)',
                    borderWidth: 1,
                    barPercentage: 1.0,
                    categoryPercentage: 1.0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { ticks: { font: { size: 8 } } },
                    y: { beginAtZero: true, ticks: { precision: 0, font: { size: 8 } } }
                }
            }
        });
    },

    updateParetoChart(obs) {
        const canvas = document.getElementById('s2ParetoCanvas');
        if (!canvas) return;

        const categoriesMap = {};
        obs.forEach(o => {
            categoriesMap[o.category] = (categoriesMap[o.category] || 0) + (o.value || 1);
        });

        const sortedCats = Object.entries(categoriesMap)
            .map(([category, count]) => ({ category, count }))
            .sort((a, b) => b.count - a.count);

        const total = sortedCats.reduce((sum, item) => sum + item.count, 0);

        // Render standard Pareto list container inside Section 5
        const container = document.getElementById('paretoContainer');
        if (container) {
            container.innerHTML = `
                <div class="pareto-row mb-1" style="display:grid;grid-template-columns:2fr 1fr 1fr 32px;gap:.5rem;align-items:end;">
                    <small class="ds-label fw-bold">Category Name</small>
                    <small class="ds-label fw-bold">Count / Value</small>
                    <small class="ds-label fw-bold">Cum. %</small>
                    <span></span>
                </div>
            `;
            let cumSumTable = 0;
            sortedCats.forEach(item => {
                cumSumTable += item.count;
                const pct = total > 0 ? ((cumSumTable / total) * 100).toFixed(1) + '%' : '0%';
                
                const row = document.createElement('div');
                row.className = 'pareto-row mb-1';
                row.style.cssText = 'display:grid;grid-template-columns:2fr 1fr 1fr 32px;gap:.5rem;align-items:center;';
                row.innerHTML = `
                    <input type="text" class="ds-input py-1 text-xs pt-cat" value="${item.category}" readonly>
                    <input type="number" class="ds-input py-1 text-xs pt-count" value="${item.count}" readonly>
                    <input type="text" class="ds-input py-1 text-xs pt-perc" value="${pct}" readonly style="background:var(--ds-surface-raised)">
                    <span></span>
                `;
                container.appendChild(row);
            });
        }

        if (window.s2ParetoChart) {
            window.s2ParetoChart.destroy();
            window.s2ParetoChart = null;
        }

        if (sortedCats.length === 0) {
            return;
        }

        const labels = sortedCats.map(x => x.category);
        const counts = sortedCats.map(x => x.count);
        
        let cumSum = 0;
        const cumulativePercentages = sortedCats.map(x => {
            cumSum += x.count;
            return total > 0 ? ((cumSum / total) * 100).toFixed(1) : 0;
        });

        const ctx = canvas.getContext('2d');
        window.s2ParetoChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Defect Frequency',
                        data: counts,
                        backgroundColor: 'rgba(239, 68, 68, 0.65)',
                        borderColor: 'rgb(239, 68, 68)',
                        borderWidth: 1.5,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Cumulative %',
                        data: cumulativePercentages,
                        type: 'line',
                        borderColor: 'rgb(249, 115, 22)',
                        backgroundColor: 'rgba(249, 115, 22, 0.1)',
                        borderWidth: 2,
                        pointBackgroundColor: 'rgb(249, 115, 22)',
                        yAxisID: 'y1',
                        tension: 0.1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        beginAtZero: true,
                        ticks: { font: { size: 9 } },
                        title: { display: true, text: 'Defects Count', font: { size: 9 } }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        min: 0,
                        max: 100,
                        ticks: { font: { size: 9 } },
                        grid: { drawOnChartArea: false },
                        title: { display: true, text: 'Cumulative %', font: { size: 9 } }
                    }
                }
            }
        });
    },

    updateStratificationFromObs(obs) {
        const stratContainer = document.getElementById('stratContainer');
        const summaryContainer = document.getElementById('stratificationSummaryContainer');
        if (!stratContainer || !summaryContainer) return;

        const shifts = {};
        const locations = {};

        obs.forEach(o => {
            const val = o.value || 1;
            shifts[o.shift] = (shifts[o.shift] || 0) + val;
            if (o.location) {
                locations[o.location] = (locations[o.location] || 0) + val;
            }
        });

        // Clear manual inputs and populate with derived rows
        stratContainer.innerHTML = `
            <div class="strat-row mb-1" style="display:grid;grid-template-columns:1fr 2fr 1fr 32px;gap:.5rem;align-items:end;">
                <small class="ds-label fw-bold">Type</small>
                <small class="ds-label fw-bold">Category Segment</small>
                <small class="ds-label fw-bold">Value / Quantity</small>
                <span></span>
            </div>
        `;

        const addDerivedStrat = (type, cat, val) => {
            const row = document.createElement('div');
            row.className = 'strat-row mb-1';
            row.style.cssText = 'display:grid;grid-template-columns:1fr 2fr 1fr 32px;gap:.5rem;align-items:center;';
            row.innerHTML = `
                <input class="ds-input py-1 text-xs st-type" value="${type}" readonly>
                <input class="ds-input py-1 text-xs st-cat" value="${cat}" readonly>
                <input class="ds-input py-1 text-xs st-val" value="${val}" readonly>
                <span></span>
            `;
            stratContainer.appendChild(row);
        };

        Object.entries(shifts).forEach(([s, v]) => addDerivedStrat('By Shift', s, v));
        Object.entries(locations).forEach(([l, v]) => addDerivedStrat('By Location', l, v));

        this.calcStratification();
    },

    // Standard manual elements builders (preserved for overrides if needed)
    addStratRow(data = {}) {
        const container = document.getElementById('stratContainer');
        if (!container) return;

        const row = document.createElement('div');
        row.className = 'strat-row mb-2';
        row.style.cssText = 'display:grid;grid-template-columns:1fr 2fr 1fr 32px;gap:.5rem;align-items:center;';
        
        const types = ['By Shift', 'By Machine', 'By Operator', 'By Material', 'By Product', 'By Customer', 'By Department', 'By Plant'];
        const typeSelect = types.map(t => `<option ${data.type===t?'selected':''}>${t}</option>`).join('');

        row.innerHTML = `
            <select class="ds-input ds-select st-type" onchange="StageModules[2].calcStratification()" required>${typeSelect}</select>
            <input type="text" class="ds-input st-cat" placeholder="e.g. First Shift, Machine A" value="${data.category || ''}" onchange="StageModules[2].calcStratification()" required>
            <input type="number" class="ds-input st-val" placeholder="Value" value="${data.value || ''}" onchange="StageModules[2].calcStratification()" required>
            <button class="ds-btn ds-btn-ghost text-danger p-1" onclick="this.closest('.strat-row').remove(); StageModules[2].calcStratification()">
                <i data-lucide="trash-2" style="width:14px;height:14px;"></i>
            </button>`;
        container.appendChild(row);
        if (window.lucide) lucide.createIcons();
    },

    calcStratification() {
        const rows = this.collectStratRow();
        const summaryContainer = document.getElementById('stratificationSummaryContainer');
        if (!summaryContainer) return;

        if (rows.length === 0) {
            summaryContainer.innerHTML = '';
            return;
        }

        const groups = {};
        rows.forEach(r => {
            if (!groups[r.type]) groups[r.type] = [];
            groups[r.type].push(r);
        });

        let html = `<h6 class="fw-bold mb-3 text-secondary d-flex align-items-center gap-2 ds-tooltip-trigger" title="QC Tool: Stratification Grouped Analysis: Automatic grouping by operational factors"><i data-lucide="layers" style="width:15px;height:15px;"></i> QC Tool: Stratification Grouped Analysis</h6>`;
        
        for (const [type, items] of Object.entries(groups)) {
            items.sort((a, b) => b.value - a.value);
            const total = items.reduce((sum, item) => sum + item.value, 0);
            const highest = items[0];

            html += `
                <div class="glass-card ds-card p-3 mb-3 border" style="border-radius: var(--radius-md);">
                    <div class="d-flex justify-content-between align-items-center mb-2 flex-wrap gap-2">
                        <span class="fw-bold text-sm text-primary ds-tooltip-trigger" title="${type} Breakdown: Grouped distribution analysis for ${type}">${type} Breakdown</span>
                        ${highest && highest.value > 0 ? `
                        <span class="ds-badge ds-badge-sm orange d-inline-flex align-items-center gap-1 ds-tooltip-trigger" title="Highest Contributor: ${highest.category} accounted for the highest defect volume (${highest.value})">
                            <i data-lucide="trending-up" style="width:10px;height:10px;"></i>
                            Highest Contributor: ${highest.category} (${highest.value})
                        </span>` : ''}
                    </div>
                    <div class="table-responsive">
                        <table class="table table-sm table-bordered text-xs mb-0 align-middle">
                            <thead style="background:var(--ds-surface-raised)">
                                <tr>
                                    <th class="ds-tooltip-trigger" title="Segment Name: Category segment under analysis">Segment Name</th>
                                    <th class="text-end ds-tooltip-trigger" style="width:80px;" title="Count / Val: Quantity or defect volume logged">Count / Val</th>
                                    <th class="text-end ds-tooltip-trigger" style="width:80px;" title="% Share: Percentage contribution of segment to total group volume">% Share</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${items.map(item => {
                                    const percent = total > 0 ? ((item.value / total) * 100).toFixed(1) : '0.0';
                                    const isHighest = item.category === highest.category && item.value > 0;
                                    return `
                                        <tr class="${isHighest ? 'table-warning fw-semibold' : ''}">
                                            <td>${item.category}</td>
                                            <td class="text-end">${item.value}</td>
                                            <td class="text-end">${percent}%</td>
                                        </tr>
                                    `;
                                }).join('')}
                                <tr class="table-light fw-bold">
                                    <td class="ds-tooltip-trigger" title="Total Group Volume: Sum of all logged quantities for this stratification category">Total Group Volume</td>
                                    <td class="text-end">${total}</td>
                                    <td class="text-end">100%</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
        }

        summaryContainer.innerHTML = html;
        if (window.lucide) lucide.createIcons();
    },

    collectStratRow() {
        return [...document.querySelectorAll('.strat-row:not(:first-child)')].map(r => ({
            type: r.querySelector('.st-type').value,
            category: r.querySelector('.st-cat').value,
            value: parseFloat(r.querySelector('.st-val').value) || 0
        })).filter(s => s.category);
    },

    addParetoRow(data = {}) {
        const container = document.getElementById('paretoContainer');
        if (!container) return;

        const row = document.createElement('div');
        row.className = 'pareto-row mb-2';
        row.style.cssText = 'display:grid;grid-template-columns:2fr 1fr 1fr 32px;gap:.5rem;align-items:center;';
        
        row.innerHTML = `
            <input type="text" class="ds-input py-1 text-sm pt-cat" placeholder="e.g. Scratch" value="${data.category || ''}" required>
            <input type="number" class="ds-input py-1 text-sm pt-count" placeholder="Count" value="${data.count || ''}" onchange="StageModules[2].calcPareto()" required>
            <input type="text" class="ds-input py-1 text-sm pt-perc" placeholder="Cum %" value="${data.cum_perc || ''}" readonly style="background:var(--ds-surface-raised)">
            <button class="ds-btn ds-btn-ghost text-danger p-1" onclick="this.closest('.pareto-row').remove(); StageModules[2].calcPareto()">
                <i data-lucide="trash-2" style="width:14px;height:14px;"></i>
            </button>`;
        container.appendChild(row);
        if (window.lucide) lucide.createIcons();
    },

    collectParetoRow() {
        return [...document.querySelectorAll('.pareto-row:not(:first-child)')].map(r => ({
            category: r.querySelector('.pt-cat').value,
            count: parseInt(r.querySelector('.pt-count').value) || 0,
            cum_perc: r.querySelector('.pt-perc').value
        })).filter(p => p.category);
    },

    calcPareto() {
        const rows = [...document.querySelectorAll('.pareto-row:not(:first-child)')];
        let total = 0;
        rows.forEach(r => { total += parseInt(r.querySelector('.pt-count').value) || 0; });
        
        rows.sort((a,b) => {
            return (parseInt(b.querySelector('.pt-count').value)||0) - (parseInt(a.querySelector('.pt-count').value)||0);
        });
        
        const container = document.getElementById('paretoContainer');
        rows.forEach(r => container.appendChild(r));

        let cum = 0;
        rows.forEach(r => {
            const val = parseInt(r.querySelector('.pt-count').value) || 0;
            if (total > 0 && val > 0) {
                cum += val;
                r.querySelector('.pt-perc').value = ((cum / total) * 100).toFixed(1) + '%';
            } else {
                r.querySelector('.pt-perc').value = '';
            }
        });
    },

    // Helper to format date strings into YYYY-MM-DD required by <input type="date">
    formatDateForInput(rawVal) {
        if (!rawVal) return new Date().toISOString().substring(0, 10);
        let str = String(rawVal).trim();
        if (!str) return new Date().toISOString().substring(0, 10);
        if (/^\d{4}-\d{2}-\d{2}/.test(str)) {
            return str.substring(0, 10);
        }
        const d = new Date(str);
        if (!isNaN(d.getTime())) {
            const year = d.getFullYear();
            const month = String(d.getMonth() + 1).padStart(2, '0');
            const day = String(d.getDate()).padStart(2, '0');
            return `${year}-${month}-${day}`;
        }
        return new Date().toISOString().substring(0, 10);
    },

    getVal(id) { return (document.getElementById(id) || {}).value || ''; },
    setVal(id, val) { 
        const el = document.getElementById(id); 
        if (!el) return;
        if (el.type === 'date') {
            el.value = this.formatDateForInput(val);
        } else if (el.type === 'datetime-local') {
            el.value = this.formatDateTimeForInput(val);
        } else {
            el.value = (val !== undefined && val !== null) ? val : ''; 
        }
    },
    getCheck(id) { const el = document.getElementById(id); return el ? el.checked : false; },
    setCheck(id, val) { const el = document.getElementById(id); if (el) el.checked = !!val; },

    onStandardChange(type) {
        const btn = document.getElementById(`btn_analyze_${type}_dev`);
        if (btn) {
            btn.classList.remove('d-none');
        }
    },

    openSopDeviationPage() {
        this.openDeviationPage('sop');
    },

    async openDeviationPage(type) {
        if (this.projectData && this.projectData.id) {
            if (typeof ProjectApp !== 'undefined' && typeof ProjectApp.saveDraft === 'function') {
                try {
                    await ProjectApp.saveDraft();
                } catch (e) {
                    console.warn("Failed to auto-save stage 2 draft before navigating", e);
                }
            }
            window.location.href = `/projects/sop-deviation-analysis.html?id=${this.projectData.id}&type=${type}`;
        }
    },

    onDeviationChange() {
        this.toggleDeviationSections();
    },

    toggleDeviationSections() {
        const sopDev = this.getCheck('sv_sop_dev');
        const specDev = this.getCheck('sv_spec_dev');
        const cpDev = this.getCheck('sv_cp_dev');
        
        const deviationFound = sopDev || specDev || cpDev;
        
        // Check if the form is currently read-only (e.g. if the checkboxes themselves are disabled)
        const isFormReadOnly = document.getElementById('sv_sop_dev')?.disabled || false;
        
        const sectionIds = ['s2_section_3', 's2_section_4', 's2_section_5', 's2_section_6', 's2_section_7'];
        
        sectionIds.forEach(id => {
            const el = document.getElementById(id);
            if (!el) return;
            
            if (deviationFound) {
                el.style.opacity = '1';
                el.style.pointerEvents = 'auto';
                if (!isFormReadOnly) {
                    el.querySelectorAll('input, select, textarea, button').forEach(input => {
                        input.removeAttribute('disabled');
                    });
                }
            } else {
                el.style.opacity = '0.4';
                el.style.pointerEvents = 'none';
                el.querySelectorAll('input, select, textarea, button').forEach(input => {
                    input.setAttribute('disabled', 'true');
                });
            }
        });
    },

    downloadTemplate() {
        const headers = ["Category / Defect", "Value / Count", "Time (YYYY-MM-DD HH:MM)", "Where (Location)", "Shift (Shift A/Shift B/Shift C)", "How (Method)", "Other Dimension"];
        const rows = [
            ["Scratch", "5", "2026-06-27 10:15", "Line A", "Shift A", "Visual Check", "Operator A"],
            ["Dent", "2", "2026-06-27 11:30", "Line B", "Shift B", "Visual Check", "Operator B"],
            ["Crack", "1", "2026-06-27 14:00", "Line A", "Shift A", "Ultrasonic Test", "Operator C"],
            ["Scratch", "3", "2026-06-27 15:45", "Line C", "Shift C", "Visual Check", "Operator D"],
            ["Dent", "4", "2026-06-27 16:30", "Line A", "Shift B", "Visual Check", "Operator A"]
        ];
        
        const csvContent = "data:text/csv;charset=utf-8," 
            + [headers, ...rows].map(e => e.map(val => `"${val.replace(/"/g, '""')}"`).join(",")).join("\n");
            
        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", "qc_data_collection_template.csv");
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    },

    handleCSVUpload(input) {
        const file = input.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const text = e.target.result;
                const rows = this.parseCSV(text);
                
                if (rows.length <= 1) {
                    QCMS.toast("Uploaded CSV is empty or invalid.", "error");
                    return;
                }

                // First row is headers
                const headers = rows[0];
                const dataRows = rows.slice(1);

                // Clear existing observation log rows
                const container = document.getElementById('observationLogContainer');
                if (container) {
                    container.innerHTML = '';
                }

                let importedCount = 0;
                dataRows.forEach(cells => {
                    if (cells.length < 1 || !cells[0] || !cells[0].trim()) return; // Skip empty rows

                    const category = cells[0].trim();
                    const value = parseFloat(cells[1]) || 1;
                    const rawTime = cells[2] ? cells[2].trim() : '';
                    const time = this.formatDateTimeForInput(rawTime);
                    const location = cells[3] ? cells[3].trim() : 'Line A';
                    
                    // Validate shift
                    let shift = cells[4] ? cells[4].trim() : 'Shift A';
                    if (!['Shift A', 'Shift B', 'Shift C'].includes(shift)) {
                        shift = 'Shift A';
                    }

                    const how = cells[5] ? cells[5].trim() : 'Visual Check';
                    const other = cells[6] ? cells[6].trim() : '';

                    this.addObservationRow({
                        category,
                        value,
                        time,
                        location,
                        shift,
                        how,
                        other
                    });
                    importedCount++;
                });

                if (importedCount > 0) {
                    this.updateAllVisualizations();
                    QCMS.toast(`Successfully imported ${importedCount} observation rows from CSV/Excel!`, "success");
                } else {
                    QCMS.toast("No valid data rows found in uploaded file.", "error");
                }
            } catch (err) {
                console.error("[QCMS] CSV Parse Error:", err);
                QCMS.toast("Failed to parse file. Please ensure it matches the template.", "error");
            }
            
            // Reset input so file can be uploaded again
            input.value = '';
        };
        reader.readAsText(file);
    },

    parseCSV(text) {
        // Automatically detect delimiter: comma, semicolon, or tab
        let delimiter = ',';
        const firstLine = text.split(/\r?\n/)[0] || '';
        const commas = (firstLine.match(/,/g) || []).length;
        const semicolons = (firstLine.match(/;/g) || []).length;
        const tabs = (firstLine.match(/\t/g) || []).length;
        if (semicolons > commas && semicolons > tabs) delimiter = ';';
        else if (tabs > commas && tabs > semicolons) delimiter = '\t';

        const lines = [];
        let row = [""];
        let inQuotes = false;

        for (let i = 0; i < text.length; i++) {
            const char = text[i];
            const nextChar = text[i + 1];

            if (char === '"') {
                if (inQuotes && nextChar === '"') {
                    row[row.length - 1] += '"';
                    i++;
                } else {
                    inQuotes = !inQuotes;
                }
            } else if (char === delimiter && !inQuotes) {
                row.push("");
            } else if ((char === '\r' || char === '\n') && !inQuotes) {
                if (char === '\r' && nextChar === '\n') {
                    i++;
                }
                if (row.some(c => c.trim().length > 0)) {
                    lines.push(row);
                }
                row = [""];
            } else {
                row[row.length - 1] += char;
            }
        }
        if (row.some(c => c.trim().length > 0)) {
            lines.push(row);
        }
        return lines;
    },

    async uploadEvidenceFiles(input) {
        if (!input.files || input.files.length === 0) return;
        
        const listContainer = document.getElementById('cs_uploaded_files_list');
        if (listContainer) {
            const spinner = document.createElement('div');
            spinner.id = 'cs_upload_spinner';
            spinner.className = 'text-xs text-primary d-flex align-items-center gap-2 mt-2';
            spinner.innerHTML = `<span class="spinner-border spinner-border-sm" role="status"></span> Uploading files...`;
            listContainer.appendChild(spinner);
        }

        this.uploadedFiles = this.uploadedFiles || [];

        for (let i = 0; i < input.files.length; i++) {
            const file = input.files[i];
            const formData = new FormData();
            formData.append('file', file);
            
            try {
                const res = await api.post('/projects/upload-evidence', formData);
                if (res && res.url) {
                    this.uploadedFiles.push({
                        url: res.url,
                        name: res.name || file.name
                    });
                }
            } catch (err) {
                QCMS.toast(`Failed to upload ${file.name}: ${err.message}`, 'error');
            }
        }
        
        document.getElementById('cs_upload_spinner')?.remove();
        input.value = '';
        this.renderUploadedFiles();
        ProjectApp.saveDraft();
    },

    renderUploadedFiles() {
        const listContainer = document.getElementById('cs_uploaded_files_list');
        if (!listContainer) return;
        
        this.uploadedFiles = this.uploadedFiles || [];
        if (this.uploadedFiles.length === 0) {
            listContainer.innerHTML = '<div class="text-xs text-muted">No files uploaded.</div>';
            return;
        }
        
        listContainer.innerHTML = this.uploadedFiles.map((f, index) => {
            const isImage = /\.(jpg|jpeg|png|gif)$/i.test(f.url);
            const isVideo = /\.(mp4|webm|mov|avi|mkv)$/i.test(f.url);
            
            let preview = '';
            if (isImage) {
                preview = `<img src="${f.url}" style="width: 32px; height: 32px; object-fit: cover; border-radius: 4px;" class="border">`;
            } else if (isVideo) {
                preview = `<div class="d-flex align-items-center justify-content-center bg-dark text-white rounded border" style="width: 32px; height: 32px;"><i data-lucide="video" style="width: 14px; height: 14px;"></i></div>`;
            } else {
                preview = `<div class="d-flex align-items-center justify-content-center bg-light text-muted rounded border" style="width: 32px; height: 32px;"><i data-lucide="file-text" style="width: 14px; height: 14px;"></i></div>`;
            }
            
            return `
                <div class="h-stack justify-content-between p-2 rounded border shadow-xs fade-in qc-evidence-file" style="font-size: 0.8rem; background: var(--ds-bg-card, #ffffff);">
                    <div class="d-flex align-items-center gap-2">
                        ${preview}
                        <a href="${f.url}" target="_blank" class="fw-medium text-main text-decoration-none hover-underline" style="max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                            ${f.name}
                        </a>
                    </div>
                    <button type="button" class="ds-btn ds-btn-ghost text-danger p-1" style="height:24px; width:24px;" onclick="StageModules[2].deleteUploadedFile(${index})">
                        <i data-lucide="trash-2" style="width:12px;height:12px;"></i>
                    </button>
                </div>
            `;
        }).join('');
        
        if (window.lucide) lucide.createIcons();
    },

    deleteUploadedFile(index) {
        this.uploadedFiles = this.uploadedFiles || [];
        this.uploadedFiles.splice(index, 1);
        this.renderUploadedFiles();
        if (typeof markDirty === 'function') markDirty();
    },

    updateLinks() {
        if (typeof markDirty === 'function') markDirty();
    }
};

window.StageModules = window.StageModules || {};
window.StageModules[2] = Stage2;
