import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://n3tman.github.io',
  base: '/vibe-check/',
  trailingSlash: 'always',
  output: 'static',
  build: { format: 'directory', inlineStylesheets: 'auto' },
  devToolbar: { enabled: false },
  vite: { server: { fs: { allow: ['..'] } } },
});
