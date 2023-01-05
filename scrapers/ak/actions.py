import re

_fiscal_dept_mapping = {
    "ADM": "Administration",
    "CED": "Commerce, Community & Economic Development",
    "COR": "Corrections",
    "CRT": "Court System",
    "EED": "Education and Early Development",
    "DEC": "Environmental Conservation ",
    "DFG": "Fish and Game",
    "GOV": "Governor's Office",
    "DHS": "Health and Social Services",
    "LWF": "Labor and Workforce Development",
    "LAW": "Law",
    "LEG": "Legislative Agency",
    "MVA": "Military and Veterans' Affairs",
    "DNR": "Natural Resources",
    "DPS": "Public Safety",
    "REV": "Revenue",
    "DOT": "Transportation and Public Facilities",
    "UA": "University of Alaska",
    "ALL": "All Departments",
}

_comm_vote_type = {
    "DP": "Do Pass",
    "DNP": "Do Not Pass",
    "NR": "No Recommendation",
    "AM": "Amend",
}

_comm_mapping = {
    "AET": "Arctic Policy, Economic Development, & Tourism",
    "CRA": "Community & Regional Affairs",
    "EDC": "Education",
    "FIN": "Finance",
    "HSS": "Health & Social Services",
    "JUD": "Judiciary",
    "L&C": "Labor & Commerce",
    "RES": "Resources",
    "RLS": "Rules",
    "STA": "State Affairs",
    "TRA": "Transportation",
    "EDT": "Economic Development, Trade & Tourism",
    "NRG": "Energy",
    "FSH": "Fisheries",
    "MLV": "Military & Veterans",
    "WTR": "World Trade",
    "ARR": "Administrative Regulation Review",
    "ASC": "Armed Services Committee",
    "BUD": "Legislative Budget & Audit",
    "ECR": "Higher Education/Career Readiness Task Force",
    "EFF": "Education Fuding District Cost Factor Committee",
    "ETH": "Select Committee on Legislative Ethics",
    "LEC": "Legislative Council",
    "ARC": "Special Committee on the Arctic",
    "EDA": "Economic Development, Trade, Tourism & Arctic Policy",
    "ENE": "Energy",
}

# Dictionary matching bill action phrases to classifications. Classifications can be found here:
# https://github.com/openstates/openstates-core/blob/5b16776b1882da925e8e8d5c0a07160a7d649c69/openstates/data/common.py#L87

_actions = {
    "read the first time": {"type": "compare", "mappings": ["reading-1"]},
    "read the second time": {"type": "compare", "mappings": ["reading-2"]},
    "read the third time": {"type": "compare", "mappings": ["reading-3"]},
    "in third": {"type": "compare", "mappings": ["reading-3"]},
    "advanced to third reading": {"type": "compare", "mappings": ["reading-3"]},
    "transmitted to governor": {"type": "compare", "mappings": ["executive-receipt"]},
    "signed into law": {"type": "compare", "mappings": ["executive-signature"]},
    "approved by the governor": {
        "type": "compare",
        "mappings": ["executive-signature"],
    },
    "veto": {"type": "compare", "mappings": ["executive-veto"]},
    "do pass": {"type": "compare", "mappings": ["committee-passage"]},
    "do not pass": {"type": "compare", "mappings": ["committee-failure"]},
    "(s) transmitted to (h)": {"type": "compare", "mappings": ["passage"]},
    "(h) transmitted to (s)": {"type": "compare", "mappings": ["passage"]},
    "passed": {"type": "compare", "mappings": ["passage"]},
    "referred to": {"type": "compare", "mappings": ["referral-committee"]},
    "prefile released": {"type": "compare", "mappings": ["filing"]},
    "law w/o gov": {"type": "compare", "mappings": ["became-law"]},
    "effective date(s) of law": {"type": "compare", "mappings": ["became-law"]},
}

_comm_re = re.compile(r"^(%s)\s" % "|".join(_comm_mapping.keys()))
_current_comm = None


def clean_action(action):
    # Clean up some acronyms
    match = re.match(r"^FN(\d+): (ZERO|INDETERMINATE)?\((\w+)\)", action)
    if match:
        num = match.group(1)

        if match.group(2) == "ZERO":
            impact = "No fiscal impact"
        elif match.group(2) == "INDETERMINATE":
            impact = "Indeterminate fiscal impact"
        else:
            impact = ""

        dept = match.group(3)
        dept = _fiscal_dept_mapping.get(dept, dept)

        action = "Fiscal Note {num}: {impact} ({dept})".format(
            num=num, impact=impact, dept=dept
        )

    match = _comm_re.match(action)
    if match:
        _current_comm = match.group(1)

    match = re.match(r"^(DP|DNP|NR|AM):\s(.*)$", action)
    if match:
        vtype = _comm_vote_type[match.group(1)]

        action = f"{_current_comm} {vtype}: {match.group(2)}"

    match = re.match(r"^COSPONSOR\(S\): (.*)$", action)
    if match:
        action = f"Cosponsors added: {match.group(1)}"

    match = re.match("^([A-Z]{3,3}), ([A-Z]{3,3})$", action)
    if match:
        action = f"REFERRED TO {_comm_mapping[match.group(1)]} and"
        "{_comm_mapping[match.group(2)]}"

    match = re.match("^([A-Z]{3,3})$", action)
    if match:
        action = f"REFERRED TO {_comm_mapping[action]}"

    match = re.match("^REFERRED TO (.*)$", action)
    if match:
        comms = match.group(1).title().replace(" And ", " and ")
        action = f"REFERRED TO {comms}"

    action = re.sub(r"\s+", " ", action)

    action = action.replace("PREFILE RELEASED", "Prefile released")

    atype = []
    for action_key, data in _actions.items():

        # If regex is required to isolate bill action phrase
        if data["type"] == "regex":
            if re.search(action_key, action.lower()):
                atype.extend(a for a in data["mappings"])

        # Otherwise, we use basic string comparison
        else:
            # If we can detect a phrase that there is an OS action classification for
            if action_key in action.lower():
                atype.extend(a for a in data["mappings"])

                # Some cleaning that was done in the original code
                if "TRANSMITTED TO GOVERNOR" in action:
                    action = action.replace(
                        "TRANSMITTED TO GOVERNOR", "Transmitted to Governor"
                    )

                if "SIGNED INTO LAW" in action:
                    action = action.replace("SIGNED INTO LAW", "Signed into law")

    # These classifications are being done separately because they require more rules for
    # an accurate classification
    if "failed" in action.lower() and "am no" not in action.lower():
        atype.append("failure")

    elif "failed" in action.lower() and "am no" in action.lower():
        atype.append("amendment-failure")

    elif "adopted" in action.lower() and "am no" in action.lower():
        atype.append("amendment-passage")

    return action, atype
