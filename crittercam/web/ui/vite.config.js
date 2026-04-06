import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // any request from the browser starting with /api or /media
      // gets forwarded to the FastAPI server on port 8000
      '/api': 'http://localhost:8000',
      '/media': 'http://localhost:8000',
    },
  },
})
