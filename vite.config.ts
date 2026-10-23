import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Root Vite config for the platform preview. It serves the root index.html,
// which loads the real frontend entry at /frontend/src/main.tsx, and proxies
// /api to the FastAPI backend.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: Number(process.env.PORT) || 5173,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
