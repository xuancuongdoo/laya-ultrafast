"""Offline: mock backend contract — choose() and field_text(), no I/O."""

import pytest

from backends.mock.model import choose, field_context, field_text


def _page():
    return {
        "url": "https://en.wikipedia.org/wiki/Main_Page",
        "title": "Wikipedia",
        "text": "Search Wikipedia article suggestions mathematics computing",
        "actions": [
            {"id": "e1", "kind": "fill", "label": "Search Wikipedia", "node": 1, "value": ""},
            {"id": "e2", "kind": "click", "label": "Search", "node": 2},
            {"id": "e3", "kind": "click", "label": "Ada Lovelace", "node": 3},
            {"id": "e4", "kind": "click", "label": "Donate now", "node": 4},
        ],
    }


def test_mock_chooses_best_overlap():
    d = choose(_page(), 'On Wikipedia, search for "Ada Lovelace".', [])
    # quoted target outranks everything: e3 matches both quoted words.
    assert d["choice"] == "e3"
    assert d["operation"] == "CLICK"
    assert abs(sum(d["probabilities"].values()) - 1) < 1e-6
    assert d["probabilities"][d["choice"]] == max(d["probabilities"].values())


def test_mock_done_when_quoted_target_visible():
    arrived = dict(_page())
    arrived["url"] = "https://en.wikipedia.org/wiki/Ada_Lovelace"
    arrived["text"] = "Ada Lovelace English mathematician Analytical Engine"
    arrived["title"] = "Ada Lovelace - Wikipedia"
    d = choose(arrived, 'Search for "Ada Lovelace".', [{"choice": "e3", "kind": "click"}])
    assert d["choice"] == "DONE"


def test_mock_not_done_on_search_page():
    page = dict(_page())
    page["text"] = "Search Wikipedia Ada Lovelace suggestions mathematician"
    page["title"] = "Wikipedia, the free encyclopedia"
    d = choose(page, 'Search for "Ada Lovelace" and open the mathematician article.', [])
    assert d["choice"] != "DONE"


def test_mock_skips_satisfied_fill():
    history = [{"choice": "e1", "kind": "fill"}]
    d = choose(_page(), 'On Wikipedia, search for "Ada Lovelace".', history)
    assert d["choice"] != "e1"


def test_mock_avoids_stalled_action():
    history = [
        {"choice": "e3", "kind": "click"},
        {"choice": "e3", "kind": "click"},
    ]
    d = choose(_page(), 'On Wikipedia, search for "Ada Lovelace".', history)
    assert d["choice"] != "e3"


def test_mock_done_blocked_and_targets_observed():
    blocked = choose(_page(), "definitely unrelated zzz qq zz9", [])
    assert blocked["choice"] == "BLOCKED"  # no history yet: nothing to claim
    done = choose(_page(), "definitely unrelated zzz qq zz9", [{"choice": "e1", "kind": "click"}])
    assert done["choice"] == "DONE"
    d = choose(_page(), 'On Wikipedia, search for "Ada Lovelace".', [])
    assert d["choice"].startswith("e")
    for key in ("operation", "target", "confidence", "probabilities", "latency_ms"):
        assert key in d


def test_mock_field_text_from_quoted_goal():
    ctx = field_context('search for "Ada Lovelace"', {"label": "Search Wikipedia"}, _page(), [])
    text, helper = field_text(ctx)
    assert text == "Ada Lovelace"
    assert helper["model"] == "mock"


def test_mock_field_text_needs_quotes():
    ctx = field_context("search for Ada Lovelace", {"label": "Search"}, _page(), [])
    with pytest.raises(ValueError):
        field_text(ctx)
