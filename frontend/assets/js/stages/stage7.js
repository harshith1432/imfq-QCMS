const Stage7 = {
    projectData: null,

    renderHTML() {
        return `
            <!-- STAGE 7 FORM -->
            <div id="stage7Form">
                <!-- Section 1 - KPI Verification -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">7.1</span>
                                <span class="ds-tooltip-trigger" title="KPI Verification: Key Performance Indicator target vs actual achievement rate">KPI Verification</span>
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Check the project's measurable KPI against the target set in Stage 1.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary ds-tooltip-trigger" title="Section 1 - KPI Verification: Verify baseline, target, and actual performance metrics">Section 1 - KPI Verification</h6>
                            <button class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[7].addKpiRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add KPI
                            </button>
                        </div>
                        <div id="s7_kpiContainer" class="mb-0">
                            <div class="row text-muted small fw-bold mb-2 px-2">
                                <div class="col-3 ds-tooltip-trigger" title="Metric: Name of Key Performance Indicator (e.g. Defect Rate, Scrap Loss)">Metric</div>
                                <div class="col-2 ds-tooltip-trigger" title="Baseline: Measured starting level prior to improvement">Baseline</div>
                                <div class="col-2 ds-tooltip-trigger" title="Target: Desired achievement goal metric level">Target</div>
                                <div class="col-2 ds-tooltip-trigger" title="Actual: Final measured performance metric post-countermeasures">Actual</div>
                                <div class="col-2 ds-tooltip-trigger" title="Variance: Difference between actual and target performance">Variance</div>
                                <div class="col-1"></div>
                            </div>
                        </div>
                        <div class="mt-3 p-2 border rounded bg-light text-xs fw-bold d-flex align-items-center justify-content-between">
                            <span class="ds-tooltip-trigger" title="KPI Achievement: Average percentage of target performance achieved across all verified KPIs">KPI Achievement (Avg Target vs Actual):</span>
                            <span id="s7_dash_kpi" class="text-primary fs-6 fw-bold">---</span>
                        </div>
                    </div>
                </div>

                <!-- Section 2 - Before vs After Analysis -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">7.2</span>
                                <span class="ds-tooltip-trigger" title="Before vs After Analysis: Comparative evaluation measuring defect reduction percentage & process variation improvements">Before vs After Analysis</span>
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Compare before and after data using histogram and control-chart views to confirm improvement.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary ds-tooltip-trigger" title="Section 2 - Before vs After Analysis: Compare pre-improvement and post-improvement process performance">Section 2 - Before vs After Analysis</h6>
                            <button class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[7].addBeforeAfterRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Item
                            </button>
                        </div>
                        <div id="s7_beforeAfterContainer" class="mb-2">
                            <div class="row text-muted small fw-bold mb-2 px-2">
                                <div class="col-3 ds-tooltip-trigger" title="Metric/Process: Quality characteristic or process parameter being compared">Metric/Process</div>
                                <div class="col-3 ds-tooltip-trigger" title="Before Condition: Initial baseline defect rate or measured process parameter before countermeasure">Before Condition</div>
                                <div class="col-3 ds-tooltip-trigger" title="After Condition: Measured defect rate or process parameter after countermeasure implementation">After Condition</div>
                                <div class="col-2 ds-tooltip-trigger" title="Improvement %: Percentage defect reduction = ((Before - After) / Before) * 100">Improvement %</div>
                                <div class="col-1"></div>
                            </div>
                        </div>
                        <div class="mt-2 p-2 border rounded bg-light text-xs fw-bold d-flex align-items-center justify-content-between mb-4">
                            <span class="ds-tooltip-trigger" title="Process Quality Improvement: Average percentage defect reduction across all evaluated process parameters">Process Quality Improvement (Avg Defect Reduction):</span>
                            <span id="s7_dash_quality" class="text-warning fs-6 fw-bold">---</span>
                        </div>

                        <!-- QC Tools Data Upload -->
                        <div class="p-3 border rounded mb-4 shadow-sm qc-tool-card" style="border-radius: var(--radius-md); background: var(--ds-bg-card, #ffffff);">
                            <label class="ds-label mb-1 ds-tooltip-trigger" title="Upload QC Tools Data (Excel/CSV): Import raw measurement log to generate Before vs After Histogram & Control Chart">Upload QC Tools Data (Excel/CSV)</label>
                            <div class="text-xs text-muted mb-2">Upload data for both the Process Variation Histogram and the Control Chart.</div>
                            <div class="d-flex align-items-center gap-2">
                                <input type="file" class="ds-input py-1" id="s7_upload" accept=".csv" style="flex-grow:1;" onchange="StageModules[7].handleCSVUpload(this)">
                                <button type="button" class="ds-btn ds-btn-ghost text-primary py-1 px-3" style="font-size:0.85rem; font-weight:bold; white-space:nowrap; border:1px solid var(--ds-primary);" onclick="StageModules[7].downloadTemplate()">
                                    <i data-lucide="download" style="width:14px;height:14px;margin-right:6px;vertical-align:text-bottom;"></i> Download CSV Template
                                </button>
                            </div>
                        </div>

                        <!-- QC Tool: Histogram Comparison -->
                        <div class="p-3 border rounded mb-4 shadow-sm qc-tool-card" style="border-radius: var(--radius-md); background: var(--ds-bg-card, #ffffff);">
                            <h6 class="fw-bold text-primary mb-3 d-flex align-items-center gap-2 ds-tooltip-trigger" title="Process Variation Histogram: Visual distribution comparison of process data standard deviation before vs after">
                                <i data-lucide="bar-chart-3" style="width:16px;height:16px;"></i> QC Tool Comparison: Process Variation Histogram (Before vs After)
                            </h6>
                            <div class="row g-3">
                                <div class="col-md-5">
                                    <label class="ds-label ds-tooltip-trigger" title="Stage 7 After Improvement Readings: Post-countermeasure numerical measurement samples">Stage 7 After Improvement Numerical Readings (comma-separated)</label>
                                    <textarea class="ds-input ds-textarea" id="s7_hist_after_values" rows="4" placeholder="e.g. 10.1, 10.2, 10.0, 9.9, 10.1, 10.2, 10.0, 10.1, 10.0, 10.1" onchange="StageModules[7].calcHistComparison()" required></textarea>
                                    <div class="mt-2 p-2 border rounded text-xs qc-stat-box" style="background: var(--ds-bg-subtle, #f8fafc);">
                                        <div class="fw-bold mb-1">Variation Reduction Stats:</div>
                                        <div>Before SD: <span id="s7_hist_sd_before" class="fw-bold">---</span> | After SD: <span id="s7_hist_sd_after" class="fw-bold">---</span></div>
                                        <div class="mt-1 text-success fw-bold" id="s7_hist_var_reduction">Variation Reduction: ---</div>
                                    </div>
                                </div>
                                <div class="col-md-7 border-start text-center">
                                    <div class="mx-auto" style="max-width: 380px;">
                                        <canvas id="s7HistogramComparisonCanvas" style="max-height: 180px; width:100%;"></canvas>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- QC Tool: Control Chart Comparison -->
                        <div class="p-3 border rounded mb-0 shadow-sm qc-tool-card" style="border-radius: var(--radius-md); background: var(--ds-bg-card, #ffffff);">
                            <h6 class="fw-bold text-primary mb-2 d-flex align-items-center gap-2">
                                <i data-lucide="line-chart" style="width:16px;height:16px;"></i> QC Tool Comparison: Control Chart Comparison (Before vs After Stability)
                            </h6>
                            <div class="p-2 mb-3 rounded border text-xs d-flex align-items-center gap-2 qc-stat-box" style="background: var(--ds-bg-subtle, #f8fafc);">
                                <i data-lucide="info" style="width:14px;height:14px;" class="text-primary flex-shrink-0"></i>
                                <span><strong>Instructions:</strong> Enter the measured values recorded after implementing countermeasures (e.g. Day 11 to Day 20 readings) in the table below to generate the After-Improvement Control Chart &amp; compare process stability.</span>
                            </div>
                            <div class="row g-3">
                                <div class="col-md-5">
                                    <div class="d-flex justify-content-between align-items-center mb-2">
                                        <small class="fw-bold">After-Improvement Readings</small>
                                        <button type="button" class="ds-btn ds-btn-ghost ds-btn-sm py-0 text-xs px-2" onclick="StageModules[7].addControlRow()">+ Add Reading</button>
                                    </div>
                                    <div id="s7ControlPointsContainer" style="max-height: 180px; overflow-y: auto;">
                                        <div class="row text-muted text-xs mb-1">
                                            <div class="col-5">Time/Date Label</div>
                                            <div class="col-5">Measured Value</div>
                                            <div class="col-2"></div>
                                        </div>
                                    </div>
                                    <div class="mt-2 p-2 border rounded text-xs qc-stat-box" style="background: var(--ds-bg-subtle, #f8fafc);">
                                        <div class="fw-bold mb-1">Stability Analysis:</div>
                                        <div>Before Out-Of-Control: <span id="s7_ctrl_violations_before" class="fw-bold text-danger">---</span></div>
                                        <div>After Out-Of-Control: <span id="s7_ctrl_violations_after" class="fw-bold text-success">---</span></div>
                                        <div class="mt-1 text-success fw-bold" id="s7_ctrl_stability_imp">Stability Improvement: ---</div>
                                    </div>
                                </div>
                                <div class="col-md-7 border-start text-center">
                                    <div class="mx-auto" style="max-width: 380px;">
                                        <canvas id="s7ControlComparisonCanvas" style="max-height: 180px; width: 100%;"></canvas>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section 3 - Statistical Validation -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">7.3</span>
                                <span class="ds-tooltip-trigger" title="Statistical Validation: Statistically confirm the improvement is real and not due to random chance (p-Value < 0.05)">Statistical Validation</span>
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Statistically confirm the improvement is real and not due to chance.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary ds-tooltip-trigger" title="Section 3 - Statistical Validation: Run statistical hypothesis tests (2-sample t-test, proportion test)">Section 3 - Statistical Validation</h6>
                            <button class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[7].addStatRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Stat Check
                            </button>
                        </div>
                        <div id="s7_statContainer" class="mb-0">
                            <div class="row text-muted small fw-bold mb-2 px-2">
                                <div class="col-4 ds-tooltip-trigger" title="Test Type: Name of statistical hypothesis test executed (e.g. 2-Sample t-Test, Chi-Square)">Test Type</div>
                                <div class="col-3 ds-tooltip-trigger" title="p-Value: Calculated probability value (p < 0.05 indicates statistically significant improvement)">p-Value</div>
                                <div class="col-4 ds-tooltip-trigger" title="Conclusion: Statistical interpretation (e.g. Reject H0; defect reduction is statistically significant)">Conclusion</div>
                                <div class="col-1"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section 4 - Benefit Realization & Savings -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">7.4</span>
                                <span class="ds-tooltip-trigger" title="Benefit Realization & Savings: Quantify actual annual savings & quality performance improvements achieved">Benefit Realization &amp; Savings</span>
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Quantify the actual annual savings and quality improvement achieved.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary ds-tooltip-trigger" title="Section 4 - Benefit Realization: Financial savings tracking comparing expected vs actual economic return">Section 4 - Benefit Realization</h6>
                            <button class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[7].addBenefitRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Benefit
                            </button>
                        </div>
                        <div id="s7_benefitContainer" class="mb-0">
                            <div class="row text-muted small fw-bold mb-2 px-2">
                                <div class="col-4 ds-tooltip-trigger" title="Benefit Category: Financial category (e.g. Scrap Reduction, Rework Cost, Warranty Savings)">Benefit Category</div>
                                <div class="col-2 ds-tooltip-trigger" title="Expected: Projected annual monetary savings estimated in Stage 5">Expected</div>
                                <div class="col-2 ds-tooltip-trigger" title="Actual: Verified actual monetary savings achieved after countermeasure implementation">Actual</div>
                                <div class="col-3 ds-tooltip-trigger" title="Variance: Difference between actual savings achieved and expected savings projection">Variance</div>
                                <div class="col-1"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section 5 - ROI Validation -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">7.5</span>
                                <span class="ds-tooltip-trigger" title="ROI Validation: Net Return on Investment (%) measuring annual net economic gain relative to capital invested">ROI Validation</span>
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Validate the return on investment against Stage 5 projections. <strong>ROI (%) represents Annual Net Return on Investment</strong>, calculated as: <code class="text-primary font-mono text-xs">((Annual Savings - Total Investment) / Total Investment) × 100</code>.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <h6 class="fw-bold mb-3 text-primary ds-tooltip-trigger" title="Section 5 - ROI Validation: Financial investment recovery and ROI analysis">Section 5 - ROI Validation</h6>
                        <div class="row g-3 mb-0">
                            <div class="col-md-3">
                                <label class="ds-label ds-tooltip-trigger" title="Total Investment: Capital expenditure, tooling, equipment, and labor implementation costs">Total Investment</label>
                                <input type="number" id="s7_roi_inv" class="ds-input" oninput="StageModules[7].calcROI()" onchange="StageModules[7].calcROI()" required>
                            </div>
                            <div class="col-md-3">
                                <label class="ds-label ds-tooltip-trigger" title="Annual Savings: Verified annual monetary savings from defect reduction & process improvements">Annual Savings</label>
                                <input type="number" id="s7_roi_sav" class="ds-input" oninput="StageModules[7].calcROI()" onchange="StageModules[7].calcROI()" required>
                            </div>
                            <div class="col-md-3">
                                <label class="ds-label ds-tooltip-trigger" title="Payback Period: Number of years required to recover total investment = Total Investment / Annual Savings">Payback Period</label>
                                <input type="text" id="s7_roi_payback" class="ds-input" readonly style="background:var(--ds-surface-raised)">
                            </div>
                            <div class="col-md-3">
                                <label class="ds-label ds-tooltip-trigger" title="Annual Net Return on Investment (%): Annual net economic return percentage = ((Annual Savings - Total Investment) / Total Investment) * 100">ROI (%) <span class="text-xs text-muted font-normal">(Annual Net ROI)</span></label>
                                <input type="text" id="s7_roi_pct" class="ds-input" readonly style="background:var(--ds-surface-raised)">
                            </div>
                        </div>
                        <div class="mt-3 p-2 border rounded bg-light text-xs fw-bold d-flex align-items-center justify-content-between flex-wrap gap-2">
                            <div>
                                <span class="ds-tooltip-trigger" title="Annual Savings (ROI Verified): Total verified monetary savings per year">Annual Savings (ROI Verified): </span>
                                <span id="s7_dash_savings" class="text-success fs-6 fw-bold me-3">---</span>
                            </div>
                            <div>
                                <span class="ds-tooltip-trigger" title="Payback Period (Investment Recovery): Years required to recover total capital outlay">Payback Period (Investment Recovery): </span>
                                <span id="s7_dash_payback" class="text-info fs-6 fw-bold me-3">---</span>
                            </div>
                            <div>
                                <span class="ds-tooltip-trigger" title="Annual Net ROI = ((Annual Savings - Total Investment) / Total Investment) * 100">Annual Net ROI (%): </span>
                                <span id="s7_dash_roi_pct" class="text-primary fs-6 fw-bold">---</span>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section 6 - Sustainability Check -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">7.6</span>
                                <span class="ds-tooltip-trigger" title="Sustainability Check: Confirm improved performance holds steady over time without reverting">Sustainability Check</span>
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Confirm the improved performance is holding steady over time, not reverting.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary ds-tooltip-trigger" title="Section 6 - Sustainability Check: Auditing long-term performance stability">Section 6 - Sustainability Check</h6>
                            <button class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[7].addSustainRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Check
                            </button>
                        </div>
                        <div id="s7_sustainContainer" class="mb-0">
                            <div class="row text-muted small fw-bold mb-2 px-2">
                                <div class="col-4 ds-tooltip-trigger" title="Check Item: Inspection item or process parameter audited for stability">Check Item</div>
                                <div class="col-2 ds-tooltip-trigger" title="Auditor: Person conducting the sustainability audit">Auditor</div>
                                <div class="col-2 ds-tooltip-trigger" title="Result: Audit finding (e.g. Pass, Fail, Stable, Reverting)">Result</div>
                                <div class="col-3 ds-tooltip-trigger" title="Action Required: Corrective action taken if performance shows signs of reversion">Action Required</div>
                                <div class="col-1"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section 7 - Side Effect Verification -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">7.7</span>
                                <span class="ds-tooltip-trigger" title="Side Effect Verification: Confirm no new quality defects or operational issues were introduced">Side Effect Verification</span>
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Check whether any negative side effects flagged in Stage 5 actually materialized.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary ds-tooltip-trigger" title="Section 7 - Side Effect Verification: Post-improvement side effect audit">Section 7 - Side Effect Verification</h6>
                            <button class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[7].addSideEffectRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Verification
                            </button>
                        </div>
                        <div id="s7_sideEffectContainer" class="mb-0">
                            <div class="row text-muted small fw-bold mb-2 px-2">
                                <div class="col-4 ds-tooltip-trigger" title="Process Area: Workstation or shop floor area audited for secondary side effects">Process Area</div>
                                <div class="col-2 ds-tooltip-trigger" title="Negative Impact?: Status indicating whether any negative side effect occurred">Negative Impact?</div>
                                <div class="col-5 ds-tooltip-trigger" title="Details: Explanation of audit findings and corrective adjustments">Details</div>
                                <div class="col-1"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section 8 - Lessons Implementation -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">7.8</span>
                                <span class="ds-tooltip-trigger" title="Lessons Implementation: Documenting key insights and best practices for future projects">Lessons Implementation</span>
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Record what worked and what didn't during implementation for future reference.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary ds-tooltip-trigger" title="Section 8 - Lessons Learned from Implementation: Key technical and process takeaways">Section 8 - Lessons Learned from Implementation</h6>
                            <button class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[7].addLessonRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Lesson
                            </button>
                        </div>
                        <div id="s7_lessonContainer" class="mb-0">
                            <div class="row text-muted small fw-bold mb-2 px-2">
                                <div class="col-3 ds-tooltip-trigger" title="Category: Insight domain (e.g. Technical, Process, Governance, Training)">Category</div>
                                <div class="col-4 ds-tooltip-trigger" title="Lesson: Key takeaway or observation during execution">Lesson</div>
                                <div class="col-4 ds-tooltip-trigger" title="Actionable Insight: Concrete recommendation for future QC Circle projects">Actionable Insight</div>
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
        const d = wf.find(w => w.stage_id === 7)?.data || {};
        
        // Populate tables
        const tables = ['kpi', 'beforeAfter', 'stat', 'benefit', 'sustain', 'sideEffect', 'lesson'];
        tables.forEach(key => {
            const arr = d[this.getMap(key)] || [];
            const containerEl = document.getElementById(`s7_${key}Container`);
            if (containerEl) {
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

        // ROI values
        const roi = d.roi_validation || {};
        this.setVal('s7_roi_inv', roi.total_investment || '');
        this.setVal('s7_roi_sav', roi.annual_savings || '');
        this.calcROI();

        // Prefill Hist comparison
        const before_after_obj = d.before_vs_after_extended || {};
        this.setVal('s7_hist_after_values', before_after_obj.histogram_after_values || '');
        this.calcHistComparison();

        // Control chart readings
        const afterControl = before_after_obj.control_after_points || [];
        const ctrlContainer = document.getElementById('s7ControlPointsContainer');
        ctrlContainer.innerHTML = `
            <div class="row text-muted text-xs mb-1">
                <div class="col-5">Time/Date Label</div>
                <div class="col-5">Measured Value</div>
                <div class="col-2"></div>
            </div>
        `;
        if (afterControl.length) {
            afterControl.forEach(row => this.addControlRow(row));
        } else {
            this.addControlRow();
        }
        this.calcControlComparison();

        // Update Dashboard
        this.updateDashboard();

        const gate = d.approval_gate || {};
        this.setVal('s7_gate_verified_by', gate.verified_by);
        this.setVal('s7_gate_date', gate.date);
        this.setVal('s7_gate_status', gate.status);
        this.setVal('s7_gate_comments', gate.comments);

        if (window.lucide) lucide.createIcons();
    },

    collectData() {
        return {
            kpi_verification: this.collectRows('s7_kpiContainer', ['.r-met', '.r-base', '.r-tgt', '.r-act', '.r-var'], ['metric', 'baseline', 'target', 'actual', 'variance']),
            before_vs_after: this.collectRows('s7_beforeAfterContainer', ['.r-met', '.r-bef', '.r-aft', '.r-imp'], ['metric', 'before_condition', 'after_condition', 'improvement_pct']),
            statistical_validation: this.collectRows('s7_statContainer', ['.r-tst', '.r-pval', '.r-conc'], ['test_type', 'p_value', 'conclusion']),
            benefit_realization: this.collectRows('s7_benefitContainer', ['.r-cat', '.r-exp', '.r-act', '.r-var'], ['benefit_category', 'expected', 'actual', 'variance']),
            roi_validation: {
                total_investment: this.getVal('s7_roi_inv'),
                annual_savings: this.getVal('s7_roi_sav'),
                payback_period: this.getVal('s7_roi_payback'),
                roi_pct: this.getVal('s7_roi_pct')
            },
            sustainability_check: this.collectRows('s7_sustainContainer', ['.r-chk', '.r-aud', '.r-res', '.r-act'], ['check_item', 'auditor', 'result', 'action_required']),
            side_effect_verification: this.collectRows('s7_sideEffectContainer', ['.r-area', '.r-imp', '.r-det'], ['process_area', 'negative_impact', 'details']),
            lessons_implementation: this.collectRows('s7_lessonContainer', ['.r-cat', '.r-les', '.r-act'], ['category', 'lesson', 'actionable_insight']),
            
            // Custom extended field for before_vs_after comparisons to keep schema intact
            before_vs_after_extended: {
                histogram_after_values: this.getVal('s7_hist_after_values'),
                control_after_points: this.collectControlPoints()
            },
            
            approval_gate: {
                verified_by: this.getVal('s7_gate_verified_by'),
                date: this.getVal('s7_gate_date'),
                status: this.getVal('s7_gate_status'),
                comments: this.getVal('s7_gate_comments')
            }
        };
    },

    // Histogram Comparison Logic
    calcHistComparison() {
        let beforeVals = [];
        let beforeText = '';
        const s2Input = document.getElementById('s2_hist_values');
        if (s2Input && s2Input.value) {
            beforeText = s2Input.value;
        } else {
            const s2 = (this.projectData?.workflows || []).find(w => w.stage_id === 2)?.data || {};
            beforeText = (s2.data_collection || {}).histogram_values || (s2.histogram || {}).values || '';
            if (!beforeText && Array.isArray(s2.checksheet)) {
                beforeVals = s2.checksheet.map(x => parseFloat(x.count || x.value || x.val)).filter(v => !isNaN(v));
            }
        }
        if (!beforeVals.length && beforeText) {
            beforeVals = beforeText.split(',').map(v => parseFloat(v.trim())).filter(v => !isNaN(v));
        }

        if (!beforeVals.length) {
            const s4 = (this.projectData?.workflows || []).find(w => w.stage_id === 4)?.data || {};
            const s4pts = (s4.data_reconfirmation || {}).control_chart?.points || (s4.control_chart || {}).points || [];
            if (Array.isArray(s4pts)) {
                beforeVals = s4pts.map(p => parseFloat(typeof p === 'object' ? p.val : p)).filter(v => !isNaN(v));
            }
        }

        const afterText = this.getVal('s7_hist_after_values') || '';
        const afterVals = afterText.split(',').map(v => parseFloat(v.trim())).filter(v => !isNaN(v));

        const setStatText = (id, text) => {
            const el = document.getElementById(id);
            if (el) el.innerText = text;
        };

        if (beforeVals.length < 3 || afterVals.length < 3) {
            setStatText('s7_hist_sd_before', '---');
            setStatText('s7_hist_sd_after', '---');
            setStatText('s7_hist_var_reduction', 'Need min 3 values in both Stage 2 & 7');
            return;
        }

        // Before stats
        const meanBefore = beforeVals.reduce((a,b)=>a+b, 0)/beforeVals.length;
        const sdBefore = Math.sqrt(beforeVals.reduce((sum, v) => sum + Math.pow(v - meanBefore, 2), 0)/(beforeVals.length-1));

        // After stats
        const meanAfter = afterVals.reduce((a,b)=>a+b, 0)/afterVals.length;
        const sdAfter = Math.sqrt(afterVals.reduce((sum, v) => sum + Math.pow(v - meanAfter, 2), 0)/(afterVals.length-1));

        const varReduction = sdBefore > 0 ? ((sdBefore - sdAfter) / sdBefore * 100) : 0;

        setStatText('s7_hist_sd_before', sdBefore.toFixed(2));
        setStatText('s7_hist_sd_after', sdAfter.toFixed(2));
        setStatText('s7_hist_var_reduction', `Variation Reduction: ${varReduction.toFixed(1)}% ${varReduction > 0 ? '(Variation Reduced)' : ''}`);

        // Update dashboard quality improvement
        const qualDisplay = document.getElementById('s7_dash_quality');
        if (qualDisplay && varReduction > 0) {
            qualDisplay.innerText = varReduction.toFixed(1) + '%';
        }

        // Bin together
        const allVals = [...beforeVals, ...afterVals];
        const min = Math.min(...allVals);
        const max = Math.max(...allVals);
        const range = max - min;
        const numBins = 7;
        const binWidth = range === 0 ? 1 : range / numBins;

        const beforeBins = Array(numBins).fill(0);
        const afterBins = Array(numBins).fill(0);
        const labels = [];
        for (let i = 0; i < numBins; i++) {
            labels.push(`${(min + i * binWidth).toFixed(1)}-${(min + (i + 1) * binWidth).toFixed(1)}`);
        }

        beforeVals.forEach(v => {
            let idx = Math.floor((v - min) / binWidth);
            if (idx >= numBins) idx = numBins - 1;
            if (idx < 0) idx = 0;
            beforeBins[idx]++;
        });

        afterVals.forEach(v => {
            let idx = Math.floor((v - min) / binWidth);
            if (idx >= numBins) idx = numBins - 1;
            if (idx < 0) idx = 0;
            afterBins[idx]++;
        });

        const canvas = document.getElementById('s7HistogramComparisonCanvas');
        if (canvas) {
            if (window.s7HistChart) window.s7HistChart.destroy();
            const ctx = canvas.getContext('2d');
            window.s7HistChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Before (Stage 2)',
                            data: beforeBins,
                            backgroundColor: 'rgba(239, 68, 68, 0.5)',
                            borderColor: 'rgb(239, 68, 68)',
                            borderWidth: 1
                        },
                        {
                            label: 'After (Stage 7)',
                            data: afterBins,
                            backgroundColor: 'rgba(16, 185, 129, 0.5)',
                            borderColor: 'rgb(16, 185, 129)',
                            borderWidth: 1
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: { title: { display: true, text: 'Value Bins', font: { size: 9 } }, ticks: { font: { size: 8 } } },
                        y: { title: { display: true, text: 'Frequency', font: { size: 9 } }, ticks: { font: { size: 8 } } }
                    }
                }
            });
        }
    },

    // Control Chart Comparison Logic
    addControlRow(data = {}) {
        const c = document.getElementById('s7ControlPointsContainer');
        const r = document.createElement('div');
        r.className = 'row g-1 mb-1 align-items-center control-row dyn-sub-row';
        r.innerHTML = `
            <div class="col-5"><input type="text" class="ds-input py-1 px-2 text-xs ctrl-lbl" value="${data.label || ''}" placeholder="e.g. Day 11" oninput="StageModules[7].calcControlComparison()" onchange="StageModules[7].calcControlComparison()" required></div>
            <div class="col-5"><input type="number" step="any" class="ds-input py-1 px-2 text-xs ctrl-val" value="${data.val !== undefined ? data.val : ''}" oninput="StageModules[7].calcControlComparison()" onchange="StageModules[7].calcControlComparison()" required></div>
            <div class="col-2"><button type="button" class="ds-btn ds-btn-ghost text-danger p-1" onclick="this.closest('.control-row').remove(); StageModules[7].calcControlComparison()"><i data-lucide="trash-2" style="width:12px;"></i></button></div>
        `;
        c.appendChild(r);
        if (window.lucide) lucide.createIcons();
    },
    collectControlPoints() {
        const c = document.getElementById('s7ControlPointsContainer');
        if (!c) return [];
        return [...c.querySelectorAll('.control-row')].map(r => ({
            label: r.querySelector('.ctrl-lbl').value || 'Pt',
            val: parseFloat(r.querySelector('.ctrl-val').value)
        })).filter(pt => !isNaN(pt.val));
    },
    calcControlComparison() {
        let beforePoints = [];
        const s4Container = document.getElementById('s4ControlPointsContainer');
        if (s4Container) {
            beforePoints = [...s4Container.querySelectorAll('.control-row')].map(r => ({
                label: r.querySelector('.ctrl-lbl')?.value || 'Pt',
                val: parseFloat(r.querySelector('.ctrl-val')?.value)
            })).filter(pt => !isNaN(pt.val));
        }
        if (beforePoints.length === 0) {
            const s4 = (this.projectData?.workflows || []).find(w => w.stage_id === 4)?.data || {};
            beforePoints = (s4.data_reconfirmation || {}).control_chart?.points || [];
        }

        const afterPoints = this.collectControlPoints();

        const setLabelText = (id, text) => {
            const el = document.getElementById(id);
            if (el) el.innerText = text;
        };

        if (afterPoints.length === 0) {
            setLabelText('s7_ctrl_violations_before', '---');
            setLabelText('s7_ctrl_violations_after', '---');
            setLabelText('s7_ctrl_stability_imp', 'Need After data points');
            if (window.s7ControlChart) {
                window.s7ControlChart.destroy();
                window.s7ControlChart = null;
            }
            return;
        }

        // Before stats
        let meanBefore = 0, sdBefore = 0, uclBefore = 0, lclBefore = 0, violationsBefore = 0;
        const beforeVals = beforePoints.map(p => p.val);
        if (beforeVals.length > 0) {
            meanBefore = beforeVals.reduce((a,b)=>a+b, 0)/beforeVals.length;
            if (beforeVals.length > 1) {
                sdBefore = Math.sqrt(beforeVals.reduce((sum, v) => sum + Math.pow(v - meanBefore, 2), 0)/(beforeVals.length-1));
            }
            uclBefore = meanBefore + 3 * sdBefore;
            lclBefore = Math.max(0, meanBefore - 3 * sdBefore);
            beforeVals.forEach(v => { if (v > uclBefore || v < lclBefore) violationsBefore++; });
            setLabelText('s7_ctrl_violations_before', `${violationsBefore} points`);
        } else {
            setLabelText('s7_ctrl_violations_before', 'No Before Data');
        }

        // After stats
        let meanAfter = 0, sdAfter = 0, uclAfter = 0, lclAfter = 0, violationsAfter = 0;
        const afterVals = afterPoints.map(p => p.val);
        if (afterVals.length > 0) {
            meanAfter = afterVals.reduce((a,b)=>a+b, 0)/afterVals.length;
            if (afterVals.length > 1) {
                sdAfter = Math.sqrt(afterVals.reduce((sum, v) => sum + Math.pow(v - meanAfter, 2), 0)/(afterVals.length-1));
            }
            uclAfter = meanAfter + 3 * sdAfter;
            lclAfter = Math.max(0, meanAfter - 3 * sdAfter);
            afterVals.forEach(v => { if (v > uclAfter || v < lclAfter) violationsAfter++; });
            setLabelText('s7_ctrl_violations_after', `${violationsAfter} points`);
        } else {
            setLabelText('s7_ctrl_violations_after', 'No After Data');
        }

        if (beforeVals.length > 0 && afterVals.length > 0) {
            const imp = violationsBefore - violationsAfter;
            setLabelText('s7_ctrl_stability_imp', imp > 0 ? `Stability Improved (+${imp} points)` : (imp === 0 ? 'No change in stability' : 'Stability degraded'));
        } else {
            setLabelText('s7_ctrl_stability_imp', 'Cannot compare');
        }

        // Render sequential comparison
        const canvas = document.getElementById('s7ControlComparisonCanvas');
        if (canvas) {
            if (window.s7ControlChart) window.s7ControlChart.destroy();

            // Combined labels
            const labels = [...beforePoints.map(p => p.label || 'Before'), ...afterPoints.map(p => p.label || 'After')];
            const combinedVals = [...beforeVals, ...afterVals];

            // Setup step limits
            const uclLine = [
                ...Array(beforePoints.length).fill(beforeVals.length > 1 ? uclBefore : null),
                ...Array(afterPoints.length).fill(afterVals.length > 1 ? uclAfter : null)
            ];
            const clLine = [
                ...Array(beforePoints.length).fill(beforeVals.length > 0 ? meanBefore : null),
                ...Array(afterPoints.length).fill(afterVals.length > 0 ? meanAfter : null)
            ];
            const lclLine = [
                ...Array(beforePoints.length).fill(beforeVals.length > 1 ? lclBefore : null),
                ...Array(afterPoints.length).fill(afterVals.length > 1 ? lclAfter : null)
            ];

            const beforeColors = beforeVals.map(v => (beforeVals.length > 1 && (v > uclBefore || v < lclBefore)) ? 'rgb(239, 68, 68)' : 'rgb(59, 130, 246)');
            const afterColors = afterVals.map(v => (afterVals.length > 1 && (v > uclAfter || v < lclAfter)) ? 'rgb(239, 68, 68)' : 'rgb(16, 185, 129)');
            const pointColors = [...beforeColors, ...afterColors];

            const ctx = canvas.getContext('2d');
            window.s7ControlChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Observations',
                            data: combinedVals,
                            borderColor: 'rgba(156, 163, 175, 0.7)',
                            borderWidth: 1.5,
                            pointBackgroundColor: pointColors,
                            pointBorderColor: pointColors,
                            fill: false,
                            tension: 0.1
                        },
                        {
                            label: 'UCL (Upper Control Limit)',
                            data: uclLine,
                            borderColor: 'rgba(239, 68, 68, 0.7)',
                            borderDash: [4, 4],
                            pointRadius: 0,
                            fill: false
                        },
                        {
                            label: 'Center Line (Mean)',
                            data: clLine,
                            borderColor: 'rgba(59, 130, 246, 0.7)',
                            pointRadius: 0,
                            fill: false
                        },
                        {
                            label: 'LCL (Lower Control Limit)',
                            data: lclLine,
                            borderColor: 'rgba(239, 68, 68, 0.7)',
                            borderDash: [4, 4],
                            pointRadius: 0,
                            fill: false
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false }
                    },
                    scales: {
                        x: { ticks: { font: { size: 8 } } },
                        y: { ticks: { font: { size: 8 } } }
                    }
                }
            });
        }
    },

    // ROI Validation
    calcROI() {
        const inv = parseFloat(this.getVal('s7_roi_inv')) || 0;
        const sav = parseFloat(this.getVal('s7_roi_sav')) || 0;
        let roi = 0, pb = 0;
        if (inv > 0) {
            roi = ((sav - inv) / inv) * 100;
            pb = inv / sav; 
        }
        this.setVal('s7_roi_pct', inv > 0 ? roi.toFixed(1) + '%' : '');
        this.setVal('s7_roi_payback', sav > 0 ? pb.toFixed(1) + ' yrs' : '');

        // Update dashboard ROI and savings
        const savingsEl = document.getElementById('s7_dash_savings');
        if (savingsEl) {
            savingsEl.innerText = sav > 0 ? '₹' + sav.toLocaleString() : '---';
        }
        const paybackEl = document.getElementById('s7_dash_payback');
        if (paybackEl) {
            paybackEl.innerText = (sav > 0 && pb > 0) ? pb.toFixed(1) + ' yrs' : '---';
        }
        const roiPctEl = document.getElementById('s7_dash_roi_pct');
        if (roiPctEl) {
            roiPctEl.innerText = inv > 0 ? roi.toFixed(1) + '%' : '---';
        }
    },

    // Dashboard dynamic values
    updateDashboard() {
        // Compute KPI average achievement
        const kpis = this.collectRows('s7_kpiContainer', ['.r-met', '.r-base', '.r-tgt', '.r-act'], ['metric', 'baseline', 'target', 'actual']);
        let sumAch = 0, countAch = 0;
        kpis.forEach(k => {
            const base = parseFloat(k.baseline), tgt = parseFloat(k.target), act = parseFloat(k.actual);
            if (!isNaN(base) && !isNaN(tgt) && !isNaN(act)) {
                let ach = 0;
                if (tgt > base) {
                    ach = ((act - base) / (tgt - base)) * 100;
                } else if (base > tgt) {
                    ach = ((base - act) / (base - tgt)) * 100;
                }
                sumAch += Math.min(120, Math.max(0, ach)); // clamp 0-120
                countAch++;
            }
        });
        const kpiDisplay = document.getElementById('s7_dash_kpi');
        if (kpiDisplay) {
            kpiDisplay.innerText = countAch > 0 ? (sumAch / countAch).toFixed(1) + '%' : '---';
        }

        // Quality Improvement (before vs after table)
        const items = this.collectRows('s7_beforeAfterContainer', ['.r-met', '.r-imp'], ['metric', 'improvement_pct']);
        let sumImp = 0, countImp = 0;
        items.forEach(it => {
            const impVal = parseFloat(it.improvement_pct);
            if (!isNaN(impVal)) {
                sumImp += impVal;
                countImp++;
            }
        });
        const qualDisplay = document.getElementById('s7_dash_quality');
        if (qualDisplay) {
            qualDisplay.innerText = countImp > 0 ? (sumImp / countImp).toFixed(1) + '%' : '---';
        }
    },

    getMap(k) {
        return {
            'kpi': 'kpi_verification', 'beforeAfter': 'before_vs_after', 'stat': 'statistical_validation',
            'benefit': 'benefit_realization', 'sustain': 'sustainability_check', 'sideEffect': 'side_effect_verification',
            'lesson': 'lessons_implementation'
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

    addRowTemplate(containerId, data, html) {
        const c = document.getElementById(containerId);
        const r = document.createElement('div');
        r.className = 'row g-2 mb-2 align-items-center dyn-row';
        r.innerHTML = html + '<div class="col-1"><button class="ds-btn ds-btn-ghost text-danger p-1" onclick="this.closest(\'.dyn-row\').remove(); StageModules[7].updateDashboard();"><i data-lucide="trash-2" style="width:14px;"></i></button></div>';
        c.appendChild(r);
        if (window.lucide) lucide.createIcons();
    },

    addKpiRow(d = {}) {
        const calc = "const p=this.closest('.dyn-row'); if(p){ p.querySelector('.r-var').value = ((parseFloat(p.querySelector('.r-act').value)||0) - (parseFloat(p.querySelector('.r-tgt').value)||0)).toFixed(2); } StageModules[7].updateDashboard();";
        this.addRowTemplate('s7_kpiContainer', d, `
            <div class="col-3"><input type="text" class="ds-input r-met" placeholder="e.g. Crimp Defect Rate" value="${d.metric || ''}" required></div>
            <div class="col-2"><input type="number" step="any" class="ds-input r-base" placeholder="e.g. 4.2" value="${d.baseline || ''}" oninput="${calc}" onchange="${calc}" required></div>
            <div class="col-2"><input type="number" step="any" class="ds-input r-tgt" placeholder="e.g. 0.5" value="${d.target || ''}" oninput="${calc}" onchange="${calc}" required></div>
            <div class="col-2"><input type="number" step="any" class="ds-input r-act" placeholder="e.g. 0.3" value="${d.actual || ''}" oninput="${calc}" onchange="${calc}" required></div>
            <div class="col-2"><input type="number" step="any" class="ds-input r-var" readonly style="background:var(--ds-surface-raised)" value="${d.variance || ''}"></div>`);
    },
    addBeforeAfterRow(d = {}) {
        let initImp = (d.improvement_pct !== undefined && d.improvement_pct !== null && d.improvement_pct !== '') ? d.improvement_pct : '';
        if (!initImp && d.before_condition && d.after_condition) {
            const b = parseFloat(String(d.before_condition).replace(/[^0-9.-]/g, ''));
            const a = parseFloat(String(d.after_condition).replace(/[^0-9.-]/g, ''));
            if (!isNaN(b) && !isNaN(a) && b !== 0) {
                const p = ((b - a) / Math.abs(b)) * 100;
                initImp = Number.isInteger(p) ? p : p.toFixed(1);
            }
        }
        const calc = "const r=this.closest('.dyn-row'); if(r){ const b=parseFloat((r.querySelector('.r-bef').value||'').replace(/[^0-9.-]/g,'')); const a=parseFloat((r.querySelector('.r-aft').value||'').replace(/[^0-9.-]/g,'')); if(!isNaN(b)&&!isNaN(a)&&b!==0){ const p=((b-a)/Math.abs(b))*100; r.querySelector('.r-imp').value = Number.isInteger(p)?p:p.toFixed(1); } } StageModules[7].updateDashboard();";
        this.addRowTemplate('s7_beforeAfterContainer', d, `
            <div class="col-3"><input type="text" class="ds-input r-met" placeholder="e.g. Crimp Defect Rate" value="${d.metric || ''}" required></div>
            <div class="col-3"><input type="text" class="ds-input r-bef" placeholder="e.g. 4.2%" value="${d.before_condition || ''}" oninput="${calc}" required></div>
            <div class="col-3"><input type="text" class="ds-input r-aft" placeholder="e.g. 0.3%" value="${d.after_condition || ''}" oninput="${calc}" required></div>
            <div class="col-2"><input type="number" step="any" class="ds-input r-imp" value="${initImp}" onchange="StageModules[7].updateDashboard()" required></div>`);
    },
    addStatRow(d = {}) {
        this.addRowTemplate('s7_statContainer', d, `
            <div class="col-4"><input type="text" class="ds-input r-tst" placeholder="e.g. Two-Sample Proportion Test" value="${d.test_type || ''}" required></div>
            <div class="col-3"><input type="text" class="ds-input r-pval" placeholder="e.g. 0.0001" value="${d.p_value || ''}" required></div>
            <div class="col-4"><input type="text" class="ds-input r-conc" placeholder="e.g. Reject H0; defect rate reduction is significant" value="${d.conclusion || ''}" required></div>`);
    },
    addBenefitRow(d = {}) {
        const calc = "const p=this.closest('.dyn-row'); p.querySelector('.r-var').value = ((parseFloat(p.querySelector('.r-act').value)||0) - (parseFloat(p.querySelector('.r-exp').value)||0)).toFixed(2);";
        this.addRowTemplate('s7_benefitContainer', d, `
            <div class="col-4"><input type="text" class="ds-input r-cat" placeholder="e.g. Monthly rework and scrap savings" value="${d.benefit_category || ''}" required></div>
            <div class="col-2"><input type="number" class="ds-input r-exp" placeholder="e.g. 120000" value="${d.expected || ''}" onchange="${calc}" required></div>
            <div class="col-2"><input type="number" class="ds-input r-act" placeholder="e.g. 125000" value="${d.actual || ''}" onchange="${calc}" required></div>
            <div class="col-3"><input type="number" class="ds-input r-var" readonly style="background:var(--ds-surface-raised)" value="${d.variance || ''}"></div>`);
    },
    addSustainRow(d = {}) {
        this.addRowTemplate('s7_sustainContainer', d, `
            <div class="col-4"><input type="text" class="ds-input r-chk" placeholder="e.g. Monthly PM audit checklist" value="${d.check_item || ''}" required></div>
            <div class="col-2"><input type="text" class="ds-input r-aud" placeholder="e.g. Ravi Kumar" value="${d.auditor || ''}" required></div>
            <div class="col-2"><input type="text" class="ds-input r-res" placeholder="e.g. Fully compliant" value="${d.result || ''}" required></div>
            <div class="col-3"><input type="text" class="ds-input r-act" placeholder="e.g. None" value="${d.action_required || ''}"></div>`);
    },
    addSideEffectRow(d = {}) {
        this.addRowTemplate('s7_sideEffectContainer', d, `
            <div class="col-4"><input type="text" class="ds-input r-area" placeholder="e.g. Downstream cable assembly" value="${d.process_area || ''}" required></div>
            <div class="col-2">
                <select class="ds-input ds-select r-imp" required>
                    <option ${d.negative_impact==='Yes'?'selected':''}>Yes</option>
                    <option ${d.negative_impact==='No'?'selected':''}>No</option>
                </select>
            </div>
            <div class="col-5"><input type="text" class="ds-input r-det" placeholder="e.g. Cable fitting is smoother due to uniform crimp height" value="${d.details || ''}" required></div>`);
    },
    addLessonRow(d = {}) {
        this.addRowTemplate('s7_lessonContainer', d, `
            <div class="col-3"><input type="text" class="ds-input r-cat" placeholder="e.g. Preventive Maintenance" value="${d.category || ''}" required></div>
            <div class="col-4"><input type="text" class="ds-input r-les" placeholder="e.g. Weekly lubrication of crimping jaw extends die life" value="${d.lesson || ''}" required></div>
            <div class="col-4"><input type="text" class="ds-input r-act" placeholder="e.g. Standardize lubrication schedules in all shift plans" value="${d.actionable_insight || ''}" required></div>`);
    },

    downloadTemplate() {
        const headers = ["Histogram Reading Value", "Control Chart Date/Time", "Control Chart Measured Value"];
        const rows = [
            ["10.1", "Day 11", "14.0"],
            ["10.2", "Day 12", "14.2"],
            ["10.0", "Day 13", "13.8"],
            ["9.9", "Day 14", "14.1"],
            ["10.1", "Day 15", "13.9"]
        ];
        
        const csvContent = "data:text/csv;charset=utf-8," 
            + [headers, ...rows].map(e => e.map(val => `"${val.replace(/"/g, '""')}"`).join(",")).join("\n");
            
        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", "stage7_qc_tools_template.csv");
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

                const dataRows = rows.slice(1);
                const histValues = [];
                let ctrlPointsAdded = 0;

                // Clear existing control chart rows except the header
                const ctrlContainer = document.getElementById('s7ControlPointsContainer');
                if (ctrlContainer) {
                    ctrlContainer.innerHTML = `
                        <div class="row text-muted text-xs mb-1">
                            <div class="col-5">Time/Date Label</div>
                            <div class="col-5">Measured Value</div>
                            <div class="col-2"></div>
                        </div>
                    `;
                }

                dataRows.forEach(cells => {
                    // Check if row has any content
                    if (!cells.some(c => c && c.trim())) return; 

                    // Histogram Reading (Column 0)
                    if (cells[0] && cells[0].trim()) {
                        const val = parseFloat(cells[0]);
                        if (!isNaN(val)) {
                            histValues.push(val);
                        }
                    }

                    // Control Chart Point (Column 1 and 2)
                    if (cells[1] && cells[1].trim() && cells[2] && cells[2].trim()) {
                        const timeLabel = cells[1].trim();
                        const measuredVal = parseFloat(cells[2]);
                        if (!isNaN(measuredVal)) {
                            this.addControlRow({ label: timeLabel, val: measuredVal });
                            ctrlPointsAdded++;
                        }
                    }
                });

                let msgParts = [];

                if (histValues.length > 0) {
                    const textarea = document.getElementById('s7_hist_after_values');
                    if (textarea) {
                        textarea.value = histValues.join(', ');
                        this.calcHistComparison();
                    }
                    msgParts.push(`${histValues.length} Histogram Readings`);
                }

                if (ctrlPointsAdded > 0) {
                    this.calcControlComparison();
                    msgParts.push(`${ctrlPointsAdded} Control Chart Points`);
                }

                if (msgParts.length > 0) {
                    QCMS.toast(`Successfully imported: ${msgParts.join(' & ')}`, "success");
                } else {
                    QCMS.toast("No valid numerical data found in uploaded file.", "error");
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

    getVal(id) { return (document.getElementById(id) || {}).value || ''; },
    setVal(id, val) { const el = document.getElementById(id); if (el) el.value = val; }
};

window.StageModules = window.StageModules || {};
window.StageModules[7] = Stage7;
