import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// base: './' -> relative asset paths so the FastAPI backend can serve the SPA
// from any mount point. Assets are emitted under dist/assets/.
export default defineConfig({
  base: './',
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
