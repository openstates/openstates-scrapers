from utils.actions import Rule, BaseCategorizer

rules = (
    Rule("First reading", "reading-1"),
    Rule("Second reading", "reading-2"),
    Rule("Reread second time", "reading-2"),
    Rule("Third reading.*passed", ["reading-3", "passage"]),
    Rule("Third reading.*failed", ["reading-3", "failure"]),
    Rule("Reread third time.*passed", ["reading-3", "passage"]),
    Rule("Reread third time.*failed", ["reading-3", "failure"]),
    Rule("referred.*Committee on", "referral-committee"),
    Rule("reassigned.*Committee on", "referral-committee"),
    Rule("Committee report.*pass", "committee-passage"),
    Rule("Committee report.*fail", "committee-failure"),
    Rule(
        "(?!.* without amendment).*[Aa]mendment.*(pass|prevail|adopted)",
        "amendment-passage",
    ),
    Rule("(?!.* without amendment).*[Aa]mendment.*fail", "amendment-failure"),
    Rule("(?!.* without amendment).*[Aa]mendment.*withdraw", "amendment-withdrawal"),
    Rule("Signed by the Governor", "executive-signature"),
    Rule("Vetoed by the Governor", "executive-veto"),
    Rule("Signed by the President", "passage"),
    Rule("Signed by the Speaker", "passage"),
    Rule("Veto overridden", "veto-override-passage"),
    Rule("Public Law", "became-law"),
    Rule("[Ff]iled", "filing"),
    Rule("failed", "failure"),
    Rule("[Ww]ithdrawn", "withdrawal"),
    Rule("Referred to the (House|Senate)", "referral"),
    Rule("Returned to the", "receipt"),
)


class Categorizer(BaseCategorizer):
    rules = rules

    def categorize(self, text):
        attrs = BaseCategorizer.categorize(self, text)
        return attrs
