import logging
from collections import defaultdict

logger = logging.getLogger("openstates")


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
                logger.warn(msg)
