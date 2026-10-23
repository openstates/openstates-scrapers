import re
from utils.actions import Rule, BaseCategorizer


rules = (
    Rule(
        [
            (
                r"(?P<yes_votes>\d+) Yeas - (?P<no_votes>\d+) "
                r"Nays- (?P<excused>\d+) Excused - (?P<absent>\d+) Absent"
            ),
            (
                r"(?P<yes_votes>\d+) -Yeas, (?P<no_votes>\d+) -Nays, "
                r"(?P<excused>\d+) -Excused, (?P<absent>\d+) -Absent"
            ),
            r"(?P<committees>Committee on .+?) suggested and ordered printed",
            (
                r"\(Yeas (?P<yes_votes>\d+) - Nays (?P<no_votes>\d+) - Absent "
                r"(?P<absent>\d+) - Excused (?P<excused>\d+)\)( \(Vacancy "
                r"(?P<vacant>\d+)\))?"
            ),
        ]
    ),
    Rule(
        [
            r"Representative (?P<legislators>.+?) of \S+",
            r"Senator (?P<legislators>.+?of \S+)",
            r"Representative (?P<legislators>[A-Z]+?( of [A-Za-z]+))",
            r"Senator (?P<legislators>\S+ of \S+)",
            r"Representative [A-Z ]+? of \S+",
        ]
    ),
    Rule(
        "REFERRED to the (?P<committees>Committee on [A-Z ]+(?![a-z]))",
        "referral-committee",
    ),
    Rule(["READ A SECOND TIME"], ["reading-2"]),
    Rule(["read once"], ["reading-1"]),
    Rule("finally passed", "passage"),
    Rule("passed to be enacted", "passage"),
    Rule(r"COMMITTED to the (?P<committees>Committee on .+?)\.", "referral-committee"),
    Rule(r"Sent to the Engrossing Department", "became-law"),
    Rule(r"VETO was NOT SUSTAINED", "veto-override-passage"),
    Rule(r"VETO was OVERRIDDEN", "veto-override-passage"),
    Rule(r"VETO was SUSTAINED", "veto-override-failure"),
    # amendment adoptions also end in "READ and ADOPTED."
    Rule(
        r"^(?!.*Amendment \").*READ and (PASSED|ADOPTED)(, in concurrence)?\.$",
        "passage",
    ),
    Rule(r"ENGROSSED", "reading-3"),
    Rule(r"Received by the ", "receipt"),
    # not a floor amendment to a committee amendment
    Rule(
        r"^(?:(?!(House|Senate) Amendment).)*Committee Amendment(?=.*ADOPTED)",
        "committee-passage-favorable",
    ),
    Rule(r"DEAD", "failure"),
    # "the Bill FAILED PASSAGE TO BE ENGROSSED AS AMENDED by Committee Amendment"
    # is the bill failing, not the amendment
    Rule(
        r"^(?!.*FAILED PASSAGE TO BE ENGROSSED)(?=.*Committee Amendment)(?=.*FAILED)",
        "amendment-failure",
    ),
    Rule(
        [
            r"^(?!.*RECONSIDER).*FAIL(ED|URE)( of)? "
            r"(PASSAGE TO BE ENACTED|ENACTMENT|FINAL PASSAGE)",
            r"^(Subsequently, )?PASSAGE TO BE ENACTED.*FAILED",
        ],
        "failure",
    ),
    Rule(r"Withdraw", "withdrawal"),
    Rule(r"REFER to the Committee", "referral-committee"),
    # House "the Majority ... Report was ACCEPTED", Senate "... Report ACCEPTED",
    # and lettered "REPORT A Ought Not to Pass was ACCEPTED"
    Rule(r"Ought Not to Pass( Report)? (was )?ACCEPTED", "committee-failure"),
)


class Categorizer(BaseCategorizer):
    rules = rules

    def categorize(self, text):
        """Wrap categorize and add boilerplate committees."""
        attrs = BaseCategorizer.categorize(self, text)
        committees = attrs["committees"]
        for committee in re.findall(committees_rgx, text):
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
                text = text.strip()
                res.add(text)
        attrs["committees"] = list(res)
        return attrs


actor_regex = [
    (re.compile(r"(in|by) senate", re.I), "upper"),
    (re.compile(r"(in|by) house", re.I), "lower"),
    (re.compile(r"by governor", re.I), "executive"),
]


def get_actor(action_text, chamber, rgxs=actor_regex):
    """Guess the actor for a particular action."""
    for r, actor in rgxs:
        m = r.search(action_text)
        if m:
            return actor
    return chamber


committees = [
    "AGRICULTURE, CONSERVATION AND FORESTRY",
    "APPROPRIATIONS AND FINANCIAL AFFAIRS",
    "CRIMINAL JUSTICE AND PUBLIC SAFETY",
    "EDUCATION AND CULTURAL AFFAIRS",
    "ENERGY, UTILITIES AND TECHNOLOGY",
    "ENVIRONMENT AND NATURAL RESOURCES",
    "HEALTH AND HUMAN SERVICES",
    "INLAND FISHERIES AND WILDLIFE",
    "INSURANCE AND FINANCIAL SERVICES",
    "JOINT RULES",
    "JUDICIARY",
    "LABOR, COMMERCE, RESEARCH AND ECONOMIC DEVELOPMENT",
    "MARINE RESOURCES",
    "REGULATORY FAIRNESS AND REFORM",
    "STATE AND LOCAL GOVERNMENT",
    "TAXATION",
    "TRANSPORTATION",
    "VETERANS AND LEGAL AFFAIRS",
]
committees_rgx = "(%s)" % "|".join(sorted(committees, key=len, reverse=True))
