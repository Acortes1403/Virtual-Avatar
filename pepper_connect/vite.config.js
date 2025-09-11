import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import legacy from '@vitejs/plugin-legacy'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    legacy({
      // Android 6.0 ~ Chrome 50 aprox.
      // Suficiente para reducir polyfills, pero garantizamos fallback ES5 si hiciera falta
      targets: ['Android >= 6', 'Chrome >= 49'],
      modernPolyfills: true,
      renderLegacyChunks: true,
      additionalLegacyPolyfills: ['whatwg-fetch'],
    }),
  ],
  build: {
    target: 'es2015',
  },
  server: {
    host: true,
    port: 5173,
    strictPort: true,
    hmr: {
      host: '192.168.10.127',
      protocol: 'ws',
      port: 5173,
    },
    proxy: {
      '^/pepper(/|$)': {
        target: 'http://pepper.local:8070',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/pepper/, ''),
        secure: false,
      }
    }
  },
})
