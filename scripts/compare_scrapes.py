#!/usr/bin/env python3
"""Deterministically diff a pre-change scrape against a post-change scrape.

Pre-change data: latest bulk data JSON from https://open.pluralpolicy.com/data/,
auto-fetched by default (jurisdiction is auto-detected from --post; requires
OPENSTATES_EMAIL / OPENSTATES_PASSWORD env vars for login). Pass --pre to override
with a local directory/zip or an explicit URL instead.
Post-change data: the download attached to a PR (fork release asset, uploaded zip,
or a raw directory) in the same schema.

The two sides are not always the same shape: a published archive is the imported
product of earlier scrapes, so it renames some fields, carries others the scraper
never writes, and folds each bill's vote events into the bill itself. Those votes
are lifted back out into vote_event records, aliased fields are renamed to the
scraper's spelling, and fields genuinely present on only one side are reported as
schema differences instead of changes -- but only when the two sides were produced
differently, so a scrape-to-scrape comparison still diffs every field.

Records are matched by (legislative_session, identifier) so vote_events are matched
by (legislative_session, bill_identifier, identifier) since they lack a bill identifier
field directly usable across runs -- see RECORD_KEY_FIELDS. Some jurisdictions (e.g. AZ)
never populate vote_events.identifier; when it's blank, vote_events fall back to
(legislative_session, bill_identifier, start_date, motion_text) instead -- see record_key.

Usage:
    python scripts/compare_scrapes.py --post PATH_OR_URL
    python scripts/compare_scrapes.py --pre PATH_OR_URL --post PATH_OR_URL
    python scripts/compare_scrapes.py --pre ... --post ... --show "SB 602"

The report is markdown, laid out to paste into a PR: a before/after counts table,
a value breakdown for each low-cardinality field that changed (e.g. how many
actions are filed under each chamber), then every change pattern. --show adds the
named records before and after, trimmed to the fields that differ, for a PR's bug
and resolution examples. scripts/scrape_before_after.sh produces both sides from
one cache and runs this.

PATH may be a directory of .json files, or a .zip containing them; either shape may
hold one record per file (scraper output) or a single JSON array of records (the
published bulk archives). If it looks like an http(s) URL it is downloaded first.
Records are streamed and read one at a time, so a full jurisdiction fits in a CI
runner's memory.
"""
from __future__ import annotations

import argparse
import http.cookiejar
import io
import json
import os
import re
import shutil
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path
from typing import Iterator

PLURAL_BASE_URL = "https://open.pluralpolicy.com"

# Buffer size for streaming reads of the large single-file bulk archives.
READ_CHUNK = 1 << 20

# Fields whose values are expected to change between any two scrapes and would
# otherwise drown real diffs in noise. "bill" is the UUID a vote_event uses to
# point at its bill and "parent_id" the UUID a chamber uses to point at its
# legislature; both are minted fresh on every run, so they never match.
VOLATILE_FIELDS = {"scraped_at", "_id", "dedupe_key", "bill", "parent_id"}

# The published bulk archives are the imported product of earlier scrapes, so the
# same field can arrive under two names. Renamed on read, before keying or diffing,
# so both sides speak the scraper's vocabulary. Without this the two spellings read
# as one whole list removed and another added, and changes *within* the list -- a
# dropped sponsor, the thing a scraper change is most likely to break -- are never
# compared at all.
FIELD_ALIASES = {"sponsors": "sponsorships"}

# Fields that exist on one side only because of how that side was produced: the
# importer adds some, and the scraper's own bookkeeping is dropped or transformed
# on the way in. They would otherwise report as added or removed on every single
# record. Only suppressed for a field genuinely absent from one side throughout
# (see one_sided_fields), so a scrape-to-scrape comparison still diffs all of them.
SCHEMA_ONLY_FIELDS = {
    # added by the importer, never present in scraper output
    "chamber",
    "id",
    "jurisdiction_name",
    "raw_text",
    "raw_text_url",
    "votes",
    # scraper-side bookkeeping the importer drops or reshapes
    "citations",
    "extras",
    "from_organization",
    "jurisdiction",
    "other_identifiers",
    # sponsor identity resolved at import time, so absent from a fresh scrape
    "entity_type",
    "person_id",
    "organization_id",
    # vote_events: the importer folds these into the bill and reshapes them on the
    # way, so an extracted vote event carries the scrape's fields under other names
    # or not at all. The tallies, the roll call, and the motion still line up.
    "organization__classification",
    "organization",
    "bill_action",
    "end_date",
    "sources",
}

