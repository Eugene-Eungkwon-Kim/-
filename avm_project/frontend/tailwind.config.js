/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx}',
    './pages/**/*.{js,ts,jsx,tsx}',
    './components/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      // globals.css와 각 페이지 컴포넌트가 이미 50~900 전 구간의 셰이드를
      // 참조하고 있었는데(hover:bg-error-700, badge-success 의 success-100
      // 등) 실제로는 색상당 셰이드 1~2개만 정의돼 있어 `next build` 자체가
      // 안 됐다(이 세션 전까지 frontend는 node_modules 도 설치된 적 없어
      // 아무도 빌드해보지 않은 상태). 기존에 정의돼 있던 값은 그대로 두고
      // (기존 화면 톤 변경 없음) 빠진 셰이드만 채운다 — success/error/info는
      // 기존 500 값이 공식 Material 팔레트와 정확히 일치해 그대로 확장했다.
      colors: {
        primary: {
          900: '#0D47A1',
          800: '#123F84',
          700: '#1565C0',
          600: '#1E88E5',
          500: '#2196F3',
          400: '#42A5F5',
          300: '#64B5F6',
          200: '#90CAF9',
          100: '#E3F2FD',
          50: '#F5FAFE',
        },
        success: {
          900: '#1B5E20',
          800: '#2E7D32',
          700: '#388E3C',
          600: '#43A047',
          500: '#4CAF50',
          400: '#66BB6A',
          300: '#81C784',
          200: '#A5D6A7',
          100: '#C8E6C9',
          50: '#E8F5E9',
        },
        warning: {
          900: '#E65100',
          800: '#EF6C00',
          700: '#F57C00',
          600: '#FB8C00',
          500: '#FFA726',
          200: '#FFCC80',
          100: '#FFE0B2',
          50: '#FFF3E0',
        },
        error: {
          900: '#B71C1C',
          800: '#C62828',
          700: '#D32F2F',
          600: '#E53935',
          500: '#F44336',
          400: '#EF5350',
          300: '#E57373',
          200: '#EF9A9A',
          100: '#FFCDD2',
          50: '#FFEBEE',
        },
        info: {
          900: '#006064',
          800: '#00838F',
          700: '#0097A7',
          600: '#00ACC1',
          500: '#00BCD4',
          400: '#26C6DA',
          300: '#4DD0E1',
          200: '#80DEEA',
          100: '#B2EBF2',
          50: '#E0F7FA',
        },
        neutral: {
          900: '#212121',
          800: '#303030',
          700: '#424242',
          600: '#616161',
          500: '#757575',
          400: '#BDBDBD',
          300: '#E0E0E0',
          200: '#EEEEEE',
          100: '#F5F5F5',
          50: '#FAFAFA',
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
