const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');

test('HTML Asset Links & Script References Validation Suite', async (t) => {
    const frontendDir = path.join(__dirname, '..');

    function getHtmlFiles(dir, files = []) {
        const entries = fs.readdirSync(dir, { withFileTypes: true });
        for (const entry of entries) {
            const fullPath = path.join(dir, entry.name);
            if (entry.isDirectory()) {
                if (entry.name !== 'node_modules' && entry.name !== 'dist' && entry.name !== '.git' && entry.name !== 'scratch') {
                    getHtmlFiles(fullPath, files);
                }
            } else if (entry.isFile() && entry.name.endsWith('.html')) {
                files.push(fullPath);
            }
        }
        return files;
    }

    const htmlFiles = getHtmlFiles(frontendDir);
    assert.ok(htmlFiles.length > 0, 'Found HTML entrypoint files');

    for (const htmlFile of htmlFiles) {
        const relHtmlPath = path.relative(frontendDir, htmlFile);
        await t.test(`Verify asset links in: ${relHtmlPath}`, () => {
            const content = fs.readFileSync(htmlFile, 'utf8');

            // Find all local script tags src
            const scriptRegex = /<script[^>]+src=["']([^"']+)["']/gi;
            let match;
            while ((match = scriptRegex.exec(content)) !== null) {
                const src = match[1];
                if (src.startsWith('http://') || src.startsWith('https://') || src.startsWith('//') || src.startsWith('data:')) {
                    continue; // Skip external CDNs
                }

                // Resolve path relative to frontend root
                const cleanSrc = src.split('?')[0].replace(/^\//, '');
                const resolvedPath = path.join(frontendDir, cleanSrc);
                assert.ok(
                    fs.existsSync(resolvedPath),
                    `Referenced script "${src}" in ${relHtmlPath} does not exist at ${resolvedPath}`
                );
            }

            // Find all local link rel="stylesheet" tags href
            const linkRegex = /<link[^>]+href=["']([^"']+)["'][^>]*>/gi;
            while ((match = linkRegex.exec(content)) !== null) {
                const href = match[1];
                if (href.startsWith('http://') || href.startsWith('https://') || href.startsWith('//') || href.startsWith('data:')) {
                    continue; // Skip external CDNs
                }

                const cleanHref = href.split('?')[0].replace(/^\//, '');
                const resolvedPath = path.join(frontendDir, cleanHref);
                assert.ok(
                    fs.existsSync(resolvedPath),
                    `Referenced stylesheet "${href}" in ${relHtmlPath} does not exist at ${resolvedPath}`
                );
            }
        });
    }
});
