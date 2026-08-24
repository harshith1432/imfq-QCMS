const DynamicRenderer = {
    // Stores in-memory values and chart instances for active dynamic stages
    activeStageId: null,
    sections: [],
    charts: {},

    escapeHtml(str) {
        if (!str) return '';
        return str
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    },

    renderHTML(sections) {
        this.sections = sections || [];
        let html = `<div class="row g-3" id="dynamicStageForm">`;

        this.sections.forEach(sec => {
            html += this.renderSectionCard(sec);
        });

        html += `</div>`;
        return html;
    },

    getAllRenderableFields(sec) {
        if (!sec) return [];
        let list = [];
        const rawFields = Array.isArray(sec.fields) ? sec.fields : (Array.isArray(sec.custom_fields) ? sec.custom_fields : []);
        if (rawFields.length > 0) {
            rawFields.forEach(f => {
                if (f) {
                    if (!list.some(item => item.id === f.id)) list.push(f);
                    if (Array.isArray(f.fields) && f.fields.length > 0) {
                        f.fields.forEach(subF => {
                            if (subF && !list.some(item => item.id === subF.id)) list.push(subF);
                        });
                    }
                }
            });
        }
        if (Array.isArray(sec.children) && sec.children.length > 0) {
            sec.children.forEach(f => {
                if (f && !list.some(item => item.id === f.id)) list.push(f);
            });
        }
        return list;
    },

    renderSectionCard(sec) {
        if (!sec) return '';

        const secType = (sec.type || '').toLowerCase();
        const isHeaderType = secType === 'section_header' || secType === 'header' || secType === 'sub_section';
        const fieldsToRender = this.getAllRenderableFields(sec);

        if (isHeaderType || fieldsToRender.length > 0) {
            let fieldsHtml = '';
            if (fieldsToRender.length > 0) {
                fieldsHtml = `<div class="row g-3">`;
                fieldsToRender.forEach(f => {
                    fieldsHtml += this.renderSingleFieldItem(f);
                });
                fieldsHtml += `</div>`;
            } else {
                fieldsHtml = `<div class="text-xs text-muted fst-italic py-2">Sub-section header (No custom elements added yet).</div>`;
            }

            const colWidth = 'col-12';
            const orderLabel = (sec.order !== undefined && sec.order !== null && sec.order !== 'undefined') ? sec.order : '';
            const orderCircle = orderLabel ? `<span class="ds-icon-circle bg-primary-soft text-primary" style="width:24px;height:24px;font-size:.65rem;font-weight:700;">${orderLabel}</span>` : '';

            const naToggleHtml = sec.allow_na ? `
                <div class="form-check form-switch mb-0 ms-auto sec-na-toggle-wrap" title="Toggle section applicability" onclick="event.stopPropagation();">
                    <input class="form-check-input section-na-toggle" type="checkbox" role="switch" checked data-sec-id="${sec.id}">
                    <label class="text-xs fw-semibold text-success ms-1 mb-0 sec-na-label">Applicable</label>
                </div>
            ` : '';

            return `
                <div class="${colWidth}">
                    <div class="glass-card ds-card mb-3 p-3 border-start border-4 border-primary" id="card_${sec.id}" data-sec-id="${sec.id}">
                        <div class="ds-card-header px-0 pt-0 pb-2 border-bottom d-flex align-items-center justify-content-between">
                            <h6 class="mb-0 fw-bold text-main d-flex align-items-center gap-2">
                                ${orderCircle}
                                ${this.escapeHtml(sec.label || 'Section')}
                            </h6>
                            ${naToggleHtml}
                        </div>
                        <div class="ds-card-body px-0 pt-2 pb-0">
                            ${fieldsHtml}
                        </div>
                    </div>
                </div>
            `;
        }

        // Single standalone tool / input section
        return this.getFieldContentHtml(sec);
    },

    renderSingleFieldItem(field) {
        if (!field) return '';
        const fieldType = (field.type || 'text').toLowerCase();
        
        let colWidth = field.col_span || field.col || 'col-md-6';
        if (['textarea', 'multi_line_text', 'table', 'five_why', 'verification_table', 'pareto', 'fishbone', 'histogram', 'control_chart', 'scatter', 'stratification', 'multi_text', 'file_upload', 'grid_2col', 'grid_3col', 'info_callout', 'action_plan_3w1h'].includes(fieldType)) {
            if (!field.col_span || field.col_span === 'col-md-6') {
                colWidth = 'col-12';
            }
        }

        const innerContent = this.getFieldContentHtml(field, true);

        return `
            <div class="${colWidth}">
                <div class="ds-field-block p-2.5 rounded border mb-2" id="field_wrap_${field.id}" style="background: var(--ds-bg-card, #ffffff);">
                    <label class="ds-label text-xs fw-semibold mb-1 d-block text-main">
                        ${this.escapeHtml(field.label || 'Field')}
                    </label>
                    ${innerContent}
                </div>
            </div>
        `;
    },

    getFieldContentHtml(sec, isSubItem = false) {
        let contentHtml = '';
        const type = (sec.type || 'text').toLowerCase();
        
        switch (type) {
            case 'text':
            case 'single_line_text':
            case 'input':
            case 'number':
            case 'numeric':
            case 'date':
            case 'date_picker':
                {
                    const ph = sec.placeholder || 'Enter details...';
                    const isNum = type === 'number' || type === 'numeric' || sec.input_type === 'number';
                    const isDate = type === 'date' || type === 'date_picker' || sec.input_type === 'date';
                    const validTypes = ['date', 'datetime-local', 'number', 'text', 'time', 'month'];
                    const inputType = validTypes.includes(sec.input_type) ? sec.input_type : (isDate ? 'date' : (isNum ? 'number' : 'text'));
                    const clickAttr = (inputType === 'date' || inputType === 'datetime-local') ? 'onclick="if(this.showPicker) this.showPicker()"' : '';
                    const unitBadge = sec.unit ? `<span class="input-group-text bg-light text-muted text-xs">${this.escapeHtml(sec.unit)}</span>` : '';
                    
                    if (unitBadge) {
                        contentHtml = `
                            <div class="input-group input-group-sm">
                                <input type="${inputType}" class="ds-input" id="${sec.id}" placeholder="${this.escapeHtml(ph)}" ${sec.required === true ? 'required' : ''} ${clickAttr}>
                                ${unitBadge}
                            </div>
                        `;
                    } else {
                        contentHtml = `
                            <div class="ds-field">
                                <input type="${inputType}" class="ds-input" id="${sec.id}" placeholder="${this.escapeHtml(ph)}" ${sec.required === true ? 'required' : ''} ${clickAttr}>
                            </div>
                        `;
                    }
                }
                break;
            case 'textarea':
            case 'multi_line_text':
                {
                    const ph = sec.placeholder || 'Enter detailed notes...';
                    contentHtml = `
                        <div class="ds-field">
                            <textarea class="ds-input ds-textarea" id="${sec.id}" rows="3" placeholder="${this.escapeHtml(ph)}" ${sec.required === true ? 'required' : ''}></textarea>
                        </div>
                    `;
                }
                break;
            case 'select':
            case 'dropdown': {
                let optionsHtml = `<option value="">-- Select option --</option>`;
                if (sec.options) {
                    const list = Array.isArray(sec.options) ? sec.options : String(sec.options).split(/[\n,]+/).map(s => s.trim()).filter(Boolean);
                    list.forEach(opt => {
                        optionsHtml += `<option value="${this.escapeHtml(opt)}">${this.escapeHtml(opt)}</option>`;
                    });
                }
                if (!sec.options && (!sec.data_source || sec.data_source === 'custom')) {
                    optionsHtml += `
                        <option value="Yes">Yes</option>
                        <option value="No">No</option>
                        <option value="N/A">N/A</option>
                        <option value="Critical">Critical</option>
                        <option value="Normal">Normal</option>
                    `;
                }
                contentHtml = `
                    <div class="ds-field">
                        <select class="ds-input ds-select" id="${sec.id}" data-source="${sec.data_source || 'custom'}" ${sec.required === true ? 'required' : ''}>
                            ${optionsHtml}
                        </select>
                    </div>
                `;
                break;
            }
            case 'checkbox':
            case 'toggle': {
                contentHtml = `
                    <div class="form-check form-switch pt-1">
                        <input class="form-check-input" type="checkbox" id="${sec.id}">
                        <label class="form-check-label text-xs fw-semibold" for="${sec.id}">${this.escapeHtml(sec.placeholder || sec.label || 'Toggle option')}</label>
                    </div>
                `;
                break;
            }
            case 'section_header':
            case 'header':
            case 'sub_section': {
                const childFields = this.getAllRenderableFields(sec);
                if (childFields.length > 0) {
                    contentHtml = `<div class="row g-3">`;
                    childFields.forEach(f => {
                        const colW = f.col_span || f.col || 'col-md-6';
                        contentHtml += `
                            <div class="${colW}">
                                <div class="ds-field-block p-2.5 rounded border mb-2" style="background: var(--ds-bg-card, #ffffff);">
                                    <label class="ds-label text-xs fw-semibold mb-1 d-block text-main">
                                        ${this.escapeHtml(f.label || 'Field')} ${f.required ? '<span class="text-danger">*</span>' : ''}
                                    </label>
                                    ${this.getFieldContentHtml(f, true)}
                                </div>
                            </div>
                        `;
                    });
                    contentHtml += `</div>`;
                } else {
                    contentHtml = `<div class="py-1"><hr class="my-2 border-secondary-subtle"></div>`;
                }
                break;
            }
            case 'multi_text':
                contentHtml = `
                    <div id="${sec.id}_container" class="mb-2"></div>
                    <button class="ds-btn ds-btn-ghost ds-btn-sm" type="button" onclick="DynamicRenderer.addMultiTextRow('${sec.id}')">
                        <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Item
                    </button>
                `;
                break;
            case 'table':
                contentHtml = `
                    <div class="table-responsive">
                        <table class="ds-table table-bordered mb-2" id="${sec.id}_table">
                            <thead>
                                <tr>
                                    <th>Item / Metric</th>
                                    <th>Planned / Target</th>
                                    <th>Actual / Outcome</th>
                                    <th>Status / Comments</th>
                                    <th style="width:40px;"></th>
                                </tr>
                            </thead>
                            <tbody></tbody>
                        </table>
                    </div>
                    <button class="ds-btn ds-btn-ghost ds-btn-sm" type="button" onclick="DynamicRenderer.addGeneralTableRow('${sec.id}')">
                        <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Row
                    </button>
                `;
                break;
            case 'file':
            case 'evidence':
            case 'file_upload':
                contentHtml = `
                    <div class="border rounded p-3 text-center bg-light" style="border-style: dashed !important; border-color: var(--ds-border-color) !important;">
                        <i data-lucide="upload-cloud" style="width:24px;height:24px;color:var(--ds-text-secondary);" class="mb-2"></i>
                        <input type="file" class="form-control form-control-sm mb-2" id="${sec.id}_file" onchange="DynamicRenderer.handleFileUpload('${sec.id}')">
                        <div id="${sec.id}_status" class="text-xs text-secondary mt-1">No file uploaded</div>
                        <input type="hidden" id="${sec.id}">
                    </div>
                `;
                break;
            case 'signature':
                contentHtml = `
                    <div class="d-flex align-items-center justify-content-between p-2 rounded bg-light border">
                        <div class="v-stack">
                            <span class="text-sm fw-semibold" id="${sec.id}_status_label">Pending Review Approval</span>
                            <span class="text-xs text-muted" id="${sec.id}_time_label">Not signed yet</span>
                        </div>
                        <div class="form-check form-switch">
                            <input class="form-check-input" type="checkbox" id="${sec.id}" onchange="DynamicRenderer.handleSignatureToggle('${sec.id}')">
                        </div>
                    </div>
                `;
                break;
            case 'pareto':
                contentHtml = `
                    <div class="row g-4">
                        <div class="col-lg-5 col-12">
                            <div class="table-responsive">
                                <table class="table table-bordered align-middle text-sm mb-2" id="${sec.id}_table">
                                    <thead style="background: rgba(15, 23, 42, 0.04);">
                                        <tr>
                                            <th>Defect / Category</th>
                                            <th>Frequency</th>
                                            <th style="width:40px;"></th>
                                        </tr>
                                    </thead>
                                    <tbody></tbody>
                                </table>
                            </div>
                            <button class="ds-btn ds-btn-ghost ds-btn-sm" type="button" onclick="DynamicRenderer.addParetoTableRow('${sec.id}')">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Category
                            </button>
                        </div>
                        <div class="col-lg-7 col-12">
                            <div class="border rounded p-3 bg-light d-flex align-items-center justify-content-center" style="min-height:280px; height: 100%;">
                                <canvas id="${sec.id}_chart" style="max-height:260px; width:100%;"></canvas>
                            </div>
                        </div>
                    </div>
                `;
                break;
            case 'fishbone':
                contentHtml = `
                    <div class="row g-3">
                        <div class="col-md-12">
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <label class="ds-label mb-0">Fishbone Diagram Visualization</label>
                                <div class="d-flex align-items-center gap-1 bg-light border p-1 rounded-3">
                                    <button type="button" class="ds-btn ds-btn-ghost p-1" style="height:26px;width:26px;" title="Zoom Out (-)" onclick="DynamicRenderer.zoomFishbone('${sec.id}', -0.15)">
                                        <i data-lucide="minus" style="width:12px;height:12px;"></i>
                                    </button>
                                    <span class="badge bg-white text-dark border px-2 py-1" id="${sec.id}_zoomBadge" style="font-size:0.75rem; min-width:40px; text-align:center;">100%</span>
                                    <button type="button" class="ds-btn ds-btn-ghost p-1" style="height:26px;width:26px;" title="Zoom In (+)" onclick="DynamicRenderer.zoomFishbone('${sec.id}', 0.15)">
                                        <i data-lucide="plus" style="width:12px;height:12px;"></i>
                                    </button>
                                    <button type="button" class="ds-btn ds-btn-ghost p-1 text-secondary ms-1" style="height:26px;width:26px;" title="Reset Zoom" onclick="DynamicRenderer.resetFishboneZoom('${sec.id}')">
                                        <i data-lucide="rotate-ccw" style="width:12px;height:12px;"></i>
                                    </button>
                                </div>
                            </div>
                            <div class="border rounded p-3 mb-2 overflow-auto qc-tool-card" style="min-height:300px; background: var(--ds-bg-card, #ffffff);">
                                <div id="${sec.id}_svgContainer" style="transform-origin: top left; transition: transform 0.2s ease-out;">
                                    <svg width="100%" height="320" viewBox="0 0 820 320" id="${sec.id}_svg" style="background:var(--ds-bg-card,#ffffff);">
                                    <defs>
                                        <marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
                                            <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--ds-primary)" />
                                        </marker>
                                    </defs>
                                    <line x1="40" y1="170" x2="680" y2="170" stroke="var(--ds-primary)" stroke-width="4" marker-end="url(#arrow)" />
                                    <rect x="680" y="125" width="115" height="90" rx="8" fill="rgba(var(--ds-primary-rgb),0.05)" stroke="var(--ds-primary)" stroke-width="2" />
                                    <text x="737" y="150" text-anchor="middle" font-size="10" font-weight="bold" fill="var(--ds-primary)">EFFECT (PROBLEM)</text>
                                    <text x="737" y="175" text-anchor="middle" font-size="10" font-weight="bold" fill="var(--ds-text-main)" id="${sec.id}_effect">Problem Definition</text>
                                    
                                    <line x1="160" y1="60" x2="230" y2="170" stroke="#4b5563" stroke-width="2" />
                                    <text x="160" y="50" font-size="11" font-weight="bold" fill="var(--ds-primary)">Man (People)</text>
                                    <g id="${sec.id}_bone_Man"></g>

                                    <line x1="330" y1="60" x2="400" y2="170" stroke="#4b5563" stroke-width="2" />
                                    <text x="330" y="50" font-size="11" font-weight="bold" fill="var(--ds-primary)">Machine</text>
                                    <g id="${sec.id}_bone_Machine"></g>

                                    <line x1="500" y1="60" x2="570" y2="170" stroke="#4b5563" stroke-width="2" />
                                    <text x="500" y="50" font-size="11" font-weight="bold" fill="var(--ds-primary)">Material</text>
                                    <g id="${sec.id}_bone_Material"></g>

                                    <line x1="160" y1="280" x2="230" y2="170" stroke="#4b5563" stroke-width="2" />
                                    <text x="160" y="295" font-size="11" font-weight="bold" fill="var(--ds-primary)">Method</text>
                                    <g id="${sec.id}_bone_Method"></g>

                                    <line x1="330" y1="280" x2="400" y2="170" stroke="#4b5563" stroke-width="2" />
                                    <text x="330" y="295" font-size="11" font-weight="bold" fill="var(--ds-primary)">Measurement</text>
                                    <g id="${sec.id}_bone_Measurement"></g>

                                    <line x1="500" y1="280" x2="570" y2="170" stroke="#4b5563" stroke-width="2" />
                                    <text x="500" y="295" font-size="11" font-weight="bold" fill="var(--ds-primary)">Environment</text>
                                    <g id="${sec.id}_bone_Environment"></g>
                                </svg>
                                </div>
                            </div>
                            <!-- Mobile Vertical Accordion Mode -->
                            <div id="${sec.id}_mobileAccordion" class="fishbone-mobile-accordion d-md-none mb-3"></div>
                        </div>
                        <div class="col-md-12">
                            <div class="table-responsive">
                                <table class="ds-table table-bordered mb-2" id="${sec.id}_table">
                                    <thead>
                                        <tr>
                                            <th>Category</th>
                                            <th>Cause (Level 1)</th>
                                            <th>Sub-Cause (Level 2)</th>
                                            <th style="width:40px;"></th>
                                        </tr>
                                    </thead>
                                    <tbody></tbody>
                                </table>
                            </div>
                            <button class="ds-btn ds-btn-ghost ds-btn-sm" type="button" onclick="DynamicRenderer.addFishboneTableRow('${sec.id}')">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Cause
                            </button>
                        </div>
                    </div>
                `;
                break;
            case '5why':
            case 'five_why':
                contentHtml = `
                    <div class="table-responsive">
                        <table class="ds-table table-bordered mb-2" id="${sec.id}_table">
                            <thead>
                                <tr>
                                    <th>Verified Cause</th>
                                    <th>Why 1</th>
                                    <th>Why 2</th>
                                    <th>Why 3</th>
                                    <th>Why 4</th>
                                    <th>Why 5</th>
                                    <th>Root Cause</th>
                                    <th style="width:40px;"></th>
                                </tr>
                            </thead>
                            <tbody></tbody>
                        </table>
                    </div>
                    <button class="ds-btn ds-btn-ghost ds-btn-sm" type="button" onclick="DynamicRenderer.addFiveWhyTableRow('${sec.id}')">
                        <i data-lucide="plus" style="width:12px;height:12px;"></i> Add 5-Why Analysis
                    </button>
                `;
                break;
            case 'verification_table':
                contentHtml = `
                    <div class="table-responsive">
                        <table class="ds-table table-bordered mb-2" id="${sec.id}_table">
                            <thead>
                                <tr>
                                    <th>Suspect Cause</th>
                                    <th>Verification Method</th>
                                    <th>Target / Criteria</th>
                                    <th>Result / Status</th>
                                    <th>Is Root Cause?</th>
                                    <th style="width:40px;"></th>
                                </tr>
                            </thead>
                            <tbody></tbody>
                        </table>
                    </div>
                    <button class="ds-btn ds-btn-ghost ds-btn-sm" type="button" onclick="DynamicRenderer.addVerificationTableRow('${sec.id}')">
                        <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Entry
                    </button>
                `;
                break;
            case 'check_sheet':
                contentHtml = `
                    <div class="table-responsive">
                        <table class="ds-table table-bordered mb-2" id="${sec.id}_table">
                            <thead>
                                <tr>
                                    <th>Defect Category / Check Item</th>
                                    <th>Tally (Tick box)</th>
                                    <th>Total Tally Count</th>
                                    <th style="width:40px;"></th>
                                </tr>
                            </thead>
                            <tbody></tbody>
                        </table>
                    </div>
                    <button class="ds-btn ds-btn-ghost ds-btn-sm" type="button" onclick="DynamicRenderer.addCheckSheetTableRow('${sec.id}')">
                        <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Check Item
                    </button>
                `;
                break;
            case 'histogram':
                contentHtml = `
                    <div class="row g-4">
                        <div class="col-lg-5 col-12">
                            <div class="table-responsive">
                                <table class="table table-bordered align-middle text-sm mb-2" id="${sec.id}_table">
                                    <thead style="background: rgba(15, 23, 42, 0.04);">
                                        <tr>
                                            <th>Interval / Class</th>
                                            <th>Freq (Before)</th>
                                            <th>Freq (After)</th>
                                            <th style="width:40px;"></th>
                                        </tr>
                                    </thead>
                                    <tbody></tbody>
                                </table>
                            </div>
                            <button class="ds-btn ds-btn-ghost ds-btn-sm" type="button" onclick="DynamicRenderer.addHistogramTableRow('${sec.id}')">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Interval
                            </button>
                        </div>
                        <div class="col-lg-7 col-12">
                            <div class="border rounded p-3 bg-light d-flex align-items-center justify-content-center" style="min-height:280px; height: 100%;">
                                <canvas id="${sec.id}_chart" style="max-height:260px; width:100%;"></canvas>
                            </div>
                        </div>
                    </div>
                `;
                break;
            case 'control_chart':
                contentHtml = `
                    <div class="row g-4">
                        <div class="col-lg-6 col-12">
                            <div class="table-responsive">
                                <table class="table table-bordered align-middle text-sm mb-2" id="${sec.id}_table">
                                    <thead style="background: rgba(15, 23, 42, 0.04);">
                                        <tr>
                                            <th style="min-width: 120px;">Date / Sample</th>
                                            <th style="min-width: 90px;">Value</th>
                                            <th style="min-width: 90px;">Target (CL)</th>
                                            <th style="min-width: 90px;">UCL</th>
                                            <th style="min-width: 90px;">LCL</th>
                                            <th style="width:40px;"></th>
                                        </tr>
                                    </thead>
                                    <tbody></tbody>
                                </table>
                            </div>
                            <button class="ds-btn ds-btn-ghost ds-btn-sm" type="button" onclick="DynamicRenderer.addControlChartTableRow('${sec.id}')">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Data Point
                            </button>
                        </div>
                        <div class="col-lg-6 col-12">
                            <div class="border rounded p-3 bg-light d-flex align-items-center justify-content-center" style="min-height:280px; height: 100%;">
                                <canvas id="${sec.id}_chart" style="max-height:260px; width:100%;"></canvas>
                            </div>
                        </div>
                    </div>
                `;
                break;
            case 'scatter':
                contentHtml = `
                    <div class="row g-4">
                        <div class="col-lg-5 col-12">
                            <div class="table-responsive">
                                <table class="table table-bordered align-middle text-sm mb-2" id="${sec.id}_table">
                                    <thead style="background: rgba(15, 23, 42, 0.04);">
                                        <tr>
                                            <th>Sample / Name</th>
                                            <th>Variable X</th>
                                            <th>Variable Y</th>
                                            <th style="width:40px;"></th>
                                        </tr>
                                    </thead>
                                    <tbody></tbody>
                                </table>
                            </div>
                            <button class="ds-btn ds-btn-ghost ds-btn-sm" type="button" onclick="DynamicRenderer.addScatterTableRow('${sec.id}')">
                                <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Point
                            </button>
                        </div>
                        <div class="col-lg-7 col-12">
                            <div class="border rounded p-3 bg-light d-flex align-items-center justify-content-center" style="min-height:280px; height: 100%;">
                                <canvas id="${sec.id}_chart" style="max-height:260px; width:100%;"></canvas>
                            </div>
                        </div>
                    </div>
                `;
                break;
            case 'stratification':
                contentHtml = `
                    <div class="row g-3">
                        <div class="col-md-6 mb-2">
                            <div class="border rounded p-3 bg-light">
                                <div class="fw-bold text-xs text-primary mb-2">Stratification by Category A (e.g. Shift)</div>
                                <div class="table-responsive">
                                    <table class="table table-bordered table-sm align-middle text-sm mb-1" id="${sec.id}_table_a">
                                        <thead style="background: rgba(15, 23, 42, 0.04);"><tr><th>Shift / Group</th><th>Count</th><th style="width:40px;"></th></tr></thead>
                                        <tbody></tbody>
                                    </table>
                                </div>
                                <button class="ds-btn ds-btn-ghost ds-btn-sm mt-2" type="button" onclick="DynamicRenderer.addStratRow('${sec.id}_table_a')">Add Row</button>
                            </div>
                        </div>
                        <div class="col-md-6 mb-2">
                            <div class="border rounded p-3 bg-light">
                                <div class="fw-bold text-xs text-primary mb-2">Stratification by Category B (e.g. Location)</div>
                                <div class="table-responsive">
                                    <table class="table table-bordered table-sm align-middle text-sm mb-1" id="${sec.id}_table_b">
                                        <thead style="background: rgba(15, 23, 42, 0.04);"><tr><th>Location / Group</th><th>Count</th><th style="width:40px;"></th></tr></thead>
                                        <tbody></tbody>
                                    </table>
                                </div>
                                <button class="ds-btn ds-btn-ghost ds-btn-sm mt-2" type="button" onclick="DynamicRenderer.addStratRow('${sec.id}_table_b')">Add Row</button>
                            </div>
                        </div>
                    </div>
                `;
                break;
            case 'grid_2col':
            case '2_column_grid':
            case 'grid_2_column': {
                const childFields = this.getAllRenderableFields(sec);
                if (childFields.length > 0) {
                    contentHtml = `<div class="row g-3">`;
                    childFields.forEach(f => {
                        const colW = f.col_span || f.col || 'col-md-6';
                        contentHtml += `
                            <div class="${colW}">
                                <div class="ds-field-block p-2.5 rounded border mb-2" style="background: var(--ds-bg-card, #ffffff);">
                                    <label class="ds-label text-xs fw-semibold mb-1 d-block text-main">
                                        ${this.escapeHtml(f.label || 'Field')} ${f.required ? '<span class="text-danger">*</span>' : ''}
                                    </label>
                                    ${this.getFieldContentHtml(f, true)}
                                </div>
                            </div>
                        `;
                    });
                    contentHtml += `</div>`;
                } else {
                    contentHtml = `
                        <div class="row g-3">
                            <div class="col-md-6"><div class="border rounded p-3 text-muted text-xs bg-light">Column 1 (Add fields inside layout)</div></div>
                            <div class="col-md-6"><div class="border rounded p-3 text-muted text-xs bg-light">Column 2 (Add fields inside layout)</div></div>
                        </div>
                    `;
                }
                break;
            }
            case 'grid_3col':
            case '3_column_grid':
            case 'grid_3_column': {
                const childFields = this.getAllRenderableFields(sec);
                if (childFields.length > 0) {
                    contentHtml = `<div class="row g-3">`;
                    childFields.forEach(f => {
                        const colW = f.col_span || f.col || 'col-md-4';
                        contentHtml += `
                            <div class="${colW}">
                                <div class="ds-field-block p-2.5 rounded border mb-2" style="background: var(--ds-bg-card, #ffffff);">
                                    <label class="ds-label text-xs fw-semibold mb-1 d-block text-main">
                                        ${this.escapeHtml(f.label || 'Field')} ${f.required ? '<span class="text-danger">*</span>' : ''}
                                    </label>
                                    ${this.getFieldContentHtml(f, true)}
                                </div>
                            </div>
                        `;
                    });
                    contentHtml += `</div>`;
                } else {
                    contentHtml = `
                        <div class="row g-3">
                            <div class="col-md-4"><div class="border rounded p-3 text-muted text-xs bg-light">Column 1</div></div>
                            <div class="col-md-4"><div class="border rounded p-3 text-muted text-xs bg-light">Column 2</div></div>
                            <div class="col-md-4"><div class="border rounded p-3 text-muted text-xs bg-light">Column 3</div></div>
                        </div>
                    `;
                }
                break;
            }
            case 'info_callout':
            case 'info':
            case 'callout': {
                const text = sec.placeholder || sec.description || sec.label || 'Information callout instructions';
                contentHtml = `
                    <div class="alert alert-info border-0 shadow-sm d-flex align-items-center gap-2 mb-0 py-2 px-3 text-xs" style="background: rgba(59, 130, 246, 0.1); color: #1e40af; border-radius: 8px;">
                        <i data-lucide="info" style="width:16px;height:16px;" class="flex-shrink-0"></i>
                        <div>${this.escapeHtml(text)}</div>
                    </div>
                `;
                break;
            }
            case 'attachment':
            case 'document_link': {
                const ph = sec.placeholder || 'https://drive.google.com/... or cloud document link';
                contentHtml = `
                    <div class="input-group input-group-sm">
                        <span class="input-group-text bg-light text-muted"><i data-lucide="link" style="width:14px;height:14px;"></i></span>
                        <input type="url" class="ds-input border-start-0" id="${sec.id}" placeholder="${this.escapeHtml(ph)}" ${sec.required === true ? 'required' : ''}>
                        <button class="ds-btn ds-btn-outline ds-btn-sm" type="button" onclick="const v=document.getElementById('${sec.id}')?.value; if(v) window.open(v,'_blank');">
                            Open Link
                        </button>
                    </div>
                `;
                break;
            }
            case 'action_btn':
            case 'view_link': {
                const label = sec.label || (type === 'action_btn' ? 'Trigger Action' : 'View / Inspect');
                contentHtml = `
                    <button class="ds-btn ds-btn-primary ds-btn-sm" type="button" id="${sec.id}_btn" onclick="if(window.QCMS && QCMS.toast) QCMS.toast('${this.escapeHtml(label)} triggered','info');">
                        <i data-lucide="${type === 'action_btn' ? 'play' : 'eye'}" style="width:14px;height:14px;margin-right:4px;"></i>
                        ${this.escapeHtml(label)}
                    </button>
                `;
                break;
            }
            case 'facilitator_gate': {
                contentHtml = `
                    <div class="d-flex align-items-center justify-content-between p-2.5 rounded bg-light border">
                        <div class="v-stack">
                            <span class="text-xs fw-bold text-main" id="${sec.id}_status_label">Facilitator Review Signoff</span>
                            <span class="text-xxs text-muted" id="${sec.id}_time_label">Pending Facilitator Approval</span>
                        </div>
                        <div class="form-check form-switch">
                            <input class="form-check-input" type="checkbox" id="${sec.id}">
                        </div>
                    </div>
                `;
                break;
            }
            case '3w1h':
            case 'action_plan':
            case 'action_plan_3w1h': {
                contentHtml = `
                    <div class="table-responsive">
                        <table class="ds-table table-bordered mb-2" id="${sec.id}_table">
                            <thead>
                                <tr>
                                    <th>What (Countermeasure Action)</th>
                                    <th>Who (Owner / Leader)</th>
                                    <th>When (Target Date)</th>
                                    <th>How (Implementation Method)</th>
                                    <th>Status</th>
                                    <th style="width:40px;"></th>
                                </tr>
                            </thead>
                            <tbody></tbody>
                        </table>
                    </div>
                    <button class="ds-btn ds-btn-ghost ds-btn-sm" type="button" onclick="DynamicRenderer.addActionPlanTableRow('${sec.id}')">
                        <i data-lucide="plus" style="width:12px;height:12px;"></i> Add Action Item
                    </button>
                `;
                break;
            }
            case 'custom': {
                let descHtml = '';
                if (sec.description && sec.description.trim()) {
                    descHtml = `<div class="text-muted text-xs mb-3 bg-light p-2.5 rounded border-start border-3 border-primary">${this.escapeHtml(sec.description)}</div>`;
                }
                const subFields = Array.isArray(sec.fields) ? sec.fields : (Array.isArray(sec.custom_fields) ? sec.custom_fields : []);
                if (subFields.length > 0) {
                    let fieldsGrid = `<div class="row g-3">`;
                    subFields.forEach(f => {
                        if (!f) return;
                        const fullCol = ['textarea', 'multi_line_text', 'table', 'five_why', '5why', 'verification_table', 'pareto', 'fishbone', 'histogram', 'control_chart', 'scatter', 'stratification', 'check_sheet', 'grid_2col', 'grid_3col', 'info_callout', 'action_plan_3w1h', '3w1h', 'action_plan'].includes((f.type || '').toLowerCase());
                        const colW = f.col_span || f.col || (fullCol ? 'col-12' : 'col-md-6');
                        fieldsGrid += `
                            <div class="${colW}">
                                <div class="ds-field-block p-2.5 rounded border mb-2 bg-white">
                                    <label class="ds-label text-xs fw-semibold mb-1 d-block text-main">
                                        ${this.escapeHtml(f.label || 'Field')} ${f.required ? '<span class="text-danger">*</span>' : ''}
                                    </label>
                                    ${this.getFieldContentHtml(f, true)}
                                </div>
                            </div>
                        `;
                    });
                    fieldsGrid += `</div>`;
                    contentHtml = descHtml + fieldsGrid;
                } else {
                    contentHtml = `
                        ${descHtml}
                        <div class="ds-field">
                            <textarea class="ds-input ds-textarea" id="${sec.id}" rows="3" placeholder="${this.escapeHtml(sec.placeholder || 'Enter notes or details for this custom section...')}"></textarea>
                        </div>
                    `;
                }
                break;
            }
            default:
                contentHtml = `<p class="text-xs text-danger mb-0 py-1">Unsupported field component type: ${this.escapeHtml(type)}</p>`;
        }

        if (isSubItem) {
            const topDesc = (sec.description && sec.description.trim() && type !== 'custom')
                ? `<div class="text-muted text-xs mb-3 bg-light p-2.5 rounded border-start border-3 border-primary">${this.escapeHtml(sec.description)}</div>`
                : '';
            return topDesc + contentHtml;
        }

        const colWidth = (['textarea', 'multi_line_text', 'table', 'five_why', 'verification_table', 'pareto', 'fishbone', 'histogram', 'control_chart', 'scatter', 'stratification', 'check_sheet', 'grid_2col', 'grid_3col', 'info_callout', 'action_plan_3w1h'].includes(type)) ? 'col-12' : 'col-md-6';
        const orderLabel = (sec.order !== undefined && sec.order !== null && sec.order !== 'undefined') ? sec.order : '';
        const orderCircle = orderLabel ? `<span class="ds-icon-circle bg-primary-soft text-primary" style="width:24px;height:24px;font-size:.65rem;font-weight:700;">${orderLabel}</span>` : '';

        const naToggleHtml = sec.allow_na ? `
            <div class="form-check form-switch mb-0 ms-auto sec-na-toggle-wrap" title="Toggle section applicability" onclick="event.stopPropagation();">
                <input class="form-check-input section-na-toggle" type="checkbox" role="switch" checked data-sec-id="${sec.id}">
                <label class="text-xs fw-semibold text-success ms-1 mb-0 sec-na-label">Applicable</label>
            </div>
        ` : '';

        return `
            <div class="${colWidth}">
                <div class="glass-card ds-card mb-3" id="card_${sec.id}" data-sec-id="${sec.id}">
                    <div class="ds-card-header p-3 border-bottom d-flex align-items-center justify-content-between">
                        <h6 class="mb-0 fw-bold d-flex align-items-center gap-2">
                            ${orderCircle}
                            ${this.escapeHtml(sec.label || 'Section')}${sec.required === true ? ' <span class="text-danger">*</span>' : ''}
                        </h6>
                        ${naToggleHtml}
                    </div>
                    <div class="ds-card-body p-3">
                        ${contentHtml}
                    </div>
                </div>
            </div>
        `;
    },

    // ── Prefill Logic ─────────────────────────────────────────────────────────────
    init(projectData, stageId) {
        this.activeStageId = stageId;
        const stageData = (projectData.workflows || []).find(w => w.stage_id === stageId)?.data || {};

        this.sections.forEach(sec => {
            const val = stageData[sec.id];

            if (sec.allow_na) {
                const cardEl = document.getElementById(`card_${sec.id}`);
                if (cardEl) {
                    const toggleInput = cardEl.querySelector('.section-na-toggle');
                    const labelEl = cardEl.querySelector('.sec-na-label');
                    const cardBody = cardEl.querySelector('.ds-card-body');

                    const updateNAState = (isApplicable) => {
                        cardEl.dataset.applicable = isApplicable ? 'true' : 'false';
                        if (isApplicable) {
                            if (labelEl) {
                                labelEl.textContent = 'Applicable';
                                labelEl.className = 'text-xs fw-semibold text-success ms-1 mb-0 sec-na-label';
                            }
                            if (cardBody) {
                                cardBody.style.opacity = '1';
                                cardBody.style.filter = 'none';
                                cardBody.style.pointerEvents = 'auto';
                                cardBody.querySelectorAll('input, select, textarea, button').forEach(el => {
                                    if (!el.classList.contains('section-na-toggle')) el.disabled = false;
                                });
                            }
                        } else {
                            if (labelEl) {
                                labelEl.textContent = 'Not Applicable (N/A)';
                                labelEl.className = 'text-xs fw-semibold text-secondary ms-1 mb-0 sec-na-label';
                            }
                            if (cardBody) {
                                cardBody.style.opacity = '0.45';
                                cardBody.style.filter = 'grayscale(0.5)';
                                cardBody.style.pointerEvents = 'none';
                                cardBody.querySelectorAll('input, select, textarea, button').forEach(el => {
                                    if (!el.classList.contains('section-na-toggle')) el.disabled = true;
                                });
                            }
                        }
                    };

                    const isInitiallyApplicable = !(val && val.applicable === false);
                    if (toggleInput) {
                        toggleInput.checked = isInitiallyApplicable;
                        updateNAState(isInitiallyApplicable);
                        toggleInput.onchange = (e) => updateNAState(e.target.checked);
                    }
                }
            }

            const allItems = this.getAllRenderableFields(sec);
            const itemsToInit = allItems.length > 0 ? allItems : [sec];

            itemsToInit.forEach(item => {
                const itemVal = stageData[item.id] || (val && typeof val === 'object' ? val[item.id] : null);
                const itemType = (item.type || 'text').toLowerCase();

                switch (itemType) {
                    case 'text':
                    case 'single_line_text':
                    case 'input':
                    case 'number':
                    case 'numeric':
                    case 'date':
                    case 'date_picker':
                    case 'textarea':
                    case 'multi_line_text':
                    case 'select':
                    case 'dropdown':
                        const el = document.getElementById(item.id);
                        if (el) el.value = itemVal || '';
                        break;
                    case 'checkbox':
                    case 'toggle':
                        const chk = document.getElementById(item.id);
                        if (chk) chk.checked = !!itemVal;
                        break;
                    case 'multi_text':
                        const container = document.getElementById(`${item.id}_container`);
                        if (container) container.innerHTML = '';
                        if (Array.isArray(itemVal)) {
                            itemVal.forEach(it => this.addMultiTextRow(item.id, it));
                        } else {
                            this.addMultiTextRow(item.id);
                        }
                        break;
                    case 'table':
                        const tBody = document.querySelector(`#${item.id}_table tbody`);
                        if (tBody) tBody.innerHTML = '';
                        if (Array.isArray(itemVal)) {
                            itemVal.forEach(row => this.addGeneralTableRow(item.id, row));
                        } else {
                            this.addGeneralTableRow(item.id);
                        }
                        break;
                    case 'file_upload':
                        const hiddenInput = document.getElementById(item.id);
                        const statusDiv = document.getElementById(`${item.id}_status`);
                        if (hiddenInput) hiddenInput.value = itemVal || '';
                        if (statusDiv) statusDiv.textContent = itemVal ? `Uploaded: ${itemVal.split('/').pop()}` : 'No file uploaded';
                        break;
                    case 'signature':
                        const sigCheck = document.getElementById(item.id);
                        if (sigCheck) {
                            sigCheck.checked = !!(itemVal && itemVal.signed);
                            this.updateSignatureUI(item.id, itemVal);
                        }
                        break;
                    case 'pareto':
                        const pBody = document.querySelector(`#${item.id}_table tbody`);
                        if (pBody) pBody.innerHTML = '';
                        if (Array.isArray(itemVal)) {
                            itemVal.forEach(row => this.addParetoTableRow(item.id, row));
                        } else {
                            this.addParetoTableRow(item.id, {});
                        }
                        this.updateParetoChart(item.id);
                        break;
                    case 'fishbone':
                        const effectLabel = document.getElementById(`${item.id}_effect`);
                        if (effectLabel) effectLabel.textContent = projectData.title || 'Problem Definition';
                        const fBody = document.querySelector(`#${item.id}_table tbody`);
                        if (fBody) fBody.innerHTML = '';
                        if (Array.isArray(itemVal)) {
                            itemVal.forEach(row => this.addFishboneTableRow(item.id, row));
                        } else {
                            this.addFishboneTableRow(item.id, { category: 'Man', cause: '', sub_cause: '' });
                        }
                        this.updateFishboneSVG(item.id);
                        break;
                    case 'five_why':
                        const fwBody = document.querySelector(`#${item.id}_table tbody`);
                        if (fwBody) fwBody.innerHTML = '';
                        if (Array.isArray(itemVal)) {
                            itemVal.forEach(row => this.addFiveWhyTableRow(item.id, row));
                        } else {
                            this.addFiveWhyTableRow(item.id);
                        }
                        break;
                    case 'verification_table':
                        const vBody = document.querySelector(`#${item.id}_table tbody`);
                        if (vBody) vBody.innerHTML = '';
                        if (Array.isArray(itemVal)) {
                            itemVal.forEach(row => this.addVerificationTableRow(item.id, row));
                        } else {
                            this.addVerificationTableRow(item.id);
                        }
                        break;
                    case 'check_sheet':
                        const csBody = document.querySelector(`#${item.id}_table tbody`);
                        if (csBody) csBody.innerHTML = '';
                        if (Array.isArray(itemVal)) {
                            itemVal.forEach(row => this.addCheckSheetTableRow(item.id, row));
                        } else {
                            this.addCheckSheetTableRow(item.id);
                        }
                        break;
                    case 'histogram':
                        const hBody = document.querySelector(`#${item.id}_table tbody`);
                        if (hBody) hBody.innerHTML = '';
                        if (Array.isArray(itemVal)) {
                            itemVal.forEach(row => this.addHistogramTableRow(item.id, row));
                        } else {
                            this.addHistogramTableRow(item.id, {});
                        }
                        this.updateHistogramChart(item.id);
                        break;
                    case 'control_chart':
                        const ccBody = document.querySelector(`#${item.id}_table tbody`);
                        if (ccBody) ccBody.innerHTML = '';
                        if (Array.isArray(itemVal)) {
                            itemVal.forEach(row => this.addControlChartTableRow(item.id, row));
                        } else {
                            this.addControlChartTableRow(item.id, {});
                        }
                        this.updateControlChart(item.id);
                        break;
                    case 'scatter':
                        const scBody = document.querySelector(`#${item.id}_table tbody`);
                        if (scBody) scBody.innerHTML = '';
                        if (Array.isArray(itemVal)) {
                            itemVal.forEach(row => this.addScatterTableRow(item.id, row));
                        } else {
                            this.addScatterTableRow(item.id, {});
                        }
                        this.updateScatterChart(item.id);
                        break;
                    case 'action_plan_3w1h':
                        const apBody = document.querySelector(`#${item.id}_table tbody`);
                        if (apBody) apBody.innerHTML = '';
                        if (Array.isArray(itemVal) && itemVal.length > 0) {
                            itemVal.forEach(row => this.addActionPlanTableRow(item.id, row));
                        } else {
                            this.addActionPlanTableRow(item.id, {});
                        }
                        break;
                    case 'attachment':
                    case 'document_link':
                        const docEl = document.getElementById(item.id);
                        if (docEl) docEl.value = itemVal || '';
                        break;
                    case 'facilitator_gate':
                        const facCheck = document.getElementById(item.id);
                        if (facCheck) facCheck.checked = !!itemVal;
                        break;
                }
            });
        });

        if (window.lucide) lucide.createIcons();
    },

    // ── Data Collection Logic ─────────────────────────────────────────────────────
    collectData() {
        const data = {};

        this.sections.forEach(sec => {
            const allItems = this.getAllRenderableFields(sec);
            const itemsToCollect = allItems.length > 0 ? allItems : [sec];

            itemsToCollect.forEach(item => {
                const itemType = (item.type || 'text').toLowerCase();

                switch (itemType) {
                    case 'text':
                    case 'single_line_text':
                    case 'input':
                    case 'number':
                    case 'numeric':
                    case 'date':
                    case 'date_picker':
                    case 'textarea':
                    case 'multi_line_text':
                    case 'select':
                    case 'dropdown':
                        data[item.id] = document.getElementById(item.id)?.value || '';
                        break;
                    case 'checkbox':
                    case 'toggle':
                        data[item.id] = !!document.getElementById(item.id)?.checked;
                        break;
                    case 'multi_text':
                        data[item.id] = [...document.querySelectorAll(`#${item.id}_container .multi-text-input`)].map(i => i.value).filter(v => v.trim());
                        break;
                    case 'table':
                        data[item.id] = [...document.querySelectorAll(`#${item.id}_table tbody tr`)].map(tr => ({
                            item: tr.querySelector('.cell-item')?.value || '',
                            target: tr.querySelector('.cell-target')?.value || '',
                            actual: tr.querySelector('.cell-actual')?.value || '',
                            comments: tr.querySelector('.cell-comments')?.value || ''
                        })).filter(r => r.item.trim());
                        break;
                    case 'file_upload':
                        data[item.id] = document.getElementById(item.id)?.value || '';
                        break;
                    case 'signature':
                        const sigCheck = document.getElementById(item.id);
                        const user = JSON.parse(sessionStorage.getItem('user') || '{}');
                        data[item.id] = {
                            signed: !!(sigCheck && sigCheck.checked),
                            signed_by: sigCheck && sigCheck.checked ? (user.full_name || user.username || 'Reviewer') : '',
                            signed_at: sigCheck && sigCheck.checked ? new Date().toISOString() : ''
                        };
                        break;
                    case 'pareto':
                        data[item.id] = [...document.querySelectorAll(`#${item.id}_table tbody tr`)].map(tr => ({
                            category: tr.querySelector('.cell-cat')?.value || '',
                            count: parseInt(tr.querySelector('.cell-count')?.value || 0)
                        })).filter(r => r.category.trim());
                        break;
                    case 'fishbone':
                        data[item.id] = [...document.querySelectorAll(`#${item.id}_table tbody tr`)].map(tr => ({
                            category: tr.querySelector('.cell-cat')?.value || 'Man',
                            cause: tr.querySelector('.cell-cause')?.value || '',
                            sub_cause: tr.querySelector('.cell-subcause')?.value || ''
                        })).filter(r => r.cause.trim());
                        break;
                    case 'five_why':
                        data[item.id] = [...document.querySelectorAll(`#${item.id}_table tbody tr`)].map(tr => ({
                            cause: tr.querySelector('.cell-cause')?.value || '',
                            why1: tr.querySelector('.cell-w1')?.value || '',
                            why2: tr.querySelector('.cell-w2')?.value || '',
                            why3: tr.querySelector('.cell-w3')?.value || '',
                            why4: tr.querySelector('.cell-w4')?.value || '',
                            why5: tr.querySelector('.cell-w5')?.value || '',
                            root_cause: tr.querySelector('.cell-root')?.value || ''
                        })).filter(r => r.cause.trim());
                        break;
                    case 'verification_table':
                        data[item.id] = [...document.querySelectorAll(`#${item.id}_table tbody tr`)].map(tr => ({
                            cause: tr.querySelector('.cell-cause')?.value || '',
                            method: tr.querySelector('.cell-method')?.value || '',
                            criteria: tr.querySelector('.cell-criteria')?.value || '',
                            result: tr.querySelector('.cell-result')?.value || '',
                            is_root: tr.querySelector('.cell-root')?.value || 'No'
                        })).filter(r => r.cause.trim());
                        break;
                    case 'check_sheet':
                        data[item.id] = [...document.querySelectorAll(`#${item.id}_table tbody tr`)].map(tr => ({
                            item: tr.querySelector('.cell-item')?.value || '',
                            checked: !!tr.querySelector('.cell-check')?.checked,
                            count: parseInt(tr.querySelector('.cell-count')?.value || 0)
                        })).filter(r => r.item.trim());
                        break;
                    case 'histogram':
                        data[item.id] = [...document.querySelectorAll(`#${item.id}_table tbody tr`)].map(tr => ({
                            interval: tr.querySelector('.cell-interval')?.value || '',
                            freq_before: parseFloat(tr.querySelector('.cell-before')?.value || 0),
                            freq_after: parseFloat(tr.querySelector('.cell-after')?.value || 0)
                        })).filter(r => r.interval.trim());
                        break;
                    case 'control_chart':
                        data[item.id] = [...document.querySelectorAll(`#${item.id}_table tbody tr`)].map(tr => ({
                            sample: tr.querySelector('.cell-sample')?.value || '',
                            val: parseFloat(tr.querySelector('.cell-val')?.value || 0),
                            cl: parseFloat(tr.querySelector('.cell-cl')?.value || 0),
                            ucl: parseFloat(tr.querySelector('.cell-ucl')?.value || 0),
                            lcl: parseFloat(tr.querySelector('.cell-lcl')?.value || 0)
                        })).filter(r => r.sample.trim());
                        break;
                    case 'scatter':
                        data[item.id] = [...document.querySelectorAll(`#${item.id}_table tbody tr`)].map(tr => ({
                            sample: tr.querySelector('.cell-sample')?.value || '',
                            x: parseFloat(tr.querySelector('.cell-x')?.value || 0),
                            y: parseFloat(tr.querySelector('.cell-y')?.value || 0)
                        })).filter(r => r.sample.trim());
                        break;
                    case 'stratification':
                        data[item.id] = {
                            table_a: [...document.querySelectorAll(`#${item.id}_table_a tbody tr`)].map(tr => ({
                                group: tr.querySelector('.cell-group')?.value || '',
                                count: parseInt(tr.querySelector('.cell-count')?.value || 0)
                            })).filter(r => r.group.trim()),
                            table_b: [...document.querySelectorAll(`#${item.id}_table_b tbody tr`)].map(tr => ({
                                group: tr.querySelector('.cell-group')?.value || '',
                                count: parseInt(tr.querySelector('.cell-count')?.value || 0)
                            })).filter(r => r.group.trim())
                        };
                        break;
                    case 'action_plan_3w1h':
                        data[item.id] = [...document.querySelectorAll(`#${item.id}_table tbody tr`)].map(tr => ({
                            what: tr.querySelector('.cell-what')?.value || '',
                            who: tr.querySelector('.cell-who')?.value || '',
                            when: tr.querySelector('.cell-when')?.value || '',
                            how: tr.querySelector('.cell-how')?.value || '',
                            status: tr.querySelector('.cell-status')?.value || 'Pending'
                        })).filter(r => r.what.trim());
                        break;
                    case 'attachment':
                    case 'document_link':
                        data[item.id] = document.getElementById(item.id)?.value || '';
                        break;
                    case 'facilitator_gate':
                        data[item.id] = !!document.getElementById(item.id)?.checked;
                        break;
                }
            });
        });

        return data;
    },

    // ── Row Insertion Handlers ────────────────────────────────────────────────────
    addMultiTextRow(secId, val = '') {
        const container = document.getElementById(`${secId}_container`);
        if (!container) return;
        const div = document.createElement('div');
        div.className = 'd-flex gap-2 mb-2 align-items-center';
        div.innerHTML = `
            <input type="text" class="ds-input multi-text-input" value="${val}" placeholder="Bullet point item...">
            <button class="ds-btn ds-btn-ghost text-danger p-2" type="button" onclick="this.closest('div').remove()">
                <i data-lucide="trash-2" style="width:14px;height:14px;"></i>
            </button>
        `;
        container.appendChild(div);
        if (window.lucide) lucide.createIcons();
    },

    addGeneralTableRow(secId, row = {}) {
        const tbody = document.querySelector(`#${secId}_table tbody`);
        if (!tbody) return;
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><input type="text" class="ds-input py-1 text-sm cell-item" value="${row.item || ''}" placeholder="e.g. Audit task"></td>
            <td><input type="text" class="ds-input py-1 text-sm cell-target" value="${row.target || ''}" placeholder="Target value"></td>
            <td><input type="text" class="ds-input py-1 text-sm cell-actual" value="${row.actual || ''}" placeholder="Actual outcome"></td>
            <td><input type="text" class="ds-input py-1 text-sm cell-comments" value="${row.comments || ''}" placeholder="Comments"></td>
            <td class="text-center">
                <button class="ds-btn ds-btn-ghost text-danger p-1" type="button" onclick="this.closest('tr').remove()">
                    <i data-lucide="trash-2" style="width:14px;height:14px;"></i>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
        if (window.lucide) lucide.createIcons();
    },

    addParetoTableRow(secId, row = {}) {
        const tbody = document.querySelector(`#${secId}_table tbody`);
        if (!tbody) return;
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><input type="text" class="table-input cell-cat" value="${row.category || ''}" placeholder="Category" oninput="DynamicRenderer.updateParetoChart('${secId}')"></td>
            <td><input type="number" class="table-input cell-count" value="${row.count || 0}" placeholder="Count" oninput="DynamicRenderer.updateParetoChart('${secId}')"></td>
            <td class="text-center">
                <button class="ds-btn ds-btn-ghost text-danger p-1" type="button" onclick="this.closest('tr').remove(); DynamicRenderer.updateParetoChart('${secId}')">
                    <i data-lucide="trash-2" style="width:14px;height:14px;"></i>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
        if (window.lucide) lucide.createIcons();
    },

    addFishboneTableRow(secId, row = {}, parentTr = null) {
        const tbody = document.querySelector(`#${secId}_table tbody`);
        if (!tbody) return;
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>
                <select class="ds-input ds-select py-1 text-sm cell-cat" onchange="DynamicRenderer.updateFishboneSVG('${secId}')">
                    ${['Man','Machine','Material','Method','Measurement','Environment'].map(c => `<option ${row.category===c?'selected':''}>${c}</option>`).join('')}
                </select>
            </td>
            <td><input type="text" class="ds-input py-1 text-sm cell-cause" value="${row.cause || ''}" placeholder="Level 1 Cause" onchange="DynamicRenderer.updateFishboneSVG('${secId}')"></td>
            <td><input type="text" class="ds-input py-1 text-sm cell-subcause" value="${row.sub_cause || ''}" maxlength="35" placeholder="Level 2 Cause (max 35 chars)" onchange="DynamicRenderer.updateFishboneSVG('${secId}')"></td>
            <td class="text-center">
                <div class="d-flex align-items-center justify-content-center gap-1">
                    <button class="ds-btn ds-btn-outline ds-btn-xs text-primary" style="font-size:0.7rem; padding: 0.2rem 0.4rem; white-space: nowrap;" type="button" onclick="DynamicRenderer.addSubCauseTableRow('${secId}', this)" title="Add another sub-cause for this cause">+ Sub-Cause</button>
                    <button class="ds-btn ds-btn-ghost text-danger p-1" type="button" onclick="this.closest('tr').remove(); DynamicRenderer.updateFishboneSVG('${secId}')">
                        <i data-lucide="trash-2" style="width:14px;height:14px;"></i>
                    </button>
                </div>
            </td>
        `;
        if (parentTr && parentTr.nextSibling) {
            tbody.insertBefore(tr, parentTr.nextSibling);
        } else {
            tbody.appendChild(tr);
        }
        if (window.lucide) lucide.createIcons();
    },

    addSubCauseTableRow(secId, btn) {
        const tr = btn ? btn.closest('tr') : null;
        const cat = tr ? (tr.querySelector('.cell-cat')?.value || 'Man') : 'Man';
        const cause = tr ? (tr.querySelector('.cell-cause')?.value || '') : '';
        this.addFishboneTableRow(secId, { category: cat, cause: cause, sub_cause: '' }, tr);
        if (tr && tr.nextSibling) {
            const subInput = tr.nextSibling.querySelector('.cell-subcause');
            if (subInput) subInput.focus();
        }
        this.updateFishboneSVG(secId);
    },

    addActionPlanTableRow(secId, row = {}) {
        const tbody = document.querySelector(`#${secId}_table tbody`);
        if (!tbody) return;
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><input type="text" class="ds-input py-1 text-sm cell-what" value="${this.escapeHtml(row.what || '')}" placeholder="Countermeasure action"></td>
            <td><input type="text" class="ds-input py-1 text-sm cell-who" value="${this.escapeHtml(row.who || '')}" placeholder="Owner / Lead"></td>
            <td><input type="date" class="ds-input py-1 text-sm cell-when" value="${this.escapeHtml(row.when || '')}"></td>
            <td><input type="text" class="ds-input py-1 text-sm cell-how" value="${this.escapeHtml(row.how || '')}" placeholder="Implementation method"></td>
            <td>
                <select class="ds-input ds-select py-1 text-sm cell-status">
                    <option value="Pending" ${row.status === 'Pending' ? 'selected' : ''}>Pending</option>
                    <option value="In Progress" ${row.status === 'In Progress' ? 'selected' : ''}>In Progress</option>
                    <option value="Completed" ${row.status === 'Completed' ? 'selected' : ''}>Completed</option>
                </select>
            </td>
            <td class="text-center">
                <button class="ds-btn ds-btn-ghost text-danger p-1" type="button" onclick="this.closest('tr').remove()">
                    <i data-lucide="trash-2" style="width:14px;height:14px;"></i>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
        if (window.lucide) lucide.createIcons();
    },

    addFiveWhyTableRow(secId, row = {}) {
        const tbody = document.querySelector(`#${secId}_table tbody`);
        if (!tbody) return;
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><input type="text" class="ds-input py-1 text-sm cell-cause" value="${row.cause || ''}" placeholder="Direct Cause"></td>
            <td><input type="text" class="ds-input py-1 text-sm cell-w1" value="${row.why1 || ''}"></td>
            <td><input type="text" class="ds-input py-1 text-sm cell-w2" value="${row.why2 || ''}"></td>
            <td><input type="text" class="ds-input py-1 text-sm cell-w3" value="${row.why3 || ''}"></td>
            <td><input type="text" class="ds-input py-1 text-sm cell-w4" value="${row.why4 || ''}"></td>
            <td><input type="text" class="ds-input py-1 text-sm cell-w5" value="${row.why5 || ''}"></td>
            <td><input type="text" class="ds-input py-1 text-sm cell-root" value="${row.root_cause || ''}" placeholder="Root Cause"></td>
            <td class="text-center">
                <button class="ds-btn ds-btn-ghost text-danger p-1" type="button" onclick="this.closest('tr').remove()">
                    <i data-lucide="trash-2" style="width:14px;height:14px;"></i>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
        if (window.lucide) lucide.createIcons();
    },

    addVerificationTableRow(secId, row = {}) {
        const tbody = document.querySelector(`#${secId}_table tbody`);
        if (!tbody) return;
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><input type="text" class="ds-input py-1 text-sm cell-cause" value="${row.cause || ''}" placeholder="Suspect Cause"></td>
            <td><input type="text" class="ds-input py-1 text-sm cell-method" value="${row.method || ''}" placeholder="Method"></td>
            <td><input type="text" class="ds-input py-1 text-sm cell-criteria" value="${row.criteria || ''}"></td>
            <td><input type="text" class="ds-input py-1 text-sm cell-result" value="${row.result || ''}"></td>
            <td>
                <select class="ds-input ds-select py-1 text-sm cell-root">
                    <option ${row.is_root==='No'?'selected':''}>No</option>
                    <option ${row.is_root==='Yes'?'selected':''}>Yes</option>
                </select>
            </td>
            <td class="text-center">
                <button class="ds-btn ds-btn-ghost text-danger p-1" type="button" onclick="this.closest('tr').remove()">
                    <i data-lucide="trash-2" style="width:14px;height:14px;"></i>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
        if (window.lucide) lucide.createIcons();
    },

    addCheckSheetTableRow(secId, row = {}) {
        const tbody = document.querySelector(`#${secId}_table tbody`);
        if (!tbody) return;
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><input type="text" class="ds-input py-1 text-sm cell-item" value="${row.item || ''}" placeholder="e.g. Scratches"></td>
            <td class="text-center"><input type="checkbox" class="form-check-input cell-check" ${row.checked?'checked':''} onchange="DynamicRenderer.handleCheckTally(this)"></td>
            <td><input type="number" class="ds-input py-1 text-sm cell-count" value="${row.count || 0}" placeholder="0"></td>
            <td class="text-center">
                <button class="ds-btn ds-btn-ghost text-danger p-1" type="button" onclick="this.closest('tr').remove()">
                    <i data-lucide="trash-2" style="width:14px;height:14px;"></i>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
        if (window.lucide) lucide.createIcons();
    },

    handleCheckTally(checkbox) {
        const row = checkbox.closest('tr');
        const countInput = row.querySelector('.cell-count');
        if (countInput) {
            let count = parseInt(countInput.value || 0);
            if (checkbox.checked) count += 1;
            countInput.value = count;
        }
    },

    addHistogramTableRow(secId, row = {}) {
        const tbody = document.querySelector(`#${secId}_table tbody`);
        if (!tbody) return;
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><input type="text" class="table-input cell-interval" value="${row.interval || ''}" placeholder="Interval" oninput="DynamicRenderer.updateHistogramChart('${secId}')"></td>
            <td><input type="number" class="table-input cell-before" value="${row.freq_before || 0}" oninput="DynamicRenderer.updateHistogramChart('${secId}')"></td>
            <td><input type="number" class="table-input cell-after" value="${row.freq_after || 0}" oninput="DynamicRenderer.updateHistogramChart('${secId}')"></td>
            <td class="text-center">
                <button class="ds-btn ds-btn-ghost text-danger p-1" type="button" onclick="this.closest('tr').remove(); DynamicRenderer.updateHistogramChart('${secId}')">
                    <i data-lucide="trash-2" style="width:14px;height:14px;"></i>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
        if (window.lucide) lucide.createIcons();
    },

    addControlChartTableRow(secId, row = {}) {
        const tbody = document.querySelector(`#${secId}_table tbody`);
        if (!tbody) return;
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><input type="text" class="table-input cell-sample" value="${row.sample || ''}" placeholder="Sample" oninput="DynamicRenderer.updateControlChart('${secId}')"></td>
            <td><input type="number" step="any" class="table-input cell-val" value="${row.val || 0}" oninput="DynamicRenderer.updateControlChart('${secId}')"></td>
            <td><input type="number" step="any" class="table-input cell-cl" value="${row.cl || 0}" oninput="DynamicRenderer.updateControlChart('${secId}')"></td>
            <td><input type="number" step="any" class="table-input cell-ucl" value="${row.ucl || 0}" oninput="DynamicRenderer.updateControlChart('${secId}')"></td>
            <td><input type="number" step="any" class="table-input cell-lcl" value="${row.lcl || 0}" oninput="DynamicRenderer.updateControlChart('${secId}')"></td>
            <td class="text-center">
                <button class="ds-btn ds-btn-ghost text-danger p-1" type="button" onclick="this.closest('tr').remove(); DynamicRenderer.updateControlChart('${secId}')">
                    <i data-lucide="trash-2" style="width:14px;height:14px;"></i>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
        if (window.lucide) lucide.createIcons();
    },

    addScatterTableRow(secId, row = {}) {
        const tbody = document.querySelector(`#${secId}_table tbody`);
        if (!tbody) return;
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><input type="text" class="table-input cell-sample" value="${row.sample || ''}" placeholder="Sample" oninput="DynamicRenderer.updateScatterChart('${secId}')"></td>
            <td><input type="number" step="any" class="table-input cell-x" value="${row.x || 0}" oninput="DynamicRenderer.updateScatterChart('${secId}')"></td>
            <td><input type="number" step="any" class="table-input cell-y" value="${row.y || 0}" oninput="DynamicRenderer.updateScatterChart('${secId}')"></td>
            <td class="text-center">
                <button class="ds-btn ds-btn-ghost text-danger p-1" type="button" onclick="this.closest('tr').remove(); DynamicRenderer.updateScatterChart('${secId}')">
                    <i data-lucide="trash-2" style="width:14px;height:14px;"></i>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
        if (window.lucide) lucide.createIcons();
    },

    addStratRow(tableId, row = {}) {
        const tbody = document.querySelector(`#${tableId} tbody`);
        if (!tbody) return;
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td><input type="text" class="table-input cell-group" value="${row.group || ''}" placeholder="e.g. Shift 1"></td>
            <td><input type="number" class="table-input cell-count" value="${row.count || 0}" placeholder="Count"></td>
            <td class="text-center">
                <button class="ds-btn ds-btn-ghost text-danger p-1" type="button" onclick="this.closest('tr').remove()">
                    <i data-lucide="trash-2" style="width:14px;height:14px;"></i>
                </button>
            </td>
        `;
        tbody.appendChild(tr);
        if (window.lucide) lucide.createIcons();
    },

    // ── File Upload Helper ────────────────────────────────────────────────────────
    async handleFileUpload(secId) {
        const fileInput = document.getElementById(`${secId}_file`);
        const statusDiv = document.getElementById(`${secId}_status`);
        const hiddenInput = document.getElementById(secId);
        if (!fileInput || !fileInput.files.length) return;

        const file = fileInput.files[0];
        statusDiv.textContent = `Uploading: ${file.name}...`;

        const formData = new FormData();
        formData.append('file', file);

        try {
            const res = await api.upload(`/projects/upload`, formData);
            hiddenInput.value = res.url || '';
            statusDiv.textContent = `✓ Uploaded: ${file.name}`;
            QCMS.toast('File uploaded successfully.', 'success');
        } catch (e) {
            statusDiv.textContent = 'Upload failed.';
            QCMS.toast('Upload failed: ' + e.message, 'error');
        }
    },

    // ── Signature Handlers ────────────────────────────────────────────────────────
    handleSignatureToggle(secId) {
        const sigCheck = document.getElementById(secId);
        const user = JSON.parse(sessionStorage.getItem('user') || '{}');
        const signatureObj = {
            signed: sigCheck.checked,
            signed_by: sigCheck.checked ? (user.full_name || user.username || 'Reviewer') : '',
            signed_at: sigCheck.checked ? new Date().toISOString() : ''
        };
        this.updateSignatureUI(secId, signatureObj);
    },

    updateSignatureUI(secId, signatureObj) {
        const label = document.getElementById(`${secId}_status_label`);
        const time = document.getElementById(`${secId}_time_label`);
        
        if (signatureObj && signatureObj.signed) {
            if (label) label.innerHTML = `<span class="text-success">✓ Approved & Signed by ${esc(signatureObj.signed_by)}</span>`;
            if (time) time.textContent = `Signed: ${new Date(signatureObj.signed_at).toLocaleString()}`;
        } else {
            if (label) label.textContent = 'Pending Review Approval';
            if (time) time.textContent = 'Not signed yet';
        }
    },

    // ── Chart Update Logic ────────────────────────────────────────────────────────
    updateParetoChart(secId) {
        const rows = [...document.querySelectorAll(`#${secId}_table tbody tr`)].map(tr => ({
            category: tr.querySelector('.cell-cat')?.value || '',
            count: parseInt(tr.querySelector('.cell-count')?.value || 0)
        })).filter(r => r.category.trim()).sort((a,b) => b.count - a.count);

        const total = rows.reduce((sum, item) => sum + item.count, 0);
        let cumSum = 0;
        const cumulativePercentages = rows.map(x => {
            cumSum += x.count;
            return total > 0 ? ((cumSum / total) * 100).toFixed(1) : 0;
        });

        const labels = rows.map(x => x.category);
        const counts = rows.map(x => x.count);

        const canvas = document.getElementById(`${secId}_chart`);
        if (!canvas) return;
        const ctx = canvas.getContext('2d');

        if (this.charts[secId]) {
            this.charts[secId].destroy();
        }

        if (rows.length === 0) return;

        this.charts[secId] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Frequency',
                        data: counts,
                        backgroundColor: 'rgba(239, 68, 68, 0.6)',
                        borderColor: 'rgb(239, 68, 68)',
                        borderWidth: 1.5,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Cum %',
                        data: cumulativePercentages,
                        type: 'line',
                        borderColor: 'rgb(249, 115, 22)',
                        borderWidth: 2,
                        yAxisID: 'y1',
                        tension: 0.1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: true, position: 'left' },
                    y1: { min: 0, max: 100, position: 'right', grid: { drawOnChartArea: false } }
                }
            }
        });
    },

    updateHistogramChart(secId) {
        const rows = [...document.querySelectorAll(`#${secId}_table tbody tr`)].map(tr => ({
            interval: tr.querySelector('.cell-interval')?.value || '',
            before: parseFloat(tr.querySelector('.cell-before')?.value || 0),
            after: parseFloat(tr.querySelector('.cell-after')?.value || 0)
        })).filter(r => r.interval.trim());

        const labels = rows.map(r => r.interval);
        const dataBefore = rows.map(r => r.before);
        const dataAfter = rows.map(r => r.after);

        const canvas = document.getElementById(`${secId}_chart`);
        if (!canvas) return;
        const ctx = canvas.getContext('2d');

        if (this.charts[secId]) {
            this.charts[secId].destroy();
        }

        if (rows.length === 0) return;

        this.charts[secId] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Before',
                        data: dataBefore,
                        backgroundColor: 'rgba(239, 68, 68, 0.6)',
                        borderColor: 'rgb(239, 68, 68)',
                        borderWidth: 1
                    },
                    {
                        label: 'After',
                        data: dataAfter,
                        backgroundColor: 'rgba(34, 197, 94, 0.6)',
                        borderColor: 'rgb(34, 197, 94)',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
    },

    updateControlChart(secId) {
        const rows = [...document.querySelectorAll(`#${secId}_table tbody tr`)].map(tr => ({
            sample: tr.querySelector('.cell-sample')?.value || '',
            val: parseFloat(tr.querySelector('.cell-val')?.value || 0),
            cl: parseFloat(tr.querySelector('.cell-cl')?.value || 0),
            ucl: parseFloat(tr.querySelector('.cell-ucl')?.value || 0),
            lcl: parseFloat(tr.querySelector('.cell-lcl')?.value || 0)
        })).filter(r => r.sample.trim());

        const labels = rows.map(r => r.sample);
        const values = rows.map(r => r.val);
        const target = rows.map(r => r.cl);
        const ucl = rows.map(r => r.ucl);
        const lcl = rows.map(r => r.lcl);

        const canvas = document.getElementById(`${secId}_chart`);
        if (!canvas) return;
        const ctx = canvas.getContext('2d');

        if (this.charts[secId]) {
            this.charts[secId].destroy();
        }

        if (rows.length === 0) return;

        this.charts[secId] = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    { label: 'Sample Value', data: values, borderColor: '#3b82f6', borderWidth: 2, pointRadius: 4, fill: false },
                    { label: 'CL (Target)', data: target, borderColor: '#10b981', borderDash: [5, 5], fill: false, pointRadius: 0 },
                    { label: 'UCL', data: ucl, borderColor: '#ef4444', borderDash: [2, 2], fill: false, pointRadius: 0 },
                    { label: 'LCL', data: lcl, borderColor: '#ef4444', borderDash: [2, 2], fill: false, pointRadius: 0 }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
    },

    updateScatterChart(secId) {
        const rows = [...document.querySelectorAll(`#${secId}_table tbody tr`)].map(tr => ({
            x: parseFloat(tr.querySelector('.cell-x')?.value || 0),
            y: parseFloat(tr.querySelector('.cell-y')?.value || 0)
        }));

        const dataPoints = rows.map(r => ({ x: r.x, y: r.y }));

        const canvas = document.getElementById(`${secId}_chart`);
        if (!canvas) return;
        const ctx = canvas.getContext('2d');

        if (this.charts[secId]) {
            this.charts[secId].destroy();
        }

        this.charts[secId] = new Chart(ctx, {
            type: 'scatter',
            data: {
                datasets: [{
                    label: 'Scatter Data',
                    data: dataPoints,
                    backgroundColor: '#8b5cf6',
                    pointRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: { type: 'linear', position: 'bottom' }
                }
            }
        });
    },

    // ── Zoom Controls for Dynamic Fishbone Diagrams ──
    zoomFishbone(secId, delta) {
        if (!this.fishboneZoomLevels) this.fishboneZoomLevels = {};
        const currentZoom = this.fishboneZoomLevels[secId] || 1.0;
        let newZoom = currentZoom + delta;
        if (newZoom < 0.5) newZoom = 0.5;
        if (newZoom > 2.5) newZoom = 2.5;

        this.fishboneZoomLevels[secId] = newZoom;
        const container = document.getElementById(`${secId}_svgContainer`);
        const badge = document.getElementById(`${secId}_zoomBadge`);
        if (container) {
            container.style.transform = `scale(${newZoom})`;
        }
        if (badge) {
            badge.textContent = `${Math.round(newZoom * 100)}%`;
        }
    },

    resetFishboneZoom(secId) {
        if (!this.fishboneZoomLevels) this.fishboneZoomLevels = {};
        this.fishboneZoomLevels[secId] = 1.0;
        const container = document.getElementById(`${secId}_svgContainer`);
        const badge = document.getElementById(`${secId}_zoomBadge`);
        if (container) {
            container.style.transform = `scale(1.0)`;
        }
        if (badge) {
            badge.textContent = `100%`;
        }
    },

    // ── Fishbone Drawing Logic ───────────────────────────────────────────────────
    updateFishboneSVG(secId) {
        const rows = [...document.querySelectorAll(`#${secId}_table tbody tr`)].map(tr => ({
            category: tr.querySelector('.cell-cat')?.value || 'Man',
            cause: tr.querySelector('.cell-cause')?.value || '',
            sub_cause: tr.querySelector('.cell-subcause')?.value || ''
        })).filter(r => r.cause.trim());

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
            const boneG = document.getElementById(`${secId}_bone_${cat}`);
            if (!boneG) return;
            boneG.innerHTML = '';

            const catRows = rows.filter(r => r.category === cat && r.cause && r.cause.trim());
            if (catRows.length === 0) return;

            // Group sub-causes by Level 1 cause name
            const causeMap = new Map();
            catRows.forEach(r => {
                const key = r.cause.trim();
                if (!causeMap.has(key)) {
                    causeMap.set(key, []);
                }
                if (r.sub_cause && r.sub_cause.trim()) {
                    causeMap.get(key).push(r.sub_cause.trim());
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
                const causeLine = document.createElementNS('http://www.w3.org/2000/svg', 'line');
                causeLine.setAttribute('x1', lx1);
                causeLine.setAttribute('y1', ly);
                causeLine.setAttribute('x2', bx);
                causeLine.setAttribute('y2', ly);
                causeLine.setAttribute('stroke', '#334155');
                causeLine.setAttribute('stroke-width', '1.5');
                boneG.appendChild(causeLine);

                // Level 1 end node dot ●
                const dot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
                dot.setAttribute('cx', lx1);
                dot.setAttribute('cy', ly);
                dot.setAttribute('r', '3.5');
                dot.setAttribute('fill', '#1e293b');
                boneG.appendChild(dot);

                // Level 1 label: ABOVE for top bones, BELOW for bottom bones
                const label1 = level1Name.length > 18 ? level1Name.substring(0, 16) + '...' : level1Name;
                const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
                text.setAttribute('x', lx1 - 5);
                text.setAttribute('y', isTop ? (ly - 5) : (ly + 12));
                text.setAttribute('text-anchor', 'end');
                text.setAttribute('font-size', '8.5');
                text.setAttribute('font-weight', 'bold');
                text.setAttribute('fill', '#0f172a');
                text.textContent = label1;
                boneG.appendChild(text);
                
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

                        boneG.appendChild(subGrp);
                    });
                }
            });
        });

        // Update Mobile Accordion View for 6M Fishbone
        const accordionEl = document.getElementById(`${secId}_mobileAccordion`);
        if (accordionEl) {
            const catColors = {
                Man: '#3b82f6', Machine: '#ca8a04', Material: '#16a34a',
                Method: '#db2777', Measurement: '#ea580c', Environment: '#0891b2'
            };
            accordionEl.innerHTML = categories.map(cat => {
                const catRows = rows.filter(r => r.category === cat && r.cause && r.cause.trim());
                const color = catColors[cat] || '#2563eb';
                const causeMap = new Map();
                catRows.forEach(r => {
                    const key = r.cause.trim();
                    if (!causeMap.has(key)) causeMap.set(key, []);
                    if (r.sub_cause && r.sub_cause.trim()) causeMap.get(key).push(r.sub_cause.trim());
                });

                let itemsHtml = '';
                if (causeMap.size === 0) {
                    itemsHtml = `<p class="text-xs text-muted mb-0 italic">No causes recorded in this category.</p>`;
                } else {
                    itemsHtml = Array.from(causeMap.entries()).map(([c, subs]) => `
                        <div class="fishbone-cause-item">
                            <div class="fishbone-cause-title">${DynamicRenderer.escapeHtml(c)}</div>
                            ${subs.length > 0 ? `
                                <div>
                                    ${subs.map(s => `<span class="fishbone-subcause-tag">↳ ${DynamicRenderer.escapeHtml(s)}</span>`).join('')}
                                </div>
                            ` : ''}
                        </div>
                    `).join('');
                }

                return `
                    <div class="fishbone-cat-card">
                        <div class="fishbone-cat-header" onclick="const b = this.nextElementSibling; b.classList.toggle('d-none');">
                            <div class="d-flex align-items-center gap-2">
                                <span class="fishbone-cat-badge" style="background:${color}">${cat}</span>
                                <span class="text-xs text-muted">(${causeMap.size} causes)</span>
                            </div>
                            <i data-lucide="chevron-down" style="width:16px;height:16px;color:var(--ds-text-secondary);"></i>
                        </div>
                        <div class="fishbone-cat-body ${causeMap.size === 0 ? 'd-none' : ''}">
                            ${itemsHtml}
                        </div>
                    </div>
                `;
            }).join('');
            if (window.lucide) lucide.createIcons();
        }
    },

    async populateMappedSelects(projectId) {
        if (!projectId) return;
        const selectEls = document.querySelectorAll('select[data-source]');
        if (selectEls.length === 0) return;

        let projectData = {};
        try {
            if (typeof api !== 'undefined') {
                const res = await api.get(`/projects/${projectId}`);
                if (res && res.project) projectData = res.project;
            }
        } catch (_) {}

        selectEls.forEach(sel => {
            const sourceKey = sel.dataset.source;
            if (!sourceKey || sourceKey === 'custom') return;

            let items = [];
            switch (sourceKey) {
                case 'stage1_team_members':
                    items = (projectData.team_members || []).map(m => m.name || m.user_name || m);
                    break;
                case 'stage1_problem_background':
                    if (projectData.theme) items.push(projectData.theme);
                    if (projectData.problem_statement) items.push(projectData.problem_statement);
                    break;
                case 'stage2_observations':
                    items = (projectData.stage2_data || {}).observations || [];
                    break;
                case 'stage3_brainstormed_causes':
                    items = (projectData.stage3_data || {}).causes || [];
                    break;
                case 'stage4_verified_root_causes':
                    items = (projectData.stage4_data || {}).root_causes || [];
                    break;
                case 'stage5_chosen_solutions':
                    items = (projectData.stage5_data || {}).solutions || [];
                    break;
                case 'stage6_countermeasures':
                    items = (projectData.stage6_data || {}).countermeasures || [];
                    break;
                case 'stage7_kpi_metrics':
                    items = (projectData.stage7_data || {}).kpis || [];
                    break;
                case 'stage8_standardized_sops':
                    items = (projectData.stage8_data || {}).sops || [];
                    break;
                case 'org_departments':
                    items = (projectData.departments || []).map(d => d.name);
                    break;
                case 'org_users':
                    items = (projectData.users || []).map(u => u.name || u.email);
                    break;
                case 'categories':
                case 'sop_categories':
                case 'org_categories':
                    if (window.QCMS && typeof window.QCMS.loadCategories === 'function') {
                        // Will be populated asynchronously or from cache
                        window.QCMS.loadCategories().then(cats => {
                            if (cats && cats.length > 0) {
                                const firstOpt = sel.firstElementChild ? sel.firstElementChild.outerHTML : '<option value="">-- Select Category --</option>';
                                sel.innerHTML = firstOpt + cats.map(it => `<option value="${QCMS.escapeHtml(it)}">${QCMS.escapeHtml(it)}</option>`).join('');
                            }
                        });
                    }
                    break;
            }

            if (items.length > 0) {
                const firstOpt = sel.firstElementChild ? sel.firstElementChild.outerHTML : '<option value="">-- Select option --</option>';
                sel.innerHTML = firstOpt + items.map(it => `<option value="${this.escapeHtml(it)}">${this.escapeHtml(it)}</option>`).join('');
            }
        });
    }
};

window.DynamicRenderer = DynamicRenderer;
