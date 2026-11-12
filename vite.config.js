import { fileURLToPath, URL } from 'node:url'
import { createReadStream } from 'node:fs'
import { stat } from 'node:fs/promises'
import { resolve, sep } from 'node:path'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Large evaluation images stay outside the Pages artifact. Serve them locally in dev.
function evaluationAssets() {
  return {
    name: 'evaluation-assets',
    configureServer(server) {
      const root = resolve(server.config.root, 'evaluation_assets')
      server.middlewares.use('/evaluation_assets', async (request, response) => {
        try {
          const relative = decodeURIComponent((request.url || '').split('?')[0]).replace(/^\/+/, '')
          const path = resolve(root, relative)
          if (!path.startsWith(root + sep) || !/\.(jpg|jpeg|png|webp)$/i.test(path)) {
            response.statusCode = 404; response.end(); return
          }
          const info = await stat(path)
          if (!info.isFile()) { response.statusCode = 404; response.end(); return }
          const extension = path.split('.').pop().toLowerCase()
          response.setHeader('Content-Type', `image/${extension === 'jpg' ? 'jpeg' : extension}`)
          response.setHeader('Content-Length', info.size)
          if (request.method === 'HEAD') { response.end(); return }
          createReadStream(path).on('error', () => response.destroy()).pipe(response)
        } catch { response.statusCode = 404; response.end() }
      })
    }
  }
}

const baseUrl = process.env.VITE_BASE_URL || '/';

export default defineConfig({
  plugins: [
    vue(),
    evaluationAssets()
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
      vue$: 'vue/dist/vue.esm-bundler.js',
    }
  },
  base: process.env.NODE_ENV === 'production' ? baseUrl : '/',
})
