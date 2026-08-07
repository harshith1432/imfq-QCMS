/**
 * Subscription Guard - UI level access control for SaaS features
 * Works in tandem with backend enforcement
 */

const SubscriptionGuard = {
    PLAN_CONFIGS: {
        'Starter': {
            features: ['basic_workflow', 'standard_reports'],
            ai_assistant: false,
            white_label: false,
            analytics: false,
            repository: false
        },
        'Professional': {
            features: ['full_workflow', 'advanced_analytics', 'repository', 'ai_assistant', 'audit_logs'],
            ai_assistant: true,
            white_label: false,
            analytics: true,
            repository: true
        },
        'Enterprise': {
            features: ['full_workflow', 'advanced_analytics', 'repository', 'ai_assistant', 'audit_logs', 'white_label', 'multi_plant', 'api_access'],
            ai_assistant: true,
            white_label: true,
            analytics: true,
            repository: true
        }
    },

    getCurrentPlan() {
        try {
            const user = JSON.parse(sessionStorage.getItem('user'));
            return user?.subscription_plan || 'Starter';
        } catch (e) {
            return 'Starter';
        }
    },

    hasFeature(featureName) {
        const plan = this.getCurrentPlan();
        const config = this.PLAN_CONFIGS[plan] || this.PLAN_CONFIGS['Starter'];
        
        return config[featureName] === true || (config.features && config.features.includes(featureName));
    },

    init() {
        // Intercept clicks on locked features
        document.addEventListener('click', (e) => {
            const lockEl = e.target.closest('[data-feature-lock]');
            if (lockEl) {
                const feature = lockEl.getAttribute('data-feature-lock');
                if (!this.hasFeature(feature)) {
                    e.preventDefault();
                    e.stopPropagation();
                    this.showUpgradeModal(feature);
                }
            }
        }, true);

        // Hide or dim locked UI elements on page load
        this.applyUIGuards();
    },

    applyUIGuards() {
        const lockedElements = document.querySelectorAll('[data-feature-lock]');
        lockedElements.forEach(el => {
            const feature = el.getAttribute('data-feature-lock');
            if (!this.hasFeature(feature)) {
                // Add visual indicator (e.g., lock icon or opacity)
                if (!el.querySelector('.fa-lock')) {
                    const lock = document.createElement('i');
                    lock.className = 'fas fa-lock ms-2 text-warning';
                    lock.style.fontSize = '0.8em';
                    el.appendChild(lock);
                }
                el.classList.add('feature-locked');
                el.title = `Upgrade your plan to access ${feature.replace('_', ' ')}`;
            }
        });
    },

    showUpgradeModal(feature) {
        if (window.UpgradeModal) {
            window.UpgradeModal.show(feature);
        } else {
            const msg = `The feature '${feature.replace('_', ' ')}' is only available on Professional or Enterprise plans. Would you like to view our pricing plans?`;
            if (confirm(msg)) {
                window.location.href = 'index.html#pricing';
            }
        }
    }
};

// Auto-init
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => SubscriptionGuard.init());
} else {
    SubscriptionGuard.init();
}

window.SubscriptionGuard = SubscriptionGuard;
