from openstates.utils.actions import Rule, BaseCategorizer

# These are regex patterns that map to action categories.
_categorizer_rules = (
    Rule(
        ["Amendment #\\S+ \\((?P<legislator>.+?)\\) bundle YES adopted"],
        ["amendment-passage"],
    ),
    Rule(["(?i)Signed by (the )Governor(.*)"], ["executive-signature"]),
    Rule(["Accompanied (by )?(?P<bill_id>[SH]\\S+)"], []),
    Rule(["Discharged to the committee on (?P<committees>.+)"], ["referral-committee"]),
    Rule(["(?i)Amendment #\\d+ adopted"], ["amendment-passage"]),
    Rule(
        [
            "Amendment #\\d+ \\((?P<legislator>.+?)\\) rejected",
            "(?i)amendment.+?rejected",
        ],
        ["amendment-failure"],
    ),
    Rule(["(?is)Amendment \\S+ withdrawn"], ["amendment-withdrawal"]),
    Rule(
        ["Amendment #\\S+ \\((?P<legislator>.+?)\\) Pending"],
        ["amendment-introduction"],
    ),
    Rule(["(?P<bill>[HS]\\d+)"], []),
    Rule(["(?i)Amendment \\(#\\d+\\) adopted"], ["amendment-passage"]),
    Rule(["(?i)with veto"], ["executive-veto"]),
    Rule(["reported favorably by committee"], ["committee-passage-favorable"]),
    Rule(["Accompan\\S+ .+?(?P<bill_id>[SH]\\S+)"], []),
    Rule(["(?i)Amendment \\d+ pending"], ["amendment-deferral"]),
    Rule(["Read,"], ["reading-1"]),
    Rule(
        [
            "(?i)Amendment #\\S+ \\((?P<legislator>.+?)\\)\\s+-\\s+rejected",
            "(?i)Amendment \\d+ rejected",
            "Amendment #?\\S+ \\((?P<legislator>.+?)\\) rejected",
        ],
        ["amendment-failure"],
    ),
    Rule(
        [
            "Amended \\((?P<legislator>.+?)\\) ",
            "Amendment #?\\S+ \\((?P<legislator>.+?)\\) adopted",
        ],
        ["amendment-passage"],
    ),
    Rule(["(?i)read.{,10}second"], ["reading-2"]),
    Rule(
        ["Amendment #\\d+ \\((?P<legislator>.+?)\\) pending"],
        ["amendment-introduction"],
    ),
    Rule(["Enacted"], ["passage"]),
    Rule(
        [
            "Amendment #\\S+ \\((?P<legislator>.+?)\\) Adopted",
            "Accompanied a study order, (see )?(?P<bill_id>[SH]\\S+)",
        ],
        [],
    ),
    Rule(["passed over veto"], ["veto-override-passage"]),
    Rule(["(?i)Read third"], ["reading-3"]),
    Rule(["Bill Filed"], ["introduction"]),
    Rule(["(?i)Amendment #\\S+ rejected"], ["amendment-failure"]),
    Rule(["laid aside"], ["amendment-deferral"]),
    Rule(["(?i)Amendment \\(#\\d+\\) rejected"], ["amendment-failure"]),
    Rule(["(?i)amendment.+?adopted"], ["amendment-passage"]),
    Rule(["Adopted, (see )?(?P<bill_id>[SH]\\S+)"], []),
    Rule(["(?is)Amendment \\(\\d+\\) rejected"], ["amendment-failure"]),
    Rule(["(?P<yes_votes>\\d+) YEAS.+?(?P<no_votes>\\d+) NAYS"], []),
    Rule(["Passed to be engrossed"], ["passage"]),
    Rule(["Amendment #\\d+ \\((?P<legislator>.+?)\\) adopted"], ["amendment-passage"]),
    Rule(["Amendment #\\S+ \\((?P<legislator>.+?)\\) Rejected"], ["amendment-failure"]),
    Rule(["referred to (?P<committees>.+)"], ["referral-committee"]),
    Rule(["Amended by"], ["amendment-passage"]),
    Rule(["Committee recommended ought to pass"], ["committee-passage-favorable"]),
    Rule(
        ["Amendment #\\S+ \\((?P<legislator>.+?)\\) bundle NO rejected"],
        ["amendment-failure"],
    ),
    Rule(["(?is)Amendment \\(\\d+\\) adopted"], ["amendment-passage"]),
    Rule(
        ["(?i)(Referred|Recommittedra) to (?P<committees>committee on.+)"],
        ["referral-committee"],
    ),
    Rule(["Accompanied a new draft, (see )?(?P<bill_id>[SH]\\S+)"], []),
    Rule(
        ["(?i)Amendment #\\S+ \\((?P<legislator>.+?)\\) bundle NO rejected"],
        ["amendment-failure"],
    ),
    Rule(
        [
            "(?i)(Referred|Recommittedra) to (?P<chamber>\\S+) (?P<committees>committee on.+)"
        ],
        ["referral-committee"],
    ),
    Rule(["Committee recommended ought NOT"], ["committee-passage-unfavorable"]),
    Rule(
        [
            "(?i)(Referred|Recommittedra) (to|from)( the)? (?P<chamber>\\S+) "
            "(?P<committees>committee on.+)"
        ],
        ["referral-committee"],
    ),
    Rule(["(?i)Amendment #\\d+ rejected"], ["amendment-failure"]),
    Rule(["(?i)Amendment \\d+ adopted"], ["amendment-passage"]),
    Rule(["Committee of Conference appointed \\((?P<legislator>.+?)\\)"], []),
)


class Categorizer(BaseCategorizer):
    rules = _categorizer_rules
