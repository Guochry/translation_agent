import { fileURLToPath, URL } from 'node:url'
import { createReadStream } from 'node:fs'
import { stat } from 'node:fs/promises'
import { resolve, sep } from 'node:path'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// Evaluation media stay outside the Pages artifact. Video seeking needs byte ranges.
function evaluationAssets() {
  return {
    name: 'evaluation-assets',
    configureServer(server) {
      const root = resolve(server.config.root, 'evaluation_assets')
      server.middlewares.use('/evaluation_assets', async (request, response) => {
        try {
          const relative = decodeURIComponent((request.url || '').split('?')[0]).replace(/^\/+/, '')
          const path = resolve(root, relative)
          if (!path.startsWith(root + sep) || !/\.(jpg|jpeg|png|webp|mp4|webm)$/i.test(path)) {
            response.statusCode = 404; response.end(); return
          }
          const info = await stat(path)
          if (!info.isFile()) { response.statusCode = 404; response.end(); return }
          const extension = path.split('.').pop().toLowerCase()
          response.setHeader('Content-Type', /^(mp4|webm)$/.test(extension) ? `video/${extension}` : `image/${extension === 'jpg' ? 'jpeg' : extension}`)
          response.setHeader('Accept-Ranges', 'bytes')
          if (request.headers.range) {
            const match = /^bytes=(\d*)-(\d*)$/.exec(request.headers.range)
            let start = match?.[1] ? Number(match[1]) : 0
            let end = match?.[2] ? Number(match[2]) : info.size - 1
            if (match && !match[1] && match[2]) { start = Math.max(0, info.size - Number(match[2])); end = info.size - 1 }
            if (!match || (!match[1] && !match[2]) || !Number.isSafeInteger(start) || !Number.isSafeInteger(end)
                || start < 0 || start >= info.size || end < start) {
              response.statusCode = 416
              response.setHeader('Content-Range', `bytes */${info.size}`)
              response.end(); return
            }
            end = Math.min(end, info.size - 1)
            response.statusCode = 206
            response.setHeader('Content-Range', `bytes ${start}-${end}/${info.size}`)
            response.setHeader('Content-Length', end - start + 1)
            if (request.method === 'HEAD') { response.end(); return }
            createReadStream(path, { start, end }).on('error', () => response.destroy()).pipe(response)
            return
          }
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
