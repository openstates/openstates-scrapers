"""python -m pytest scripts/test_compare_scrapes.py"""
import json

import compare_scrapes as cs

LOWER, UPPER = '~{"classification": "lower"}', '~{"classification": "upper"}'


def write_side(tmp_path, name, chamber, classification, option):
    side = tmp_path / name
    side.mkdir()
    for i in range(3):
        bill = {
            "_id": f"b{i}",
            "identifier": f"SB {i}",
            "legislative_session": "2025",
            "actions": [
                {
                    "date": "2025-01-01",
                    "description": "Passed",
                    "organization_id": chamber,
                    "classification": classification,
                }
            ],
        }
        vote = {
            "_id": f"v{i}",
            "identifier": f"RC {i}",
            "bill_identifier": f"SB {i}",
            "legislative_session": "2025",
            "votes": [{"voter_name": "Geiss", "option": option}, {"voter_name": "Smith", "option": "yes"}],
        }
        (side / f"bill_{i}.json").write_text(json.dumps(bill))
        (side / f"vote_event_{i}.json").write_text(json.dumps(vote))
    store = cs.RecordStore(side)
    store.index, store.vocab, store.counts = cs.index_store(store)
    return store


def test_report_and_examples(tmp_path):
    pre = write_side(tmp_path, "pre", LOWER, [], "no")
    post = write_side(tmp_path, "post", UPPER, ["passage"], "other")
    report = cs.summarize(pre, post)

    assert "| vote_events.votes | 6 | 6 |  |" in report
    # A classification list counts as one value, so "none" gets its own row.
    assert "| bills `actions.*.classification` | before | after |" in report
    assert "| `(none)` | 3 | 0 |" in report
    assert "| `passage` | 0 | 3 |" in report
    assert "| `other` | 0 | 3 |" in report
    # Entries that are whole objects get no "votes" table of their own.
    assert "`votes` |" not in report

    examples = "\n".join(cs.show_records(pre, post, ["sb1"]))
    assert "### bills ('2025', 'SB 1')" in examples
    assert "### vote_events ('2025', 'SB 1', 'RC 1')" in examples
    # Only the changed voter is shown, with the record's identifying fields.
    assert '"Geiss"' in examples and '"Smith"' not in examples
    assert '"bill_identifier": "SB 1"' in examples
    assert "No changed record matches `SB 9`." in "\n".join(cs.show_records(pre, post, ["SB 9"]))
