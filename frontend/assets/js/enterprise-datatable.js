/**
 * EnterpriseDataTable — Production-ready server-side Data Table Controller
 * Scalable for datasets with 100,000+ to 1,000,000+ records.
 * 
 * Features:
 * - Server-side pagination, search, sort, and filtering
 * - Debounced input search
 * - Custom page size choices: 10, 25, 50, 100, 250
 * - Standardized footer ("Showing X–Y of Z records", pagination controls)
 * - Shimmer skeleton state & error handling
 */

class EnterpriseDataTable {
    constructor(config) {
        this.container = typeof config.container === 'string' 
            ? document.querySelector(config.container) 
            : config.container;
            
        if (!this.container) {
            console.error('[EnterpriseDataTable] Container not found:', config.container);
            return;
        }

        this.apiUrl = config.apiUrl;
        this.columns = config.columns || [];
        this.rowKey = config.rowKey || 'id';
        this.onRowClick = config.onRowClick || null;
        this.fetcher = config.fetcher || this.defaultFetcher.bind(this);
        
        // State
        this.page = config.page || 1;
        this.perPage = config.perPage || 25;
        this.search = config.search || '';
        this.sortBy = config.sortBy || '';
        this.order = config.order || 'asc';
        this.filters = config.filters || {};
        
        this.data = [];
        this.total = 0;
        this.totalPages = 1;
        this.loading = false;
        this.error = null;
        
        this.searchDebounceTimer = null;
        
        this.init();
    }

    async defaultFetcher(params) {
        const queryParams = new URLSearchParams({
            page: params.page,
            per_page: params.perPage,
            q: params.search,
            search: params.search,
            sort_by: params.sortBy,
            order: params.order,
            sort_dir: params.order,
            ...params.filters
        });

        const token = localStorage.getItem('token') || sessionStorage.getItem('token');
        const headers = { 'Content-Type': 'application/json' };
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const res = await fetch(`${this.apiUrl}?${queryParams.toString()}`, { headers });
        if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        const json = await res.json();
        
        // Standardize response payload
        const items = json.items || json.data || [];
        const total = json.total || (json.meta ? json.meta.total : items.length);
        const page = json.page || (json.meta ? json.meta.page : params.page);
        const perPage = json.per_page || (json.meta ? json.meta.page_size : params.perPage);
        const totalPages = json.total_pages || Math.max(1, Math.ceil(total / perPage));
        
        return { items, total, page, perPage, totalPages };
    }

    init() {
        this.renderLayout();
        this.bindEvents();
        this.loadData();
    }

    renderLayout() {
        this.container.innerHTML = `
            <div class="enterprise-datatable-wrapper ds-card border shadow-sm rounded-3 overflow-hidden bg-body">
                <!-- Header Toolbar -->
                <div class="dt-header p-3 border-bottom d-flex align-items-center justify-content-between flex-wrap gap-2 bg-body-tertiary">
                    <div class="d-flex align-items-center gap-2 flex-grow-1" style="max-width: 320px;">
                        <div class="position-relative w-100">
                            <i data-lucide="search" style="width:14px;height:14px;position:absolute;left:10px;top:50%;transform:translateY(-50%);opacity:0.5;"></i>
                            <input type="search" class="dt-search-input ds-input w-100" placeholder="Search records..." style="padding-left:32px;height:36px;font-size:13px;" value="${this.search}">
                        </div>
                    </div>
                    
                    <div class="d-flex align-items-center gap-2">
                        <label class="text-xs text-muted me-1 mb-0">Rows:</label>
                        <select class="dt-per-page-select ds-input" style="height:36px;font-size:12.5px;padding:4px 28px 4px 10px;width:auto;">
                            <option value="5" ${this.perPage===5?'selected':''}>5</option>
                            <option value="10" ${this.perPage===10?'selected':''}>10</option>
                            <option value="20" ${this.perPage===20?'selected':''}>20</option>
                            <option value="50" ${this.perPage===50?'selected':''}>50</option>
                            <option value="100" ${this.perPage===100?'selected':''}>100</option>
                        </select>
                        <button class="dt-refresh-btn ds-btn ds-btn-secondary btn-sm" title="Refresh data" style="height:36px;">
                            <i data-lucide="refresh-cw" style="width:14px;height:14px;"></i>
                        </button>
                    </div>
                </div>

                <!-- Table Container -->
                <div class="dt-table-container position-relative overflow-auto" style="min-height: 240px;">
                    <table class="table table-hover align-middle mb-0 text-sm">
                        <thead class="bg-body-secondary text-uppercase text-muted text-xs sticky-top border-bottom">
                            <tr>
                                ${this.columns.map(col => `
                                    <th style="${col.width ? `width:${col.width};` : ''}" class="${col.sortable ? 'cursor-pointer select-none dt-sort-header' : ''}" data-key="${col.key || ''}">
                                        <div class="d-flex align-items-center justify-content-between gap-1">
                                            <span>${col.title}</span>
                                            ${col.sortable ? `<i data-lucide="chevrons-up-down" style="width:12px;height:12px;opacity:0.4;"></i>` : ''}
                                        </div>
                                    </th>
                                `).join('')}
                            </tr>
                        </thead>
                        <tbody class="dt-body">
                            <!-- Rows loaded via JS -->
                        </tbody>
                    </table>
                </div>

                <!-- Footer Pagination Bar -->
                <div class="dt-footer p-3 border-top d-flex align-items-center justify-content-between flex-wrap gap-2 bg-body-tertiary">
                    <div class="dt-info text-xs text-muted fw-medium">
                        Showing 0–0 of 0 records
                    </div>
                    <div class="dt-pagination d-flex align-items-center gap-1">
                        <!-- Pagination buttons -->
                    </div>
                </div>
            </div>
        `;

        if (window.lucide) lucide.createIcons();
    }

