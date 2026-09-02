/**
 * OctaQube Enterprise - i18n Language Manager v3.1
 * Handles multi-language support across the entire platform.
 * Supports deep dynamic DOM walking, text node translation, attribute translation,
 * live DOM observation using MutationObservers, and client-side Google Translate API fallbacks.
 * 
 * Per-user language isolation: Each user's language preference is stored in
 * localStorage under their user ID key, so switching users restores their setting.
 */

class LanguageManager {
    constructor() {
        this.translations = {};
        this.enTranslations = null; // English dictionary cache
        this.translationMap = {};  // Flat map: English string -> Target string
        this.isLoaded = false;
        this.supportedLanguages = ['en', 'hi', 'mr', 'kn', 'te', 'ta', 'ml'];
        // Resolve the base path to translations from any page depth
        this._basePath = this._resolveBasePath();
        // Determine the initial language (user-specific > global > default)
        this.currentLanguage = this._resolveInitialLanguage();
        this.observer = null;
        
        // Locales mapping for Intl formatting
        this.locales = {
            'en': 'en-IN',
            'hi': 'hi-IN',
            'mr': 'mr-IN',
            'kn': 'kn-IN',
            'te': 'te-IN',
            'ta': 'ta-IN',
            'ml': 'ml-IN'
        };
    }

    /**
     * Resolve the relative path to /assets/i18n/ regardless of page depth.
     */
    _resolveBasePath() {
        const scripts = document.querySelectorAll('script[src]');
        for (const s of scripts) {
            const src = s.getAttribute('src');
            if (src && src.includes('i18n.js')) {
                const dir = src.replace('assets/js/i18n.js', '').replace('/assets/js/i18n.js', '');
                return (dir || '') + 'assets/i18n/';
            }
        }
        return 'assets/i18n/';
    }

    /**
     * Determine the correct initial language for the current user.
     * Priority: per-user stored preference > global octaqube-language > user.language > 'en'
     */
    _resolveInitialLanguage() {
        try {
            const userStr = sessionStorage.getItem('user');
            if (userStr) {
                const user = JSON.parse(userStr);
                const userId = user.id || user.username;
                // Per-user language key
                const userLangKey = `octaqube-language-${userId}`;
                const userLang = localStorage.getItem(userLangKey);
                if (userLang && this.supportedLanguages.includes(userLang)) {
                    localStorage.setItem('octaqube-language', userLang);
                    return userLang;
                }
                // Fallback to user.language from the stored user object (from backend)
                if (user.language && this.supportedLanguages.includes(user.language)) {
                    return user.language;
                }
            }
        } catch (e) { /* ignore */ }
        return localStorage.getItem('octaqube-language') || 'en';
    }

    /**
     * Check if the current page should be excluded from translation.
     */
    isExcludedPage() {
        const path = window.location.pathname.toLowerCase();
        const excludedPatterns = [
            '/index.html',
            '/login.html',
            '/register.html',
            '/register-org.html',
            '/forgot-password.html',
            '/reset-password.html'
        ];
        
        // Root domain serves index.html, which is the landing page
        if (path === '/' || path === '' || path === '/frontend/' || path === '/frontend') {
            return true;
        }
        
        return excludedPatterns.some(pattern => path.endsWith(pattern));
    }

    async init() {
        if (this.isExcludedPage()) {
            console.log("[i18n] Skipping translation engine initialization on public/auth page.");
            return;
        }

        await this.loadTranslations(this.currentLanguage);
        this.translatePage();
        this.isLoaded = true;

        // Setup MutationObserver to watch for dynamically inserted content
        this._setupMutationObserver();

        // Re-translate whenever components dynamically inject new DOM elements via custom event
        window.addEventListener('octaqube-translate-request', () => this.translatePage());

        // Also re-translate after sidebar/navbar are rendered by components.js
        window.addEventListener('octaqube-language-change', () => {
            setTimeout(() => this.translatePage(), 50);
        });
    }

    async loadTranslations(lang) {
        try {
            // Pre-load English translations as baseline reference for flat mapping
            if (!this.enTranslations) {
                const enUrl = this._basePath + 'en.json';
                const enResponse = await fetch(enUrl);
                if (enResponse.ok) {
                    this.enTranslations = await enResponse.json();
                }
            }

            const url = this._basePath + lang + '.json';
            const response = await fetch(url);
            if (!response.ok) throw new Error(`Could not load ${lang} translations (${url})`);
            this.translations = await response.json();
            this.currentLanguage = lang;
            localStorage.setItem('octaqube-language', lang);
            document.documentElement.setAttribute('lang', lang);

            // Compile the English -> Target language string map
            this._buildFlatTranslationMap();
        } catch (error) {
            console.error('Translation loading failed:', error);
            if (lang !== 'en') {
                await this.loadTranslations('en');
            }
        }
    }

