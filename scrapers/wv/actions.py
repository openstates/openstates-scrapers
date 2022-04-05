"""

"""
import re
from utils.actions import Rule, BaseCategorizer


committees = [
    "Veterans' Affairs",
    "Agriculture and Agri-business Committee",
    "Agriculture",
    "Banking and Insurance",
    "Banking",
    "Children, Juveniles and Other Issues",
    "Constitutional Revision",
    "Council of Finance and Administration",
    "Economic Development and Small Business",
    "Economic Development",
    "Education Accountability",
    "Education",
    "Employee Suggestion Award Board",
    "Energy, Industry and Labor",
    "Energy, Industry and Labor/Economic Development and Small Business",
    "Enrolled Bills",
    "Equal Pay Commission",
    "Finance",
    "Forest Management Review Commission",
    "Government and Finance",
    "Government Operations",
    "Government Organization",
    "Health and Human Resources Accountability",
    "Health and Human Resources",
    "Health",
    "Homeland Security",
    "House Rules",
    "House Select Committee on Redistricting",
    "Infrastructure",
    "Insurance",
    "Intern Committee",
    "Interstate Cooperation",
    "Judiciary",
    "Law Institute",
    "Minority Issues",
    "Natural Resources",
    "Outcomes-Based Funding Models in Higher Education",
    "Parks, Recreation and Natural Resources",
    "PEIA, Seniors and Long Term Care",
    "Pensions and Retirement",
    "Political Subdivisions",
    "Post Audits",
    "Regional Jail and Correctional Facility Authority",
    "Roads and Transportation",
    "Rule-Making Review Committee",
    "Senior Citizen Issues",
    "Special Investigations",
    "Technology",
    "Veterans Affairs",
    "Veterans Affairs/ Homeland Security",
    "Water Resources",
    "Workforce Investment for Economic Development",
]


committees_rgx = "(%s)" % "|".join(sorted(committees, key=len, reverse=True))


rules = (
    Rule(
        ["Communicated to Senate", "Senate received", "Ordered to Senate"],
        actor="upper",
    ),
    Rule(
        ["Communicated to House", "House received", "Ordered to House"], actor="lower"
    ),
    Rule("Read 1st time", "reading-1"),
    Rule("Read 2nd time", "reading-2"),
    Rule("Read 3rd time", "reading-3"),
    Rule("Filed for introduction", "filing"),
    Rule("^Introduced in", "introduction"),
    Rule(["Passed Senate", "Passed House"], "passage"),
    Rule(["Reported do pass", "With amendment, do pass"], "committee-passage"),
    Rule(
        [
            ", but first to .+?; then (?P<committees>[^;]+)",
            "To (?P<committees>.+?) then",
        ]
    ),
    Rule("(?i)voice vote", voice_vote=True),
    Rule(["Amendment rejected"], ["amendment-failure"]),
    Rule(["To Governor"], ["executive-receipt"]),
    Rule(["Passed House"], ["passage"]),
    Rule(["Read 2nd time"], ["reading-2"]),
    Rule([", but first to (?P<committees>[^;]+)", "Rejected"], []),
    Rule([r"Approved by Governor \d{1,2}/\d{1,2}/\d{1,2}$"], ["executive-signature"]),
    Rule(["^Introduced"], ["introduction"]),
    Rule(["To .+? then (?P<committees>.+)"], []),
    Rule(["^Filed for intro"], ["filing"]),
    Rule(["(?i)referred to (?P<committees>.+)"], ["referral-committee"]),
    Rule("Senator (?P<legislators>.+? )requests " "to be removed as sponsor of bill"),
    Rule(["To House (?P<committees>[A-Z].+)"], ["referral-committee"]),
    Rule(["Passed Senate"], ["passage"]),
    Rule(["(?i)committed to (?P<committees>.+?) on"], []),
    Rule(["Vetoed by Governor"], ["executive-veto"]),
    Rule(["(?i)House concurred in senate amendment"], []),
    Rule(["Be rejected"], ["failure"]),
    Rule(["To .+? then (?P<committees>.+) then", "reading to (?P<committees>.+)"]),
    Rule(["Adopted by"], ["passage"]),
    Rule(["House appointed conferees:  (?P<legislators>.+)"], []),
    Rule(["Read 3rd time"], ["reading-3"]),
    Rule(["Be adopted$"], ["passage"]),
    Rule(
        [
            "(?i)originating in (House|Senate) (?P<committees>.+)",
            "(?i)to house (?P<committees>.+)",
        ]
    ),
    Rule(["Read 1st time"], ["reading-1"]),
    Rule(["To .+? then .+? then (?P<committees>.+)"]),
    Rule(r"To %s" % committees_rgx, "referral-committee"),
)


class Categorizer(BaseCategorizer):
    rules = rules

    def categorize(self, text):
        """Wrap categorize and add boilerplate committees."""
        attrs = BaseCategorizer.categorize(self, text)
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

                # Strip stuff like "Rules on 1st reading"
                for text in text.split("then"):
                    text = re.sub(r" on .+", "", text)
                    text = text.strip()
                    res.add(text)
        attrs["committees"] = list(res)
        return attrs
