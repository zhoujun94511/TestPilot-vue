import tailwindcssAnimate from 'tailwindcss-animate';

/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ['selector', '[data-theme="dark"]'],
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  corePlugins: {
    preflight: false
  },
  theme: {
    extend: {
      colors: {
        border: 'var(--tp-border)',
        input: 'var(--tp-border)',
        ring: 'var(--tp-ring)',
        background: 'var(--tp-background)',
        foreground: 'var(--tp-foreground)',
        primary: {
          DEFAULT: 'var(--tp-color-primary-600)',
          foreground: 'var(--tp-color-text-inverse)'
        },
        secondary: {
          DEFAULT: 'var(--tp-muted)',
          foreground: 'var(--tp-foreground)'
        },
        destructive: {
          DEFAULT: 'var(--tp-color-danger-600)',
          foreground: 'var(--tp-color-text-inverse)'
        },
        card: {
          DEFAULT: 'var(--tp-bg-surface)',
          foreground: 'var(--tp-foreground)'
        },
        muted: {
          DEFAULT: 'var(--tp-muted)',
          foreground: 'var(--tp-muted-foreground)'
        },
        accent: {
          DEFAULT: 'var(--tp-accent)',
          foreground: 'var(--tp-accent-foreground)'
        },
        popover: {
          DEFAULT: 'var(--tp-bg-surface)',
          foreground: 'var(--tp-foreground)'
        }
      },
      borderRadius: {
        lg: 'var(--tp-radius-lg)',
        md: 'var(--tp-radius-md)',
        sm: 'var(--tp-radius-sm)'
      },
      fontFamily: {
        sans: ['var(--tp-font-sans)']
      },
      transitionDuration: {
        'tp-fast': 'var(--tp-motion-fast)',
        'tp-normal': 'var(--tp-motion-normal)'
      },
      keyframes: {
        'accordion-down': {
          from: { height: '0' },
          to: { height: 'var(--radix-accordion-content-height)' }
        },
        'accordion-up': {
          from: { height: 'var(--radix-accordion-content-height)' },
          to: { height: '0' }
        },
        'page-toast-in': {
          from: { opacity: '0', transform: 'translateX(-50%) translateY(10px)' },
          to: { opacity: '1', transform: 'translateX(-50%) translateY(0)' }
        },
        'doc-row-highlight-fade': {
          '0%': {
            background: 'color-mix(in srgb, var(--tp-color-primary-500) 22%, transparent)'
          },
          '100%': { background: 'transparent' }
        },
        'cases-row-highlight-fade': {
          '0%': {
            background: 'color-mix(in srgb, var(--tp-color-primary-500) 42%, transparent)'
          },
          '100%': { background: 'transparent' }
        }
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
        'page-toast-in': 'page-toast-in 180ms ease-out',
        'doc-row-highlight-fade': 'doc-row-highlight-fade 3.6s ease forwards',
        'cases-row-highlight-fade': 'cases-row-highlight-fade 4.6s ease forwards'
      }
    }
  },
  plugins: [tailwindcssAnimate]
};
