import re


# ----------------------------------------------------------------------------
# Dictionary matching bill action phrases to classifications. Classifications can be found here:
# https://github.com/openstates/openstates-core/blob/5b16776b1882da925e8e8d5c0a07160a7d649c69/openstates/data/common.py#L87
# The "regex" included in some actions denotes that regex should be used to identify those phrases
_actions = {
    # Bill is introduced or prefiled
    "^introduced$": ["introduction", "regex"],
    # Bill has passed a chamber, a bill has undergone its third (or final) reading
    "3rd reading passed": ["passage", "reading-3"],
    "^resolution adopted": ["passage", "regex"],
    "3rd reading concurred": ["passage", "reading-3"],
    "3rd reading passed as amended by senate": ["passage", "reading-3"],
    "3rd reading passed as amended by house": ["passage", "reading-3"],
    # Bill has failed to pass a chamber
    "3rd reading failed": ["failure", "reading-3"],
    "died in process": ["failure"],
    # The chamber attempted a veto override and succeeded
    "veto overridden in house": ["veto-override-passage"],
    # The chamber attempted a veto override and failed
    "veto override motion failed": ["veto-override-failure"],
    "veto override failed": ["veto-override-failure"],
    # Became law, potentially without governor signature
    "chapter number assigned": ["became-law"],
    # A bill has undergone its first reading
    "first reading": ["reading-1"],
    # A bill has undergone its second reading, the bill has been amended,
    # an offered amendment has been amended (seen in Texas)
    "taken from committee; placed on 2nd reading": ["reading-2"],
    "2nd reading passed": ["reading-2"],
    "2nd reading conference committee report adopted": ["reading-2"],
    "2nd reading senate amendments concurred": [
        "reading-2",
        "amendment-passage",
        "amendment-amendment",
    ],
    "2nd reading pass motion failed; 3rd reading vote required": ["reading-2"],
    "2nd reading not passed as amended": ["reading-2"],
    "2nd reading house amendments concurred": [
        "reading-2",
        "amendment-passage",
        "amendment-amendment",
    ],
    "2nd reading concurred": ["reading-2"],
    "reconsidered previous action; placed on 2nd reading": ["reading-2"],
    "2nd reading indefinitely postponed": ["reading-2"],
    "taken from 3rd reading; placed on 2nd reading": ["reading-2"],
    "2nd reading concur motion failed": ["reading-2"],
    "2nd reading not concurred; 3rd reading vote required": ["reading-2"],
    "reconsidered previous act; remains in 2nd reading fcc process": ["reading-2"],
    "2nd reading indefinitely postpone motion failed": ["reading-2"],
    "2nd reading pass motion failed": ["reading-2"],
    "2nd reading not concurred": ["reading-2"],
    "2nd reading not passed": ["reading-2"],
    "2nd reading": ["reading-2"],
    # A bill has undergone its third (or final) reading
    "3rd reading pass consideration": ["reading-3"],
    "3rd reading not passed as amended by senate": ["reading-3"],
    "reconsidered previous action; remains in 3rd reading process": ["reading-3"],
    "3rd reading conference committee report adopted": ["reading-3"],
    "scheduled for 3rd reading": ["reading-3"],
    # The bill has been transmitted to the governor for consideration
    "transmitted to governor": ["executive-receipt"],
    # The bill has signed into law by the governor
    "signed by governor": ["executive-signature"],
    # The bill has been vetoed by the governor
    "vetoed by governor": ["executive-veto"],
    # The governor has issued a line-item (partial) veto
    "returned with governor's line-item veto": ["executive-veto-line-item"],
    # An amendment has been offered on the bill
    "^(?i)amendment.{,200}introduced": ["amendment-introduction", "regex"],
    # The bill has been amended, an offered amendment has been amended (seen in Texas)
    "3rd reading governor's proposed amendments adopted": [
        "amendment-passage",
        "amendment-amendment",
    ],
    "2nd reading governor's proposed amendments adopted": [
        "amendment-passage",
        "amendment-amendment",
    ],
    # An offered amendment has failed
    "2nd reading house amendments not concur motion failed": ["amendment-failure"],
    "2nd reading senate amendments concur motion failed": ["amendment-failure"],
    "2nd reading house amendments concur motion failed": ["amendment-failure"],
    "2nd reading governor's proposed amendments not adopted": ["amendment-failure"],
    "3rd reading governor's proposed amendments not adopted": ["amendment-failure"],
    "2nd reading governor's proposed amendments adopt motion failed": [
        "amendment-failure"
    ],
    "2nd reading motion to amend failed": ["amendment-failure"],
    "2nd reading house amendments not concurred": ["amendment-failure"],
    # An amendment has been 'laid on the table' (generally preventing further consideration)
    "tabled in committee": ["amendment-deferral"],
    # The bill has been referred to a committee
    "referred to committee": ["referral-committee"],
    "rereferred to committee": ["referral-committee"],
    # The bill has been passed out of a committee
    "committee executive action--bill passed": ["committee-passage"],
    "committee report--bill passed": ["committee-passage"],
    "committee executive action--resolution adopted": ["committee-passage"],
    # The bill has failed to make it out of committee
    "committee executive action--resolution not adopted": ["committee-failure"],
    "committee executive action--bill not passed": ["committee-failure"],
    "died in standing committee": ["committee-failure"],
    # Misc actions
    "signed by speaker": ["became-law"],
    "signed by president": ["became-law"],
    "failed": ["failure"],
    "received": ["receipt"],
    "enrolled": ["enrolled"],
}


# TODO: write function description comment, remove unncessary comments, CHANGE MT INIT FILE BACK
# Takes in a string description of an action and returns the respective OS classification
def categorize_actions(act_desc):
    atype = []
    for action_key in _actions.keys():

        # If the action requires regex to be correctly classified
        if _actions[action_key][-1] == "regex":
            if re.search(action_key, act_desc.lower()):
                # Add all action classifications in the list, excluding regex marker
                atype.extend(a for a in _actions[action_key] if a != "regex")

        else:
            if action_key in act_desc.lower():
                atype.extend(a for a in _actions[action_key] if a != "regex")

    return atype
