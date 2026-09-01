import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

// 프론트 9503, 백엔드 9523. 개발 중에는 /api 를 백엔드로 프록시해
// 브라우저에서 같은 출처로 보이게 한다(운영에서는 Nginx 가 같은 일을 한다).
export default defineConfig({
  plugins: [vue()],
  server: {
    port: 9503,
    host: true,
    strictPort: true,
    proxy: { '/api': { target: 'http://127.0.0.1:9523', changeOrigin: true } },
    allowedHosts: ['p3.sumzip.com', 'localhost', '127.0.0.1'],
  },
  preview: { port: 9503, host: true, strictPort: true, allowedHosts: ['p3.sumzip.com'] },
  build: { outDir: 'dist', sourcemap: false },
});
