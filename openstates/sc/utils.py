import re


def action_type(action):
    action = action.lower()
    atypes = []
    if re.match('^read (the )?(first|1st) time', action):
        atypes.append('bill:introduced')
        atypes.append('bill:reading:1')
    elif re.match('^read second time', action):
        atypes.append('bill:reading:2')
    elif re.match('^read third time', action):
        atypes.append('bill:reading:3')

    if re.match('^referred to (the )?committee', action):
        atypes.append('committee:referred')
    elif re.match('^referred to (the )?subcommittee', action):
        atypes.append('committee:referred')

    if re.match('^introduced and adopted', action):
        atypes.append('bill:introduced')
        #not sure if adopted means passed
        atypes.append('bill:passed')
    elif re.match('^introduced and read first time', action):
        atypes.append('bill:introduced')
        atypes.append('bill:reading:1')
    elif re.match('^introduced', action):
        atypes.append('bill:introduced')

    if atypes:
        return atypes

    return ['other']

