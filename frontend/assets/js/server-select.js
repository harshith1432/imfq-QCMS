/**
 * ServerSelect — Enterprise Lazy-Loading Dropdown Component
 * Enables search-as-you-type for high-cardinality foreign key lookups
 * (Users, Organizations, Departments, Products, Projects) without preloading.
 */

class ServerSelect {
    constructor(config) {
        this.element = typeof config.element === 'string' 
            ? document.querySelector(config.element) 
            : config.element;
            
        if (!this.element) {
            console.error('[ServerSelect] Element not found:', config.element);
            return;
        }

        this.apiUrl = config.apiUrl;
        this.placeholder = config.placeholder || 'Search or select...';
        this.valueKey = config.valueKey || 'id';
        this.labelKey = config.labelKey || 'name';
        this.sublabelKey = config.sublabelKey || 'email';
        this.onChange = config.onChange || null;

        this.selectedValue = config.value || null;
        this.selectedItem = config.selectedItem || null;
        this.options = [];
        this.loading = false;
        this.debounceTimer = null;

        this.init();
    }

    init() {
        this.element.classList.add('server-select-container', 'position-relative');
        this.render();
        this.bindEvents();
    }

    render() {
        const labelText = this.selectedItem 
            ? (this.selectedItem[this.labelKey] || this.selectedValue)
            : this.placeholder;

        this.element.innerHTML = `
            <div class="server-select-trigger ds-input d-flex align-items-center justify-content-between cursor-pointer" style="height:38px;padding:6px 12px;font-size:13px;">
                <span class="server-select-label ${!this.selectedItem ? 'text-muted' : ''}">${this.escape(labelText)}</span>
                <i data-lucide="chevron-down" style="width:14px;height:14px;opacity:0.6;"></i>
            </div>
            <div class="server-select-dropdown position-absolute w-100 bg-body border rounded-3 shadow-lg mt-1 p-2 d-none" style="z-index: 1050; top: 100%; left: 0;">
                <div class="mb-2">
                    <input type="search" class="server-select-search ds-input w-100" placeholder="Type to search..." style="height:32px;font-size:12px;">
                </div>
                <div class="server-select-results overflow-auto" style="max-height: 200px;">
                    <div class="text-xs text-muted text-center py-2">Start typing to search...</div>
                </div>
            </div>
        `;

        if (window.lucide) lucide.createIcons();
    }

    bindEvents() {
        const trigger = this.element.querySelector('.server-select-trigger');
        const dropdown = this.element.querySelector('.server-select-dropdown');
        const searchInput = this.element.querySelector('.server-select-search');

        trigger.addEventListener('click', (e) => {
            e.stopPropagation();
            const isOpen = !dropdown.classList.contains('d-none');
            document.querySelectorAll('.server-select-dropdown').forEach(d => d.classList.add('d-none'));
            if (!isOpen) {
                dropdown.classList.remove('d-none');
                searchInput.focus();
                if (this.options.length === 0) this.fetchOptions('');
            }
        });

        searchInput.addEventListener('input', (e) => {
            clearTimeout(this.debounceTimer);
            this.debounceTimer = setTimeout(() => {
                this.fetchOptions(e.target.value.trim());
            }, 300);
        });

        document.addEventListener('click', (e) => {
            if (!this.element.contains(e.target)) {
                dropdown.classList.add('d-none');
            }
        });
    }

    async fetchOptions(query) {
        this.loading = true;
        const resultsEl = this.element.querySelector('.server-select-results');
        if (resultsEl) resultsEl.innerHTML = `<div class="text-xs text-muted text-center py-2"><span class="spinner-border spinner-border-sm me-1"></span>Loading...</div>`;

        try {
            const token = window.api ? window.api.token : null;
            const headers = { 'Content-Type': 'application/json' };
            if (token) headers['Authorization'] = `Bearer ${token}`;

            const url = new URL(this.apiUrl, window.location.origin);
            url.searchParams.set('q', query);
            url.searchParams.set('search', query);
            url.searchParams.set('per_page', '20');

            const res = await fetch(url.toString(), { headers });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const json = await res.json();

            this.options = json.items || json.data || [];
            this.renderResults();
        } catch (err) {
            console.error('[ServerSelect] Fetch error:', err);
            if (resultsEl) resultsEl.innerHTML = `<div class="text-xs text-danger text-center py-2">Failed to load options.</div>`;
        } finally {
            this.loading = false;
        }
    }

    renderResults() {
        const resultsEl = this.element.querySelector('.server-select-results');
        if (!resultsEl) return;

        if (this.options.length === 0) {
            resultsEl.innerHTML = `<div class="text-xs text-muted text-center py-2">No matching options found.</div>`;
            return;
        }

        resultsEl.innerHTML = this.options.map(opt => `
            <div class="server-select-item p-2 rounded-2 cursor-pointer border-bottom-light text-sm hover-bg-tertiary" data-val="${opt[this.valueKey]}">
                <div class="fw-medium text-main">${this.escape(opt[this.labelKey])}</div>
                ${opt[this.sublabelKey] ? `<div class="text-xs text-muted">${this.escape(opt[this.sublabelKey])}</div>` : ''}
            </div>
        `).join('');

        resultsEl.querySelectorAll('.server-select-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const val = e.currentTarget.dataset.val;
                const selected = this.options.find(o => String(o[this.valueKey]) === String(val));
                if (selected) {
                    this.selectedValue = val;
                    this.selectedItem = selected;
                    this.render();
                    if (this.onChange) this.onChange(val, selected);
                }
            });
        });
    }

    getValue() { return this.selectedValue; }
    setValue(val, item = null) {
        this.selectedValue = val;
        this.selectedItem = item;
        this.render();
    }

    escape(str) {
        if (!str) return '';
        return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
    }
}

if (typeof window !== 'undefined') {
    window.ServerSelect = ServerSelect;
}
