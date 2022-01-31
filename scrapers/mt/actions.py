import re


# ----------------------------------------------------------------------------
# Data for action categorization.

_categories = {
    # Bill is introduced or prefiled
    "introduction": {"rgxs": ["^Introduced$"], "funcs": {}},
    # Bill has passed a chamber
    "passage": {
        "rgxs": [
            "3rd Reading Passed",
            "^Resolution Adopted",
            "3rd Reading Concurred",
            "3rd Reading Passed as Amended by Senate",
            "3rd Reading Passed as Amended by House",
        ]
    },
    # Bill has failed to pass a chamber
    "failure": {"rgxs": ["3rd Reading Failed", "Died in Process"], "funcs": {}},
    # Bill has been withdrawn from consideration
    "withdrawal": {"rgxs": [], "funcs": {}},
    # ???
    # The chamber attempted a veto override and succeeded
    "veto-override-passage": {"rgxs": ["Veto Overridden in House"]},
    # ???
    # The chamber attempted a veto override and failed
    "veto-override-failure": {
        "rgxs": ["Veto Override Motion Failed", "Veto Override Failed"]
    },
    # Became law, potentially without governor signature
    "became-law": {"rgxs": ["Chapter Number Assigned"]},
    # ???
    # A bill has undergone its first reading
    "reading-1": {"rgxs": ["First Reading"], "funcs": {}},
    # A bill has undergone its second reading
    "reading-2": {
        "rgxs": [
            "Taken from Committee; Placed on 2nd Reading",
            "2nd Reading Passed",
            "2nd Reading Conference Committee Report Adopted",
            "2nd Reading Senate Amendments Concurred",
            "2nd Reading Pass Motion Failed; 3rd Reading Vote Required",
            "2nd Reading Not Passed as Amended",
            "2nd Reading House Amendments Concurred",
            "2nd Reading Concurred",
            "Reconsidered Previous Action; Placed on 2nd Reading",
            "2nd Reading Indefinitely Postponed",
            "Taken from 3rd Reading; Placed on 2nd Reading",
            "2nd Reading Concur Motion Failed",
            "2nd Reading Not Concurred; 3rd Reading Vote Required",
            "Reconsidered Previous Act; Remains in 2nd Reading FCC Process",
            "2nd Reading Indefinitely Postpone Motion Failed",
            "2nd Reading Pass Motion Failed",
            "2nd Reading Not Concurred",
            "2nd Reading Not Passed",
        ]
    },
    # A bill has undergone its third (or final) reading
    "reading-3": {
        "rgxs": [
            "3rd Reading Passed as Amended by Senate",
            "3rd Reading Passed as Amended by House",
            "3rd Reading Pass Consideration",
            "3rd Reading Concurred",
            "3rd Reading Passed",
            "3rd Reading Not Passed as Amended by Senate",
            "Reconsidered Previous Action; Remains in 3rd Reading Process",
            "3rd Reading Conference Committee Report Adopted",
            "3rd Reading Failed",
        ]
    },
    # A bill has been filed (for states where this is a separate event from
    # introduction)
    "filing": {"rgxs": [], "funcs": {}},
    # A bill has been replaced with a substituted wholesale (called hoghousing
    # in some states)
    "substitution": {"rgxs": [], "funcs": {}},
    # The bill has been transmitted to the governor for consideration
    "executive-receipt": {"rgxs": ["Transmitted to Governor"], "funcs": {}},
    # The bill has signed into law by the governor
    "executive-signature": {"rgxs": ["Signed by Governor"], "funcs": {}},
    # The bill has been vetoed by the governor
    "executive-veto": {"rgxs": ["Vetoed by Governor"], "funcs": {}},
    # The governor has issued a line-item (partial) veto
    "executive-veto-line-item": {"rgxs": ["Returned with Governor's Line-item Veto"]},
    # An amendment has been offered on the bill
    "amendment-introduction": {"rgxs": ["^(?i)amendment.{,200}introduced"]},
    # The bill has been amended
    "amendment-passage": {
        "rgxs": [
            "3rd Reading Governor's Proposed Amendments Adopted",
            "2nd Reading Governor's Proposed Amendments Adopted",
            "2nd Reading House Amendments Concurred",
            "2nd Reading Senate Amendments Concurred",
        ]
    },
    # An offered amendment has failed
    "amendment-failure": {
        "rgxs": [
            "2nd Reading House Amendments Not Concur Motion Failed",
            "2nd Reading Senate Amendments Concur Motion Failed",
            "2nd Reading House Amendments Concur Motion Failed",
            "2nd Reading Governor's Proposed Amendments Not Adopted",
            "3rd Reading Governor's Proposed Amendments Not Adopted",
            "2nd Reading Governor's Proposed Amendments Adopt Motion Failed",
            "2nd Reading Motion to Amend Failed",
            "2nd Reading House Amendments Not Concurred",
        ]
    },
    # An offered amendment has been amended (seen in Texas)
    "amendment-amendment": {
        "rgxs": [
            "3rd Reading Governor's Proposed Amendments Adopted",
            "2nd Reading Governor's Proposed Amendments Adopted",
            "2nd Reading House Amendments Concurred",
            "2nd Reading Senate Amendments Concurred",
        ]
    },
    # ???
    # An offered amendment has been withdrawn
    "amendment-withdrawal": {"rgxs": []},
    # An amendment has been 'laid on the table' (generally
    # preventing further consideration)
    # TODO: restore this once py-ocd-django has this classification
    "amendment-deferral": {"rgxs": ["Tabled in Committee"]},
    # The bill has been referred to a committee
    "referral-committee": {
        "rgxs": ["Referred to Committee", "Rereferred to Committee"]
    },
    # The bill has been passed out of a committee
    "committee-passage": {
        "rgxs": [
            r"Committee Executive Action--Bill Passed",
            r"Committee Report--Bill Passed",
            r"Committee Executive Action--Resolution Adopted",
        ]
    },
    # ??? Looks like this'd require parsing
    # The bill has been passed out of a committee with a favorable report
    "committee-passage-favorable": {"rgxs": []},
    # ??? Looks like this'd require parsing
    # The bill has been passed out of a committee with an unfavorable report
    "committee-passage-unfavorable": {"rgxs": []},
    # The bill has failed to make it out of committee
    "committee-failure": {
        "rgxs": [
            r"Committee Executive Action--Resolution Not Adopted",
            r"Committee Executive Action--Bill Not Passed",
            r"Died in Standing Committee",
        ]
    },
    # All other actions will have a type of "other"
}

