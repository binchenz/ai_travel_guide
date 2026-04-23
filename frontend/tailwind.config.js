/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'museum-brown': '#5c3d2e',
        'museum-gold': '#c9a066',
        'museum-blue': '#1e3a5f',
      },
    },
  },
  plugins: [],
}
