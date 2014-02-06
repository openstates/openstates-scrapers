from billy.scrape.actions import Rule, BaseCategorizer

# These are regex patterns that map to action categories.
_categorizer_rules = (
    Rule(r'Amendment proposed on floor', 'amendment:introduced'),
    Rule(r'Amendment failed', 'amendment:failed'),
    Rule(r'Amendment adopted, placed on calendar', ''),
    Rule(r'^Filed with ', 'bill:introduced'),
    Rule(r'^Introduced', 'bill:introduced'),
    Rule(r'^Second reading', 'bill:reading:2'),
    Rule(r'passed as amended', 'bill:passed'),
    Rule(r'passed', 'bill:passed'),
    Rule(r'Sent to Governor', 'governor:received'),
    Rule(r'Reported back', 'committee:passed'),
    Rule(r'Reported back.*do pass', 'committee:passed:favorable'),
    Rule(r'Reported back.*do not pass', 'committee:passed:unfavorable'),
    Rule(r'^Signed by Governor', 'governor:signed'),
)


class NDCategorizer(BaseCategorizer):
    rules = _categorizer_rules
