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
