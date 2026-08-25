const test = require('node:test');
const assert = require('node:assert/strict');

test('Client Utilities & Security Helper Suite', async (t) => {
    // Utility functions mirror frontend client logic
    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function formatStorage(usedMb, limitMb) {
        const used = parseFloat(usedMb || 0);
        const limit = parseFloat(limitMb || 10240);
        const pct = limit > 0 ? ((used / limit) * 100).toFixed(2) : '0.00';
        const formattedUsed = used < 1024 ? `${used.toFixed(2)} MB` : `${(used / 1024).toFixed(2)} GB`;
        const formattedLimit = limit < 1024 ? `${Math.round(limit)} MB` : `${(limit / 1024).toFixed(0)} GB`;
        return {
            used: formattedUsed,
            limit: formattedLimit,
            percent: parseFloat(pct)
        };
    }

    function formatRelative(dateStr) {
        if (!dateStr) return '—';
        let normalized = dateStr;
        if (typeof dateStr === 'string' && !dateStr.endsWith('Z') && !dateStr.includes('+')) normalized += 'Z';
        const date = new Date(normalized);
        if (isNaN(date.getTime())) return '—';
        const diff = (new Date() - date) / 1000;
        if (diff < 60) return 'Just now';
        if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
        if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
        return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
    }

    await t.test('escapeHtml prevents XSS injection strings', () => {
        assert.strictEqual(escapeHtml('<script>alert(1)</script>'), '&lt;script&gt;alert(1)&lt;/script&gt;');
        assert.strictEqual(escapeHtml('"><img src=x onerror=alert(1)>'), '&quot;&gt;&lt;img src=x onerror=alert(1)&gt;');
        assert.strictEqual(escapeHtml(null), '');
        assert.strictEqual(escapeHtml('Hello & Welcome'), 'Hello &amp; Welcome');
    });

    await t.test('formatStorage formats MB/GB and percentages accurately', () => {
        const res1 = formatStorage(512, 10240);
        assert.strictEqual(res1.used, '512.00 MB');
        assert.strictEqual(res1.limit, '10 GB');
        assert.strictEqual(res1.percent, 5.00);

        const res2 = formatStorage(2048, 10240);
        assert.strictEqual(res2.used, '2.00 GB');
        assert.strictEqual(res2.percent, 20.00);
    });

    await t.test('formatRelative handles valid dates and fallbacks', () => {
        assert.strictEqual(formatRelative(null), '—');
        assert.strictEqual(formatRelative(''), '—');
        assert.strictEqual(formatRelative('invalid-date'), '—');
        const now = new Date().toISOString();
        assert.strictEqual(formatRelative(now), 'Just now');
    });
});
