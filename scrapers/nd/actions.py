from utils.actions import Rule, BaseCategorizer

# These are regex patterns that map to action categories.
_categorizer_rules = (
    Rule(r"Amendment proposed on floor", "amendment-introduction"),
    Rule(r"Amendment failed", "amendment-failure"),
    Rule(r"Amendment adopted, placed on calendar", ""),
    Rule(r"^Filed with ", "introduction"),
    Rule(r"^Introduced", "introduction"),
    Rule(r"^Second reading", "reading-2"),
    Rule(r"passed as amended", "passage"),
    Rule(r"passed", "passage"),
    Rule(r"Sent to Governor", "executive-receipt"),
    Rule(r"Reported back", "committee-passage"),
    Rule(r"Reported back.*do pass", "committee-passage-favorable"),
    Rule(r"Reported back.*do not pass", "committee-passage-unfavorable"),
    Rule(r"^Signed by Governor", "executive-signature"),
)


class NDCategorizer(BaseCategorizer):
    rules = _categorizer_rules
