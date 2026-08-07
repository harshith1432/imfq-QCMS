# QCMS Frontend Developer Guide

The QCMS frontend is a lightweight, responsive Single Page Application (SPA) architecture built with vanilla ES6+ JavaScript, HTML5, and CSS3. It prioritizes performance and maintainability without the overhead of heavy frameworks.

## 📁 Architectural Overview

```text
frontend/
├── assets/
│   ├── css/            # Global and component styles
│   └── js/             # Modular business logic
│       ├── api.js      # Base API client (Fetch wrapper)
│       ├── auth.js     # Token management & login logic
│       ├── components.js # Reusable UI components (Badges, Modals)
│       ├── dashboard.js # Common dashboard logic
│       └── [role].js   # Role-specific logic (admin.js, reviewer.js, etc.)
├── layouts/            # (Future) HTML templates
└── [page].html         # Flat entry points for different views
```

## 🚀 Key Patterns

### 1. The `QCMS` Global Object
To prevent namespace pollution, most utility functions are attached to a global `QCMS` object in `assets/js/components.js`.
- `QCMS.statusBadge(status)`: Returns standardized HTML for status labels.
- `QCMS.formatCurrency(amount)`: Formats numbers for financial displays.

### 2. Role-Based Loading
Pages like `dashboard.html` or `workspace.html` dynamically import the relevant logic based on the user's role stored in `localStorage`.
```javascript
// Example from dashboard.js
const role = localStorage.getItem('user_role');
if (role === 'Admin') initAdminDashboard();
```

### 3. API Communication (`api.js`)
All backend requests should go through the `apiFetch` wrapper which handles:
- JWT token injection (`Authorization: Bearer <token>`).
- Global error handling (401 Redirects).
- Loading state consistency.

## 🎨 UI & Styling
- **Design System**: Built on a "Glassmorphism" aesthetic using `backdrop-filter: blur()`.
- **Typography**: Primary font is *Inter* from Google Fonts.
- **Icons**: *Font Awesome 6* is used throughout the application.
- **i18n Translation Engine**: Dynamic client-side internationalization system (English, Hindi, Kannada, Telugu, Tamil, Malayalam) with deep DOM walking and MutationObserver monitoring.

## 🌐 Internationalization (i18n) Architecture

The platform supports full dynamic translation across all dashboard pages:
- **Baseline Reference**: `en.json` is used as the master key catalog.
- **Languages Supported**: English (en), Hindi (hi), Kannada (kn), Telugu (te), Tamil (ta), and Malayalam (ml).
- **Execution Flow**:
  - `i18n.js` loads dictionary assets from `/assets/i18n/`.
  - Builds a flat string map (`English -> Target Language`).
  - Performs a deep traversal of the DOM body, converting text nodes, placeholders, titles, and aria attributes.
  - Registers a `MutationObserver` to intercept dynamic dashboard elements and translation-renders them instantly.
  - Skips public/auth pages (landing page, login, register, password recovery) to maintain design layout.
- **State Preservation**: Original English values are cached inside `node._originalText` to support dynamic, multi-hop switching between non-English locales (e.g. Hindi directly to Kannada) without losing context.

## 🛠️ Adding a New Page

1. Create the HTML file in the `frontend/` root.
2. Link the core stylesheets in `<head>`:
   ```html
   <link rel="stylesheet" href="assets/css/style.css">
   <link rel="stylesheet" href="assets/css/glass.css">
   ```
3. Link the core scripts at the end of `<body>`:
   ```html
   <script src="assets/js/api.js"></script>
   <script src="assets/js/components.js"></script>
   <script src="assets/js/your-page-logic.js"></script>
   ```

---

