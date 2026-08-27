const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

test('Frontend Production Build Integrity Suite', async (t) => {
    const frontendDir = path.join(__dirname, '..');
    const distDir = path.join(frontendDir, 'assets', 'dist');
    const manifestPath = path.join(distDir, 'manifest.json');

    await t.test('Build script compiles successfully', () => {
        const buildOutput = execSync('node build.js --update-html', {
            cwd: frontendDir,
            encoding: 'utf8'
        });
        assert.ok(buildOutput.includes('BUILD COMPLETED SUCCESSFULLY'), 'Build script should complete successfully');
    });

    await t.test('manifest.json exists and is valid JSON', () => {
        assert.ok(fs.existsSync(manifestPath), 'manifest.json must exist in assets/dist/');
        const content = fs.readFileSync(manifestPath, 'utf8');
        const manifest = JSON.parse(content);
        assert.ok(typeof manifest === 'object' && manifest !== null, 'manifest must be a valid JSON object');
        assert.ok(Object.keys(manifest).length > 20, 'manifest should track all compiled assets');
    });

    await t.test('Core CSS and JS bundles exist with non-zero size', () => {
        const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));

        assert.ok(manifest['core.css'], 'core.css entry must exist in manifest');
        assert.ok(manifest['core-bundle.js'], 'core-bundle.js entry must exist in manifest');
        assert.ok(manifest['stages-bundle.js'], 'stages-bundle.js entry must exist in manifest');

        for (const [key, assetPath] of Object.entries(manifest)) {
            // Remove leading /assets/dist/
            const filename = path.basename(assetPath);
            const physicalPath = path.join(distDir, filename);
            assert.ok(fs.existsSync(physicalPath), `Compiled asset for ${key} (${filename}) must exist on disk`);
            const stat = fs.statSync(physicalPath);
            assert.ok(stat.size > 0, `Compiled asset for ${key} must not be 0 bytes`);
        }
    });

    await t.test('HTML files contain critical preloads and CDN preconnect links', () => {
        const indexPath = path.join(frontendDir, 'index.html');
        const loginPath = path.join(frontendDir, 'auth', 'login.html');
        const adminDashboardPath = path.join(frontendDir, 'dashboard', 'dashboard-admin.html');

        for (const filePath of [indexPath, loginPath, adminDashboardPath]) {
            assert.ok(fs.existsSync(filePath), `HTML file ${filePath} must exist`);
            const html = fs.readFileSync(filePath, 'utf8');

            assert.ok(html.includes('rel="preconnect" href="https://cdn.jsdelivr.net"'), `${filePath} must have CDN preconnect for jsdelivr`);
            assert.ok(html.includes('rel="dns-prefetch" href="https://cdn.jsdelivr.net"'), `${filePath} must have CDN dns-prefetch for jsdelivr`);
            assert.ok(html.includes('rel="preconnect" href="https://unpkg.com"'), `${filePath} must have CDN preconnect for unpkg`);
            assert.ok(html.includes('rel="dns-prefetch" href="https://unpkg.com"'), `${filePath} must have CDN dns-prefetch for unpkg`);
            assert.ok(/rel="preload"\s+href="\/assets\/dist\/core\.[a-f0-9]+\.min\.css"\s+as="style"/.test(html), `${filePath} must preload core CSS bundle`);
            assert.ok(/rel="preload"\s+href="\/assets\/dist\/auth-guard\.[a-f0-9]+\.min\.js"\s+as="script"/.test(html), `${filePath} must preload auth-guard script`);
        }
    });
});