# How to identify one entry inside a list-valued field (votes, actions, sponsorships,
# sources, versions...), tried in order; the first tuple present and unique on both
# sides wins. See list_item_key_fields.
LIST_ITEM_KEY_CANDIDATES = [
    ("voter_name",),
    ("url",),
    ("date", "description"),
    ("name", "classification"),
    ("identifier",),
    ("note", "date"),
    ("name",),
    ("description",),
    ("note",),
    ("classification",),
]

# Above this many distinct values for one (record type, field, change kind), the
# report rolls them into a single line with samples rather than listing each.
MAX_DISTINCT_VALUES = 5

# A changed field gets a before/after value breakdown table when it takes at most
# this many distinct values on each side: chambers and classifications, not dates.
BREAKDOWN_MAX_VALUES = 8

# --show prints at most this many records per name, so a bill with a hundred
# changed vote events does not bury the rest.
MAX_SHOWN = 10

# Fields kept in a --show excerpt even when unchanged, so it says which record it is.
CONTEXT_FIELDS = ("identifier", "bill_identifier", "legislative_session", "motion_text", "start_date", "name")

# How to build a stable identity key per object type (checked in order).
RECORD_KEY_FIELDS = [
    ("vote_events", ("legislative_session", "bill_identifier", "identifier")),
    ("bills", ("legislative_session", "identifier")),
    ("events", ("name", "start_date")),
    ("organizations", ("name", "classification")),
    ("jurisdictions", ("id",)),
]


def detect_jurisdiction_name(store: "RecordStore") -> str | None:
    """Pull the full jurisdiction name (e.g. "Virginia") off any record."""
    for _ref, obj in store.entries():
        name = (obj.get("jurisdiction") or {}).get("name") or obj.get("jurisdiction_name")
        if name:
            return name
    return None


def login_to_pluralpolicy(email: str, password: str) -> urllib.request.OpenerDirector:
    """Mirrors govglow's plural-auth.ts: django-allauth form login, cookie-jar session."""
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    login_url = f"{PLURAL_BASE_URL}/accounts/login/"

    login_page = opener.open(login_url).read().decode()
    csrf_match = re.search(r'name="csrfmiddlewaretoken" value="([^"]+)"', login_page)
    if not csrf_match:
        raise RuntimeError("OpenStates bulk data login page did not contain a CSRF token.")

    data = urllib.parse.urlencode(
        {"csrfmiddlewaretoken": csrf_match.group(1), "login": email, "password": password}
    ).encode()
    request = urllib.request.Request(login_url, data=data, headers={"Referer": login_url})
    opener.open(request).read()

    if not any(c.name == "sessionid" for c in jar):
        raise RuntimeError("OpenStates bulk data login failed -- check OPENSTATES_EMAIL/OPENSTATES_PASSWORD.")
    return opener


def resolve_latest_bulk_url(opener: urllib.request.OpenerDirector, jurisdiction_name: str) -> str:
    """Latest session-json archive URL for a jurisdiction, per the authenticated
    listing page's "(updated YYYY-MM-DD)" labels -- there is no stable URL template,
    this listing is the only place session -> archive-URL mappings are published."""
    listing_url = f"{PLURAL_BASE_URL}/data/session-json/"
    html = opener.open(listing_url).read().decode()

    anchor = f'<a name="{jurisdiction_name}">'
    start = html.find(anchor)
    if start == -1:
        raise RuntimeError(f'No "{jurisdiction_name}" section on the OpenStates session-json listing page.')
    section_end = html.find('<a name="', start + len(anchor))
    section = html[start : section_end if section_end != -1 else None]

    entries = re.findall(r'<a href="([^"]+)">\s*[^<]+?\s*</a>\s*\(updated (\d{4}-\d{2}-\d{2})\)', section)
    if not entries:
        raise RuntimeError(f"No bulk data sessions found for {jurisdiction_name}.")
    href, _ = max(entries, key=lambda e: e[1])
    return urllib.parse.urljoin(PLURAL_BASE_URL, href)


def fetch_latest_bulk_data(jurisdiction_name: str) -> Path:
    email, password = os.environ.get("OPENSTATES_EMAIL"), os.environ.get("OPENSTATES_PASSWORD")
    if not email or not password:
        raise RuntimeError(
            "No --pre given and OPENSTATES_EMAIL/OPENSTATES_PASSWORD are not set -- "
            "either set them to auto-fetch the latest bulk data, or pass --pre explicitly."
        )
    print(f"Logging into {PLURAL_BASE_URL} ...", file=sys.stderr)
    opener = login_to_pluralpolicy(email, password)
    url = resolve_latest_bulk_url(opener, jurisdiction_name)
    print(f"Fetching latest {jurisdiction_name} bulk data: {url}", file=sys.stderr)
    tmp = Path(tempfile.mkdtemp()) / "pre.zip"
    with opener.open(url) as resp, tmp.open("wb") as out:
        shutil.copyfileobj(resp, out)
    return tmp


