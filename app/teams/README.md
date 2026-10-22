# Teams (Phase 4)

Five specialists: **Sourcer** (web), **DataAnalyst** (Yahoo Finance + portfolio table), **NewsAgent** (headlines),
**RiskAgent** (concentration), **Reporter** (writes the answer). Three teams use them in different ways.

| File | Mode | Use it when | Why this mode |
|---|---|---|---|
| `coordinate.py` | coordinate | The question is open-ended ("research NVDA") | The leader splits the work, asks several specialists and merges the answers. |
| `route.py` | route | The user already knows what they need ("price of AAPL?") | One specialist answers directly. It is the fastest, with no merging step. |
| `broadcast.py` | broadcast | Every specialist should look at the same thing (portfolio risk check) | Each member gets the same task, and the leader combines several viewpoints. |

## Members depend on the user's role

`members.py` has the function that Agno calls on every run:

- `admin` gets all five members, including the RiskAgent
- `viewer` gets four: no RiskAgent

It builds new agent objects each time, so members never share state.

## Reasoning

Agno's `Team` has no `reasoning=True` flag any more. The coordinate team's instructions make the leader start with a
`## Reasoning` section, and `run_phase4.py` saves it with every member's answer to `logs/phase4_reasoning.log`.

## Run

```powershell
python -m app.teams.run_phase4
```
