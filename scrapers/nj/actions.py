from utils.actions import Rule, BaseCategorizer

# PLEASE NOTE: this classifier is used by the bills_web scraper but NOT the main bills scraper
# So if you make changes here, you may need to make changes to the self._actions structure there.

# These are regex patterns that map to action categories.
_categorizer_rules = (
    Rule(r"Introduced", "introduction"),
    Rule(r"2nd Reading", "reading-2"),
    Rule(r"Reported out of (Senate|Assembly) Committee", "committee-passage"),
    Rule(r"Assembly Floor Amendment Passed", "amendment-passage"),
    Rule(r"Senate Amendment", "amendment-passage"),
    Rule(r"Passed (Senate|Assembly)", "passage"),
    Rule(r"^Approved$", "executive-signature"),
    Rule(r"Approved with Line Item Veto", "executive-veto-line-item"),
    Rule(r"(Absolute|Conditional) Veto", "executive-veto"),
    Rule(
        r"(Introduced|Received) in the (Assembly|Senate), Referred to",
        "referral-committee",
    ),
    Rule(r"Referred to .+ Committee", "referral-committee"),
    Rule(r"Reported and Referred to", "referral-committee"),
    Rule(r"(Transferred|Recommitted) to", "referral-committee"),
    Rule(
        r"Reported out of (Assembly|Senate) Committee with Amendments and Referred to",
        "referral-committee",
    ),
    Rule(r"Withdrawn from Consideration", "withdrawal"),
)


class Categorizer(BaseCategorizer):
    rules = _categorizer_rules

    def categorize(self, text):
        """Wrap categorize and add boilerplate committees."""
        attrs = BaseCategorizer.categorize(self, text)
        return attrs