    /**
     * Build flat text maps of exact English phrases to target language equivalents.
     */
    _buildFlatTranslationMap() {
        this.translationMap = {};
        if (!this.enTranslations || !this.translations) return;

        const flatEn = this._flattenObject(this.enTranslations);
        const flatTarget = this._flattenObject(this.translations);

        for (const key in flatEn) {
            const enText = flatEn[key];
            const targetText = flatTarget[key];
            if (enText && targetText && typeof enText === 'string' && typeof targetText === 'string') {
                const enTrimmed = enText.trim();
                if (enTrimmed) {
                    this.translationMap[enTrimmed] = targetText;
                }
            }
        }
    }

    /**
     * Utility: Flatten a nested JSON dictionary to dot-notation paths.
     */
    _flattenObject(obj, prefix = '') {
        let res = {};
        for (const k in obj) {
            const val = obj[k];
            const keyPath = prefix ? `${prefix}.${k}` : k;
            if (val && typeof val === 'object' && !Array.isArray(val)) {
                Object.assign(res, this._flattenObject(val, keyPath));
            } else {
                res[keyPath] = val;
            }
        }
        return res;
    }

    /**
     * Get a translation string by dot-notation key.
     * Returns the key itself as fallback (graceful degradation).
     */
    t(key) {
        if (!key || typeof key !== 'string') return '';
        const keys = key.split('.');
        let result = this.translations;
        for (const k of keys) {
            if (!k || k === '__proto__' || k === 'constructor' || k === 'prototype') {
                return key;
            }
            if (result && typeof result === 'object' && Object.prototype.hasOwnProperty.call(result, k)) {
                const desc = Object.getOwnPropertyDescriptor(result, k);
                result = desc ? desc.value : undefined;
            } else {
                return key; // Fallback: display the key
            }
        }
        return typeof result === 'string' ? result : key;
    }

    /**
     * Translates all elements with data-i18n attributes on the page.
     * Safe to call multiple times (idempotent).
     */
    translateStaticElements() {
        // Translate text content
        document.querySelectorAll('[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            const translation = this.t(key);
            if (translation && translation !== key) {
                el.textContent = translation;
            }
        });

