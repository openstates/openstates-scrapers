from utils.actions import Rule, BaseCategorizer

rules = (
    Rule(r"Governor Signed", "executive-signature"),
    Rule(r"Governor Vetoed", "executive-veto"),
    Rule(r"Governor Line Item Veto", "executive-veto-line-item"),
    Rule(r"^1st reading", ["introduction", "reading-1"]),
    Rule(r"to Governor", "executive-receipt"),
    Rule(r"passed 3rd reading", "passage"),
    Rule(r"^passed 2nd & 3rd readings", "passage"),
    Rule(r"passed 3rd reading", "passage"),
    Rule(r"to standing committee", "referral-committee"),
    Rule(r"^2nd reading", "reading-2"),
    Rule(r"^3rd reading", "reading-3"),
    Rule(r"failed", "failure"),
    Rule(r"^2nd & 3rd readings", ["reading-2", "reading-3"]),
    Rule(r"passed 2nd reading", "reading-2"),
    Rule(r"Comm - Favorable Recommendation", "committee-passage-favorable"),
    Rule(r"committee report favorable", "committee-passage-favorable"),
    Rule(r"signed by President", "passage"),
    Rule(r"signed by Speaker", "passage"),
    Rule(r"filed", "filing"),
    Rule(r"Enrolled Bill Returned", "enrolled"),
    Rule(r"2nd Reading Calendar to Rules", "reading-2"),
    Rule(r"override Governor", "veto-override-passage"),
    Rule(r"Conference Committee Appointed", "referral-committee"),
    Rule(r"Final Passage", "passage"),
    Rule(r"floor amendment failed", "amendment-failure"),
    Rule(r"Motion to Recommend Failed", "failure"),
    Rule(r"substituted from", "substitution"),
    Rule(r"substituted by", "substitution"),
    Rule(r"substitute recommendation", "substitution"),
    Rule(r"Amendment Recommendation", "amendment-introduction"),
    Rule(r"amended", "amendment-passage"),
    Rule(r"^.*concurs with.*amendment", "amendment-passage"),
    Rule(r"received", "receipt"),
    Rule(r"to Lieutenant Governor", "executive-receipt"),
    Rule(r"Became Law", "became-law"),
    Rule(r"[Tt]abled", "deferral"),
    Rule(r"Not Lifted from Table", "deferral"),
    Rule(r"refer", "referral"),
)


class Categorizer(BaseCategorizer):
    rules = rules

    def categorize(self, text):
        attrs = BaseCategorizer.categorize(self, text)
        return attrs
