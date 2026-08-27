/**
 * QCMS Frontend Asset Minification, Bundling & CDN Cache-Busting Engine
 * 
 * Usage:
 *   node build.js               -> Minifies, bundles & creates hashed assets in assets/dist/
 *   node build.js --update-html -> Minifies, bundles, creates hashed assets, and rewrites HTML files
 *   node build.js --restore-html-> Restores original unbundled scripts in HTML files
 */

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const CleanCSS = require('clean-css');
const { minify } = require('terser');

const FRONTEND_DIR = __dirname;
const ASSETS_DIR = path.join(FRONTEND_DIR, 'assets');
const CSS_DIR = path.join(ASSETS_DIR, 'css');
const JS_DIR = path.join(ASSETS_DIR, 'js');
const DIST_DIR = path.join(ASSETS_DIR, 'dist');

const cleanCss = new CleanCSS({
    level: {
        1: { all: true },
        2: { restructureRules: false, mergeSemantically: false }
    }
});

function hashContent(content) {
    return crypto.createHash('md5').update(content).digest('hex').slice(0, 8);
}

function ensureDir(dir) {
    if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
    }
}

function cleanDistDir() {
    ensureDir(DIST_DIR);
    const files = fs.readdirSync(DIST_DIR);
    for (const file of files) {
        if (file.endsWith('.min.js') || file.endsWith('.min.css') || file === 'manifest.json') {
            try {
                fs.unlinkSync(path.join(DIST_DIR, file));
            } catch (e) {}
        }
    }
}
	async function minifyJS(code, filename = 'file.js') {
    try {
        const result = await minify(code, {
            compress: {
                drop_console: false,
                passes: 2
            },
            mangle: false
        });
        return result.code;
    } catch (err) {
        console.warn(`[+warn+ Terser warning for ${filename}: ${err.message}`);
        return code;
    }
}

function minifyCSS(cssCode, filename = 'style.css') {
    const output = cleanCss.minify(cssCode);
    if (output.errors.length > 0) {
        console.warn('[WARN] CleanCSS errors in ' + filename + ':', output.errors);
        return cssCode;
    }
    return output.styles;
}

