from utils.actions import Rule, BaseCategorizer

rules = (
    Rule(r"Introduced", "introduction"),
    Rule("[Rr]eferred", "referral-committee"),
    Rule("passed", "passage"),
    Rule("recommends passage", "committee-passage-favorable"),
    Rule("Withdrawn", "withdrawal"),
    Rule("Signed by Governor", "executive-signature"),
    Rule("Transmitted to Governor", "executive-receipt"),
    Rule("Effective without Governor's signature", "became-law"),
    Rule(
        r"Committee recommended measure be held for further study", "committee-failure"
    ),
    Rule(r".*Placed on.*Calendar", "reading-3"),
    Rule(r"Vetoed by Governor", "executive-veto"),
    Rule(r"Substitute", "substitution"),
)


class Categorizer(BaseCategorizer):
    rules = rules

    def categorize(self, text):
        attrs = BaseCategorizer.categorize(self, text)
        return attrs
