from utils.actions import Rule, BaseCategorizer

# These are regex patterns that map to action categories.
_categorizer_rules = (
    Rule(r"Introduced", "introduction"),
    Rule(
        r"Introduced and Referred to Committee", ["introduction", "referral-committee"]
    ),
    Rule(r"Offered", "introduction"),
    Rule(r"Refer to Committee", "referral-committee"),
    Rule(r"Referred to committee", "referral-committee"),
    Rule(r"Concurred in (Senate|House) amendments", "amendment-passage"),
    Rule(r"Refused to concur in (Senate|House) amendments", "amendment-failure"),
    Rule(r"Adopted", "passage"),
    Rule(r"Passed", "passage"),
    Rule(r"Sent to Governor", "passage"),
    Rule(r"Sent To The Governor", "passage"),
    Rule(r"line item veto receipt", "executive-veto"),
    Rule(
        r"Item passed notwithstanding objections of the Governor",
        ["veto-override-passage"],
    ),
    Rule(r"Effective \d{1,2}\/\d{1,2}\/\d{2,2}", "became-law"),
    Rule(r"Effective", "became-law"),
    Rule(r"Signed By The Governor", "became-law"),
)


class OHCategorizer(BaseCategorizer):
    rules = _categorizer_rules
