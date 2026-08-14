/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        db: {
          primary: '#1B3A5C',
          dark: '#0F2440',
          darker: '#0A1929',
          accent: '#FF3621',
          light: '#E8EEF4',
          muted: '#8EA4BC',
          surface: '#162D4A',
          card: '#1E3F63',
        },
      },
    },
  },
  plugins: [],
};