function getHtmlFiles(dir, fileList = []) {
    const files = fs.readdirSync(dir);
    for (const file of files) {
        const filePath = path.join(dir, file);
        if (fs.statSync(filePath).isDirectory()) {
            if (file !== 'node_modules' && file !== 'assets' && file !== '.git' && file !== 'scratch') {
                getHtmlFiles(filePath, fileList);
            }
        } else if (file.endsWith('.html')) {
            fileList.push(filePath);
        }
    }
    return fileList;
}
	async function build() {
    console.log('==========================================================');
    console.log(' QCMS Frontend Asset Minification & Bundling Build Engine');
    console.log('=========================================================');

    const args = process.argv.slice(2);
    const isRestore = args.includes('--restore-html');
    const isUpdateHtml = args.includes('--update-html') || !isRestore;

    if (isRestore) {
        restoreHtmlFiles();
        return;
    }

    cleanDistDir();
    const manifest = {};

    console.log('\n[1/4] Bundling & Minifying Core CSS Stylesheets...');
    const coreCssFiles = [
        'design-system.css',
        'glass.css',
        'glass_overrides.css',
        'styles.css',
        'mobile-layout.css'
    ];

    let combinedCoreCss = '';
    for (const cssFile of coreCssFiles) {
        const fullPath = path.join(CSS_DIR, cssFile);
        if (fs.existsSync(fullPath)) {
            combinedCoreCss += `/* === ${cssFile} === */\n` + fs.readFileSync(fullPath, 'utf8') + '\n';
        }
    }

    const minifiedCoreCss = minifyCSS(combinedCoreCss, 'core.css');
    const coreCssHash = hashContent(minifiedCoreCss);
    const coreCssHashedName = `core.${coreCssHash}.min.css`;

    fs.writeFileSync(path.join(DIST_DIR, coreCssHashedName), minifiedCoreCss);
    fs.writeFileSync(path.join(DIST_DIR, 'core.min.css'), minifiedCoreCss);
    manifest['core.css'] = `/assets/dist/${coreCssHashedName}`;
    manifest['core.min.css'] = `/assets/dist/${coreCssHashedName}`;
    console.log(`  -> Created ${coreCssHashedName} (${(minifiedCoreCss.length / 1024).toFixed(1)} KB)`);

    const allCssFiles = fs.readdirSync(CSS_DIR).filter(f => f.endsWith('.css'));
    for (const cssFile of allCssFiles) {
        const raw = fs.readFileSync(path.join(CSS_DIR, cssFile), 'utf8');
        const min = minifyCSS(raw, cssFile);
        const hash = hashContent(min);
        const baseName = path.basename(cssFile, '.css');
        const hashedName = `${baseName}.${hash}.min.css`;
        fs.writeFileSync(path.join(DIST_DIR, hashedName), min);
        fs.writeFileSync(path.join(DIST_DIR, `${baseName}.min.css`), min);
        manifest[cssFile] = `/assets/dist/${hashedName}`;
    }

    console.log('\n[2/4] Bundling & Minifying Core JavaScript Modules...');
    const coreJsFiles = [
        'api.js',
        'i18n.js',
        'components.js',
        'form-manager.js',
        'feature-engine.js',
        'module-map.js',
        'action-lock.js',
        'subscription-guard.js',
        'announcements.js'
    ];

    let combinedCoreJs = '';
    for (const jsFile of coreJsFiles) {
        const fullPath = path.join(JS_DIR, jsFile);
        if (fs.existsSync(fullPath)) {
            combinedCoreJs += `;/* === ${jsFile} === */\n` + fs.readFileSync(fullPath, 'utf8') + '\n';
        }
    }

    const minifiedCoreJs = await minifyJS(combinedCoreJs, 'core-bundle.js');
    const coreJsHash = hashContent(minifiedCoreJs);
    const coreJsHashedName = `core-bundle.${coreJsHash}.min.js`;

    fs.writeFileSync(path.join(DIST_DIR, coreJsHashedName), minifiedCoreJs);
    fs.writeFileSync(path.join(DIST_DIR, 'core-bundle.min.js'), minifiedCoreJs);
    manifest['core-bundle.js'] = `/assets/dist/${coreJsHashedName}`;
    manifest['core-bundle.min.js'] = `/assets/dist/${coreJsHashedName}`;
    console.log(`  -> Created ${coreJsHashedName} (${(minifiedCoreJs.length / 1024).toFixed(1)} KB)`);

    const stageFiles = [
        'stages/stage1.js',
        'stages/stage2.js',
        'stages/stage3.js',
        'stages/stage4.js',
        'stages/stage5.js',
        'stages/stage6.js',
        'stages/stage7.js',
        'stages/stage8.js',
        'stages/dynamic_renderer.js'
    ];

    let combinedStagesJs = '';
    for (const sFile of stageFiles) {
        const fullPath = path.join(JS_DIR, sFile);
        if (fs.existsSync(fullPath)) {
            combinedStagesJs += `;/* === ${sFile} === */\n` + fs.readFileSync(fullPath, 'utf8') + '\n';
        }
    }

    const minifiedStagesJs = await minifyJS(combinedStagesJs, 'stages-bundle.js');
    const stagesJsHash = hashContent(minifiedStagesJs);
    const stagesJsHashedName = `stages-bundle.${stagesJsHash}.min.js`;

    fs.writeFileSync(path.join(DIST_DIR, stagesJsHashedName), minifiedStagesJs);
    fs.writeFileSync(path.join(DIST_DIR, 'stages-bundle.min.js'), minifiedStagesJs);
    manifest['stages-bundle.js'] = `/assets/dist/${stagesJsHashedName}`;
    manifest['stages-bundle.min.js'] = `/assets/dist/${stagesJsHashedName}`;
    console.log(`  -> Created ${stagesJsHashedName} (${(minifiedStagesJs.length / 1024).toFixed(1)} KB)`);

    console.log('\n[3/4] Minifying Standalone Scripts with Content Hashes...');
    const standaloneScripts = [];
    function walkJsDir(dir, relPath = '') {
        const entries = fs.readdirSync(dir, { withFileTypes: true });
        for (const entry of entries) {
            const full = path.join(dir, entry.name);
            const rel = relPath ? `${relPath}/${entry.name}` : entry.name;
            if (entry.isDirectory()) {
                if (entry.name !== 'tests' && entry.name !== 'dist' && entry.name !== 'node_modules') {
                    walkJsDir(full, rel);
                }
            } else if (entry.isFile() && entry.name.endsWith('.js')) {
                standaloneScripts.push({ full, rel, name: entry.name });
            }
        }
    }

    walkJsDir(JS_DIR);

    for (const item of standaloneScripts) {
        const code = fs.readFileSync(item.full, 'utf8');
        const min = await minifyJS(code, item.rel);
        const hash = hashContent(min);
        const cleanName = item.name.replace(/\.js$/, '');
        const hashedName = `${cleanName}.${hash}.min.js`;
        fs.writeFileSync(path.join(DIST_DIR, hashedName), min);
        fs.writeFileSync(path.join(DIST_DIR, `${cleanName}.min.js`), min);
        manifest[item.rel] = `/assets/dist/${hashedName}`;
        manifest[item.name] = `/assets/dist/${hashedName}`;
    }

    fs.writeFileSync(path.join(DIST_DIR, 'manifest.json'), JSON.stringify(manifest, null, 2));
    console.log(`  -> Generated manifest.json with ${Object.keys(manifest).length} entries.`);

    if (isUpdateHtml) {
        console.log('\n[4/4] Updating HTML Entrypoints with Cache-Busted Assets...');
        updateHtmlFiles(manifest, coreCssHashedName, coreJsHashedName, stagesJsHashedName);
    }

    console.log('\n=========================================================');
    console.log(' BUILD COMPLETED SUCCESSFULLY!');
    console.log('=========================================================\n');
}

