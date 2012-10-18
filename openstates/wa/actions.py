from billy.scrape.actions import Rule, BaseCategorizer


# These are regex patterns that map to action categories.
_categorizer_rules = (
    Rule(r"(?i)third reading, (?P<pass_fail>(passed|failed)); yeas, (?P<yes_votes>\d+); nays, (?P<no_votes>\d+); absent, (?P<absent_voters>\d+); excused, (?P<excused_voters>\d+)", 'bill:reading:3'),
    Rule(r"(?i)first reading, referred to (?P<committees>.*)\.", 'bill:reading:1'),
    Rule(r"(?i)And refer to (?P<committees>.*)", 'committee:referred'),
    Rule(r"(?i).* substitute bill substituted.*", 'bill:substituted'),
    Rule(r"(?i)chapter (((\d+),?)+) \d+ laws.( .+)?", "other"),  # XXX: Thom: Code stuff?
    Rule(r"(?i)effective date \d{1,2}/\d{1,2}/\d{4}.*", "other"),
    Rule(r"(?i)(?P<committees>\w+) - majority; do pass with amendment\(s\) (but without amendments\(s\))?.*\.", "committee:passed:favorable", "committee:passed"),
    Rule(r"(?i)Executive action taken in the (House|Senate) committee on (?P<committees>.*) (at)? .*\.", "other"),
    Rule(r"(?i)(?P<committees>\w+) \- Majority; do pass .* \(Majority Report\)", 'bill:passed'),
    Rule(r"(?i)Conference committee appointed.", "other"),
    Rule(r"(?i)Conference committee report;", 'other'),
    Rule(r"(?i).+ - Majority; \d+.+ substitute bill be substituted, do pass", 'bill:passed'),
    Rule(r"(?i)Signed by (?P<signed_chamber>(Representatives|Senators)) (?P<members>.*)", "bill:passed"),
    Rule(r"(?i)Referred to (?P<committees>.*)(\.)?"),
    Rule(r"(?i)(?P<from_committee>.*) relieved of further consideration. On motion, referred to (?P<committees>.*)", 'committee:referred'),
    Rule(r"(?i)Governor partially vetoed", 'governor:vetoed:line-item'),
    Rule(r"(?i)Governor vetoed", 'governor:vetoed'),
    Rule(r"(?i)Governor signed", 'governor:signed'),
#    Rule(r"(?i)"),
#    Rule(r"(?i)"),
)


class WACategorizer(BaseCategorizer):
    rules = _categorizer_rules
