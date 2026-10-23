# Connecting Valura to Slack and the AgentOS UI

The server works without Slack (browser chat over AG-UI, the API, and the webhook). Slack turns on by itself
when both secrets exist in `.env`. This is what you need to do, because it has to be done in your Slack account.

## 1. Start the server

```powershell
cd d:\Valura\agno\valura
docker compose up -d db
$env:PYTHONUTF8=1
python -m app.server            # http://localhost:8000   (API docs: /docs)
```

## 2. Look at it in the AgentOS UI (traces, chat, approvals)

1. Open https://os.agno.com and sign in.
2. Add a new OS, choose **Local**, and enter `http://localhost:8000`.
3. Chat with an agent, then open **Traces** to see the tree of model calls and tool calls with their inputs and outputs.
4. Run the `trader` agent ("Buy 1 share of MSFT") to see a paused run, and approve or reject it from the UI.

## 3. Create the Slack app

1. Go to https://api.slack.com/apps and choose **Create New App**.
2. **OAuth & Permissions** - add these bot token scopes:
   `app_mentions:read`, `assistant:write`, `channels:read`, `chat:write`, `im:history`, `im:read`,
   `users:read`, `users:read.email` (the last two are needed for `resolve_user_identity=True`).
3. Install the app to your workspace and copy the **Bot User OAuth Token** (starts with `xoxb-`).
4. **Basic Information** - copy the **Signing Secret**.
5. Add both to `.env`:

```env
SLACK_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...
```

## 4. Give Slack a public address

Slack must reach your computer, so use a tunnel while developing:

```powershell
ngrok http 8000
```

In the Slack app: **Event Subscriptions** -> turn on -> Request URL `https://<your-ngrok-address>/slack/events`
-> subscribe to bot events `app_mention` and `message.im`. Then set **Interactivity** to
`https://<your-ngrok-address>/slack/interactions` (used for approve/reject buttons).

## 5. Try it

Restart the server. You should see no "Slack interface is OFF" line. Send the bot a DM, or `@Valura` in a channel.
Replies in the same thread share one session; a message from you in the browser chat with the same e-mail
shares your memory.

## Webhook

```powershell
curl -X POST http://localhost:8000/webhooks/news -H "Content-Type: application/json" -d '{"ticker": "NVDA"}'
```

Returns `{"ticker": "NVDA", "run_id": "...", "summary": "..."}`. A ticker that is not 1-5 letters gets HTTP 422.

## What is checked by `scripts/prove_phase8.py`, and what is not

Checked on a real local server: the component list, tool inputs and outputs in the trace, memory shared between
the API and AG-UI, one session per Slack thread (with a signed test event), the webhook, and approve/reject over HTTP.

Not checked: real Slack delivery, the e-mail lookup (`resolve_user_identity`), the streaming task cards, and the
os.agno.com UI itself. Those need a real bot and your browser.
