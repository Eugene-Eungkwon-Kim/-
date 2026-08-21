#!/bin/bash
# AVM Dashboard Setup Script
# Next.js + Tailwind CSS + TypeScript 프로젝트 초기화

set -e

PROJECT_DIR="/home/user/-/avm_project"
FRONTEND_DIR="$PROJECT_DIR/frontend"

echo "🚀 AVM Dashboard 프로젝트 초기화 시작..."
echo "=================================="

# 1. 프론트엔드 디렉토리 생성
mkdir -p "$FRONTEND_DIR"
cd "$FRONTEND_DIR"

# 2. package.json 생성
cat > package.json <<'EOF'
{
  "name": "avm-dashboard",
  "version": "1.0.0",
  "description": "AVM (Automated Valuation Model) Dashboard",
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "next": "^14.0.0",
    "axios": "^1.6.0",
    "recharts": "^2.10.0",
    "lucide-react": "^0.294.0"
  },
  "devDependencies": {
    "typescript": "^5.3.0",
    "@types/react": "^18.2.0",
    "@types/node": "^20.10.0",
    "tailwindcss": "^3.3.0",
    "postcss": "^8.4.0",
    "autoprefixer": "^10.4.0",
    "eslint": "^8.55.0",
    "eslint-config-next": "^14.0.0"
  }
}
EOF

echo "✅ package.json 생성"

# 3. tsconfig.json
cat > tsconfig.json <<'EOF'
{
  "compilerOptions": {
    "target": "es2020",
    "useDefineForClassFields": true,
    "lib": ["es2020", "dom", "dom.iterable"],
    "module": "esnext",
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "noImplicitAny": true,
    "moduleResolution": "node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "paths": {
      "@/*": ["./*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx"],
  "exclude": ["node_modules"]
}
EOF

echo "✅ tsconfig.json 생성"

# 4. next.config.js
cat > next.config.js <<'EOF'
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
}

module.exports = nextConfig
EOF

echo "✅ next.config.js 생성"

# 5. tailwind.config.js
cat > tailwind.config.js <<'EOF'
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
EOF

echo "✅ tailwind.config.js 생성"

# 6. postcss.config.js
cat > postcss.config.js <<'EOF'
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
EOF

echo "✅ postcss.config.js 생성"

# 7. .eslintrc.json
cat > .eslintrc.json <<'EOF'
{
  "extends": "next/core-web-vitals"
}
EOF

echo "✅ .eslintrc.json 생성"

# 8. .gitignore
cat > .gitignore <<'EOF'
node_modules/
.next/
dist/
build/
*.log
.env.local
.env.*.local
.vscode/
.DS_Store
EOF

echo "✅ .gitignore 생성"

# 9. 디렉토리 구조 생성
mkdir -p app
mkdir -p components/ui
mkdir -p components/layout
mkdir -p components/pages
mkdir -p hooks
mkdir -p lib
mkdir -p public/images
mkdir -p styles

echo "✅ 디렉토리 구조 생성"

echo ""
echo "✅ 프로젝트 초기화 완료!"
echo ""
echo "📦 다음 단계:"
echo "  cd $FRONTEND_DIR"
echo "  npm install"
echo "  npm run dev"
echo ""
echo "🌐 브라우저에서 http://localhost:3000 접속"
