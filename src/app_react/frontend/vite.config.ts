import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// base: '/' -> ABSOLUTE asset paths. The SPA is served at the domain root and
// uses client-side routing (e.g. /claim/:id). Relative ('./') asset URLs break
// on nested routes because the browser resolves them against the route path
// (/claim/assets/... -> index.html -> MIME error). Absolute '/assets/...' always
// resolves correctly regardless of route depth.
export default defineConfig({
  base: '/',
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    assetsDir: 'assets',
  },
})
