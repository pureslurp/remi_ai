import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          navy: 'rgb(var(--brand-navy-rgb) / <alpha-value>)',
          slate: 'rgb(var(--brand-slate-rgb) / <alpha-value>)',
          cloud: 'rgb(var(--brand-cloud-rgb) / <alpha-value>)',
          mint: 'rgb(var(--brand-mint-rgb) / <alpha-value>)',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['Inter', 'system-ui', 'sans-serif'],
        landingDisplay: ['"Cormorant Garamond"', 'Georgia', 'serif'],
        landingSans: ['Manrope', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}

export default config