def iter_json_array(fp) -> Iterator[dict]:
    """Yield the elements of a top-level JSON array without holding the whole thing.

    The published bulk archives are a single file containing one array of every
    bill in a session -- 146MB of text for California, which json.load turns into
    something on the order of a gigabyte of dicts. Decode one element at a time
    off a sliding buffer instead."""
    decoder = json.JSONDecoder()
    text = io.TextIOWrapper(fp, encoding="utf-8")
    buf = text.read(READ_CHUNK)
    pos = buf.index("[") + 1 if "[" in buf else 0

    while True:
        # Skip the separators between elements, refilling if the buffer runs dry.
        while True:
            stripped = len(buf) - len(buf[pos:].lstrip(" \t\r\n,"))
            pos = stripped
            if pos < len(buf):
                break
            chunk = text.read(READ_CHUNK)
            if not chunk:
                return
            buf, pos = buf[pos:] + chunk, 0
        if buf[pos] == "]":
            return

        while True:
            try:
                obj, end = decoder.raw_decode(buf, pos)
                break
            except ValueError:
                chunk = text.read(READ_CHUNK)
                if not chunk:
                    return  # trailing garbage or a truncated file
                buf += chunk
        yield obj
        # Drop the consumed prefix so the buffer stays near one element in size.
        buf, pos = buf[end:], 0


class RecordStore:
    """Random access to the JSON records in a directory or zip, one record at a time.

    A full jurisdiction is far too big to hold in memory on a CI runner, and a
    comparison needs two of them at once. So nothing is bulk-extracted and no
    record is retained: each is parsed only for as long as it takes to key or
    diff it. Records that arrive inside a JSON array are spilled to individual
    temp files on the way past, since the diff needs to revisit them by key and
    re-scanning a 146MB array per lookup would not finish.
    """

    def __init__(self, path: Path):
        self.path = path
        self.zip = None
        self._spill_dir = None
        self._spilled = 0
        if not path.is_dir():
            if not zipfile.is_zipfile(path):
                raise ValueError(f"{path} is neither a directory nor a zip file")
            self.zip = zipfile.ZipFile(path)

    def _members(self) -> list[str]:
        if self.zip is not None:
            return [i.filename for i in self.zip.infolist() if not i.is_dir() and i.filename.endswith(".json")]
        return [str(f.relative_to(self.path)) for f in self.path.rglob("*.json")]

    def _open(self, member: str):
        return self.zip.open(member) if self.zip is not None else (self.path / member).open("rb")

    def entries(self) -> Iterator[tuple]:
        """Yield (ref, record) for every record in the source, parsed one at a time.

        A ref is an opaque handle to re-read that record later, via read()."""
        for member in self._members():
            label = Path(member).name
            with self._open(member) as fp:
                head = fp.read(READ_CHUNK)
                if head.lstrip()[:1] == b"[":
                    with self._open(member) as full:
                        for obj in iter_json_array(full):
                            yield from self._emit(label, obj, spill=True)
                    continue
                while True:  # a single record, but possibly larger than one chunk
                    chunk = fp.read(READ_CHUNK)
                    if not chunk:
                        break
                    head += chunk
            try:
                obj = json.loads(head)
            except json.JSONDecodeError:
                continue
            yield from self._emit(label, obj, spill=False, member=member)

    def _emit(self, label: str, obj: dict, spill: bool, member: str = "") -> Iterator[tuple]:
        """The record itself, plus any records that have to be lifted out of it."""
        obj = apply_aliases(obj)
        yield (self._spill(label, obj) if spill else ("member", member, label)), obj
        # Bills only: a vote_event's own "votes" field is its roll call, not a
        # nested set of vote events, and lifting those out would invent a record
        # per voter.
        if classify(label, obj) == "bills":
            for vote_event in extract_vote_events(obj):
                yield self._spill("vote_event.json", vote_event), vote_event

    def _spill(self, label: str, obj: dict) -> tuple:
        if self._spill_dir is None:
            self._spill_dir = Path(tempfile.mkdtemp())
        self._spilled += 1
        path = self._spill_dir / f"{self._spilled}.json"
        path.write_text(json.dumps(obj))
        return ("spill", str(path), label)

    def read(self, ref: tuple) -> dict:
        kind, locator, _ = ref
        if kind == "spill":
            return json.loads(Path(locator).read_text())  # already aliased when spilled
        raw = self.zip.read(locator) if self.zip is not None else (self.path / locator).read_bytes()
        return apply_aliases(json.loads(raw))


