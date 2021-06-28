import re
from utils.actions import Rule, BaseCategorizer


rules = (
    Rule([r"Amendment (?P<bills>.+?) -\s+Laid On Table"], ["amendment-deferral"]),
    Rule(["Favorable"], ["committee-passage-favorable"]),
    Rule(["(?i)Amendment (?P<bills>.+?) defeated"], ["amendment-failure"]),
    Rule(["(?i)introduced and adopted in lieu of (?P<bills>.+)"], ["introduction"]),
    Rule(
        ["(?i)assigned to (?P<committees>.+?) Committee in"],
        ["referral-committee", "introduction"],
    ),
    Rule(["Signed by Governor"], ["executive-signature"]),
    Rule([r"(?i)Amendment (?P<bills>[\w\s]+?) Introduced"], ["amendment-introduction"]),
    Rule(["Amendment (?P<bills>.+?) -  Passed"], ["amendment-passage"]),
    Rule(["(?i)^Passed by"], ["passage"]),
    Rule(["^Defeated"], ["failure"]),
    Rule(["(?i)unfavorable"], ["committee-passage-unfavorable"]),
    Rule([r"Reported Out of Committee \((?P<committees>.+?)\)"], ["committee-passage"]),
    Rule(["Vetoed by Governor"], ["executive-veto"]),
    Rule(
        [r"(?i)Amendment (?P<bills>.+?)\s+-\s+Introduced"], ["amendment-introduction"]
    ),
    Rule([r"(?i)Amendment (?P<bills>[\w\s]+?) Passed"], ["amendment-passage"]),
    Rule(
        [r"Amendment (?P<bills>.+?) -  Defeated by House of .+?\. Votes: Defeated"],
        ["amendment-failure"],
    ),
    Rule(["^Introduced"], ["introduction"]),
    Rule(["Amendment (?P<bills>.+?) -  Defeated in House"], ["amendment-failure"]),
    Rule(["^Passed in House"], ["passage"]),
)


class Categorizer(BaseCategorizer):
    rules = rules

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


def get_actor(
    action_text,
    chamber,
    rgxs=(
        (re.compile(r"(in|by) senate", re.IGNORECASE), "upper"),
        (re.compile(r"(in|by) house", re.IGNORECASE), "lower"),
        (re.compile(r"by governor", re.IGNORECASE), "governor"),
    ),
):
    """Guess the actor for a particular action."""
    for r, actor in rgxs:
        m = r.search(action_text)
        if m:
            return actor
    return chamber
