import type { SignalLaneId, SignalLaneSnapshot } from '$lib/landing/realtimeSignalMap';

export const LANDING_GRID_X = [...Array(13).keys()];
export const LANDING_GRID_Y = [...Array(9).keys()];

export const SIGNAL_CENTER = Object.freeze({ x: 320, y: 210 });

export const LANE_ANCHOR_NUDGE: Readonly<Record<SignalLaneId, { x: number; y: number }>> =
	Object.freeze({
		economic_visibility: { x: -40, y: -30 },
		deterministic_enforcement: { x: 40, y: -30 },
		financial_governance: { x: 40, y: 30 },
		operational_resilience: { x: -40, y: 30 }
	});

export const LABEL_TRANSLATE: Readonly<Record<SignalLaneId, string>> = Object.freeze({
	economic_visibility: 'transform: translate(-100%, -50%) translateX(-12px);',
	deterministic_enforcement: 'transform: translate(0, -50%) translateX(12px);',
	financial_governance: 'transform: translate(0, -50%) translateX(12px);',
	operational_resilience: 'transform: translate(-100%, -50%) translateX(-12px);'
});

export function resolveLaneAnchor(lane: SignalLaneSnapshot): { x: number; y: number } {
	const nudge = LANE_ANCHOR_NUDGE[lane.id];
	return {
		x: Math.min(622, Math.max(18, lane.x + nudge.x)),
		y: Math.min(402, Math.max(18, lane.y + nudge.y))
	};
}

export function resolveSvgProjection(
	signalMapWidth: number,
	signalMapHeight: number,
	viewboxWidth: number,
	viewboxHeight: number
): { scale: number; offsetX: number; offsetY: number } | undefined {
	if (signalMapWidth <= 0 || signalMapHeight <= 0) {
		return undefined;
	}
	const scale = Math.min(signalMapWidth / viewboxWidth, signalMapHeight / viewboxHeight);
	const renderedWidth = viewboxWidth * scale;
	const renderedHeight = viewboxHeight * scale;
	return {
		scale,
		offsetX: (signalMapWidth - renderedWidth) / 2,
		offsetY: (signalMapHeight - renderedHeight) / 2
	};
}

export function resolveHotspotPoint(
	point: { x: number; y: number },
	projection: { scale: number; offsetX: number; offsetY: number } | undefined
): { leftPx: number; topPx: number } | undefined {
	if (!projection) {
		return undefined;
	}
	return {
		leftPx: projection.offsetX + point.x * projection.scale,
		topPx: projection.offsetY + point.y * projection.scale
	};
}
