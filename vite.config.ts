import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],

  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@services': path.resolve(__dirname, './src/services'),
      '@types': path.resolve(__dirname, './src/types'),
      '@db': path.resolve(__dirname, './src/db'),
      '@repositories': path.resolve(__dirname, './src/repositories'),
      '@validation': path.resolve(__dirname, './src/validation'),
      '@api': path.resolve(__dirname, './src/api'),
      '@audit': path.resolve(__dirname, './src/audit')
    }
  },

  server: {
    proxy: {
      // 프론트엔드는 /api/*를 그대로 호출하고, Vite 개발 서버가 Fastify(src/server)로 전달한다
      '/api': {
        target: 'http://localhost:3001',
        changeOrigin: true
      }
    }
  }
});
