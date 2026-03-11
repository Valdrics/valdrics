import { readFile } from 'node:fs/promises';
import { createServer } from 'node:http';
import { join } from 'node:path';
import { Readable } from 'node:stream';

import { Server } from './build/server/index.js';
import { manifest } from './build/server/manifest.js';

const host = process.env.HOST || '0.0.0.0';
const port = Number(process.env.PORT || '3000');
const clientDir = join(process.cwd(), 'build', 'client');

const app = new Server(manifest);
await app.init({ env: process.env });

function toRequestHeaders(nodeHeaders) {
	const headers = new Headers();

	for (const [key, value] of Object.entries(nodeHeaders)) {
		if (value === undefined) continue;
		if (Array.isArray(value)) {
			for (const item of value) headers.append(key, item);
			continue;
		}
		headers.set(key, value);
	}

	return headers;
}

function writeResponseHeaders(response, res) {
	const setCookies =
		typeof response.headers.getSetCookie === 'function' ? response.headers.getSetCookie() : [];

	for (const [key, value] of response.headers.entries()) {
		if (key === 'set-cookie') continue;
		res.setHeader(key, value);
	}

	if (setCookies.length > 0) {
		res.setHeader('set-cookie', setCookies);
	}
}

const server = createServer(async (req, res) => {
	try {
		const origin = `http://${req.headers.host || `${host}:${port}`}`;
		const request = new Request(new URL(req.url || '/', origin), {
			method: req.method,
			headers: toRequestHeaders(req.headers),
			body:
				req.method === 'GET' || req.method === 'HEAD' || req.method === undefined
					? undefined
					: Readable.toWeb(req)
		});

		const response = await app.respond(request, {
			getClientAddress: () => req.socket.remoteAddress || '',
			platform: {
				context: {
					waitUntil: () => {}
				},
				env: process.env
			},
			read: (file) => readFile(join(clientDir, file))
		});

		res.statusCode = response.status;
		writeResponseHeaders(response, res);

		if (!response.body || req.method === 'HEAD') {
			res.end();
			return;
		}

		Readable.fromWeb(response.body).pipe(res);
	} catch (error) {
		console.error('dashboard_runtime_request_failed', error);
		if (!res.headersSent) {
			res.statusCode = 500;
			res.setHeader('content-type', 'text/plain; charset=utf-8');
		}
		res.end('Internal Server Error');
	}
});

server.listen(port, host, () => {
	console.log(`dashboard_runtime_listening http://${host}:${port}`);
});
