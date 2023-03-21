import re
from collections import namedtuple


class Rule(namedtuple("Rule", "regex types stop attrs")):
    """If ``regex`` matches the action text, the resulting action's
    types should include ``types``.

    If stop is true, no other rules should be tested after this one;
    in other words, this rule conclusively determines the action's
    types and attrs.

    The resulting action should contain ``attrs``, which basically
    enables overwriting certain attributes, like the chamber if
    the action was listed in the wrong column.
    """

    def __new__(_cls, regex, types=None, stop=True, **kwargs):
        "Create new instance of Rule(regex, types, attrs, stop)"

        # Types can be a string or a sequence.
        if isinstance(types, str):
            types = set([types])
        types = set(types or [])

        # If no types are associated, assume that the categorizer
        # should continue looking at other rules.
        if not types:
            stop = False
        return tuple.__new__(_cls, (regex, types, stop, kwargs))


rules = (
    Rule("Filed for introduction", "filing"),
    Rule("Introduced, passed on first", ["introduction", "reading-1"]),
    # Some actions are listed in the wrong chamber column.
    # Fix the chamber before moving on to the other rules.
    Rule(r"^H\.\s", stop=False, chamber="lower"),
    Rule(r"^S\.\s", stop=False, chamber="upper"),
    Rule(r"Signed by S(\.|enate) Speaker", chamber="upper"),
    Rule(r"Signed by H(\.|ouse) Speaker", chamber="lower"),
    # Extract the vote counts to help disambiguate chambers later.
    Rule(r"Ayes\s*(?P<yes_votes>\d+),\s*Nays\s*(?P<no_votes>\d+)", stop=False),
    # Committees
    Rule(r"(?i)ref\. to (?P<committees>.+?Comm\.)", "referral-committee"),
    Rule(r"^Failed In S\.(?P<committees>.+?Comm\.)", "committee-failure"),
    Rule(r"^Failed In s/c (?P<committees>.+)", "committee-failure"),
    Rule(
        r"Rcvd\. from H., ref\. to S\. (?P<committees>.+)",
        "referral-committee",
        chamber="upper",
    ),
    Rule(r"Placed on cal\. (?P<committees>.+?) for", stop=False),
    Rule(r"Taken off notice for cal in s/c (?P<committees>.+)"),
    Rule(r"to be heard in (?P<committees>.+?Comm\.)"),
    Rule(r"Action Def. in S. (?P<committees>.+?Comm.)", chamber="upper"),
    Rule(r"(?i)Placed on S. (?P<committees>.+?Comm\.) cal. for", chamber="upper"),
    Rule(r"(?i)Assigned to (?P<committees>.+?comm\.)"),
    Rule(r"(?i)Placed on S. (?P<committees>.+?Comm.) cal.", chamber="upper"),
    Rule(r"(?i)Taken off Notice For cal\. in s/c.+?\sof\s(?P<committees>.+?)"),
    Rule(r"(?i)Taken off Notice For cal\. in s/c.+?\sof\s(?P<committees>.+?)"),
    Rule(r"(?i)Taken off Notice For cal\. in[: ]+(?!s/c)(?P<committees>.+)"),
    Rule(r"(?i)Re-referred To:\s+(?P<committees>.+)", "referral-committee"),
    Rule(r"Recalled from S. (?P<committees>.+?Comm.)"),
    # Amendments
    Rule(r"^Am\..+?tabled", "amendment-deferral"),
    Rule(
        r"^Am\. withdrawn\.\(Amendment \d+ \- (?P<version>\S+)", "amendment-withdrawal"
    ),
    Rule(
        r"^Am\. reconsidered(, withdrawn)?\.\(Amendment \d \- (?P<version>.+?\))",
        "amendment-withdrawal",
    ),
    Rule(
        r"adopted am\.\(Amendment \d+ of \d+ - (?P<version>\S+)\)", "amendment-passage"
    ),
    Rule(r"refused to concur.+?in.+?am", "amendment-failure"),
    # Bill passage
    Rule(r"^Passed H\.", "passage", chamber="lower"),
    Rule(r"^Passed S\.", "passage", chamber="upper"),
    Rule(r"^Passed Senate", "passage", chamber="upper"),
    Rule(r"^R/S Adopted", "passage"),
    Rule(r"R/S Intro., adopted", "passage"),
    Rule(r"R/S Concurred", "passage"),
    # Veto
    Rule(r"(?i)veto", "executive-veto"),
    # The existing rules for TN categorization:
    Rule("Amendment adopted", "amendment-passage"),
    Rule("Amendment failed", "amendment-failure"),
    Rule("Amendment proposed", "amendment-introduction"),
    Rule("adopted am.", "amendment-passage"),
    Rule("Am. withdrawn", "amendment-withdrawal"),
    Rule("Divided committee report", "committee-passage"),
    Rule("Filed for intro.", ["introduction", "reading-1"]),
    # TN has a process where it's 'passed' on each reading,
    # Prior to committee referral/passage and chamber passage
    # see http://www.capitol.tn.gov/about/billtolaw.html
    # these don't fall under committee-passage or passage classifications
    Rule("Intro., P1C", ["introduction"]),
    Rule("Introduced, Passed on First Consideration", ["introduction"]),
    Rule("Reported back amended, do not pass", "committee-passage-unfavorable"),
    Rule("Reported back amended, do pass", "committee-passage-favorable"),
    Rule("Rec. For Pass.", "committee-passage-favorable"),
    Rule("Rec. For pass.", "committee-passage-favorable"),
    Rule("Rec. for pass.", "committee-passage-favorable"),
    Rule("Reported back amended, without recommendation", "committee-passage"),
    Rule("Reported back, do not pass", "committee-passage-unfavorable"),
    Rule("w/ recommend", "committee-passage-favorable"),
    Rule("Ref. to", "referral-committee"),
    Rule("ref. to", "referral-committee"),
    Rule("Assigned to", "referral-committee"),
    Rule("Received from House", "introduction"),
    Rule("Received from Senate", "introduction"),
    Rule("Adopted, ", ["passage"]),
    Rule("Concurred, ", ["passage"]),
    Rule("Passed H., ", ["passage"]),
    Rule("Passed S., ", ["passage"]),
    Rule("Passed", "passage"),
    Rule("Second reading, adopted", ["passage", "reading-2"]),
    Rule("Second reading, failed", ["failure", "reading-2"]),
    Rule("Second reading, passed", ["passage", "reading-2"]),
    Rule("Transmitted to Gov. for action.", "executive-receipt"),
    Rule("Transmitted to Governor for.* action.", "executive-receipt"),
    Rule("Signed by Governor, but item veto", "executive-veto-line-item"),
    Rule("Signed by Governor", "executive-signature"),
    Rule("Signed by.* Speaker", "passage"),
    Rule("Withdrawn", "withdrawal"),
    Rule("tabled", "amendment-deferral"),
    Rule("widthrawn", "amendment-withdrawal"),
    Rule(r"Intro", "introduction"),
    Rule("ready for transmission", "receipt"),
    Rule("Subst", "substitution"),
    Rule("substituted", "substitution"),
    Rule("Enrolled", "enrolled"),
    Rule("Sponsor", "sponsorship"),
)


def categorize_action(action):
    types = set()
    attrs = {}

    for rule in rules:

        # Try to match the regex.
        m = re.search(rule.regex, action)
        if m or (rule.regex in action):
            # If so, apply its associated types to this action.
            types |= rule.types

            # Also add its specified attrs.
            attrs.update(m.groupdict())
            attrs.update(rule.attrs)

            # Break if the rule says so, otherwise continue testing against
            # other rules.
            if rule.stop is True:
                break

    # Returns types, attrs
    return list(types), attrs
