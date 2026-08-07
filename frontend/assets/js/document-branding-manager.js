/**
 * QCMS Enterprise OS — Centralized Document Identity, Branding & Usage Mapping Explorer Manager
 */

const DocIdentityManager = {
    data: null,

    async init() {
        try {
            const token = localStorage.getItem('token') || localStorage.getItem('access_token');
            const res = await fetch('/api/document-identity/all', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const result = await res.json();

            if (result.status === 'success') {
                this.data = result;
                this.populateFormFields();
                this.loadTemplateForm();
            }
        } catch (err) {
            console.error("Failed to load document identity settings:", err);
        }
    },

    populateFormFields() {
        if (!this.data || !this.data.branding_context) return;
        const ctx = this.data.branding_context;

        // Platform Identity
        this.setValue('di-software-name', ctx.software_name);
        this.setValue('di-software-short', ctx.software_short_name);
        this.setValue('di-software-display', ctx.software_display_name);
        this.setValue('di-platform-title', ctx.platform_title);
        this.setValue('di-platform-subtitle', ctx.platform_subtitle);
        this.setValue('di-version', ctx.version);
        this.setValue('di-edition', ctx.edition);
        this.setValue('di-currency', ctx.default_currency);
        this.setValue('di-website', ctx.website);
        this.setValue('di-support-portal', ctx.support_portal);
        this.setValue('di-footer-copyright', ctx.footer_copyright);

        // Company Information
        this.setValue('di-legal-name', ctx.legal_company_name);
        this.setValue('di-trading-name', ctx.trading_name);
        this.setValue('di-gstin', ctx.gstin);
        this.setValue('di-pan', ctx.pan);
        this.setValue('di-cin', ctx.cin);
        this.setValue('di-iso', ctx.iso_certifications);

        // Addresses
        this.setValue('di-reg-office', ctx.registered_office);
        this.setValue('di-corp-office', ctx.corporate_office);
        this.setValue('di-country', 'India');
        this.setValue('di-state', 'Maharashtra');
        this.setValue('di-city-pin', 'Mumbai 400051');

        // Contacts
        this.setValue('di-email-general', ctx.general_email);
        this.setValue('di-email-support', ctx.support_email);
        this.setValue('di-email-billing', ctx.billing_email);
        this.setValue('di-phone-general', ctx.general_phone);
        this.setValue('di-phone-emergency', '+91 98765 43210');
    },

    setValue(id, val) {
        const el = document.getElementById(id);
        if (el) el.value = val || '';
    },

    loadTemplateForm() {
        if (!this.data || !this.data.templates) return;
        const selector = document.getElementById('di-template-selector');
        if (!selector) return;
        const key = selector.value;
        const tmpl = this.data.templates[key] || {};

        this.setValue('di-tmpl-title', tmpl.header_title || '');
        this.setValue('di-tmpl-subtitle', tmpl.subtitle || '');
        this.setValue('di-tmpl-footer', tmpl.footer_text || tmpl.terms_and_conditions || '');
        this.setValue('di-tmpl-watermark', tmpl.watermark_text || 'CONFIDENTIAL');
        this.setValue('di-tmpl-confidential', tmpl.confidential_text || 'STRICTLY CONFIDENTIAL');
    },

    async saveSection(section) {
        let payload = {};

        if (section === 'platform') {
            payload = {
                software_name: document.getElementById('di-software-name')?.value,
                software_short_name: document.getElementById('di-software-short')?.value,
                software_display_name: document.getElementById('di-software-display')?.value,
                platform_title: document.getElementById('di-platform-title')?.value,
                platform_subtitle: document.getElementById('di-platform-subtitle')?.value,
                version: document.getElementById('di-version')?.value,
                edition: document.getElementById('di-edition')?.value,
                default_currency: document.getElementById('di-currency')?.value,
                website: document.getElementById('di-website')?.value,
                support_portal: document.getElementById('di-support-portal')?.value,
                footer_copyright: document.getElementById('di-footer-copyright')?.value
            };
        } else if (section === 'company') {
            payload = {
                legal_company_name: document.getElementById('di-legal-name')?.value,
                trading_name: document.getElementById('di-trading-name')?.value,
                gstin: document.getElementById('di-gstin')?.value,
                pan: document.getElementById('di-pan')?.value,
                cin: document.getElementById('di-cin')?.value,
                iso_certifications: document.getElementById('di-iso')?.value
            };
        } else if (section === 'addresses') {
            payload = {
                registered_office: document.getElementById('di-reg-office')?.value,
                corporate_office: document.getElementById('di-corp-office')?.value
            };
        } else if (section === 'contacts') {
            payload = {
                general_email: document.getElementById('di-email-general')?.value,
                support_email: document.getElementById('di-email-support')?.value,
                billing_email: document.getElementById('di-email-billing')?.value,
                general_phone: document.getElementById('di-phone-general')?.value
            };
        }

        try {
            const token = localStorage.getItem('token') || localStorage.getItem('access_token');
            const res = await fetch('/api/document-identity/update', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ section, payload })
            });

            const result = await res.json();
            if (result.status === 'success') {
                alert(`Document Identity section '${section}' updated successfully!`);
                this.init();
            } else {
                alert(`Error saving section: ${result.message || 'Failed'}`);
            }
        } catch (err) {
            console.error("Save error:", err);
            alert("Failed to save changes.");
        }
    },

    async saveTemplateForm() {
        const selector = document.getElementById('di-template-selector');
        if (!selector) return;
        const template_key = selector.value;
        const payload = {
            template_key,
            header_title: document.getElementById('di-tmpl-title')?.value,
            subtitle: document.getElementById('di-tmpl-subtitle')?.value,
            footer_text: document.getElementById('di-tmpl-footer')?.value,
            watermark_text: document.getElementById('di-tmpl-watermark')?.value,
            confidential_text: document.getElementById('di-tmpl-confidential')?.value
        };

        try {
            const token = localStorage.getItem('token') || localStorage.getItem('access_token');
            const res = await fetch('/api/document-identity/update', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ section: 'template', payload })
            });

            const result = await res.json();
            if (result.status === 'success') {
                alert(`Template '${template_key}' updated successfully!`);
                this.init();
            }
        } catch (err) {
            console.error("Template save error:", err);
        }
    },

    async openLivePreview(type) {
        try {
            const token = localStorage.getItem('token') || localStorage.getItem('access_token');
            const res = await fetch('/api/document-identity/preview', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                },
                body: JSON.stringify({ type })
            });

            const result = await res.json();
            if (result.status === 'success') {
                document.getElementById('doc-preview-title').textContent = `Live Preview: ${type.toUpperCase()} Template`;
                document.getElementById('doc-preview-body').innerHTML = result.preview_html;

                const modal = new bootstrap.Modal(document.getElementById('doc-preview-modal'));
                modal.show();
            }
        } catch (err) {
            console.error("Preview error:", err);
        }
    }
};

