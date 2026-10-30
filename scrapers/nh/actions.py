from utils.actions import Rule, BaseCategorizer

# These are regex patterns that map to action categories.
_categorizer_rules = (
    Rule(r"Minority Committee Report", None),  # avoid calling these passage
    # floor vote on the committee report: the House passes the bill when the
    # motion carries (MA), the Senate when it also orders third reading (OT3rdg)
    Rule(r"^Ought to Pass.*(: MA [A-Z]|\bMA\b.*OT3rdg)", ["passage"]),
    Rule(r"Passed by Third Reading", ["reading-3", "passage"]),
    Rule(
        r"^(Majority )?Committee Report: Ought to Pass", ["committee-passage-favorable"]
    ),
    Rule(r"^Ought to Pass.*Refer to Finance", "referral-committee"),
    Rule(r".*Introduced(.*) and (R|r)eferred", ["introduction", "referral-committee"]),
    Rule(r"Proposed(.*) Amendment", "amendment-introduction"),
    Rule(r"Amendment .* Adopted", "amendment-passage"),
    Rule(r"Amendment .* Failed", "amendment-failure"),
    Rule(r"Signed by (the )?Governor", "executive-signature"),
    Rule(r"Vetoed", "executive-veto"),
    Rule(r"^Introduced", "introduction"),
    Rule(r"Enrolled Adopted", "enrolled"),
    Rule(r"^Inexpedient(?!.*\bMF\b)", "failure"),
    Rule(r"^Died on Table", "failure"),
    Rule(r"^Indefinitely Postpone.*\bMA\b", "failure"),
    Rule(r"Withdraws Floor Amendment", "amendment-withdrawal"),
    Rule(r"Refer to Interim Study", "referral"),
    Rule(r"^(?!.*Committee Report).*[Rr]eferred [Tt]o.*$", "referral-committee"),
    Rule(r"(Lay|Laid) .*on Table(?!.*\bMF\b)", "deferral"),
    Rule(
        r"^(?!.*Minority).*Committee Report: Inexpedient to Legislate",
        "committee-failure",
    ),
)


class Categorizer(BaseCategorizer):
    rules = _categorizer_rules

    def categorize(self, text):
        """Wrap categorize and add boilerplate committees."""
        attrs = BaseCategorizer.categorize(self, text)
        return attrs
