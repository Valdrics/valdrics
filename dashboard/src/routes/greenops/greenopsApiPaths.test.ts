import { describe, expect, it } from 'vitest';

import {
	GREENOPS_DEFAULT_PROVIDER,
	buildCarbonBudgetPath,
	buildCarbonFootprintPath,
	buildCarbonIntensityPath,
	buildGravitonPath,
	buildGreenSchedulePath
} from './greenopsApiPaths';

describe('greenops API path helpers', () => {
	it('includes provider on carbon footprint requests', () => {
		const path = buildCarbonFootprintPath({
			startDate: '2026-02-01',
			endDate: '2026-03-01',
			region: 'eu-west-1'
		});

		expect(path).toContain('/api/edge/api/v1/carbon?');
		expect(path).toContain('start_date=2026-02-01');
		expect(path).toContain('end_date=2026-03-01');
		expect(path).toContain('region=eu-west-1');
		expect(path).toContain(`provider=${GREENOPS_DEFAULT_PROVIDER}`);
	});

	it('includes provider on carbon budget requests', () => {
		const path = buildCarbonBudgetPath({ region: 'us-west-2' });

		expect(path).toContain('/api/edge/api/v1/carbon/budget?');
		expect(path).toContain('region=us-west-2');
		expect(path).toContain(`provider=${GREENOPS_DEFAULT_PROVIDER}`);
	});

	it('preserves existing regional helper behavior for schedule, intensity, and Graviton paths', () => {
		expect(buildCarbonIntensityPath('eu-north-1', 24)).toContain(
			'/api/edge/api/v1/carbon/intensity?region=eu-north-1&hours=24'
		);
		expect(buildGreenSchedulePath('ap-northeast-1', 6)).toContain(
			'/api/edge/api/v1/carbon/schedule?region=ap-northeast-1&duration_hours=6'
		);
		expect(buildGravitonPath('us-east-1')).toContain('/api/edge/api/v1/carbon/graviton?region=us-east-1');
	});
});
