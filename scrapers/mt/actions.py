import re


# ----------------------------------------------------------------------------
# Dictionary matching bill action phrases to classifications. Classifications can be found here:
# https://github.com/openstates/openstates-core/blob/5b16776b1882da925e8e8d5c0a07160a7d649c69/openstates/data/common.py#L87
# The "type" denotes whether regex or a simple string comparison should be used in categorize_action()
_actions = {
    # Bill is introduced or prefiled
    "^introduced$": {"type": "regex", "mappings": ["introduction"]},
    # Bill has passed a chamber, a bill has undergone its third (or final) reading
    "3rd reading passed": {"type": "compare", "mappings": ["passage", "reading-3"]},
    "^resolution adopted": {"type": "regex", "mappings": ["passage"]},
    "3rd reading concurred": {"type": "compare", "mappings": ["passage", "reading-3"]},
    "3rd reading passed as amended by senate": {
        "type": "compare",
        "mappings": ["passage", "reading-3"],
    },
    "3rd reading passed as amended by house": {
        "type": "compare",
        "mappings": ["passage", "reading-3"],
    },
    # Bill has failed to pass a chamber
    "3rd reading failed": {"type": "compare", "mappings": ["failure", "reading-3"]},
    "died in process": {"type": "compare", "mappings": ["failure"]},
    # The chamber attempted a veto override and succeeded
    "veto overridden in house": {
        "type": "compare",
        "mappings": ["veto-override-passage"],
    },
    # The chamber attempted a veto override and failed
    "veto override motion failed": {
        "type": "compare",
        "mappings": ["veto-override-failure"],
    },
    "veto override failed": {"type": "compare", "mappings": ["veto-override-failure"]},
    # Became law, potentially without governor signature
    "chapter number assigned": {"type": "compare", "mappings": ["became-law"]},
    # A bill has undergone its first reading
    "first reading": {"type": "compare", "mappings": ["reading-1"]},
    # A bill has undergone its second reading, the bill has been amended,
    # an offered amendment has been amended (seen in Texas)
    "taken from committee; placed on 2nd reading": {
        "type": "compare",
        "mappings": ["reading-2"],
    },
    "2nd reading passed": {"type": "compare", "mappings": ["reading-2"]},
    "2nd reading conference committee report adopted": {
        "type": "compare",
        "mappings": ["reading-2"],
    },
    "2nd reading senate amendments concurred": {
        "type": "compare",
        "mappings": [
            "reading-2",
            "amendment-passage",
            "amendment-amendment",
        ],
    },
    "2nd reading pass motion failed; 3rd reading vote required": {
        "type": "compare",
        "mappings": ["reading-2"],
    },
    "2nd reading not passed as amended": {"type": "compare", "mappings": ["reading-2"]},
    "2nd reading house amendments concurred": {
        "type": "compare",
        "mappings": [
            "reading-2",
            "amendment-passage",
            "amendment-amendment",
        ],
    },
    "2nd reading concurred": {"type": "compare", "mappings": ["reading-2"]},
    "reconsidered previous action; placed on 2nd reading": {
        "type": "compare",
        "mappings": ["reading-2"],
    },
    "2nd reading indefinitely postponed": {
        "type": "compare",
        "mappings": ["reading-2"],
    },
    "taken from 3rd reading; placed on 2nd reading": {
        "type": "compare",
        "mappings": ["reading-2"],
    },
    "2nd reading concur motion failed": {"type": "compare", "mappings": ["reading-2"]},
    "2nd reading not concurred; 3rd reading vote required": {
        "type": "compare",
        "mappings": ["reading-2"],
    },
    "reconsidered previous act; remains in 2nd reading fcc process": {
        "type": "compare",
        "mappings": ["reading-2"],
    },
    "2nd reading indefinitely postpone motion failed": {
        "type": "compare",
        "mappings": ["reading-2"],
    },
    "2nd reading pass motion failed": {"type": "compare", "mappings": ["reading-2"]},
    "2nd reading not concurred": {"type": "compare", "mappings": ["reading-2"]},
    "2nd reading not passed": {"type": "compare", "mappings": ["reading-2"]},
    "2nd reading": {"type": "compare", "mappings": ["reading-2"]},
    # A bill has undergone its third (or final) reading
    "3rd reading pass consideration": {"type": "compare", "mappings": ["reading-3"]},
    "3rd reading not passed as amended by senate": {
        "type": "compare",
        "mappings": ["reading-3"],
    },
    "reconsidered previous action; remains in 3rd reading process": {
        "type": "compare",
        "mappings": ["reading-3"],
    },
    "3rd reading conference committee report adopted": {
        "type": "compare",
        "mappings": ["reading-3"],
    },
    "scheduled for 3rd reading": {"type": "compare", "mappings": ["reading-3"]},
    # The bill has been transmitted to the governor for consideration
    "transmitted to governor": {"type": "compare", "mappings": ["executive-receipt"]},
    # The bill has signed into law by the governor
    "signed by governor": {"type": "compare", "mappings": ["executive-signature"]},
    # The bill has been vetoed by the governor
    "vetoed by governor": {"type": "compare", "mappings": ["executive-veto"]},
    # The governor has issued a line-item (partial) veto
    "returned with governor's line-item veto": {
        "type": "compare",
        "mappings": ["executive-veto-line-item"],
    },
    # An amendment has been offered on the bill
    "^(?i)amendment.{,200}introduced": {
        "type": "regex",
        "mappings": ["amendment-introduction"],
    },
    # The bill has been amended, an offered amendment has been amended (seen in Texas)
    "3rd reading governor's proposed amendments adopted": {
        "type": "compare",
        "mappings": [
            "amendment-passage",
            "amendment-amendment",
        ],
    },
    "2nd reading governor's proposed amendments adopted": {
        "type": "compare",
        "mappings": [
            "amendment-passage",
            "amendment-amendment",
        ],
    },
    # An offered amendment has failed
    "2nd reading house amendments not concur motion failed": {
        "type": "compare",
        "mappings": ["amendment-failure"],
    },
    "2nd reading senate amendments concur motion failed": {
        "type": "compare",
        "mappings": ["amendment-failure"],
    },
    "2nd reading house amendments concur motion failed": {
        "type": "compare",
        "mappings": ["amendment-failure"],
    },
    "2nd reading governor's proposed amendments not adopted": {
        "type": "compare",
        "mappings": ["amendment-failure"],
    },
    "3rd reading governor's proposed amendments not adopted": {
        "type": "compare",
        "mappings": ["amendment-failure"],
    },
    "2nd reading governor's proposed amendments adopt motion failed": {
        "type": "compare",
        "mappings": ["amendment-failure"],
    },
    "2nd reading motion to amend failed": {
        "type": "compare",
        "mappings": ["amendment-failure"],
    },
    "2nd reading house amendments not concurred": {
        "type": "compare",
        "mappings": ["amendment-failure"],
    },
    # An amendment has been 'laid on the table' (generally preventing further consideration)
    "tabled in committee": {"type": "compare", "mappings": ["amendment-deferral"]},
    # The bill has been referred to a committee
    "referred to committee": {"type": "compare", "mappings": ["referral-committee"]},
    "rereferred to committee": {"type": "compare", "mappings": ["referral-committee"]},
    # The bill has been passed out of a committee
    "committee executive action--bill passed": {
        "type": "compare",
        "mappings": ["committee-passage"],
    },
    "committee report--bill passed": {
        "type": "compare",
        "mappings": ["committee-passage"],
    },
    "committee executive action--resolution adopted": {
        "type": "compare",
        "mappings": ["committee-passage"],
    },
    # The bill has failed to make it out of committee
    "committee executive action--resolution not adopted": {
        "type": "compare",
        "mappings": ["committee-failure"],
    },
    "committee executive action--bill not passed": {
        "type": "compare",
        "mappings": ["committee-failure"],
    },
    "died in standing committee": {
        "type": "compare",
        "mappings": ["committee-failure"],
    },
    # Misc actions
    "signed by speaker": {"type": "compare", "mappings": ["became-law"]},
    "signed by president": {"type": "compare", "mappings": ["became-law"]},
    "failed": {"type": "compare", "mappings": ["failure"]},
    "received": {"type": "compare", "mappings": ["receipt"]},
    "enrolled": {"type": "compare", "mappings": ["enrolled"]},
}


# TODO: write function description comment, remove unncessary comments, CHANGE MT INIT FILE BACK
# Takes in a string description of an action and returns the respective OS classification
def categorize_actions(act_desc):
    atype = []
    for action_key, data in _actions.items():

        # If the action requires regex to be correctly classified
        if data["type"] == "regex":
            if re.search(action_key, act_desc.lower()):
                # Add all action classifications in the list, excluding regex marker
                atype.extend(a for a in data["mappings"])

        else:
            if action_key in act_desc.lower():
                atype.extend(a for a in data["mappings"])

    return atype
