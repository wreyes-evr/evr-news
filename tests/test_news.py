import datetime as dt
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "bot"))
import news  # noqa: E402


def test_item_id_ignores_tracking_and_fragment():
    a = news.item_id("https://www.gov.uk/x/report?utm_source=feed#2026-11-17T09:00:00Z")
    b = news.item_id("https://www.gov.uk/x/report/")
    assert a == b


def test_quote_found_tolerates_typography():
    text = "The department said “schools must not use AI as the sole marker” of coursework."
    assert news.quote_found('schools must not use AI as the sole marker', text)
    assert not news.quote_found("schools must always use AI as the marker for coursework", text)
    assert not news.quote_found("too short", text)


def test_slack_escape():
    assert news.slack_escape("A & B <c>") == "A &amp; B &lt;c&gt;"


def test_pick_mode():
    tue = dt.datetime(2026, 11, 17, 8, 7, tzinfo=news.LONDON)
    wed = dt.datetime(2026, 11, 18, 8, 7, tzinfo=news.LONDON)
    assert news.pick_mode("auto", tue) == "digest"
    assert news.pick_mode("auto", wed) == "alert"
    assert news.pick_mode("alert", tue) == "alert"


def test_build_message_without_summary_keeps_title_and_link():
    item = {"link": "https://example.org/a", "title": "Title <x>", "source": "DfE", "published": "2026-11-18"}
    msg = news.build_message("digest", [(item, None)], dt.date(2026, 11, 18))
    body = msg["blocks"][1]["text"]["text"]
    assert "https://example.org/a" in body and "Title &lt;x&gt;" in body
    assert len(msg["blocks"]) <= 50


def test_dry_run_post_reports_not_posted(capsys):
    assert news.post({"text": "x", "blocks": []}, dry_run=True) is False


def test_missing_webhook_skips_without_touching_state(monkeypatch, tmp_path):
    state = tmp_path / "seen.json"
    monkeypatch.setattr(news, "STATE_PATH", state)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    monkeypatch.delenv("SLACK_WEBHOOK_URL", raising=False)
    monkeypatch.setattr(news, "collect", lambda s: (_ for _ in ()).throw(AssertionError("must not fetch")))
    assert news.main(["--force"]) == 0
    assert not state.exists()


def test_failed_triage_stores_nothing(monkeypatch, tmp_path):
    state = tmp_path / "seen.json"
    monkeypatch.setattr(news, "STATE_PATH", state)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.example/x")
    item = {"id": "a" * 16, "link": "https://e.org/a", "title": "T", "snippet": "", "published": "2026-11-18",
            "source": "DfE", "tier": "official"}
    monkeypatch.setattr(news, "collect", lambda s: ([item], []))
    monkeypatch.setattr(news, "ask", lambda *a, **k: None)
    monkeypatch.setattr(news, "post", lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not post")))
    assert news.main(["--force", "--mode", "digest"]) == 1
    assert not state.exists()
