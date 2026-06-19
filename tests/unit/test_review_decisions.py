"""Unit tests for the SQLite-backed reviewer-decision store (no data store needed)."""

from review_decisions import REVIEW_STATUSES, ReviewDecisionStore


def test_empty_workspace_listing(tmp_path):
    store = ReviewDecisionStore(tmp_path / "rev.sqlite3")
    listing = store.list_for_workspace("ws1")
    assert listing["ok"] is True
    assert listing["decisions"] == []
    assert listing["summary"]["total_recorded"] == 0
    assert listing["source_gis_modified"] is False


def test_set_get_roundtrip(tmp_path):
    store = ReviewDecisionStore(tmp_path / "rev.sqlite3")
    result = store.set_decision("ws1", {"generator_id": "g1", "status": "reviewed", "note": "n", "assignee": "a"})
    assert result["ok"] is True
    assert result["decision"]["status"] == "reviewed"
    assert result["decision"]["assignee"] == "a"
    assert result["decision"]["updated_at_utc"]

    listing = store.list_for_workspace("ws1")
    assert len(listing["decisions"]) == 1
    assert listing["summary"]["reviewed"] == 1
    assert listing["summary"]["total_recorded"] == 1


def test_upsert_replaces_existing(tmp_path):
    store = ReviewDecisionStore(tmp_path / "rev.sqlite3")
    store.set_decision("ws1", {"generator_id": "g1", "status": "to_review"})
    store.set_decision("ws1", {"generator_id": "g1", "status": "dismissed", "note": "later"})
    listing = store.list_for_workspace("ws1")
    assert len(listing["decisions"]) == 1
    assert listing["decisions"][0]["status"] == "dismissed"
    assert listing["decisions"][0]["note"] == "later"


def test_invalid_status_rejected(tmp_path):
    store = ReviewDecisionStore(tmp_path / "rev.sqlite3")
    result = store.set_decision("ws1", {"generator_id": "g1", "status": "bogus"})
    assert result.get("error") == "review_decision_invalid_status"
    assert set(REVIEW_STATUSES).issubset(set(result["allowed"]))


def test_missing_target_rejected(tmp_path):
    store = ReviewDecisionStore(tmp_path / "rev.sqlite3")
    assert store.set_decision("ws1", {"status": "reviewed"}).get("error") == "review_decision_target_required"
    assert store.list_for_workspace("").get("error") == "review_decisions_workspace_required"


def test_note_and_assignee_truncated(tmp_path):
    store = ReviewDecisionStore(tmp_path / "rev.sqlite3")
    result = store.set_decision("ws1", {"generator_id": "g1", "status": "reviewed", "note": "x" * 5000, "assignee": "y" * 500})
    assert len(result["decision"]["note"]) == 4000
    assert len(result["decision"]["assignee"]) == 200


def test_workspace_isolation(tmp_path):
    store = ReviewDecisionStore(tmp_path / "rev.sqlite3")
    store.set_decision("ws1", {"generator_id": "g1", "status": "reviewed"})
    store.set_decision("ws2", {"generator_id": "g1", "status": "dismissed"})
    ws1 = store.list_for_workspace("ws1")
    ws2 = store.list_for_workspace("ws2")
    assert ws1["decisions"][0]["status"] == "reviewed"
    assert ws2["decisions"][0]["status"] == "dismissed"


def test_persists_across_instances(tmp_path):
    db = tmp_path / "rev.sqlite3"
    ReviewDecisionStore(db).set_decision("ws1", {"generator_id": "g1", "status": "reviewed"})
    # a fresh store over the same file sees the persisted decision (durability)
    reopened = ReviewDecisionStore(db)
    assert reopened.list_for_workspace("ws1")["summary"]["reviewed"] == 1
