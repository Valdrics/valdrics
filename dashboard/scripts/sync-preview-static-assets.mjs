import { cpSync, existsSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = dirname(fileURLToPath(import.meta.url));
const dashboardRoot = resolve(scriptDir, '..');
const staticDir = resolve(dashboardRoot, 'static');
const previewClientDir = resolve(dashboardRoot, '.svelte-kit', 'output', 'client');

if (!existsSync(previewClientDir)) {
	throw new Error(
		`Missing preview client output at ${previewClientDir}. Run "pnpm --dir dashboard run build" before preview.`
	);
}

if (existsSync(staticDir)) {
	cpSync(staticDir, previewClientDir, { recursive: true });
}
