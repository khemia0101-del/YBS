/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: { DEFAULT: '#1e40af', light: '#3b82f6', dark: '#1e3a8a' },
        success: '#16a34a',
        warning: '#d97706',
        danger: '#dc2626',
        surface: '#f8fafc',
      },
    },
  },
  plugins: [],
}