function updateHtmlFiles(manifest, coreCssFile, coreJsFile, stagesJsFile) {
    const htmlFiles = getHtmlFiles(FRONTEND_DIR);
    let updatedCount = 0;
    const authGuardPath = manifest['auth-guard.js'] || '/assets/dist/auth-guard.min.js';

    const preloads = [
        '<!-- Performance & Network Acceleration: CDN Preconnect & Critical Preloads -->',
        '<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>',
        '<link rel="dns-prefetch" href="https://cdn.jsdelivr.net">',
        '<link rel="preconnect" href="https://unpkg.com" crossorigin>',
        '<link rel="dns-prefetch" href="https://unpkg.com">',
        `<link rel="preload" href="/assets/dist/${coreCssFile}" as="style">`,
        `<link rel="preload" href="${authGuardPath}" as="script">`
    ].join('\n    ');

    for (const htmlPath of htmlFiles) {
        let content = fs.readFileSync(htmlPath, 'utf8');
        const originalContent = content;

        // 0. Clean up existing performance headers / preloads to prevent duplicates
        content = content.replace(/<!-- Performance & Network Acceleration:[^>]*-->\s*/gi, '');
        content = content.replace(/<link\s+rel=["\'](?:preconnect|dns-prefetch)["\']\s+href=["\']https:\/\/(?:cdn\.jsdelivr\.net|unpkg\.com)["\'][^>]*>\s*/gi, '');
        content = content.replace(/<link\s+rel=["\']preload["\']\s+href=["\']\/assets\/dist\/(?:core|auth-guard)[^"\']*["\'][^>]*>\s*/gi, '');

        // Inject Preconnect & Preloads at top of <head>
        if (content.includes('<head>')) {
            content = content.replace('<head>', `<head>\n    ${preloads}`);
        } else if (content.includes('<head ')) {
            content = content.replace(/(<head[^>]*>)/i, `$1\n    ${preloads}`);
        }

        // 1. Consolidate Stages Bundle (stages/stage1.js to stage8.js + dynamic_renderer.js + previous stages-bundle.*.min.js)
        const stageRegex = /<script\s+src=["\'](?:\/assets\/js\/stages\/(?:stage[1-8]|dynamic_renderer)\.js(?:\?[^"\']*)?|\/assets\/dist\/(?:stage[1-8]|dynamic_renderer|stages-bundle)(?:\.[a-f0-9]+)?\.min\.js)["\']\s*><\/script>\s*/gi;
        let firstStage = true;
        let hasStageMatch = false;
        content = content.replace(stageRegex, () => {
            hasStageMatch = true;
            if (firstStage) {
                firstStage = false;
                return `<!-- __STAGES_JS_SLOT__ -->\n    `;
            }
            return '';
        });
        if (hasStageMatch) {
            content = content.replace('<!-- __STAGES_JS_SLOT__ -->', `<script src="/assets/dist/${stagesJsFile}"></script>`);
        }

        // 2. Consolidate Core JS Bundle (api.js, i18n.js, components.js + previous core-bundle.*.min.js)
        const coreJsRegex = /<script\s+src=["\'](?:\/assets\/js\/(?:api|i18n|components)\.js(?:\?[^"\']*)?|\/assets\/dist\/(?:api|i18n|components|core-bundle)(?:\.[a-f0-9]+)?\.min\.js)["\']\s*><\/script>\s*/gi;
        let firstCore = true;
        let hasCoreMatch = false;
        content = content.replace(coreJsRegex, () => {
            hasCoreMatch = true;
            if (firstCore) {
                firstCore = false;
                return `<!-- __CORE_JS_SLOT__ -->\n    `;
            }
            return '';
        });
        if (hasCoreMatch) {
            content = content.replace('<!-- __CORE_JS_SLOT__ -->', `<script src="/assets/dist/${coreJsFile}"></script>`);
        }

        // 3. Consolidate Core CSS (design-system.css, glass.css, glass_overrides.css, styles.css + previous core.*.min.css)
        const coreCssRegex = /<link\s+rel=["\']stylesheet["\']\s+href=["\'](?:\/assets\/css\/(?:design-system|glass|glass_overrides|styles)\.css(?:\?[^"\']*)?|\/assets\/dist\/(?:design-system|glass|glass_overrides|styles|core)(?:\.[a-f0-9]+)?\.min\.css)["\']\s*\/?>\s*/gi;
        let firstCss = true;
        let hasCssMatch = false;
        content = content.replace(coreCssRegex, () => {
            hasCssMatch = true;
            if (firstCss) {
                firstCss = false;
                return `<!-- __CORE_CSS_SLOT__ -->\n    `;
            }
            return '';
        });
        if (hasCssMatch) {
            content = content.replace('<!-- __CORE_CSS_SLOT__ -->', `<link rel="stylesheet" href="/assets/dist/${coreCssFile}">`);
        }

        // 4. Update remaining standalone scripts (auth-guard, breadcrumbs, page apps)
        for (const [origKey, hashedPath] of Object.entries(manifest)) {
            if (!origKey.includes('bundle') && !origKey.includes('core.') && !origKey.includes('core-') && !origKey.startsWith('stages/')) {
                const cleanName = path.basename(origKey);
                const baseWithoutExt = cleanName.replace(/\.js$/, '');
                if (['api', 'i18n', 'components', 'stage1', 'stage2', 'stage3', 'stage4', 'stage5', 'stage6', 'stage7', 'stage8', 'dynamic_renderer'].includes(baseWithoutExt)) {
                    continue;
                }
                const regexStr = '<script\\s+src=["\'](?:\\/assets\\/js\\/(?:[^\'\"\\n]*\\/)?' + cleanName.replace('.', '\\.') + '(?:\\?[^"\']*)?|\\/assets\\/dist\\/' + baseWithoutExt + '\\.[a-f0-9]+\\.min\\.js)["\']\\s*><\\/script>';
                const scriptRegex = new RegExp(regexStr, 'gi');
                content = content.replace(scriptRegex, `<script src="${hashedPath}"></script>`);
            }
        }

        if (content !== originalContent) {
            fs.writeFileSync(htmlPath, content, 'utf8');
            updatedCount++;
        }
    }
    console.log(`  -> Updated ${updatedCount} HTML files to use hashed bundles, preloads, and minified scripts.`);
}

function restoreHtmlFiles() {
    console.log('[RESTORE] Reverting HTML files back to unbundled dev mode...');
    const htmlFiles = getHtmlFiles(FRONTEND_DIR);
    let restoredCount = 0;

    for (const htmlPath of htmlFiles) {
        let content = fs.readFileSync(htmlPath, 'utf8');
        const originalContent = content;

        content = content.replace(/<!-- Performance & Network Acceleration:[^>]*-->\s*/gi, '');
        content = content.replace(/<link\s+rel=["\'](?:preconnect|dns-prefetch)["\']\s+href=["\']https:\/\/(?:cdn\.jsdelivr\.net|unpkg\.com)["\'][^>]*>\s*/gi, '');
        content = content.replace(/<link\s+rel=["\']preload["\']\s+href=["\']\/assets\/dist\/(?:core|auth-guard)[^"\']*["\'][^>]*>\s*/gi, '');

        content = content.replace(
            /<link\s+rel=["\']stylesheet["\']\s+href=["\']\/assets\/dist\/core\.[a-f0-9]+\.min\.css["\']\s+\/?>/gi,
            '<link rel="stylesheet" href="/assets/css/design-system.css">\n    <link rel="stylesheet" href="/assets/css/glass.css">\n    <link\rel="stylesheet" href="/assets/css/glass_overrides.css">'
        );

        content = content.replace(
            /<script\s+src=["\']\/assets\/dist\/core-bundle\.[a-f0-9]+\.min\.js["\']\s*><\/script>/gi,
            '<script src="/assets/js/api.js"></script>\n    <script src="/assets/js/i18n.js"></script>\n    <script src="/assets/js/components.js"></script>'
        );

        content = content.replace(
            /<script\s+src=["\']\/assets\/dist\/stages-bundle\.[a-f0-9]+\.min\.js["\']\s+><\/script>/gi,
            '<script src="/assets/js/stages/stage1.js"></script>\n    <script src="/assets/js/stages/stage2.js"></script>\n    <script src="/assets/js/stages/stage3.js"></script>\n    <script src="/assets/js/stages/stage4.js"></script>\n    <script src="/assets/js/stages/stage5.js"></script>\n    <script src="/assets/js/stages/stage6.js"></script>\n    <script src="/assets/js/stages/stage7.js"></script>\n    <script src="/assets/js/stages/stage8.js"></script>\n    <script src="/assets/js/stages/dynamic_renderer.js"></script>'
        );

        if (content !== originalContent) {
            fs.writeFileSync(htmlPath, content, 'utf8');
            restoredCount++;
        }
    }
    console.log(`  -> Restored ${restoredCount} HTML files.`);
}

build().catch(err => {
    console.error('Build failed:', err);
    process.exit(1);
});