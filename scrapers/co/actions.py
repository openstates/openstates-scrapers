import re
from utils.actions import Rule, BaseCategorizer


committees = [
    "Agriculture, Livestock (?:and|&) Natural Resources",
    "Finance",
    "Joint Budget Committee",
    "Appropriations",
    "Health (?:and|&) Environment",
    "Transportation",
    "Education",
    "Agriculture, Livestock, (?:and|&) Natural Resources",
    "Judiciary",
    "Legal Services",
    "State, Veterans (?:and|&) Military Affairs",
    "Economic (?:and|&) Business Development",
    "Local Government",
    "Congressional Redistricting",
    "Legislative Council",
    "State Veterans, (?:and|&) Military Affairs",
    "Health (?:and|&) Environment",
    "Legislative Audit",
    "Capital Development",
    "State, Veterans, (?:and|&) Military Affairs",
    "State, Veterans, (?:and|&) Military Affairs",
    "Executive Committee of Legislative Council",
    "Health (?:and|&) Environment",
    "Finance",
    "Appropriations",
    "Agriculture, Natural Resources (?:and|&) Energy",
    "Judiciary",
    "Business, Labor (?:and|&) Technology",
    "Health (?:and|&) Human Services",
    "State, Veterans (?:and|&) Military Affairs",
    "Local Government",
    "Legislative Audit",
    "Executive Committee of Legislative Council",
    "Transportation",
    "Health (?:and|&) Human Services",
    "Education",
    "Legislative Council",
    "Legal Services",
    "Capital Development",
    "Transportation (?:and|&) Energy",
    "Joint Budget Committee",
    "Business, Labor, (?:and|&) Technology",
    "State, Veterans, (?:and|&) Military Affairs",
]


rules = (
    Rule("^House", actor="lower"),
    Rule("^Senate", actor="upper"),
    Rule("^Introduced in Senate", actor="upper"),
    Rule("^Introduced in House", actor="lower"),
    Rule("^Governor", actor="executive"),
    Rule("Governor Action - Partial Veto", "executive-veto-line-item"),
    Rule("Sent to the Governor", "executive-receipt"),
    Rule("Governor Action - Signed", "executive-signature"),
    Rule("Governor Signed", "executive-signature"),
    Rule("Governor Action - Vetoed", "executive-veto"),
    Rule(r"^Introduced", "introduction"),
    Rule(r"Assigned to (?P<committees>.+)"),
    Rule("(?i)refer (un)?amended to (?P<committees>.+)", ["referral-committee"]),
    Rule(r"(?i)\S+ Committee on (?P<committees>.+?) Refer (un)amended"),
    Rule("Assigned to (<?P<committees>.+?)", "referral-committee"),
    Rule("Second Reading Passed", ["reading-2"]),
    Rule("Third Reading Passed", ["reading-3", "passage"]),
    Rule("to Senate Committee of the Whole", "committee-passage", actor="upper"),
    Rule("to House Committee of the Whole", "committee-passage", actor="lower"),
    Rule("Governor Vetoed", "executive-veto", actor="executive"),
)

committees_rgx = "(%s)" % "|".join(sorted(committees, key=len, reverse=True))


class Categorizer(BaseCategorizer):
    rules = rules

    def categorize(self, text):
        """Wrap categorize and add boilerplate committees."""
        attrs = BaseCategorizer.categorize(self, text)
        if "committees" in attrs:
            committees = attrs["committees"]
            for committee in re.findall(committees_rgx, text, re.I):
                if committee not in committees:
                    committees.append(committee)
        return attrs

    def post_categorize(self, attrs):
        res = set()
        if "legislators" in attrs:
            for text in attrs["legislators"]:
                rgx = r"(,\s+(?![a-z]\.)|\s+and\s+)"
                legs = re.split(rgx, text)
                legs = filter(lambda x: x not in [", ", " and "], legs)
                res |= set(legs)
        attrs["legislators"] = list(res)

        res = set()
        if "committees" in attrs:
            for text in attrs["committees"]:
                for committee in text.split(" + "):
                    res.add(committee.strip())
        attrs["committees"] = list(res)
        return attrs
