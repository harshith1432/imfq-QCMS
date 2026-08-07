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
                        <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                            <span class="ds-icon-circle bg-primary-soft text-primary" style="width:28px;height:28px;font-size:.7rem;">1</span>
                            Brainstorming Session
                        </h5>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="row g-3 mb-4">
                            <div class="col-md-6">
                                <label class="ds-label">Session Name</label>
                                <input type="text" id="s3_bs_session" class="ds-input" required>
                            </div>
                            <div class="col-md-6">
                                <label class="ds-label">Facilitator</label>
                                <input type="text" id="s3_bs_facilitator" class="ds-input" required>
                            </div>
                            <div class="col-md-6">
                                <label class="ds-label">Participants</label>
                                <input type="text" id="s3_bs_participants" class="ds-input" placeholder="e.g. Ravi Kumar, Shubham Singh, Rajesh Kumar" required>
                            </div>
                            <div class="col-md-6">
                                <label class="ds-label">Date</label>
                                <input type="date" id="s3_bs_date" class="ds-input" required>
                            </div>
                            <div class="col-12">
                                <label class="ds-label">Notes</label>
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
                                <div class="border p-3 rounded bg-white shadow-sm" style="max-height: 280px; position: relative;">
                                    <canvas id="s3ParetoCanvas" style="max-height: 250px; width: 100%;"></canvas>
                                </div>
                            </div>
                            <div class="col-md-5">
                                <div class="p-3 border rounded bg-light" style="border-radius: var(--radius-md);">
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
                        <h5 class="mb-0 fw-bold d-flex align-items-center gap-2 text-primary">
                            <i data-lucide="git-branch" style="width:20px;height:20px;transform: rotate(90deg);"></i>
                            QC Tool 5: Ishikawa (Fishbone) Diagram
                        </h5>
                    </div>
                    <div class="ds-card-body p-4">
                        <label class="ds-label mb-3">Interactive Fishbone Visualization</label>
                        
                        <!-- Visual Fishbone SVG -->
                        <div class="border p-3 rounded bg-white shadow-sm mb-4" style="overflow-x: auto;">
                            <div style="min-width: 1000px; position: relative; height: 420px;">
                                <svg viewBox="0 0 1100 440" width="100%" height="100%" style="font-family: inherit;">
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
                            <h6 class="fw-bold mb-0 text-primary">Detailed Causes List (Level 1 & 2)</h6>
                            <button class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[3].addFishboneRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Cause
                            </button>
                        </div>
                        
                        <div id="s3_fishboneContainer" class="mb-4">
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

                <!-- Section 4 - Cause Register -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                            <span class="ds-icon-circle bg-primary-soft text-primary" style="width:28px;height:28px;font-size:.7rem;">2</span>
                            Cause Register
                        </h5>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary">Register Details</h6>
                            <button class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[3].addRegisterRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Register Entry
                            </button>
                        </div>
                        <div id="s3_registerContainer" class="mb-4">
                            <div class="row text-muted small fw-bold mb-2 px-2">
                                <div class="col-2">ID</div>
                                <div class="col-2">Category</div>
                                <div class="col-4">Cause Description</div>
                                <div class="col-3">Origin</div>
                                <div class="col-1"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section 5 - Cause Prioritization -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                            <span class="ds-icon-circle bg-primary-soft text-primary" style="width:28px;height:28px;font-size:.7rem;">3</span>
                            Cause Prioritization Matrix
                        </h5>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary">Prioritization Ranks</h6>
                            <button class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[3].addPrioritizationRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Cause to Rank
                            </button>
                        </div>
                        <div id="s3_priorityContainer" class="mb-4">
                            <div class="row text-muted small fw-bold mb-2 px-2">
                                <div class="col-3">Cause</div>
                                <div class="col-2">Impact (1-10)</div>
                                <div class="col-2">Freq (1-10)</div>
                                <div class="col-2">Control (1-10)</div>
                                <div class="col-2">Total Score</div>
                                <div class="col-1"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section 6 - Cause Verification -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                            <span class="ds-icon-circle bg-primary-soft text-primary" style="width:28px;height:28px;font-size:.7rem;">4</span>
                            Cause Verification
                        </h5>
                    </div>
                    <div class="ds-card-body p-4">
                        <div class="d-flex justify-content-between align-items-center mb-3">
                            <h6 class="fw-bold mb-0 text-primary">Verification Checklist</h6>
                            <button class="ds-btn ds-btn-ghost" style="font-size:.75rem;padding:.25rem .75rem;" onclick="StageModules[3].addVerificationRow()">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Verification
                            </button>
                        </div>
                        <div id="s3_verificationContainer" class="mb-4">
                            <div class="row text-muted small fw-bold mb-2 px-2">
                                <div class="col-2">Cause</div>
                                <div class="col-2">Method</div>
                                <div class="col-3">Data Source</div>
                                <div class="col-2">Result</div>
                                <div class="col-2">Conclusion</div>
                                <div class="col-1"></div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Section 6.5 - Ishikawa (Fishbone) Diagram (Post-Verification) -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <h5 class="mb-0 fw-bold d-flex align-items-center gap-2 text-primary">
                            <span class="ds-icon-circle bg-primary-soft text-primary" style="width:28px;height:28px;font-size:.7rem;">5</span>
                            Ishikawa (Fishbone) Diagram (Post-Verification)
                        </h5>
                    </div>
                    <div class="ds-card-body p-4">
                        <label class="ds-label mb-3">Interactive Fishbone Visualization (Verified Causes)</label>
                        
                        <!-- Visual Fishbone SVG -->
                        <div class="border p-3 rounded bg-white shadow-sm mb-4" style="overflow-x: auto;">
                            <div style="min-width: 1000px; position: relative; height: 420px;">
                                <svg viewBox="0 0 1100 440" width="100%" height="100%" style="font-family: inherit;">
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

                <!-- Section 7 - Fishbone Level 3 Summary -->
                <div class="glass-card ds-card mb-4">
                    <div class="ds-card-header p-4 border-bottom">
                        <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                            <span class="ds-icon-circle bg-primary-soft text-primary" style="width:28px;height:28px;font-size:.7rem;">6</span>
                            Final Causes Summary (Level 3 Output)
                        </h5>
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

        // Register
        const reg = d.cause_register || [];
        const regContainer = document.getElementById('s3_registerContainer');
        regContainer.innerHTML = `
            <div class="row text-muted small fw-bold mb-2 px-2">
                <div class="col-2">ID</div>
                <div class="col-2">Category</div>
                <div class="col-4">Cause Description</div>
                <div class="col-3">Origin</div>
                <div class="col-1"></div>
            </div>
        `;
        if (reg.length) reg.forEach(r => this.addRegisterRow(r));
        else this.addRegisterRow();

        // Prioritization
        const prio = d.cause_prioritization || [];
        const prioContainer = document.getElementById('s3_priorityContainer');
        prioContainer.innerHTML = `
            <div class="row text-muted small fw-bold mb-2 px-2">
                <div class="col-3">Cause</div>
                <div class="col-2">Impact (1-10)</div>
                <div class="col-2">Freq (1-10)</div>
                <div class="col-2">Control (1-10)</div>
                <div class="col-2">Total Score</div>
                <div class="col-1"></div>
            </div>
        `;
        if (prio.length) prio.forEach(r => this.addPrioritizationRow(r));
        else this.addPrioritizationRow();

        // Verification
        const ver = d.cause_verification || [];
        const verContainer = document.getElementById('s3_verificationContainer');
        verContainer.innerHTML = `
            <div class="row text-muted small fw-bold mb-2 px-2">
                <div class="col-2">Cause</div>
                <div class="col-2">Method</div>
                <div class="col-3">Data Source</div>
                <div class="col-2">Result</div>
                <div class="col-2">Conclusion</div>
                <div class="col-1"></div>
            </div>
        `;
        if (ver.length) ver.forEach(r => this.addVerificationRow(r));
        else this.addVerificationRow();

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
            <div class="col-3"><input type="text" class="ds-input r-l1" placeholder="e.g. Die wear" value="${data.level1 || ''}" onchange="StageModules[3].drawVisualFishbone()" required></div>
            <div class="col-3"><input type="text" class="ds-input r-l2" placeholder="e.g. PM overdue by 2 weeks" value="${data.level2 || ''}" maxlength="35" onchange="StageModules[3].drawVisualFishbone()" required></div>
            <div class="col-2">
                <select class="ds-input ds-select r-stat" required>
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
            <div class="col-3"><input type="text" class="ds-input r-l1" placeholder="e.g. Die wear" value="${this.escapeHtml(level1)}" onchange="StageModules[3].drawVisualFishbone()" required></div>
            <div class="col-3"><input type="text" class="ds-input r-l2" placeholder="e.g. PM overdue by 2 weeks" value="" maxlength="35" onchange="StageModules[3].drawVisualFishbone()" required></div>
            <div class="col-2">
                <select class="ds-input ds-select r-stat" required>
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
                if (subCauses && subCauses.length > 0) {
                    if (window.fbTipInit) window.fbTipInit();
                    subCauses.slice(0, 3).forEach((subStr, sIdx) => {
                        const fullText = String(subStr).trim();
                        if (!fullText) return;

                        // Position attachment point on horizontal line
                        const subX1 = bx - 25 - (sIdx * 25);
                        const subOffset = 18 + (sIdx * 4);
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

    addRegisterRow(data = {}) {
        const c = document.getElementById('s3_registerContainer');
        const r = document.createElement('div');
        r.className = 'row g-2 mb-2 align-items-center dyn-row';
        r.innerHTML = `
            <div class="col-2"><input type="text" class="ds-input r-id" placeholder="e.g. RC-1" value="${data.id || ''}" required></div>
            <div class="col-2"><input type="text" class="ds-input r-cat" placeholder="e.g. Machine" value="${data.category || ''}" required></div>
            <div class="col-4"><input type="text" class="ds-input r-desc" placeholder="e.g. Crimping pressure fluctuation" value="${data.description || ''}" required></div>
            <div class="col-3"><input type="text" class="ds-input r-orig" placeholder="e.g. Brainstorming" value="${data.origin || ''}" required></div>
            <div class="col-1"><button class="ds-btn ds-btn-ghost text-danger p-1" onclick="this.closest('.dyn-row').remove()"><i data-lucide="trash-2" style="width:14px;"></i></button></div>`;
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
                if (subCauses && subCauses.length > 0) {
                    if (window.fbTipInit) window.fbTipInit();
                    subCauses.slice(0, 3).forEach((subStr, sIdx) => {
                        const fullText = String(subStr).trim();
                        if (!fullText) return;

                        // Position attachment point on horizontal line
                        const subX1 = bx - 25 - (sIdx * 25);
                        const subOffset = 18 + (sIdx * 4);
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

    getVal(id) { return (document.getElementById(id) || {}).value || ''; },
    setVal(id, val) { const el = document.getElementById(id); if (el) el.value = (val !== undefined && val !== null) ? val : ''; }
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
