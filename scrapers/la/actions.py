from utils.actions import Rule, BaseCategorizer


rules = (
    Rule(
        r"Vetoed by the Governor",
        "executive-veto",
    ),
    Rule(r"Becomes Act No", "became-law"),
    Rule(r"Sent to the Governor", "executive-receipt"),
    Rule(r"Signed by the Governor", "executive-signature"),
    Rule(r"ordered to the Senate", "passage"),
    Rule(r"ordered returned to the House", "passage"),
    Rule(r"sent to the House", "passage"),
    Rule(r"referred to the Committee", "referral-committee"),
    Rule(r"Prefiled", "filing"),
    Rule(r"passed to 3rd reading", "reading-3"),
    Rule(r"Finally passed", "passage"),
    Rule(r"passed by", "passage"),
    Rule(r"Sent to the Governor", "executive-receipt"),
    Rule(r"Reported with amendments", "committee-passage-favorable"),
    Rule(r"Reported favorably", "committee-passage-favorable"),
    Rule(r"Enrolled", "enrolled"),
    Rule(r"Read by title and passed to third reading", "reading-3"),
    Rule(r"Read first time by title", "reading-1"),
    Rule(r"Read second time by title", "reading-2"),
    Rule(r"Received from", "receipt"),
)


class Categorizer(BaseCategorizer):
    rules = rules

    def categorize(self, text):
        """Wrap categorize"""
        attrs = BaseCategorizer.categorize(self, text)

        return attrs