const UsageExplorer = {
    records: [],

    async init() {
        try {
            const token = localStorage.getItem('token') || localStorage.getItem('access_token');
            const res = await fetch('/api/document-identity/usage-map', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const result = await res.json();

            if (result.status === 'success') {
                this.records = result.usage_map || [];
                this.renderTable(this.records);
                document.getElementById('ue-total-mapped').textContent = `${this.records.length} Active Mappings`;
            }
        } catch (err) {
            console.error("Failed to load usage map:", err);
        }
    },

    renderTable(list) {
        const tbody = document.getElementById('ue-table-body');
        if (!tbody) return;

        if (list.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center p-4 text-muted">No settings usage mappings found. Click "Rescan Codebase" to generate.</td></tr>`;
            return;
        }

        tbody.innerHTML = list.map(r => `
            <tr>
                <td><code class="text-primary font-monospace bg-light p-1 rounded-1">${r.setting_key}</code></td>
                <td>
                    <div class="fw-bold">${r.module}</div>
                    <span class="text-xs text-muted">${r.feature}</span>
                </td>
                <td>
                    <div class="fw-bold">${r.component}</div>
                    <span class="text-xs text-muted">${r.page || 'N/A'}</span>
                </td>
                <td>
                    <span class="badge ${this.getBadgeClass(r.export_type)}">${r.export_type}</span>
                </td>
                <td class="font-monospace text-xs">${r.backend_service}</td>
                <td class="font-monospace text-xs text-muted" style="max-width:180px; overflow:hidden; text-overflow:ellipsis;" title="${r.file_path}">${r.file_path}</td>
                <td>
                    <button class="btn btn-sm btn-outline-primary py-0 px-2" onclick="UsageExplorer.showImpact('${r.setting_key}')">Impact</button>
                </td>
            </tr>
        `).join('');
    },

    getBadgeClass(type) {
        if (type === 'PDF') return 'bg-danger-subtle text-danger border border-danger-subtle';
        if (type === 'Excel') return 'bg-success-subtle text-success border border-success-subtle';
        if (type === 'CSV') return 'bg-info-subtle text-info border border-info-subtle';
        if (type === 'Email') return 'bg-warning-subtle text-warning border border-warning-subtle';
        return 'bg-primary-subtle text-primary border border-primary-subtle';
    },

    filterTable() {
        const query = document.getElementById('ue-search')?.value.toLowerCase() || '';
        const exportFilter = document.getElementById('ue-export-filter')?.value || '';

        const filtered = this.records.filter(r => {
            const matchesQuery = (
                r.setting_key.toLowerCase().includes(query) ||
                r.module.toLowerCase().includes(query) ||
                r.component.toLowerCase().includes(query) ||
                (r.file_path && r.file_path.toLowerCase().includes(query))
            );
            const matchesExport = !exportFilter || r.export_type === exportFilter;
            return matchesQuery && matchesExport;
        });

        this.renderTable(filtered);
    },

    async showImpact(setting_key) {
        try {
            const token = localStorage.getItem('token') || localStorage.getItem('access_token');
            const res = await fetch(`/api/document-identity/impact-analysis?setting_key=${setting_key}`, {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const result = await res.json();

            if (result.status === 'success') {
                const info = result.impact_analysis;
                alert(`IMPACT ANALYSIS FOR '${setting_key.toUpperCase()}':\n\n` +
                      `• Total Active Mappings: ${info.total_dependencies}\n` +
                      `• Affected Modules (${info.affected_modules_count}): ${info.affected_modules.join(', ')}\n` +
                      `• Affected Export Formats: ${info.affected_export_types.join(', ')}\n\n` +
                      `Modifying or deleting this setting will automatically update all ${info.total_dependencies} dependent outputs.`);
            }
        } catch (err) {
            console.error("Impact error:", err);
        }
    },

    async rescanCodebase() {
        try {
            const token = localStorage.getItem('token') || localStorage.getItem('access_token');
            const res = await fetch('/api/document-identity/scan-dependencies', {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const result = await res.json();
            if (result.status === 'success') {
                alert(result.message);
                this.init();
            }
        } catch (err) {
            console.error("Rescan error:", err);
        }
    }
};

// Auto-initialize when Document Identity or Usage Mapping tab is selected
document.addEventListener('DOMContentLoaded', () => {
    DocIdentityManager.init();
    UsageExplorer.init();

    const urlParams = new URLSearchParams(window.location.search);
    const tabParam = urlParams.get('tab');
    if (tabParam && window.settingsManager) {
        setTimeout(() => {
            const btn = document.querySelector(`[data-target="${tabParam}"]`);
            if (btn) window.settingsManager.switchTab(tabParam, btn);
        }, 200);
    }
});
