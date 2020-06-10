"""

"""
import re
from utils.actions import Rule, BaseCategorizer


committees = [
    u"Veterans' Affairs",
    u"Agriculture and Agri-business Committee",
    u"Agriculture",
    u"Banking and Insurance",
    u"Banking",
    u"Children, Juveniles and Other Issues",
    u"Constitutional Revision",
    u"Council of Finance and Administration",
    u"Economic Development and Small Business",
    u"Economic Development",
    u"Education Accountability",
    u"Education",
    u"Employee Suggestion Award Board",
    u"Energy, Industry and Labor",
    u"Energy, Industry and Labor/Economic Development and Small Business",
    u"Enrolled Bills",
    u"Equal Pay Commission",
    u"Finance",
    u"Forest Management Review Commission",
    u"Government and Finance",
    u"Government Operations",
    u"Government Organization",
    u"Health and Human Resources Accountability",
    u"Health and Human Resources",
    u"Health",
    u"Homeland Security",
    u"House Rules",
    u"House Select Committee on Redistricting",
    u"Infrastructure",
    u"Insurance",
    u"Intern Committee",
    u"Interstate Cooperation",
    u"Judiciary",
    u"Law Institute",
    u"Minority Issues",
    u"Natural Resources",
    u"Outcomes-Based Funding Models in Higher Education",
    u"Parks, Recreation and Natural Resources",
    u"PEIA, Seniors and Long Term Care",
    u"Pensions and Retirement",
    u"Political Subdivisions",
    u"Post Audits",
    u"Regional Jail and Correctional Facility Authority",
    u"Roads and Transportation",
    u"Rule-Making Review Committee",
    u"Senior Citizen Issues",
    u"Special Investigations",
    u"Technology",
    u"Veterans Affairs",
    u"Veterans Affairs/ Homeland Security",
    u"Water Resources",
    u"Workforce Investment for Economic Development",
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
    Rule(["Amendment rejected"], [u"amendment-failure"]),
    Rule(["To Governor"], [u"executive-receipt"]),
    Rule(["Passed House"], [u"passage"]),
    Rule(["Read 2nd time"], [u"reading-2"]),
    Rule([", but first to (?P<committees>[^;]+)", u"Rejected"], []),
    Rule([r"Approved by Governor \d{1,2}/\d{1,2}/\d{1,2}$"], [u"executive-signature"]),
    Rule(["^Introduced"], [u"introduction"]),
    Rule(["To .+? then (?P<committees>.+)"], []),
    Rule(["^Filed for intro"], [u"filing"]),
    Rule(["(?i)referred to (?P<committees>.+)"], [u"referral-committee"]),
    Rule("Senator (?P<legislators>.+? )requests " "to be removed as sponsor of bill"),
    Rule(["To House (?P<committees>[A-Z].+)"], [u"referral-committee"]),
    Rule(["Passed Senate"], [u"passage"]),
    Rule(["(?i)committed to (?P<committees>.+?) on"], []),
    Rule(["Vetoed by Governor"], [u"executive-veto"]),
    Rule(["(?i)House concurred in senate amendment"], []),
    Rule(["Be rejected"], [u"failure"]),
    Rule(["To .+? then (?P<committees>.+) then", "reading to (?P<committees>.+)"]),
    Rule(["Adopted by"], [u"passage"]),
    Rule(["House appointed conferees:  (?P<legislators>.+)"], []),
    Rule(["Read 3rd time"], [u"reading-3"]),
    Rule(["Be adopted$"], [u"passage"]),
    Rule(
        [
            "(?i)originating in (House|Senate) (?P<committees>.+)",
            "(?i)to house (?P<committees>.+)",
        ]
    ),
    Rule(["Read 1st time"], [u"reading-1"]),
    Rule(["To .+? then .+? then (?P<committees>.+)"]),
    Rule(r"To %s" % committees_rgx, "referral-committee"),
)


class Categorizer(BaseCategorizer):
    rules = rules

    def categorize(self, text):
        """Wrap categorize and add boilerplate committees.
        """
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
