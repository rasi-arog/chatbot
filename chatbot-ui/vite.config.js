import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import basicSsl from '@vitejs/plugin-basic-ssl'

export default defineConfig({
  plugins: [react(), basicSsl({ allowHTTP1: true })],
  server: {
    https: { allowHTTP1: true },
    proxy: {
      '/chat': { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
      '/transcribe': { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
      '/verify-image': { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
      '/login': { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
      '/register': { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
    }
  }
})
