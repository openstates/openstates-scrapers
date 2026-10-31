<!--
A reviewer checks a scraper change by its output, so this template asks for
evidence more than description: one real record that was wrong, why, what the
code does now, and a before/after scrape with every difference explained.
#5869, #5889 and #5866 are written this way. Delete a section that doesn't apply
(a crash fix may have no bug example), but say so rather than leaving it empty.
-->

## Summary

<!--
What was wrong, in terms of the data: which field, on which records, how many.
Name one real record and link its page on the legislature's site, e.g.
"SB 602, roll call 342 (link): the journal says 28-7-2, but the published data
has 28-9, with excused senators Geiss and Santana recorded as nays."
Then one sentence on what this PR changes. Link the issue: Fixes openstates/issues#NNNN
-->

## Cause

<!--
Why the scraper produced that: the function, and what on the page it misreads
(often a site redesign). One bullet per cause.
-->

## Fix

<!-- One bullet per behavior change. Mention tests added or updated. -->

## Bug example / Resolution example

<!--
The record from the summary, before and after, trimmed to the fields that change.
compare_scrapes.py prints these for you; paste its "Examples" section:

    SHOW="SB 602" scripts/scrape_before_after.sh <jurisdiction> ...
    python scripts/compare_scrapes.py --pre before.zip --post after.zip --show "SB 602"
-->

## Before/after scrape

<!--
Scrape the base branch and this branch, and diff them:

    scripts/scrape_before_after.sh <jurisdiction> [scraper args, e.g. bills session=2025]

It scrapes the merge base first, then replays the same cached pages for this
branch, so the diff shows your change and not what the site changed in between.
Output goes to _scrapes/<jurisdiction>/: before.zip, after.zip and report.md.
It needs the local poetry install from the README; in Docker, run the scraper on
each branch yourself (docker compose run --rm scrape <jurisdiction> bills --scrape),
zip each _data/<jurisdiction>, and diff the zips with compare_scrapes.py.

Paste here:
- the command and the before/after commits (the top of report.md)
- the counts table, plus "Changed values" rows for the fields your fix targets
- one bullet per change pattern in the report, including the ones this PR does
  not cause (the site changed, flaky fetches, run-order noise) and how you know
- what you checked against the live site, and anything you didn't scrape

Upload both zips: drag them into this description, or attach them to a release
on your fork. Put their links below; a check diffs them and posts the full
report as a comment. Re-post the two lines in a comment after a re-run and the
report updates. If you can't scrape the base, use the session's latest archive
from https://open.pluralpolicy.com/data/session-json/ (sign-in required) as
pre-data, and expect some noise from site changes since it was published.
-->

pre-data: https://REPLACE-ME/before.zip
post-data: https://REPLACE-ME/after.zip

## Checklist

- [ ] Scraper runs cleanly end to end
- [ ] Both links above are filled in, and every difference in the report is explained (or say below why there's no scrape)
- [ ] Parser changes have a test (`pytest scrapers/<jurisdiction>/tests`), and flake8 and black are clean
