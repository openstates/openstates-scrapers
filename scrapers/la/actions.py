# Dictionary matching bill action phrases to classifications. Classifications can be found here:
# https://github.com/openstates/openstates-core/blob/5b16776b1882da925e8e8d5c0a07160a7d649c69/openstates/data/common.py#L87
_actions = [
    {
        "type": "compare",
        "value": "vetoed by the governor",
        "mappings": ["executive-veto"],
    },
    {"type": "compare", "value": "becomes Act", "mappings": ["became-law"]},
    {
        "type": "compare",
        "value": "sent to the governor",
        "mappings": ["executive-receipt"],
    },
    {
        "type": "compare",
        "value": "signed by the governor",
        "mappings": ["executive-signature"],
    },
    {"type": "compare", "value": "ordered to the senate", "mappings": ["passage"]},
    {
        "type": "compare",
        "value": "ordered returned to the house",
        "mappings": ["passage"],
    },
    {"type": "compare", "value": "sent to the house", "mappings": ["passage"]},
    {
        "type": "compare",
        "value": "referred to the committee",
        "mappings": ["referral-committee"],
    },
    {"type": "compare", "value": "prefiled", "mappings": ["filing"]},
    {"type": "compare", "value": "passed to 3rd reading", "mappings": ["reading-3"]},
    {"type": "compare", "value": "inially passed", "mappings": ["passage"]},
    {"type": "compare", "value": "assed by", "mappings": ["passage"]},
    {
        "type": "compare",
        "value": "sent to the governor",
        "mappings": ["executive-receipt"],
    },
    {
        "type": "compare",
        "value": "reported with amendments",
        "mappings": ["committee-passage-favorable"],
    },
    {
        "type": "compare",
        "value": "reported favorably",
        "mappings": ["committee-passage-favorable"],
    },
    {"type": "compare", "value": "enrolled", "mappings": ["enrolled"]},
    {
        "type": "compare",
        "value": "read by title and passed to third reading",
        "mappings": ["reading-3"],
    },
    {"type": "compare", "value": "read first time by title", "mappings": ["reading-1"]},
    {
        "type": "compare",
        "value": "read second time by title",
        "mappings": ["reading-2"],
    },
    {
        "type": "compare",
        "value": "read second time by title",
        "mappings": ["reading-2"],
    },
    {"type": "compare", "value": "received from", "mappings": ["receipt"]},
]


def categorize_actions(action_description):
    atype = []
    for action_dict in _actions:
        if action_dict["value"] in action_description.lower():
            atype.extend(a for a in action_dict["mappings"])

    return atype
