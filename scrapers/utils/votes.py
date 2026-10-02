import logging
from collections import defaultdict

logger = logging.getLogger("openstates")


def safe_lookup(mapping, key, *, what, context=None):
    """Look up `key` in a hardcoded classification `mapping` (a vote-result or vote-choice
    enum sourced from a legislature's own site). These sites don't publish a schema or
    enumerated list of valid values for this kind of field -- new phrasing only turns up by
    encountering it in real data -- so a bare `mapping[key]` crashes the whole scrape the
    first time a legislature uses a string the mapping doesn't have yet.

    On a miss, logs a clear warning naming `what` and the exact unmapped value instead of
    raising, and returns None so the caller can skip just the affected row (one vote_event, or
    one voter's row within it) rather than losing everything scraped after that point.
    """
    if key in mapping:
        return mapping[key]
    msg = f"Unmapped {what}: {key!r}"
    if context:
        msg += f" ({context})"
    logger.warning(msg)
    return None


def check_counts(vote, raise_error=False):
    expected_counts = defaultdict(int)
    actual_counts = defaultdict(int)

    for item in vote.counts:
        expected_counts[item["option"]] = item["value"]
    for item in vote.votes:
        actual_counts[item["option"]] += 1

    for how in set(expected_counts.keys()) | set(actual_counts.keys()):
        expected = expected_counts[how]
        actual = actual_counts[how]
        if expected != actual:
            names = [v["voter_name"] for v in vote.votes if v["option"] == how]
            msg = f"{vote}: {how} count mismatch, expected={expected} actual={actual} (names: {names})"
            if raise_error:
                raise ValueError(msg)
            else:
                logger.warning(msg)
