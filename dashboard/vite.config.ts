import { defineConfig, type TestProjectConfiguration } from 'vitest/config';
import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { playwright } from '@vitest/browser-playwright';

const clientProject: TestProjectConfiguration = {
	extends: './vite.config.ts',
	resolve: {
		conditions: ['browser']
	},
	test: {
		name: 'client',
		environment: 'jsdom',
		include: ['src/**/*.svelte.{test,spec}.{js,ts}'],
		exclude: ['src/lib/server/**', 'src/**/*.browser.{test,spec}.{js,ts}']
	}
};

const browserProject: TestProjectConfiguration = {
	extends: './vite.config.ts',
	test: {
		name: 'browser',
		browser: {
			enabled: true,
			provider: playwright(),
			instances: [{ browser: 'chromium' }]
		},
		include: ['src/**/*.browser.{test,spec}.{js,ts}']
	}
};

const serverProject: TestProjectConfiguration = {
	extends: './vite.config.ts',
	test: {
		name: 'server',
		environment: 'node',
		include: ['src/**/*.{test,spec}.{js,ts}'],
		exclude: ['src/**/*.svelte.{test,spec}.{js,ts}', 'src/**/*.browser.{test,spec}.{js,ts}']
	}
};

const projects: TestProjectConfiguration[] = [clientProject, serverProject];

if (process.env.VITEST_BROWSER === '1') {
	projects.splice(1, 0, browserProject);
}

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],

	build: {
		rollupOptions: {
			output: {
				manualChunks(id) {
					if (!id.includes('node_modules')) return undefined;
					if (id.includes('/node_modules/@supabase/')) return 'vendor-supabase';
					if (id.includes('/node_modules/zod/')) return 'vendor-zod';
					return undefined;
				}
			}
		}
	},

	test: {
		expect: { requireAssertions: true },
		projects
	}
});
