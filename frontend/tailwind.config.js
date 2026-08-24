/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./**/*.{html,js}",
    "./assets/**/*.{html,js,css}",
    "./admin/**/*.{html,js}",
    "./dashboard/**/*.{html,js}",
    "./auth/**/*.{html,js}",
    "./analytics/**/*.{html,js}",
    "./projects/**/*.{html,js}",
    "./rewards/**/*.{html,js}"
  ],
  darkMode: ['class', '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        background: {
          DEFAULT: '#F8F9FA',
          dark: '#001830',
        },
        surface: {
          DEFAULT: '#FFFFFF',
          dark: '#002347',
        },
        primary: {
          DEFAULT: '#002347', // Deep Institutional Navy
          dark: '#001830',
          light: '#00305F',
        },
        gold: {
          DEFAULT: '#C4A25A', // Warm Ochre Gold (Primary CTA)
          hover: '#AC8839',   // Gold Hover / Dark Gold
          light: 'rgba(196, 162, 90, 0.12)',
          border: 'rgba(196, 162, 90, 0.35)',
        },
        accent: {
          DEFAULT: '#C4A25A',
          hover: '#AC8839',
          violet: '#4809BD',  // Accent Violet / Secondary
        },
        slate: {
          text: '#476585',    // Text Muted / Body Slate
          muted: '#476585',
        },
        border: {
          DEFAULT: '#DAE0E7',
          focus: 'rgba(196, 162, 90, 0.35)',
          hover: 'rgba(196, 162, 90, 0.35)',
        },
        success: {
          DEFAULT: '#10B981', // Checkmark Green
        }
      },
      fontFamily: {
        sans: ['"Inter"', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', 'sans-serif'],
      },
      borderRadius: {
        'card': '16px',
        'btn-primary': '12px',
        'btn-dark': '10px',
        'pill': '9999px',
        'auth-pill': '10px',
      },
      boxShadow: {
        'card': '0 2px 8px -2px rgba(0, 35, 71, 0.08)',
        'card-hover': '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
        'gold-glow': '0 8px 24px -6px rgba(196, 162, 90, 0.45)',
      },
      backgroundImage: {
        'hero-gradient': 'radial-gradient(ellipse 80% 80% at 50% -20%, hsl(41 47% 56% / 0.1) 0%, transparent 50%), linear-gradient(180deg, #001830 0%, #002347 50%, #001830 100%)',
      }
    },
  },
  plugins: [],
};
