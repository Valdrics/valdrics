type ClientLogLevel = 'error' | 'warn' | 'info';

const CLIENT_LOGGING_ENABLED = !import.meta.env.PROD;

function emitClientLog(level: ClientLogLevel, message: string, context?: unknown): void {
	if (!CLIENT_LOGGING_ENABLED) {
		return;
	}
	if (context === undefined) {
		console[level](message);
		return;
	}
	console[level](message, context);
}

export const clientLogger = {
	error(message: string, context?: unknown): void {
		emitClientLog('error', message, context);
	},
	warn(message: string, context?: unknown): void {
		emitClientLog('warn', message, context);
	},
	info(message: string, context?: unknown): void {
		emitClientLog('info', message, context);
	}
};
