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
2. `PromptInjectionGuardrail()` - Agno's list of about 18 jailbreak phrases. A match ends the run with status `error`; no tool runs (fails closed).
3. `StrongerInjectionGuardrail` (ours) - a wider phrase list, matched after lower-casing, swapping look-alike characters (`1gnore` becomes `ignore`) and squeezing spaces.
4. `TickerPermissionGuardrail` (ours, `app/hooks/guardrails.py`) - blocks any known ticker, or company name such as "Tesla", that is not on the user's allow-list.
   The list is read from `session_state["permitted_tickers"]` for each run, with the list given when the agent was built as the default.

Limits: these are pattern checks, not a guarantee. A new jailbreak wording, or a company that is not in `COMPANY_NAMES`, gets through.
The human confirmation step is the real protection, because no trade runs without a yes.

## Trade safety

`execute_trade` refuses (returns `REFUSED: ...`) a bad side, a quantity of 0 or less, a buy that costs more than the user's cash
(`STARTING_CASH_USD` minus earlier buys plus sells), and a sell of more shares than the user holds. Trades are saved under the
`user_id` of the run, at Yahoo Finance's latest price.

## Audit trail

`app/hooks/audit.py` is a `@hook(run_in_background=True)` post-hook that writes one row to `ai.audit_log`
for each trade tool that was confirmed or approved. Rejected calls are not logged as actions.
It runs in the background only under AgentOS; a direct `agent.run()` executes it inline.

## Not covered

- No real authentication: "admin" is a fixed id in `admin.py`. Phase 11 adds JWT-based auth.
- Cash is a pretend balance (`STARTING_CASH_USD`); nothing is connected to a brokerage.
