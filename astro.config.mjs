// @ts-check
import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';
import sitemap from '@astrojs/sitemap';

// https://astro.build/config
export default defineConfig({
  site: 'https://theacaiclub.com',
  output: 'static',
  // Checkout is noindex, so keep it out of the sitemap too.
  integrations: [sitemap({ filter: (page) => !page.includes('/store/checkout') })],
  vite: {
    plugins: [tailwindcss()]
  },
});
