type DashboardCaptureFinding = {
	provider: 'aws' | 'azure' | 'gcp';
	finding_id: string;
	resource_id: string;
	resource_type: string;
	monthly_cost: string;
	confidence: 'high' | 'medium' | 'low';
	risk_if_deleted: 'high' | 'medium' | 'low';
	explanation: string;
	confidence_reason: string;
	recommended_action: string;
	connection_id: string;
	owner: string;
	confidence_score: number;
	explainability_notes: string;
	is_gpu?: boolean;
	instance_type?: string;
};

function formatDateOnly(value: Date): string {
	return value.toISOString().split('T')[0] ?? '';
}

function buildDefaultDateRange(): { startDate: string; endDate: string } {
	const end = new Date();
	const start = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
	return {
		startDate: formatDateOnly(start),
		endDate: formatDateOnly(end)
	};
}

const ENGINEERING_FINDINGS: DashboardCaptureFinding[] = [
	{
		provider: 'aws',
		finding_id: 'finding-ec2-idle-1',
		resource_id: 'i-0ac9e73d42f9187f2',
		resource_type: 'EC2 Instance',
		monthly_cost: '842.00',
		confidence: 'high',
		risk_if_deleted: 'medium',
		explanation:
			'Instance utilization stayed below 3% for 14 days, with no deployment tag activity or production traffic attached.',
		confidence_reason: 'Matched against CPU, network, ownership, and deployment history.',
		recommended_action: 'Resize to burstable class or stop outside production hours.',
		connection_id: 'conn-aws-prod',
		owner: 'platform@valdrics.com',
		confidence_score: 0.94,
		explainability_notes:
			'Cost, traffic, and ownership signals agree that this instance is materially underused.',
		instance_type: 'm6i.2xlarge'
	},
	{
		provider: 'aws',
		finding_id: 'finding-ebs-orphan-1',
		resource_id: 'vol-0473c1d239a6de91d',
		resource_type: 'EBS Volume',
		monthly_cost: '386.00',
		confidence: 'high',
		risk_if_deleted: 'low',
		explanation:
			'Volume has been detached for 21 days and is not referenced by any launch template, AMI, or recovery policy.',
		confidence_reason:
			'No compute attachment, no backup policy reference, no snapshot delta changes.',
		recommended_action: 'Archive snapshot, then delete detached volume.',
		connection_id: 'conn-aws-prod',
		owner: 'finops@valdrics.com',
		confidence_score: 0.97,
		explainability_notes:
			'Detached storage with no matching recovery or deployment dependency was found.',
		is_gpu: false
	},
	{
		provider: 'azure',
		finding_id: 'finding-snapshot-stale-1',
		resource_id: 'snap-prd-ledger-2025-12-01',
		resource_type: 'Snapshot',
		monthly_cost: '214.00',
		confidence: 'medium',
		risk_if_deleted: 'medium',
		explanation:
			'Snapshot retention exceeds the current policy and newer validated restore points already exist.',
		confidence_reason: 'Retention history suggests safe archive or policy-based expiration.',
		recommended_action: 'Move to cold retention or expire on next review window.',
		connection_id: 'conn-azure-prod',
		owner: 'security@valdrics.com',
		confidence_score: 0.82,
		explainability_notes:
			'Newer restore points are available and the existing snapshot is outside the stated retention window.'
	}
];

const ZOMBIE_FINDINGS = {
	idle_instances: [ENGINEERING_FINDINGS[0]],
	unattached_volumes: [ENGINEERING_FINDINGS[1]],
	old_snapshots: [ENGINEERING_FINDINGS[2]]
} as const;

export function buildDashboardHeroCaptureData() {
	const { startDate, endDate } = buildDefaultDateRange();

	return {
		user: {
			id: 'user-capture-1',
			tenant_id: 'tenant-capture-1'
		},
		session: null,
		subscription: { tier: 'pro', status: 'active' },
		profile: {
			persona: 'engineering',
			role: 'admin',
			platform_operator: false
		},
		costs: {
			total_cost: 184236.45,
			data_quality: {
				freshness: {
					status: 'final',
					latest_record_date: endDate
				}
			}
		},
		carbon: {
			total_co2_kg: 42.8
		},
		zombies: {
			...ZOMBIE_FINDINGS,
			total_monthly_waste: 1442,
			ai_analysis: {
				total_monthly_savings: '$18,420',
				summary:
					'Three owner-ready actions are carrying the majority of avoidable monthly waste across compute, storage, and backup retention.',
				resources: ENGINEERING_FINDINGS,
				general_recommendations: [
					'Route underused compute to the platform owner before the next planning cycle.',
					'Archive detached storage after backup validation completes.',
					'Collapse stale snapshot retention into the reviewed cold-storage policy.'
				]
			}
		},
		analysis: null,
		allocation: null,
		unitEconomics: null,
		freshness: {
			status: 'final',
			latest_record_date: endDate
		},
		startDate,
		endDate,
		provider: '',
		error: ''
	};
}