_funcs = []
append = _funcs.append
for category, data in _categories.items():

    for rgx in data["rgxs"]:
        append((category, re.compile(rgx).search))

ac = set(
    [
        "2nd Reading Concur Motion Failed",
        "2nd Reading Concur as Amended Motion Failed",
        "2nd Reading Concurred",
        "2nd Reading Concurred as Amended",
        "2nd Reading Conference Committee Report Adopt Motion Failed",
        "2nd Reading Conference Committee Report Adopted",
        "2nd Reading Free Conference Committee Report Adopt Motion Failed",
        "2nd Reading Free Conference Committee Report Adopted",
        "2nd Reading Free Conference Committee Report Rejected",
        "2nd Reading Governor's Proposed Amendments Adopt Motion Failed",
        "2nd Reading Governor's Proposed Amendments Adopted",
        "2nd Reading Governor's Proposed Amendments Not Adopted",
        "2nd Reading House Amendments Concur Motion Failed",
        "2nd Reading House Amendments Concurred",
        "2nd Reading House Amendments Not Concur Motion Failed",
        "2nd Reading House Amendments Not Concurred",
        "2nd Reading Indefinitely Postpone Motion Failed",
        "2nd Reading Indefinitely Postponed",
        "2nd Reading Motion to Amend Carried",
        "2nd Reading Motion to Amend Failed",
        "2nd Reading Not Concurred",
        "2nd Reading Not Concurred; 3rd Reading Vote Required",
        "2nd Reading Not Passed",
        "2nd Reading Not Passed as Amended",
        "2nd Reading Pass Consideration",
        "2nd Reading Pass Motion Failed",
        "2nd Reading Pass Motion Failed; 3rd Reading Vote Required",
        "2nd Reading Pass as Amended Motion Failed",
        "2nd Reading Passed",
        "2nd Reading Passed Consideration",
        "2nd Reading Passed as Amended",
        "2nd Reading Senate Amendments Concur Motion Failed",
        "2nd Reading Senate Amendments Concurred",
        "2nd Reading Senate Amendments Not Concurred",
        "3rd Reading Concurred",
        "3rd Reading Conference Committee Report Adopted",
        "3rd Reading Failed",
        "3rd Reading Free Conference Committee Report Adopted",
        "3rd Reading Governor's Proposed Amendments Adopted",
        "3rd Reading Governor's Proposed Amendments Not Adopted",
        "3rd Reading Not Passed as Amended by Senate",
        "3rd Reading Pass Consideration",
        "3rd Reading Passed",
        "3rd Reading Passed as Amended by House",
        "3rd Reading Passed as Amended by Senate",
        "Adverse Committee Report Rejected",
        "Bill Draft Text Available Electronically",
        "Bill Not Heard at Sponsor's Request",
        "Chapter Number Assigned",
        "Clerical Corrections Made - New Version Available",
        "Committee Executive Action--Bill Concurred",
        "Committee Executive Action--Bill Concurred as Amended",
        "Committee Executive Action--Bill Not Passed as Amended",
        "Committee Executive Action--Bill Passed",
        "Committee Executive Action--Bill Passed as Amended",
        "Committee Executive Action--Resolution Adopted",
        "Committee Executive Action--Resolution Adopted as Amended",
        "Committee Executive Action--Resolution Not Adopted",
        "Committee Report--Bill Concurred",
        "Committee Report--Bill Concurred as Amended",
        "Committee Report--Bill Passed",
        "Committee Report--Bill Passed as Amended",
        "Committee Report--Resolution Adopted",
        "Committee Report--Resolution Adopted as Amended",
        "Committee Report--Resolution Not Adopted",
        "Committee Vote Failed; Remains in Committee",
        "Conference Committee Appointed",
        "Conference Committee Dissolved",
        "Conference Committee Report Received",
        "Died in Process",
        "Died in Standing Committee",
        "Draft Back for Redo",
        "Draft Back for Requester Changes",
        "Draft Back for Technical Correction",
        "Draft Canceled",
        "Draft Delivered to Requester",
        "Draft On Hold",
        "Draft Ready for Delivery",
        "Draft Request Received",
        "Draft Taken Off Hold",
        "Draft Taken by Drafter",
        "Draft in Assembly/Executive Director Review",
        "Draft in Edit",
        "Draft in Final Drafter Review",
        "Draft in Input/Proofing",
        "Draft in Legal Review",
        "Draft to Drafter - Edit Review [CMD]",
        "Draft to Drafter - Edit Review [JLN]",
        "Draft to Drafter - Edit Review [SAB]",
        "Draft to Requester for Review",
        "Filed with Secretary of State",
        "First Reading",
        "Fiscal Note Printed",
        "Fiscal Note Probable",
        "Fiscal Note Received",
        "Fiscal Note Requested",
        "Fiscal Note Requested (Local Government Fiscal Impact)",
        "Fiscal Note Signed",
        "Free Conference Committee Appointed",
        "Free Conference Committee Dissolved",
        "Free Conference Committee Report Received",
        "Hearing",
        "Hearing Canceled",
        "Introduced",
        "Introduced Bill Text Available Electronically",
        "Line-item Veto Override Failed",
        "Missed Deadline for Appropriation Bill Transmittal",
        "Missed Deadline for General Bill Transmittal",
        "Missed Deadline for Interim Study Resolution Transmittal",
        "Missed Deadline for Referendum Proposal Transmittal",
        "Missed Deadline for Revenue Bill Transmittal",
        "Motion Carried",
        "Motion Failed",
        "On Motion Rules Suspended",
        "Placed on Consent Calendar",
        "Pre-Introduction Letter Sent",
        "Printed - Enrolled Version Available",
        "Printed - New Version Available",
        "Reconsidered Previous Act; Remains in 2nd Read Process to Consider (H) Amend",
        "Reconsidered Previous Act; Remains in 2nd Read Process to Consider (S) Amend",
        "Reconsidered Previous Act; Remains in 2nd Reading FCC Process",
        "Reconsidered Previous Act; Remains in 3rd Read Gov Amend Process",
        "Reconsidered Previous Action; Placed on 2nd Reading",
        "Reconsidered Previous Action; Remains in 2nd Reading Process",
        "Reconsidered Previous Action; Remains in 3rd Reading Process",
        "Referred to Committee",
        "Rereferred to Committee",
        "Resolution Adopted",
        "Resolution Failed",
        "Returned from Enrolling",
        "Returned to House",
        "Returned to House Concurred in Governor's Proposed Amendments",
        "Returned to House Not Concurred in Governor's Proposed Amendments",
        "Returned to House with Amendments",
        "Returned to Senate",
        "Returned to Senate Concurred in Governor's Proposed Amendments",
        "Returned to Senate Not Concurred in Governor's Proposed Amendments",
        "Returned to Senate with Amendments",
        "Returned with Governor's Line-item Veto",
        "Returned with Governor's Proposed Amendments",
        "Revised Fiscal Note Printed",
        "Revised Fiscal Note Received",
        "Revised Fiscal Note Requested",
        "Revised Fiscal Note Signed",
        "Rules Suspended to Accept Late Return of Amended Bill",
        "Rules Suspended to Accept Late Transmittal of Bill",
        "Scheduled for 2nd Reading",
        "Scheduled for 3rd Reading",
        "Scheduled for Consideration under Special Orders",
        "Scheduled for Executive Action",
        "Segregated from Committee of the Whole Report",
        "Sent to Enrolling",
        "Signed by Governor",
        "Signed by President",
        "Signed by Speaker",
        "Special Note",
        "Sponsor List Modified",
        "Sponsor Rebuttal to Fiscal Note Printed",
        "Sponsor Rebuttal to Fiscal Note Received",
        "Sponsor Rebuttal to Fiscal Note Requested",
        "Sponsor Rebuttal to Fiscal Note Signed",
        "Sponsors Engrossed",
        "Tabled in Committee",
        "Taken from 2nd Reading; Rereferred to Committee",
        "Taken from 3rd Reading; Placed on 2nd Reading",
        "Taken from Committee; Placed on 2nd Reading",
        "Taken from Table in Committee",
        "Transmitted to Governor",
        "Transmitted to House",
        "Transmitted to House for Consideration of Governor's Proposed Amendments",
        "Transmitted to Senate",
        "Transmitted to Senate for Consideration of Governor's Proposed Amendments",
        "Veto Overridden in House",
        "Veto Override Failed in Legislature",
        "Veto Override Motion Failed in House",
        "Veto Override Motion Failed in Senate",
        "Veto Override Vote Mail Poll Letter Being Prepared",
        "Veto Override Vote Mail Poll in Progress",
        "Vetoed by Governor",
    ]
)


def categorize(action, funcs=_funcs):
    action = action.strip('" ')
    res = set()
    for category, f in funcs:
        if f(action):
            res.add(category)

    if not res:
        return None

    return tuple(res)