def fetch_local(path_or_url: str) -> Path:
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        print(f"Downloading {path_or_url} ...", file=sys.stderr)
        tmp = Path(tempfile.mkdtemp()) / "download.zip"
        # Streamed rather than read() into memory: these archives run to hundreds
        # of megabytes and both sides are downloaded in the same process.
        with urllib.request.urlopen(path_or_url) as resp, tmp.open("wb") as out:
            shutil.copyfileobj(resp, out)
        return tmp
    return Path(path_or_url)


def classify(filename: str, obj: dict) -> str:
    if filename.startswith("vote_event") or "bill_identifier" in obj:
        return "vote_events"
    if filename.startswith("bill") or ("identifier" in obj and "actions" in obj):
        return "bills"
    if filename.startswith("event"):
        return "events"
    if filename.startswith("organization"):
        return "organizations"
    if filename.startswith("jurisdiction"):
        return "jurisdictions"
    return "other"


def record_key(record_type: str, obj: dict):
    if record_type == "vote_events" and not obj.get("identifier"):
        # Some jurisdictions (e.g. AZ) never set vote_events.identifier, so every
        # vote on a bill would otherwise collapse to the same key and get paired
        # with an arbitrary other vote on that bill. Fall back to (start_date,
        # motion_text), which is unique per vote even when identifier is blank.
        return (
            obj.get("legislative_session"),
            obj.get("bill_identifier"),
            obj.get("start_date"),
            obj.get("motion_text"),
        )
    fields = dict(RECORD_KEY_FIELDS).get(record_type, ("identifier",))
    return tuple(obj.get(f) for f in fields)


def index_store(store: RecordStore) -> tuple[dict, dict, dict]:
    """({record type: {identity key: member path}}, {record type: field names seen},
    {record type: {"records" or list field: count}}).

    The second return value is the side's field vocabulary, used to tell a field
    that one side never produces from one a change actually removed. The third
    counts records and the entries of their list fields (actions, votes...) for
    the report's counts table.

    Only keys and member paths are kept, never the records themselves, so the
    index of a whole jurisdiction stays small enough to hold both sides at once.

    AZ runs the same motion text on the same bill on the same day more than once
    (250 such groups in a single session), so a plain dict comprehension keeps
    whichever file the filesystem yielded last -- which differs between runs and
    makes two unrelated vote events look like a huge diff. Rank the members of a
    colliding group deterministically instead and pair them off by rank.
    """
    groups = defaultdict(lambda: defaultdict(list))
    vocab = defaultdict(set)
    counts = defaultdict(lambda: defaultdict(int))
    for ref, obj in store.entries():
        record_type = classify(ref[2], obj)
        groups[record_type][record_key(record_type, obj)].append(ref)
        field_names(obj, vocab[record_type])
        counts[record_type]["records"] += 1
        for field, value in obj.items():
            if isinstance(value, list):
                counts[record_type][field] += len(value)

    indexed = {}
    for record_type, by_key in groups.items():
        resolved = {}
        for key, members in by_key.items():
            if len(members) == 1:
                resolved[key] = members[0]
                continue
            # Rare enough that re-reading the colliding records to rank them costs
            # nothing next to holding every record in memory to avoid it.
            members.sort(key=lambda m: collision_rank(store.read(m)))
            for i, ref in enumerate(members):
                resolved[key + (f"#{i}",)] = ref
        indexed[record_type] = resolved
    return indexed, vocab, counts


def extract_vote_events(bill: dict) -> Iterator[dict]:
    """Lift a bulk bill's embedded votes out into standalone vote_event records.

    A scraper writes one file per vote event; the importer folds them into the
    bill it belongs to. Left alone, the two sides share no vote records at all
    and every vote regression -- miscounted tallies, missing roll calls, dropped
    voters -- goes unreported. The identifying fields a vote_event is keyed on
    that the embedded copy lacks are exactly the ones its parent bill carries."""
    for vote in bill.get("votes") or []:
        if not isinstance(vote, dict):
            continue
        yield {
            **vote,
            "bill_identifier": bill.get("identifier"),
            "legislative_session": bill.get("legislative_session"),
        }


def apply_aliases(obj: dict) -> dict:
    """Rename bulk-archive spellings to the scraper's, in place."""
    for old, new in FIELD_ALIASES.items():
        if old in obj and new not in obj:
            obj[new] = obj.pop(old)
    return obj


