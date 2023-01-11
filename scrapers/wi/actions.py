from utils.actions import Rule, BaseCategorizer

rules = (
    Rule(
        r"(Senate|Assembly)( substitute)? amendment .* offered",
        "amendment-introduction",
    ),
    Rule(r"(Senate|Assembly)( substitute)? amendment .* rejected", "amendment-failure"),
    Rule(r"(Senate|Assembly)( substitute)? amendment .* adopted", "amendment-passage"),
    Rule(
        r"(Senate|Assembly)( substitute)? amendment .* laid on table",
        "amendment-deferral",
    ),
    Rule(
        r"(Senate|Assembly)( substitute)? amendment .* withdrawn",
        "amendment-withdrawal",
    ),
    Rule(
        r"Report (adoption|introduction and adoption) of Senate( Substitute)? Amendment",
        "amendment-passage",
    ),
    Rule(r"Report (passage|concurrence).* recommended", "committee-passage-favorable"),
    Rule(
        r"Report approved by the Governor with partial veto", "executive-veto-line-item"
    ),
    Rule(r"Report approved by the Governor on", "executive-signature"),
    Rule(r"Report vetoed by the Governor", "executive-veto"),
    Rule(r"R(ead (first time )?and r)?eferred to committee", "referral-committee"),
    Rule(r"Read a third time and (passed|concurred)", "passage"),
    Rule(r"Adopted", "passage"),
    Rule(r"Presented to the Governor", "executive-receipt"),
    Rule(r"Introduced by", "introduction"),
    Rule(r"Read a second time", "reading-2"),
    Rule(r"Ordered to a third reading", "reading-3"),
    Rule(r"Read a third time", "reading-3"),
    Rule(r"Report correctly enrolled", "enrolled"),
    Rule(r"Published", "became-law"),
    Rule(r"^Read first time.*Committee", ["reading-1", "referral-committee"]),
    Rule(r"Read first time and referred to calendar", "reading-1"),
    Rule(r"Failed to pass", "failure"),
    Rule(r"Failed to concur", "amendment-failure"),
    Rule(r"Failed to adopt", "amendment-failure"),
    Rule(r"referred to committee", "referral-committee"),
    Rule(r"withdraw from calendar", "withdrawal"),
    Rule(r"withdrawn as a coauthor", "withdrawal"),
    Rule(r"withdrawn as a cosponsor", "withdrawal"),
    Rule(r"adoption recommended by.*[Cc]ommittee", "committee-passage-favorable"),
    Rule(r"Refused to adopt.*Amendment", "amendment-failure"),
    Rule(r".*Amendment.*adopted", "amendment-passage"),
    Rule(r"[Rr]eceive", "receipt"),
    Rule(r"table", "deferral"),
    Rule(r"table", "deferral"),
    Rule(r"Referred to.*[Cc]ommittee", "referral-committee"),
    Rule(r"Referred to calendar", "referral"),
)


class Categorizer(BaseCategorizer):
    rules = rules

    def categorize(self, text):
        attrs = BaseCategorizer.categorize(self, text)
        return attrs
