from utils.actions import Rule, BaseCategorizer

rules = (
    Rule("^Amended$", "amendment-passage"),
    Rule(r"^Amendment\(s\) offered$", "amendment-introduction"),
    Rule("^Amendment amended$", "amendment-amendment"),
    Rule("^Amendment withdrawn$", "amendment-withdrawal"),
    Rule("^Passed$", "passage"),
    Rule("^Adopted$", "passage"),
    Rule("^Received (by|from) the.*Secretary of the Senate", "filing"),
    Rule("^Received (by|from) the", "introduction"),
    Rule("^Sent to the Governor", "executive-receipt"),
    Rule("^Signed by the Governor", "executive-signature"),
    Rule("^Effective on", "became-law"),
    Rule("^Vetoed by the Governor$", "executive-veto"),
    Rule("^Read first time$", ["introduction", "reading-1"]),
    Rule("^Read & adopted$", ["passage", "introduction"]),
    Rule("^Passed as amended$", "passage"),
    Rule("^Referred to", "referral-committee"),
    Rule("^Recommended to be sent to", "referral-committee"),
    Rule(r"^Reported favorably w/o amendment\(s\)$", "committee-passage"),
    Rule("^Filed$", "filing"),
    Rule("^Read 3rd time$", "reading-3"),
    Rule("^Read 2nd time$", "reading-2"),
    Rule("^Reported favorably", "committee-passage-favorable"),
    Rule("^Effective immediately$", "became-law"),
    Rule("^Filed without the Governor's signature$", "became-law"),
    Rule("Signed in the House", "passage"),
    Rule("Signed in the Senate", "passage"),
    Rule("Reported enrolled", "enrolled"),
    Rule("filed", "filing"),
    Rule("Read 2nd time", "reading-2"),
    Rule("Passed.*amended", "amendment-passage"),
    Rule("Senate passage.*amended", "amendment-passage"),
    Rule("House passage.*amended", "amendment-passage"),
    Rule("House passage reported", "passage"),
    Rule("Senate passage reported", "passage"),
    Rule("[Aa]mendment fails of adoption", "amendment-failure"),
    Rule("Failed to receive affirmative vote in comm", "committee-failure"),
    Rule("Failed to pass", "failure"),
    Rule("[Ww]ithdraw", "withdrawal"),
    Rule("Amendment.*adopted", "amendment-passage"),
    Rule("Laid before", "receipt"),
    Rule("adopts conference committee report", "committee-passage-favorable"),
    Rule("Transmitted to the Governor", "executive-signature"),
    Rule("on the table", "deferral"),
    Rule("Amendment tabled", "deferral"),
    Rule("Committee substitute", "substitution"),
)


class Categorizer(BaseCategorizer):
    rules = rules

    def categorize(self, text):
        attrs = BaseCategorizer.categorize(self, text)
        return attrs
