from utils.actions import Rule, BaseCategorizer


# These are regex patterns that map to action categories.
_categorizer_rules = (
    Rule(
        (
            r"\(Ayes (?P<yes_votes>\d+)\.\s+Noes\s+"
            r"(?P<no_votes>\d+)\.( Page \S+\.)?\)"
        )
    ),
    Rule(r"^Introduced", "introduction"),
    Rule(r"(?i)Referred to (?P<committees>.+)", "referral-committee"),
    Rule(r"(?i)Referred to (?P<committees>.+?)(\.\s+suspense)", "referral-committee"),
    Rule(r"re-refer to Standing (?P<committees>[^.]+)\.", "referral-committee"),
    Rule(r"Read first time\.", "reading-1"),
    Rule(r"Read second time and amended", ["reading-2"]),
    Rule(r"Read third time", "reading-3"),
    Rule(r"Read third time. Refused passage\.", "failure"),
    Rule(
        [r"(?i)read third time.{,5}passed", r"(?i)Read third time.+?Passed"],
        ["passage", "reading-3"],
    ),
    Rule(r"Approved by the Governor", "executive-signature"),
    Rule(r"Approved by the Governor with item veto", "executive-veto-line-item"),
    Rule(r"Chaptered by Secretary of State", "became-law"),
    Rule("Vetoed by Governor", "executive-veto"),
    Rule("Vetoed by the Governor", "executive-veto"),
    Rule(r"To Governor", "executive-receipt"),
    Rule(r"amendments concurred in", "amendment-passage"),
    Rule(r"refused to concur in Assembly amendments", "amendment-failure"),
    Rule(r"Failed passage in committee", "committee-failure"),
    Rule(
        r"From committee: Filed with the Chief Clerk pursuant to Joint Rule 56.",
        "failure",
    ),
    Rule(
        r"(?i)From committee: ((?!Without further action))((?!Filed with the Chief Clerk pursuant to Joint Rule 56))",
        "committee-passage",
    ),
    Rule(r"(?i)From committee: Do pass", "committee-passage-favorable"),
    Rule(r"From committee with author\'s amendments", "committee-passage"),
    # Resolutions
    Rule(r"Adopted", "passage"),
    Rule(r"Read", "reading-1"),
    Rule(r"^From committee: Be adopted", "committee-passage-favorable"),
    # New actions added per issue 2755
    Rule(r"Amend,", "amendment-introduction"),
    Rule(r"Adopted.", "amendment-passage"),
    Rule(r"amended", "amendment-passage"),
    Rule(r"died", "failure"),
    Rule(r"Refused adoption.", "failure"),
    Rule(r"refused passage", "failure"),
    Rule(r"returned to Secretary", "failure"),
    Rule(r"without further action", "failure"),
    Rule(r"Introduced.", "introduction"),
    Rule(r"adopted Conference Committee", "committee-passage"),
    Rule(r"adopts Conference Committee", "committee-passage"),
    Rule(r"to Engrossing and Enrolling", "committee-passage"),
    Rule(r"Read first time", "reading-1"),
    Rule(r"Read second time", "reading-2"),
    Rule(r"Read third time", "reading-3"),
    Rule(r"veto stricken from file", "veto-override-failure"),
    Rule(r"failed passage", "committee-passage-unfavorable"),
    Rule(r"refused to concur", "committee-failure"),
    Rule(r"from committee with ", "committee-passage"),
    Rule(r"from committee:", "committee-passage"),
    Rule(r"from committee chair", "committee-passage"),
    Rule(r"from conference committee:", "committee-passage"),
    Rule(r"amendments concurred in", "committee-passage-favorable"),
    Rule(r"from committee without", "committee-passage-unfavorable"),
    Rule(r"to com.", "referral-committee"),
    Rule(r"to coms.", "referral-committee"),
    Rule(r"Ordered to Conference Committee", "referral-committee"),
    Rule(r"enrolled", "executive-receipt"),
    Rule(r"approved by the Governor.", "executive-signature"),
    Rule(r"vetoed", "executive-veto"),
    Rule(r"with item veto", "executive-veto-line-item"),
    Rule(r"returned by the Governor", "withdrawal"),
    Rule(r"withdrawn from committee", "withdrawal"),
    Rule(r"ordered to third reading", "reading-3"),
    Rule(r"ordered to second reading", "reading-2"),
    Rule(r"^Died pursuant to", "failure"),
)


class CACategorizer(BaseCategorizer):
    rules = _categorizer_rules
