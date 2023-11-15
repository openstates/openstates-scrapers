from utils.actions import Rule, BaseCategorizer

rules = (
    Rule("^introduced ((?!referred to).)", "introduction"),
    Rule("^introduced.*referred to", ["introduction", "referral-committee"]),
    Rule("^referred to", "referral-committee"),
    Rule("^read first time", "reading-1"),
    Rule("^(sent to governor)", "executive-receipt"),
    Rule("^(reported signed by governor)", "executive-signature"),
    Rule("^(signed by governor)", "executive-signature"),
    Rule("^(vetoed by governor)", "executive-veto"),
    Rule("^(item veto)", "executive-veto-line-item"),
    Rule("passed (house|senate)", "passage"),
    Rule(r"amendment (s|h)-\d+ filed.*((?!adopted).)", "amendment-introduction"),
    Rule(
        r"amendment (s|h)-\d+ filed.*adopted",
        ["amendment-introduction", "amendment-passage"],
    ),
    Rule(r"amendment (s|h)-\d+( as amended,)? adopted", "amendment-passage"),
    Rule(r"amendment (s|n)-\d+ lost", "amendment-failure"),
    Rule("^(resolution filed)", "introduction"),
    Rule("^(resolution adopted)", "passage"),
    Rule("^committee report", "committee-passage"),
    Rule("subcommittee recommends passage", "committee-passage-favorable"),
    Rule("^withdrawn", "withdrawal"),
)


class Categorizer(BaseCategorizer):
    rules = rules

    def categorize(self, text):
        attrs = BaseCategorizer.categorize(self, text)
        return attrs
