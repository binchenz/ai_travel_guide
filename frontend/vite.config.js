import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const BACKEND = 'http://127.0.0.1:8080'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/exhibits':  { target: BACKEND, changeOrigin: true },
      '/chat':      { target: BACKEND, changeOrigin: true },
      '/tts':       { target: BACKEND, changeOrigin: true },
      '/asr':       { target: BACKEND, changeOrigin: true },
      '/ontology':  { target: BACKEND, changeOrigin: true },
      '/voice':     { target: BACKEND, changeOrigin: true },
    },
  },
})