def field_names(obj, into: set) -> set:
    """Every field name appearing anywhere in a record, at any depth."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            into.add(key)
            field_names(value, into)
    elif isinstance(obj, list):
        for value in obj:
            field_names(value, into)
    return into


def store_shape(vocab: dict) -> str:
    """Whether a side is raw scraper output or a published bulk archive.

    Every scraped object carries the _id it was saved under; the importer replaces
    it with an ocd- id. Nothing else distinguishes the two shapes as reliably."""
    return "scrape" if any("_id" in names for names in vocab.values()) else "bulk"


def one_sided_fields(pre_vocab: dict, post_vocab: dict, record_type: str) -> set:
    """Known schema-only fields that really are absent from one side throughout.

    Suppression applies only when the two sides were produced differently, and
    only to fields the data confirms are one-sided. Comparing two scrapes leaves
    every field under scrutiny, so a change that strips one from every record --
    which looks identical to a schema difference -- is still reported."""
    if store_shape(pre_vocab) == store_shape(post_vocab):
        return set()
    pre = pre_vocab.get(record_type, set())
    post = post_vocab.get(record_type, set())
    return SCHEMA_ONLY_FIELDS & (pre ^ post)


def collision_rank(obj: dict):
    return (str(obj.get("result")), len(obj.get("votes") or []), json.dumps(strip_volatile(obj), sort_keys=True))


def strip_volatile(obj, drop: frozenset = frozenset()):
    if isinstance(obj, dict):
        return {k: strip_volatile(v, drop) for k, v in obj.items() if k not in VOLATILE_FIELDS and k not in drop}
    if isinstance(obj, list):
        items = [strip_volatile(v, drop) for v in obj]
        # Lists in this schema (actions, votes, sponsorships, sources...) carry
        # no stable order guarantee across scrape runs -- sort for determinism.
        try:
            items.sort(key=lambda v: json.dumps(v, sort_keys=True))
        except TypeError:
            pass
        return items
    return obj


def list_item_key_fields(pre: list, post: list) -> tuple[str, ...] | None:
    """Pick fields that identify an item within a list of objects, so the two lists
    can be aligned by identity instead of position. Positional comparison turns a
    single insertion, deletion, or re-sort into a cascade of bogus pairings: change
    seven voters from "other" to "not voting" and every later entry shifts, making
    unrelated legislators look like they replaced each other."""
    items = pre + post
    if not items or not all(isinstance(i, dict) for i in items):
        return None
    for fields in LIST_ITEM_KEY_CANDIDATES:
        if not all(all(f in i for f in fields) for i in items):
            continue
        try:
            pre_keys = [tuple(i[f] for f in fields) for i in pre]
            post_keys = [tuple(i[f] for f in fields) for i in post]
            if len(set(pre_keys)) == len(pre_keys) and len(set(post_keys)) == len(post_keys):
                return fields
        except TypeError:  # unhashable field value
            continue
    return None


def diff_records(pre: dict, post: dict, path: str = "") -> list[tuple[str, str, object, object]]:
    """Return list of (path, kind, old, new). kind is one of added/removed/changed."""
    diffs = []
    if isinstance(pre, dict) and isinstance(post, dict):
        for key in sorted(set(pre) | set(post)):
            p = f"{path}.{key}" if path else key
            if key not in pre:
                diffs.append((p, "added", None, post[key]))
            elif key not in post:
                diffs.append((p, "removed", pre[key], None))
            else:
                diffs.extend(diff_records(pre[key], post[key], p))
    elif isinstance(pre, list) and isinstance(post, list):
        p = f"{path}.*"
        fields = list_item_key_fields(pre, post)
        if fields:
            # Align by identity: only genuinely differing entries are reported.
            pre_by_key = {tuple(i[f] for f in fields): i for i in pre}
            post_by_key = {tuple(i[f] for f in fields): i for i in post}
            for key in sorted(set(pre_by_key) | set(post_by_key), key=lambda k: json.dumps(k, default=str)):
                if key not in pre_by_key:
                    diffs.append((p, "added", None, post_by_key[key]))
                elif key not in post_by_key:
                    diffs.append((p, "removed", pre_by_key[key], None))
                else:
                    diffs.extend(diff_records(pre_by_key[key], post_by_key[key], p))
        else:
            # No identity fields (scalars, or duplicate keys): fall back to the
            # positional comparison of the lists sorted by strip_volatile.
            for i in range(max(len(pre), len(post))):
                if i >= len(pre):
                    diffs.append((p, "added", None, post[i]))
                elif i >= len(post):
                    diffs.append((p, "removed", pre[i], None))
                else:
                    diffs.extend(diff_records(pre[i], post[i], p))
    else:
        if pre != post:
            diffs.append((path, "changed", pre, post))
    return diffs


def summarize(pre: RecordStore, post: RecordStore) -> str:
    """The markdown report. Both stores must have been indexed (see main)."""
    pre_index, pre_vocab, post_index, post_vocab = pre.index, pre.vocab, post.index, post.vocab
    lines = []
    notes = []
    counts_rows = []
    total_added = total_removed = total_changed = 0
    pattern_counts = defaultdict(lambda: {"count": 0, "examples": [], "records": set()})
    matched_totals = {}
    # (record_type, field_path, kind) -> how the change is spread across records.
    # Values like version notes and document URLs are unique per bill, so every
    # exact-value pattern is a count of one and the report becomes hundreds of
    # near-identical lines. Roll those up into a single shape line instead.
    field_stats = defaultdict(lambda: {"count": 0, "records": set(), "values": set(), "samples": []})
    # (record_type, field path) -> [before Counter, after Counter] of the values it
    # takes across matched records, or None once it has too many to tabulate.
    tallies = {}

    for record_type in sorted(set(pre_index) | set(post_index)):
        pre_by_key = pre_index.get(record_type, {})
        post_by_key = post_index.get(record_type, {})

        # A type missing from one side entirely is a shape difference, not thousands
        # of new records: say so once, and keep it out of the totals and key lists.
        one_sided_type = not pre_by_key or not post_by_key
        suppressed = set() if one_sided_type else one_sided_fields(pre_vocab, post_vocab, record_type)
        if one_sided_type:
            missing = "pre" if not pre_by_key else "post"
            notes.append(f"- {record_type}: absent from the {missing} data entirely, so nothing is compared")
        elif suppressed:
            notes.append(f"- {record_type}: ignoring {fmt_keys(sorted(suppressed))} (present on one side only)")

        pre_counts, post_counts = pre.counts.get(record_type, {}), post.counts.get(record_type, {})
        for field in ["records"] + sorted((set(pre_counts) | set(post_counts)) - {"records"} - suppressed):
            label = record_type if field == "records" else f"{record_type}.{field}"
            if pre_counts.get(field) or post_counts.get(field):
                counts_rows.append((label, pre_counts.get(field, 0), post_counts.get(field, 0)))

        matched_totals[record_type] = len(set(pre_by_key) & set(post_by_key))
        added_keys = sorted(set(post_by_key) - set(pre_by_key))
        removed_keys = sorted(set(pre_by_key) - set(post_by_key))
        matched_keys = sorted(set(pre_by_key) & set(post_by_key))

        if not one_sided_type:
            total_added += len(added_keys)
            total_removed += len(removed_keys)

        lines.append(f"### {record_type}")
        lines.append(
            f"pre={len(pre_by_key)} post={len(post_by_key)} "
            f"matched={len(matched_keys)} added={len(added_keys)} removed={len(removed_keys)}"
        )
        if added_keys and not one_sided_type:
            lines.append(f"- added: {fmt_keys(added_keys)}")
        if removed_keys and not one_sided_type:
            lines.append(f"- removed: {fmt_keys(removed_keys)}")

        for key in matched_keys:
            drop = frozenset(suppressed)
            pre_obj = strip_volatile(pre.read(pre_by_key[key]), drop)
            post_obj = strip_volatile(post.read(post_by_key[key]), drop)
            diffs = diff_records(pre_obj, post_obj)
            if diffs:
                total_changed += 1
            for side, obj in enumerate((pre_obj, post_obj)):
                tally_leaves(obj, "", record_type, side, tallies)
            for field_path, kind, old, new in diffs:
                pattern = (record_type, field_path, kind, json.dumps(old), json.dumps(new))
                entry = pattern_counts[pattern]
                entry["count"] += 1
                entry["records"].add(key)
                if len(entry["examples"]) < 3 and key not in entry["examples"]:
                    entry["examples"].append(key)

                stats = field_stats[(record_type, field_path, kind)]
                stats["count"] += 1
                stats["records"].add(key)
                stats["values"].add((pattern[3], pattern[4]))
                if len(stats["samples"]) < 2:
                    stats["samples"].append((key, pattern[3], pattern[4]))
        lines.append("")

    header = ["## Counts", "", "| | before | after | change |", "|---|---:|---:|---:|"]
    for label, before, after in counts_rows:
        change = f"{after - before:+,}" if after != before else ""
        header.append(f"| {label} | {before:,} | {after:,} | {change} |")
    header += ["", "## Records", ""]
    lines = header + lines

    if notes:
        lines.append("## Schema differences (not changes)")
        lines.extend(notes)
        lines.append("")

    lines.extend(breakdown_tables(field_stats, tallies))

    lines.append("## Change patterns (deduplicated)")
    lines.append(f"totals: added={total_added} removed={total_removed} records-with-diffs={total_changed}")
    lines.append("")

    patterns_by_field = defaultdict(list)
    for pattern, info in pattern_counts.items():
        patterns_by_field[pattern[:3]].append((pattern, info))

    for field, stats in sorted(field_stats.items(), key=lambda kv: -kv[1]["count"]):
        record_type, field_path, kind = field
        if len(stats["values"]) <= MAX_DISTINCT_VALUES:
            for pattern, info in sorted(patterns_by_field[field], key=lambda kv: -kv[1]["count"]):
                lines.append(fmt_pattern(pattern, info, matched_totals.get(record_type, 0)))
            continue

        # Too many distinct values to list: one line for the shape, then samples.
        records = len(stats["records"])
        total = matched_totals.get(record_type, 0)
        lines.append(
            f"- {records} of {total} {record_type} {code(field_path)} {kind} "
            f"-- {stats['count']} occurrences ({stats['count'] / records:.1f} per record), "
            f"{len(stats['values'])} distinct values"
        )
        for key, old, new in stats["samples"]:
            detail = (
                f"{code(truncate(old))} -> {code(truncate(new))}"
                if kind == "changed"
                else code(truncate(new if kind == "added" else old))
            )
            lines.append(f"  - e.g. {key}: {detail}")

    return "\n".join(lines)


def fmt_pattern(pattern, info, total: int) -> str:
    record_type, field_path, kind, old, new = pattern
    examples = ", ".join(str(e) for e in info["examples"])
    hidden = len(info["records"]) - len(info["examples"])
    more = f" (+{hidden} more records)" if hidden > 0 else ""
    if kind == "changed":
        detail = f"{code(truncate(old))} -> {code(truncate(new))}"
    else:
        detail = f"{kind} {code(truncate(new if kind == 'added' else old))}"
    return (
        f"- {len(info['records'])} of {total} {record_type} {code(field_path)} {detail} "
        f"-- {info['count']} occurrences, e.g. {examples}{more}"
    )


def code(text: str) -> str:
    """A markdown code span that survives backticks in the value."""
    return f"`` {text} ``" if "`" in text else f"`{text}`"


def tally_leaves(obj, path: str, record_type: str, side: int, tallies: dict) -> None:
    """Count the scalar values at each field path of one side's record.

    A list of scalars (a classification) counts as one value, so an empty one
    gets a row of its own; lists of objects are walked into. An empty list of
    objects is counted as "(none)" too, but breakdown_tables never shows it."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            tally_leaves(value, f"{path}.{key}" if path else key, record_type, side, tallies)
        return
    if isinstance(obj, list) and any(isinstance(v, (dict, list)) for v in obj):
        for value in obj:
            tally_leaves(value, f"{path}.*", record_type, side, tallies)
        return
    if isinstance(obj, list):
        value = ", ".join(map(str, obj)) or "(none)"
    else:
        value = obj if isinstance(obj, str) else json.dumps(obj)
    slot = (record_type, path)
    if slot not in tallies:
        tallies[slot] = [defaultdict(int), defaultdict(int)]
    counters = tallies[slot]
    if counters is None:
        return
    counters[side][value] += 1
    if len(counters[side]) > BREAKDOWN_MAX_VALUES:
        tallies[slot] = None


