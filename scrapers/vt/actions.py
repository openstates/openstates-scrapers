import re

# Dictionary matching bill action phrases to classifications. Classifications can be found here:
# https://github.com/openstates/openstates-core/blob/5b16776b1882da925e8e8d5c0a07160a7d649c69/openstates/data/common.py#L87
_actions = {
    "read first": {"type": "compare", "mappings": ["introduction"]},
    "read 1st time": {"type": "compare", "mappings": ["introduction"]},
    "first read": {"type": "compare", "mappings": ["introduction"]},
    "read second": {"type": "compare", "mappings": ["reading-2"]},
    "read 2nd": {"type": "compare", "mappings": ["reading-2"]},
    "second read": {"type": "compare", "mappings": ["reading-2"]},
    "read third": {"type": "compare", "mappings": ["reading-3"]},
    "read 3rd": {"type": "compare", "mappings": ["reading-3"]},
    "third read": {"type": "compare", "mappings": ["reading-3"]},
    "reported favorably": {
        "type": "compare",
        "mappings": ["committee-passage-favorable"],
    },
    "rules suspended & messaged to house forthwith": {
        "type": "compare",
        "mappings": ["passage"],
    },
    "delivered to governor": {"type": "compare", "mappings": ["executive-receipt"]},
    "signed by governor": {"type": "compare", "mappings": ["executive-signature"]},
    "vetoed by the governor": {"type": "compare", "mappings": ["executive-veto"]},
    "vetoed": {"type": "compare", "mappings": ["executive-veto"]},
    "overrid": {"type": "compare", "mappings": ["veto-override-passage"]},
    "proposal of amendment": {
        "type": "compare",
        "mappings": ["amendment-introduction"],
    },
    "become law without signature of governor": {
        "type": "compare",
        "mappings": ["became-law"],
    },
    "governor allowed to become law": {"type": "compare", "mappings": ["became-law"]},
    "allowed to go into effect without the signature of the governor": {
        "type": "compare",
        "mappings": ["became-law"],
    },
}


# Takes in a string description of an action and returns the respective OS classification
def categorize_actions(action_description):
    atype = []
    for action_key, data in _actions.items():
        # If regex is required to isolate bill action phrase
        if data["type"] == "regex":
            if re.search(action_key, action_description.lower()):
                atype.extend(a for a in data["mappings"])

        # Otherwise, we use basic string comparison
        else:
            # If we can detect a phrase that there is an OS action classification for
            if action_key in action_description.lower():
                atype.extend(a for a in data["mappings"])

    return atype
