from utils.actions import Rule, BaseCategorizer

bill_action_rules = (
    Rule("Introduced", "introduction"),
    Rule("Transmitted to Mayor", "executive-receipt"),
    Rule("Signed", "executive-signature"),
    Rule("Signed by the Mayor ", "executive-signature"),
    Rule("Enacted", "became-law"),
    Rule("Law", "became-law"),
    Rule("Approved with Resolution Number", "became-law"),
    Rule("First Reading", "reading-1"),
    Rule("1st Reading", "reading-1"),
    Rule("Second Reading", "reading-2"),
    Rule("2nd Reading", "reading-2"),
    Rule("Final Reading|Third Reading|3rd Reading", "reading-3"),
    Rule("Third Reading", "reading-3"),
    Rule("3rd Reading", "reading-3"),
    Rule("Referred to", "referral-committee"),
    Rule("[Ff]iled", "filing"),
    Rule("Failed", "failure"),
    Rule("Failed", "failure"),
    Rule("Amendment.*Withdrawn", "amendment-withdrawal"),
    Rule("[Ww][Ii][Tt][Hh][Dd][Rr][Aa][Ww][Nn]", "withdrawal"),
    Rule("Amendment.*Substitute", "substitution"),
    Rule("Amendment.*Not Considered", "amendment-failure"),
    Rule("(?!.* Substitute )Amendment.*", "amendment-introduction"),
    Rule("with comments from the", "referral-committee"),
    Rule("Transmitted", "receipt"),
)

vote_action_rules = (
    Rule("Introduced", "introduction"),
    Rule("Transmitted to Mayor", "executive-receipt"),
    Rule("Signed", "executive-signature"),
    Rule("Signed by the Mayor ", "executive-signature"),
    Rule("Enacted", "became-law"),
    Rule("Law", "became-law"),
    Rule("Approved with Resolution Number", "became-law"),
    Rule("First Reading", "reading-1"),
    Rule("1st Reading", "reading-1"),
    Rule("Second Reading", "reading-2"),
    Rule("2nd Reading", "reading-2"),
    Rule("Final Reading|Third Reading|3rd Reading", "reading-3"),
    Rule("Third Reading", "reading-3"),
    Rule("3rd Reading", "reading-3"),
    Rule("Referred to", "referral-committee"),
)


class Vote_Categorizer(BaseCategorizer):
    rules = vote_action_rules

    def categorize(self, text):
        attrs = BaseCategorizer.categorize(self, text)
        return attrs


class Bill_Categorizer(BaseCategorizer):
    rules = bill_action_rules

    def categorize(self, text):
        attrs = BaseCategorizer.categorize(self, text)
        return attrs
