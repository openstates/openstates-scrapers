import re


# ----------------------------------------------------------------------------
# Data for action categorization.

_categories = {
    # Bill is introduced or prefiled
    "introduction": {"rgxs": ["^Introduced$"], "funcs": {}},
    # Bill has passed a chamber
    "passage": {
        "rgxs": [
            u"3rd Reading Passed",
            u"^Resolution Adopted",
            u"3rd Reading Concurred",
            u"3rd Reading Passed as Amended by Senate",
            u"3rd Reading Passed as Amended by House",
        ]
    },
    # Bill has failed to pass a chamber
    "failure": {"rgxs": [u"3rd Reading Failed", u"Died in Process"], "funcs": {}},
    # Bill has been withdrawn from consideration
    "withdrawal": {"rgxs": [], "funcs": {}},
    # ???
    # The chamber attempted a veto override and succeeded
    "veto-override-passage": {"rgxs": [u"Veto Overridden in House"]},
    # ???
    # The chamber attempted a veto override and failed
    "veto-override-failure": {
        "rgxs": [u"Veto Override Motion Failed", u"Veto Override Failed"]
    },
    # ???
    # A bill has undergone its first reading
    "reading-1": {"rgxs": ["First Reading"], "funcs": {}},
    # A bill has undergone its second reading
    "reading-2": {
        "rgxs": [
            u"Taken from Committee; Placed on 2nd Reading",
            u"2nd Reading Passed",
            u"2nd Reading Conference Committee Report Adopted",
            u"2nd Reading Senate Amendments Concurred",
            u"2nd Reading Pass Motion Failed; 3rd Reading Vote Required",
            u"2nd Reading Not Passed as Amended",
            u"2nd Reading House Amendments Concurred",
            u"2nd Reading Concurred",
            u"Reconsidered Previous Action; Placed on 2nd Reading",
            u"2nd Reading Indefinitely Postponed",
            u"Taken from 3rd Reading; Placed on 2nd Reading",
            u"2nd Reading Concur Motion Failed",
            u"2nd Reading Not Concurred; 3rd Reading Vote Required",
            u"Reconsidered Previous Act; Remains in 2nd Reading FCC Process",
            u"2nd Reading Indefinitely Postpone Motion Failed",
            u"2nd Reading Pass Motion Failed",
            u"2nd Reading Not Concurred",
            u"2nd Reading Not Passed",
        ]
    },
    # A bill has undergone its third (or final) reading
    "reading-3": {
        "rgxs": [
            u"3rd Reading Passed as Amended by Senate",
            u"3rd Reading Passed as Amended by House",
            u"3rd Reading Pass Consideration",
            u"3rd Reading Concurred",
            u"3rd Reading Passed",
            u"3rd Reading Not Passed as Amended by Senate",
            u"Reconsidered Previous Action; Remains in 3rd Reading Process",
            u"3rd Reading Conference Committee Report Adopted",
            u"3rd Reading Failed",
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
    "executive-veto-line-item": {"rgxs": [u"Returned with Governor's Line-item Veto"]},
    # An amendment has been offered on the bill
    "amendment-introduction": {"rgxs": ["^(?i)amendment.{,200}introduced"]},
    # The bill has been amended
    "amendment-passage": {
        "rgxs": [
            u"3rd Reading Governor's Proposed Amendments Adopted",
            u"2nd Reading Governor's Proposed Amendments Adopted",
            u"2nd Reading House Amendments Concurred",
            u"2nd Reading Senate Amendments Concurred",
        ]
    },
    # An offered amendment has failed
    "amendment-failure": {
        "rgxs": [
            u"2nd Reading House Amendments Not Concur Motion Failed",
            u"2nd Reading Senate Amendments Concur Motion Failed",
            u"2nd Reading House Amendments Concur Motion Failed",
            u"2nd Reading Governor's Proposed Amendments Not Adopted",
            u"3rd Reading Governor's Proposed Amendments Not Adopted",
            u"2nd Reading Governor's Proposed Amendments Adopt Motion Failed",
            u"2nd Reading Motion to Amend Failed",
            u"2nd Reading House Amendments Not Concurred",
        ]
    },
    # An offered amendment has been amended (seen in Texas)
    "amendment-amendment": {
        "rgxs": [
            u"3rd Reading Governor's Proposed Amendments Adopted",
            u"2nd Reading Governor's Proposed Amendments Adopted",
            u"2nd Reading House Amendments Concurred",
            u"2nd Reading Senate Amendments Concurred",
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
        u"2nd Reading Concur Motion Failed",
        u"2nd Reading Concur as Amended Motion Failed",
        u"2nd Reading Concurred",
        u"2nd Reading Concurred as Amended",
        u"2nd Reading Conference Committee Report Adopt Motion Failed",
        u"2nd Reading Conference Committee Report Adopted",
        u"2nd Reading Free Conference Committee Report Adopt Motion Failed",
        u"2nd Reading Free Conference Committee Report Adopted",
        u"2nd Reading Free Conference Committee Report Rejected",
        u"2nd Reading Governor's Proposed Amendments Adopt Motion Failed",
        u"2nd Reading Governor's Proposed Amendments Adopted",
        u"2nd Reading Governor's Proposed Amendments Not Adopted",
        u"2nd Reading House Amendments Concur Motion Failed",
        u"2nd Reading House Amendments Concurred",
        u"2nd Reading House Amendments Not Concur Motion Failed",
        u"2nd Reading House Amendments Not Concurred",
        u"2nd Reading Indefinitely Postpone Motion Failed",
        u"2nd Reading Indefinitely Postponed",
        u"2nd Reading Motion to Amend Carried",
        u"2nd Reading Motion to Amend Failed",
        u"2nd Reading Not Concurred",
        u"2nd Reading Not Concurred; 3rd Reading Vote Required",
        u"2nd Reading Not Passed",
        u"2nd Reading Not Passed as Amended",
        u"2nd Reading Pass Consideration",
        u"2nd Reading Pass Motion Failed",
        u"2nd Reading Pass Motion Failed; 3rd Reading Vote Required",
        u"2nd Reading Pass as Amended Motion Failed",
        u"2nd Reading Passed",
        u"2nd Reading Passed Consideration",
        u"2nd Reading Passed as Amended",
        u"2nd Reading Senate Amendments Concur Motion Failed",
        u"2nd Reading Senate Amendments Concurred",
        u"2nd Reading Senate Amendments Not Concurred",
        u"3rd Reading Concurred",
        u"3rd Reading Conference Committee Report Adopted",
        u"3rd Reading Failed",
        u"3rd Reading Free Conference Committee Report Adopted",
        u"3rd Reading Governor's Proposed Amendments Adopted",
        u"3rd Reading Governor's Proposed Amendments Not Adopted",
        u"3rd Reading Not Passed as Amended by Senate",
        u"3rd Reading Pass Consideration",
        u"3rd Reading Passed",
        u"3rd Reading Passed as Amended by House",
        u"3rd Reading Passed as Amended by Senate",
        u"Adverse Committee Report Rejected",
        u"Bill Draft Text Available Electronically",
        u"Bill Not Heard at Sponsor's Request",
        u"Chapter Number Assigned",
        u"Clerical Corrections Made - New Version Available",
        u"Committee Executive Action--Bill Concurred",
        u"Committee Executive Action--Bill Concurred as Amended",
        u"Committee Executive Action--Bill Not Passed as Amended",
        u"Committee Executive Action--Bill Passed",
        u"Committee Executive Action--Bill Passed as Amended",
        u"Committee Executive Action--Resolution Adopted",
        u"Committee Executive Action--Resolution Adopted as Amended",
        u"Committee Executive Action--Resolution Not Adopted",
        u"Committee Report--Bill Concurred",
        u"Committee Report--Bill Concurred as Amended",
        u"Committee Report--Bill Passed",
        u"Committee Report--Bill Passed as Amended",
        u"Committee Report--Resolution Adopted",
        u"Committee Report--Resolution Adopted as Amended",
        u"Committee Report--Resolution Not Adopted",
        u"Committee Vote Failed; Remains in Committee",
        u"Conference Committee Appointed",
        u"Conference Committee Dissolved",
        u"Conference Committee Report Received",
        u"Died in Process",
        u"Died in Standing Committee",
        u"Draft Back for Redo",
        u"Draft Back for Requester Changes",
        u"Draft Back for Technical Correction",
        u"Draft Canceled",
        u"Draft Delivered to Requester",
        u"Draft On Hold",
        u"Draft Ready for Delivery",
        u"Draft Request Received",
        u"Draft Taken Off Hold",
        u"Draft Taken by Drafter",
        u"Draft in Assembly/Executive Director Review",
        u"Draft in Edit",
        u"Draft in Final Drafter Review",
        u"Draft in Input/Proofing",
        u"Draft in Legal Review",
        u"Draft to Drafter - Edit Review [CMD]",
        u"Draft to Drafter - Edit Review [JLN]",
        u"Draft to Drafter - Edit Review [SAB]",
        u"Draft to Requester for Review",
        u"Filed with Secretary of State",
        u"First Reading",
        u"Fiscal Note Printed",
        u"Fiscal Note Probable",
        u"Fiscal Note Received",
        u"Fiscal Note Requested",
        u"Fiscal Note Requested (Local Government Fiscal Impact)",
        u"Fiscal Note Signed",
        u"Free Conference Committee Appointed",
        u"Free Conference Committee Dissolved",
        u"Free Conference Committee Report Received",
        u"Hearing",
        u"Hearing Canceled",
        u"Introduced",
        u"Introduced Bill Text Available Electronically",
        u"Line-item Veto Override Failed",
        u"Missed Deadline for Appropriation Bill Transmittal",
        u"Missed Deadline for General Bill Transmittal",
        u"Missed Deadline for Interim Study Resolution Transmittal",
        u"Missed Deadline for Referendum Proposal Transmittal",
        u"Missed Deadline for Revenue Bill Transmittal",
        u"Motion Carried",
        u"Motion Failed",
        u"On Motion Rules Suspended",
        u"Placed on Consent Calendar",
        u"Pre-Introduction Letter Sent",
        u"Printed - Enrolled Version Available",
        u"Printed - New Version Available",
        u"Reconsidered Previous Act; Remains in 2nd Read Process to Consider (H) Amend",
        u"Reconsidered Previous Act; Remains in 2nd Read Process to Consider (S) Amend",
        u"Reconsidered Previous Act; Remains in 2nd Reading FCC Process",
        u"Reconsidered Previous Act; Remains in 3rd Read Gov Amend Process",
        u"Reconsidered Previous Action; Placed on 2nd Reading",
        u"Reconsidered Previous Action; Remains in 2nd Reading Process",
        u"Reconsidered Previous Action; Remains in 3rd Reading Process",
        u"Referred to Committee",
        u"Rereferred to Committee",
        u"Resolution Adopted",
        u"Resolution Failed",
        u"Returned from Enrolling",
        u"Returned to House",
        u"Returned to House Concurred in Governor's Proposed Amendments",
        u"Returned to House Not Concurred in Governor's Proposed Amendments",
        u"Returned to House with Amendments",
        u"Returned to Senate",
        u"Returned to Senate Concurred in Governor's Proposed Amendments",
        u"Returned to Senate Not Concurred in Governor's Proposed Amendments",
        u"Returned to Senate with Amendments",
        u"Returned with Governor's Line-item Veto",
        u"Returned with Governor's Proposed Amendments",
        u"Revised Fiscal Note Printed",
        u"Revised Fiscal Note Received",
        u"Revised Fiscal Note Requested",
        u"Revised Fiscal Note Signed",
        u"Rules Suspended to Accept Late Return of Amended Bill",
        u"Rules Suspended to Accept Late Transmittal of Bill",
        u"Scheduled for 2nd Reading",
        u"Scheduled for 3rd Reading",
        u"Scheduled for Consideration under Special Orders",
        u"Scheduled for Executive Action",
        u"Segregated from Committee of the Whole Report",
        u"Sent to Enrolling",
        u"Signed by Governor",
        u"Signed by President",
        u"Signed by Speaker",
        u"Special Note",
        u"Sponsor List Modified",
        u"Sponsor Rebuttal to Fiscal Note Printed",
        u"Sponsor Rebuttal to Fiscal Note Received",
        u"Sponsor Rebuttal to Fiscal Note Requested",
        u"Sponsor Rebuttal to Fiscal Note Signed",
        u"Sponsors Engrossed",
        u"Tabled in Committee",
        u"Taken from 2nd Reading; Rereferred to Committee",
        u"Taken from 3rd Reading; Placed on 2nd Reading",
        u"Taken from Committee; Placed on 2nd Reading",
        u"Taken from Table in Committee",
        u"Transmitted to Governor",
        u"Transmitted to House",
        u"Transmitted to House for Consideration of Governor's Proposed Amendments",
        u"Transmitted to Senate",
        u"Transmitted to Senate for Consideration of Governor's Proposed Amendments",
        u"Veto Overridden in House",
        u"Veto Override Failed in Legislature",
        u"Veto Override Motion Failed in House",
        u"Veto Override Motion Failed in Senate",
        u"Veto Override Vote Mail Poll Letter Being Prepared",
        u"Veto Override Vote Mail Poll in Progress",
        u"Vetoed by Governor",
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
