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


def _story(ids, headline, quote_id, quote, detail="", why=""):
    return news.Story(item_ids=ids, emoji="📝", headline=headline, detail=detail,
                      why_it_matters=why, quote=quote, quote_item_id=quote_id)


def test_build_message_has_voice_lead_hits_and_links():
    items = {"a": {"link": "https://e.org/a", "source": "Ofqual"}, "b": {"link": "https://e.org/b", "source": "BBC"}}
    d = news.Digest(intro="Morning all ☕ Busy week for coursework.", signoff="Have a good weekend, all.",
                    lead=_story(["a"], "Ofqual <warns> boards", "a", "q", "Fact.", "Why."),
                    hits=[_story(["b"], "Tories pledge cuts", "b", "q")], also_seen=[])
    msg = news.build_message("digest", d, items, dt.date(2026, 11, 21))
    texts = " ".join(b["text"]["text"] if "text" in b else b["elements"][0]["text"] for b in msg["blocks"] if b["type"] != "divider")
    assert texts.startswith("Morning all")
    assert "Ofqual &lt;warns&gt; boards" in texts and "<https://e.org/a|Ofqual>" in texts
    assert "Quick hits" in texts and "Have a good weekend" in texts
    assert msg["unfurl_links"] is False


def test_story_checks_quote_and_numbers():
    texts = {"a": "Ofqual said that more than 1,100 students lost a whole qualification last year because of malpractice."}
    good = _story(["a"], "1,100 students lost a qualification", "a", "more than 1,100 students lost a whole qualification")
    bad_num = _story(["a"], "2,000 students lost a qualification", "a", "more than 1,100 students lost a whole qualification")
    bad_quote = _story(["a"], "Students lost qualifications", "a", "this sentence is not in the source text at all")
    assert news.story_ok(good, texts)
    assert not news.story_ok(bad_num, texts)
    assert not news.story_ok(bad_quote, texts)


def test_numbers_must_match_whole_numbers():
    src = "published 2,040 pages in 2026 and 150 schools took part"
    assert news.numbers_supported("2,040 pages and 150 schools", src)
    assert not news.numbers_supported("40% of schools", src)
    assert not news.numbers_supported("15 schools", src)


def test_quote_must_come_from_the_story_itself():
    texts = {"a": "Ofqual wrote to awarding organisations about misuse of AI in coursework this week.",
             "b": "Unrelated text about something else entirely in another document."}
    s = _story(["b"], "Ofqual writes to exam boards", "a", "wrote to awarding organisations about misuse of AI")
    assert not news.story_ok(s, texts)


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
