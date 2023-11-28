from utils.actions import Rule, BaseCategorizer

rules = (
    Rule("introduced and referred", ["introduction", "referral-committee"]),
    Rule("rerefer to", "referral-committee"),
    Rule("do pass failed", "committee-failure"),
    Rule("2nd reading:passed", "reading-2"),
    Rule("3rd reading:passed", ["reading-3", "passage"]),
    Rule("failed 3rd reading", ["reading-3", "failure"]),
    Rule("did not adopt", "amendment-failure"),
    Rule("withdrawn by sponsor", "withdrawal"),
    Rule("line item veto", "executive-veto-line-item"),
    Rule("governor signed", "executive-signature"),
    Rule("recommend (amend and )?do pass", "committee-passage-favorable"),
    Rule("recommend (amend and )?do not pass", "committee-passage-unfavorable"),
    Rule("received for introduction", "filing"),
    Rule("bill number assigned", "reading-1"),
    Rule("cow:passed", "committee-passage-favorable"),
    Rule("did not consider for introduction", "deferral"),
    Rule("did not consider for cow", "committee-failure"),
    Rule("died in committee returned bill", "committee-failure"),
    Rule("veto message received", "executive-veto"),
    Rule("assigned chapter number", "became-law"),
    Rule("governor vetoed sea no", "executive-veto"),
    Rule("governor vetoed hea no", "executive-veto"),
    Rule("governor signed hejr no", "executive-signature"),
    Rule("cow:failed", "committee-failure"),
    Rule("3rd reading:failed", "failure"),
    Rule("withdrawn", "withdrawal"),
)


class Categorizer(BaseCategorizer):
    rules = rules

    def categorize(self, text):
        attrs = BaseCategorizer.categorize(self, text)
        return attrs
