import type { SignalLaneId, SignalLaneSeverity } from './realtimeSignalMap';
import { buildSnapshotTrace } from './signalTrace';

export interface LandingSignalLaneSnapshot {
	id: SignalLaneId;
	status: string;
	severity: SignalLaneSeverity;
	wasteUsd?: number;
	actionLabel?: string;
}

interface LandingSignalSnapshotInput {
	id: string;
	label: string;
	capturedAt: string;
	traceSummary: string;
	lanes: Record<
		SignalLaneId,
		{
			status: string;
			severity: SignalLaneSeverity;
			wasteUsd?: number;
			actionLabel?: string;
		}
	>;
	sources: readonly string[];
}

export interface LandingSignalSnapshot {
	id: string;
	label: string;
	capturedAt: string;
	traceId: string;
	lanes: readonly LandingSignalLaneSnapshot[];
	sources: readonly string[];
}

const RAW_LANDING_SIGNAL_SNAPSHOTS: readonly LandingSignalSnapshotInput[] = [
	{
		id: 'snp-2026-02-27-a',
		label: 'Snapshot A',
		capturedAt: '2026-02-27T20:55:58Z',
		traceSummary: 'Owner and approval attached before action moves.',
		lanes: {
			economic_visibility: {
				status: 'Watch',
				severity: 'watch',
				wasteUsd: 12400,
				actionLabel: 'Assign Owner'
			},
			deterministic_enforcement: {
				status: 'Stable',
				severity: 'healthy'
			},
			financial_governance: {
				status: 'Stable',
				severity: 'healthy'
			},
			operational_resilience: {
				status: 'Stable',
				severity: 'healthy'
			}
		},
		sources: ['Cloud cost telemetry', 'Failure drill evidence', 'Execution coverage report']
	},
	{
		id: 'snp-2026-02-28-b',
		label: 'Snapshot B',
		capturedAt: '2026-02-28T06:30:00Z',
		traceSummary: 'Exception review stays on the same operating record.',
		lanes: {
			economic_visibility: {
				status: 'Stable',
				severity: 'healthy'
			},
			deterministic_enforcement: {
				status: 'Watch',
				severity: 'watch',
				wasteUsd: 8200,
				actionLabel: 'Review Guardrails'
			},
			financial_governance: {
				status: 'Stable',
				severity: 'healthy'
			},
			operational_resilience: {
				status: 'Stable',
				severity: 'healthy'
			}
		},
		sources: ['Pricing decision records', 'Approval routing checks']
	},
	{
		id: 'snp-2026-02-28-c',
		label: 'Snapshot C',
		capturedAt: '2026-02-28T12:00:00Z',
		traceSummary: 'Leadership gets one reviewable decision trail.',
		lanes: {
			economic_visibility: {
				status: 'Stable',
				severity: 'healthy'
			},
			deterministic_enforcement: {
				status: 'Stable',
				severity: 'healthy'
			},
			financial_governance: {
				status: 'Watch',
				severity: 'watch',
				wasteUsd: 15800,
				actionLabel: 'Adjust Approval Limit'
			},
			operational_resilience: {
				status: 'Stable',
				severity: 'healthy'
			}
		},
		sources: ['Finance telemetry snapshot', 'Control gap register', 'Release sanity checks']
	},
	{
		id: 'snp-2026-03-01-d',
		label: 'Snapshot D',
		capturedAt: '2026-03-01T09:00:00Z',
		traceSummary: 'Rollback and proof stay attached through remediation.',
		lanes: {
			economic_visibility: {
				status: 'Stable',
				severity: 'healthy'
			},
			deterministic_enforcement: {
				status: 'Stable',
				severity: 'healthy'
			},
			financial_governance: {
				status: 'Stable',
				severity: 'healthy'
			},
			operational_resilience: {
				status: 'Watch',
				severity: 'watch',
				wasteUsd: 9400,
				actionLabel: 'Refresh Record'
			}
		},
		sources: ['Resilience audit logs', 'Recovery playbook telemetry']
	}
] as const;

function hydrateLandingSignalSnapshot(input: LandingSignalSnapshotInput): LandingSignalSnapshot {
	const lanes = Object.entries(input.lanes).map(([id, lane]) =>
		Object.freeze({
			id: id as SignalLaneId,
			...lane
		})
	);

	return Object.freeze({
		id: input.id,
		label: input.label,
		capturedAt: input.capturedAt,
		traceId: buildSnapshotTrace(input.id, input.capturedAt, input.traceSummary),
		lanes: Object.freeze(lanes),
		sources: Object.freeze([...input.sources])
	});
}

export const LANDING_SIGNAL_SNAPSHOTS: readonly LandingSignalSnapshot[] = Object.freeze(
	RAW_LANDING_SIGNAL_SNAPSHOTS.map((snapshot) => hydrateLandingSignalSnapshot(snapshot))
);
