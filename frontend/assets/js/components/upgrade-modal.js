/**
 * Upgrade Modal Component
 * Displays a premium upgrade prompt with plan benefits
 */

const UpgradeModal = {
    modalId: 'upgradeModal',
    
    show(feature = '') {
        this.ensureModalExists();
        const featureTitle = feature.replace(/_/g, ' ').toUpperCase();
        document.getElementById('lockedFeatureName').textContent = featureTitle || 'Premium Feature';
        
        const modal = new bootstrap.Modal(document.getElementById(this.modalId));
        modal.show();
    },

    ensureModalExists() {
        if (document.getElementById(this.modalId)) return;

        const modalHTML = `
        <div class="modal fade" id="${this.modalId}" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-dialog-centered modal-lg">
                <div class="modal-content glass-card border-0 overflow-hidden" style="background: rgba(255, 255, 255, 0.95); backdrop-filter: blur(20px);">
                    <div class="modal-body p-0">
                        <div class="row g-0">
                            <div class="col-md-5 bg-primary p-5 d-flex flex-column justify-content-center text-white">
                                <i class="fas fa-gem fa-4x mb-4 opacity-50"></i>
                                <h2 class="fw-bold mb-3">Upgrade to Premium</h2>
                                <p class="opacity-75 mb-4">Unlock advanced features, unlimited projects, and AI-powered insights to scale your quality management.</p>
                                <ul class="list-unstyled mb-0">
                                    <li class="mb-2"><i class="fas fa-check-circle me-2"></i> Full 8-Stage Workflow</li>
                                    <li class="mb-2"><i class="fas fa-check-circle me-2"></i> AI-Powered Assistant</li>
                                    <li class="mb-2"><i class="fas fa-check-circle me-2"></i> Advanced Analytics</li>
                                    <li class="mb-2"><i class="fas fa-check-circle me-2"></i> Custom White Labeling</li>
                                </ul>
                            </div>
                            <div class="col-md-7 p-5 position-relative">
                                <button type="button" class="btn-close position-absolute top-0 end-0 m-4" data-bs-dismiss="modal" aria-label="Close"></button>
                                
                                <div class="text-center mb-4">
                                    <div class="badge bg-warning-soft text-warning mb-2 px-3 py-2 rounded-pill fw-bold">
                                        LOCKED: <span id="lockedFeatureName">FEATURE</span>
                                    </div>
                                    <h3 class="fw-bold">Ready to scale?</h3>
                                    <p class="text-muted">Choose the plan that fits your organization's needs.</p>
                                </div>

                                <div class="d-grid gap-3">
                                    <div class="plan-option p-3 border rounded-3 hover-shadow cursor-pointer transition" onclick="window.location.href='index.html#pricing'">
                                        <div class="d-flex justify-content-between align-items-center">
                                            <div>
                                                <h5 class="fw-bold mb-0">Professional</h5>
                                                <small class="text-muted">For growing teams</small>
                                            </div>
                                            <div class="text-primary fw-bold">₹499/mo</div>
                                        </div>
                                    </div>
                                    
                                    <div class="plan-option p-3 border border-primary bg-primary-soft rounded-3 hover-shadow cursor-pointer transition" onclick="window.location.href='index.html#pricing'">
                                        <div class="d-flex justify-content-between align-items-center">
                                            <div>
                                                <h5 class="fw-bold mb-0">Enterprise</h5>
                                                <small class="text-muted">For global operations</small>
                                            </div>
                                            <div class="text-primary fw-bold">Custom</div>
                                        </div>
                                    </div>
                                </div>

                                <div class="mt-4 text-center">
                                    <a href="index.html#pricing" class="btn btn-primary btn-lg w-100 rounded-pill mb-3">View All Plans</a>
                                    <p class="small text-muted mb-0">Need a custom demo? <a href="#" class="text-primary fw-bold text-decoration-none">Contact Sales</a></p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        <style>
            .bg-primary-soft { background-color: rgba(37, 99, 235, 0.05); }
            .bg-warning-soft { background-color: rgba(245, 158, 11, 0.1); }
            .plan-option:hover { border-color: #2563eb !important; background-color: rgba(37, 99, 235, 0.02); transform: translateY(-2px); }
            .cursor-pointer { cursor: pointer; }
            .feature-locked { opacity: 0.6; filter: grayscale(0.8); cursor: not-allowed !important; pointer-events: auto !important; }
            .feature-locked * { pointer-events: none !important; }
        </style>
        `;

        const container = document.createElement('div');
        container.innerHTML = modalHTML;
        document.body.appendChild(container);
    }
};

window.UpgradeModal = UpgradeModal;
