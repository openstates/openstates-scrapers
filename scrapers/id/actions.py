from utils.actions import Rule, BaseCategorizer

rules = (
    Rule(r"^Introduced", "introduction"),
    # reading-1
    Rule(
        r"(\w+) intro - (\d)\w+ rdg - to (\w+/?\s?\w+\s?\w+)",
        ["introduction", "reading-1"],
    ),
    # committee actions
    Rule(r"rpt prt - to\s(\w+/?\s?\w+)", "referral-committee"),
    # it is difficult to figure out which committee passed/reported out a bill
    # but i guess we at least know that only committees report out
    Rule(r"rpt out - rec d/p", "committee-passage-favorable"),
    Rule(r"^rpt out", "committee-passage"),
    Rule(r"^rpt out", "committee-passage"),
    Rule(
        r"Reported out of Committee with Do Pass Recommendation",
        "committee-passage-favorable",
    ),
    Rule(r"Reported out of Committee without Recommendation", "committee-passage"),
    Rule(r"^Reported Signed by Governor", "executive-signature"),
    Rule(r"^Signed by Governor", "executive-signature"),
    Rule(r"Became law without Governor.s signature", "became-law"),
    # I dont recall seeing a 2nd rdg by itself
    Rule(r"^1st rdg - to 2nd rdg", "reading-2"),
    # second to third will count as a third read if there is no
    # explicit third reading action
    Rule(r"2nd rdg - to 3rd rdg", "reading-3"),
    Rule(r"^3rd rdg$", "reading-3"),
    Rule(r".*Third Time.*PASSED.*", ["reading-3", "passage"]),
    # reading-3, passage
    Rule(r"^3rd rdg as amen - (ADOPTED|PASSED)", ["reading-3", "passage"]),
    Rule(r"^3rd rdg - (ADOPTED|PASSED)", ["reading-3", "passage"]),
    Rule(r"^Read Third Time in Full .* (ADOPTED|PASSED).*", ["reading-3", "passage"]),
    Rule(r"^.*read three times - (ADOPTED|PASSED).*", ["reading-3", "passage"]),
    Rule(r"^.*Read in full .* (ADOPTED|PASSED).*", ["reading-3", "passage"]),
    # reading-3, failure
    Rule(r"^3rd rdg as amen - (FAILED)", ["reading-3", "failure"]),
    Rule(r"^3rd rdg - (FAILED)", ["reading-3", "failure"]),
    # rules suspended
    Rule(r"^Rls susp - ADOPTED", "passage"),
    Rule(r"^Rls susp - PASSED", "passage"),
    Rule(r"^Rls susp - FAILED", "failure"),
    Rule(r"^to governor", "executive-receipt"),
    Rule(r"^Governor signed", "executive-signature"),
    Rule(r"^Returned from Governor vetoed", "executive-veto"),
    Rule(r"Reported out of Committee and referred to", "referral-committee"),
    Rule(r"Read second time", "reading-2"),
    Rule(r"Signed by President", "passage"),
    Rule(r"Signed by Speaker", "passage"),
    Rule(r"to Governor", "executive-receipt"),
    Rule(r"Read First Time, Referred to", ["reading-1", "referral-committee"]),
    Rule(r"Read First Time, Filed for Second Reading", "reading-1"),
    Rule(r"Read First Time, Filed for Second Reading", "reading-1"),
    Rule(r"[Ee]nrolling", "enrolled"),
    Rule(r"Read third time in full – PASSED", "passage"),
    Rule(r"Read third time in full – FAILED", "failure"),
)


class Categorizer(BaseCategorizer):
    rules = rules

    def categorize(self, text):
        attrs = BaseCategorizer.categorize(self, text)
        return attrs
