from billy.scrape.actions import Rule, BaseCategorizer

# These are regex patterns that map to action categories.
_categorizer_rules = (
    Rule(r'^Filed with ', 'bill:introduced'),
    Rule(r'^Introduced', 'bill:introduced'),
    Rule(r'^Second reading', 'bill:reading:2'),
    Rule(r'^Signed by Governor', 'governor:signed'),
)


class NDCategorizer(BaseCategorizer):
    rules = _categorizer_rules