def breakdown_tables(field_stats: dict, tallies: dict) -> list[str]:
    """A before/after table of values for each low-cardinality field that changed.

    The change patterns say what moved; this says where the field ended up, e.g.
    actions filed under each chamber, which is the table a reviewer wants."""
    lines = []
    seen = set()
    for (record_type, field_path, _kind), stats in sorted(field_stats.items()):
        # A scalar list's entries diff as "<path>.*" but are tallied as one value.
        # Entries that are objects (votes.*) have no such tally worth showing.
        scalar_entries = all(not v.startswith(("{", "[")) for _, *values in stats["samples"] for v in values)
        whole_list = field_path[:-2] if field_path.endswith(".*") and scalar_entries else None
        for path in (field_path, whole_list):
            slot = (record_type, path)
            if path is None or slot in seen or not tallies.get(slot):
                continue
            seen.add(slot)
            before, after = tallies[slot]
            if before == after:
                continue
            if not lines:
                lines += ["## Changed values", "", "Over the records matched on both sides.", ""]
            lines += [f"| {record_type} {code(path)} | before | after |", "|---|---:|---:|"]
            for value in sorted(set(before) | set(after), key=lambda v: (-after.get(v, 0), -before.get(v, 0), v)):
                cell = code(truncate(value, 80)).replace("|", "\\|")
                lines.append(f"| {cell} | {before.get(value, 0):,} | {after.get(value, 0):,} |")
            lines.append("")
    return lines


