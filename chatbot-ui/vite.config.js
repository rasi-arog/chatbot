import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import basicSsl from '@vitejs/plugin-basic-ssl'

export default defineConfig({
  plugins: [react(), basicSsl()],
  server: {
    https: true,
    proxy: {
      '/chat': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/transcribe': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '/verify-image': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      }
    }
  }
})
