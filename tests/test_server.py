"""Fast tests for the Phase 8 server. They build the app but never call the LLM."""

from fastapi.testclient import TestClient

from app import server


def test_server_has_everything_wired():
    assert len(server.agent_os.teams) == 3
    assert len(server.agent_os.workflows) == 1
    assert server.agent_os.tracing is True
    assert "AGUI" in [type(i).__name__ for i in server.interfaces]


def test_slack_is_off_without_credentials(monkeypatch):
    # The module was built without SLACK_* in the environment, so Slack must not be registered.
    assert "Slack" not in [type(i).__name__ for i in server.interfaces]


def test_webhook_rejects_a_bad_ticker_before_running_anything():
    client = TestClient(server.app)
    for bad in ("NOT A TICKER!", "TOOLONGTICKER", "123", ""):
        assert client.post("/webhooks/news", json={"ticker": bad}).status_code == 422


def test_webhook_requires_a_ticker_field():
    assert TestClient(server.app).post("/webhooks/news", json={}).status_code == 422