def trim_to_diff(pre, post):
    """The parts of two versions of a value that differ, as (pre part, post part).

    A list whose entries have identity keys keeps only the entries that changed,
    whole; anything else that differs is kept whole. None means nothing differs."""
    if isinstance(pre, dict) and isinstance(post, dict):
        pre_part, post_part = {}, {}
        for key in sorted(set(pre) | set(post)):
            if key in pre and key in post:
                a, b = trim_to_diff(pre[key], post[key])
                if a is not None:
                    pre_part[key], post_part[key] = a, b
            elif key in pre:
                pre_part[key] = pre[key]
            else:
                post_part[key] = post[key]
        return (pre_part, post_part) if pre_part or post_part else (None, None)
    if pre == post:
        return None, None
    if isinstance(pre, list) and isinstance(post, list):
        fields = list_item_key_fields(pre, post)
        if fields:
            pre_by_key = {tuple(i[f] for f in fields): i for i in pre}
            post_by_key = {tuple(i[f] for f in fields): i for i in post}
            return (
                [i for k, i in pre_by_key.items() if post_by_key.get(k) != i],
                [i for k, i in post_by_key.items() if pre_by_key.get(k) != i],
            )
    return pre, post


def show_records(pre: RecordStore, post: RecordStore, names: list[str]) -> list[str]:
    """Each named record before and after, trimmed to what differs.

    A name matches any part of a record's key, ignoring case and spaces, so
    "SB 602" picks out that bill and every vote event on it."""

    def norm(value) -> str:
        return re.sub(r"\s+", "", str(value)).lower()

    def dump(obj) -> list[str]:
        return ["```json", json.dumps(obj, indent=2, ensure_ascii=False), "```"]

    lines = ["## Examples", ""]
    for name in names:
        shown = skipped = 0
        for record_type in sorted(set(pre.index) | set(post.index)):
            drop = frozenset(one_sided_fields(pre.vocab, post.vocab, record_type))
            pre_by_key, post_by_key = pre.index.get(record_type, {}), post.index.get(record_type, {})
            for key in sorted(set(pre_by_key) | set(post_by_key), key=str):
                if norm(name) not in {norm(k) for k in key}:
                    continue
                pre_obj = strip_volatile(pre.read(pre_by_key[key]), drop) if key in pre_by_key else None
                post_obj = strip_volatile(post.read(post_by_key[key]), drop) if key in post_by_key else None
                if pre_obj is not None and post_obj is not None:
                    before, after = trim_to_diff(pre_obj, post_obj)
                    if before is None:
                        continue
                    context = {f: pre_obj[f] for f in CONTEXT_FIELDS if f in pre_obj and f not in before}
                    before, after = {**context, **before}, {**context, **after}
                else:
                    before, after = pre_obj, post_obj
                if shown == MAX_SHOWN:
                    skipped += 1
                    continue
                shown += 1
                lines.append(f"### {record_type} {key}")
                for label, obj in (("Before", before), ("After", after)):
                    lines += [f"{label}:", ""] + (dump(obj) if obj is not None else ["(not in this scrape)"]) + [""]
        if not shown:
            lines += [f"No changed record matches {code(name)}.", ""]
        elif skipped:
            lines += [f"{skipped} more changed records match {code(name)}.", ""]
    return lines


