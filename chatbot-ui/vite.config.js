import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import basicSsl from '@vitejs/plugin-basic-ssl'

const isDev = process.env.NODE_ENV !== 'production'

export default defineConfig({
  plugins: isDev ? [react(), basicSsl({ allowHTTP1: true })] : [react()],
  server: {
    https: isDev ? { allowHTTP1: true } : false,
    proxy: isDev ? {
      '/chat': { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
      '/transcribe': { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
      '/verify-image': { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
      '/login': { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
      '/register': { target: 'http://127.0.0.1:8000', changeOrigin: true, secure: false },
    } : {}
  }
})
