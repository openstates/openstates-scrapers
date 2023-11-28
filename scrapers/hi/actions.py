from utils.actions import Rule, BaseCategorizer
import re

rules = (
    Rule("Pass(ed)? First Reading", "reading-1"),
    Rule("Introduced and Pass(ed)? First Reading", ["introduction", "reading-1"]),
    Rule("Introduced", "introduction"),
    Rule("Re(-re)?ferred to ", "referral-committee"),
    Rule(
        "Passed Second Reading .* referred to the committee",
        ["reading-2", "referral-committee"],
    ),
    Rule(".* that the measure be PASSED", "committee-passage-favorable"),
    Rule("Received from (House|Senate)", "introduction"),
    Rule("Floor amendment .* offered", "amendment-introduction"),
    Rule("Floor amendment adopted", "amendment-passage"),
    Rule("Floor amendment failed", "amendment-failure"),
    Rule(".*Passed Third Reading", "passage"),
    Rule("Report and Resolution Adopted", "passage"),
    Rule("Enrolled to Governor", "executive-receipt"),
    Rule(" Act ", "became-law"),
    # Note, occasionally the gov sends intent to veto then doesn't. So use Vetoed not Veto
    Rule("Vetoed .* line-item", "executive-veto-line-item"),
    Rule("Vetoed", "executive-veto"),
    Rule("Veto overridden", "veto-override-passage"),
    # these are for resolutions
    Rule("Offered", "introduction"),
    Rule("Adopted", "passage"),
    Rule("Received", "receipt"),
    Rule("Report adopted; Passed Second Reading", ["reading-2", "referral-committee"]),
    Rule("adopted in final form", "passage"),
    Rule("Received", "receipt"),
    Rule("committee.*recommends.*deferred", "committee-passage-unfavorable"),
    Rule("Passed Final Reading", "passage"),
    Rule("disagrees with.*amendment", "amendment-failure"),
    Rule("Carried over", "carried-over"),
    Rule("[Dd]efer", "deferral"),
)


class Categorizer(BaseCategorizer):
    rules = rules

    def categorize(self, text):
        attrs = BaseCategorizer.categorize(self, text)
        return attrs


def find_committee(action):
    ctty = None
    for rule in rules:
        pattern = rule[0][0]
        types = rule[1]
        if re.match(pattern, action):
            if "referral-committee" in types:
                ctty = re.findall(r"\w+", re.sub(pattern, "", action))
                # DELETE THIS!!
            return ctty
    # return other by default
    return ctty
