"""Tests for the MA House roll-call regression: they were never scraped at all.

Two independent bugs, both silent, which is why they survived long enough to gate
Massachusetts' production flip:

1. **The trigger matched nothing.** House votes were only created when an action
   description contained "Supplement", and Massachusetts stopped using that word.
   Across the 24 bills that failed the MA 194th coverage comparison, "Supplement"
   appears zero times while "YEA and NAY" appears 57. The Senate branch ("Roll
   Call") still matched reality, so the symptom was "Senate votes but no House
   votes" rather than an obvious blank.

2. **The roll-call URL carried the session's ordinal suffix.** It built
   `.../Journal/House/194th/2025/RollCalls`; the site wants `194`. Verified live:
   the ordinal form returns HTTP 404 with a 68KB HTML error page, the bare number
   returns HTTP 200 with the real ~740KB PDF.

The second was invisible for a specific reason worth pinning: `urlretrieve` saved
the 404 page, `convert_pdf` turned it into junk, the `"No. <n>"` lookup in
`scrape_house_vote()` missed, and that path does a bare `return` rather than
`return False`. The caller tests `is False`, so `None` took the success branch and
yielded a vote event with correct counts and zero voters. Tallies looked right
while every individual House vote was dropped.

These tests pin the two conditions rather than a scraped snapshot, because a
snapshot would not have caught either bug: both produced well-formed output.
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scrapers"))

from ma.bills import MABillScraper  # noqa: E402,F401  (import guards the module)

SESSION = "194th"


def _house_vote_triggered(action_name):
    """The gate `scrape_action_page` applies before creating a House vote.

    Mirrors the condition in `scrapers/ma/bills.py` rather than calling into the
    scraper, which needs a live page and a full Bill object. If that condition is
    edited, this must be edited with it -- which is the point: it should not be
    possible to narrow the trigger back to "Supplement" without a test failing.
    """
    return "Supplement" in action_name or bool(
        re.search(r"YEA and NAY", action_name, re.IGNORECASE)
    )


def _rollcall_session(legislative_session):
    """The transform applied to the session before it goes into the URL."""
    return re.sub(r"\D+$", "", legislative_session)


class TestHouseVoteTrigger:
    def test_modern_yea_and_nay_text_triggers_a_house_vote(self):
        """The bug. This is the form Massachusetts actually uses now -- 57
        occurrences across the 24 failing bills, against zero for "Supplement"."""
        assert _house_vote_triggered(
            "Rules suspended. Read second and ordered to a third reading "
            "(See YEA and NAY No. 62 )"
        )

    def test_case_is_not_load_bearing(self):
        """The real text varies; the trigger should not depend on which way."""
        for text in ("See YEA AND NAY No. 3", "see yea and nay no. 3", "Yea and Nay No. 3"):
            assert _house_vote_triggered(text), text

    def test_the_old_supplement_trigger_still_works(self):
        """Kept deliberately rather than replaced: older sessions may still use it,
        and dropping it would trade this bug for its mirror image."""
        assert _house_vote_triggered("Supplement No. 14 adopted")

    def test_an_unrelated_action_does_not_trigger_a_house_vote(self):
        """The gate must stay a gate. A Senate roll call in particular has its own
        branch and must not be picked up here."""
        for text in (
            "Referred to the committee on Ways and Means",
            "Roll Call #123 -- Senate",
            "Reported favorably by committee",
            "Enacted and laid before the Governor",
        ):
            assert not _house_vote_triggered(text), text


class TestRollCallUrlSession:
    def test_the_ordinal_suffix_is_stripped(self):
        """The whole second bug. `194th` in this URL is a 404; `194` is the PDF."""
        assert _rollcall_session(SESSION) == "194"

    def test_every_ordinal_form_is_handled(self):
        """MA sessions run through the ordinals, so this cannot be a special case
        for "th" alone."""
        assert _rollcall_session("193rd") == "193"
        assert _rollcall_session("191st") == "191"
        assert _rollcall_session("192nd") == "192"

    def test_a_bare_number_is_left_alone(self):
        """Idempotent, so this is safe if the session format ever changes upstream."""
        assert _rollcall_session("194") == "194"

    def test_the_built_url_carries_no_ordinal(self):
        """Asserted on the assembled string, because that is what actually gets
        fetched -- and the ordinal form silently returned a saved HTML error page
        rather than failing."""
        url = "https://malegislature.gov/Journal/House/{}/{}/RollCalls".format(
            _rollcall_session(SESSION), 2025
        )
        assert url == "https://malegislature.gov/Journal/House/194/2025/RollCalls"
        assert "194th" not in url


def test_the_scraper_module_applies_both_fixes():
    """Guards against the tests above drifting from the code they mirror.

    Both conditions are asserted against the module source, so narrowing the
    trigger or putting the ordinal back fails here even though the helpers above
    would still pass.
    """
    source = open(
        os.path.join(os.path.dirname(__file__), "..", "scrapers", "ma", "bills.py")
    ).read()
    assert "YEA and NAY" in source, "the House vote trigger no longer matches modern text"
    assert (
        're.sub(r"\\D+$", "", bill.legislative_session)' in source
    ), "the roll-call URL is carrying the session ordinal again"
