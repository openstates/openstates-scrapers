from utils.actions import Rule, BaseCategorizer

_categorizer_rules = (
    Rule(r"Introduced and Referred", ["introduction", "referral"]),
    Rule(r"Read First Time", "reading-1"),
    Rule("Introduced", "introduction"),
    Rule("(Forwarded|Delivered) to Governor", "executive-receipt"),
    Rule("Amendment (?:.*)Offered", "amendment-introduction"),
    Rule("Substitute (?:.*)Offered", "amendment-introduction"),
    Rule("Amendment (?:.*)adopted", "amendment-passage"),
    Rule("Amendment lost", "amendment-failure"),
    Rule(
        "Read for the first time and referred to", ["reading-1", "referral-committee"]
    ),
    Rule("(r|R)eferred to", "referral-committee"),
    Rule("Read for the second time", "reading-2"),
    Rule("(S|s)ubstitute adopted", "substitution"),
    Rule("(m|M)otion to Adopt (?:.*)adopted", "amendment-passage"),
    Rule("(m|M)otion to (t|T)able (?:.*)adopted", "amendment-passage"),
    Rule("(m|M)otion to Adopt (?:.*)lost", "amendment-failure"),
    Rule("(m|M)otion to Read a Third Time and Pass adopted", "passage"),
    Rule("(m|M)otion to Concur In and Adopt adopted", "passage"),
    Rule("Third Reading Passed", "passage"),
    Rule("Reported from", "committee-passage"),
    Rule("Reported Favorably", "committee-passage"),
    Rule("Indefinitely Postponed", "failure"),
    Rule("Passed by House of Origin", "passage"),
    Rule("Passed Second House", "passage"),
    Rule("Read a Third Time and Pass", "passage"),
    # memorial resolutions can pass w/o debate
    Rule("Joint Rule 11", ["introduction", "passage"]),
    Rule("Lost in", "failure"),
    Rule("Favorable from", "committee-passage-favorable"),
    # Signature event does not appear to be listed as a specific action
    Rule("Assigned Act No", "executive-signature"),
    Rule("Enacted", "became-law"),
)


class Categorizer(BaseCategorizer):
    rules = _categorizer_rules

    def categorize(self, text):
        attrs = BaseCategorizer.categorize(self, text)
        return attrs