def truncate(value: str, limit: int = 140) -> str:
    return value if len(value) <= limit else value[: limit - 3] + "..."


def fmt_keys(keys, limit=20):
    shown = [str(k) for k in keys[:limit]]
    rest = f" (+{len(keys) - limit} more)" if len(keys) > limit else ""
    return ", ".join(shown) + rest


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--pre",
        help="pre-change data: dir, zip, or URL (default: auto-fetch latest bulk "
        "data for the jurisdiction detected in --post)",
    )
    parser.add_argument("--post", required=True, help="post-change data: dir, zip, or URL")
    parser.add_argument("-o", "--output", help="write report to file instead of stdout")
    parser.add_argument(
        "--show",
        action="append",
        default=[],
        metavar="NAME",
        help='append these records before and after, trimmed to what changed (e.g. "SB 602"); repeatable',
    )
    args = parser.parse_args()

    post = RecordStore(fetch_local(args.post))
    if args.pre:
        pre = RecordStore(fetch_local(args.pre))
    else:
        jurisdiction_name = detect_jurisdiction_name(post)
        if not jurisdiction_name:
            parser.error("--pre was not given and no jurisdiction could be detected in --post; pass --pre explicitly.")
        pre = RecordStore(fetch_latest_bulk_data(jurisdiction_name))

    for store in (pre, post):
        store.index, store.vocab, store.counts = index_store(store)
    report = summarize(pre, post)
    if args.show:
        report += "\n\n" + "\n".join(show_records(pre, post, args.show))

    if args.output:
        Path(args.output).write_text(report)
    else:
        print(report)


if __name__ == "__main__":
    main()
