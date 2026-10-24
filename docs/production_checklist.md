# Production checklist (Phase 11)

Walk this before calling the Railway deploy “done”.

| Item | How we satisfy it | Status |
|---|---|---|
| HTTPS | Railway terminates TLS on the public hostname | Needs Railway |
| `/health` returns 200 | Built into AgentOS; proved locally and via `curl $URL/health` after deploy | Local OK |
| Secrets in a manager | Railway Variables / `.env` not committed; see `.env.example` | Local OK |
| Persistent DB volume | Railway Postgres + local Docker volume `pgdata` | Local OK |
| Tracing on | `tracing=True` or `setup_tracing(db=trace_db)` | Local OK |
| Guardrails on | Trader `pre_hooks` (PII, injection, custom ticker) | Local OK |
| HITL on irreversible tools | `propose_trade` / `propose_large_trade` / `set_risk_preference` | Local OK |
| JWT on every protected endpoint | `RUNTIME_ENV=prd` + `JWT_VERIFICATION_KEY` → `authorization=True` | Needs your key |
| Split `db` / `trace_db` | `DATABASE_URL` + `TRACE_DATABASE_URL` | Optional second Postgres |
| Slack against deployed URL | Event URL → `https://<railway>/slack/events` | Needs Slack + deploy |

## Local prod-mode smoke

```powershell
$env:RUNTIME_ENV="prd"
$env:JWT_VERIFICATION_KEY="-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"
$env:TRACE_DATABASE_URL="postgresql+psycopg://ai:ai@localhost:5533/ai"   # optional second DB
python -m app.server
# Unauthenticated POST /agents/chat/runs should be 401; GET /health stays 200
```
