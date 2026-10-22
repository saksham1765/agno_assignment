# Valura security model (Phase 7)

Valura never moves money on its own. Every trade tool is gated by a human step.
`execute_trade` is a **stub**: it only writes a row to `ai.trades`. There is no brokerage.

## The three HITL tiers

| Tier | Decorator | Who decides | Used by | What is stored |
|---|---|---|---|---|
| 1. Confirmation | `@tool(requires_confirmation=True)` | The user, in the same session | `propose_trade` (notional up to $10K) | Nothing extra; run pauses, then `continue_run` |
| 2. Required approval | `@approval(type="required")` + `requires_confirmation` | An **admin**, in the database | `propose_large_trade` (notional over $10K) | A `pending` row in `ai.agno_approvals`, resolved to `approved`/`rejected` by the admin |
| 3. Audit | `@approval(type="audit")` + `requires_confirmation` | The user (no admin gate) | `record_trade_note` | An audit record in `ai.agno_approvals` after the user answers |

Flow for tier 2: the run pauses and a pending approval is written. `app/agents/admin.py` plays the admin
(it lists pending approvals and resolves them). Only after `approved` does `continue_run` execute the trade.
A rejected approval means the tool never runs.

`requires_user_input` (the third HITL primitive in the PDF) is not used by any trade tool here.

## Guardrails (`pre_hooks` on the Trader agent)

1. `PIIDetectionGuardrail(mask_pii=True)` - SSN, card, email and phone numbers are replaced with `*` before the model sees them.
2. `PromptInjectionGuardrail()` - known jailbreak phrases raise `InputCheckError`; the run ends with status `error` and no tool runs (fails closed).
3. `TickerPermissionGuardrail` (custom, `app/hooks/guardrails.py`) - blocks any known ticker not in the user's allow-list.

Limits: these are pattern checks, not a guarantee. The injection guardrail matches fixed phrases only.

## Audit trail

`app/hooks/audit.py` is a `@hook(run_in_background=True)` post-hook that writes one row to `ai.audit_log`
for each trade tool that was confirmed or approved. Rejected calls are not logged as actions.
It runs in the background only under AgentOS; a direct `agent.run()` executes it inline.

## Not covered

- No real authentication: "admin" is a fixed id in `admin.py`. Phase 11 adds JWT-based auth.
- The ticker allow-list is passed when the agent is built, not read from `session_state` at run time.
