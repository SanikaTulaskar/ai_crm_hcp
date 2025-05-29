// frontend_app/tailwind.config.js
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html" // If you use Tailwind classes directly in index.html
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
      colors: {
        primary: {
          light: '#60a5fa', // blue-400
          DEFAULT: '#3b82f6', // blue-500
          dark: '#2563eb', // blue-600
        },
        secondary: {
          light: '#a78bfa', // violet-400
          DEFAULT: '#8b5cf6', // violet-500
          dark: '#7c3aed', // violet-600
        }
      }
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
  ],
}
