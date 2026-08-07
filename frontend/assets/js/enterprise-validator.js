/**
 * Enterprise Form Validator & Input Sanitizer (QCMS Platform)
 * Implements real-time input validation, ARIA accessibility, submit protection,
 * auto-trimming, character counting, and XSS sanitization across all forms.
 */
class EnterpriseValidator {
    constructor() {
        this.rules = {
            required: (val) => val !== null && val !== undefined && String(val).trim().length > 0,
            email: (val) => !val || /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(String(val).trim()),
            phone: (val) => !val || /^\+?[0-9\s\-()]{7,20}$/.test(String(val).trim()),
            number: (val) => !val || !isNaN(Number(val)),
            url: (val) => !val || /^(https?:\/\/)?([\w.-]+)+[\w\-_~:/?#[\]@!$&'()*+,;=.]+$/.test(String(val).trim()),
            password: (val) => !val || (
                val.length >= 8 &&
                val.length <= 128 &&
                /[A-Z]/.test(val) &&
                /[a-z]/.test(val) &&
                /[0-9]/.test(val) &&
                /[^A-Za-z0-9]/.test(val)
            ),
            pan: (val) => {
                if (!val) return true;
                const clean = String(val).trim().toUpperCase();
                return /^[A-Z]{5}[0-9]{4}[A-Z]{1}$/.test(clean) && ['C','P','H','F','A','T','B','L','J','G'].includes(clean[3]);
            },
            gstin: (val) => {
                if (!val) return true;
                const clean = String(val).trim().toUpperCase();
                if (!/^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/.test(clean)) return false;
                
                // Modulus 36 Checksum Validation
                const chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ";
                let factor = 1, sum = 0;
                for (let i = 0; i < 14; i++) {
                    let code = chars.indexOf(clean[i]);
                    let digit = code * factor;
                    factor = (factor === 1) ? 2 : 1;
                    sum += Math.floor(digit / 36) + (digit % 36);
                }
                let checkChar = chars[(36 - (sum % 36)) % 36];
                return clean[14] === checkChar;
            },
            tan: (val) => !val || /^[A-Z]{4}[0-9]{5}[A-Z]{1}$/.test(String(val).trim().toUpperCase()),
            cin: (val) => !val || /^[LU][0-9]{5}[A-Z]{2}[0-9]{4}[A-Z]{3}[0-9]{6}$/.test(String(val).trim().toUpperCase()),
            ifsc: (val) => !val || /^[A-Z]{4}0[A-Z0-9]{6}$/.test(String(val).trim().toUpperCase()),
            swift: (val) => !val || /^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$/.test(String(val).trim().toUpperCase()),
            pincode: (val) => !val || /^[1-9][0-9]{5}$/.test(String(val).trim()),
            aadhaar: (val) => {
                if (!val) return true;
                const clean = String(val).replace(/[\s\-]/g, '');
                if (!/^[2-9][0-9]{11}$/.test(clean)) return false;
                // Verhoeff checksum
                const d = [[0,1,2,3,4,5,6,7,8,9],[1,2,3,4,0,6,7,8,9,5],[2,3,4,0,1,7,8,9,5,6],[3,4,0,1,2,8,9,5,6,7],[4,0,1,2,3,9,5,6,7,8],[5,9,8,7,6,0,4,3,2,1],[6,5,9,8,7,1,0,4,3,2],[7,6,5,9,8,2,1,0,4,3],[8,7,6,5,9,3,2,1,0,4],[9,8,7,6,5,4,3,2,1,0]];
                const p = [[0,1,2,3,4,5,6,7,8,9],[1,5,7,6,2,8,3,0,9,4],[5,8,0,3,7,9,6,1,4,2],[8,9,1,6,0,4,3,5,2,7],[9,4,5,3,1,2,6,8,7,0],[4,2,8,6,5,7,3,9,0,1],[2,7,9,3,8,0,6,4,1,5],[7,0,4,6,9,1,3,2,5,8]];
                let c = 0;
                const digits = clean.split('').reverse().map(Number);
                for (let i = 0; i < digits.length; i++) {
                    c = d[c][p[i % 8][digits[i]]];
                }
                return c === 0;
            }
        };
        this.init();
    }

    init() {
        document.addEventListener('DOMContentLoaded', () => {
            this.bindForms();
            this.bindInputSanitizers();
            this.bindCharacterCounters();
        });
    }

    /**
     * Binds validation handlers to all forms on the page
     */
    bindForms(container = document) {
        const forms = container.querySelectorAll('form[novalidate], form.enterprise-form, form[data-validate-form]');
        forms.forEach(form => {
            if (form.dataset.validatorBound) return;
            form.dataset.validatorBound = "true";

            form.addEventListener('submit', (e) => {
                if (!this.validateForm(form)) {
                    e.preventDefault();
                    e.stopPropagation();
                }
            });

            // Bind blur/input real-time validation to form elements
            const inputs = form.querySelectorAll('input, select, textarea');
            inputs.forEach(input => {
                input.addEventListener('blur', () => this.validateField(input));
                input.addEventListener('input', () => {
                    if (input.classList.contains('is-invalid')) {
                        this.validateField(input);
                    }
                });
            });
        });
    }

    /**
     * Sanitizes user input string on the client side (prevents XSS)
     */
    sanitizeString(str) {
        if (typeof str !== 'string') return str;
        const div = document.createElement('div');
        div.textContent = str.trim();
        return div.innerHTML;
    }

    /**
     * Auto-trims and collapses extra spaces on blur
     */
    bindInputSanitizers(container = document) {
        const inputs = container.querySelectorAll('input[type="text"], input[type="email"], input[type="search"], textarea');
        inputs.forEach(input => {
            if (input.dataset.sanitizerBound) return;
            input.dataset.sanitizerBound = "true";
            input.addEventListener('blur', () => {
                if (input.type !== 'password') {
                    input.value = input.value.trim().replace(/ {2,}/g, ' ');
                }
            });
        });
    }

    /**
     * Attaches dynamic character counter to text inputs/textareas with maxlength
     */
    bindCharacterCounters(container = document) {
        const textFields = container.querySelectorAll('[maxlength], [data-max-length]');
        textFields.forEach(field => {
            if (field.dataset.counterBound) return;
            field.dataset.counterBound = "true";

            const max = field.getAttribute('maxlength') || field.dataset.maxLength;
            if (!max) return;

            let counterEl = field.parentNode.querySelector('.char-counter');
            if (!counterEl) {
                counterEl = document.createElement('div');
                counterEl.className = 'char-counter text-xs text-muted mt-1 text-end';
                field.parentNode.appendChild(counterEl);
            }

            const updateCount = () => {
                const len = field.value.length;
                counterEl.textContent = `${len} / ${max} characters`;
                if (len >= max) {
                    counterEl.classList.add('text-danger');
                } else {
                    counterEl.classList.remove('text-danger');
                }
            };

            field.addEventListener('input', updateCount);
            updateCount();
        });
    }

    /**
     * Validates an individual form control element
     */
    validateField(field) {
        if (field.disabled || field.type === 'hidden') return true;

        const val = field.value;
        const fieldName = field.getAttribute('data-field-name') || field.name || field.placeholder || 'This field';
        let errorMessage = '';

        // Check required
        if (field.hasAttribute('required') || (field.dataset.validate && field.dataset.validate.includes('required'))) {
            if (!this.rules.required(val)) {
                errorMessage = `${fieldName} is required.`;
            }
        }

        // Check minlength / maxlength
        if (!errorMessage && val) {
            const minLen = field.getAttribute('minlength') || field.dataset.minLength;
            const maxLen = field.getAttribute('maxlength') || field.dataset.maxLength;
            if (minLen && val.length < parseInt(minLen, 10)) {
                errorMessage = `${fieldName} must be at least ${minLen} characters long.`;
            } else if (maxLen && val.length > parseInt(maxLen, 10)) {
                errorMessage = `${fieldName} cannot exceed ${maxLen} characters.`;
            }
        }

        // Check specific data-validate rules
        if (!errorMessage && val && field.dataset.validate) {
            const ruleNames = field.dataset.validate.split('|');
            for (const r of ruleNames) {
                if (r === 'required') continue;
                if (this.rules[r] && !this.rules[r](val)) {
                    switch (r) {
                        case 'email':
                            errorMessage = `Please enter a valid email address.`;
                            break;
                        case 'phone':
                            errorMessage = `Please enter a valid phone number.`;
                            break;
                        case 'number':
                            errorMessage = `${fieldName} must be a valid number.`;
                            break;
                        case 'url':
                            errorMessage = `Please enter a valid URL (e.g. https://example.com).`;
                            break;
                        case 'password':
                            errorMessage = `Password must contain at least 8 characters, an uppercase letter, a number, and a special character.`;
                            break;
                        case 'pan':
                            errorMessage = `Invalid PAN Number (e.g. ABCDE1234F).`;
                            break;
                        case 'gstin':
                            errorMessage = `Invalid GST Number format or checksum (e.g. 27AAAAA0000A1Z5).`;
                            break;
                        case 'tan':
                            errorMessage = `Invalid TAN Number format (e.g. ABCD12345E).`;
                            break;
                        case 'cin':
                            errorMessage = `Invalid 21-character CIN format.`;
                            break;
                        case 'ifsc':
                            errorMessage = `Invalid IFSC Code (e.g. SBIN0001234).`;
                            break;
                        case 'swift':
                            errorMessage = `Invalid SWIFT / BIC code.`;
                            break;
                        case 'pincode':
                            errorMessage = `Invalid 6-digit PIN Code.`;
                            break;
                        case 'aadhaar':
                            errorMessage = `Invalid 12-digit Aadhaar Number or checksum.`;
                            break;
                        default:
                            errorMessage = `${fieldName} format is invalid.`;
                    }
                    break;
                }
            }
        }

        // Check password match if data-match attribute exists
        if (!errorMessage && field.dataset.match) {
            const target = document.getElementById(field.dataset.match);
            if (target && val !== target.value) {
                errorMessage = `Passwords do not match.`;
            }
        }

        // Apply error UI & ARIA attributes
        const feedbackEl = this.getOrCreateFeedbackEl(field);
        if (errorMessage) {
            field.classList.add('is-invalid');
            field.classList.remove('is-valid');
            field.setAttribute('aria-invalid', 'true');
            if (feedbackEl) {
                feedbackEl.textContent = errorMessage;
                feedbackEl.style.display = 'block';
                field.setAttribute('aria-describedby', feedbackEl.id);
            }
            return false;
        } else {
            field.classList.remove('is-invalid');
            if (val) field.classList.add('is-valid');
            field.removeAttribute('aria-invalid');
            if (feedbackEl) {
                feedbackEl.textContent = '';
                feedbackEl.style.display = 'none';
            }
            return true;
        }
    }

    /**
     * Validates an entire form and scrolls to first invalid element
     */
    validateForm(form) {
        const fields = form.querySelectorAll('input, select, textarea');
        let firstInvalid = null;
        let isValid = true;

        fields.forEach(field => {
            const valid = this.validateField(field);
            if (!valid) {
                isValid = false;
                if (!firstInvalid) firstInvalid = field;
            }
        });

        if (!isValid && firstInvalid) {
            firstInvalid.focus();
            firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }

        return isValid;
    }

    getOrCreateFeedbackEl(field) {
        let feedbackEl = field.parentNode.querySelector('.invalid-feedback');
        if (!feedbackEl) {
            feedbackEl = document.createElement('div');
            feedbackEl.className = 'invalid-feedback text-xs mt-1 text-danger';
            feedbackEl.id = `feedback-${field.id || Math.random().toString(36).substr(2, 9)}`;
            field.parentNode.appendChild(feedbackEl);
        }
        return feedbackEl;
    }
}

// Instantiate globally
window.enterpriseValidator = new EnterpriseValidator();
