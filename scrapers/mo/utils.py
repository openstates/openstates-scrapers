import re


# remove whitespace, linebreaks, and end parentheses
def clean_text(text):
    newtext = re.sub(r"[\r\n]+", " ", text)
    newtext = re.sub(r"\s{2,}", " ", newtext)
    m = re.match(r"(.*)\(.*?\)", newtext)
    if not m:
        return newtext.strip()
    else:
        return m.group(1).strip()


def house_get_actor_from_action(text):
    m = re.search(r"\((\bH\b|\bS\b)\)", text)
    if not m:
        if text.endswith("Governor"):
            return "executive"
        else:
            return "lower"

    abbrev = m.group(1)
    if abbrev == "S":
        return "upper"
    return "lower"


def senate_get_actor_from_action(text):
    if re.search("Prefiled", text):
        return "upper"

    m = re.search(r"(\bH\b|\bS\b|House)", text)
    if not m:
        if text.endswith("Governor"):
            return "executive"
        else:
            return "upper"

    if m.group(1) == "S":
        return "upper"
    else:
        return "lower"


JOURNAL_PAGE_HEADER = re.compile(
    r"^\s*(\d+)\s{2,}.*(?:Journal of the|Day)|^.*(?:Journal of the|Day).*\s{2,}(\d+)\s*$"
)
# House floor rolls: "AYES: 083" followed by names in columns.
HOUSE_FLOOR_HEADER = re.compile(
    r"^(AYES|NOES|PRESENT|ABSENT WITH LEAVE|ABSENT|VACANCIES): (\d+)\s*$"
)
# House committee reports: "Ayes (12): Allen, Boyko and Steinhoff"
HOUSE_COMMITTEE_HEADER = re.compile(
    r"^(Ayes|Noes|Present|Abstain|Absent) \((\d+)\)(?::\s*(.*))?$"
)
# Senate: "YEAS—Senators" followed by names in columns, the last one ending "—20"
SENATE_HEADER = re.compile(
    r"^\s*(YEAS|NAYS|Present|Absent with leave|Absent|Vacancies)—(.*)$"
)
BILL_CITATION = re.compile(r"\b[HS](?:B|JR|CR|R|RM)s?\s+\d")
ROLL_OPTIONS = {
    "ayes": "yes",
    "yeas": "yes",
    "noes": "no",
    "nays": "no",
    "present": "other",
    "abstain": "abstain",
    "absent": "absent",
    "absent with leave": "excused",
}


def split_journal_pages(text):
    """Split `pdftotext -layout` output into (page number, lines) without page headers."""
    pages = []
    for raw in text.split("\f"):
        lines = raw.splitlines()
        num = None
        for i, line in enumerate(lines[:4]):
            m = JOURNAL_PAGE_HEADER.match(line)
            if m:
                num = int(m.group(1) or m.group(2))
                del lines[i]
                break
        else:
            # a day's first page has its number alone at the bottom
            while lines and not lines[-1].strip():
                lines.pop()
            if lines and lines[-1].strip().isdigit():
                num = int(lines.pop())
        pages.append([num, lines])
    return pages


def _add_vote(roll, option, name):
    name = re.sub(r"^(.*\D) (\d+)$", r"\1 (\2)", name.strip())
    if name:
        roll["votes"].append((ROLL_OPTIONS[option], name))


def parse_journal_rolls(pages):
    """
    Find the roll calls in a House or Senate journal.

    Each roll has the page it starts on, the journal text since the previous
    roll (which names the bill), the printed count for each option, and
    (option, name) votes. Names are read until an option's printed count is
    reached (House) or its "—N" terminator (Senate).
    """
    rolls = []
    context = []
    roll = option = None
    remaining = 0
    wrapped = False

    def finish():
        for key, count in roll["counts"].items():
            names = sum(1 for o, _ in roll["votes"] if o == ROLL_OPTIONS[key])
            if names != count:
                roll["complete"] = False
        rolls.append(roll)

    def take(line):
        nonlocal remaining, wrapped
        if roll["style"] == "senate":
            text = re.sub(r"^\s*Senators?\b", "", line)
            end = re.search(r"—(\d+|None)\s*$", text)
            if end:
                text = text[: end.start()]
            for name in re.split(r"\s{2,}|—", text.strip()):
                _add_vote(roll, option, name)
            if end:
                roll["counts"][option] = (
                    0 if end.group(1) == "None" else int(end.group(1))
                )
                remaining = 0
        else:
            sep = r",|\band\b" if roll["style"] == "committee" else r"\s{2,}"
            if roll["style"] == "committee":
                # a name can wrap onto the next line, e.g. "Van" / "Schoiack, Warwick"
                if wrapped and roll["votes"]:
                    line = roll["votes"].pop()[1] + " " + line.strip()
                    remaining += 1
                wrapped = not re.search(r"(,|\band)\s*$", line)
            for name in re.split(sep, line.strip()):
                if name.strip():
                    _add_vote(roll, option, name)
                    remaining -= 1
            remaining = max(remaining, 0)

    for page_num, lines in pages:
        for line in lines:
            header = None
            for style, regex in (
                ("floor", HOUSE_FLOOR_HEADER),
                ("committee", HOUSE_COMMITTEE_HEADER),
                ("senate", SENATE_HEADER),
            ):
                m = regex.match(line)
                if m:
                    header = m
                    break
            if header:
                key = header.group(1).lower()
                if key in ("ayes", "yeas"):
                    if roll:
                        finish()
                    text = "\n".join(context)
                    # e.g. "The emergency clause was adopted by the following vote:"
                    # right after the bill's passage roll
                    if rolls and not BILL_CITATION.search(text):
                        text = rolls[-1]["context"] + "\n" + text
                    roll = {
                        "page": page_num,
                        "context": text,
                        "style": style,
                        "counts": {},
                        "votes": [],
                        "complete": True,
                    }
                    context = []
                elif roll is None or roll["style"] != style:
                    context.append(line)
                    continue
                if key == "vacancies":
                    option, remaining = None, 0
                    continue
                option = key
                wrapped = False
                if style == "senate":
                    remaining = 1
                    take(header.group(2))
                else:
                    remaining = roll["counts"][key] = int(header.group(2))
                    if style == "committee" and header.group(3):
                        take(header.group(3))
                continue

            if roll and remaining:
                take(line)
            elif roll and line.strip():
                # the first other text after the last name ends the roll
                finish()
                roll = option = None
                context.append(line)
            else:
                context.append(line)
    if roll:
        finish()
    return rolls