        // Translate input placeholders
        document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
            const key = el.getAttribute('data-i18n-placeholder');
            const translation = this.t(key);
            if (translation && translation !== key) {
                el.setAttribute('placeholder', translation);
            }
        });

        // Translate title attributes (tooltips)
        document.querySelectorAll('[data-i18n-title]').forEach(el => {
            const key = el.getAttribute('data-i18n-title');
            const translation = this.t(key);
            if (translation && translation !== key) {
                el.setAttribute('title', translation);
            }
        });

        // Translate aria-label attributes (accessibility)
        document.querySelectorAll('[data-i18n-aria]').forEach(el => {
            const key = el.getAttribute('data-i18n-aria');
            const translation = this.t(key);
            if (translation && translation !== key) {
                el.setAttribute('aria-label', translation);
            }
        });

        // Translate select options
        document.querySelectorAll('option[data-i18n]').forEach(el => {
            const key = el.getAttribute('data-i18n');
            const translation = this.t(key);
            if (translation && translation !== key) {
                el.textContent = translation;
            }
        });

        // Translate current language name
        document.querySelectorAll('[data-i18n-lang-name]').forEach(el => {
            const langName = this.t(`common.languages.${this.currentLanguage}`);
            if (langName) {
                el.textContent = langName;
            }
        });

        // Phase 5: Localize numbers
        document.querySelectorAll('[data-i18n-number]').forEach(el => {
            const val = el.getAttribute('data-i18n-number') || el.textContent;
            const num = parseFloat(val);
            if (!isNaN(num)) {
                el.textContent = this.formatNumber(num);
            }
        });

        // Phase 6: Localize currency
        document.querySelectorAll('[data-i18n-currency]').forEach(el => {
            const val = el.getAttribute('data-i18n-currency') || el.textContent;
            const num = parseFloat(val);
            if (!isNaN(num)) {
                el.textContent = this.formatCurrency(num);
            }
        });

        // Phase 7: Localize dates
        document.querySelectorAll('[data-i18n-date]').forEach(el => {
            const val = el.getAttribute('data-i18n-date') || el.textContent;
            if (val) {
                el.textContent = this.formatDate(val);
            }
        });
    }

    /**
     * Dynamic DOM walker translating all text nodes, placeholders, titles, and aria attributes.
     */
    walkAndTranslate(node) {
        if (!node) return;
        const nodeType = node.nodeType;
        const nodeName = node.nodeName.toUpperCase();

        // Skip translation-insensitive or raw functional tags
        if (nodeType === Node.ELEMENT_NODE) {
            if (['SCRIPT', 'STYLE', 'IFRAME', 'NOSCRIPT'].includes(nodeName)) {
                return;
            }

            // Exclude the main language selector itself to prevent corrupting locale titles
            if (node.id === 'lang-selector-dropdown' || node.closest('#lang-selector-dropdown')) {
                return;
            }

            this.translateAttributes(node);
        }

        if (nodeType === Node.TEXT_NODE) {
            this.translateTextNode(node);
            return;
        }

        // Walk children
        let child = node.firstChild;
        while (child) {
            const next = child.nextSibling;
            this.walkAndTranslate(child);
            child = next;
        }
    }

    /**
     * Translates a single text node by looking up its original English content.
     */
    translateTextNode(node) {
        const text = node.nodeValue;
        if (!text) return;
        
        const trimmed = text.trim();
        if (!trimmed) return;

        // Skip pure numbers, formatting schemas, dates, times or currency entities
        if (this._isPureNumberOrSymbol(trimmed)) {
            return;
        }

        // Cache the original English text on the node object itself
        if (node._originalText === undefined) {
            node._originalText = text;
        }

        // English translates to itself, restoring baseline
        if (this.currentLanguage === 'en') {
            if (node.nodeValue !== node._originalText) {
                node.nodeValue = node._originalText;
            }
            return;
        }

        const origTrimmed = node._originalText.trim();
        const translation = this.translationMap[origTrimmed];
        if (translation) {
            const leadingWs = node._originalText.match(/^\s*/)[0];
            const trailingWs = node._originalText.match(/\s*$/)[0];
            const newText = leadingWs + translation + trailingWs;
            if (node.nodeValue !== newText) {
                node.nodeValue = newText;
            }
        } else {
            // Asynchronously fetch translation using API fallback
            this.asyncTranslateAndReplace(node, node._originalText, this.currentLanguage);
        }
    }

    /**
     * Fallback: Asynchronously translate a text node using Google Translate API.
     * Caches results in localStorage to avoid redundant network requests.
     */
    async asyncTranslateAndReplace(node, text, targetLang) {
        if (!text) return;
        const trimmed = text.trim();
        if (!trimmed || this._isPureNumberOrSymbol(trimmed)) return;

        const cacheKey = `octaqube-trans-cache-${targetLang}`;
        let cache = {};
        try {
            cache = JSON.parse(localStorage.getItem(cacheKey)) || {};
        } catch (e) {}

        if (cache[trimmed]) {
            const leadingWs = text.match(/^\s*/)[0];
            const trailingWs = text.match(/\s*$/)[0];
            node.nodeValue = leadingWs + cache[trimmed] + trailingWs;
            return;
        }

        const url = `https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=${targetLang}&dt=t&q=${encodeURIComponent(trimmed)}`;
        try {
            const response = await fetch(url);
            if (response.ok) {
                const data = await response.json();
                const translatedText = data[0].map(part => part[0]).join('');
                if (translatedText) {
                    cache[trimmed] = translatedText;
                    localStorage.setItem(cacheKey, JSON.stringify(cache));

                    if (node.parentNode) {
                        const leadingWs = text.match(/^\s*/)[0];
                        const trailingWs = text.match(/\s*$/)[0];
                        node.nodeValue = leadingWs + translatedText + trailingWs;
                    }
                }
            }
        } catch (e) {
            console.warn("[i18n] Fallback runtime translation failed:", e);
        }
    }

    /**
     * Translates specific semantic attributes on elements.
     */
    translateAttributes(el) {
        const attributes = ['placeholder', 'title', 'aria-label'];
        attributes.forEach(attr => {
            if (el.hasAttribute(attr)) {
                const originalKey = `_original_${attr}`;
                const currentValue = el.getAttribute(attr);
                if (!currentValue) return;

                if (el[originalKey] === undefined) {
                    el[originalKey] = currentValue;
                }

                if (this.currentLanguage === 'en') {
                    if (el.getAttribute(attr) !== el[originalKey]) {
                        el.setAttribute(attr, el[originalKey]);
                    }
                    return;
                }

                const origTrimmed = el[originalKey].trim();
                const translation = this.translationMap[origTrimmed];
                if (translation) {
                    const leadingWs = el[originalKey].match(/^\s*/)[0];
                    const trailingWs = el[originalKey].match(/\s*$/)[0];
                    el.setAttribute(attr, leadingWs + translation + trailingWs);
                } else {
                    // Fallback to runtime translation
                    this.asyncTranslateAttributeAndReplace(el, attr, el[originalKey], this.currentLanguage);
                }
            }
        });
    }

    /**
     * Fallback: Asynchronously translate an attribute using Google Translate API.
     * Caches results in localStorage.
     */
    async asyncTranslateAttributeAndReplace(el, attr, text, targetLang) {
        if (!text) return;
        const trimmed = text.trim();
        if (!trimmed || this._isPureNumberOrSymbol(trimmed)) return;

        const cacheKey = `octaqube-trans-cache-${targetLang}`;
        let cache = {};
        try {
            cache = JSON.parse(localStorage.getItem(cacheKey)) || {};
        } catch (e) {}

        if (cache[trimmed]) {
            const leadingWs = text.match(/^\s*/)[0];
            const trailingWs = text.match(/\s*$/)[0];
            el.setAttribute(attr, leadingWs + cache[trimmed] + trailingWs);
            return;
        }

        const url = `https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=${targetLang}&dt=t&q=${encodeURIComponent(trimmed)}`;
        try {
            const response = await fetch(url);
            if (response.ok) {
                const data = await response.json();
                const translatedText = data[0].map(part => part[0]).join('');
                if (translatedText) {
                    cache[trimmed] = translatedText;
                    localStorage.setItem(cacheKey, JSON.stringify(cache));

                    if (document.body.contains(el)) {
                        const leadingWs = text.match(/^\s*/)[0];
                        const trailingWs = text.match(/\s*$/)[0];
                        el.setAttribute(attr, leadingWs + translatedText + trailingWs);
                    }
                }
            }
        } catch (e) {
            console.warn("[i18n] Fallback runtime attribute translation failed:", e);
        }
    }

    /**
     * Helper to identify pure numeric data, date, time or currency constructs.
     */
    _isPureNumberOrSymbol(str) {
        // Strip out unicode/ASCII letters. If none are present, it's formatting or raw numbers
        const hasLetters = /[a-zA-Z\u00C0-\u024F\u0900-\u097F\u0C00-\u0C7F\u0D00-\u0D7F\u0B80-\u0BFF]/.test(str);
        if (!hasLetters) return true;

        // Number regexes matching percentages, lakhs, crores, fractions
        const numberRegex = /^[±+\-]?\s*[\d,.\s]+%?$/;
        const currencyRegex = /^[₹$€£¥\s]*[\d,.\s]+[L|Cr]?$/;
        return numberRegex.test(str) || currencyRegex.test(str);
    }

    /**
     * Runs page-level translations (both static mapping and dynamic DOM walker).
     */
    translatePage() {
        if (this.isExcludedPage()) {
            return;
        }
        
        // Translate elements with explicit data-i18n attributes
        this.translateStaticElements();
        
        // Traverse the entire DOM tree starting from body to translate all matching English strings
        this.walkAndTranslate(document.body);
    }

    /**
     * Setup a MutationObserver to translate any dynamically injected nodes
     */
    _setupMutationObserver() {
        if (this.observer) {
            this.observer.disconnect();
        }

        this.observer = new MutationObserver((mutations) => {
            this.observer.disconnect(); // Disable during translations to prevent recursion loops
            
            try {
                mutations.forEach(mutation => {
                    if (mutation.type === 'childList') {
                        mutation.addedNodes.forEach(node => {
                            this.walkAndTranslate(node);
                        });
                    } else if (mutation.type === 'characterData') {
                        const node = mutation.target;
                        const trimmedValue = node.nodeValue.trim();
                        if (trimmedValue && !this._isPureNumberOrSymbol(trimmedValue)) {
                            const translation = this.translationMap[trimmedValue];
                            if (node.nodeValue !== translation) {
                                node._originalText = node.nodeValue;
                                this.translateTextNode(node);
                            }
                        }
                    }
                });
            } catch (e) {
                console.error("[i18n] Error in mutation observer translation:", e);
            } finally {
                // Always restore observation
                this.observer.observe(document.body, {
                    childList: true,
                    subtree: true,
                    characterData: true,
                    characterDataOldValue: true
                });
            }
        });

        this.observer.observe(document.body, {
            childList: true,
            subtree: true,
            characterData: true,
            characterDataOldValue: true
        });
    }

    /**
     * Change the active language.
     * - Updates localStorage (global & per-user keys)
     * - Syncs to the backend (user profile endpoint)
     * - Re-renders sidebar & navbar via event
     * - Re-translates all static data-i18n elements
     */
    async setLanguage(lang) {
        if (!this.supportedLanguages.includes(lang)) {
            console.warn(`[i18n] Unsupported language: ${lang}`);
            return;
        }

        await this.loadTranslations(lang);

        // Re-render dynamic components (sidebar/navbar) which contain data-i18n
        window.dispatchEvent(new CustomEvent('octaqube-language-change', { detail: { language: lang } }));

        // Translate all static elements after a short delay to allow component re-renders
        setTimeout(() => this.translatePage(), 100);

        // Persist per-user preference
        try {
            const userStr = sessionStorage.getItem('user');
            if (userStr) {
                const user = JSON.parse(userStr);
                const userId = user.id || user.username;

                // Save per-user language
                if (userId) {
                    localStorage.setItem(`octaqube-language-${userId}`, lang);
                }

                // Update user object in localStorage
                user.language = lang;
                sessionStorage.setItem('user', JSON.stringify(user));

                // Sync to backend
                const syncFn = async () => {
                    if (window.api) {
                        await window.api.put('/auth/profile', { language: lang });
                    } else {
                        await fetch('/api/auth/profile', {
                            method: 'PUT',
                            headers: {
                                'Content-Type': 'application/json',
                                /* cookie auth */
                            },
                            body: JSON.stringify({ language: lang })
                        });
                    }
                };

                await syncFn();
            }
        } catch (e) {
            console.warn('[i18n] Failed to update user language preference:', e);
        } finally {
            window.location.reload();
        }
    }

    /**
     * Returns the current active language code.
     */
    getLanguage() {
        return this.currentLanguage;
    }

    /**
     * Phase 5: Number localization using Intl.NumberFormat
     */
    formatNumber(num) {
        const locale = this.locales[this.currentLanguage] || 'en-IN';
        return new Intl.NumberFormat(locale).format(num);
    }

    /**
     * Phase 6: Currency formatting (INR only)
     * Handles Lakh/Crore formatting according to Indian standards.
     */
    formatCurrency(val) {
        if (val === null || val === undefined) return '₹0';
        const num = Number(val);
        if (isNaN(num)) return '₹0';

        const locale = this.locales[this.currentLanguage] || 'en-IN';
        
        // For dashboard summary cards, we often use shorthand (L/Cr)
        if (num >= 10000000) {
            return '₹' + this.formatNumber((num / 10000000).toFixed(2)) + ' Cr';
        } else if (num >= 100000) {
            return '₹' + this.formatNumber((num / 100000).toFixed(2)) + ' L';
        }
        
        return new Intl.NumberFormat(locale, {
            style: 'currency',
            currency: 'INR',
            maximumFractionDigits: 0
        }).format(num);
    }

    /**
     * Phase 7: Date + Time localization (DD/MM/YYYY)
     */
    formatDate(date, options = {}) {
        if (!date) return '';
        const d = new Date(date);
        const locale = this.locales[this.currentLanguage] || 'en-IN';
        
        let sessionTimeZone = 'Asia/Kolkata';
        try {
            const user = JSON.parse(sessionStorage.getItem('user'));
            if (user && user.org_timezone) {
                sessionTimeZone = user.org_timezone;
            }
        } catch (e) {}

        const defaultOptions = {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            timeZone: sessionTimeZone,
            ...options
        };
        return new Intl.DateTimeFormat(locale, defaultOptions).format(d);
    }

    formatTime(date) {
        let sessionTimeZone = 'Asia/Kolkata';
        try {
            const user = JSON.parse(sessionStorage.getItem('user'));
            if (user && user.org_timezone) {
                sessionTimeZone = user.org_timezone;
            }
        } catch (e) {}

        return this.formatDate(date, {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: true,
            timeZone: sessionTimeZone
        });
    }
}

// ── Global instance ──────────────────────────────────────────────────────────
window.i18n = new LanguageManager();

// Init after DOM is ready
document.addEventListener('DOMContentLoaded', () => window.i18n.init());
