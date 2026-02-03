import adapter from '@sveltejs/adapter-static';

const basePath = process.env.PUBLIC_BASE_PATH || '';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	kit: {
		paths: {
			base: basePath
		},
		adapter: adapter({
			fallback: 'index.html'
		})
	}
};

export default config;
