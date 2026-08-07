window.StageModules = window.StageModules || {};

const ProjectApp = {
    projectId: new URLSearchParams(window.location.search).get('id'),
    projectData: null,
    orgUsers: [],
    activeStageId: null,
    myAssistanceRequests: [],  // Cache of this user's requests for this project

    async init() {
        QCMS.init();
        if (!this.projectId) {
            window.location.href = 'projects-repository.html';
            return;
        }

        await this.loadOrgUsers();
        await this.loadProject();

        if (window.lucide) lucide.createIcons();
    },

    openOriginalIdeaModal() {
        const idea = (this.projectData && this.projectData.linked_idea) ? this.projectData.linked_idea : null;
        const body = document.getElementById('originalIdeaModalBody');
        if (!body) return;

        if (idea) {
            body.innerHTML = `
                <div class="row g-3 text-sm">
                    <div class="col-md-6"><strong>Idea Code:</strong> <span class="font-monospace text-primary fw-bold">${QCMS.escapeHtml(idea.idea_code)}</span></div>
                    <div class="col-md-6"><strong>Status:</strong> <span class="badge bg-success-subtle text-success border border-success-subtle">${QCMS.escapeHtml(idea.status || 'Approved')}</span></div>
                    <div class="col-md-12"><strong>Title:</strong> ${QCMS.escapeHtml(idea.title)}</div>
                    <div class="col-md-6"><strong>Department:</strong> ${QCMS.escapeHtml(idea.department || 'N/A')}</div>
                    <div class="col-md-6"><strong>Category:</strong> ${QCMS.escapeHtml(idea.category || 'N/A')}</div>
                    <div class="col-md-6"><strong>Submitted By:</strong> ${QCMS.escapeHtml(idea.submitted_by || 'N/A')}</div>
                    <div class="col-md-6"><strong>Co-Suggesters:</strong> ${QCMS.escapeHtml((idea.co_suggesters || []).join(', ') || 'None')}</div>
                    <div class="col-md-12 border-top pt-2 mt-2"><strong>Present Situation:</strong><br><span class="text-muted">${QCMS.escapeHtml(idea.present_situation || 'N/A')}</span></div>
                    <div class="col-md-12"><strong>Proposed Solution:</strong><br><span class="text-muted">${QCMS.escapeHtml(idea.proposed_solution || 'N/A')}</span></div>
                    <div class="col-md-6 border-top pt-2 mt-2"><strong>Tangible Benefit:</strong> $${(idea.tangible_benefit || 0).toLocaleString()}</div>
                    <div class="col-md-6 border-top pt-2 mt-2"><strong>Intangible Benefit:</strong> ${QCMS.escapeHtml(idea.intangible_benefit || 'N/A')}</div>
                    <div class="col-md-6"><strong>Investment Required:</strong> $${(idea.investment_required || 0).toLocaleString()}</div>
                    <div class="col-md-6"><strong>Implementation Time:</strong> ${QCMS.escapeHtml(idea.implementation_time || 'N/A')}</div>
                </div>
            `;
        } else {
            body.innerHTML = `<p class="text-muted text-center py-4">No original idea payload cached. Reference Code: <strong>${QCMS.escapeHtml((this.projectData && this.projectData.reference_number) || 'N/A')}</strong></p>`;
        }

        const modal = new bootstrap.Modal(document.getElementById('originalIdeaModal'));
        modal.show();
    },

    async loadProject() {
        try {
            const data = await api.get(`/projects/${this.projectId}`);
            this.projectData = data;

            // Default to the highest stage they've unlocked/are working on, or URL parameter
            const stageParam = new URLSearchParams(window.location.search).get('stage');
            this.activeStageId = stageParam ? parseInt(stageParam) : (data.current_stage || 1);

            this.renderHeader(data);
            this.renderStepper(data);   // also sets this._stagesCfg
            
            // Resolve the original module id for the active sequence position
            const initCfgEntry = (this._stagesCfg || [])[this.activeStageId - 1];
            const initOriginalId = initCfgEntry ? initCfgEntry.original_id : this.activeStageId;
            this.loadStage(this.activeStageId, initOriginalId);
            await this.renderExecutiveReview(data);

            // Load Team Member's facilitator assistance requests (shows replies per-stage)
            await this.loadMyAssistanceRequests();

        } catch (err) {
            QCMS.toast('Failed to load project: ' + err.message, 'error');
        }
    },

    async loadOrgUsers() {
        try {
            const users = await api.get('/projects/members');
            window.orgUsers = users || []; // Attach to window so modules can use it
        } catch (e) {
            window.orgUsers = [];
            console.warn('Could not load org users', e);
        }
    },

    renderHeader(data) {
        document.getElementById('projectTitleDisplay').textContent = data.title;
        document.getElementById('projectUidDisplay').textContent = `UID: ${data.project_uid}`;
        
        // Active stage status
        const activeTracker = (data.stages || []).find(s => s.stage_number === this.activeStageId);
        const status = activeTracker ? activeTracker.status : 'Incomplete';
        
        const badge = document.getElementById('stageStatusBadge');
        badge.textContent = `Stage ${this.activeStageId}: ${status}`;
        if (status === 'Completed') { badge.style.cssText = 'background:rgba(var(--ds-success-rgb),.12);color:var(--ds-success)'; }
        else if (status === 'Submitted For Review') { badge.style.cssText = 'background:rgba(var(--ds-info-rgb),.12);color:var(--ds-info)'; }
        else if (status === 'Rejected' || status === 'Revision') { badge.style.cssText = 'background:rgba(var(--ds-danger-rgb),.12);color:var(--ds-danger)'; }
        else { badge.style.cssText = 'background:rgba(var(--ds-warning-rgb),.12);color:var(--ds-warning)'; }
        
        document.getElementById('projectMeta').textContent =
            `${data.category} Project · ${data.department} · Status: ${data.status}`;

        // Render Facilitator Card - ONLY for Team Member role (not Team Leader, Reviewer, etc.)
        const facCard = document.getElementById('facilitatorSupportCard');
        if (facCard) {
            try {
                const sessionUser = JSON.parse(sessionStorage.getItem('user') || '{}');
                const roleName = sessionUser.role || '';
                const role = roleName.toLowerCase().replace(/[^a-z0-9]/g, '');
                const isTeamMember = (role === 'teammember');

                if (isTeamMember && data.facilitator_name) {
                    facCard.classList.remove('d-none');
                    document.getElementById('facName').textContent = data.facilitator_name;
                    document.getElementById('facEmail').textContent = data.facilitator_email || '';
                    document.getElementById('facAvatar').textContent = data.facilitator_name.charAt(0).toUpperCase();
                } else {
                    facCard.classList.add('d-none');
                }
            } catch (e) {
                facCard.classList.add('d-none');
            }
        }

        // Render Idea Information Card ONLY if project was imported from Ideation Tool
        const ideaCard = document.getElementById('ideaInformationCard');
        if (ideaCard) {
            const isImportedFromIdeation = (data.project_source === 'Ideation Tool') || (data.is_linked_idea === true) || !!data.linked_idea;
            if (isImportedFromIdeation) {
                const idea = data.linked_idea || {};
                ideaCard.classList.remove('d-none');
                document.getElementById('ideaCardCode').textContent = idea.idea_code || data.idea_code || data.reference_number || 'N/A';
                document.getElementById('ideaCardTitle').textContent = idea.title || data.title || 'N/A';
                document.getElementById('ideaCardOwner').textContent = idea.submitted_by || 'Ideation Tool User';
                document.getElementById('ideaCardImportDate').textContent = idea.imported_at ? new Date(idea.imported_at).toLocaleDateString() : 'Recently';
            } else {
                ideaCard.classList.add('d-none');
            }
        }

        // Find most recent review comment for active stage if rejected/revision
        const banner = document.getElementById('rejectionCommentsBanner');
        if (banner) {
            const activeReview = (data.reviews || []).find(r => r.stage_number === this.activeStageId && (r.decision === 'Rejected' || r.decision === 'Revision'));
            if (activeReview && (status === 'Rejected' || status === 'Revision')) {
                banner.className = "alert alert-danger d-flex align-items-start gap-3 mb-4 fade-in";
                banner.style.cssText = "border: none; background: rgba(220, 38, 38, 0.08); border-left: 4px solid #dc2626; border-radius: var(--ds-radius-md); box-shadow: var(--ds-shadow-sm);";
                banner.innerHTML = `
                    <div class="rounded-circle d-flex align-items-center justify-content-center flex-shrink-0" style="width: 36px; height: 36px; background: rgba(220, 38, 38, 0.15); margin-top: 2px;">
                        <i data-lucide="x-circle" style="width: 20px; height: 20px; color: #dc2626;"></i>
                    </div>
                    <div class="flex-grow-1">
                        <h6 class="alert-heading mb-1 fw-bold" style="font-size: 14px; color: #dc2626;">Stage ${this.activeStageId} Review Status: ${status === 'Revision' ? 'Revision Requested' : 'Rejected'}</h6>
                        <p class="mb-2 text-secondary text-xs" style="line-height: 1.4;">The Reviewer has requested changes/rejected this stage. Please find their comments below:</p>
                        <div class="p-3 border rounded bg-white text-sm fw-semibold text-main shadow-xs" style="border-color: rgba(220, 38, 38, 0.15) !important;">
                            ${activeReview.comments || 'No comments provided.'}
                        </div>
                        <div class="text-xxs text-muted mt-2">
                            Reviewed by <strong>${activeReview.reviewer_name}</strong> on ${QCMS.formatRelative ? QCMS.formatRelative(activeReview.decided_at) : new Date(activeReview.decided_at).toLocaleString()}
                        </div>
                    </div>
                `;
                if (window.lucide) lucide.createIcons();
            } else {
                banner.className = "d-none";
            }
        }
    },

    // Load all assistance requests sent by this user for this project.
    // Runs once on page load; updateFacReplyCard() is called per stage-switch.
    async loadMyAssistanceRequests() {
        try {
            const sessionUser = JSON.parse(sessionStorage.getItem('user') || '{}');
            const role = (sessionUser.role || '').toLowerCase().replace(/[^a-z0-9]/g, '');
            // Only relevant for team members
            if (role !== 'teammember') return;

            const requests = await api.get(`/projects/${this.projectId}/my-assistance-requests`);
            this.myAssistanceRequests = requests || [];
            // Show reply card for the currently active stage
            this.updateFacReplyCard(this.activeStageId);
        } catch (e) {
            // Non-critical — silently ignore if not a team member or if endpoint fails
            this.myAssistanceRequests = [];
        }
    },

    // Show or hide the facilitator reply card based on requests for the given stage.
    // Displays the most recent request and its reply (if any).
    updateFacReplyCard(stageId) {
        const card = document.getElementById('facilitatorReplyCard');
        if (!card) return;

        // Find most recent request for this stage (sorted descending from server)
        const forStage = (this.myAssistanceRequests || []).filter(r => Number(r.stage_id) === Number(stageId));
        if (!forStage.length) {
            card.classList.add('d-none');
            return;
        }
        const req = forStage[0];  // most recent

        // Show the card
        card.classList.remove('d-none');

        // Original message
        const msgEl = document.getElementById('facReplyOriginalMsg');
        if (msgEl) msgEl.textContent = req.message || '';

        // Badge: status colour
        const badge = document.getElementById('facReplyBadge');
        if (badge) {
            badge.textContent = req.status;
            badge.className = 'ds-badge ms-auto';
            if (req.status === 'Approved')      badge.classList.add('green');
            else if (req.status === 'Not Approved') badge.classList.add('red');
            else if (req.status === 'Needs Info')   badge.classList.add('blue');
            else                                     badge.classList.add('orange');
        }

        // Facilitator response
        const responseWrap = document.getElementById('facReplyResponseWrap');
        const responseText = document.getElementById('facReplyResponseText');
        if (req.response) {
            if (responseWrap) responseWrap.classList.remove('d-none');
            if (responseText) responseText.textContent = req.response;
        } else {
            if (responseWrap) responseWrap.classList.add('d-none');
        }

        // Date line
        const dateEl = document.getElementById('facReplyDate');
        if (dateEl && req.updated_at) {
            const d = new Date(req.updated_at);
            dateEl.textContent = `Last updated: ${d.toLocaleDateString('en-IN', {day:'2-digit', month:'short', year:'numeric'})}`;
        }

        if (window.lucide) lucide.createIcons();
    },

    renderStepper(data) {
        const container = document.getElementById('stepperContainer');
        if (!container || !data.stages) return;

        // Use org-level custom config, or fall back to built-in defaults
        const DEFAULT_STAGES = [
            { stage_id: 1, original_id: 1, title: 'S0/S1 Plan & Establish Team',    icon: 'target'      },
            { stage_id: 2, original_id: 2, title: 'S2 Define Problem',               icon: 'database'    },
            { stage_id: 3, original_id: 3, title: 'S3 Interim Containment',          icon: 'git-branch'  },
            { stage_id: 4, original_id: 4, title: 'S4 Determine Root Causes',        icon: 'search'      },
            { stage_id: 5, original_id: 5, title: 'S5 Choose Permanent Corrections', icon: 'lightbulb'   },
            { stage_id: 6, original_id: 6, title: 'S6 Implement Corrective Actions', icon: 'settings-2'  },
            { stage_id: 7, original_id: 7, title: 'S7 Take Preventive Measures',     icon: 'trending-up' },
            { stage_id: 8, original_id: 8, title: 'S8 Congratulate Team & Closure',  icon: 'award'       },
        ];
        const cfgRaw = (data.stages_config && data.stages_config.length > 0)
            ? data.stages_config
            : DEFAULT_STAGES;
        // Sort by stage_id to guarantee display order
        const cfg = [...cfgRaw].sort((a, b) => a.stage_id - b.stage_id);

        // Persist the config on the app object so switchStage can resolve original_id
        this._stagesCfg = cfg;

        const stages = cfg.map(c => ({
            name: c.title,
            icon: c.icon,
            original_id: c.original_id,
        }));

        const statusStyle = {
            'Completed':            { color: '#16a34a', bg: '#dcfce7', border: '#86efac', glyph: 'check-circle-2' },
            'Submitted For Review': { color: '#2563eb', bg: '#dbeafe', border: '#93c5fd', glyph: 'hourglass'      },
            'Incomplete':           { color: '#d97706', bg: '#fef3c7', border: '#fcd34d', glyph: null             },
            'Rejected':             { color: '#dc2626', bg: '#fee2e2', border: '#fca5a5', glyph: 'x-circle'       },
            'Not Started':          { color: '#94a3b8', bg: '#f1f5f9', border: '#e2e8f0', glyph: null             },
        };

        container.innerHTML = `
        <style>
            .qcms-stepper { display:flex; align-items:flex-start; overflow-x:auto; padding:16px 8px 8px; gap:0; scrollbar-width:none; }
            .qcms-stepper::-webkit-scrollbar { display:none; }
            .qcms-step { display:flex; flex-direction:column; align-items:center; min-width:100px; max-width:120px; position:relative; cursor:pointer; transition:opacity .2s; }
            .qcms-step.locked { opacity:.42; cursor:default; }
            .qcms-step:hover:not(.locked) .step-icon-wrap { transform:translateY(-3px); }
            .step-icon-wrap { width:52px; height:52px; border-radius:16px; display:flex; align-items:center; justify-content:center; border:2px solid; transition:all .25s cubic-bezier(.4,0,.2,1); position:relative; }
            .step-icon-wrap.is-active { box-shadow:0 8px 20px -4px rgba(0,0,0,.18); transform:translateY(-2px); }
            .step-badge { position:absolute; top:-6px; right:-6px; width:18px; height:18px; border-radius:50%; background:white; display:flex; align-items:center; justify-content:center; box-shadow:0 1px 4px rgba(0,0,0,.15); }
            .step-label { font-size:.6rem; font-weight:700; text-align:center; margin-top:8px; line-height:1.4; white-space:pre-line; }
            .step-status { font-size:.52rem; text-align:center; margin-top:2px; font-weight:600; letter-spacing:.03em; }
            .step-connector { flex:1; height:2px; min-width:12px; border-radius:1px; margin-bottom:36px; background:linear-gradient(90deg, var(--c-from), var(--c-to)); }
        </style>
        <div class="qcms-stepper">
        ` + data.stages.map((s, i) => {
            const stg     = stages[i];
            const st      = statusStyle[s.status] || statusStyle['Not Started'];
            const isActive= (i + 1) === this.activeStageId;
            const isClickable = s.status !== 'Not Started' || (i + 1) <= data.current_stage;
            const next    = i < data.stages.length - 1 ? (statusStyle[data.stages[i+1].status] || statusStyle['Not Started']) : null;

            return `
            <div class="qcms-step ${isClickable ? '' : 'locked'}"
                 onclick="ProjectApp.switchStage(${i+1}, ${isClickable})"
                 title="${stg.name.replace(/\n/g,' ')}">
                <div class="step-icon-wrap ${isActive ? 'is-active' : ''}"
                     style="background:${isActive ? st.color : st.bg};
                            border-color:${st.border};
                            color:${isActive ? '#fff' : st.color};">
                    <i data-lucide="${stg.icon}" style="width:22px;height:22px;stroke-width:1.75;"></i>
                    ${st.glyph ? `<div class="step-badge"><i data-lucide="${st.glyph}" style="width:11px;height:11px;color:${st.color};stroke-width:2.5;"></i></div>` : ''}
                </div>
                <span class="step-label" style="color:${isActive ? st.color : (s.status === 'Not Started' ? '#94a3b8' : st.color)};">${stg.name}</span>
                <span class="step-status" style="color:${st.color};">${s.status}</span>
            </div>
            ${next ? `<div class="step-connector" style="--c-from:${st.border};--c-to:${next.border};"></div>` : ''}
            `;
        }).join('') + `</div>`;

        if (window.lucide) lucide.createIcons();
    },

    switchStage(stageId, isClickable) {
        if (!isClickable || stageId === this.activeStageId) return;
        this.activeStageId = stageId;
        this.renderHeader(this.projectData);
        this.renderStepper(this.projectData);
        // Resolve the module original_id for this sequence position
        const cfgEntry = (this._stagesCfg || [])[stageId - 1];
        const originalId = cfgEntry ? cfgEntry.original_id : stageId;
        this.loadStage(stageId, originalId);
        // Update facilitator reply card for the newly active stage
        this.updateFacReplyCard(stageId);
    },

    loadStage(stageId, originalId) {
        const container = document.getElementById('stageContentContainer');
        const stageCfg = (this._stagesCfg || [])[stageId - 1];

        // Fall back to original hardcoded stage modules
        const moduleId = (originalId !== undefined) ? originalId : stageId;
        const module = StageModules[moduleId];

        
        if (!module) {
            container.innerHTML = `
                <div class="glass-card ds-card p-5 text-center mb-4">
                    <i data-lucide="wrench" style="width:40px;height:40px;color:var(--ds-text-secondary);"></i>
                    <h5 class="mt-3 fw-bold">Stage ${stageId} Under Construction</h5>
                    <p class="ds-text-secondary">This stage is currently being implemented.</p>
                </div>
            `;
            if (window.lucide) lucide.createIcons();
            document.getElementById('saveDraftBtn').classList.add('d-none');
            document.getElementById('submitBtn').classList.add('d-none');
            document.getElementById('reviewPanel').classList.add('d-none');
            return;
        }

        // Render HTML
        container.innerHTML = module.renderHTML();
        
        // Wrap getVal to automatically bypass validation/checks for hidden elements
        const originalGetVal = module.getVal;
        module.getVal = function(id) {
            const el = document.getElementById(id);
            if (el && el.offsetParent === null) {
                return 'N/A'; // return dummy value to bypass checks
            }
            if (originalGetVal) {
                return originalGetVal.call(module, id);
            }
            return (el || {}).value || '';
        };

        // Apply predefined fields customizations from stage configuration template
        try {
            if (stageCfg && stageCfg.sections) {
                stageCfg.sections.forEach(sec => {
                    if (sec && sec.predefined_fields) {
                        Object.keys(sec.predefined_fields).forEach(id => {
                            const cfg = sec.predefined_fields[id];
                            const el = container.querySelector(`#${id}`);
                            if (el && cfg) {
                                if (cfg.disabled) {
                                    const wrapper = el.closest('.col-md-4, .col-md-6, .col-md-3, .col-12, .ds-field, .col-md-5, .col-md-7, .team-member-row') || el.parentElement;
                                    if (wrapper) {
                                        wrapper.style.setProperty('display', 'none', 'important');
                                    }
                                } else {
                                    // Update label and required status
                                    const wrapper = el.closest('.ds-field, .team-member-row') || el.parentElement;
                                    if (wrapper) {
                                        const label = wrapper.querySelector('label');
                                        if (label) {
                                            let cleanLbl = (cfg.label || label.textContent || '').replace(/\s*\*$/, '');
                                            if (cfg.required !== false) {
                                                label.innerHTML = `${cleanLbl} <span class="text-danger">*</span>`;
                                                el.required = true;
                                            } else {
                                                label.textContent = cleanLbl;
                                                el.required = false;
                                                el.removeAttribute('required');
                                            }
                                        }
                                    }
                                    // Update placeholder
                                    if (cfg.placeholder) el.placeholder = cfg.placeholder;
                                    // Update type
                                    if (cfg.input_type && el.tagName.toLowerCase() === 'input' && el.type !== 'checkbox' && el.type !== 'radio' && el.type !== 'file') {
                                        const validTypes = ['date', 'datetime-local', 'number', 'text', 'time', 'month', 'email', 'tel', 'url'];
                                        if (validTypes.includes(cfg.input_type)) {
                                            el.type = cfg.input_type;
                                        }
                                    }
                                }
                            }
                        });
                    }
                });
            }
        } catch (e) {
            console.error("[QCMS] Error applying predefined fields customization:", e);
        }

        // Initialize logic
        if (module.init) {
            try {
                module.init(this.projectData);
            } catch (e) {
                console.error("[QCMS] Error during module.init:", e);
            }
        }

        // 0. Tag predefined cards BEFORE injecting custom cards to prevent index shift issues
        const predefinedCards = Array.from(container.querySelectorAll('.glass-card.ds-card'));
        try {
            if (stageCfg && stageCfg.sections) {
                stageCfg.sections.forEach((sec, sIdx) => {
                    if (sec && sec.id && !sec.id.startsWith('sec_')) {
                        const cardIdx = sec.card_index !== undefined ? sec.card_index : sIdx;
                        const cardEl = predefinedCards[cardIdx];
                        if (cardEl) {
                            cardEl.dataset.secId = sec.id;
                            const titleEl = cardEl.querySelector('.ds-card-header h5, .ds-card-header h6');
                            if (titleEl) {
                                let cleanTitle = titleEl.innerHTML.replace(/\s*<span class="text-danger">\*<\/span>/g, '');
                                if (sec.required !== false) {
                                    titleEl.innerHTML = `${cleanTitle} <span class="text-danger">*</span>`;
                                } else {
                                    titleEl.innerHTML = cleanTitle;
                                }
                            }
                        }
                    }
                });
            }
        } catch (e) {
            console.error("[QCMS] Error tagging predefined cards:", e);
        }

        // 1. Inject custom top-level section cards
        try {
            const formEl = container.querySelector('[id$="Form"]') || container.firstElementChild;
            if (formEl && stageCfg && stageCfg.sections) {
                stageCfg.sections.forEach(sec => {
                    if (sec && sec.id && typeof sec.id === 'string' && sec.id.startsWith('sec_')) {
                        if (container.querySelector(`#card_${sec.id}`)) return; // already exists

                        const cardEl = document.createElement('div');
                        cardEl.className = 'glass-card ds-card mb-4';
                        cardEl.id = `card_${sec.id}`;
                        cardEl.dataset.secId = sec.id;
                        cardEl.innerHTML = `
                            <div class="ds-card-header p-4 border-bottom">
                                <h5 class="mb-0 fw-bold d-flex align-items-center gap-2">
                                    <span class="ds-icon-circle bg-primary-soft text-primary" style="width:28px;height:28px;font-size:.7rem;">
                                        <i data-lucide="layout" style="width:14px;height:14px;"></i>
                                    </span>
                                    ${sec.label || 'Custom Section'}${sec.required !== false ? ' <span class="text-danger">*</span>' : ''}
                                </h5>
                            </div>
                            <div class="ds-card-body p-4">
                                ${DynamicRenderer.getFieldContentHtml(sec)}
                            </div>
                        `;

                        // Insert before the last card (usually Approval Gate)
                        const cards = Array.from(formEl.querySelectorAll(':scope > .glass-card.ds-card'));
                        if (cards.length > 0) {
                            const lastCard = cards[cards.length - 1];
                            formEl.insertBefore(cardEl, lastCard);
                        } else {
                            formEl.appendChild(cardEl);
                        }
                    }
                });
            }
        } catch (e) {
            console.error("[QCMS] Error rendering custom cards:", e);
        }

        // 2. Dynamically inject custom sub-fields defined on sections
        try {
            const customElements = [];
            if (stageCfg && stageCfg.sections) {
                stageCfg.sections.forEach((sec, sIdx) => {
                    if (sec && sec.id && typeof sec.id === 'string' && sec.id.startsWith('sec_')) {
                        customElements.push(sec);
                    }

                    if (sec && sec.fields && sec.fields.length > 0) {
                        const cardIdx = sec.card_index !== undefined ? sec.card_index : sIdx;
                        const cardEl = predefinedCards[cardIdx];
                        if (cardEl) {
                            const cardBody = cardEl.querySelector('.ds-card-body');
                            if (cardBody) {
                                sec.fields.forEach(field => {
                                    if (field) {
                                        const fieldWrapper = document.createElement('div');
                                        fieldWrapper.className = 'ds-field mt-3 border-top pt-3';
                                        
                                        const labelEl = document.createElement('label');
                                        labelEl.className = 'ds-label fw-bold mb-2 d-block';
                                        labelEl.innerHTML = `${field.label || ''} <span class="text-danger">*</span>`;
                                        fieldWrapper.appendChild(labelEl);

                                        // Render sub-field inner content via DynamicRenderer
                                        const contentWrapper = document.createElement('div');
                                        contentWrapper.innerHTML = DynamicRenderer.getFieldContentHtml(field);
                                        fieldWrapper.appendChild(contentWrapper);
                                        
                                        cardBody.appendChild(fieldWrapper);
                                        customElements.push(field);
                                    }
                                });
                            }
                        }
                    }
                });

                if (customElements.length > 0) {
                    // Initialize all custom elements using DynamicRenderer
                    DynamicRenderer.sections = customElements;
                    DynamicRenderer.init(this.projectData, stageId);
                }
                if (window.lucide) lucide.createIcons();
            }
        } catch (e) {
            console.error("[QCMS] Error injecting custom subfields:", e);
        }

        // 3. Sort all cards in formEl according to stageCfg.sections order
        try {
            const formEl = container.querySelector('[id$="Form"]') || container.firstElementChild;
            if (formEl && stageCfg && stageCfg.sections) {
                const orderMap = {};
                stageCfg.sections.forEach((sec, idx) => {
                    if (sec && sec.id) {
                        orderMap[sec.id] = idx;
                    }
                });

                const cards = Array.from(formEl.querySelectorAll(':scope > .glass-card.ds-card'));
                cards.sort((a, b) => {
                    const idA = a.dataset.secId || '';
                    const idB = b.dataset.secId || '';
                    const orderA = orderMap[idA] !== undefined ? orderMap[idA] : 999;
                    const orderB = orderMap[idB] !== undefined ? orderMap[idB] : 999;
                    return orderA - orderB;
                });

                // Re-append in the sorted order
                cards.forEach(card => formEl.appendChild(card));

                // Update circle numbers to match stage.section order (e.g. 6.1, 6.2) and hide duplicate inner "Section X - Title" headings
                let circleIdx = 1;
                cards.forEach(card => {
                    const circle = card.querySelector('.ds-card-header .ds-icon-circle');
                    const isApproval = card.dataset.secId && card.dataset.secId.includes('approval');
                    if (circle && !isApproval) {
                        const secNum = `${stageId}.${circleIdx++}`;
                        circle.innerHTML = secNum;
                        circle.style.minWidth = '28px';
                        circle.style.width = 'auto';
                        circle.style.padding = '0 6px';
                        circle.style.borderRadius = '50px';
                        circle.style.fontSize = '.7rem';
                        circle.style.fontWeight = '700';
                    }

                    // Hide redundant inner "Section X - ..." headings inside card body so title appears only once in header
                    card.querySelectorAll('.ds-card-body h6, .ds-card-body h5').forEach(heading => {
                        if (heading.closest('.card-edit-header')) return;
                        if (/^\s*Section\s+\d+/i.test(heading.textContent.trim())) {
                            heading.style.display = 'none';
                            const parentFlex = heading.closest('.d-flex');
                            if (parentFlex) {
                                const visibleSiblings = Array.from(parentFlex.children).filter(child => child !== heading && window.getComputedStyle(child).display !== 'none');
                                if (visibleSiblings.length === 1 && (visibleSiblings[0].tagName === 'BUTTON' || visibleSiblings[0].querySelector('button, .ds-btn') || visibleSiblings[0].classList.contains('ds-btn'))) {
                                    parentFlex.classList.remove('justify-content-between');
                                    parentFlex.classList.add('justify-content-end');
                                }
                            }
                        }
                    });
                });
            }
        } catch (e) {
            console.error("[QCMS] Error sorting section cards:", e);
        }

        // Fallback pass: ensure circle numbers are stageId.secNum and hide duplicate inner section headings
        try {
            const formEl = container.querySelector('[id$="Form"]') || container.firstElementChild;
            if (formEl) {
                const cards = Array.from(formEl.querySelectorAll(':scope > .glass-card.ds-card, .glass-card.ds-card'));
                let secIdx = 1;
                cards.forEach(card => {
                    const circle = card.querySelector('.ds-card-header .ds-icon-circle');
                    const isApproval = card.dataset.secId && card.dataset.secId.includes('approval');
                    if (circle && !isApproval) {
                        const secNum = `${stageId}.${secIdx++}`;
                        circle.innerHTML = secNum;
                        circle.style.minWidth = '28px';
                        circle.style.width = 'auto';
                        circle.style.padding = '0 6px';
                        circle.style.borderRadius = '50px';
                        circle.style.fontSize = '.7rem';
                        circle.style.fontWeight = '700';
                    }

                    card.querySelectorAll('.ds-card-body h6, .ds-card-body h5').forEach(heading => {
                        if (heading.closest('.card-edit-header')) return;
                        if (/^\s*Section\s+\d+/i.test(heading.textContent.trim())) {
                            heading.style.display = 'none';
                            const parentFlex = heading.closest('.d-flex');
                            if (parentFlex) {
                                const visibleSiblings = Array.from(parentFlex.children).filter(child => child !== heading && window.getComputedStyle(child).display !== 'none');
                                if (visibleSiblings.length === 1 && (visibleSiblings[0].tagName === 'BUTTON' || visibleSiblings[0].querySelector('button, .ds-btn') || visibleSiblings[0].classList.contains('ds-btn'))) {
                                    parentFlex.classList.remove('justify-content-between');
                                    parentFlex.classList.add('justify-content-end');
                                }
                            }
                        }
                    });
                });
            }
        } catch (e) {
            console.error("[QCMS] Error applying stage section numbering:", e);
        }

        // 4. Setup Section N/A (Applicable / Not Applicable) Toggles
        try {
            this.setupSectionNAToggles(container, stageCfg);
        } catch (e) {
            console.error("[QCMS] Error setting up section N/A toggles:", e);
        }

        this.applyPermissions(stageId);

    },

    setupSectionNAToggles(container, stageCfg) {
        if (!stageCfg || !stageCfg.sections) return;

        const predefinedCards = Array.from(container.querySelectorAll('.glass-card.ds-card'));

        stageCfg.sections.forEach((sec, sIdx) => {
            if (!sec) return;

            let cardEl = null;
            if (sec.id && typeof sec.id === 'string' && sec.id.startsWith('sec_')) {
                cardEl = container.querySelector(`#card_${sec.id}`);
            } else {
                const cardIdx = sec.card_index !== undefined ? sec.card_index : sIdx;
                cardEl = predefinedCards[cardIdx];
            }

            if (!cardEl) return;

            const headerEl = cardEl.querySelector('.ds-card-header');
            if (!headerEl) return;

            if (sec.allow_na) {
                headerEl.classList.add('d-flex', 'align-items-center', 'justify-content-between');

                let naWrap = headerEl.querySelector('.sec-na-toggle-wrap');
                if (!naWrap) {
                    naWrap = document.createElement('div');
                    naWrap.className = 'form-check form-switch mb-0 ms-auto sec-na-toggle-wrap';
                    naWrap.title = 'Toggle section applicability';
                    naWrap.onclick = (e) => e.stopPropagation();
                    naWrap.innerHTML = `
                        <input class="form-check-input section-na-toggle" type="checkbox" role="switch" checked data-sec-id="${sec.id}">
                        <label class="text-xs fw-semibold text-success ms-1 mb-0 sec-na-label">Applicable</label>
                    `;
                    headerEl.appendChild(naWrap);
                }

                const toggleInput = naWrap.querySelector('.section-na-toggle');
                const labelEl = naWrap.querySelector('.sec-na-label');

                const updateNAState = (isApplicable) => {
                    cardEl.dataset.applicable = isApplicable ? 'true' : 'false';
                    const cardBody = cardEl.querySelector('.ds-card-body') || cardEl;
                    if (isApplicable) {
                        labelEl.textContent = 'Applicable';
                        labelEl.className = 'text-xs fw-semibold text-success ms-1 mb-0 sec-na-label';
                        if (cardBody) {
                            cardBody.style.opacity = '1';
                            cardBody.style.filter = 'none';
                            cardBody.style.pointerEvents = 'auto';
                            cardBody.querySelectorAll('input, select, textarea, button').forEach(el => {
                                if (!el.classList.contains('section-na-toggle')) {
                                    el.disabled = false;
                                }
                            });
                        }
                    } else {
                        labelEl.textContent = 'Not Applicable (N/A)';
                        labelEl.className = 'text-xs fw-semibold text-secondary ms-1 mb-0 sec-na-label';
                        if (cardBody) {
                            cardBody.style.opacity = '0.45';
                            cardBody.style.filter = 'grayscale(0.5)';
                            cardBody.style.pointerEvents = 'none';
                            cardBody.querySelectorAll('input, select, textarea, button').forEach(el => {
                                if (!el.classList.contains('section-na-toggle')) {
                                    el.disabled = true;
                                }
                            });
                        }
                    }
                };

                const stageData = (this.projectData.workflows || []).find(w => w.stage_id === this.activeStageId)?.data || {};
                const savedSec = stageData[sec.id] || {};
                const isInitiallyApplicable = savedSec.applicable !== false;
                
                toggleInput.checked = isInitiallyApplicable;
                updateNAState(isInitiallyApplicable);

                toggleInput.onchange = (e) => {
                    updateNAState(e.target.checked);
                };
            }
        });
    },


    applyPermissions(stageId) {
        const user = JSON.parse(sessionStorage.getItem('user') || '{}');
        const roleName = (user.role && user.role.name) ? user.role.name : (user.role || '');
        const role = roleName.toLowerCase().replace(/[^a-z0-9]/g, '');
        const activeTracker = (this.projectData.stages || []).find(s => s.stage_number === stageId) || {};
        let isReviewer = (role === 'reviewer');
        const isStage8 = (stageId === this._stagesCfg.length);

        const stage8Tracker = (this.projectData.stages || []).find(s => s.stage_number === this._stagesCfg.length) || {};

        const isProjectRejected = this.projectData.status === 'Rejected' || 
                                  this.projectData.status === 'Stage 8 Rejected' || 
                                  (this.projectData.status && this.projectData.status.includes('Rejected')) ||
                                  (stage8Tracker && stage8Tracker.status === 'Rejected');

        const isSubmitted = activeTracker.status === 'Submitted For Review' && !isProjectRejected;
        const isApproved = (activeTracker.status === 'Completed' || activeTracker.status === 'Approved') && !isProjectRejected;

        // Check if role is allowed to edit/add details for this stage
        let allowedToEdit = false;
        if (stageId === 1) {
            allowedToEdit = ['teamleader', 'teammember', 'admin', 'superadmin'].includes(role);
        } else if (stageId >= 2 && stageId <= this._stagesCfg.length) {
            if (stageId === 6) {
                allowedToEdit = ['teammember', 'teamleader', 'reviewer', 'facilitator', 'admin', 'superadmin'].includes(role);
            } else {
                allowedToEdit = ['teammember', 'teamleader', 'admin', 'superadmin'].includes(role);
            }
        }

        const isReadOnly = !allowedToEdit || (isApproved && !isProjectRejected) || isSubmitted;

        const reviewPanel = document.getElementById('reviewPanel');
        const stage8Notice = document.getElementById('stage8Notice');
        const stage8AdminApproval = document.getElementById('stage8AdminApproval');
        const saveBtn = document.getElementById('saveDraftBtn');
        const submitBtn = document.getElementById('submitBtn');
        const lockedNotice = document.getElementById('lockedStagesNotice');
        const exportBtn = document.getElementById('exportReportBtn');
        const qcBtn = document.getElementById('qcAnalysisBtn');

        const isStage8Completed = stage8Tracker.status === 'Completed' || this.projectData.status === 'Closed' || this.projectData.status === 'Stage 8 Reviewer Approved';
        
        if (exportBtn) {
            if (isStage8Completed) {
                exportBtn.classList.remove('d-none');
            } else {
                exportBtn.classList.add('d-none');
            }
        }
        if (qcBtn) {
            if (isStage8Completed) {
                qcBtn.classList.remove('d-none');
            } else {
                qcBtn.classList.add('d-none');
            }
        }

        if (isStage8Completed && sessionStorage.getItem('auto_download_report_' + this.projectId) === 'true') {
            sessionStorage.removeItem('auto_download_report_' + this.projectId);
            this.exportReport();
        }

        let isStageLocked = false;
        if (stageId > 1 && !isProjectRejected) {
            const prevTracker = (this.projectData.stages || []).find(s => s.stage_number === stageId - 1) || {};
            if (prevTracker.status !== 'Completed' && prevTracker.status !== 'Approved') {
                isStageLocked = true;
            }
        }

        // Render Rejection Alert Banner if Project is Rejected at Stage 8
        let rejectionBanner = document.getElementById('projectRejectionNotice');
        if (isProjectRejected) {
            if (!rejectionBanner) {
                rejectionBanner = document.createElement('div');
                rejectionBanner.id = 'projectRejectionNotice';
                rejectionBanner.className = 'alert alert-danger fade-in mb-4 d-flex align-items-center justify-content-between p-3';
                rejectionBanner.style.cssText = 'background: rgba(239,68,68,0.08); border-left: 4px solid #ef4444; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);';
                
                const container = document.getElementById('stageContentContainer')?.parentElement;
                if (container) {
                    container.insertBefore(rejectionBanner, container.firstChild);
                }
            }
            rejectionBanner.innerHTML = `
                <div class="d-flex align-items-start gap-3">
                    <div class="rounded-circle d-flex align-items-center justify-content-center flex-shrink-0" style="width:36px;height:36px;background:rgba(239,68,68,0.15);border:1px solid #ef4444;">
                        <i data-lucide="alert-octagon" style="width:20px;height:20px;color:#ef4444;"></i>
                    </div>
                    <div>
                        <h6 class="mb-1 fw-bold text-danger">⚠️ Stage 8 Approval Rejected by Reviewer</h6>
                        <p class="mb-0 text-xs text-secondary">The reviewer rejected the final approval submission. <strong>All stages (Stage 1 through Stage 8) are now unlocked for editing and revision</strong>. You may navigate to any stage (Stage 1, 2, 3, 4, 5, 6, 7, or 8), update inputs, and re-submit Stage 8 when ready.</p>
                    </div>
                </div>
            `;
            rejectionBanner.classList.remove('d-none');
            if (window.lucide) lucide.createIcons();
        } else if (rejectionBanner) {
            rejectionBanner.classList.add('d-none');
        }

        const meetingsSec = document.getElementById('stageMeetingsSection');

        if (isStageLocked) {
            lockedNotice.classList.remove('d-none');
            document.getElementById('stageContentContainer').classList.add('d-none');
            saveBtn.classList.add('d-none');
            submitBtn.classList.add('d-none');
            reviewPanel.classList.add('d-none');
            if (stage8Notice) stage8Notice.classList.add('d-none');
            if (stage8AdminApproval) stage8AdminApproval.classList.add('d-none');
            if (meetingsSec) meetingsSec.classList.add('d-none');
        } else {
            lockedNotice.classList.add('d-none');
            document.getElementById('stageContentContainer').classList.remove('d-none');
            if (meetingsSec) {
                meetingsSec.classList.remove('d-none');
                this.loadMeetings();
            }

            // Stage 8 review is handled by Reviewer inline, or closure panel by admin/facilitator
            if (isStage8) {
                if (isReviewer && isSubmitted) {
                    reviewPanel.classList.remove('d-none');
                } else {
                    reviewPanel.classList.add('d-none');
                }
                
                const isAdmin = ['admin', 'superadmin'].includes(role);
                
                if (stage8Notice) {
                    const showNotice = isReviewer && isSubmitted && !allowedToEdit;
                    stage8Notice.classList.toggle('d-none', !showNotice);
                }
                
                if (stage8AdminApproval) {
                    const showApproval = isAdmin && this.projectData.status === 'Pending Closure';
                    stage8AdminApproval.classList.toggle('d-none', !showApproval);
                }
                
                if (window.lucide) lucide.createIcons();
            } else {
                if (stage8Notice) stage8Notice.classList.add('d-none');
                if (stage8AdminApproval) stage8AdminApproval.classList.add('d-none');
                // Show reviewer panel for Stage 1 ONLY
                if (stageId === 1 && isReviewer && isSubmitted) {
                    reviewPanel.classList.remove('d-none');
                } else {
                    reviewPanel.classList.add('d-none');
                }
            }

            // Disable form if submitted or approved
            if (isReadOnly) {
                document.getElementById('stageContentContainer').querySelectorAll('input, textarea, select, button').forEach(el => el.disabled = true);
                saveBtn.classList.add('d-none');
                submitBtn.classList.add('d-none');
            } else {
                saveBtn.classList.remove('d-none');
                submitBtn.classList.remove('d-none');
                saveBtn.disabled = false;
                submitBtn.disabled = false;
                
                const isReviewStage = [1, 8].includes(stageId);
                if (isReviewStage) {
                    submitBtn.innerHTML = `<i data-lucide="send" style="width:14px;height:14px;"></i> Submit For Review`;
                } else {
                    submitBtn.innerHTML = `<i data-lucide="send" style="width:14px;height:14px;"></i> Submit`;
                }
                if (window.lucide) lucide.createIcons();
            }

            if (isSubmitted && !isReviewer) {
                submitBtn.classList.remove('d-none');
                submitBtn.disabled = true;
                const isReviewStage = [1, 8].includes(stageId);
                if (isReviewStage) {
                    submitBtn.innerHTML = `<i data-lucide="send" style="width:14px;height:14px;"></i> Awaiting Review`;
                } else {
                    submitBtn.innerHTML = `<i data-lucide="check-circle" style="width:14px;height:14px;"></i> Submitted`;
                }
                if (window.lucide) lucide.createIcons();
            }
        }

        // Synchronize Bottom Action Bar buttons with Top Action Bar buttons
        const bottomContainer = document.getElementById('bottomStageActionsContainer');
        const saveBtnBottom = document.getElementById('saveDraftBtnBottom');
        const submitBtnBottom = document.getElementById('submitBtnBottom');
        if (bottomContainer) {
            const isSaveHidden = !saveBtn || saveBtn.classList.contains('d-none');
            const isSubmitHidden = !submitBtn || submitBtn.classList.contains('d-none');

            if (isSaveHidden && isSubmitHidden) {
                bottomContainer.classList.add('d-none');
            } else {
                bottomContainer.classList.remove('d-none');
                bottomContainer.style.setProperty('display', 'flex', 'important');
                bottomContainer.style.setProperty('flex-direction', 'row', 'important');
                bottomContainer.style.setProperty('justify-content', 'flex-end', 'important');
                bottomContainer.style.setProperty('align-items', 'center', 'important');

                if (saveBtnBottom && saveBtn) {
                    saveBtnBottom.className = saveBtn.className;
                    saveBtnBottom.disabled = saveBtn.disabled;
                    saveBtnBottom.innerHTML = saveBtn.innerHTML;
                    saveBtnBottom.style.setProperty('display', isSaveHidden ? 'none' : 'inline-flex', 'important');
                    saveBtnBottom.style.setProperty('align-items', 'center', 'important');
                }

                if (submitBtnBottom && submitBtn) {
                    submitBtnBottom.className = submitBtn.className;
                    submitBtnBottom.disabled = submitBtn.disabled;
                    submitBtnBottom.innerHTML = submitBtn.innerHTML;
                    submitBtnBottom.style.setProperty('display', isSubmitHidden ? 'none' : 'inline-flex', 'important');
                    submitBtnBottom.style.setProperty('align-items', 'center', 'important');
                }
            }
            if (window.lucide) lucide.createIcons();
        }
    },

    clearValidationHighlights() {
        const container = document.getElementById('stageContentContainer');
        if (!container) return;
        container.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
        container.querySelectorAll('[style*="border-color"]').forEach(el => {
            el.style.borderColor = '';
            el.style.boxShadow = '';
            el.style.borderWidth = '';
            el.style.borderStyle = '';
            el.style.borderRadius = '';
            el.style.padding = '';
        });
        container.querySelectorAll('.is-invalid-feedback').forEach(el => el.remove());
    },

    highlightInvalidFields(invalidFields) {
        console.log("[QCMS] highlightInvalidFields called with:", invalidFields);
        this.clearValidationHighlights();
        let firstInvalidElement = null;
        invalidFields.forEach(fieldId => {
            console.log("[QCMS] processing fieldId:", fieldId);
            const el = document.getElementById(fieldId);
            if (el) {
                console.log("[QCMS] adding is-invalid class to:", fieldId);
                el.classList.add('is-invalid');
                if (!firstInvalidElement) firstInvalidElement = el;
                const parent = el.closest('.ds-field');
                if (parent && !parent.querySelector('.is-invalid-feedback')) {
                    const label = parent.querySelector('.ds-label');
                    const labelText = label ? label.textContent.replace('*', '').trim() : 'This field';
                    const feedback = document.createElement('div');
                    feedback.className = 'is-invalid-feedback';
                    feedback.textContent = `${labelText} is required.`;
                    parent.appendChild(feedback);
                }
            } else {
                const container = document.getElementById(fieldId);
                if (container) {
                    console.log("[QCMS] styling container as invalid:", fieldId);
                    container.classList.add('is-invalid');
                    container.style.borderColor = 'rgb(var(--ds-red-rgb))';
                    container.style.borderWidth = '1px';
                    container.style.borderStyle = 'solid';
                    container.style.borderRadius = 'var(--ds-radius-md)';
                    container.style.padding = '8px';
                    if (!firstInvalidElement) firstInvalidElement = container;
                    const feedback = document.createElement('div');
                    feedback.className = 'is-invalid-feedback';
                    feedback.style.marginTop = '8px';
                    if (fieldId === 'teamMembersContainer') {
                        feedback.textContent = 'At least one team member must be assigned.';
                    } else if (fieldId === 'milestonesContainer') {
                        feedback.textContent = 'At least one milestone must be defined.';
                    } else {
                        feedback.textContent = 'This section is incomplete.';
                    }
                    container.parentNode.appendChild(feedback);
                } else {
                    console.warn("[QCMS] element not found in DOM for highlighting:", fieldId);
                }
            }
        });
        if (firstInvalidElement) {
            console.log("[QCMS] scrolling to element:", firstInvalidElement);
            firstInvalidElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    },

    async saveDraft() {
        const module = StageModules[this.activeStageId];
        if (!module) return;

        this.clearValidationHighlights();
        try {
            const data = module.collectData();

            // Auto-merge custom fields/cards data using DynamicRenderer
            const customElements = [];
            const stageCfg = (this._stagesCfg || [])[this.activeStageId - 1];
            if (stageCfg && stageCfg.sections) {
                stageCfg.sections.forEach(sec => {
                    if (sec.id.startsWith('sec_')) {
                        customElements.push(sec);
                    }
                    if (sec.fields) {
                        sec.fields.forEach(field => {
                            customElements.push(field);
                        });
                    }
                });
            }
            if (customElements.length > 0) {
                const origSecs = DynamicRenderer.sections;
                DynamicRenderer.sections = customElements;
                const customData = DynamicRenderer.collectData();
                Object.assign(data, customData);
                DynamicRenderer.sections = origSecs; // restore
            }


            // Use stage1/save for Stage 1, generic route for 2-8
            const route = this.activeStageId === 1 ? `/projects/${this.projectId}/stage1/save` : `/projects/${this.projectId}/stage/${this.activeStageId}/save`;
            await api.post(route, data);


            // Keep in-memory projectData in sync
            if (this.projectData) {
                if (!this.projectData.workflows) {
                    this.projectData.workflows = [];
                }
                let wf = this.projectData.workflows.find(w => w.stage_id === this.activeStageId);
                if (!wf) {
                    wf = { stage_id: this.activeStageId, data: {} };
                    this.projectData.workflows.push(wf);
                }
                wf.data = data;
            }

            QCMS.toast(`Stage ${this.activeStageId} draft saved successfully.`, 'success');
        } catch (e) {
            QCMS.toast('Save failed: ' + e.message, 'error');
        }
    },

    validateStageForSubmission(stageId, activePane) {
        if (!activePane) return { valid: true, emptyFields: [], missingSections: [], missingDetails: [] };

        const stageCfg = (this._stagesCfg || [])[stageId - 1];
        const emptyFields = [];
        const missingSections = [];
        const missingDetails = [];

        const addInvalid = (el, secName, fieldName = '') => {
            if (el) {
                if (!emptyFields.includes(el)) emptyFields.push(el);
                if (secName && !missingSections.includes(secName)) {
                    missingSections.push(secName);
                }
                if (secName && fieldName) {
                    const detail = `${secName} → ${fieldName}`;
                    if (!missingDetails.includes(detail)) missingDetails.push(detail);
                } else if (secName && !missingDetails.includes(secName)) {
                    missingDetails.push(secName);
                }
            }
        };

        const isInputEmpty = (input) => {
            if (!input) return true;
            if (input.type === 'checkbox' || input.type === 'radio') return false;
            if (input.tagName.toLowerCase() === 'select') {
                const val = (input.value || '').trim().toLowerCase();
                return !val || val === '-- select option --' || val === '-- select --' || val === '- select -' || (val === '0' && input.classList.contains('require-select'));
            }
            return !(input.value || '').trim();
        };

        const getColumnOrLabelName = (input, cardEl) => {
            if (!input) return '';
            const placeholder = (input.placeholder || '').replace(/^e\.g\.?\s*/i, '').trim();
            if (placeholder) return placeholder;

            const labelEl = input.labels && input.labels[0] ? input.labels[0] : (input.id ? cardEl.querySelector(`label[for="${input.id}"]`) : null);
            if (labelEl) {
                const txt = labelEl.textContent.replace(/\*+/g, '').trim();
                if (txt) return txt;
            }

            const colParent = input.closest('[class*="col-"]');
            if (colParent && colParent.parentElement) {
                const row = colParent.parentElement;
                const colIndex = Array.from(row.children).indexOf(colParent);
                const headerRow = row.parentElement ? row.parentElement.querySelector('.row.text-muted, thead tr') : null;
                if (headerRow && headerRow.children[colIndex]) {
                    const headerTxt = headerRow.children[colIndex].textContent.replace(/\*+/g, '').trim();
                    if (headerTxt) return headerTxt;
                }
            }

            if (input.name) return input.name.replace(/_/g, ' ');
            if (input.id) return input.id.replace(/^[a-z0-9]+_/, '').replace(/_/g, ' ');
            return 'Required Field';
        };

        const allCards = Array.from(activePane.querySelectorAll('.ds-card, .glass-card, .card, [class*="card"]'));

        allCards.forEach((cardEl, cIdx) => {
            if (!cardEl || cardEl.closest('.d-none') || cardEl.offsetParent === null) return;
            if (cardEl.dataset.applicable === 'false' || cardEl.classList.contains('section-na')) return;

            const headerEl = cardEl.querySelector('h5, h6, .card-title, .ds-card-title, .ds-card-header');
            const headerHtml = headerEl ? headerEl.innerHTML : '';
            const headerText = headerEl ? headerEl.textContent.trim() : `Section ${cIdx + 1}`;
            const cleanSecTitle = headerText.replace(/\s*\*.*$/, '').replace(/\*+/g, '').trim();

            const isAsteriskRequired = headerHtml.includes('text-danger') || headerText.includes('*') || cardEl.dataset.required === 'true';

            let cfgSecRequired = false;
            if (stageCfg && stageCfg.sections) {
                const matchingSec = stageCfg.sections.find(s => s && s.label && cleanSecTitle.toLowerCase().includes(s.label.trim().toLowerCase()));
                if (matchingSec && matchingSec.required !== false) {
                    cfgSecRequired = true;
                }
            }

            const isSecRequired = isAsteriskRequired || cfgSecRequired;

            if (isSecRequired) {
                const visibleInputs = Array.from(cardEl.querySelectorAll('input:not([type="button"]):not([type="submit"]):not([type="checkbox"]):not([type="radio"]):not([type="hidden"]):not([readonly]):not(:disabled), select:not([readonly]):not(:disabled), textarea:not([readonly]):not(:disabled)'));

                visibleInputs.forEach(input => {
                    if (input.closest('.d-none') || input.offsetParent === null) return;
                    if (input.classList.contains('ignore-validation')) return;
                    if (isInputEmpty(input)) {
                        const colName = getColumnOrLabelName(input, cardEl);
                        addInvalid(input, cleanSecTitle, colName);
                    }
                });

                const dynContainers = cardEl.querySelectorAll('[id$="Container"], [id$="Table"], .table-responsive, table, .dyn-container');
                dynContainers.forEach(container => {
                    if (container.closest('.d-none') || container.offsetParent === null) return;

                    const rowSelector = 'tbody tr, .row.dyn-row, .row.align-items-center, .s1-row, .s2-row, .s3-row, .s4-row, .s5-row, .s6-task-row, .s6-resource-row, .s7-row, .s8-row, .team-member-row, .mapping-row, .why-row, .item-row, .countermeasure-row, .resource-row, [class*="-row"]';
                    const rows = container.querySelectorAll(rowSelector);

                    if (rows.length === 0) {
                        addInvalid(cardEl, cleanSecTitle, 'At least 1 row entry is required');
                    } else {
                        rows.forEach((row, rIdx) => {
                            const rowInputs = row.querySelectorAll('input:not([type="button"]):not([type="hidden"]):not([readonly]):not(:disabled), select:not([readonly]):not(:disabled), textarea:not([readonly]):not(:disabled)');
                            rowInputs.forEach(rowInp => {
                                if (isInputEmpty(rowInp)) {
                                    const colName = getColumnOrLabelName(rowInp, cardEl);
                                    addInvalid(rowInp, cleanSecTitle, colName ? `${colName} (Row ${rIdx + 1})` : `Row ${rIdx + 1}`);
                                }
                            });
                        });
                    }
                });

                const fileDropzones = cardEl.querySelectorAll('.border-dashed, [id*="upload"], [id*="evidence"], [id*="file"]');
                fileDropzones.forEach(zone => {
                    if (zone.closest('.d-none') || zone.offsetParent === null) return;
                    const hasFile = zone.querySelector('.uploaded-file-link, .file-attached-badge, [data-file-url], input[type="file"]:valid') ||
                                    (zone.dataset && zone.dataset.fileUploaded === 'true');
                    if (!hasFile) {
                        addInvalid(zone, cleanSecTitle, 'Evidence / File Upload');
                    }
                });
            }
        });

        return {
            valid: emptyFields.length === 0,
            emptyFields,
            missingSections,
            missingDetails
        };
    },

    showSubmissionWarningModal(stageId) {
        return new Promise((resolve) => {
            let modalEl = document.getElementById('stageSubmissionModal');
            if (!modalEl) {
                modalEl = document.createElement('div');
                modalEl.id = 'stageSubmissionModal';
                modalEl.className = 'modal fade';
                modalEl.setAttribute('tabindex', '-1');
                modalEl.setAttribute('aria-hidden', 'true');
                modalEl.setAttribute('data-bs-backdrop', 'static');
                document.body.appendChild(modalEl);
            }

            const isReviewStage = [1, 8].includes(stageId);
            const submitLabel = isReviewStage ? `Stage ${stageId} for Review` : `Stage ${stageId}`;

            modalEl.innerHTML = `
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content border-0 shadow-lg" style="border-radius: 16px; overflow: hidden;">
                        <div class="modal-header border-0 bg-warning-subtle py-3 px-4">
                            <h5 class="modal-title fw-bold text-dark d-flex align-items-center gap-2" style="font-size: 1.1rem;">
                                <span class="rounded-circle bg-warning text-dark d-flex align-items-center justify-content-center" style="width: 32px; height: 32px; flex-shrink:0;">
                                    <i data-lucide="alert-triangle" style="width: 18px; height: 18px;"></i>
                                </span>
                                Confirm Stage ${stageId} Submission
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body p-4">
                            <div class="alert alert-warning border-0 p-3 mb-3 rounded-3" style="background: rgba(245, 158, 11, 0.1); border-left: 4px solid #f59e0b !important;">
                                <p class="mb-0 text-sm fw-bold text-dark d-flex align-items-start gap-2">
                                    <span>⚠️ <strong>Warning:</strong> Once submitted, all inputs, attachments, and changes made in Stage ${stageId} will be locked and cannot be edited.</span>
                                </p>
                            </div>
                            <p class="text-secondary text-xs mb-0">
                                Please ensure all entered section details, tables, and uploaded documents are complete and accurate before proceeding. Are you sure you want to finalize and submit ${submitLabel}?
                            </p>
                        </div>
                        <div class="modal-footer border-0 bg-light-subtle py-3 px-4 d-flex justify-content-end gap-2">
                            <button type="button" class="ds-btn ds-btn-ghost text-xs" data-bs-dismiss="modal">
                                <i data-lucide="x" style="width: 14px; height: 14px; margin-right: 4px;"></i> Cancel &amp; Review
                            </button>
                            <button type="button" class="ds-btn ds-btn-primary text-xs" id="confirmStageSubmitBtn">
                                <i data-lucide="send" style="width: 14px; height: 14px; margin-right: 4px;"></i> Confirm &amp; Submit ${submitLabel}
                            </button>
                        </div>
                    </div>
                </div>
            `;

            if (window.lucide) lucide.createIcons();

            const bsModal = new bootstrap.Modal(modalEl);
            let resolved = false;

            const confirmBtn = modalEl.querySelector('#confirmStageSubmitBtn');
            confirmBtn.onclick = () => {
                resolved = true;
                bsModal.hide();
                resolve(true);
            };

            modalEl.addEventListener('hidden.bs.modal', () => {
                if (!resolved) resolve(false);
            }, { once: true });

            bsModal.show();
        });
    },

    async submitForReview() {
        console.log("[QCMS] submitForReview started for activeStageId:", this.activeStageId);
        const module = StageModules[this.activeStageId];
        if (!module) {
            console.error("[QCMS] active stage module not found!");
            return;
        }

        this.clearValidationHighlights();

        // 1. Template-driven mandatory section & input validation
        const activePane = document.getElementById('stageContentContainer') || document.querySelector('.tab-pane.active') || document.body;
        if (activePane) {
            const validation = this.validateStageForSubmission(this.activeStageId, activePane);
            if (!validation.valid) {
                validation.emptyFields.forEach(f => {
                    if (f && f.classList) {
                        f.classList.add('is-invalid');
                        f.style.border = '2px solid var(--ds-danger)';
                        f.style.boxShadow = '0 0 0 0.25rem rgba(239, 68, 68, 0.25)';

                        const removeHighlight = function() {
                            this.classList.remove('is-invalid');
                            this.style.border = '';
                            this.style.boxShadow = '';
                        };
                        f.addEventListener('input', removeHighlight, { once: true });
                        f.addEventListener('change', removeHighlight, { once: true });
                    }
                });

                let secMsg = ' Please fill out all mandatory sections and fields before submitting.';
                if (validation.missingDetails && validation.missingDetails.length > 0) {
                    secMsg = ` Mandatory field(s) missing:\n• ${validation.missingDetails.slice(0, 4).join('\n• ')}${validation.missingDetails.length > 4 ? '\n• and more...' : ''}`;
                } else if (validation.missingSections && validation.missingSections.length > 0) {
                    secMsg = ` Mandatory section(s) incomplete: ${validation.missingSections.join(', ')}.`;
                }

                QCMS.toast(`Cannot submit Stage ${this.activeStageId}:${secMsg}`, 'error');

                const targetEl = validation.emptyFields[0];
                if (targetEl) {
                    if (typeof targetEl.scrollIntoView === 'function') {
                        targetEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }
                    if (typeof targetEl.focus === 'function') {
                        targetEl.focus();
                    }
                }
                return;
            }
        }

        const isReviewStage = [1, 8].includes(this.activeStageId);
        const userConfirmed = await this.showSubmissionWarningModal(this.activeStageId);
        if (!userConfirmed) return;
        try {
            const data = module.collectData();

            // Auto-merge custom fields/cards data using DynamicRenderer
            const customElements = [];
            const stageCfg = (this._stagesCfg || [])[this.activeStageId - 1];
            if (stageCfg && stageCfg.sections) {
                stageCfg.sections.forEach(sec => {
                    if (sec.id.startsWith('sec_')) {
                        customElements.push(sec);
                    }
                    if (sec.fields) {
                        sec.fields.forEach(field => {
                            customElements.push(field);
                        });
                    }
                });
            }
            if (customElements.length > 0) {
                const origSecs = DynamicRenderer.sections;
                DynamicRenderer.sections = customElements;
                const customData = DynamicRenderer.collectData();
                Object.assign(data, customData);
                DynamicRenderer.sections = origSecs; // restore
            }


            const routeSave = this.activeStageId === 1 ? `/projects/${this.projectId}/stage1/save` : `/projects/${this.projectId}/stage/${this.activeStageId}/save`;
            const routeSubmit = this.activeStageId === 1 ? `/projects/${this.projectId}/stage1/submit` : `/projects/${this.projectId}/stage/${this.activeStageId}/submit`;



            
            await api.post(routeSave, data);
            await api.post(routeSubmit, {});
            QCMS.toast(isReviewStage ? `Stage ${this.activeStageId} submitted for review!` : `Stage ${this.activeStageId} submitted!`, 'success');
            setTimeout(() => location.reload(), 1000);
        } catch (e) {
            console.error("[QCMS] submission caught exception:", e);
            const errors = e.errors || [];
            const msg = errors.length ? 'Incomplete: ' + errors.join(', ') : e.message;

            // Map backend validation errors to fields if possible
            const invalidFields = [];
            errors.forEach(err => {
                if (err.includes("Team")) {
                    invalidFields.push('teamMembersContainer');
                }
                if (err.includes("5W2H")) {
                    const fields_5w2h = ['s1_5w2h_what', 's1_5w2h_where', 's1_5w2h_when', 's1_5w2h_who', 's1_5w2h_why', 's1_5w2h_how_discovered', 's1_5w2h_how_big', 's1_5w2h_problem_definition'];
                    fields_5w2h.forEach(f => {
                        const val = document.getElementById(f)?.value;
                        if (!val) invalidFields.push(f);
                    });
                }
                if (err.includes("Current Performance")) {
                    invalidFields.push('s1_cp_kpi');
                }
                if (err.includes("Justification")) {
                    invalidFields.push('s1_j_why');
                }
                if (err.includes("Theme")) {
                    ['s1_tts_theme', 's1_tts_current', 's1_tts_target'].forEach(f => {
                        const val = document.getElementById(f)?.value;
                        if (!val) invalidFields.push(f);
                    });
                }
                if (err.includes("timeline") || err.includes("milestones")) {
                    invalidFields.push('milestonesContainer');
                }
            });

            console.log("[QCMS] mapping results, invalidFields:", invalidFields);
            if (invalidFields.length > 0) {
                this.highlightInvalidFields(invalidFields);
            }

            QCMS.toast(msg, 'error');
        }
    },

    async reviewStage(decision) {
        const comments = document.getElementById('reviewComments').value;
        const labels = { approve: 'Approve', reject: 'Reject', send_back: 'Send Back' };
        if (!confirm(`Confirm: ${labels[decision]} Stage ${this.activeStageId}?`)) return;
        try {
            const route = this.activeStageId === 1 ? `/projects/${this.projectId}/stage1/review` : `/projects/${this.projectId}/stage/${this.activeStageId}/review`;
            await api.post(route, { decision, comments });
            QCMS.toast(`Stage ${this.activeStageId} ${labels[decision]}d successfully.`, 'success');
            
            if (this.activeStageId === this._stagesCfg.length && decision === 'approve') {
                sessionStorage.setItem('auto_download_report_' + this.projectId, 'true');
            }
            
            setTimeout(() => location.reload(), 1000);
        } catch (e) {
            QCMS.toast(e.message, 'error');
        }
    },

    facRequestModal: null,

    openFacilitatorRequestModal() {
        if (!this.facRequestModal) {
            this.facRequestModal = new bootstrap.Modal(document.getElementById('requestFacilitatorModal'));
        }
        document.getElementById('facilitatorRequestForm').reset();
        // Update modal title to show which stage the request is for
        const titleEl = document.getElementById('facModalTitle');
        if (titleEl) {
            titleEl.innerHTML = `<i data-lucide="message-square" class="me-2 text-primary" style="width:20px;height:20px;vertical-align:text-bottom;"></i> Approach Facilitator — Stage ${this.activeStageId || 1}`;
            if (window.lucide) lucide.createIcons();
        }
        this.facRequestModal.show();
    },

    async submitFacilitatorRequest() {
        const message = document.getElementById('assistanceMessage').value.trim();
        if (!message) return;
        try {
            await api.post(`/projects/${this.projectId}/request-facilitator-assistance`, {
                message,
                stage_id: this.activeStageId || 1
            });
            QCMS.toast('Assistance request sent to facilitator successfully.', 'success');
            if (this.facRequestModal) {
                this.facRequestModal.hide();
            }
        } catch (e) {
            QCMS.toast('Failed to send request: ' + e.message, 'error');
        }
    },

    meetingModal: null,

    openMeetingModal() {
        if (!this.meetingModal) {
            this.meetingModal = new bootstrap.Modal(document.getElementById('scheduleMeetingModal'));
        }
        document.getElementById('meetingForm').reset();
        
        // Set default time to 1 hour from now
        const now = new Date();
        now.setHours(now.getHours() + 1);
        now.setMinutes(0);
        now.setSeconds(0);
        now.setMilliseconds(0);
        
        const pad = (n) => n.toString().padStart(2, '0');
        const formattedDate = `${now.getFullYear()}-${pad(now.getMonth()+1)}-${pad(now.getDate())}T${pad(now.getHours())}:${pad(now.getMinutes())}`;
        document.getElementById('meetingDateTime').value = formattedDate;
        
        this.onMeetingTypeChange('online');
        this.meetingModal.show();
    },

    onMeetingTypeChange(type) {
        const urlContainer = document.getElementById('meetingUrlContainer');
        const urlInput = document.getElementById('meetingUrl');
        if (type === 'online') {
            urlContainer.style.display = 'block';
            urlInput.required = true;
        } else {
            urlContainer.style.display = 'none';
            urlInput.required = false;
            urlInput.value = '';
        }
    },

    async loadMeetings() {
        const listContainer = document.getElementById('stageMeetingsList');
        if (!listContainer) return;
        
        listContainer.innerHTML = `
            <div class="text-center py-4 text-muted">
                <div class="spinner-border spinner-border-sm text-primary opacity-25" role="status"></div>
                <p class="text-xs mt-2">Loading stage meetings...</p>
            </div>
        `;
        if (window.lucide) lucide.createIcons();

        try {
            const meetings = await api.get(`/projects/${this.projectId}/stage/${this.activeStageId}/meetings`);
            if (!meetings || !meetings.length) {
                listContainer.innerHTML = `
                    <div class="text-center py-4 text-muted">
                        <i data-lucide="calendar-x" class="mb-2 opacity-50" style="width:24px;height:24px;"></i>
                        <p class="text-xs mb-0">No meetings scheduled for this stage.</p>
                    </div>
                `;
                if (window.lucide) lucide.createIcons();
                return;
            }

            listContainer.innerHTML = meetings.map(m => {
                const dateStr = new Date(m.scheduled_at).toLocaleDateString(undefined, {
                    weekday: 'short', month: 'short', day: 'numeric', year: 'numeric'
                });
                const timeStr = new Date(m.scheduled_at).toLocaleTimeString(undefined, {
                    hour: '2-digit', minute: '2-digit'
                });
                const duration = m.duration;
                
                const isOnline = m.meeting_type === 'online';
                const actionBtn = isOnline && m.url ? `
                    <a href="${m.url}" target="_blank" class="ds-btn ds-btn-primary ds-btn-sm mt-2">
                        <i data-lucide="video" class="me-1" style="width:12px;height:12px;"></i> Join Meeting
                    </a>
                ` : `
                    <span class="ds-badge ds-badge-sm mt-2" style="background:rgba(var(--ds-info-rgb),0.12);color:var(--ds-info);width:fit-content;display:inline-block;">
                        <i data-lucide="map-pin" class="me-1" style="width:10px;height:10px;vertical-align:middle;"></i> Offline (No URL)
                    </span>
                `;

                return `
                    <div class="activity-item pb-3 mb-3 border-bottom fade-in">
                        <div class="activity-dot bg-primary"></div>
                        <div class="activity-content d-flex flex-wrap flex-sm-nowrap justify-content-between align-items-start gap-3">
                            <div class="v-stack">
                                <h6 class="fw-bold mb-1" style="color:var(--ds-text-main);">${m.title}</h6>
                                <span class="text-xs ds-text-secondary">
                                    <i data-lucide="clock" class="me-1" style="width:12px;height:12px;vertical-align:text-top;"></i>
                                    ${dateStr} @ ${timeStr} (${duration} mins)
                                </span>
                                ${actionBtn}
                            </div>
                            <span class="ds-badge ds-badge-sm ${isOnline ? 'blue' : 'gray'}">
                                ${isOnline ? 'Online' : 'Offline'}
                            </span>
                        </div>
                    </div>
                `;
            }).join('');
            if (window.lucide) lucide.createIcons();
        } catch (e) {
            console.error(e);
            listContainer.innerHTML = `
                <div class="text-center py-4 text-danger text-xs">
                    <i data-lucide="alert-triangle" class="mb-1" style="width:18px;height:18px;"></i>
                    Failed to load meetings.
                </div>
            `;
            if (window.lucide) lucide.createIcons();
        }
    },

    async saveMeeting() {
        const title = document.getElementById('meetingTitle').value.trim();
        const meeting_type = document.getElementById('meetingType').value;
        const scheduled_at = document.getElementById('meetingDateTime').value;
        const duration = document.getElementById('meetingDuration').value;
        const url = document.getElementById('meetingUrl').value.trim();
        
        if (!title || !scheduled_at || !duration) {
            QCMS.toast('Please fill all required fields.', 'error');
            return;
        }
        
        if (meeting_type === 'online' && !url) {
            QCMS.toast('Meeting URL is required for online meetings.', 'error');
            return;
        }

        try {
            await api.post(`/projects/${this.projectId}/stage/${this.activeStageId}/meetings`, {
                title,
                meeting_type,
                scheduled_at,
                duration,
                url
            });
            QCMS.toast('Meeting scheduled successfully!', 'success');
            if (this.meetingModal) this.meetingModal.hide();
            this.loadMeetings();
        } catch (e) {
            QCMS.toast('Failed to schedule meeting: ' + e.message, 'error');
        }
    },

    async adminApproveClose() {
        const btn = document.getElementById('adminApproveCloseBtn');
        if (btn) btn.disabled = true;
        
        try {
            const res = await api.post(`/admin/projects/${this.projectId}/close`);
            QCMS.toast(res.message || 'Project approved & closed successfully!', 'success');
            
            sessionStorage.setItem('auto_download_report_' + this.projectId, 'true');
            
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } catch (e) {
            QCMS.toast('Failed to close project: ' + e.message, 'error');
            if (btn) btn.disabled = false;
        }
    },

    async exportReport() {
        if (window.FeatureEngine) {
            const isPdfEnabled = FeatureEngine.isEnabled('reports.pdf');
            if (!isPdfEnabled) {
                FeatureEngine.showDisabledModuleNotice('reports.pdf');
                return;
            }
        }
        QCMS.toast('Generating report...', 'info');
        const filename = `${this.projectData.project_uid || 'Project'}_8D_Report.pdf`;
        await api.downloadFile(`/reports/export/pdf/${this.projectId}`, filename);
    },

    async renderExecutiveReview(data) {
        const user = JSON.parse(sessionStorage.getItem('user') || '{}');
        const roleName = (user.role && user.role.name) ? user.role.name : (user.role || '');
        const role = roleName.toLowerCase().replace(/[^a-z0-9]/g, '');
        const isFacOrAdmin = ['facilitator', 'admin', 'superadmin'].includes(role);
        
        const container = document.getElementById('facilitatorExecutiveReview');
        if (!container) return;

        const isClosedOrStage8 = ['Closed', 'Pending Closure', 'Rejected', 'Stage 8 Reviewer Approved'].includes(data.status) || data.current_stage >= 8;
        
        if (isFacOrAdmin && isClosedOrStage8) {
            container.classList.remove('d-none');
            await this.renderExecutiveReviewPanel(container, data);
        } else {
            container.classList.add('d-none');
        }
    },

    async renderExecutiveReviewPanel(container, data) {
        const workflows = data.workflows || [];
        const s1 = (workflows.find(w => w.stage_id === 1) || {}).data || {};
        const s2 = (workflows.find(w => w.stage_id === 2) || {}).data || {};
        const s3 = (workflows.find(w => w.stage_id === 3) || {}).data || {};
        const s4 = (workflows.find(w => w.stage_id === 4) || {}).data || {};
        const s5 = (workflows.find(w => w.stage_id === 5) || {}).data || {};
        const s6 = (workflows.find(w => w.stage_id === 6) || {}).data || {};
        const s7 = (workflows.find(w => w.stage_id === 7) || {}).data || {};
        const s8 = (workflows.find(w => w.stage_id === this._stagesCfg.length) || {}).data || {};

        container.innerHTML = `
            <div class="ds-card-header d-flex justify-content-between align-items-center mb-3">
                <h5 class="card-title mb-0">
                    <i data-lucide="award" class="me-2 text-primary" style="width:20px;height:20px;vertical-align:text-bottom;"></i>
                    Facilitator &amp; Admin Executive Project Oversight
                </h5>
                <span class="ds-badge ${data.status === 'Closed' ? 'green' : (data.status === 'Pending Closure' ? 'orange' : 'blue')}">${data.status}</span>
            </div>
            <div class="ds-card-body p-0">
                <!-- Tabs for subsections -->
                <div class="ds-tab-group mb-4" id="execOversightTabs" style="border-bottom:1px solid rgba(var(--ds-primary-rgb),.15); padding-bottom:8px;">
                    <button class="ds-btn-tab active" data-exec-tab="dashboard">
                        <i data-lucide="bar-chart-2" style="width:14px;height:14px;margin-right:6px;"></i> QC Performance Dashboard
                    </button>
                    <button class="ds-btn-tab" data-exec-tab="workflow">
                        <i data-lucide="git-merge" style="width:14px;height:14px;margin-right:6px;"></i> 8-Stage Workflow Data
                    </button>
                    <button class="ds-btn-tab" data-exec-tab="sop">
                        <i data-lucide="book-open" style="width:14px;height:14px;margin-right:6px;"></i> SOP &amp; Standardization
                    </button>
                    <button class="ds-btn-tab" data-exec-tab="notes">
                        <i data-lucide="message-square" style="width:14px;height:14px;margin-right:6px;"></i> Review Comments &amp; Notes
                    </button>
                </div>

                <!-- Sub-tab contents -->
                <div id="exec-tab-dashboard" class="exec-tab-content">
                    <div class="row g-4">
                        <div class="col-md-6">
                            <div class="border rounded p-3 bg-light">
                                <h6 class="fw-bold mb-2 text-xs text-primary">Stage 2: Defect Pareto Chart</h6>
                                <div style="height:220px;position:relative;">
                                    <canvas id="execS2ParetoCanvas"></canvas>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="border rounded p-3 bg-light">
                                <h6 class="fw-bold mb-2 text-xs text-primary">Stage 3: Cause Prioritization Pareto</h6>
                                <div style="height:220px;position:relative;">
                                    <canvas id="execS3ParetoCanvas"></canvas>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="border rounded p-3 bg-light">
                                <h6 class="fw-bold mb-2 text-xs text-primary">Stage 4: Process Stability Control Chart</h6>
                                <div style="height:220px;position:relative;">
                                    <canvas id="execS4ControlCanvas"></canvas>
                                </div>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="border rounded p-3 bg-light">
                                <h6 class="fw-bold mb-2 text-xs text-primary">Stage 7: Before vs After Stability Comparison</h6>
                                <div style="height:220px;position:relative;">
                                    <canvas id="execS7ControlCanvas"></canvas>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div id="exec-tab-workflow" class="exec-tab-content d-none">
                    <div class="accordion" id="execWorkflowAccordion">
                        <div class="accordion-item">
                            <h2 class="accordion-header">
                                <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseS1">
                                    Stage 1: Theme Identification &amp; Goal Setting
                                </button>
                            </h2>
                            <div id="collapseS1" class="accordion-collapse collapse" data-bs-parent="#execWorkflowAccordion">
                                <div class="accordion-body text-sm text-secondary">
                                    <p><strong>Improvement Theme:</strong> ${s1.theme_target_schedule?.improvement_theme || 'N/A'}</p>
                                    <p><strong>Problem Statement:</strong> ${s1.background_5w2h?.problem_definition || 'N/A'}</p>
                                    <p><strong>Target vs Baseline:</strong> ${s1.theme_target_schedule?.current_level || 'N/A'} vs ${s1.theme_target_schedule?.target_level || 'N/A'} (${s1.current_performance?.current_kpi || 'N/A'})</p>
                                </div>
                            </div>
                        </div>
                        <div class="accordion-item">
                            <h2 class="accordion-header">
                                <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseS2">
                                    Stage 2: Gemba Walk &amp; Data Collection
                                </button>
                            </h2>
                            <div id="collapseS2" class="accordion-collapse collapse" data-bs-parent="#execWorkflowAccordion">
                                <div class="accordion-body text-sm text-secondary">
                                    <p><strong>Observer / Location:</strong> ${s2.process_observation?.observer || 'N/A'} / ${s2.process_observation?.area || 'N/A'}</p>
                                    <p><strong>Observation Findings:</strong> ${s2.process_observation?.finding_desc || 'N/A'} (Severity: ${s2.process_observation?.finding_severity || 'N/A'})</p>
                                    <p><strong>Standards Audited:</strong> SOP Avail: ${s2.standard_verification?.sop_avail ? 'Yes' : 'No'} | SOP Followed: ${s2.standard_verification?.sop_follow ? 'Yes' : 'No'} | SOP Deviation: ${s2.standard_verification?.sop_dev ? 'Yes' : 'No'}</p>
                                </div>
                            </div>
                        </div>
                        <div class="accordion-item">
                            <h2 class="accordion-header">
                                <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseS3">
                                    Stage 3: Brainstorming &amp; Factor Prioritization
                                </button>
                            </h2>
                            <div id="collapseS3" class="accordion-collapse collapse" data-bs-parent="#execWorkflowAccordion">
                                <div class="accordion-body text-sm text-secondary">
                                    <p><strong>Brainstorming Session:</strong> ${s3.brainstorming?.session_name || 'N/A'} (Facilitator: ${s3.brainstorming?.facilitator || 'N/A'})</p>
                                    <p><strong>Identified Causes:</strong> ${s3.cause_register?.length || 0} causes brainstormed</p>
                                </div>
                            </div>
                        </div>
                        <div class="accordion-item">
                            <h2 class="accordion-header">
                                <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseS4">
                                    Stage 4: Root Cause Analysis &amp; Stability Verification
                                </button>
                            </h2>
                            <div id="collapseS4" class="accordion-collapse collapse" data-bs-parent="#execWorkflowAccordion">
                                <div class="accordion-body text-sm text-secondary">
                                    <p><strong>Verified Root Causes:</strong> ${s4.root_cause_register?.map(c => c.root_cause).join(', ') || 'N/A'}</p>
                                    <p><strong>Why-Why Chain:</strong> ${s4.why_why_analysis?.map(w => `${w.cause} -> Why: ${w.why1} -> Root: ${w.root_cause}`).join('; ') || 'N/A'}</p>
                                </div>
                            </div>
                        </div>
                        <div class="accordion-item">
                            <h2 class="accordion-header">
                                <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseS5">
                                    Stage 5: Action Planning &amp; Hypothesis Testing
                                </button>
                            </h2>
                            <div id="collapseS5" class="accordion-collapse collapse" data-bs-parent="#execWorkflowAccordion">
                                <div class="accordion-body text-sm text-secondary">
                                    <p><strong>Hypothesis Statement:</strong> ${s5.hypothesis?.hypothesis_statement || 'N/A'}</p>
                                    <p><strong>Validation Method:</strong> ${s5.validation_methods?.map(m => m.method_name).join(', ') || 'N/A'}</p>
                                </div>
                            </div>
                        </div>
                        <div class="accordion-item">
                            <h2 class="accordion-header">
                                <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseS6">
                                    Stage 6: Countermeasure Trial &amp; Task Execution
                                </button>
                            </h2>
                            <div id="collapseS6" class="accordion-collapse collapse" data-bs-parent="#execWorkflowAccordion">
                                <div class="accordion-body text-sm text-secondary">
                                    <p><strong>Action Executions:</strong> ${s6.countermeasure_execution?.map(a => `${a.action} (${a.status})`).join('; ') || 'No tasks defined'}</p>
                                </div>
                            </div>
                        </div>
                        <div class="accordion-item">
                            <h2 class="accordion-header">
                                <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseS7">
                                    Stage 7: Benefit Realization &amp; ROI
                                </button>
                            </h2>
                            <div id="collapseS7" class="accordion-collapse collapse" data-bs-parent="#execWorkflowAccordion">
                                <div class="accordion-body text-sm text-secondary">
                                    <p><strong>ROI Metrics:</strong> Investment: ₹${s7.roi_validation?.total_investment || 'N/A'} | Annual Savings: ₹${s7.roi_validation?.annual_savings || 'N/A'} | Payback: ${s7.roi_validation?.payback_period || 'N/A'} | ROI: ${s7.roi_validation?.roi_pct || 'N/A'}%</p>
                                    <p><strong>KPI Benefit Verification:</strong> ${s7.kpi_verification?.map(k => `${k.metric}: Baseline ${k.baseline} -> Actual ${k.actual} (Variance: ${k.variance})`).join('; ') || 'N/A'}</p>
                                </div>
                            </div>
                        </div>
                        <div class="accordion-item">
                            <h2 class="accordion-header">
                                <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapseS8">
                                    Stage 8: Standardization &amp; SOP Creation
                                </button>
                            </h2>
                            <div id="collapseS8" class="accordion-collapse collapse" data-bs-parent="#execWorkflowAccordion">
                                <div class="accordion-body text-sm text-secondary">
                                    <p><strong>Linked SOP:</strong> ${s8.sop?.title || 'N/A'} (${s8.sop?.sop_type || 'N/A'})</p>
                                    <p><strong>Lessons Learned:</strong> ${s8.lessons_learned?.map(l => l.lesson).join(', ') || 'N/A'}</p>
                                    <p><strong>Training Record Groups:</strong> ${s8.training_adoption?.map(t => `${t.target_group} (${t.adoption_status})`).join('; ') || 'N/A'}</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <div id="exec-tab-sop" class="exec-tab-content d-none">
                    <div id="execSopViewer">
                        ${s8.sop?.title ? `
                            <div class="border rounded p-3 bg-light">
                                <div class="d-flex justify-content-between align-items-center mb-3 border-bottom pb-2">
                                    <h6 class="fw-bold text-primary mb-0">${s8.sop.title}</h6>
                                    <span class="ds-badge blue">${s8.sop.sop_type || 'SOP'}</span>
                                </div>
                                <p class="text-sm"><strong>Purpose:</strong> ${s8.sop.purpose || 'N/A'}</p>
                                <p class="text-sm"><strong>Scope:</strong> ${s8.sop.scope || 'N/A'}</p>
                                <p class="text-sm"><strong>Applicability:</strong> ${s8.sop.applicability || 'N/A'}</p>
                                <p class="text-sm"><strong>Responsibilities:</strong> ${s8.sop.responsibilities || 'N/A'}</p>
                                <hr>
                                <h6 class="fw-bold text-xs mb-2">Procedure Steps:</h6>
                                <ol class="text-sm ps-3">
                                    ${(s8.sop.steps || []).map(s => `<li><strong>${s.step_name}:</strong> ${s.description} (Role: ${s.responsible_role || 'All'})</li>`).join('') || '<li class="text-muted">No steps configured</li>'}
                                </ol>
                            </div>
                        ` : `
                            <div class="p-4 text-center text-muted border rounded">
                                <i data-lucide="alert-circle" style="width:36px;height:36px;" class="mb-2"></i>
                                <p class="mb-0">No SOP created or linked for this project yet.</p>
                            </div>
                        `}
                    </div>
                </div>

                <div id="exec-tab-notes" class="exec-tab-content d-none">
                    <div class="mb-3">
                        <label class="form-label fw-bold text-xs" for="execOversightNoteInput">Add Review Comment / Guidance</label>
                        <textarea class="form-control ds-input" id="execOversightNoteInput" rows="3" placeholder="Enter your review comments, guidance, or observations for this project..."></textarea>
                        <button class="ds-btn ds-btn-primary ds-btn-sm mt-2" onclick="ProjectApp.saveOversightNote()">
                            <i data-lucide="save" style="width:14px;height:14px;margin-right:6px;"></i> Save Review Comment
                        </button>
                    </div>
                    <hr>
                    <h6 class="fw-bold mb-2 text-xs">Oversight History</h6>
                    <div id="execOversightNotesList" class="v-stack gap-2" style="max-height: 250px; overflow-y: auto;">
                        <div class="text-xs text-muted">Loading review history...</div>
                    </div>
                </div>
            </div>
        `;

        if (window.lucide) lucide.createIcons();

        // Wire tabs
        container.querySelectorAll('[data-exec-tab]').forEach(btn => {
            btn.addEventListener('click', () => {
                container.querySelectorAll('[data-exec-tab]').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                container.querySelectorAll('.exec-tab-content').forEach(p => p.classList.add('d-none'));
                container.querySelector('#exec-tab-' + btn.dataset.execTab).classList.remove('d-none');
            });
        });

        // Load charts
        this.renderExecutiveCharts(data);

        // Load history notes
        await this.loadOversightNotes();
    },

    renderExecutiveCharts(data) {
        const workflows = data.workflows || [];
        const s2 = (workflows.find(w => w.stage_id === 2) || {}).data || {};
        const s3 = (workflows.find(w => w.stage_id === 3) || {}).data || {};
        const s4 = (workflows.find(w => w.stage_id === 4) || {}).data || {};
        const s7 = (workflows.find(w => w.stage_id === 7) || {}).data || {};

        // 1. Stage 2 Pareto
        const s2Obs = s2.data_collection?.observations || [];
        const s2Canvas = document.getElementById('execS2ParetoCanvas');
        if (s2Canvas && s2Obs.length > 0) {
            const counts = {};
            s2Obs.forEach(o => { counts[o.category] = (counts[o.category] || 0) + parseFloat(o.value || 0); });
            const sorted = Object.entries(counts).sort((a,b) => b[1] - a[1]);
            const labels = sorted.map(x => x[0]);
            const values = sorted.map(x => x[1]);
            const total = values.reduce((a,b) => a+b, 0);
            let cum = 0;
            const cumPerc = values.map(v => { cum += v; return total > 0 ? ((cum/total)*100).toFixed(1) : 0; });

            new Chart(s2Canvas.getContext('2d'), {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Frequency',
                            data: values,
                            backgroundColor: 'rgba(239, 68, 68, 0.65)',
                            borderColor: 'rgb(239, 68, 68)',
                            borderWidth: 1.5,
                            yAxisID: 'y'
                        },
                        {
                            label: 'Cumulative %',
                            data: cumPerc,
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
                        y: { type: 'linear', display: true, position: 'left', beginAtZero: true },
                        y1: { type: 'linear', display: true, position: 'right', min: 0, max: 100 }
                    }
                }
            });
        } else if (s2Canvas) {
            s2Canvas.parentNode.innerHTML = `<div class="text-xs text-muted text-center py-5">No observations collected in Stage 2</div>`;
        }

        // 2. Stage 3 Pareto
        const s3Prior = s3.cause_prioritization || [];
        const s3Canvas = document.getElementById('execS3ParetoCanvas');
        if (s3Canvas && s3Prior.length > 0) {
            const sorted = [...s3Prior].sort((a,b) => parseFloat(b.total || 0) - parseFloat(a.total || 0));
            const labels = sorted.map(x => x.cause);
            const values = sorted.map(x => parseFloat(x.total || 0));
            const total = values.reduce((a,b) => a+b, 0);
            let cum = 0;
            const cumPerc = values.map(v => { cum += v; return total > 0 ? ((cum/total)*100).toFixed(1) : 0; });

            new Chart(s3Canvas.getContext('2d'), {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Score',
                            data: values,
                            backgroundColor: 'rgba(59, 130, 246, 0.65)',
                            borderColor: 'rgb(59, 130, 246)',
                            borderWidth: 1.5,
                            yAxisID: 'y'
                        },
                        {
                            label: 'Cumulative %',
                            data: cumPerc,
                            type: 'line',
                            borderColor: 'rgb(16, 185, 129)',
                            backgroundColor: 'rgba(16, 185, 129, 0.1)',
                            borderWidth: 2,
                            pointBackgroundColor: 'rgb(16, 185, 129)',
                            yAxisID: 'y1',
                            tension: 0.1
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { type: 'linear', display: true, position: 'left', beginAtZero: true },
                        y1: { type: 'linear', display: true, position: 'right', min: 0, max: 100 }
                    }
                }
            });
        } else if (s3Canvas) {
            s3Canvas.parentNode.innerHTML = `<div class="text-xs text-muted text-center py-5">No factor prioritization in Stage 3</div>`;
        }

        // 3. Stage 4 Control Chart
        const s4Ctrl = s4.data_reconfirmation?.control_chart || {};
        const s4Points = s4Ctrl.points || [];
        const s4Canvas = document.getElementById('execS4ControlCanvas');
        if (s4Canvas && s4Points.length > 0) {
            const labels = s4Points.map(p => p.label || '');
            const values = s4Points.map(p => parseFloat(p.val || 0));
            const ucl = parseFloat(s4Ctrl.ucl || 0);
            const lcl = parseFloat(s4Ctrl.lcl || 0);
            const cl = parseFloat(s4Ctrl.cl || 0);

            new Chart(s4Canvas.getContext('2d'), {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Observation',
                            data: values,
                            borderColor: 'rgb(79, 70, 229)',
                            backgroundColor: 'rgba(79, 70, 229, 0.1)',
                            borderWidth: 2,
                            pointBackgroundColor: values.map(v => (v > ucl || v < lcl) ? '#ef4444' : 'rgb(79, 70, 229)')
                        },
                        { label: 'UCL', data: Array(labels.length).fill(ucl), borderColor: 'rgba(239, 68, 68, 0.6)', borderDash: [5,5], fill: false, pointRadius: 0 },
                        { label: 'CL', data: Array(labels.length).fill(cl), borderColor: 'rgba(156, 163, 175, 0.6)', borderDash: [2,2], fill: false, pointRadius: 0 },
                        { label: 'LCL', data: Array(labels.length).fill(lcl), borderColor: 'rgba(239, 68, 68, 0.6)', borderDash: [5,5], fill: false, pointRadius: 0 }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false
                }
            });
        } else if (s4Canvas) {
            s4Canvas.parentNode.innerHTML = `<div class="text-xs text-muted text-center py-5">No control chart points in Stage 4</div>`;
        }

        // 4. Stage 7 Control Chart Comparison
        const s7Ctrl = s7.before_vs_after_extended || {};
        const s7Points = s7Ctrl.control_after_points || [];
        const s7Canvas = document.getElementById('execS7ControlCanvas');
        if (s7Canvas && s4Points.length > 0 && s7Points.length > 0) {
            const beforeVals = s4Points.map(p => parseFloat(p.val || 0));
            const afterVals = s7Points.map(p => parseFloat(p.val || 0));
            const combinedVals = [...beforeVals, ...afterVals];
            const labels = [...s4Points.map(p => p.label || ''), ...s7Points.map(p => p.label || '')];
            
            const uclBefore = parseFloat(s4Ctrl.ucl || 0);
            const lclBefore = parseFloat(s4Ctrl.lcl || 0);
            const clBefore = parseFloat(s4Ctrl.cl || 0);
            const uclAfter = parseFloat(s7Ctrl.ucl || uclBefore);
            const lclAfter = parseFloat(s7Ctrl.lcl || lclBefore);
            const clAfter = parseFloat(s7Ctrl.cl || clBefore);

            const uclLine = [...Array(beforeVals.length).fill(uclBefore), ...Array(afterVals.length).fill(uclAfter)];
            const lclLine = [...Array(beforeVals.length).fill(lclBefore), ...Array(afterVals.length).fill(lclAfter)];
            const clLine = [...Array(beforeVals.length).fill(clBefore), ...Array(afterVals.length).fill(clAfter)];

            new Chart(s7Canvas.getContext('2d'), {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Combined Readings',
                            data: combinedVals,
                            borderColor: 'rgba(156, 163, 175, 0.7)',
                            borderWidth: 1.5,
                            segment: {
                                borderColor: ctx => ctx.p0.parsed.x >= beforeVals.length ? 'rgb(16, 185, 129)' : 'rgb(59, 130, 246)'
                            },
                            pointBackgroundColor: combinedVals.map((v, idx) => {
                                const isAfter = idx >= beforeVals.length;
                                const ucl = isAfter ? uclAfter : uclBefore;
                                const lcl = isAfter ? lclAfter : lclBefore;
                                return (v > ucl || v < lcl) ? '#ef4444' : (isAfter ? 'rgb(16, 185, 129)' : 'rgb(59, 130, 246)');
                            })
                        },
                        { label: 'UCL', data: uclLine, borderColor: 'rgba(239, 68, 68, 0.5)', borderDash: [5,5], fill: false, pointRadius: 0 },
                        { label: 'CL', data: clLine, borderColor: 'rgba(156, 163, 175, 0.5)', borderDash: [2,2], fill: false, pointRadius: 0 },
                        { label: 'LCL', data: lclLine, borderColor: 'rgba(239, 68, 68, 0.5)', borderDash: [5,5], fill: false, pointRadius: 0 }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false
                }
            });
        } else if (s7Canvas) {
            s7Canvas.parentNode.innerHTML = `<div class="text-xs text-muted text-center py-5">Before vs After comparison points not fully set</div>`;
        }
    },

    async loadOversightNotes() {
        try {
            const notes = await api.get(`/facilitator/notes/${this.projectId}`);
            const listEl = document.getElementById('execOversightNotesList');
            if (listEl) {
                if (notes.length === 0) {
                    listEl.innerHTML = '<div class="text-xs text-muted p-2">No review comments recorded.</div>';
                } else {
                    listEl.innerHTML = notes.map(n => `
                        <div class="border rounded p-2 bg-white shadow-sm mb-2" style="font-size:0.8rem;">
                            <div class="d-flex justify-content-between text-xs text-muted mb-1">
                                <strong>${n.created_by}</strong>
                                <span>${new Date(n.created_at).toLocaleString()}</span>
                            </div>
                            <div class="text-secondary">${n.note_text}</div>
                        </div>
                    `).join('');
                }
            }
        } catch (e) {
            console.error('Failed to load notes', e);
        }
    },

    async saveOversightNote() {
        const textEl = document.getElementById('execOversightNoteInput');
        if (!textEl) return;
        const text = textEl.value.trim();
        if (!text) {
            QCMS.toast('Comment text cannot be empty.', 'warning');
            return;
        }
        try {
            await api.post('/facilitator/notes', {
                project_id: parseInt(this.projectId),
                stage_number: 8,
                note_text: text
            });
            QCMS.toast('Review comment saved successfully.', 'success');
            textEl.value = '';
            await this.loadOversightNotes();
        } catch (e) {
            QCMS.toast('Failed to save review comment: ' + e.message, 'error');
        }
    },

    openQcAnalysisModal() {
        const data = this.projectData;
        const workflows = data.workflows || [];
        const s1 = (workflows.find(w => w.stage_id === 1) || {}).data || {};
        const s2 = (workflows.find(w => w.stage_id === 2) || {}).data || {};
        const s3 = (workflows.find(w => w.stage_id === 3) || {}).data || {};
        const s4 = (workflows.find(w => w.stage_id === 4) || {}).data || {};
        const s5 = (workflows.find(w => w.stage_id === 5) || {}).data || {};
        const s6 = (workflows.find(w => w.stage_id === 6) || {}).data || {};
        const s7 = (workflows.find(w => w.stage_id === 7) || {}).data || {};
        const s8 = (workflows.find(w => w.stage_id === this._stagesCfg.length) || {}).data || {};

        document.getElementById('qc_modal_meta').textContent = `Project: ${data.title} (${data.project_uid}) · 7 QC Tools Performance`;

        // 1. Check Sheet Data
        const checkSheetBody = document.getElementById('qc_checksheet_body');
        const s2Obs = s2.data_collection?.observations || [];
        if (checkSheetBody) {
            if (s2Obs.length === 0) {
                checkSheetBody.innerHTML = `<tr><td colspan="3" class="text-center text-muted">No Check Sheet observations logged in Stage 2.</td></tr>`;
            } else {
                const categoryCounts = {};
                s2Obs.forEach(o => {
                    if (!categoryCounts[o.category]) {
                        categoryCounts[o.category] = { count: 0, locations: [] };
                    }
                    categoryCounts[o.category].count += parseFloat(o.value || 0);
                    if (o.location && !categoryCounts[o.category].locations.includes(o.location)) {
                        categoryCounts[o.category].locations.push(o.location);
                    }
                });
                checkSheetBody.innerHTML = Object.entries(categoryCounts).map(([cat, info]) => `
                    <tr>
                        <td class="fw-semibold">${cat}</td>
                        <td><span class="ds-badge orange" style="background:rgba(var(--ds-warning-rgb),.12);color:var(--ds-warning);padding:4px 8px;border-radius:4px;">${info.count}</span></td>
                        <td>${info.locations.join(', ') || 'N/A'}</td>
                    </tr>
                `).join('');
            }
        }

        // 2. Histogram Data (Before vs After)
        const histCanvas = document.getElementById('qc_histogram_canvas');
        if (histCanvas) {
            const beforeVals = (s2.data_collection?.histogram_values || '').split(',').map(v => parseFloat(v.trim())).filter(v => !isNaN(v));
            const afterVals = (s7.before_vs_after_extended?.histogram_after_values || '').split(',').map(v => parseFloat(v.trim())).filter(v => !isNaN(v));
            
            // Draw comparative histogram
            const ctx = histCanvas.getContext('2d');
            if (window.qcHistChartInstance) window.qcHistChartInstance.destroy();

            // Stats Helper
            const calcStats = (vals) => {
                if (vals.length === 0) return { mean: 'N/A', sd: 'N/A' };
                const sum = vals.reduce((a,b) => a+b, 0);
                const mean = sum / vals.length;
                const sqDiff = vals.map(v => Math.pow(v - mean, 2));
                const variance = sqDiff.reduce((a,b) => a+b, 0) / vals.length;
                const sd = Math.sqrt(variance);
                return { mean: mean.toFixed(2), sd: sd.toFixed(2) };
            };
            const beforeStats = calcStats(beforeVals);
            const afterStats = calcStats(afterVals);

            document.getElementById('qc_hist_mean_bef').textContent = beforeStats.mean;
            document.getElementById('qc_hist_mean_aft').textContent = afterStats.mean;
            document.getElementById('qc_hist_sd_bef').textContent = beforeStats.sd;
            document.getElementById('qc_hist_sd_aft').textContent = afterStats.sd;

            // Simple distribution bins
            const minVal = Math.min(...beforeVals, ...afterVals, 0);
            const maxVal = Math.max(...beforeVals, ...afterVals, 10);
            const binCount = 6;
            const step = (maxVal - minVal) / binCount;
            const labels = [];
            const beforeBins = Array(binCount).fill(0);
            const afterBins = Array(binCount).fill(0);

            for (let i = 0; i < binCount; i++) {
                const low = minVal + i * step;
                const high = low + step;
                labels.push(`${low.toFixed(1)}-${high.toFixed(1)}`);
                beforeVals.forEach(v => { if (v >= low && v <= high) beforeBins[i]++; });
                afterVals.forEach(v => { if (v >= low && v <= high) afterBins[i]++; });
            }

            window.qcHistChartInstance = new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [
                        { label: 'Before Improvement', data: beforeBins, backgroundColor: 'rgba(239, 68, 68, 0.5)', borderColor: 'rgb(239, 68, 68)', borderWidth: 1 },
                        { label: 'After Improvement', data: afterBins, backgroundColor: 'rgba(16, 185, 129, 0.5)', borderColor: 'rgb(16, 185, 129)', borderWidth: 1 }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false
                }
            });
        }

        // 3. Pareto Charts
        const p2Canvas = document.getElementById('qc_s2_pareto_canvas');
        if (p2Canvas && s2Obs.length > 0) {
            const counts = {};
            s2Obs.forEach(o => { counts[o.category] = (counts[o.category] || 0) + parseFloat(o.value || 0); });
            const sorted = Object.entries(counts).sort((a,b) => b[1] - a[1]);
            const labels = sorted.map(x => x[0]);
            const values = sorted.map(x => x[1]);
            const total = values.reduce((a,b) => a+b, 0);
            let cum = 0;
            const cumPerc = values.map(v => { cum += v; return total > 0 ? ((cum/total)*100).toFixed(1) : 0; });

            if (window.qcS2ParetoChartInstance) window.qcS2ParetoChartInstance.destroy();
            window.qcS2ParetoChartInstance = new Chart(p2Canvas.getContext('2d'), {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [
                        { label: 'Frequency', data: values, backgroundColor: 'rgba(239, 68, 68, 0.65)', borderColor: 'rgb(239, 68, 68)', borderWidth: 1.5, yAxisID: 'y' },
                        { label: 'Cumulative %', data: cumPerc, type: 'line', borderColor: 'rgb(249, 115, 22)', borderWidth: 2, yAxisID: 'y1' }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { type: 'linear', display: true, position: 'left', beginAtZero: true },
                        y1: { type: 'linear', display: true, position: 'right', min: 0, max: 100 }
                    }
                }
            });
        }

        const p3Canvas = document.getElementById('qc_s3_pareto_canvas');
        const s3Prior = s3.cause_prioritization || [];
        if (p3Canvas && s3Prior.length > 0) {
            const sorted = [...s3Prior].sort((a,b) => parseFloat(b.total || 0) - parseFloat(a.total || 0));
            const labels = sorted.map(x => x.cause);
            const values = sorted.map(x => parseFloat(x.total || 0));
            const total = values.reduce((a,b) => a+b, 0);
            let cum = 0;
            const cumPerc = values.map(v => { cum += v; return total > 0 ? ((cum/total)*100).toFixed(1) : 0; });

            if (window.qcS3ParetoChartInstance) window.qcS3ParetoChartInstance.destroy();
            window.qcS3ParetoChartInstance = new Chart(p3Canvas.getContext('2d'), {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [
                        { label: 'Score', data: values, backgroundColor: 'rgba(59, 130, 246, 0.65)', borderColor: 'rgb(59, 130, 246)', borderWidth: 1.5, yAxisID: 'y' },
                        { label: 'Cumulative %', data: cumPerc, type: 'line', borderColor: 'rgb(16, 185, 129)', borderWidth: 2, yAxisID: 'y1' }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: { type: 'linear', display: true, position: 'left', beginAtZero: true },
                        y1: { type: 'linear', display: true, position: 'right', min: 0, max: 100 }
                    }
                }
            });
        }

        // 4. Fishbone Diagram Visual Drawings (Pre vs Post Verification)
        const drawVisualFishboneHelper = (rows, prefix, effectText) => {
            const effectEl = document.getElementById(`qc_fb_${prefix}_effect`);
            if (effectEl) {
                effectEl.textContent = effectText.length > 20 ? effectText.substring(0, 18) + '...' : effectText;
            }

            const groups = { Man: [], Machine: [], Material: [], Method: [], Measurement: [], Environment: [] };
            rows.forEach(r => {
                const cat = r.category || 'Other';
                if (groups[cat]) groups[cat].push(r);
            });

            const boneConfigs = {
                Man: { x1: 160, y1: 60, x2: 230, y2: 175, direction: 'down-right' },
                Machine: { x1: 330, y1: 60, x2: 400, y2: 175, direction: 'down-right' },
                Material: { x1: 500, y1: 60, x2: 570, y2: 175, direction: 'down-right' },
                Method: { x1: 160, y1: 290, x2: 230, y2: 175, direction: 'up-right' },
                Measurement: { x1: 330, y1: 290, x2: 400, y2: 175, direction: 'up-right' },
                Environment: { x1: 500, y1: 290, x2: 570, y2: 175, direction: 'up-right' }
            };

            for (const [cat, config] of Object.entries(boneConfigs)) {
                const g = document.getElementById(`qc_fb_${prefix}_${cat}`);
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
                    const lineLen = 50;
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

                    const textVal = (cause.level1 || cause.cause || '') + (cause.level2 ? ` (${cause.level2})` : '');
                    const label = textVal.length > 16 ? textVal.substring(0, 14) + '...' : textVal;

                    const txt = document.createElementNS("http://www.w3.org/2000/svg", "text");
                    txt.setAttribute("x", lx1 - 4);
                    txt.setAttribute("y", ly + 3);
                    txt.setAttribute("text-anchor", "end");
                    txt.setAttribute("font-size", "8");
                    txt.setAttribute("fill", "#374151");
                    txt.textContent = label;
                    g.appendChild(txt);
                });
            }
        };

        const preCauses = s3.fishbone_l1 || s3.fishbone_l2 || [];
        const postCauses = s3.fishbone_l3?.diagram_data || [];
        const problemStatement = s1.problem_statement || s2.problem_statement || data.title || 'Problem';

        drawVisualFishboneHelper(preCauses, 'pre', problemStatement);
        drawVisualFishboneHelper(postCauses, 'post', problemStatement);

        // 5. Control Chart Comparison
        const controlCanvas = document.getElementById('qc_control_comparison_canvas');
        const s4Ctrl = s4.data_reconfirmation?.control_chart || {};
        const beforePoints = s4Ctrl.points || [];
        const afterPoints = s7.before_vs_after_extended?.control_after_points || [];
        if (controlCanvas && beforePoints.length > 0 && afterPoints.length > 0) {
            const beforeVals = beforePoints.map(p => parseFloat(p.val || 0));
            const afterVals = afterPoints.map(p => parseFloat(p.val || 0));
            const combinedVals = [...beforeVals, ...afterVals];
            const labels = [...beforePoints.map(p => p.label || ''), ...afterPoints.map(p => p.label || '')];
            
            const uclBefore = parseFloat(s4Ctrl.ucl || 0);
            const lclBefore = parseFloat(s4Ctrl.lcl || 0);
            const clBefore = parseFloat(s4Ctrl.cl || 0);
            const uclAfter = parseFloat(s7.before_vs_after_extended?.ucl || uclBefore);
            const lclAfter = parseFloat(s7.before_vs_after_extended?.lcl || lclBefore);
            const clAfter = parseFloat(s7.before_vs_after_extended?.cl || clBefore);

            const uclLine = [...Array(beforeVals.length).fill(uclBefore), ...Array(afterVals.length).fill(uclAfter)];
            const lclLine = [...Array(beforeVals.length).fill(lclBefore), ...Array(afterVals.length).fill(lclAfter)];
            const clLine = [...Array(beforeVals.length).fill(clBefore), ...Array(afterVals.length).fill(clAfter)];

            if (window.qcControlChartInstance) window.qcControlChartInstance.destroy();
            window.qcControlChartInstance = new Chart(controlCanvas.getContext('2d'), {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Observation Value',
                            data: combinedVals,
                            borderColor: 'rgba(156, 163, 175, 0.7)',
                            borderWidth: 1.5,
                            segment: {
                                borderColor: ctx => ctx.p0.parsed.x >= beforeVals.length ? 'rgb(16, 185, 129)' : 'rgb(59, 130, 246)'
                            },
                            pointBackgroundColor: combinedVals.map((v, idx) => {
                                const isAfter = idx >= beforeVals.length;
                                const ucl = isAfter ? uclAfter : uclBefore;
                                const lcl = isAfter ? lclAfter : lclBefore;
                                return (v > ucl || v < lcl) ? '#ef4444' : (isAfter ? 'rgb(16, 185, 129)' : 'rgb(59, 130, 246)');
                            })
                        },
                        { label: 'UCL (Limit)', data: uclLine, borderColor: 'rgba(239, 68, 68, 0.5)', borderDash: [5,5], fill: false, pointRadius: 0 },
                        { label: 'CL (Mean)', data: clLine, borderColor: 'rgba(156, 163, 175, 0.5)', borderDash: [2,2], fill: false, pointRadius: 0 },
                        { label: 'LCL (Limit)', data: lclLine, borderColor: 'rgba(239, 68, 68, 0.5)', borderDash: [5,5], fill: false, pointRadius: 0 }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false
                }
            });
        }

        // 6. Scatter Diagram
        const scatterCanvas = document.getElementById('qc_scatter_canvas');
        const s4Scatter = s4.statistical_validation?.scatter || {};
        const scatterPoints = s4Scatter.points || [];
        if (scatterCanvas && scatterPoints.length > 0) {
            const pointsData = scatterPoints.map(p => ({ x: parseFloat(p.x), y: parseFloat(p.y) }));
            const r = parseFloat(s4Scatter.r || 0);
            const m = parseFloat(s4Scatter.m || 0);
            const c = parseFloat(s4Scatter.c || 0);
            const strength = s4Scatter.strength || 'N/A';

            document.getElementById('qc_scatter_r_val').textContent = r.toFixed(3);
            document.getElementById('qc_scatter_strength').textContent = strength;
            document.getElementById('qc_scatter_m_val').textContent = m.toFixed(3);
            document.getElementById('qc_scatter_c_val').textContent = c.toFixed(3);

            // Generate trend line points
            const xVals = pointsData.map(p => p.x);
            const minX = Math.min(...xVals);
            const maxX = Math.max(...xVals);
            const trendLine = [
                { x: minX, y: m * minX + c },
                { x: maxX, y: m * maxX + c }
            ];

            if (window.qcScatterChartInstance) window.qcScatterChartInstance.destroy();
            window.qcScatterChartInstance = new Chart(scatterCanvas.getContext('2d'), {
                type: 'scatter',
                data: {
                    datasets: [
                        { label: 'Data Points', data: pointsData, backgroundColor: 'rgb(79, 70, 229)' },
                        { label: 'Trend Line', data: trendLine, type: 'line', borderColor: 'rgba(239, 68, 68, 0.8)', borderDash: [3,3], fill: false, pointRadius: 0 }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: { title: { display: true, text: s4Scatter.x_label || 'Cause Factor' } },
                        y: { title: { display: true, text: s4Scatter.y_label || 'Effect KPI' } }
                    }
                }
            });
        }

        // 7. Stratification Analysis
        const shiftBody = document.getElementById('qc_strat_shift_body');
        const locBody = document.getElementById('qc_strat_location_body');
        if (shiftBody && locBody) {
            const shiftCounts = {};
            const locCounts = {};
            s2Obs.forEach(o => {
                if (o.shift) shiftCounts[o.shift] = (shiftCounts[o.shift] || 0) + parseFloat(o.value || 0);
                if (o.location) locCounts[o.location] = (locCounts[o.location] || 0) + parseFloat(o.value || 0);
            });

            shiftBody.innerHTML = Object.keys(shiftCounts).length === 0 
                ? '<tr><td colspan="2" class="text-center text-muted">No shift data.</td></tr>'
                : Object.entries(shiftCounts).map(([s, c]) => `<tr><td>${s}</td><td><span class="ds-badge blue">${c}</span></td></tr>`).join('');
            
            locBody.innerHTML = Object.keys(locCounts).length === 0
                ? '<tr><td colspan="2" class="text-center text-muted">No location data.</td></tr>'
                : Object.entries(locCounts).map(([l, c]) => `<tr><td>${l}</td><td><span class="ds-badge blue">${c}</span></td></tr>`).join('');
        }

        // Open modal
        new bootstrap.Modal(document.getElementById('qcAnalysisModal')).show();
        if (window.lucide) setTimeout(() => lucide.createIcons(), 100);
    },
};

document.addEventListener('DOMContentLoaded', () => ProjectApp.init());
