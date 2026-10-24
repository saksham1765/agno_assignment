#!/usr/bin/env bash
# Phase 11 — deploy Valura AgentOS to Railway (managed Postgres + optional pgvector).
# Prerequisites: railway CLI logged in (`railway login`), Docker not required on the laptop.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Linking / creating Railway project"
if ! railway status >/dev/null 2>&1; then
  railway init
fi

echo "==> Ensuring Postgres plugin"
railway add --database postgres || true

echo "==> Setting runtime env (edit secrets in the Railway dashboard for real keys)"
railway variables set RUNTIME_ENV=prd
railway variables set PORT=8000
# You must paste these in the dashboard (do not commit real values):
#   JWT_VERIFICATION_KEY, LITELLM_API_KEY or GROQ_API_KEY,
#   SLACK_TOKEN, SLACK_SIGNING_SECRET,
#   DATABASE_URL (from the Postgres plugin), TRACE_DATABASE_URL (optional second DB)

echo "==> Deploying"
railway up --detach

echo "==> Public URL"
railway domain || true
echo "When DNS is ready: curl -sS https://\$(railway domain)/health"
echo "Loom + Slack Event URL should point at that hostname."
