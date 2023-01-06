from utils.actions import Rule, BaseCategorizer

rules = (
    Rule(r"^Referred to", "referral-committee"),
    Rule(r"^Favorable by", "committee-passage-favorable"),
    Rule(r"Filed", "filing"),
    Rule(r"^Withdrawn", "withdrawal"),
    Rule(r"^Died", "failure"),
    Rule(r"^Introduced", "introduction"),
    Rule(r"^Referred to", "referral-committee"),
    Rule(r"^Read 2nd time", "reading-2"),
    Rule(r"^Read 3rd time", "reading-3"),
    Rule(r"^Adopted", "passage"),
    Rule(r"Approved by Governor", "executive-signature"),
    Rule(r"Vetoed by Governor", "executive-veto"),
    Rule(r"[Pp]assed;", "passage"),
    Rule(r"[Cc][Ss] passed", "passage"),
    Rule(r"[Pp]assed as amended", "passage"),
    Rule(r"Approved by Governor", "executive-signature"),
    Rule(r"Placed on 3rd reading", "reading-3"),
    Rule(r"withdrawn from consideration", "withdrawal"),
    Rule(r"1st Reading", "reading-1"),
    Rule(r"Laid on Table", "deferral"),
    Rule(r"CS Filed", "filing"),
    Rule(r"presented to Governor", "executive-receipt"),
    Rule(r"enroll", "enrolled"),
    Rule(r"Favorable.*[Cc]ommittee", "committee-passage-favorable"),
    Rule(r"[Rr]eceived", "enrolled"),
)


class Categorizer(BaseCategorizer):
    rules = rules

    def categorize(self, text):
        attrs = BaseCategorizer.categorize(self, text)
        return attrs
