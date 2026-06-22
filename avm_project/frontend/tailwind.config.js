/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx}',
    './pages/**/*.{js,ts,jsx,tsx}',
    './components/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          900: '#0D47A1',
          700: '#1565C0',
          500: '#2196F3',
          300: '#64B5F6',
          100: '#E3F2FD',
        },
        success: {
          500: '#4CAF50',
        },
        warning: {
          500: '#FFA726',
        },
        error: {
          500: '#F44336',
        },
        info: {
          500: '#00BCD4',
        },
        neutral: {
          900: '#212121',
          700: '#424242',
          500: '#757575',
          300: '#E0E0E0',
          100: '#F5F5F5',
        },
      },
      spacing: {
        'sidebar': '170px',
        'header': '56px',
      },
      fontSize: {
        'h1': ['36px', { lineHeight: '44px', fontWeight: '700' }],
        'h2': ['28px', { lineHeight: '36px', fontWeight: '600' }],
        'h3': ['24px', { lineHeight: '32px', fontWeight: '600' }],
        'h4': ['20px', { lineHeight: '28px', fontWeight: '600' }],
        'body-lg': ['16px', { lineHeight: '24px', fontWeight: '400' }],
        'body': ['14px', { lineHeight: '20px', fontWeight: '400' }],
        'body-sm': ['12px', { lineHeight: '16px', fontWeight: '400' }],
        'label': ['12px', { lineHeight: '16px', fontWeight: '600' }],
      },
    },
  },
  plugins: [],
}
