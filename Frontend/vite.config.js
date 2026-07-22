import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'node:path'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

const DEFAULT_API_TARGET = 'http://localhost:9999'

export function resolveApiTarget(mode, cwd = process.cwd()) {
  return loadEnv(mode, cwd, 'VITE_').VITE_API_TARGET?.trim() || DEFAULT_API_TARGET
}

export default defineConfig(({ mode }) => ({
  plugins: [
    vue(),
    AutoImport({ resolvers: [ElementPlusResolver()] }),
    Components({ resolvers: [ElementPlusResolver()] }),
  ],
  resolve: { alias: { '@': path.resolve(__dirname, 'src') } },
  css: {
    preprocessorOptions: {
      scss: { additionalData: `@use "@/assets/styles/variables.scss" as *;` },
    },
  },
  server: {
    port: 3000,
    open: false,
    proxy: {
      '/api': {
        target: resolveApiTarget(mode),
        changeOrigin: true,
      },
    },
  },
}))
