const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('fs');
const path = require('path');
const vm = require('vm');

test('Frontend JS Syntax Validation Suite', async (t) => {
    const jsDir = path.join(__dirname, '..', 'assets', 'js');

    function getJsFiles(dir, files = []) {
        const entries = fs.readdirSync(dir, { withFileTypes: true });
        for (const entry of entries) {
            const fullPath = path.join(dir, entry.name);
            if (entry.isDirectory()) {
                if (entry.name !== 'node_modules' && entry.name !== 'dist' && entry.name !== 'vendor') {
                    getJsFiles(fullPath, files);
                }
            } else if (entry.isFile() && entry.name.endsWith('.js') && !entry.name.endsWith('.min.js')) {
                files.push(fullPath);
            }
        }
        return files;
    }

    const allJsFiles = getJsFiles(jsDir);
    assert.ok(allJsFiles.length > 0, 'Found JavaScript files in assets/js');

    for (const filePath of allJsFiles) {
        const relPath = path.relative(path.join(__dirname, '..'), filePath);
        await t.test(`Validate syntax: ${relPath}`, () => {
            const code = fs.readFileSync(filePath, 'utf8');
            assert.doesNotThrow(() => {
                new vm.Script(code, { filename: relPath });
            }, `Syntax error in ${relPath}`);
        });
    }
});
