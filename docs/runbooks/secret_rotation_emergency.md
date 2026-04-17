# Secret Rotation Emergency Runbook

## Trigger

Run this procedure when any local `.env` or deployment secret is suspected exposed.

## Scope

Rotate all high-impact credentials immediately:

- `DATABASE_URL` / DB password or token
- `SUPABASE_JWT_SECRET`
- `ENFORCEMENT_APPROVAL_TOKEN_SECRET`
- `ENFORCEMENT_EXPORT_SIGNING_SECRET`
- `ENCRYPTION_KEY` and fallback encryption keys
- `ADMIN_API_KEY`
- `PAYSTACK_SECRET_KEY`
- `GROQ_API_KEY` / other LLM provider keys
- `SLACK_BOT_TOKEN`
- `SMTP_PASSWORD`

## Procedure

0. Confirm exposure surface:
   - `python3 scripts/security/check_local_env_for_live_secrets.py`

1. Freeze risky operations:
   - Disable remediation/autopilot execution.
   - Restrict admin endpoints at edge/WAF if needed.
2. Rotate secrets at source systems (Supabase, Paystack, Slack, SMTP, and LLM vendors).
3. Update runtime secret store (Google Secret Manager or other provider-managed secret store).
4. Restart services with new credentials.
5. Validate old credentials are invalidated.
6. Review audit logs for use of compromised credentials.
7. Re-enable operations after validation.

## Verification Checklist

- Old credentials rejected by provider APIs.
- App health checks green.
- Auth, billing webhooks, notifications, and DB connectivity verified.
- Incident timeline documented in `docs/runbooks/incident_response.md`.
- Rotation drill evidence updated in `docs/ops/key-rotation-drill-2026-02-27.md` (or newer dated successor) with:
  - `rollback_validation_passed: true`
  - `post_drill_status: PASS`
