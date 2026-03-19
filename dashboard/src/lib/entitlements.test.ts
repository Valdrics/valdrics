import { describe, expect, it } from 'vitest';

import {
	canAccessAdminHealth,
	canAccessAuditLogs,
	canAccessOpsAcceptanceEvidence,
	canAccessOpsCloseWorkflow,
	canAccessOpsJobSlo
} from './entitlements';

describe('entitlements helpers', () => {
	it('gates audit logs to pro-plus admins', () => {
		expect(canAccessAuditLogs('free', 'admin')).toBe(false);
		expect(canAccessAuditLogs('growth', 'admin')).toBe(false);
		expect(canAccessAuditLogs('pro', 'member')).toBe(false);
		expect(canAccessAuditLogs('pro', 'admin')).toBe(true);
	});

	it('uses the same pro-plus admin gate for advanced ops evidence', () => {
		expect(canAccessOpsJobSlo('growth', 'admin')).toBe(false);
		expect(canAccessOpsAcceptanceEvidence('growth', 'admin')).toBe(false);
		expect(canAccessOpsCloseWorkflow('growth', 'admin')).toBe(false);
		expect(canAccessOpsJobSlo('enterprise', 'owner')).toBe(true);
		expect(canAccessOpsAcceptanceEvidence('enterprise', 'owner')).toBe(true);
		expect(canAccessOpsCloseWorkflow('enterprise', 'owner')).toBe(true);
	});

	it('keeps admin health restricted to platform operators', () => {
		expect(canAccessAdminHealth('admin', false)).toBe(false);
		expect(canAccessAdminHealth('member', true)).toBe(false);
		expect(canAccessAdminHealth('owner', true)).toBe(true);
	});
});
