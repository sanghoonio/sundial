import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';

const basePath = process.env.PUBLIC_BASE_PATH || '';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	server: {
		proxy: {
			[`${basePath}/api`]: {
				target: 'http://localhost:8000',
				changeOrigin: true
			},
			[`${basePath}/ws`]: {
				target: 'ws://localhost:8000',
				ws: true
			}
		}
	}
});
