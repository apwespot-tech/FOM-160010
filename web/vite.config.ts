import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    // В Docker на Windows изменения файлов видны только с опросом
    watch: { usePolling: true },
    // Запросы /health уходят в Laravel API (сервис api в compose.yaml)
    proxy: {
      '/health': 'http://api:8000',
    },
  },
})
