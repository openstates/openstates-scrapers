#!/usr/bin/env python3
"""Report data problems in scrape output that the schema doesn't catch.

    python scripts/check_scrape.py _data/<jurisdiction> [more dirs or zips]

Reads the bill_*, vote_event_* and jurisdiction_* JSON that os-update writes
(a directory, or a zip of one) and prints how many objects fail each check,
with a few examples. Run it on the before and after output of a scraper change
and compare the numbers. Every check is a heuristic, so a problem is a lead to
look at, not proof of a bug.
"""

import datetime
import json
import re
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

EXAMPLES = 3
NOT_A_NAME = re.compile(
    r"\d|^.$|^(yeas?|nays?|ayes?|noes?|absent|excused|present|not voting|total"
    r"|votes?|certification|(mr|madam)\.? (speaker|president))$",
    re.IGNORECASE,
)
PREFIX_CHAMBER = {"H": "lower", "A": "lower", "S": "upper"}


def load(path):
    """Yield (filename, object) for every JSON file in a directory or zip."""
    path = Path(path)
    if path.is_dir():
        for f in sorted(path.glob("*.json")):
            yield f.name, json.loads(f.read_text())
    else:
        with zipfile.ZipFile(path) as z:
            for name in sorted(z.namelist()):
                if name.endswith(".json"):
                    yield Path(name).name, json.loads(z.read(name))


def chamber(pseudo_id):
    if pseudo_id and pseudo_id.startswith("~"):
        return json.loads(pseudo_id[1:]).get("classification")
    return None


def day(value):
    try:
        return datetime.date.fromisoformat(value[:10])
    except (TypeError, ValueError):
        return None


def check(path):
    bills, votes, sessions = [], [], {}
    for name, obj in load(path):
        if name.startswith("bill_"):
            bills.append(obj)
        elif name.startswith("vote_event_"):
            votes.append(obj)
        elif name.startswith("jurisdiction_"):
            for s in obj.get("legislative_sessions", []):
                sessions[s["identifier"]] = (
                    day(s.get("start_date")),
                    day(s.get("end_date")),
                )

    problems = defaultdict(list)

    def other_session(session, value):
        """The session a date falls in, if it's outside its own session's dates."""
        d = day(value)
        start, end = sessions.get(session, (None, None))
        if not (d and start and end) or start <= d <= end:
            return None
        for other, (s, e) in sessions.items():
            if s and e and s <= d <= e:
                return other

    seen_bills = Counter((b["legislative_session"], b["identifier"]) for b in bills)
    for key, n in seen_bills.items():
        if n > 1:
            problems["bill scraped more than once"].append(f"{key[1]} ({key[0]}) x{n}")

    for b in bills:
        label = f"{b['identifier']} ({b['legislative_session']})"
        expected = PREFIX_CHAMBER.get(b["identifier"][:1].upper())
        actual = chamber(b.get("from_organization"))
        if expected and actual in ("lower", "upper") and actual != expected:
            problems["bill chamber doesn't match its prefix"].append(
                f"{label}: {actual}"
            )
        for a in b.get("actions", []):
            if len(set(a["classification"])) != len(a["classification"]):
                problems["action has a repeated classification"].append(
                    f"{label} {a['date']} {a['description']!r}: {a['classification']}"
                )

    seen_votes = defaultdict(list)
    for v in votes:
        label = f"{v.get('bill_identifier') or v.get('bill')} {v['start_date'][:10]} {v['motion_text']!r}"
        counts = {c["option"]: c["value"] for c in v["counts"]}
        roll = Counter(r["option"] for r in v["votes"])
        names = Counter(r["voter_name"] for r in v["votes"])

        if not any(counts.values()):
            problems["vote has no counts"].append(label)
        elif v["votes"]:
            off = {
                o: (counts.get(o, 0), roll[o])
                for o in set(counts) | set(roll)
                if counts.get(o, 0) != roll[o]
            }
            if off:
                detail = ", ".join(
                    f"{o} {c} counted/{n} named" for o, (c, n) in sorted(off.items())
                )
                problems["vote count doesn't match the named voters"].append(
                    f"{label}: {detail}"
                )
        for voter, n in names.items():
            if n > 1:
                problems["voter appears twice in one vote"].append(
                    f"{label}: {voter} x{n}"
                )
            if NOT_A_NAME.search(voter):
                problems["voter name looks like a header, count or title"].append(
                    f"{label}: {voter!r}"
                )
        other = other_session(v["legislative_session"], v["start_date"])
        if other:
            problems["vote is dated in another session"].append(
                f"{label}: filed under {v['legislative_session']}, date is in {other}"
            )

        key = (
            v.get("bill_identifier") or v.get("bill"),
            v["start_date"],
            v["motion_text"],
            v.get("organization"),
            tuple(sorted(counts.items())),
            tuple(sorted((r["option"], r["voter_name"]) for r in v["votes"])),
        )
        seen_votes[key].append(label)
    for labels in seen_votes.values():
        if len(labels) > 1:
            problems["same vote saved more than once"].append(
                f"{labels[0]} x{len(labels)}"
            )

    print(f"## {path}: {len(bills)} bills, {len(votes)} votes\n")
    if not problems:
        print("No problems found.\n")
    for name, found in sorted(problems.items(), key=lambda kv: -len(kv[1])):
        print(f"- {name}: {len(found)}")
        for example in found[:EXAMPLES]:
            print(f"    - {example}")
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for arg in sys.argv[1:]:
        check(arg)
