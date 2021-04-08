import re
from utils.actions import Rule, BaseCategorizer

# These are regex patterns that map to action categories.
_categorizer_rules = (
    Rule(
        [
            # Add a bajilion links to entities.
            r"SCs (changed|removed) (?P<legislators>.+)",
            r"Conference Committee on (?P<committees>.+)",
            r"Conference granted, naming:?\s+Conference Committee on (?P<committees>.+)",
            r"vote by Representative(?P<legislators>.+)",
            r"amended (?P<committees>.+?) committee",
            r"coauthored by (?P<legislators>.+)",
            (
                r"Remove Senator .+? as principal Senate author "
                r"and substitute with Senator (?P<legislators>.+?)"
            ),
            r"(?i)committee substitute (?P<committees>.+)",
            r"(?i)remove\s{,10}as\s{,10}author\s{,10}(?P<legislators>.+);",
            r"(?i)SCs\s{,10}named\s{,10}(?P<legislators>.+)",
            (
                r"Pending removal author Senator (?P<legislators>.+?) "
                r"and replace with Senator"
            ),
            r"(?i)Representative\(s\)\s{,10}(?P<legislators>.+)",
            r"Withdrawn from Calendar; (?P<committees>.+)",
            (
                r"Pending removal author Senator .+? and replace "
                r"with Senator (?P<legislators>.+)"
            ),
            r"Ayes:\s+(?P<yes_votes>\d+)\s+Nays:\s+(?P<no_votes>\d+)",
            (
                r"remove as principal author Representative .+? and substitute "
                r"with Representative (?P<legislators>.+?)"
            ),
            r"Pending coauthorship Senator\(s\) (?P<legislators>.+)",
            (
                r"Remove Representative (?P<legislators>.+?) as principal "
                r"House author and substitute with Representative"
            ),
            r"Pending removal principal author Representative .+? and "
            r"replace with Representative (?P<legislators>.+)",
            r"(?i)(co)?authored\s{,10}by\s{,10}(?P<legislators>.+)",
            r"Second Reading referred to (?P<committees>.+? Committee)",
            r"Notice served to reconsider vote on measure (?P<legislators>.+)",
            (
                r"Pending removal principal author Representative (?P<legislators>.+) "
                r"and replace with Representative .+"
            ),
            (
                r"remove as principal author Representative (?P<legislators>.+?) "
                r"and substitute with Representative"
            ),
            r"CR; Do Pass(, as amended,|, amended by)? (?P<committees>.+)",
            r"coauthor (Senator|Representative) (?P<legislators>.+)",
            r"Ayes:\s+(?P<yes_votes>\d+)\s+Nays:\s+(?P<no_votes>\d+)",
        ]
    ),
    Rule(u"Introduced", "introduction"),
    Rule([u"Adopted"], [u"passage"]),
    Rule([u"HAs rejected"], [u"amendment-failure"]),
    Rule(u"(?i)Measure.+?passed", "passage"),
    Rule(u"(?i)Measure.+?passed", "passage"),
    Rule(u"Engrossed", "passage"),
    Rule(u"Third Reading, Measure passed", ["passage", "reading-3"]),
    Rule([u"^Amendment withdrawn"], [u"amendment-withdrawal"]),
    Rule([u"^Amended$"], [u"amendment-passage"]),
    Rule([u"^Amendment failed"], [u"amendment-failure"]),
    Rule([u"^Amendment restore"], [u"amendment-passage"]),
    Rule("First Reading", ("introduction", "reading-1")),
    Rule(
        [u"Second Reading referred to (?P<committees>.+)"],
        [u"referral-committee", u"reading-2"],
    ),
    Rule(
        [u"Second Reading referred to (?P<committees>.+? Committee)"],
        [u"referral-committee", u"reading-2"],
    ),
    Rule(
        [u"Second Reading referred to .+? then to (?P<committees>.+)"],
        [u"referral-committee", u"reading-2"],
    ),
    Rule(
        [u"Second Reading referred to (?P<committees>.+?) then to "],
        [u"referral-committee", u"reading-2"],
    ),
    Rule(
        [u"Second Reading referred to .+? then to (?P<committees>.+)"],
        [u"referral-committee", u"reading-2"],
    ),
    Rule([u"(?i)Placed on Third Reading"], [u"reading-3"]),
    Rule([u"^(?i)Third Reading"], [u"reading-3"]),
    Rule(r"committee substitute (?P<committees>.+?);"),
    Rule([u"Do Pass (as amended )?(?P<committees>.+)"], [u"committee-passage"]),
    Rule([u"Failed in Committee - (?P<committees>.+)"], [u"committee-failure"]),
    Rule([u"CR; Do not pass (?P<committees>.+)"], [u"committee-failure"]),
    Rule([u"rereferred to (?P<committees>.+)"], [u"referral-committee"]),
    Rule([u"Referred to (?P<committees>.+?)"], [u"referral-committee"]),
    Rule(
        [u"Reported Do Pass, amended by committee substitute (?P<committees>.+?);"],
        [u"committee-passage"],
    ),
    Rule([u"^(?i)Reported Do Pass"], [u"committee-passage"]),
    Rule(
        [u"Do pass, amended by committee substitute (?P<committees>)"],
        [u"committee-passage"],
    ),
    Rule([u"Sent to Governor"], [u"executive-receipt"], actor="governor"),
    Rule(
        [u"^(Signed|Approved) by Governor"], [u"executive-signature"], actor="governor"
    ),
    Rule([u"^Vetoed"], [u"executive-veto"], actor="governor"),
    Rule([r"Veto overridden"], ["veto-override-passage"]),
)


class Categorizer(BaseCategorizer):
    rules = _categorizer_rules

    def post_categorize(self, attrs):
        res = set()
        if "legislators" in attrs:
            for text in attrs["legislators"]:
                text = text.replace("Representative(s)", "")
                text = text.replace("(principal House author) ", "")
                rgx = r"(,\s+(?![a-z]\.)|\s+and\s+)"
                legs = re.split(rgx, text)
                legs = filter(lambda x: x not in [", ", " and "], legs)
                res |= set(legs)
        attrs["legislators"] = list(res)

        res = set()
        if "committees" in attrs:
            for text in attrs["committees"]:
                text = text.replace("by committee substitute", "")
                text = text.replace("CR filed;", "")
                text = text.replace("; pending CR", "")
                text = text.strip()
                res.add(text)
        attrs["committees"] = list(res)
        return attrs
