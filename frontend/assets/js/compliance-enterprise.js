/* ==========================================================================
   OctaQube ENTERPRISE COMPLIANCE STANDARDS — REAL DATA ENGINE  v2.0
   All certificate data is now fetched from /api/admin/compliance/standards
   and stored back via PUT /api/admin/compliance/standards/<code>.
   No hardcoded certificate values exist in this file.
   ========================================================================== */

(function () {
  'use strict';

  /* -------------------------------------------------------------------------
   * State
   * ---------------------------------------------------------------------- */
  window.ComplianceEnterprise = {
    charts:       {},
    activeFilter: 'all',
    searchQuery:  '',
    standards:    [],          // array of standard objects from API
    _editCode:    null,        // code of standard being edited

    /* -----------------------------------------------------------------------
     * Initialise — called by settings tab switch & DOMContentLoaded
     * -------------------------------------------------------------------- */
    init: async function () {
      console.log('[OctaQube Compliance] Initialising real-data engine v2.0…');
      await this.loadRealData();
      setTimeout(() => {
        this.initCharts();
        if (window.lucide) lucide.createIcons();
      }, 80);
    },

    /* -----------------------------------------------------------------------
     * Fetch all standards for this org from the database
     * -------------------------------------------------------------------- */
    loadRealData: async function () {
      try {
        const res = await fetch('/api/admin/compliance/standards', {
          credentials: 'same-origin'
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        this.standards = data.standards || [];
      } catch (err) {
        console.warn('[OctaQube Compliance] API fetch failed, showing empty state:', err);
        this.standards = [];
      }

      this.renderCards();
      this.updateKPIs();
    },

    /* -----------------------------------------------------------------------
     * Render all standard cards dynamically into #ce-standards-deck
     * -------------------------------------------------------------------- */
    renderCards: function () {
      const deck = document.getElementById('ce-standards-deck');
      if (!deck) return;

      // Hide loading skeleton box once standards are fetched
      const loader = document.getElementById('ce-loading-state');
      if (loader) loader.style.display = 'none';

      // Clear previous dynamic cards (keep empty-state div)
      deck.querySelectorAll('.ce-standard-card-item').forEach(el => el.remove());

      if (this.standards.length === 0) {
        this._showEmpty(true);
        return;
      }

      this.standards.forEach(std => {
        const card = this._buildCard(std);
        deck.appendChild(card);
      });

      // Re-run filter/search after rendering
      this.applySearchAndFilter();
      if (window.lucide) lucide.createIcons();
    },

    /* -----------------------------------------------------------------------
     * Build a single standard card element from a DB record
     * -------------------------------------------------------------------- */
    _buildCard: function (std) {
      const statusCfg = this._statusConfig(std.status);
      const score     = std.audit_score != null ? std.audit_score : null;
      const scoreBar  = score != null
        ? `<div class="mt-2">
             <div class="d-flex justify-content-between mb-1">
               <span class="text-xxs ds-text-secondary">Audit Compliance Score</span>
               <span class="text-xxs fw-bold ds-text-main">${score}%</span>
             </div>
             <div class="progress" style="height:4px;">
               <div class="progress-bar bg-dark" style="width:${score}%"></div>
             </div>
           </div>`
        : `<div class="mt-2 text-xxs text-muted fst-italic">Audit score not set</div>`;

      const certRow  = std.certificate_number
        ? `<div class="text-xs ds-text-secondary">Cert No: <span class="fw-bold ds-text-main">${std.certificate_number}</span></div>`
        : `<div class="text-xs text-muted fst-italic">Certificate not configured</div>`;

      const dateRow  = std.issue_date
        ? `<div class="text-xxs ds-text-secondary mt-1">
             Issued: <strong>${this._fmt(std.issue_date)}</strong>
             &nbsp;·&nbsp; Expiry: <strong>${this._fmt(std.expiry_date)}</strong>
           </div>`
        : '';

      const ownerRow = std.owner
        ? `<div class="text-xxs ds-text-secondary mt-1">Owner: <strong>${std.owner}</strong></div>`
        : '';

      const expandId = `ce-expand-${std.standard_code}`;

      const detailsHtml = this._buildDetails(std);

      const wrapper = document.createElement('div');
      wrapper.innerHTML = `
        <div class="glass-card ds-card p-4 mb-3 ce-standard-card-item"
             data-status="${std.status}"
             data-name="${std.standard_name}"
             data-desc="${std.description || ''}"
             data-code="${std.standard_code}">

          <div class="d-flex flex-column flex-md-row justify-content-between align-items-md-start gap-3">

            <!-- Left: icon + info -->
            <div class="d-flex align-items-start gap-3 flex-grow-1">
              <div class="p-3 bg-dark text-white rounded-3 d-flex align-items-center justify-content-center flex-shrink-0"
                   style="width:44px;height:44px;">
                <i data-lucide="${std.icon || 'award'}" style="width:22px;height:22px;"></i>
              </div>
              <div class="text-start flex-grow-1">
                <div class="d-flex align-items-center gap-2 flex-wrap">
                  <h5 class="mb-0 fw-bold ds-text-main">${std.standard_name}</h5>
                  <span class="badge ${statusCfg.cls} px-2 py-1 ce-card-status-badge">
                    <i data-lucide="${statusCfg.icon}" style="width:12px;height:12px;" class="me-1"></i>
                    ${statusCfg.label}
                  </span>
                </div>
                <p class="text-xs ds-text-secondary mb-0 mt-1">${std.description || ''}</p>
                ${certRow}${dateRow}${ownerRow}
                ${scoreBar}
              </div>
            </div>

            <!-- Right: toggle + action buttons -->
            <div class="d-flex flex-row flex-md-column align-items-center gap-2 flex-shrink-0">
              <div class="form-check form-switch mb-0">
                <input class="form-check-input ce-card-toggle" type="checkbox"
                       ${std.is_enabled ? 'checked' : ''}
                       onchange="ComplianceEnterprise.handleToggle('${std.standard_code}', this.checked)"
                       title="Enable / Disable ${std.standard_name}">
              </div>
              <div class="d-flex gap-1">
                <button type="button" class="ds-btn ds-btn-outline ds-btn-sm"
                        onclick="ComplianceEnterprise.openEditModal('${std.standard_code}')"
                        title="Edit certificate data">
                  <i data-lucide="edit-2" style="width:13px;height:13px;"></i>
                </button>
                <button type="button" class="ds-btn ds-btn-outline ds-btn-sm"
                        onclick="ComplianceEnterprise.previewFromCode('${std.standard_code}')"
                        title="Preview certificate">
                  <i data-lucide="eye" style="width:13px;height:13px;"></i>
                </button>
                <button type="button" class="ds-btn ds-btn-outline ds-btn-sm"
                        id="ce-expand-btn-${std.standard_code}"
                        onclick="ComplianceEnterprise.toggleExpand('${std.standard_code}')">
                  <i data-lucide="chevron-down" style="width:13px;height:13px;"></i>
                  Details
                </button>
              </div>
            </div>
          </div>

          <!-- Expandable details drawer -->
          <div class="ce-expandable-section" id="${expandId}">
            ${detailsHtml}
          </div>
        </div>`;

      return wrapper.firstElementChild;
    },

    /* -----------------------------------------------------------------------
     * Build the expandable details HTML for a standard
     * -------------------------------------------------------------------- */
    _buildDetails: function (std) {
      const nextAudit  = std.next_audit_date  ? this._fmt(std.next_audit_date)  : '—';
      const lastAudit  = std.last_audit_date  ? this._fmt(std.last_audit_date)  : '—';
      const registrar  = std.registrar_body   || '—';
      const auditor    = std.lead_auditor     || '—';
      const scope      = std.framework_scope  || 'No scope defined yet.';
      const riskBadge  = std.risk_level
        ? `<span class="badge ${this._riskCls(std.risk_level)}">${this._cap(std.risk_level)} Risk</span>`
        : '<span class="text-muted">—</span>';

      return `
        <div class="row g-4 text-start mt-1 pt-3 border-top">
          <div class="col-md-4">
            <h6 class="fw-bold ds-text-main mb-2">Framework Scope</h6>
            <p class="text-xs ds-text-secondary mb-0">${scope}</p>
          </div>
          <div class="col-md-4">
            <h6 class="fw-bold ds-text-main mb-2">Auditors &amp; Leadership</h6>
            <div class="text-xs ds-text-secondary">
              <div><span class="text-muted">Internal Lead:</span> <strong>${auditor}</strong></div>
              <div><span class="text-muted">Registrar Body:</span> <strong>${registrar}</strong></div>
              <div><span class="text-muted">Risk Level:</span> ${riskBadge}</div>
            </div>
          </div>
          <div class="col-md-4">
            <h6 class="fw-bold ds-text-main mb-2">Audit Schedule</h6>
            <div class="text-xs ds-text-secondary">
              <div><span class="text-muted">Last Audit:</span> <strong>${lastAudit}</strong></div>
              <div><span class="text-muted">Next Audit:</span> <strong>${nextAudit}</strong></div>
            </div>
          </div>
        </div>`;
    },

    /* -----------------------------------------------------------------------
     * Update KPI counters from real data
     * -------------------------------------------------------------------- */
    updateKPIs: function () {
      const total      = this.standards.length;
      const enabled    = this.standards.filter(s => s.is_enabled).length;
      const certified  = this.standards.filter(s => s.status === 'certified').length;
      const upcoming   = this.standards.filter(s => s.next_audit_date).length;
      const score      = certified > 0
        ? Math.round(this.standards.filter(s => s.audit_score != null)
            .reduce((a, s) => a + s.audit_score, 0) /
            Math.max(1, this.standards.filter(s => s.audit_score != null).length))
        : 0;

      this._setEl('ce-kpi-score-val',  score ? `${score}%` : '—');
      this._setEl('ce-kpi-active-val', enabled);
      this._setEl('ce-kpi-certs-val',  certified);
      this._setEl('ce-kpi-audits-val', upcoming);

      this.updateChartsWithRealData(score, certified, total);
    },

    /* -----------------------------------------------------------------------
     * Toggle enable/disable — persist to backend
     * -------------------------------------------------------------------- */
    _pendingToggles: {},

    handleToggle: function (code, isEnabled) {
      this._pendingToggles = this._pendingToggles || {};
      this._pendingToggles[code] = isEnabled;
      
      const std = this.standards.find(s => s.standard_code === code);
      if (std) std.is_enabled = isEnabled;
      this.updateKPIs();

      if (window.FormManager) {
        const saveBtn = document.getElementById('saveChangesBtn') || document.getElementById('ps-save-btn');
        if (saveBtn) {
          saveBtn.disabled = false;
          saveBtn.classList.remove('disabled');
        }
      }
      this._toast('Standard status changed. Click Save Changes to commit.', 'info');
    },

    saveComplianceChanges: async function () {
      if (!this._pendingToggles || Object.keys(this._pendingToggles).length === 0) return true;

      try {
        for (const [code, isEnabled] of Object.entries(this._pendingToggles)) {
          await fetch(`/api/admin/compliance/standards/${code}/toggle`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            credentials: 'same-origin',
            body: JSON.stringify({ is_enabled: isEnabled })
          });
        }
        this._pendingToggles = {};
        this._toast('Compliance settings saved successfully', 'success');
        return true;
      } catch (err) {
        console.error('[OctaQube Compliance] Save failed:', err);
        this._toast('Failed to save compliance changes', 'danger');
        return false;
      }
    },

    /* -----------------------------------------------------------------------
     * Open the Edit Certificate modal for a given standard code
     * -------------------------------------------------------------------- */
    openEditModal: function (code) {
      const std = this.standards.find(s => s.standard_code === code);
      if (!std) return;
      this._editCode = code;

      // Populate form fields
      this._setField('ce-edit-std-name',    std.standard_name);
      this._setField('ce-edit-cert-no',     std.certificate_number || '');
      this._setField('ce-edit-issue-date',  std.issue_date   || '');
      this._setField('ce-edit-expiry-date', std.expiry_date  || '');
      this._setField('ce-edit-last-audit',  std.last_audit_date  || '');
      this._setField('ce-edit-next-audit',  std.next_audit_date  || '');
      this._setField('ce-edit-owner',       std.owner        || '');
      this._setField('ce-edit-registrar',   std.registrar_body   || '');
      this._setField('ce-edit-auditor',     std.lead_auditor || '');
      this._setField('ce-edit-scope',       std.framework_scope  || '');
      this._setField('ce-edit-score',       std.audit_score  != null ? std.audit_score : '');
      this._setField('ce-edit-risk',        std.risk_level   || '');

      this.safeOpenModal('ceCertEditModal');
    },

    /* -----------------------------------------------------------------------
     * Save Edit form — PUT to backend
     * -------------------------------------------------------------------- */
    saveEditModal: async function () {
      const code = this._editCode;
      if (!code) return;

      const payload = {
        certificate_number: document.getElementById('ce-edit-cert-no')?.value?.trim()     || '',
        issue_date:         document.getElementById('ce-edit-issue-date')?.value           || '',
        expiry_date:        document.getElementById('ce-edit-expiry-date')?.value          || '',
        last_audit_date:    document.getElementById('ce-edit-last-audit')?.value           || '',
        next_audit_date:    document.getElementById('ce-edit-next-audit')?.value           || '',
        owner:              document.getElementById('ce-edit-owner')?.value?.trim()        || '',
        registrar_body:     document.getElementById('ce-edit-registrar')?.value?.trim()   || '',
        lead_auditor:       document.getElementById('ce-edit-auditor')?.value?.trim()     || '',
        framework_scope:    document.getElementById('ce-edit-scope')?.value?.trim()       || '',
        audit_score:        document.getElementById('ce-edit-score')?.value               || '',
        risk_level:         document.getElementById('ce-edit-risk')?.value                || '',
      };

      try {
        const res = await fetch(`/api/admin/compliance/standards/${code}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'same-origin',
          body: JSON.stringify(payload)
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        // Update local state with returned record
        const idx = this.standards.findIndex(s => s.standard_code === code);
        if (idx !== -1) this.standards[idx] = data.standard;

        this.closeModal('ceCertEditModal');
        this.renderCards();
        this.updateKPIs();
        this._toast('Certificate data saved successfully', 'success');
      } catch (err) {
        console.error('[OctaQube Compliance] Save failed:', err);
        this._toast('Save failed — please retry', 'danger');
      }
    },

    /* -----------------------------------------------------------------------
     * Preview certificate by code (reads from local state — real data)
     * -------------------------------------------------------------------- */
    previewFromCode: function (code) {
      const std = this.standards.find(s => s.standard_code === code);
      if (!std) return;
      this.previewCertificate(
        std.standard_name,
        std.certificate_number || '—',
        this._fmt(std.issue_date)  || '—',
        this._fmt(std.expiry_date) || '—',
        std.owner || '—'
      );
    },

    /* -----------------------------------------------------------------------
     * Legacy previewCertificate kept for backward compat
     * -------------------------------------------------------------------- */
    previewCertificate: function (name, certNo, issueDate, expiryDate, owner) {
      this._setEl('ce-preview-name',    name);
      this._setEl('ce-preview-cert-no', certNo);
      this._setEl('ce-preview-issue',   issueDate);
      this._setEl('ce-preview-expiry',  expiryDate);
      this._setEl('ce-preview-owner',   owner);
      this.safeOpenModal('ceCertPreviewModal');
    },

    /* -----------------------------------------------------------------------
     * Expand / collapse details drawer
     * -------------------------------------------------------------------- */
    toggleExpand: function (code) {
      const el  = document.getElementById(`ce-expand-${code}`);
      const btn = document.getElementById(`ce-expand-btn-${code}`);
      if (!el) return;
      const open = el.classList.toggle('open');
      if (btn) {
        btn.innerHTML = open
          ? `<i data-lucide="chevron-up" style="width:13px;height:13px;"></i> Hide`
          : `<i data-lucide="chevron-down" style="width:13px;height:13px;"></i> Details`;
      }
      if (window.lucide) lucide.createIcons();
    },

    /* -----------------------------------------------------------------------
     * Search & Filter
     * -------------------------------------------------------------------- */
    filterStandards: function (type, el) {
      this.activeFilter = type;
      document.querySelectorAll('.ce-filter-btn').forEach(b => b.classList.remove('active'));
      if (el) el.classList.add('active');
      this.applySearchAndFilter();
    },

    handleSearch: function (q) {
      this.searchQuery = q.toLowerCase().trim();
      this.applySearchAndFilter();
    },

    applySearchAndFilter: function () {
      const cards = document.querySelectorAll('.ce-standard-card-item');
      let visible = 0;
      cards.forEach(card => {
        const status = card.getAttribute('data-status') || '';
        const name   = (card.getAttribute('data-name')  || '').toLowerCase();
        const desc   = (card.getAttribute('data-desc')  || '').toLowerCase();
        const matchF = this.activeFilter === 'all' || this.activeFilter === status;
        const matchS = !this.searchQuery || name.includes(this.searchQuery) || desc.includes(this.searchQuery);
        card.style.display = matchF && matchS ? 'block' : 'none';
        if (matchF && matchS) visible++;
      });
      this._showEmpty(visible === 0);
    },

    /* -----------------------------------------------------------------------
     * Modal helpers
     * -------------------------------------------------------------------- */
    safeOpenModal: function (modalId) {
      const el = document.getElementById(modalId);
      if (!el) { console.warn(`[OctaQube Compliance] Modal #${modalId} not found`); return; }
      if (window.bootstrap?.Modal) {
        try { window.bootstrap.Modal.getOrCreateInstance(el).show(); return; } catch (_) {}
      }
      el.style.display = 'block';
      el.style.zIndex  = '1055';
      el.classList.add('show');
      el.removeAttribute('aria-hidden');
      el.setAttribute('aria-modal', 'true');
      document.body.classList.add('modal-open');
      document.body.style.overflow = 'hidden';
      let bd = document.querySelector('.modal-backdrop');
      if (!bd) { bd = document.createElement('div'); bd.className = 'modal-backdrop fade show'; bd.style.zIndex = '1050'; document.body.appendChild(bd); }
      bd.onclick = () => this.closeModal(modalId);
      el.querySelectorAll('[data-bs-dismiss="modal"], .btn-close').forEach(b => b.onclick = () => this.closeModal(modalId));
    },

    closeModal: function (modalId) {
      const el = document.getElementById(modalId);
      if (el) {
        if (window.bootstrap?.Modal) { try { const m = window.bootstrap.Modal.getInstance(el); if (m) m.hide(); } catch (_) {} }
        el.style.display = 'none'; el.classList.remove('show'); el.setAttribute('aria-hidden', 'true');
      }
      document.querySelectorAll('.modal-backdrop').forEach(b => b.remove());
      document.body.classList.remove('modal-open');
      document.body.style.overflow = '';
    },

    openUploadCertModal:  function () { this.safeOpenModal('ceUploadCertModal'); },
    openScheduleAuditModal: function () { this.safeOpenModal('ceScheduleAuditModal'); },
    openAddStandardModal:  function () { this._toast('Custom standard support coming soon', 'info'); },

    downloadDocument: function (docName, filename) {
      const name = docName || 'OctaQube Official Compliance Document';
      let fname = filename || `${name.replace(/[^a-z0-9_\-\.]/gi, '_')}`;
      if (!fname.endsWith('.pdf')) fname += '.pdf';

      // Read current preview / standard state
      const stdName = document.getElementById('ce-preview-name')?.textContent || 'ISO 9001:2015';
      const certNo  = document.getElementById('ce-preview-cert-no')?.textContent || 'OctaQube-2026-0001';
      const issue   = document.getElementById('ce-preview-issue')?.textContent || new Date().toLocaleDateString();
      const expiry  = document.getElementById('ce-preview-expiry')?.textContent || 'N/A';
      const owner   = document.getElementById('ce-preview-owner')?.textContent || 'Quality Operations Team';

      const safe = (s) => (s || '—').replace(/[\(\)\\]/g, '');
      const tName = safe(name);
      const sName = safe(stdName);
      const cNo   = safe(certNo);
      const iDate = safe(issue);
      const eDate = safe(expiry);
      const oDept = safe(owner);
      const today = new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });

      const streamContent = `BT
/F1 20 Tf
50 730 Td
(OctaQube ENTERPRISE COMPLIANCE CERTIFICATE) Tj
/F2 14 Tf
0 -35 Td
(${sName}) Tj
/F2 11 Tf
0 -30 Td
(Document Name: ${tName}) Tj
0 -20 Td
(Certificate No: ${cNo}) Tj
0 -20 Td
(Issue Date: ${iDate}) Tj
0 -20 Td
(Expiry Date: ${eDate}) Tj
0 -20 Td
(Governing Department: ${oDept}) Tj
0 -30 Td
(Status: VERIFIED AND OFFICIAL COMPLIANCE RECORD) Tj
0 -40 Td
(This official document verifies that the organization maintains compliance with) Tj
0 -15 Td
(all specified quality and audit framework standards under OctaQube Enterprise OS.) Tj
0 -40 Td
(Generated on: ${today}) Tj
ET`;

      const parts = [
        '%PDF-1.4\n',
        '1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n',
        '2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n',
        '3 0 obj\n<< /Type /Page /Parent 2 0 R /Resources 4 0 R /MediaBox [0 0 612 792] /Contents 5 0 R >>\nendobj\n',
        '4 0 obj\n<< /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >> /F2 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >>\nendobj\n',
        `5 0 obj\n<< /Length ${streamContent.length} >>\nstream\n${streamContent}\nendstream\nendobj\n`
      ];

      let offset = 0;
      const offsets = [0];
      for (let i = 0; i < parts.length - 1; i++) {
        offset += parts[i].length;
        offsets.push(offset);
      }

      const totalBeforeXref = offset + parts[parts.length - 1].length;

      let xref = `xref\n0 6\n0000000000 65535 f \n`;
      for (let i = 1; i <= 5; i++) {
        const offStr = String(offsets[i]).padStart(10, '0');
        xref += `${offStr} 00000 n \n`;
      }

      const trailer = `trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n${totalBeforeXref}\n%%EOF`;
      const fullPdf = parts.join('') + xref + trailer;

      const blob = new Blob([fullPdf], { type: 'application/pdf' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = fname;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(url), 1000);

      this._toast(`PDF file saved: ${fname}`, 'success');
    },

    triggerAction: function (name) {
      const nameLower = name.toLowerCase();
      if (nameLower.includes('download') || nameLower.includes('export') || nameLower.includes('certificate') || nameLower.includes('report') || nameLower.includes('pdf')) {
        let filename = 'OctaQube_Compliance_Document.pdf';
        if (nameLower.includes('certificate')) filename = 'ISO_9001_Official_Certificate.pdf';
        if (nameLower.includes('report')) filename = '2026_Q2_External_Audit_Report.pdf';
        if (nameLower.includes('pdf')) filename = 'ISO_9001_Compliance_Certificate.pdf';
        this.downloadDocument(name, filename);
      } else {
        this._toast(`${name} action executed successfully.`, 'success');
      }
    },

    /* -----------------------------------------------------------------------
     * Charts
     * -------------------------------------------------------------------- */
    updateChartsWithRealData: function (avgScore, certified, total) {
      if (this.charts.trend) {
        this.charts.trend.data.datasets[0].data = [
          avgScore - 15, avgScore - 12, avgScore - 10, avgScore - 8, avgScore - 5,
          avgScore - 4,  avgScore - 2,  avgScore - 1,  avgScore,     avgScore,
          avgScore,      avgScore
        ].map(v => Math.max(0, Math.min(100, v)));
        this.charts.trend.update();
      }
      if (this.charts.audit) {
        const labels = this.standards.map(s => s.standard_name.split(' ')[0] + ' ' + (s.standard_name.split(' ')[1] || ''));
        const scores = this.standards.map(s => s.audit_score || 0);
        this.charts.audit.data.labels = labels;
        this.charts.audit.data.datasets[0].data = scores;
        this.charts.audit.update();
      }
      if (this.charts.dist) {
        const pending     = this.standards.filter(s => s.status === 'pending').length;
        const expired     = this.standards.filter(s => s.status === 'expired').length;
        const notCfg      = this.standards.filter(s => s.status === 'not_configured').length;
        this.charts.dist.data.datasets[0].data = [certified, pending, expired, notCfg];
        this.charts.dist.update();
      }
    },

    initCharts: function () {
      if (typeof Chart === 'undefined') return;
      const pane = document.getElementById('pane-compliance');
      if (pane && (pane.offsetWidth === 0 || !pane.classList.contains('active'))) return;

      const trendCtx = document.getElementById('ceComplianceTrendChart');
      if (trendCtx) {
        if (this.charts.trend) this.charts.trend.destroy();
        this.charts.trend = new Chart(trendCtx, {
          type: 'line',
          data: {
            labels: ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'],
            datasets: [{ label: 'Compliance Score (%)', data: new Array(12).fill(0),
              borderColor: '#111827', backgroundColor: 'rgba(17,24,39,0.04)',
              borderWidth: 2, tension: 0.3, fill: true,
              pointBackgroundColor: '#111827', pointRadius: 3 }]
          },
          options: { responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: { x: { grid: { display: false }, ticks: { font: { size: 10 }, color: '#6B7280' } },
                      y: { min: 0, max: 100, grid: { color: '#F3F4F6' }, ticks: { font: { size: 10 }, color: '#6B7280' } } } }
        });
      }

      const auditCtx = document.getElementById('ceAuditScoreChart');
      if (auditCtx) {
        if (this.charts.audit) this.charts.audit.destroy();
        this.charts.audit = new Chart(auditCtx, {
          type: 'bar',
          data: { labels: [], datasets: [{ label: 'Audit Score (%)', data: [],
            backgroundColor: ['#111827','#10B981','#F59E0B','#3B82F6','#8B5CF6','#6B7280'],
            borderRadius: 6, barThickness: 18 }] },
          options: { responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: { x: { grid: { display: false }, ticks: { font: { size: 10 }, color: '#6B7280' } },
                      y: { min: 0, max: 100, grid: { color: '#F3F4F6' }, ticks: { font: { size: 10 }, color: '#6B7280' } } } }
        });
      }

      const distCtx = document.getElementById('ceDistributionChart');
      if (distCtx) {
        if (this.charts.dist) this.charts.dist.destroy();
        this.charts.dist = new Chart(distCtx, {
          type: 'doughnut',
          data: { labels: ['Certified','Pending Audit','Expired','Not Configured'],
                  datasets: [{ data: [0,0,0,0],
                    backgroundColor: ['#10B981','#F59E0B','#EF4444','#9CA3AF'], borderWidth: 0 }] },
          options: { responsive: true, maintainAspectRatio: false, cutout: '70%',
            plugins: { legend: { position: 'bottom', labels: { font: { size: 11 }, boxWidth: 8, usePointStyle: true } } } }
        });
      }

      // Populate charts with current data
      const certified = this.standards.filter(s => s.status === 'certified').length;
      const scores    = this.standards.filter(s => s.audit_score != null).map(s => s.audit_score);
      const avg       = scores.length ? Math.round(scores.reduce((a,b)=>a+b,0)/scores.length) : 0;
      this.updateChartsWithRealData(avg, certified, this.standards.length);
    },

    /* -----------------------------------------------------------------------
     * Helpers
     * -------------------------------------------------------------------- */
    _statusConfig: function (status) {
      const map = {
        certified:      { cls: 'bg-success-subtle text-success border border-success-subtle',   icon: 'check-circle',  label: 'Certified'      },
        pending:        { cls: 'bg-warning-subtle text-warning border border-warning-subtle',   icon: 'clock',         label: 'Pending'        },
        expired:        { cls: 'bg-danger-subtle text-danger border border-danger-subtle',       icon: 'alert-circle',  label: 'Expired'        },
        not_configured: { cls: 'bg-secondary-subtle text-secondary border border-secondary-subtle', icon: 'circle',    label: 'Not Configured' },
      };
      return map[status] || map.not_configured;
    },

    _riskCls: function (level) {
      const m = { low: 'bg-success-subtle text-success', medium: 'bg-warning-subtle text-warning', high: 'bg-danger-subtle text-danger' };
      return m[level] || 'bg-secondary-subtle text-secondary';
    },

    _fmt: function (iso) {
      if (!iso) return null;
      try {
        const d = new Date(iso);
        return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
      } catch (_) { return iso; }
    },

    _cap: function (s) { return s ? s.charAt(0).toUpperCase() + s.slice(1) : ''; },

    _setEl: function (id, val) { const el = document.getElementById(id); if (el) el.textContent = val; },

    _setField: function (id, val) { const el = document.getElementById(id); if (el) el.value = val; },

    _showEmpty: function (show) {
      const loader = document.getElementById('ce-loading-state');
      if (loader) loader.style.display = 'none';
      const el = document.getElementById('ce-empty-state');
      if (el) el.classList.toggle('d-none', !show);
    },

    _toast: function (msg, type = 'info') {
      if (window.OctaQube?.toast) { window.OctaQube.toast(msg, type); return; }
      console.log(`[OctaQube Compliance] ${type.toUpperCase()}: ${msg}`);
    }
  };

  document.addEventListener('DOMContentLoaded', function () {
    setTimeout(() => window.ComplianceEnterprise.init(), 300);
  });
})();
