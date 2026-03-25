export function buildSnapshotTrace(
	snapshotId: string,
	capturedAt: string,
	summary: string
): string {
	const value = `${snapshotId}|${capturedAt}|${summary}`;
	let hash = 0x811c9dc5;

	for (let index = 0; index < value.length; index += 1) {
		hash ^= value.charCodeAt(index);
		hash = Math.imul(hash, 0x01000193);
	}

	return `TRC-${(hash >>> 0).toString(16).toUpperCase().padStart(8, '0')}`;
}
