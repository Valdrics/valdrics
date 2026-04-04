import { readFile } from 'node:fs/promises';
import { createServer } from 'node:http';
import { join } from 'node:path';
import { Readable } from 'node:stream';

import { Server } from './build/server/index.js';
import { manifest } from './build/server/manifest.js';

const host = process.env.HOST || '0.0.0.0';
const port = Number(process.env.PORT || '3000');
const clientDir = join(process.cwd(), 'build', 'client');
const configuredOrigin = normalizeOrigin(process.env.ORIGIN);
const protocolHeader = normalizeHeaderName(process.env.PROTOCOL_HEADER);
const hostHeader = normalizeHeaderName(process.env.HOST_HEADER);
const portHeader = normalizeHeaderName(process.env.PORT_HEADER);

const app = new Server(manifest);
await app.init({ env: process.env });

if (process.env.ORIGIN && !configuredOrigin) {
	throw new Error('dashboard_runtime_invalid_origin_env');
}

if (process.env.NODE_ENV === 'production' && !configuredOrigin && !(protocolHeader && hostHeader)) {
	console.warn('dashboard_runtime_origin_not_explicitly_configured');
}

function normalizeOrigin(value) {
	const candidate = String(value || '').trim();
	if (!candidate) return '';

	try {
		return new URL(candidate).origin;
	} catch {
		return '';
	}
}

function normalizeHeaderName(value) {
	return String(value || '')
		.trim()
		.toLowerCase();
}

function firstHeaderValue(value) {
	if (Array.isArray(value)) {
		return String(value[0] || '').trim();
	}

	return String(value || '')
		.split(',')[0]
		.trim();
}

function requestOrigin(req) {
	if (configuredOrigin) return configuredOrigin;

	if (protocolHeader && hostHeader) {
		const forwardedProtocol = firstHeaderValue(req.headers[protocolHeader]);
		const forwardedHost = firstHeaderValue(req.headers[hostHeader]);
		const forwardedPort = portHeader ? firstHeaderValue(req.headers[portHeader]) : '';
		const portSuffix =
			forwardedPort && forwardedHost && !forwardedHost.includes(':') ? `:${forwardedPort}` : '';
		const derivedOrigin = normalizeOrigin(
			forwardedProtocol && forwardedHost
				? `${forwardedProtocol}://${forwardedHost}${portSuffix}`
				: ''
		);

		if (derivedOrigin) return derivedOrigin;
	}

	return `http://localhost:${port}`;
}

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
		const request = new Request(new URL(req.url || '/', requestOrigin(req)), {
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
