import { describe, expect, it } from 'vitest';
import { LANDING_SIGNAL_SNAPSHOTS } from './landingSignalSnapshots';
import { buildSnapshotTrace } from './signalTrace';

describe('landingSignalSnapshots', () => {
	it('publishes deterministic lightweight snapshots for the public landing page', () => {
		expect(LANDING_SIGNAL_SNAPSHOTS.length).toBeGreaterThanOrEqual(3);

		for (const snapshot of LANDING_SIGNAL_SNAPSHOTS) {
			expect(Number.isNaN(Date.parse(snapshot.capturedAt))).toBe(false);
			expect(snapshot.lanes).toHaveLength(4);
			for (const lane of snapshot.lanes) {
				expect(typeof lane.id).toBe('string');
				expect(typeof lane.status).toBe('string');
				expect(typeof lane.severity).toBe('string');
			}
		}
	});

	it('derives stable trace ids without importing the full signal-map module', () => {
		const [first] = LANDING_SIGNAL_SNAPSHOTS;
		expect(first).toBeDefined();
		if (!first) return;

		expect(first.traceId).toBe(
			buildSnapshotTrace(
				first.id,
				first.capturedAt,
				'Owner and approval attached before action moves.'
			)
		);
		expect(first.traceId).toMatch(/^TRC-[A-F0-9]{8}$/);
	});
});
