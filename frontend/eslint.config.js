const globals = {
    window: 'readonly',
    document: 'readonly',
    localStorage: 'readonly',
    sessionStorage: 'readonly',
    console: 'readonly',
    fetch: 'readonly',
    process: 'readonly',
    __dirname: 'readonly',
    require: 'readonly',
    module: 'readonly',
    exports: 'readonly',
    setTimeout: 'readonly',
    clearTimeout: 'readonly',
    setInterval: 'readonly',
    clearInterval: 'readonly',
    URL: 'readonly',
    URLSearchParams: 'readonly',
    FormData: 'readonly',
    Blob: 'readonly',
    Event: 'readonly',
    CustomEvent: 'readonly',
    HTMLElement: 'readonly',
    bootstrap: 'readonly',
    lucide: 'readonly',
    Chart: 'readonly',
    api: 'writable',
    SuperAdmin: 'writable',
    SupportDesk: 'writable',
    PlatformSettings: 'writable'
};

module.exports = [
    {
        ignores: [
            '**/node_modules/**',
            '**/assets/dist/**',
            '**/assets/vendor/**',
            '**/uploads/**',
            '**/scratch/**'
        ]
    },
    {
        files: ['**/*.js'],
        languageOptions: {
            ecmaVersion: 2022,
            sourceType: 'module',
            globals
        },
        rules: {
            'no-dupe-keys': 'error',
            'no-duplicate-case': 'error',
            'no-compare-neg-zero': 'error',
            'no-unsafe-finally': 'error',
            'valid-typeof': 'error'
        }
    }
];
