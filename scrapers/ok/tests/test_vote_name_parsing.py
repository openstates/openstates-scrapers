"""
Regression test for the OK vote-roll name tokenizer.

Real OK vote pages render names separated by single spaces (Word's
mso-spacerun columns collapse to one space each once lxml pulls string()),
not the 3-space runs the old `line.split("   ")` heuristic assumed. That
heuristic silently glommed whole lines of 4 names into a single garbage
"name", producing itemized counts far below the declared count.
`extract_names` fixes this by tokenizing on name shape instead of
whitespace width, and by stopping at the declared count so trailing free
text (e.g. "STRIKE THE TITLE - ADOPTED" after a zero-count section) never
gets mistaken for a vote.
"""

from ..bills import NAME_RE, extract_names


def test_plain_names():
    assert NAME_RE.findall("Baker Bashore Bennett Blancett") == [
        "Baker",
        "Bashore",
        "Bennett",
        "Blancett",
    ]


def test_parenthetical_disambiguator_stays_attached():
    line = "Caldwell (C) Humphrey Pae Turner"
    assert NAME_RE.findall(line) == ["Caldwell (C)", "Humphrey", "Pae", "Turner"]


def test_mr_speaker_is_one_token():
    line = "Dobrinski Martinez Sims Mr. Speaker"
    assert NAME_RE.findall(line) == ["Dobrinski", "Martinez", "Sims", "Mr. Speaker"]


def test_apostrophe_and_hyphen_names():
    line = "O'Donnell Alonso-Sandoval"
    assert NAME_RE.findall(line) == ["O'Donnell", "Alonso-Sandoval"]


def test_extract_names_stops_at_declared_limit():
    # Real example: a zero-count "CONSTITUTIONAL PRIVILEGE" section is
    # sometimes followed by trailing outcome text before the "*****"
    # separator. A declared limit of 0 must yield zero fake "votes".
    assert extract_names("STRIKE THE TITLE - ADOPTED", 0) == []


def test_extract_names_caps_at_limit_not_line_contents():
    # If a line has more name-shaped tokens than the declared count still
    # needs, only take what's left -- this is what keeps a stray extra
    # entry (e.g. "Mr. Speaker" voting without being in the declared
    # total) from inflating the itemized count past what's expected.
    line = "Dobrinski Martinez Sims Mr. Speaker"
    assert extract_names(line, 3) == ["Dobrinski", "Martinez", "Sims"]


if __name__ == "__main__":
    test_plain_names()
    test_parenthetical_disambiguator_stays_attached()
    test_mr_speaker_is_one_token()
    test_apostrophe_and_hyphen_names()
    test_extract_names_stops_at_declared_limit()
    test_extract_names_caps_at_limit_not_line_contents()
    print("ok")
