import { defineConfig } from 'vite';
import { fileURLToPath } from 'node:url';

const viewer = fileURLToPath(new URL('.', import.meta.url));
const market = fileURLToPath(new URL('../market/web', import.meta.url));

export default defineConfig({
  server: { fs: { allow: [viewer, market] } },
  build: {
    manifest: true,
    rolldownOptions: {
      input: { index: fileURLToPath(new URL('index.html', import.meta.url)), market: fileURLToPath(new URL('market.html', import.meta.url)) },
    },
  },
});
