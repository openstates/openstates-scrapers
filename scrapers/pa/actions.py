import re

_categorizer_rules = (
    (r"(?i)introduced", "introduction"),
    # Committee referred, reported.
    (r"Referred to (?P<committees>.+)", "referral-committee"),
    (r"Re-(referred|committed) to (?P<committees>.+)", "referral-committee"),
    (r"(?i)(re-)?reported", "committee-passage"),
    (
        r"Reported with request to re-refer to (?P<committees>.+)",
        ["referral-committee", "committee-passage"],
    ),
    (r"^Amended on", "amendment-passage"),
    (r"as amended", "amendment-passage"),
    # Governor.
    (r"^Approved by the Governor", "executive-signature"),
    (r"^Presented to the Governor", "executive-receipt"),
    (r"^Became Law without Governor.s signature", "became-law"),
    (r"^Vetoed by the Governor", "executive-veto"),
    # Passage.
    (r"^Final passage", "passage"),
    (r"^Third consideration and final passage", "passage"),
    (r"(?i)adopted", "passage"),
    (r"^First consideration", "reading-1"),
    (r"Second consideration", "reading-2"),
    (r"Third consideration", "reading-3"),
)


def categorize(action):
    for pattern, labels in _categorizer_rules:
        if re.search(pattern, action):
            for label in labels if isinstance(labels, list) else [labels]:
                yield label