    bindEvents() {
        const searchInput = this.container.querySelector('.dt-search-input');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                clearTimeout(this.searchDebounceTimer);
                this.searchDebounceTimer = setTimeout(() => {
                    this.search = e.target.value.trim();
                    this.page = 1;
                    this.loadData();
                }, 350);
            });
        }

        const perPageSelect = this.container.querySelector('.dt-per-page-select');
        if (perPageSelect) {
            perPageSelect.addEventListener('change', (e) => {
                this.perPage = parseInt(e.target.value, 10);
                this.page = 1;
                this.loadData();
            });
        }

        const refreshBtn = this.container.querySelector('.dt-refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadData());
        }

        const headers = this.container.querySelectorAll('.dt-sort-header');
        headers.forEach(h => {
            h.addEventListener('click', () => {
                const key = h.dataset.key;
                if (!key) return;
                if (this.sortBy === key) {
                    this.order = this.order === 'asc' ? 'desc' : 'asc';
                } else {
                    this.sortBy = key;
                    this.order = 'asc';
                }
                this.page = 1;
                this.loadData();
            });
        });
    }

    async loadData() {
        this.loading = true;
        this.error = null;
        this.renderSkeleton();

        try {
            const res = await this.fetcher({
                page: this.page,
                perPage: this.perPage,
                search: this.search,
                sortBy: this.sortBy,
                order: this.order,
                filters: this.filters
            });

            this.data = res.items || [];
            this.total = res.total || 0;
            this.page = res.page || 1;
            this.perPage = res.perPage || 25;
            this.totalPages = res.totalPages || 1;

            this.renderRows();
            this.renderFooter();
        } catch (err) {
            console.error('[EnterpriseDataTable] Fetch error:', err);
            this.error = err.message || 'Failed to load records.';
            this.renderError();
        } finally {
            this.loading = false;
        }
    }

    renderSkeleton() {
        const tbody = this.container.querySelector('.dt-body');
        if (!tbody) return;

        const colsCount = this.columns.length || 1;
        const rows = Array.from({ length: 5 }).map(() => `
            <tr>
                ${Array.from({ length: colsCount }).map(() => `
                    <td><div class="placeholder-glow"><span class="placeholder col-8 py-2 rounded"></span></div></td>
                `).join('')}
            </tr>
        `).join('');

        tbody.innerHTML = rows;
    }

    renderError() {
        const tbody = this.container.querySelector('.dt-body');
        if (!tbody) return;

        tbody.innerHTML = `
            <tr>
                <td colspan="${this.columns.length}" class="text-center py-5">
                    <div class="text-danger mb-2 fw-medium">${this.escape(this.error)}</div>
                    <button class="ds-btn ds-btn-secondary btn-sm dt-retry-btn">
                        <i data-lucide="rotate-ccw" class="me-1" style="width:13px;height:13px;"></i> Retry
                    </button>
                </td>
            </tr>
        `;

        const retryBtn = tbody.querySelector('.dt-retry-btn');
        if (retryBtn) retryBtn.addEventListener('click', () => this.loadData());
        if (window.lucide) lucide.createIcons();
    }

    renderRows() {
        const tbody = this.container.querySelector('.dt-body');
        if (!tbody) return;

        if (this.data.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="${this.columns.length}" class="text-center py-5 text-muted">
                        <i data-lucide="inbox" style="width:28px;height:28px;opacity:0.3;" class="mb-2 d-block mx-auto"></i>
                        <div>No matching records found.</div>
                    </td>
                </tr>
            `;
            if (window.lucide) lucide.createIcons();
            return;
        }

        tbody.innerHTML = this.data.map(row => `
            <tr class="${this.onRowClick ? 'cursor-pointer' : ''}" data-id="${row[this.rowKey] || ''}">
                ${this.columns.map(col => `
                    <td>
                        ${col.render ? col.render(row[col.key], row) : this.escape(row[col.key])}
                    </td>
                `).join('')}
            </tr>
        `).join('');

        if (this.onRowClick) {
            tbody.querySelectorAll('tr').forEach(tr => {
                tr.addEventListener('click', () => {
                    const id = tr.dataset.id;
                    const row = this.data.find(r => String(r[this.rowKey]) === String(id));
                    if (row) this.onRowClick(row);
                });
            });
        }

        if (window.lucide) lucide.createIcons();
    }

    renderFooter() {
        const info = this.container.querySelector('.dt-info');
        const pagination = this.container.querySelector('.dt-pagination');

        const start = this.total === 0 ? 0 : (this.page - 1) * this.perPage + 1;
        const end = Math.min(this.page * this.perPage, this.total);

        if (info) {
            info.textContent = `Showing ${start.toLocaleString()}–${end.toLocaleString()} of ${this.total.toLocaleString()} records`;
        }

        if (!pagination) return;

        const btns = [];
        btns.push(`<button class="ds-btn ds-btn-secondary btn-sm dt-pg-btn" data-page="1" ${this.page <= 1 ? 'disabled' : ''} title="First Page">«</button>`);
        btns.push(`<button class="ds-btn ds-btn-secondary btn-sm dt-pg-btn" data-page="${this.page - 1}" ${this.page <= 1 ? 'disabled' : ''} title="Previous Page">‹</button>`);

        const pStart = Math.max(1, this.page - 2);
        const pEnd = Math.min(this.totalPages, this.page + 2);

        if (pStart > 1) {
            btns.push(`<button class="ds-btn ds-btn-secondary btn-sm dt-pg-btn" data-page="1">1</button>`);
            if (pStart > 2) btns.push(`<span class="text-muted px-1 text-xs">…</span>`);
        }

        for (let i = pStart; i <= pEnd; i++) {
            btns.push(`<button class="ds-btn ${i === this.page ? 'ds-btn-primary' : 'ds-btn-secondary'} btn-sm dt-pg-btn" data-page="${i}">${i}</button>`);
        }

        if (pEnd < this.totalPages) {
            if (pEnd < this.totalPages - 1) btns.push(`<span class="text-muted px-1 text-xs">…</span>`);
            btns.push(`<button class="ds-btn ds-btn-secondary btn-sm dt-pg-btn" data-page="${this.totalPages}">${this.totalPages}</button>`);
        }

        btns.push(`<button class="ds-btn ds-btn-secondary btn-sm dt-pg-btn" data-page="${this.page + 1}" ${this.page >= this.totalPages ? 'disabled' : ''} title="Next Page">›</button>`);
        btns.push(`<button class="ds-btn ds-btn-secondary btn-sm dt-pg-btn" data-page="${this.totalPages}" ${this.page >= this.totalPages ? 'disabled' : ''} title="Last Page">»</button>`);

        pagination.innerHTML = btns.join('');

        pagination.querySelectorAll('.dt-pg-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const targetPage = parseInt(e.currentTarget.dataset.page, 10);
                if (targetPage && targetPage !== this.page && targetPage >= 1 && targetPage <= this.totalPages) {
                    this.page = targetPage;
                    this.loadData();
                }
            });
        });
    }

    setFilters(filters) {
        this.filters = { ...this.filters, ...filters };
        this.page = 1;
        this.loadData();
    }

    escape(str) {
        if (str === null || str === undefined) return '—';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }
}

if (typeof window !== 'undefined') {
    window.EnterpriseDataTable = EnterpriseDataTable;

    /**
     * Universal QCMS Pagination Component
     */
    window.createStandardPagination = function({
        containerId,
        entityName = 'records',
        totalItems = 0,
        currentPage = 1,
        pageSize = 5,
        pageSizeOptions = [5, 10, 25, 50, 100],
        onPageChange,
        onPageSizeChange
    }) {
        const container = typeof containerId === 'string' ? document.getElementById(containerId) : containerId;
        if (!container) return;

        const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
        const startItem = totalItems === 0 ? 0 : (currentPage - 1) * pageSize + 1;
        const endItem = Math.min(currentPage * pageSize, totalItems);
        const isPrevDisabled = currentPage <= 1;
        const isNextDisabled = currentPage >= totalPages;

        const elementId = typeof containerId === 'string' ? containerId : (container.id || 'qcms_pag');

        container.innerHTML = `
            <div class="d-flex align-items-center justify-content-between flex-wrap gap-2 pt-3 pb-2 px-3 border-top mt-2" style="font-size: 13px; color: var(--ds-text-secondary, #64748b);">
                <!-- Left: Showing Info -->
                <div class="text-muted fw-medium text-xs">
                    Showing <strong class="text-dark fw-bold">${startItem.toLocaleString()}-${endItem.toLocaleString()}</strong> of <strong class="text-dark fw-bold">${totalItems.toLocaleString()}</strong> ${entityName}
                </div>

                <!-- Right: Controls Group -->
                <div class="d-flex align-items-center gap-3 flex-wrap">
                    <!-- Page Size Dropdown -->
                    <div class="d-flex align-items-center gap-1">
                        <select class="form-select form-select-sm shadow-none border rounded-2 px-2 py-1" style="width: auto; font-size: 12.5px; height: 32px; font-weight: 500; cursor: pointer; background-color: var(--ds-input-bg, #fff);" id="${elementId}_pageSize">
                            ${pageSizeOptions.map(size => `<option value="${size}" ${size === pageSize ? 'selected' : ''}>${size}</option>`).join('')}
                        </select>
                        <span class="text-muted text-xs ms-1">per page</span>
                    </div>

                    <!-- Prev / Page / Next Buttons -->
                    <div class="d-flex align-items-center gap-2">
                        <button class="btn btn-sm btn-light border px-2 py-1 rounded-2 text-xs d-flex align-items-center gap-1 shadow-none" 
                                id="${elementId}_prevBtn" ${isPrevDisabled ? 'disabled style="opacity: 0.4; cursor: not-allowed;"' : ''}>
                            <i data-lucide="chevron-left" style="width: 14px; height: 14px;"></i> Prev
                        </button>
                        
                        <span class="fw-semibold text-dark text-xs px-1" style="white-space: nowrap;">
                            Page ${currentPage} of ${totalPages}
                        </span>

                        <button class="btn btn-sm btn-light border px-2 py-1 rounded-2 text-xs d-flex align-items-center gap-1 shadow-none" 
                                id="${elementId}_nextBtn" ${isNextDisabled ? 'disabled style="opacity: 0.4; cursor: not-allowed;"' : ''}>
                            Next <i data-lucide="chevron-right" style="width: 14px; height: 14px;"></i>
                        </button>
                    </div>
                </div>
            </div>
        `;

        if (window.lucide) window.lucide.createIcons();

        // Event Bindings
        document.getElementById(`${elementId}_pageSize`)?.addEventListener('change', (e) => {
            if (typeof onPageSizeChange === 'function') {
                onPageSizeChange(parseInt(e.target.value, 10));
            }
        });

        document.getElementById(`${elementId}_prevBtn`)?.addEventListener('click', () => {
            if (currentPage > 1 && typeof onPageChange === 'function') {
                onPageChange(currentPage - 1);
            }
        });

        document.getElementById(`${elementId}_nextBtn`)?.addEventListener('click', () => {
            if (currentPage < totalPages && typeof onPageChange === 'function') {
                onPageChange(currentPage + 1);
            }
        });
    };
}
