# Production checklist (Phase 11)

Walk this before calling production "done".

| Item | How we satisfy it | Status |
|---|---|---|
| HTTPS | TLS termination at proxy/gateway | Needs proxy |
| `/health` returns 200 | Built into AgentOS; proved locally | Local OK |
| Secrets in a manager | `.env` not committed; see `.env.example` | Local OK |
| Persistent DB volume | Docker Compose volume `pgdata` | Local OK |
| Tracing on | `tracing=True` or `setup_tracing(db=trace_db)` | Local OK |
| Guardrails on | Trader `pre_hooks` (PII, injection, custom ticker) | Local OK |
| HITL on irreversible tools | `propose_trade` / `propose_large_trade` / `set_risk_preference` | Local OK |
| JWT on every protected endpoint | `RUNTIME_ENV=prd` + `JWT_VERIFICATION_KEY` → `authorization=True` | Local OK |
| Split `db` / `trace_db` | `DATABASE_URL` + `TRACE_DATABASE_URL` | Optional second Postgres |
| Slack against deployed URL | Event URL → `https://<host>/slack/events` | Needs Slack + deploy |

## Local prod-mode smoke

```powershell
$env:RUNTIME_ENV="prd"
$env:JWT_VERIFICATION_KEY="-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"
$env:TRACE_DATABASE_URL="postgresql+psycopg://ai:ai@localhost:5533/ai"   # optional second DB
python -m app.server
# Unauthenticated POST /agents/chat/runs should be 401; GET /health stays 200
```
