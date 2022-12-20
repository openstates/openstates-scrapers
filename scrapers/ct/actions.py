from utils.actions import Rule, BaseCategorizer

_categorizer_rules = (
    Rule(r"^ADOPTED, (HOUSE|SENATE|SEN\.?)", "passage"),
    Rule(r"^(HOUSE|SENATE|SEN\.?) PASSED", "passage"),
    Rule(r"^Joint [Ff]avorable", "committee-passage-favorable"),
    Rule(r"^Joint [Uu]n?[Ff]avorable", "committee-passage-unfavorable"),
    Rule(r"SIGNED BY GOVERNOR", "executive-signature"),
    Rule(r"^LINE ITEM VETOED", "executive-veto-line-item"),
    Rule(r"VETOED BY GOVERNOR", "executive-veto"),
    # According to CT leg website, tabled for calendar = second reading
    Rule(r"TABLED FOR", "reading-2"),
    Rule(r"^.*ADOPTED.*AMEND.*$", "amendment-passage"),
    Rule(r"^.*REJECTED.*AMEND.*$", "amendment-failure"),
    Rule(r"FILED", "filing"),
    Rule(r"REFERRED TO", "referral"),
    Rule(r"TRANSMITTED BY SECRETARY OF THE STATE TO GOVERNOR", "executive-receipt"),
    Rule(r"TAB. FOR CAL.", "reading-2"),
    Rule(r"^.*REJ.*AMEND.*$", "amendment-failure"),
    Rule(r"^.*REF.*TO JOINT COMM.*$", "referral-committee"),
)


class Categorizer(BaseCategorizer):
    rules = _categorizer_rules

    def categorize(self, text):
        attrs = BaseCategorizer.categorize(self, text)
        return attrs
