"""Offline: batching + validation logic, no model calls."""

from backends.laya.model import shortlist, validate_choice


def test_shortlist_chunks():
    cands = {str(i): {"label": "link %d" % i, "value": ""} for i in range(25)}
    batches = shortlist(cands, "open link 14", 10)
    assert [len(b) for b in batches] == [10, 10, 5]
    # keyword match ranks first
    assert list(batches[0])[0] == "14"


def test_validate_choice_rejects_pad():
    ans = {"choice": "1", "confidence": 0.8,
           "probabilities": {"1": 0.8, "0": 0.2}}
    try:
        validate_choice(ans, {"1": {}})
        raise AssertionError("pad leaked through")
    except ValueError:
        pass
