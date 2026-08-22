const Stage3 = {
    projectData: null,

    renderHTML() {
        return `
            <!-- STAGE 3 FORM -->
            <div id="stage3Form">
                
                <div class="alert alert-info mb-4 shadow-sm" style="background:rgba(var(--ds-primary-rgb),.06); border-left:4px solid var(--ds-primary); border-radius: var(--radius-md);">
                    <h6 class="fw-bold mb-1 d-flex align-items-center gap-2" style="color:var(--ds-primary)">
                        <i data-lucide="info" style="width:16px;height:16px;"></i>Stage Purpose
                    </h6>
                    <p class="mb-0" style="font-size:0.85rem; color:var(--ds-text-secondary);">Identify all potential causes of the problem using brainstorming and structured Fishbone analysis. Prioritize using a Pareto Chart and verify suspect causes before proceeding to Root Cause Analysis.</p>
                </div>

                <!-- Section 1 - Brainstorming -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">3.1</span>
                                <span class="ds-tooltip-trigger" title="Brainstorming Session: Open team cause generation session capturing all potential causes">Brainstorming Session</span>
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Capture every potential cause the team raises before narrowing the list.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="row g-3 mb-4">
                            <div class="col-md-6">
                                <label class="ds-label ds-tooltip-trigger" title="Session Name: Title or topic of team brainstorming meeting">Session Name</label>
                                <input type="text" id="s3_bs_session" class="ds-input" required>
                            </div>
                            <div class="col-md-6">
                                <label class="ds-label ds-tooltip-trigger" title="Facilitator: Quality Leader facilitating brainstorming discussion">Facilitator</label>
                                <div class="position-relative" id="s3_bs_facilitator_wrapper">
                                    <input type="hidden" id="s3_bs_facilitator" style="display:none !important;" required>
                                    <div class="ds-input d-flex align-items-center justify-content-between cursor-pointer" id="s3_bs_facilitator_btn" style="background:#fff; min-height: 38px; border-radius: var(--radius-md); padding: 0.375rem 0.75rem;">
                                        <span id="s3_bs_facilitator_selected" class="text-muted text-sm">Select Facilitator...</span>
                                        <i data-lucide="chevron-down" style="width:16px;height:16px;" class="text-muted ms-2"></i>
                                    </div>
                                    <div class="dropdown-menu shadow-lg p-2 w-100" id="s3_bs_facilitator_menu" style="display:none; position:absolute; top:100%; left:0; z-index:1050; max-height:260px; overflow-y:auto; background:#fff; border-radius:10px; border:1px solid var(--ds-border-color);">
                                        <div class="mb-2 position-relative">
                                            <input type="text" class="form-control form-control-sm text-xs" id="s3_bs_facilitator_search" placeholder="🔍 Search facilitator..." style="padding-left: 8px;">
                                        </div>
                                        <div id="s3_bs_facilitator_list" class="list-group list-group-flush text-sm">
                                            <div class="text-muted text-xs p-2 text-center">Loading plant facilitators...</div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <label class="ds-label ds-tooltip-trigger" title="Participants: QC Circle team members participating in session">Participants</label>
                                <input type="text" id="s3_bs_participants" class="ds-input" placeholder="e.g. Ravi Kumar, Shubham Singh, Rajesh Kumar" required>
                            </div>
                            <div class="col-md-6">
                                <label class="ds-label ds-tooltip-trigger" title="Date: Date brainstorming session was conducted">Date</label>
                                <input type="date" id="s3_bs_date" class="ds-input" required>
                            </div>
                            <div class="col-12">
                                <label class="ds-label ds-tooltip-trigger" title="Notes: Summary discussion notes and focus areas from session">Notes</label>
                                <textarea id="s3_bs_notes" class="ds-input ds-textarea" rows="2" placeholder="e.g. Focus on Line A night shift crimping parameters and operator training gaps." required></textarea>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- QC Tool 4: Pareto Chart -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <h5 class="mb-0 fw-bold d-flex align-items-center gap-2 text-primary">
                            <i data-lucide="bar-chart-3" style="width:20px;height:20px;"></i>
                            QC Tool 4: Pareto Prioritization Chart
                        </h5>
                    </div>
                    <div class="ds-card-body p-4">
                        <div id="paretoAlertContainer"></div>
                        <div class="row align-items-center g-3">
                            <div class="col-md-7">
                                <div class="border p-3 rounded shadow-sm qc-tool-card" style="max-height: 280px; position: relative; background: var(--ds-bg-card, #ffffff);">
                                    <canvas id="s3ParetoCanvas" style="max-height: 250px; width: 100%;"></canvas>
                                </div>
                            </div>
                            <div class="col-md-5">
                                <div class="p-3 border rounded" style="border-radius: var(--radius-md); background: var(--ds-bg-subtle, #f8fafc);">
                                    <h6 class="fw-bold mb-2 text-primary d-flex align-items-center gap-1">
                                        <i data-lucide="shield-alert" style="width:16px;height:16px;"></i>
                                        Vital Few Top Causes (80% Line)
                                    </h6>
                                    <p class="text-xs text-muted mb-3">These causes represent 80% of the defects and are automatically set as default entries for the Fishbone Diagram.</p>
                                    <ul class="list-group list-group-flush text-sm" id="s3ParetoVitalFewList">
                                        <li class="list-group-item text-muted bg-transparent">No check sheet data available</li>
                                    </ul>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- QC Tool 5: Fishbone Diagram -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <h5 class="mb-0 fw-bold d-flex align-items-center gap-2 text-primary ds-tooltip-trigger" title="Ishikawa (Fishbone) 6M Diagram: Categorizing potential causes under Man, Machine, Material, Method, Measurement, Environment">
                            <i data-lucide="git-branch" style="width:20px;height:20px;transform: rotate(90deg);"></i>
                            QC Tool 5: Ishikawa (Fishbone) Diagram
                        </h5>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <label class="ds-label mb-0 ds-tooltip-trigger" title="Interactive Fishbone Visualization: Zoomable 6M Cause & Effect diagram">Interactive Fishbone Visualization</label>
                            <div class="d-flex align-items-center gap-1 bg-light border p-1 rounded-3">
                                <button type="button" class="ds-btn ds-btn-ghost p-1" style="height:28px;width:28px;" title="Zoom Out (-)" onclick="StageModules[3].zoomFishbone(-0.15)">
                                    <i data-lucide="minus" style="width:14px;height:14px;"></i>
                                </button>
                                <span class="badge bg-white text-dark border px-2 py-1" id="fishboneZoomBadge" style="font-size:0.75rem; min-width:45px; text-align:center;">100%</span>
                                <button type="button" class="ds-btn ds-btn-ghost p-1" style="height:28px;width:28px;" title="Zoom In (+)" onclick="StageModules[3].zoomFishbone(0.15)">
                                    <i data-lucide="plus" style="width:14px;height:14px;"></i>
                                </button>
                                <button type="button" class="ds-btn ds-btn-ghost p-1 text-secondary ms-1" style="height:28px;width:28px;" title="Reset Zoom" onclick="StageModules[3].resetFishboneZoom()">
                                    <i data-lucide="rotate-ccw" style="width:13px;height:13px;"></i>
                                </button>
                            </div>
                        </div>
                        
                        <!-- Visual Fishbone SVG -->
                        <div class="border p-3 rounded shadow-sm mb-4 qc-tool-card" style="overflow: auto; background: var(--ds-bg-card, #ffffff);">
                            <div id="fishboneSvgContainer" style="min-width: 1000px; position: relative; height: 420px; transform-origin: top left; transition: transform 0.2s ease-out;">
                                <svg id="fishboneSvg" viewBox="0 0 1100 440" width="100%" height="100%" style="font-family: inherit;">
                                    <defs>
                                        <marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                                            <path d="M 0 0 L 10 5 L 0 10 z" fill="#1e293b" />
                                        </marker>
                                    </defs>
                                    
                                    <!-- Main Spine -->
                                    <line x1="50" y1="220" x2="950" y2="220" stroke="#1e293b" stroke-width="4" marker-end="url(#arrow)" />
                                    
                                    <!-- Effect Head (Right Side) -->
                                    <rect x="950" y="170" width="140" height="100" rx="10" fill="rgba(30, 41, 59, 0.06)" stroke="#1e293b" stroke-width="2.5" />
                                    <text x="1020" y="195" text-anchor="middle" font-size="10" font-weight="bold" fill="#2563eb" letter-spacing="1">EFFECT (PROBLEM)</text>
                                    <text x="1020" y="222" text-anchor="middle" font-size="11" font-weight="bold" fill="#0f172a" id="fishboneEffectText">Problem Statement</text>
                                    
                                    <!-- Top Bones & Color-Coded Pill Badges -->
                                    <!-- Man Bone -->
                                    <line x1="130" y1="50" x2="230" y2="220" stroke="#475569" stroke-width="2" />
                                    <rect x="70" y="25" width="120" height="28" rx="6" fill="#3b82f6" />
                                    <text x="130" y="44" text-anchor="middle" font-size="11" font-weight="bold" fill="#ffffff">1. MAN</text>
                                    <g id="bone_Man"></g>
                                    
                                    <!-- Machine Bone -->
                                    <line x1="450" y1="50" x2="550" y2="220" stroke="#475569" stroke-width="2" />
                                    <rect x="385" y="25" width="130" height="28" rx="6" fill="#ca8a04" />
                                    <text x="450" y="44" text-anchor="middle" font-size="11" font-weight="bold" fill="#ffffff">2. MACHINE</text>
                                    <g id="bone_Machine"></g>
                                    
                                    <!-- Material Bone -->
                                    <line x1="770" y1="50" x2="870" y2="220" stroke="#475569" stroke-width="2" />
                                    <rect x="705" y="25" width="130" height="28" rx="6" fill="#16a34a" />
                                    <text x="770" y="44" text-anchor="middle" font-size="11" font-weight="bold" fill="#ffffff">3. MATERIAL</text>
                                    <g id="bone_Material"></g>
                                    
                                    <!-- Bottom Bones & Color-Coded Pill Badges -->
                                    <!-- Method Bone -->
                                    <line x1="130" y1="390" x2="230" y2="220" stroke="#475569" stroke-width="2" />
                                    <rect x="70" y="388" width="120" height="28" rx="6" fill="#db2777" />
                                    <text x="130" y="407" text-anchor="middle" font-size="11" font-weight="bold" fill="#ffffff">4. METHOD</text>
                                    <g id="bone_Method"></g>
                                    
                                    <!-- Measurement Bone -->
                                    <line x1="450" y1="390" x2="550" y2="220" stroke="#475569" stroke-width="2" />
                                    <rect x="385" y="388" width="135" height="28" rx="6" fill="#ea580c" />
                                    <text x="452" y="407" text-anchor="middle" font-size="11" font-weight="bold" fill="#ffffff">5. MEASUREMENT</text>
                                    <g id="bone_Measurement"></g>
                                    
                                    <!-- Environment Bone -->
                                    <line x1="770" y1="390" x2="870" y2="220" stroke="#475569" stroke-width="2" />
                                    <rect x="705" y="388" width="135" height="28" rx="6" fill="#0891b2" />
                                    <text x="772" y="407" text-anchor="middle" font-size="11" font-weight="bold" fill="#ffffff">6. ENVIRONMENT</text>
                                    <g id="bone_Environment"></g>
                                </svg>
                            </div>
                        </div>

                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary ds-tooltip-trigger" title="Detailed Causes List: Level 1 primary causes and Level 2 sub-causes">Detailed Causes List (Level 1 & 2)</h6>
                            <button class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[3].addFishboneRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Cause
                            </button>
                        </div>
                        
                        <div id="s3_fishboneContainer" class="mb-4">
                            <div class="row text-muted small fw-bold mb-2 px-2">
                                <div class="col-2 ds-tooltip-trigger" title="Category (6M): Man, Machine, Material, Method, Measurement, Environment">Category (6M)</div>
                                <div class="col-3 ds-tooltip-trigger" title="Cause (Level 1): Primary suspect cause factor">Cause (Level 1)</div>
                                <div class="col-3 ds-tooltip-trigger" title="Sub-Cause (Level 2): Detailed sub-cause factor contributing to primary cause">Sub-Cause (Level 2)</div>
                                <div class="col-2 ds-tooltip-trigger" title="Probability / Status: Likelihood rating (High, Medium, Low)">Probability / Status</div>
                                <div class="col-2 ds-tooltip-trigger" title="Actions: Row edit and delete controls">Actions</div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section 2 - Cause Register -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">3.2</span>
                                <span class="ds-tooltip-trigger" title="Cause Register: Master consolidated list of suspect causes for tracking">Cause Register</span>
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Consolidate the brainstormed causes into a single tracked list.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary ds-tooltip-trigger" title="Register Details: Master cause inventory tracking">Register Details</h6>
                            <button class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[3].addRegisterRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Register Entry
                            </button>
                        </div>
                        <div id="s3_registerContainer" class="mb-4">
                            <div class="row text-muted small fw-bold mb-2 px-2">
                                <div class="col-2 ds-tooltip-trigger" title="ID: Unique identifier tag for cause entry">ID</div>
                                <div class="col-2 ds-tooltip-trigger" title="Category: 6M category classification">Category</div>
                                <div class="col-4 ds-tooltip-trigger" title="Cause Description: Full description of suspect cause">Cause Description</div>
                                <div class="col-3 ds-tooltip-trigger" title="Origin: Brainstorming or Pareto source origin">Origin</div>
                                <div class="col-1"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section 3 - Cause Prioritization -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">3.3</span>
                                <span class="ds-tooltip-trigger" title="Cause Prioritization Matrix: Prioritizing causes using Impact (1-10) x Frequency (1-10) x Control (1-10)">Cause Prioritization Matrix</span>
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Score and rank the registered causes to decide which to verify first.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary ds-tooltip-trigger" title="Prioritization Ranks: Risk priority score evaluation">Prioritization Ranks</h6>
                            <button class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[3].addPrioritizationRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Cause to Rank
                            </button>
                        </div>
                        <div id="s3_priorityContainer" class="mb-4">
                            <div class="row text-muted small fw-bold mb-2 px-2">
                                <div class="col-3 ds-tooltip-trigger" title="Cause: Suspect cause description being evaluated">Cause</div>
                                <div class="col-2 ds-tooltip-trigger" title="Impact (1-10): Severity score of cause impact on defect (1=low, 10=critical)">Impact (1-10)</div>
                                <div class="col-2 ds-tooltip-trigger" title="Freq (1-10): Occurrence frequency score (1=rare, 10=continuous)">Freq (1-10)</div>
                                <div class="col-2 ds-tooltip-trigger" title="Control (1-10): Team ability to control or influence cause (1=no control, 10=full control)">Control (1-10)</div>
                                <div class="col-2 ds-tooltip-trigger" title="Total Score: Calculated risk priority score = Impact x Freq x Control">Total Score</div>
                                <div class="col-1"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section 4 - Cause Verification -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">3.4</span>
                                <span class="ds-tooltip-trigger" title="Cause Verification: Empirical testing protocol confirming whether suspect causes are true root causes">Cause Verification</span>
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Test the top-ranked causes against actual data to confirm which are real.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary ds-tooltip-trigger" title="Verification Checklist: Empirical test execution tracking">Verification Checklist</h6>
                            <button class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[3].addVerificationRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Verification
                            </button>
                        </div>
                        <div id="s3_verificationContainer" class="mb-4">
                            <div class="row text-muted small fw-bold mb-2 px-2">
                                <div class="col-2 ds-tooltip-trigger" title="Cause: Suspect cause undergoing empirical verification test">Cause</div>
                                <div class="col-2 ds-tooltip-trigger" title="Method: Verification testing protocol (e.g. Audit, Measurement, DOE)">Method</div>
                                <div class="col-3 ds-tooltip-trigger" title="Data Source: Log sheet, measurement gauge, or observation record">Data Source</div>
                                <div class="col-2 ds-tooltip-trigger" title="Result: Test observation and numerical result">Result</div>
                                <div class="col-2 ds-tooltip-trigger" title="Conclusion: Verification conclusion (True Cause vs Invalidated)">Conclusion</div>
                                <div class="col-1"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section 5 - Ishikawa (Fishbone) Diagram (Post-Verification) -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2 text-primary">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">3.5</span>
                                Ishikawa (Fishbone) Diagram (Post-Verification)
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Map the verified causes onto a Fishbone diagram grouped by category.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <label class="ds-label mb-0">Interactive Fishbone Visualization (Verified Causes)</label>
                            <div class="d-flex align-items-center gap-1 bg-light border p-1 rounded-3">
                                <button type="button" class="ds-btn ds-btn-ghost p-1" style="height:28px;width:28px;" title="Zoom Out (-)" onclick="StageModules[3].zoomFishboneL3(-0.15)">
                                    <i data-lucide="minus" style="width:14px;height:14px;"></i>
                                </button>
                                <span class="badge bg-white text-dark border px-2 py-1" id="fishboneL3ZoomBadge" style="font-size:0.75rem; min-width:45px; text-align:center;">100%</span>
                                <button type="button" class="ds-btn ds-btn-ghost p-1" style="height:28px;width:28px;" title="Zoom In (+)" onclick="StageModules[3].zoomFishboneL3(0.15)">
                                    <i data-lucide="plus" style="width:14px;height:14px;"></i>
                                </button>
                                <button type="button" class="ds-btn ds-btn-ghost p-1 text-secondary ms-1" style="height:28px;width:28px;" title="Reset Zoom" onclick="StageModules[3].resetFishboneL3Zoom()">
                                    <i data-lucide="rotate-ccw" style="width:13px;height:13px;"></i>
                                </button>
                            </div>
                        </div>
                        
                        <!-- Visual Fishbone SVG -->
                        <div class="border p-3 rounded shadow-sm mb-4 qc-tool-card" style="overflow: auto; background: var(--ds-bg-card, #ffffff);">
                            <div id="fishboneL3SvgContainer" style="min-width: 1000px; position: relative; height: 420px; transform-origin: top left; transition: transform 0.2s ease-out;">
                                <svg id="fishboneL3Svg" viewBox="0 0 1100 440" width="100%" height="100%" style="font-family: inherit;">
                                    <defs>
                                        <marker id="arrow_v2" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                                            <path d="M 0 0 L 10 5 L 0 10 z" fill="#1e293b" />
                                        </marker>
                                    </defs>
                                    
                                    <!-- Main Spine -->
                                    <line x1="50" y1="220" x2="950" y2="220" stroke="#1e293b" stroke-width="4" marker-end="url(#arrow_v2)" />
                                    
                                    <!-- Effect Head (Right Side) -->
                                    <rect x="950" y="170" width="140" height="100" rx="10" fill="rgba(30, 41, 59, 0.06)" stroke="#1e293b" stroke-width="2.5" />
                                    <text x="1020" y="195" text-anchor="middle" font-size="10" font-weight="bold" fill="#2563eb" letter-spacing="1">EFFECT (PROBLEM)</text>
                                    <text x="1020" y="222" text-anchor="middle" font-size="11" font-weight="bold" fill="#0f172a" id="fishboneEffectText_v2">Problem Statement</text>
                                    
                                    <!-- Top Bones & Color-Coded Pill Badges -->
                                    <!-- Man Bone -->
                                    <line x1="130" y1="50" x2="230" y2="220" stroke="#475569" stroke-width="2" />
                                    <rect x="70" y="25" width="120" height="28" rx="6" fill="#3b82f6" />
                                    <text x="130" y="44" text-anchor="middle" font-size="11" font-weight="bold" fill="#ffffff">1. MAN</text>
                                    <g id="bone_Man_v2"></g>
                                    
                                    <!-- Machine Bone -->
                                    <line x1="450" y1="50" x2="550" y2="220" stroke="#475569" stroke-width="2" />
                                    <rect x="385" y="25" width="130" height="28" rx="6" fill="#ca8a04" />
                                    <text x="450" y="44" text-anchor="middle" font-size="11" font-weight="bold" fill="#ffffff">2. MACHINE</text>
                                    <g id="bone_Machine_v2"></g>
                                    
                                    <!-- Material Bone -->
                                    <line x1="770" y1="50" x2="870" y2="220" stroke="#475569" stroke-width="2" />
                                    <rect x="705" y="25" width="130" height="28" rx="6" fill="#16a34a" />
                                    <text x="770" y="44" text-anchor="middle" font-size="11" font-weight="bold" fill="#ffffff">3. MATERIAL</text>
                                    <g id="bone_Material_v2"></g>
                                    
                                    <!-- Bottom Bones & Color-Coded Pill Badges -->
                                    <!-- Method Bone -->
                                    <line x1="130" y1="390" x2="230" y2="220" stroke="#475569" stroke-width="2" />
                                    <rect x="70" y="388" width="120" height="28" rx="6" fill="#db2777" />
                                    <text x="130" y="407" text-anchor="middle" font-size="11" font-weight="bold" fill="#ffffff">4. METHOD</text>
                                    <g id="bone_Method_v2"></g>
                                    
                                    <!-- Measurement Bone -->
                                    <line x1="450" y1="390" x2="550" y2="220" stroke="#475569" stroke-width="2" />
                                    <rect x="385" y="388" width="135" height="28" rx="6" fill="#ea580c" />
                                    <text x="452" y="407" text-anchor="middle" font-size="11" font-weight="bold" fill="#ffffff">5. MEASUREMENT</text>
                                    <g id="bone_Measurement_v2"></g>
                                    
                                    <!-- Environment Bone -->
                                    <line x1="770" y1="390" x2="870" y2="220" stroke="#475569" stroke-width="2" />
                                    <rect x="705" y="388" width="135" height="28" rx="6" fill="#0891b2" />
                                    <text x="772" y="407" text-anchor="middle" font-size="11" font-weight="bold" fill="#ffffff">6. ENVIRONMENT</text>
                                    <g id="bone_Environment_v2"></g>
                                </svg>
                            </div>
                        </div>

                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary">Detailed Causes List (Post-Verification)</h6>
                            <button class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[3].addFishboneL3Row()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Cause
                            </button>
                        </div>
                        
                        <div id="s3_fishboneL3Container" class="mb-4">
                            <div class="row text-muted small fw-bold mb-2 px-2">
                                <div class="col-2">Category (6M)</div>
                                <div class="col-3">Cause (Level 1)</div>
                                <div class="col-3">Sub-Cause (Level 2)</div>
                                <div class="col-2">Probability / Status</div>
                                <div class="col-2">Actions</div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section 6 - Fishbone Level 3 Summary -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <div>
                            <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                <span class="ds-icon-circle bg-primary-soft text-primary" style="width:32px;height:32px;font-size:.75rem;font-weight:700;">3.6</span>
                                Final Causes Summary (Level 3 Output)
                            </h5>
                            <p class="text-xs text-muted mb-0 mt-1 ms-1">Summarize the verified causes carried forward into Root Cause Analysis.</p>
                        </div>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="mb-0">
                            <label class="ds-label">Summary / Final Root Cause Output</label>
                            <textarea id="s3_fishbone_l3_summary" class="ds-input ds-textarea" rows="3" placeholder="Summarize the final identified root causes for the updated diagram" required></textarea>
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    init(projectData) {
        this.projectData = projectData;
        const wf = projectData.workflows || [];
        const d = wf.find(w => w.stage_id === 3)?.data || {};
        
        // Brainstorming
        const bs = d.brainstorming || {};
        this.setVal('s3_bs_session', bs.session_name);
        this.setVal('s3_bs_facilitator', bs.facilitator);
        this.setVal('s3_bs_participants', bs.participants);
        this.setVal('s3_bs_date', bs.date);
        this.setVal('s3_bs_notes', bs.notes);

        this.initFacilitatorDropdown(projectData, bs.facilitator);

        // Fetch Stage 1 Problem Statement for fishbone Effect Head
        const s1 = wf.find(w => w.stage_id === 1)?.data || {};
        const problemEffect = projectData.title || (s1.theme_target_schedule || {}).improvement_theme || 'Process Defects';
        const effectTextEl = document.getElementById('fishboneEffectText');
        if (effectTextEl) {
            effectTextEl.textContent = problemEffect.length > 18 ? problemEffect.substring(0, 16) + '...' : problemEffect;
        }

        // Load Pareto Chart and find Vital Few
        this.initPareto();

        // Fishbone L1 & L2
        const fb = d.fishbone_l2 || [];
        const fbContainer = document.getElementById('s3_fishboneContainer');
        fbContainer.innerHTML = `
            <div class="row text-muted small fw-bold mb-2 px-2">
                <div class="col-2">Category (6M)</div>
                <div class="col-3">Cause (Level 1)</div>
                <div class="col-3">Sub-Cause (Level 2)</div>
                <div class="col-2">Probability / Status</div>
                <div class="col-2">Actions</div>
            </div>
        `;

        if (fb.length) {
            fb.forEach(r => this.addFishboneRow(r));
        } else {
            // Auto pre-populate with Pareto Vital Few if table is empty
            const vitalFew = this.getVitalFewCauses();
            if (vitalFew.length) {
                const categories = ['Machine', 'Method', 'Man', 'Material', 'Measurement', 'Environment'];
                vitalFew.forEach((cause, idx) => {
                    this.addFishboneRow({
                        category: categories[idx % 6],
                        level1: cause,
                        level2: '',
                        status: 'Selected'
                    });
                });
            } else {
                this.addFishboneRow();
            }
        }
        this.drawVisualFishbone();

        // Register: Sync from Selected Fishbone causes
        const reg = d.cause_register || [];
        const fishboneRows = this.collectFishboneRows();
        const selectedFishboneRows = fishboneRows.filter(r => r.status === 'Selected' && r.level1 && r.level1.trim());

        if (selectedFishboneRows.length > 0) {
            this.syncCauseRegisterFromFishbone();
        } else {
            const regContainer = document.getElementById('s3_registerContainer');
            regContainer.innerHTML = `
                <div class="row text-muted small fw-bold mb-2 px-2">
                    <div class="col-2">ID</div>
                    <div class="col-2">Category</div>
                    <div class="col-4">Cause Description</div>
                    <div class="col-3">Origin / Sub-Cause</div>
                    <div class="col-1"></div>
                </div>
            `;
            if (reg.length) reg.forEach(r => this.addRegisterRow(r));
            else this.addRegisterRow();
        }

        // Prioritization & Verification: Always perform live sync from Cause Register!
        const prio = d.cause_prioritization || [];
        const ver = d.cause_verification || [];
        this.syncPrioritizationAndVerificationFromRegister(prio, ver);

        // L3 summary
        const l3 = d.fishbone_l3 || {};
        this.setVal('s3_fishbone_l3_summary', l3.summary);

        // Fishbone L3 (Post-Verification)
        const fb3 = l3.diagram_data || [];
        const fbL3Container = document.getElementById('s3_fishboneL3Container');
        if (fbL3Container) {
            fbL3Container.innerHTML = `
                <div class="row text-muted small fw-bold mb-2 px-2">
                    <div class="col-2">Category (6M)</div>
                    <div class="col-3">Cause (Level 1)</div>
                    <div class="col-3">Sub-Cause (Level 2)</div>
                    <div class="col-2">Probability / Status</div>
                    <div class="col-2">Actions</div>
                </div>
            `;
            if (fb3.length) {
                fb3.forEach(r => this.addFishboneL3Row(r));
            } else {
                // Pre-populate with first fishbone data (either all or verified ones)
                if (fb.length) {
                    fb.forEach(r => this.addFishboneL3Row(r));
                } else {
                    this.addFishboneL3Row();
                }
            }
            this.drawVisualFishboneL3();
        }

        const effectTextElV2 = document.getElementById('fishboneEffectText_v2');
        if (effectTextElV2) {
            effectTextElV2.textContent = problemEffect.length > 18 ? problemEffect.substring(0, 16) + '...' : problemEffect;
        }

        // Gate
        const gate = d.approval_gate || {};
        this.setVal('s3_gate_verified_by', gate.verified_by);
        this.setVal('s3_gate_date', gate.date);
        this.setVal('s3_gate_status', gate.status);
        this.setVal('s3_gate_comments', gate.comments);

        if (window.lucide) lucide.createIcons();
    },

    getVitalFewCauses() {
        const wf = this.projectData.workflows || [];
        const s2 = wf.find(w => w.stage_id === 2)?.data || {};
        const checkSheet = (s2.data_collection || {}).check_sheet || [];
        
        if (checkSheet.length === 0) return [];

        const sorted = [...checkSheet].sort((a, b) => b.count - a.count);
        const total = sorted.reduce((sum, item) => sum + item.count, 0);
        
        let cum = 0;
        const vitalFew = [];
        for (let i = 0; i < sorted.length; i++) {
            cum += sorted[i].count;
            vitalFew.push(sorted[i].category);
            if (total > 0 && (cum / total) >= 0.8) {
                break;
            }
        }
        return vitalFew;
    },

    initPareto() {
        const wf = this.projectData.workflows || [];
        const s2 = wf.find(w => w.stage_id === 2)?.data || {};
        const checkSheet = (s2.data_collection || {}).check_sheet || [];
        const alertContainer = document.getElementById('paretoAlertContainer');
        const vitalFewList = document.getElementById('s3ParetoVitalFewList');

        if (checkSheet.length === 0) {
            if (alertContainer) {
                alertContainer.innerHTML = `
                    <div class="alert alert-warning text-xs p-2 mb-3">
                        <i data-lucide="alert-triangle" style="width:14px;height:14px;margin-right:4px;"></i>
                        No Check Sheet tally records found in Stage 2. Defaulting to general categorization.
                    </div>
                `;
            }
            if (window.lucide) lucide.createIcons();
            return;
        }

        // Sort descending
        const sorted = [...checkSheet].sort((a, b) => b.count - a.count);
        const total = sorted.reduce((sum, item) => sum + item.count, 0);

        const labels = sorted.map(x => x.category);
        const counts = sorted.map(x => x.count);
        const cumulativePerc = [];
        
        let runningSum = 0;
        const vitalFew = [];
        let htmlList = '';

        sorted.forEach(item => {
            runningSum += item.count;
            const percentage = total > 0 ? (runningSum / total) * 100 : 0;
            cumulativePerc.push(percentage.toFixed(1));

            // Identify Vital Few (up to 80% line)
            const isVitalFew = total > 0 && ((runningSum - item.count) / total) < 0.8;
            if (isVitalFew) {
                vitalFew.push(item.category);
                htmlList += `
                    <li class="list-group-item d-flex justify-content-between align-items-center bg-transparent py-2 border-0 ps-0">
                        <span class="d-flex align-items-center gap-2 font-medium">
                            <span class="bullet bg-danger" style="width:6px;height:6px;border-radius:50%;"></span>
                            ${item.category}
                        </span>
                        <span class="badge rounded-pill bg-danger-soft text-danger fw-bold font-mono">${item.count} counts</span>
                    </li>
                `;
            }
        });

        if (vitalFewList) {
            vitalFewList.innerHTML = htmlList || `<li class="list-group-item text-muted bg-transparent">No critical factors found</li>`;
        }

        // Render Pareto Chart using Chart.js
        const canvas = document.getElementById('s3ParetoCanvas');
        if (canvas) {
            if (window.s3ParetoChart) window.s3ParetoChart.destroy();

            const ctx = canvas.getContext('2d');
            window.s3ParetoChart = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Defect Frequency (LHS)',
                            data: counts,
                            backgroundColor: 'rgba(239, 68, 68, 0.65)',
                            borderColor: 'rgb(239, 68, 68)',
                            borderWidth: 1.5,
                            yAxisID: 'y'
                        },
                        {
                            label: 'Cumulative % (RHS)',
                            data: cumulativePerc,
                            type: 'line',
                            borderColor: 'rgb(59, 130, 246)',
                            backgroundColor: 'rgb(59, 130, 246)',
                            borderWidth: 2,
                            fill: false,
                            tension: 0.1,
                            yAxisID: 'y1'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            type: 'linear',
                            position: 'left',
                            title: { display: true, text: 'Defect counts', font: { size: 10 } },
                            ticks: { font: { size: 9 } }
                        },
                        y1: {
                            type: 'linear',
                            position: 'right',
                            min: 0,
                            max: 100,
                            title: { display: true, text: 'Cumulative Percentage', font: { size: 10 } },
                            ticks: { callback: value => value + '%', font: { size: 9 } },
                            grid: { drawOnChartArea: false } // only show grid for LHS
                        },
                        x: {
                            ticks: { font: { size: 9 } },
                            grid: { display: false }
                        }
                    },
                    plugins: {
                        legend: { labels: { boxWidth: 12, font: { size: 10 } } },
                        annotation: {
                            annotations: {
                                line80: {
                                    type: 'line',
                                    yMin: 80,
                                    yMax: 80,
                                    yScaleID: 'y1',
                                    borderColor: 'rgba(239, 68, 68, 0.75)',
                                    borderWidth: 1.5,
                                    borderDash: [5, 5],
                                    label: {
                                        content: '80% Cutoff (Vital Few)',
                                        enabled: true,
                                        position: 'start',
                                        font: { size: 8, weight: 'bold' }
                                    }
                                }
                            }
                        }
                    }
                }
            });
        }
    },

    // ── Zoom Control Methods for Fishbone Diagrams ──
    zoomFishbone(delta) {
        this.fishboneZoomLevel = (this.fishboneZoomLevel || 1.0) + delta;
        if (this.fishboneZoomLevel < 0.5) this.fishboneZoomLevel = 0.5;
        if (this.fishboneZoomLevel > 2.5) this.fishboneZoomLevel = 2.5;

        const container = document.getElementById('fishboneSvgContainer');
        const badge = document.getElementById('fishboneZoomBadge');
        if (container) {
            container.style.transform = `scale(${this.fishboneZoomLevel})`;
        }
        if (badge) {
            badge.textContent = `${Math.round(this.fishboneZoomLevel * 100)}%`;
        }
    },

    resetFishboneZoom() {
        this.fishboneZoomLevel = 1.0;
        const container = document.getElementById('fishboneSvgContainer');
        const badge = document.getElementById('fishboneZoomBadge');
        if (container) {
            container.style.transform = `scale(1.0)`;
        }
        if (badge) {
            badge.textContent = `100%`;
        }
    },

    zoomFishboneL3(delta) {
        this.fishboneL3ZoomLevel = (this.fishboneL3ZoomLevel || 1.0) + delta;
        if (this.fishboneL3ZoomLevel < 0.5) this.fishboneL3ZoomLevel = 0.5;
        if (this.fishboneL3ZoomLevel > 2.5) this.fishboneL3ZoomLevel = 2.5;

        const container = document.getElementById('fishboneL3SvgContainer');
        const badge = document.getElementById('fishboneL3ZoomBadge');
        if (container) {
            container.style.transform = `scale(${this.fishboneL3ZoomLevel})`;
        }
        if (badge) {
            badge.textContent = `${Math.round(this.fishboneL3ZoomLevel * 100)}%`;
        }
    },

    resetFishboneL3Zoom() {
        this.fishboneL3ZoomLevel = 1.0;
        const container = document.getElementById('fishboneL3SvgContainer');
        const badge = document.getElementById('fishboneL3ZoomBadge');
        if (container) {
            container.style.transform = `scale(1.0)`;
        }
        if (badge) {
            badge.textContent = `100%`;
        }
    },

    // Fishbone dynamic drawing
    drawVisualFishbone() {
        const rows = this.collectFishboneRows();
        
        // Group by category
        const groups = { Man: [], Machine: [], Material: [], Method: [], Measurement: [], Environment: [] };
        rows.forEach(r => {
            if (groups[r.category]) groups[r.category].push(r);
        });

        // Bone configuration parameters (xOffset, yBranch, textSide)
        const boneConfigs = {
            Man: { x1: 160, y1: 60, x2: 230, y2: 175, direction: 'down-right' },
            Machine: { x1: 330, y1: 60, x2: 400, y2: 175, direction: 'down-right' },
            Material: { x1: 500, y1: 60, x2: 570, y2: 175, direction: 'down-right' },
            Method: { x1: 160, y1: 290, x2: 230, y2: 175, direction: 'up-right' },
            Measurement: { x1: 330, y1: 290, x2: 400, y2: 175, direction: 'up-right' },
            Environment: { x1: 500, y1: 290, x2: 570, y2: 175, direction: 'up-right' }
        };

        for (const [cat, config] of Object.entries(boneConfigs)) {
            const g = document.getElementById(`bone_${cat}`);
            if (!g) continue;
            g.innerHTML = '';

            const causes = groups[cat] || [];
            causes.forEach((cause, idx) => {
                if (idx >= 3) return; // render max 3 branches visually to fit

                // Calculate branching position on diagonal bone
                const t = (idx + 1) / 4; // space out at 0.25, 0.50, 0.75
                const bx = config.x1 + t * (config.x2 - config.x1);
                const by = config.y1 + t * (config.y2 - config.y1);

                // Horizontal line parameters
                const lineLen = cause.level2 ? 65 : 50;
                const lx1 = bx - lineLen;
                const ly = by;

                // Create SVG elements
                const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
                line.setAttribute("x1", lx1);
                line.setAttribute("y1", ly);
                line.setAttribute("x2", bx);
                line.setAttribute("y2", ly);
                line.setAttribute("stroke", "#9ca3af");
                line.setAttribute("stroke-width", "1");
                g.appendChild(line);

                const label1 = cause.level1.length > 18 ? cause.level1.substring(0, 16) + '...' : cause.level1;
                const txt = document.createElementNS("http://www.w3.org/2000/svg", "text");
                txt.setAttribute("x", lx1 - 4);
                txt.setAttribute("y", ly + 3);
                txt.setAttribute("text-anchor", "end");
                txt.setAttribute("font-size", "8");
                txt.setAttribute("fill", "#374151");
                txt.textContent = label1;
                g.appendChild(txt);

                if (cause.level2) {
                    const isTop = config.direction.startsWith('down');
                    const subX = lx1 + 25;
                    const subY = isTop ? ly - 15 : ly + 15;
                    const subX2 = subX - 15;

                    const subLine = document.createElementNS("http://www.w3.org/2000/svg", "line");
                    subLine.setAttribute("x1", subX);
                    subLine.setAttribute("y1", ly);
                    subLine.setAttribute("x2", subX2);
                    subLine.setAttribute("y2", subY);
                    subLine.setAttribute("stroke", "#9ca3af");
                    subLine.setAttribute("stroke-width", "1");
                    g.appendChild(subLine);

                    const label2 = cause.level2.length > 18 ? cause.level2.substring(0, 16) + '...' : cause.level2;
                    const subTxt = document.createElementNS("http://www.w3.org/2000/svg", "text");
                    subTxt.setAttribute("x", subX2 - 4);
                    subTxt.setAttribute("y", subY + (isTop ? 2 : 7));
                    subTxt.setAttribute("text-anchor", "end");
                    subTxt.setAttribute("font-size", "7");
                    subTxt.setAttribute("fill", "#6b7280");
                    subTxt.textContent = label2;
                    g.appendChild(subTxt);
                }
            });
        }
    },

    collectData() {
        return {
            brainstorming: {
                session_name: this.getVal('s3_bs_session'),
                facilitator: this.getVal('s3_bs_facilitator'),
                participants: this.getVal('s3_bs_participants'),
                date: this.getVal('s3_bs_date'),
                notes: this.getVal('s3_bs_notes')
            },
            fishbone_l1: this.collectFishboneRows(),
            fishbone_l2: this.collectFishboneRows(),
            cause_register: this.collectRegisterRows(),
            cause_prioritization: this.collectPrioritizationRows(),
            cause_verification: this.collectVerificationRows(),
            fishbone_l3: {
                summary: this.getVal('s3_fishbone_l3_summary'),
                diagram_data: this.collectFishboneL3Rows()
            },
            approval_gate: {
                verified_by: this.getVal('s3_gate_verified_by'),
                date: this.getVal('s3_gate_date'),
                status: this.getVal('s3_gate_status'),
                comments: this.getVal('s3_gate_comments')
            }
        };
    },

    splitTextIntoTwoLines(str, maxLen = 18) {
        if (!str) return [];
        const text = String(str).trim().substring(0, 35);
        if (text.length <= maxLen) return [text];

        let splitIdx = text.lastIndexOf(' ', maxLen);
        if (splitIdx <= 0 || splitIdx < 5) {
            splitIdx = maxLen;
        }

        const line1 = text.substring(0, splitIdx).trim();
        const line2 = text.substring(splitIdx).trim().substring(0, 18);
        return [line1, line2];
    },

    escapeHtml(str) {
        if (!str) return '';
        return String(str).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    },

    addFishboneRow(data = {}) {
        const c = document.getElementById('s3_fishboneContainer');
        const r = document.createElement('div');
        r.className = 'row g-2 mb-2 align-items-center dyn-row';
        r.innerHTML = `
            <div class="col-2">
                <select class="ds-input ds-select r-cat" onchange="StageModules[3].drawVisualFishbone()" required>
                    ${['Man','Machine','Method','Material','Measurement','Environment'].map(x => `<option ${data.category===x?'selected':''}>${x}</option>`).join('')}
                </select>
            </div>
            <div class="col-3"><input type="text" class="ds-input r-l1" placeholder="e.g. Die wear" value="${data.level1 || ''}" onchange="StageModules[3].drawVisualFishbone()" oninput="StageModules[3].drawVisualFishbone()" required></div>
            <div class="col-3"><input type="text" class="ds-input r-l2" placeholder="e.g. PM overdue by 2 weeks" value="${data.level2 || ''}" maxlength="35" onchange="StageModules[3].drawVisualFishbone()" oninput="StageModules[3].drawVisualFishbone()" required></div>
            <div class="col-2">
                <select class="ds-input ds-select r-stat" onchange="StageModules[3].drawVisualFishbone()" required>
                    <option value="Selected" ${data.status==='Selected'?'selected':''}>Selected</option>
                    <option value="Rejected" ${data.status==='Rejected'?'selected':''}>Rejected</option>
                </select>
            </div>
            <div class="col-2 d-flex align-items-center gap-1">
                <button type="button" class="ds-btn ds-btn-outline ds-btn-xs text-primary" style="font-size:0.7rem; padding: 0.2rem 0.4rem; white-space: nowrap;" title="Add another sub-cause for this cause" onclick="StageModules[3].addSubCauseRow(this)">+ Sub-Cause</button>
                <button type="button" class="ds-btn ds-btn-ghost text-danger p-1" onclick="this.closest('.dyn-row').remove(); StageModules[3].drawVisualFishbone()"><i data-lucide="trash-2" style="width:14px;"></i></button>
            </div>`;
        c.appendChild(r);
        if (window.lucide) lucide.createIcons();
    },

    addSubCauseRow(btn) {
        const parentRow = btn ? btn.closest('.dyn-row') : null;
        const category = parentRow ? (parentRow.querySelector('.r-cat')?.value || 'Man') : 'Man';
        const level1 = parentRow ? (parentRow.querySelector('.r-l1')?.value || '') : '';
        
        const container = document.getElementById('s3_fishboneContainer');
        if (!container) return;

        const r = document.createElement('div');
        r.className = 'row g-2 mb-2 align-items-center dyn-row';
        r.innerHTML = `
            <div class="col-2">
                <select class="ds-input ds-select r-cat" onchange="StageModules[3].drawVisualFishbone()" required>
                    ${['Man','Machine','Method','Material','Measurement','Environment'].map(x => `<option ${category===x?'selected':''}>${x}</option>`).join('')}
                </select>
            </div>
            <div class="col-3"><input type="text" class="ds-input r-l1" placeholder="e.g. Die wear" value="${this.escapeHtml(level1)}" onchange="StageModules[3].drawVisualFishbone()" oninput="StageModules[3].drawVisualFishbone()" required></div>
            <div class="col-3"><input type="text" class="ds-input r-l2" placeholder="e.g. PM overdue by 2 weeks" value="" maxlength="35" onchange="StageModules[3].drawVisualFishbone()" oninput="StageModules[3].drawVisualFishbone()" required></div>
            <div class="col-2">
                <select class="ds-input ds-select r-stat" onchange="StageModules[3].drawVisualFishbone()" required>
                    <option value="Selected" selected>Selected</option>
                    <option value="Rejected">Rejected</option>
                </select>
            </div>
            <div class="col-2 d-flex align-items-center gap-1">
                <button type="button" class="ds-btn ds-btn-outline ds-btn-xs text-primary" style="font-size:0.7rem; padding: 0.2rem 0.4rem; white-space: nowrap;" title="Add another sub-cause for this cause" onclick="StageModules[3].addSubCauseRow(this)">+ Sub-Cause</button>
                <button type="button" class="ds-btn ds-btn-ghost text-danger p-1" onclick="this.closest('.dyn-row').remove(); StageModules[3].drawVisualFishbone()"><i data-lucide="trash-2" style="width:14px;"></i></button>
            </div>`;
        
        if (parentRow && parentRow.nextSibling) {
            container.insertBefore(r, parentRow.nextSibling);
        } else {
            container.appendChild(r);
        }
        if (window.lucide) lucide.createIcons();
        const inputL2 = r.querySelector('.r-l2');
        if (inputL2) inputL2.focus();
        this.drawVisualFishbone();
    },

    collectFishboneRows() {
        const container = document.getElementById('s3_fishboneContainer');
        if (!container) return [];
        return [...container.querySelectorAll('.dyn-row')].map(r => ({
            category: r.querySelector('.r-cat').value,
            level1: r.querySelector('.r-l1').value,
            level2: r.querySelector('.r-l2').value,
            status: r.querySelector('.r-stat').value
        })).filter(x => x.level1);
    },

    // Fishbone dynamic drawing with clean non-overlapping hierarchy
    drawVisualFishbone() {
        const rows = this.collectFishboneRows();
        const categories = ['Man', 'Machine', 'Material', 'Method', 'Measurement', 'Environment'];
        const boneConfigs = {
            Man:         { x1: 130, y1: 50,  x2: 230, y2: 220, isTop: true  },
            Machine:     { x1: 450, y1: 50,  x2: 550, y2: 220, isTop: true  },
            Material:    { x1: 770, y1: 50,  x2: 870, y2: 220, isTop: true  },
            Method:      { x1: 130, y1: 390, x2: 230, y2: 220, isTop: false },
            Measurement: { x1: 450, y1: 390, x2: 550, y2: 220, isTop: false },
            Environment: { x1: 770, y1: 390, x2: 870, y2: 220, isTop: false }
        };

        categories.forEach(cat => {
            const g = document.getElementById(`bone_${cat}`);
            if (!g) return;
            g.innerHTML = '';

            const catRows = rows.filter(r => r.category === cat && r.level1 && r.level1.trim());
            if (catRows.length === 0) return;

            // Group sub-causes by Level 1 cause name
            const causeMap = new Map();
            catRows.forEach(r => {
                const key = r.level1.trim();
                if (!causeMap.has(key)) {
                    causeMap.set(key, []);
                }
                if (r.level2 && r.level2.trim()) {
                    causeMap.get(key).push(r.level2.trim());
                }
            });

            const causeEntries = Array.from(causeMap.entries());
            const config = boneConfigs[cat];
            const { x1, y1, x2, y2, isTop } = config;

            // Clamp Y ranges: top bones [82..185], bottom bones [255..358]
            const minY = isTop ? 82 : 255;
            const maxY = isTop ? 185 : 358;
            const boneRange = maxY - minY; // 103px

            const zonePerCause = causeEntries.map(([, subs]) => subs.length > 0 ? 55 : 35);
            const totalNeeded = zonePerCause.reduce((a, b) => a + b, 0);
            const scale = totalNeeded > boneRange ? (boneRange / totalNeeded) : 1.0;
            const scaledZones = zonePerCause.map(z => z * scale);

            // Position causes from badge end toward spine end
            let curY = isTop ? minY : maxY;
            const causeYs = causeEntries.map((_, i) => {
                const ly = curY;
                curY = isTop ? (curY + scaledZones[i]) : (curY - scaledZones[i]);
                return Math.max(minY, Math.min(maxY, ly));
            });

            causeEntries.forEach(([level1Name, subCauses], cIdx) => {
                if (cIdx >= 4) return;
                const ly = causeYs[cIdx];
                const t = (ly - y1) / (y2 - y1);
                const bx = x1 + t * (x2 - x1);
                const lineLen = 100;
                const lx1 = bx - lineLen;

                // Horizontal Level 1 Cause line
                const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
                line.setAttribute("x1", lx1);
                line.setAttribute("y1", ly);
                line.setAttribute("x2", bx);
                line.setAttribute("y2", ly);
                line.setAttribute("stroke", "#334155");
                line.setAttribute("stroke-width", "1.5");
                g.appendChild(line);

                // Level 1 end node dot ●
                const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
                dot.setAttribute("cx", lx1);
                dot.setAttribute("cy", ly);
                dot.setAttribute("r", "3.5");
                dot.setAttribute("fill", "#1e293b");
                g.appendChild(dot);

                // Level 1 label: ABOVE line for top bones, BELOW line for bottom bones
                const label1 = level1Name.length > 18 ? level1Name.substring(0, 16) + '...' : level1Name;
                const txt = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                txt.setAttribute('x', lx1 - 5);
                txt.setAttribute('y', isTop ? (ly - 5) : (ly + 12));
                txt.setAttribute('text-anchor', 'end');
                txt.setAttribute('font-size', '8.5');
                txt.setAttribute('font-weight', 'bold');
                txt.setAttribute('fill', '#0f172a');
                txt.textContent = label1;
                g.appendChild(txt);                // Sub-causes: branch lines terminating in interactive node point dots ● (hover for details, no text overlap)
                const validSubCauses = (subCauses || []).map(s => String(s).trim()).filter(Boolean);
                if (validSubCauses.length > 0) {
                    if (window.fbTipInit) window.fbTipInit();
                    const totalCount = validSubCauses.length;
                    const startMargin = 15;
                    const endMargin = 15;
                    const lineLen = 100;
                    const usableLength = Math.max(lineLen - startMargin - endMargin, 30);
                    const step = totalCount > 1 ? usableLength / (totalCount - 1) : usableLength / 2;

                    validSubCauses.forEach((fullText, sIdx) => {
                        // Calculate attachment point along horizontal line
                        const subX1 = (totalCount === 1)
                            ? bx - startMargin - (usableLength / 2)
                            : bx - startMargin - (sIdx * step);
                        const subOffset = Math.max(14, 20 - (totalCount > 4 ? (totalCount - 4) * 1.5 : 0));
                        const subY = isTop ? (ly + subOffset) : (ly - subOffset);
                        // Calculate subX2 so the sub-branch line is EXACTLY PARALLEL to the main category diagonal spine
                        const slopeRatio = 10 / 17; // dx/dy slope of main category spine
                        const subX2 = Math.round(subX1 + slopeRatio * subOffset);

                        const subGrp = document.createElementNS('http://www.w3.org/2000/svg', 'g');
                        subGrp.setAttribute('style', 'cursor:pointer');
                        subGrp.addEventListener('mouseover', (e) => window.fbTipShow && window.fbTipShow(fullText, e));
                        subGrp.addEventListener('mouseout',  ()  => window.fbTipHide && window.fbTipHide());

                        // Invisible expanded hover hit line
                        const hitLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                        hitLine.setAttribute('x1', subX1); hitLine.setAttribute('y1', ly);
                        hitLine.setAttribute('x2', subX2); hitLine.setAttribute('y2', subY);
                        hitLine.setAttribute('stroke', 'transparent'); hitLine.setAttribute('stroke-width', '10');
                        subGrp.appendChild(hitLine);

                        // Visible branch line
                        const subLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                        subLine.setAttribute('x1', subX1); subLine.setAttribute('y1', ly);
                        subLine.setAttribute('x2', subX2); subLine.setAttribute('y2', subY);
                        subLine.setAttribute('stroke', '#94a3b8'); subLine.setAttribute('stroke-width', '1.2');
                        subGrp.appendChild(subLine);

                        // Node point dot ●
                        const subDot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                        subDot.setAttribute('cx', subX2); subDot.setAttribute('cy', subY);
                        subDot.setAttribute('r', '3.5');
                        subDot.setAttribute('fill', '#334155');
                        subDot.setAttribute('stroke', '#ffffff');
                        subDot.setAttribute('stroke-width', '1');
                        subGrp.appendChild(subDot);

                        g.appendChild(subGrp);
                    });
                }
            });
        });

        this.syncCauseRegisterFromFishbone();
    },

    syncCauseRegisterFromFishbone() {
        const regContainer = document.getElementById('s3_registerContainer');
        if (!regContainer) return;

        const fishboneRows = this.collectFishboneRows();
        const selectedRows = fishboneRows.filter(r => r.status === 'Selected' && r.level1 && r.level1.trim());

        const headerHtml = `
            <div class="row text-muted small fw-bold mb-2 px-2">
                <div class="col-2">ID</div>
                <div class="col-2">Category</div>
                <div class="col-4">Cause Description</div>
                <div class="col-3">Origin / Sub-Cause</div>
                <div class="col-1"></div>
            </div>
        `;

        if (selectedRows.length === 0) {
            return;
        }

        regContainer.innerHTML = headerHtml;
        selectedRows.forEach((r, idx) => {
            const rowId = `C-${String(idx + 1).padStart(2, '0')}`;
            this.addRegisterRow({
                id: rowId,
                category: r.category,
                description: r.level1,
                origin: r.level2 || 'Brainstorming'
            });
        });

        this.syncPrioritizationAndVerificationFromRegister();
    },

    syncPrioritizationAndVerificationFromRegister(initialPrio = null, initialVer = null) {
        const regRows = this.collectRegisterRows();
        const causeList = regRows.map(r => {
            const desc = (r.description || '').trim();
            const orig = (r.origin || '').trim();
            if (orig && orig !== 'Brainstorming') {
                return `${desc} - ${orig}`;
            }
            return desc;
        }).filter(Boolean);

        if (causeList.length === 0) return;

        // 1. Sync Prioritization Matrix
        const prioContainer = document.getElementById('s3_priorityContainer');
        if (prioContainer) {
            const existingPrio = (initialPrio && initialPrio.length) ? initialPrio : this.collectPrioritizationRows();
            const findPrio = (causeName) => {
                let match = existingPrio.find(p => p.cause && p.cause.trim() === causeName);
                if (match) return match;
                const baseDesc = causeName.split(' - ')[0].trim();
                return existingPrio.find(p => p.cause && (causeName.includes(p.cause.trim()) || p.cause.trim().includes(baseDesc)));
            };

            const headerHtml = `
                <div class="row text-muted small fw-bold mb-2 px-2">
                    <div class="col-3">Cause</div>
                    <div class="col-2">Impact (1-10)</div>
                    <div class="col-2">Freq (1-10)</div>
                    <div class="col-2">Control (1-10)</div>
                    <div class="col-2">Total Score</div>
                    <div class="col-1"></div>
                </div>
            `;

            prioContainer.innerHTML = headerHtml;
            causeList.forEach(cause => {
                const existing = findPrio(cause);
                this.addPrioritizationRow({
                    cause: cause,
                    impact: existing ? existing.impact : '',
                    frequency: existing ? existing.frequency : '',
                    control: existing ? existing.control : '',
                    total: existing ? existing.total : ''
                });
            });
        }

        // 2. Sync Verification Checklist
        const verContainer = document.getElementById('s3_verificationContainer');
        if (verContainer) {
            const existingVer = (initialVer && initialVer.length) ? initialVer : this.collectVerificationRows();
            const findVer = (causeName) => {
                let match = existingVer.find(v => v.cause && v.cause.trim() === causeName);
                if (match) return match;
                const baseDesc = causeName.split(' - ')[0].trim();
                return existingVer.find(v => v.cause && (causeName.includes(v.cause.trim()) || v.cause.trim().includes(baseDesc)));
            };

            const headerHtml = `
                <div class="row text-muted small fw-bold mb-2 px-2">
                    <div class="col-2">Cause</div>
                    <div class="col-2">Method</div>
                    <div class="col-3">Data Source</div>
                    <div class="col-2">Result</div>
                    <div class="col-2">Conclusion</div>
                    <div class="col-1"></div>
                </div>
            `;

            verContainer.innerHTML = headerHtml;
            causeList.forEach(cause => {
                const existing = findVer(cause);
                this.addVerificationRow({
                    cause: cause,
                    method: existing ? existing.method : '',
                    source: existing ? (existing.source || existing.dataSource) : '',
                    result: existing ? existing.result : '',
                    conclusion: existing ? existing.conclusion : ''
                });
            });
        }
    },

    addRegisterRow(data = {}) {
        const c = document.getElementById('s3_registerContainer');
        const r = document.createElement('div');
        r.className = 'row g-2 mb-2 align-items-center dyn-row';
        r.innerHTML = `
            <div class="col-2"><input type="text" class="ds-input r-id" placeholder="e.g. RC-1" value="${data.id || ''}" oninput="StageModules[3].syncPrioritizationAndVerificationFromRegister()" required></div>
            <div class="col-2"><input type="text" class="ds-input r-cat" placeholder="e.g. Machine" value="${data.category || ''}" oninput="StageModules[3].syncPrioritizationAndVerificationFromRegister()" required></div>
            <div class="col-4"><input type="text" class="ds-input r-desc" placeholder="e.g. Crimping pressure fluctuation" value="${data.description || ''}" oninput="StageModules[3].syncPrioritizationAndVerificationFromRegister()" required></div>
            <div class="col-3"><input type="text" class="ds-input r-orig" placeholder="e.g. Brainstorming" value="${data.origin || ''}" oninput="StageModules[3].syncPrioritizationAndVerificationFromRegister()" required></div>
            <div class="col-1"><button type="button" class="ds-btn ds-btn-ghost text-danger p-1" onclick="this.closest('.dyn-row').remove(); StageModules[3].syncPrioritizationAndVerificationFromRegister()"><i data-lucide="trash-2" style="width:14px;"></i></button></div>`;
        c.appendChild(r);
        if (window.lucide) lucide.createIcons();
    },
    collectRegisterRows() {
        const container = document.getElementById('s3_registerContainer');
        if (!container) return [];
        return [...container.querySelectorAll('.dyn-row')].map(r => ({
            id: r.querySelector('.r-id').value, category: r.querySelector('.r-cat').value,
            description: r.querySelector('.r-desc').value, origin: r.querySelector('.r-orig').value
        })).filter(x => x.description);
    },

    addPrioritizationRow(data = {}) {
        const c = document.getElementById('s3_priorityContainer');
        const r = document.createElement('div');
        r.className = 'row g-2 mb-2 align-items-center dyn-row';
        const calc = "const p=this.closest('.dyn-row'); p.querySelector('.r-tot').value = (parseInt(p.querySelector('.r-imp').value)||0)*(parseInt(p.querySelector('.r-frq').value)||0)*(parseInt(p.querySelector('.r-con').value)||0);";
        r.innerHTML = `
            <div class="col-3"><input type="text" class="ds-input r-cause" placeholder="e.g. PM overdue by 2 weeks" value="${data.cause || ''}" required></div>
            <div class="col-2"><input type="number" class="ds-input r-imp" placeholder="1-10" value="${data.impact || ''}" onchange="${calc}" required></div>
            <div class="col-2"><input type="number" class="ds-input r-frq" placeholder="1-10" value="${data.frequency || ''}" onchange="${calc}" required></div>
            <div class="col-2"><input type="number" class="ds-input r-con" placeholder="1-10" value="${data.control || ''}" onchange="${calc}" required></div>
            <div class="col-2"><input type="number" class="ds-input r-tot" readonly style="background:var(--ds-surface-raised)" value="${data.total || ''}"></div>
            <div class="col-1"><button class="ds-btn ds-btn-ghost text-danger p-1" onclick="this.closest('.dyn-row').remove()"><i data-lucide="trash-2" style="width:14px;"></i></button></div>`;
        c.appendChild(r);
        if (window.lucide) lucide.createIcons();
    },
    collectPrioritizationRows() {
        const container = document.getElementById('s3_priorityContainer');
        if (!container) return [];
        return [...container.querySelectorAll('.dyn-row')].map(r => ({
            cause: r.querySelector('.r-cause').value, impact: r.querySelector('.r-imp').value,
            frequency: r.querySelector('.r-frq').value, control: r.querySelector('.r-con').value,
            total: r.querySelector('.r-tot').value
        })).filter(x => x.cause);
    },

    addVerificationRow(data = {}) {
        const c = document.getElementById('s3_verificationContainer');
        const r = document.createElement('div');
        r.className = 'row g-2 mb-2 align-items-center dyn-row';
        r.innerHTML = `
            <div class="col-2"><input type="text" class="ds-input r-cause" placeholder="e.g. PM overdue by 2 weeks" value="${data.cause || ''}" required></div>
            <div class="col-2"><input type="text" class="ds-input r-meth" placeholder="e.g. Review maintenance logs" value="${data.method || ''}" required></div>
            <div class="col-3"><input type="text" class="ds-input r-src" placeholder="e.g. Log sheet ML-2025" value="${data.source || ''}" required></div>
            <div class="col-2"><input type="text" class="ds-input r-res" placeholder="e.g. Verified PM was missed in Dec" value="${data.result || ''}" required></div>
            <div class="col-2"><input type="text" class="ds-input r-conc" placeholder="e.g. Confirmed Root Cause" value="${data.conclusion || ''}" required></div>
            <div class="col-1"><button class="ds-btn ds-btn-ghost text-danger p-1" onclick="this.closest('.dyn-row').remove()"><i data-lucide="trash-2" style="width:14px;"></i></button></div>`;
        c.appendChild(r);
        if (window.lucide) lucide.createIcons();
    },
    collectVerificationRows() {
        const container = document.getElementById('s3_verificationContainer');
        if (!container) return [];
        return [...container.querySelectorAll('.dyn-row')].map(r => ({
            cause: r.querySelector('.r-cause').value, method: r.querySelector('.r-meth').value,
            source: r.querySelector('.r-src').value, result: r.querySelector('.r-res').value,
            conclusion: r.querySelector('.r-conc').value
        })).filter(x => x.cause);
    },

    addFishboneL3Row(data = {}) {
        const c = document.getElementById('s3_fishboneL3Container');
        if (!c) return;
        const r = document.createElement('div');
        r.className = 'row g-2 mb-2 align-items-center dyn-row';
        r.innerHTML = `
            <div class="col-2">
                <select class="ds-input ds-select r-cat" onchange="StageModules[3].drawVisualFishboneL3()" required>
                    ${['Man','Machine','Method','Material','Measurement','Environment'].map(x => `<option ${data.category===x?'selected':''}>${x}</option>`).join('')}
                </select>
            </div>
            <div class="col-3"><input type="text" class="ds-input r-l1" placeholder="e.g. Die wear" value="${data.level1 || ''}" onchange="StageModules[3].drawVisualFishboneL3()" required></div>
            <div class="col-3"><input type="text" class="ds-input r-l2" placeholder="e.g. PM overdue by 2 weeks" value="${data.level2 || ''}" maxlength="35" onchange="StageModules[3].drawVisualFishboneL3()" required></div>
            <div class="col-2">
                <select class="ds-input ds-select r-stat" required>
                    <option value="Selected" ${data.status==='Selected'?'selected':''}>Selected</option>
                    <option value="Rejected" ${data.status==='Rejected'?'selected':''}>Rejected</option>
                </select>
            </div>
            <div class="col-2 d-flex align-items-center gap-1">
                <button type="button" class="ds-btn ds-btn-outline ds-btn-xs text-primary" style="font-size:0.7rem; padding: 0.2rem 0.4rem; white-space: nowrap;" title="Add another sub-cause for this cause" onclick="StageModules[3].addSubCauseL3Row(this)">+ Sub-Cause</button>
                <button type="button" class="ds-btn ds-btn-ghost text-danger p-1" onclick="this.closest('.dyn-row').remove(); StageModules[3].drawVisualFishboneL3()"><i data-lucide="trash-2" style="width:14px;"></i></button>
            </div>`;
        c.appendChild(r);
        if (window.lucide) lucide.createIcons();
    },

    addSubCauseL3Row(btn) {
        const parentRow = btn ? btn.closest('.dyn-row') : null;
        const category = parentRow ? (parentRow.querySelector('.r-cat')?.value || 'Man') : 'Man';
        const level1 = parentRow ? (parentRow.querySelector('.r-l1')?.value || '') : '';
        
        const container = document.getElementById('s3_fishboneL3Container');
        if (!container) return;

        const r = document.createElement('div');
        r.className = 'row g-2 mb-2 align-items-center dyn-row';
        r.innerHTML = `
            <div class="col-2">
                <select class="ds-input ds-select r-cat" onchange="StageModules[3].drawVisualFishboneL3()" required>
                    ${['Man','Machine','Method','Material','Measurement','Environment'].map(x => `<option ${category===x?'selected':''}>${x}</option>`).join('')}
                </select>
            </div>
            <div class="col-3"><input type="text" class="ds-input r-l1" placeholder="e.g. Die wear" value="${this.escapeHtml(level1)}" onchange="StageModules[3].drawVisualFishboneL3()" required></div>
            <div class="col-3"><input type="text" class="ds-input r-l2" placeholder="e.g. PM overdue by 2 weeks" value="" maxlength="35" onchange="StageModules[3].drawVisualFishboneL3()" required></div>
            <div class="col-2">
                <select class="ds-input ds-select r-stat" required>
                    <option value="Selected" selected>Selected</option>
                    <option value="Rejected">Rejected</option>
                </select>
            </div>
            <div class="col-2 d-flex align-items-center gap-1">
                <button type="button" class="ds-btn ds-btn-outline ds-btn-xs text-primary" style="font-size:0.7rem; padding: 0.2rem 0.4rem; white-space: nowrap;" title="Add another sub-cause for this cause" onclick="StageModules[3].addSubCauseL3Row(this)">+ Sub-Cause</button>
                <button type="button" class="ds-btn ds-btn-ghost text-danger p-1" onclick="this.closest('.dyn-row').remove(); StageModules[3].drawVisualFishboneL3()"><i data-lucide="trash-2" style="width:14px;"></i></button>
            </div>`;
        
        if (parentRow && parentRow.nextSibling) {
            container.insertBefore(r, parentRow.nextSibling);
        } else {
            container.appendChild(r);
        }
        if (window.lucide) lucide.createIcons();
        const inputL2 = r.querySelector('.r-l2');
        if (inputL2) inputL2.focus();
        this.drawVisualFishboneL3();
    },

    collectFishboneL3Rows() {
        const container = document.getElementById('s3_fishboneL3Container');
        if (!container) return [];
        return [...container.querySelectorAll('.dyn-row')].map(r => ({
            category: r.querySelector('.r-cat').value,
            level1: r.querySelector('.r-l1').value,
            level2: r.querySelector('.r-l2').value,
            status: r.querySelector('.r-stat').value
        })).filter(x => x.level1);
    },
    drawVisualFishboneL3() {
        const rows = this.collectFishboneL3Rows();
        const categories = ['Man', 'Machine', 'Material', 'Method', 'Measurement', 'Environment'];
        const boneConfigs = {
            Man:         { x1: 130, y1: 50,  x2: 230, y2: 220, isTop: true  },
            Machine:     { x1: 450, y1: 50,  x2: 550, y2: 220, isTop: true  },
            Material:    { x1: 770, y1: 50,  x2: 870, y2: 220, isTop: true  },
            Method:      { x1: 130, y1: 390, x2: 230, y2: 220, isTop: false },
            Measurement: { x1: 450, y1: 390, x2: 550, y2: 220, isTop: false },
            Environment: { x1: 770, y1: 390, x2: 870, y2: 220, isTop: false }
        };

        categories.forEach(cat => {
            const g = document.getElementById(`bone_${cat}_v2`);
            if (!g) return;
            g.innerHTML = '';

            const catRows = rows.filter(r => r.category === cat && r.level1 && r.level1.trim());
            if (catRows.length === 0) return;

            // Group sub-causes by Level 1 cause name
            const causeMap = new Map();
            catRows.forEach(r => {
                const key = r.level1.trim();
                if (!causeMap.has(key)) {
                    causeMap.set(key, []);
                }
                if (r.level2 && r.level2.trim()) {
                    causeMap.get(key).push(r.level2.trim());
                }
            });

            const causeEntries = Array.from(causeMap.entries());
            const config = boneConfigs[cat];
            const { x1, y1, x2, y2, isTop } = config;

            // Clamp Y ranges: top bones [82..185], bottom bones [255..358]
            const minY = isTop ? 82 : 255;
            const maxY = isTop ? 185 : 358;
            const boneRange = maxY - minY;

            const zonePerCause = causeEntries.map(([, subs]) => subs.length > 0 ? 55 : 35);
            const totalNeeded = zonePerCause.reduce((a, b) => a + b, 0);
            const scale = totalNeeded > boneRange ? (boneRange / totalNeeded) : 1.0;
            const scaledZones = zonePerCause.map(z => z * scale);

            let curY = isTop ? minY : maxY;
            const causeYs = causeEntries.map((_, i) => {
                const ly = curY;
                curY = isTop ? (curY + scaledZones[i]) : (curY - scaledZones[i]);
                return Math.max(minY, Math.min(maxY, ly));
            });

            causeEntries.forEach(([level1Name, subCauses], cIdx) => {
                if (cIdx >= 4) return;
                const ly = causeYs[cIdx];
                const t = (ly - y1) / (y2 - y1);
                const bx = x1 + t * (x2 - x1);
                const lineLen = 100;
                const lx1 = bx - lineLen;

                // Horizontal Level 1 Cause line
                const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
                line.setAttribute("x1", lx1);
                line.setAttribute("y1", ly);
                line.setAttribute("x2", bx);
                line.setAttribute("y2", ly);
                line.setAttribute("stroke", "#334155");
                line.setAttribute("stroke-width", "1.5");
                g.appendChild(line);

                // Level 1 end node dot ●
                const dot = document.createElementNS("http://www.w3.org/2000/svg", "circle");
                dot.setAttribute("cx", lx1);
                dot.setAttribute("cy", ly);
                dot.setAttribute("r", "3.5");
                dot.setAttribute("fill", "#1e293b");
                g.appendChild(dot);

                // Level 1 label: ABOVE for top bones, BELOW for bottom bones
                const label1 = level1Name.length > 18 ? level1Name.substring(0, 16) + '...' : level1Name;
                const txt = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                txt.setAttribute('x', lx1 - 5);
                txt.setAttribute('y', isTop ? (ly - 5) : (ly + 12));
                txt.setAttribute('text-anchor', 'end');
                txt.setAttribute('font-size', '8.5');
                txt.setAttribute('font-weight', 'bold');
                txt.setAttribute('fill', '#0f172a');
                txt.textContent = label1;
                g.appendChild(txt);

                // Sub-causes: branch lines terminating in interactive node point dots ● (hover for details, no text overlap)
                const validSubCauses = (subCauses || []).map(s => String(s).trim()).filter(Boolean);
                if (validSubCauses.length > 0) {
                    if (window.fbTipInit) window.fbTipInit();
                    const totalCount = validSubCauses.length;
                    const startMargin = 15;
                    const endMargin = 15;
                    const lineLen = 100;
                    const usableLength = Math.max(lineLen - startMargin - endMargin, 30);
                    const step = totalCount > 1 ? usableLength / (totalCount - 1) : usableLength / 2;

                    validSubCauses.forEach((fullText, sIdx) => {
                        // Calculate attachment point along horizontal line
                        const subX1 = (totalCount === 1)
                            ? bx - startMargin - (usableLength / 2)
                            : bx - startMargin - (sIdx * step);
                        const subOffset = Math.max(14, 20 - (totalCount > 4 ? (totalCount - 4) * 1.5 : 0));
                        const subY = isTop ? (ly + subOffset) : (ly - subOffset);
                        // Calculate subX2 so the sub-branch line is EXACTLY PARALLEL to the main category diagonal spine
                        const slopeRatio = 10 / 17; // dx/dy slope of main category spine
                        const subX2 = Math.round(subX1 + slopeRatio * subOffset);

                        const subGrp = document.createElementNS('http://www.w3.org/2000/svg', 'g');
                        subGrp.setAttribute('style', 'cursor:pointer');
                        subGrp.addEventListener('mouseover', (e) => window.fbTipShow && window.fbTipShow(fullText, e));
                        subGrp.addEventListener('mouseout',  ()  => window.fbTipHide && window.fbTipHide());

                        // Invisible expanded hover hit line
                        const hitLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                        hitLine.setAttribute('x1', subX1); hitLine.setAttribute('y1', ly);
                        hitLine.setAttribute('x2', subX2); hitLine.setAttribute('y2', subY);
                        hitLine.setAttribute('stroke', 'transparent'); hitLine.setAttribute('stroke-width', '10');
                        subGrp.appendChild(hitLine);

                        // Visible branch line
                        const subLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                        subLine.setAttribute('x1', subX1); subLine.setAttribute('y1', ly);
                        subLine.setAttribute('x2', subX2); subLine.setAttribute('y2', subY);
                        subLine.setAttribute('stroke', '#94a3b8'); subLine.setAttribute('stroke-width', '1.2');
                        subGrp.appendChild(subLine);

                        // Node point dot ●
                        const subDot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                        subDot.setAttribute('cx', subX2); subDot.setAttribute('cy', subY);
                        subDot.setAttribute('r', '3.5');
                        subDot.setAttribute('fill', '#334155');
                        subDot.setAttribute('stroke', '#ffffff');
                        subDot.setAttribute('stroke-width', '1');
                        subGrp.appendChild(subDot);

                        g.appendChild(subGrp);
                    });
                }
            });
        });
    },

    async initFacilitatorDropdown(projectData, initialFacilitator = '') {
        const hiddenInput = document.getElementById('s3_bs_facilitator');
        const selectedText = document.getElementById('s3_bs_facilitator_selected');
        const menuEl = document.getElementById('s3_bs_facilitator_menu');
        const searchEl = document.getElementById('s3_bs_facilitator_search');
        const listEl = document.getElementById('s3_bs_facilitator_list');
        const btnEl = document.getElementById('s3_bs_facilitator_btn');

        if (!hiddenInput || !listEl || !btnEl) return;

        let facilitators = [];

        try {
            const plantParam = projectData.plant_id ? `plant_id=${projectData.plant_id}` : (projectData.plant_name ? `plant_name=${encodeURIComponent(projectData.plant_name)}` : '');
            const url = `/projects/potential-members?role=facilitator${plantParam ? '&' + plantParam : '&ignore_dept=true'}`;
            const res = await api.get(url);
            if (Array.isArray(res)) {
                facilitators = res;
            } else if (res && Array.isArray(res.members)) {
                facilitators = res.members;
            }
        } catch (e) {
            console.error('[Stage 3] Failed to fetch plant facilitators:', e);
        }

        // Ensure currently assigned project facilitator is present at the top
        const assignedFacName = projectData.facilitator_name || (projectData.facilitator && (projectData.facilitator.full_name || projectData.facilitator.username)) || '';
        if (assignedFacName && !facilitators.some(f => (f.full_name || f.username || f.name) === assignedFacName)) {
            facilitators.unshift({
                id: projectData.facilitator_id || 'assigned',
                full_name: assignedFacName,
                email: projectData.facilitator_email || (projectData.facilitator && projectData.facilitator.email) || '',
                department: 'Methodological Guide'
            });
        }

        if (!facilitators.length && initialFacilitator) {
            facilitators.push({ id: 'current', full_name: initialFacilitator, email: '', department: 'Facilitator' });
        }

        // Preselect initial value or assigned facilitator
        const defaultVal = initialFacilitator || assignedFacName || (facilitators[0] ? (facilitators[0].full_name || facilitators[0].username || facilitators[0].name) : '');
        if (defaultVal) {
            hiddenInput.value = defaultVal;
            const match = facilitators.find(f => (f.full_name || f.username || f.name) === defaultVal);
            if (match) {
                const subText = match.email || match.department || 'Facilitator';
                selectedText.innerHTML = `<strong class="text-dark">${QCMS.escapeHtml(match.full_name || match.username || match.name)}</strong> <span class="text-xs text-muted">(${QCMS.escapeHtml(subText)})</span>`;
            } else {
                selectedText.innerHTML = `<strong class="text-dark">${QCMS.escapeHtml(defaultVal)}</strong>`;
            }
        } else {
            selectedText.innerHTML = '<span class="text-muted text-sm">Select Facilitator...</span>';
        }

        // Render option list function with search filtering
        const renderList = (filterText = '') => {
            const query = filterText.toLowerCase().trim();
            const filtered = facilitators.filter(f => {
                const name = (f.full_name || f.username || f.name || '').toLowerCase();
                const email = (f.email || '').toLowerCase();
                const dept = (f.department || '').toLowerCase();
                return !query || name.includes(query) || email.includes(query) || dept.includes(query);
            });

            if (!filtered.length) {
                listEl.innerHTML = '<div class="text-muted text-xs p-2 text-center">No facilitators found for this plant.</div>';
                return;
            }

            listEl.innerHTML = filtered.map(f => {
                const facName = f.full_name || f.username || f.name || 'Facilitator';
                const subInfo = f.email || f.department || 'Methodological Guide';
                const isSelected = hiddenInput.value === facName;
                return `
                    <button type="button" class="list-group-item list-group-item-action d-flex align-items-center justify-content-between py-2 px-3 ${isSelected ? 'active' : ''}" data-name="${QCMS.escapeHtml(facName)}" data-sub="${QCMS.escapeHtml(subInfo)}">
                        <div>
                            <div class="fw-bold text-sm mb-0">${QCMS.escapeHtml(facName)}</div>
                            <div class="text-xs ${isSelected ? 'text-white-50' : 'text-muted'}">${QCMS.escapeHtml(subInfo)}</div>
                        </div>
                        ${isSelected ? '<i data-lucide="check" style="width:14px;height:14px;"></i>' : ''}
                    </button>
                `;
            }).join('');

            if (window.lucide) lucide.createIcons();

            listEl.querySelectorAll('.list-group-item-action').forEach(item => {
                item.addEventListener('click', (ev) => {
                    ev.preventDefault();
                    ev.stopPropagation();
                    const chosenName = item.getAttribute('data-name');
                    const chosenSub = item.getAttribute('data-sub');
                    hiddenInput.value = chosenName;
                    selectedText.innerHTML = `<strong class="text-dark">${QCMS.escapeHtml(chosenName)}</strong> <span class="text-xs text-muted">(${QCMS.escapeHtml(chosenSub)})</span>`;
                    menuEl.style.display = 'none';
                });
            });
        };

        renderList();

        btnEl.onclick = (e) => {
            e.stopPropagation();
            const isOpen = menuEl.style.display === 'block';
            menuEl.style.display = isOpen ? 'none' : 'block';
            if (!isOpen && searchEl) {
                searchEl.value = '';
                renderList();
                setTimeout(() => searchEl.focus(), 100);
            }
        };

        if (searchEl) {
            searchEl.oninput = () => {
                renderList(searchEl.value);
            };
        }

        document.addEventListener('click', (e) => {
            if (!btnEl.contains(e.target) && !menuEl.contains(e.target)) {
                menuEl.style.display = 'none';
            }
        });
    },

    getVal(id) { return (document.getElementById(id) || {}).value || ''; },
    setVal(id, val) {
        const el = document.getElementById(id);
        if (el) {
            el.value = (val !== undefined && val !== null) ? val : '';
            if (id === 's3_bs_facilitator') {
                const selEl = document.getElementById('s3_bs_facilitator_selected');
                if (selEl) {
                    selEl.innerHTML = el.value ? `<strong class="text-dark">${QCMS.escapeHtml(el.value)}</strong>` : '<span class="text-muted text-sm">Select Facilitator...</span>';
                }
            }
        }
    }
};

window.StageModules = window.StageModules || {};
window.StageModules[3] = Stage3;

// ============================================================
// Fishbone Tooltip Utility (shared across all fishbone SVGs)
// ============================================================
window.fbTipInit = function () {
    if (document.getElementById('fb-tooltip')) return;
    const tip = document.createElement('div');
    tip.id = 'fb-tooltip';
    tip.style.cssText = [
        'position:fixed', 'display:none', 'z-index:99999',
        'background:#1e293b', 'color:#f1f5f9',
        'font-size:12px', 'line-height:1.55', 'font-family:inherit',
        'padding:8px 12px', 'border-radius:8px',
        'pointer-events:none', 'max-width:260px',
        'box-shadow:0 6px 24px rgba(0,0,0,0.38)',
        'border:1px solid rgba(148,163,184,0.18)',
        'word-break:break-word', 'white-space:pre-wrap',
        'transition:opacity .12s'
    ].join(';');
    document.body.appendChild(tip);
    document.addEventListener('mousemove', (e) => {
        if (tip.style.display !== 'none') {
            const x = e.clientX + 16, y = e.clientY - 40;
            // Keep inside viewport
            tip.style.left = Math.min(x, window.innerWidth - tip.offsetWidth - 8) + 'px';
            tip.style.top  = Math.max(4, Math.min(y, window.innerHeight - tip.offsetHeight - 8)) + 'px';
        }
    });
};
window.fbTipShow = function (text, e) {
    window.fbTipInit();
    const tip = document.getElementById('fb-tooltip');
    if (!tip) return;
    tip.textContent = text;
    tip.style.left = (e.clientX + 16) + 'px';
    tip.style.top  = (e.clientY - 40) + 'px';
    tip.style.display = 'block';
};
window.fbTipHide = function () {
    const tip = document.getElementById('fb-tooltip');
    if (tip) tip.style.display = 'none';
};

// Helper: truncate a string to the first N words
window.fbShortLabel = function (str, maxWords) {
    maxWords = maxWords || 3;
    const words = str.trim().split(/\s+/);
    if (words.length <= maxWords) return str;
    return words.slice(0, maxWords).join(' ') + '\u2026';
};
