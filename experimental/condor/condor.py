#

from billy import db

state = "oh"


def get_state_breakdown(abbr):
    legs = db.legislators.find({"state": abbr})
    repub, dem, other = [], [], []
    for leg in legs:
        roles = leg['roles']
        if len(roles) <= 0:
            continue

        if not "party" in roles[0]:
            continue

        parta = roles[0]['party'].strip()
        if parta == "Republican":
            repub.append(leg)
        elif parta == "Democratic":
            dem.append(leg)
        else:
            other.append(leg)

    rC = float(len(repub))
    dC = float(len(dem))
    oC = float(len(other))
    tC = (rC + dC + oC)
    rP = rC / tC
    dP = dC / tC
    oP = oC / tC

    return (
        (rP, dP, oP),
        (rC, dC, oC),
        (repub, dem, other)
    )


def grok_committee(cid):
    ctty = db.committees.find_one({"_id": cid})
    if ctty is None:
        return

    (pcts, cts, raw) = get_state_breakdown(ctty['state'])

    rC, dC, oC = cts
    rP, dP, oP = pcts

    missing = 0.0
    total = 0.0

    rCount = 0.0
    dCount = 0.0
    oCount = 0.0

    for member in ctty['members']:
        total += 1
        if "leg_id" in member:
            leg = db.legislators.find_one({"_id": member['leg_id']})
            if leg is None:
                missing += 1
                continue

            roles = leg['roles']
            if len(roles) <= 0:
                missing += 1
                continue

            if not "party" in roles[0]:
                missing += 1
                continue

            parta = roles[0]['party'].strip()
            if parta == "Republican":
                rCount += 1
            elif parta == "Democratic":
                dCount += 1
            else:
                oCount += 1
        else:
            missing += 1

    if total == 0:
        return None

    rPct = rCount / total
    dPct = dCount / total
    oPct = oCount / total

    rD = rPct - rP
    dD = dPct - dP
    oD = oPct - oP

    pErr = missing / total

    # print "Ctty:", rPct, dPct, oPct
    # print "CoW: ", rP, dP, oP
    # print "Delt:", rD, dD, oD

    return (rD, dD, oD, pErr)


def digest_state(state):
    ctties = db.committees.find({"state": state})

    raw = []

    for c in ctties:
        ctty_stuff = grok_committee(c['_id'])
        if ctty_stuff is None:
            continue

        rD, dD, oD, pE = ctty_stuff
        raw.append({
            "err": pE,
            "repub": rD,
            "dem": dD,
            "other": oD,
            "cid": c['_id']
        })

    demSkew = sorted(raw, key=lambda x: x['dem'])
    repSkew = sorted(raw, key=lambda x: x['repub'])
    othSkew = sorted(raw, key=lambda x: x['other'])
    allSkew = sorted(raw, key=lambda x: (abs(x['dem']) + abs(x['repub']) + abs(x['other'])))

    return (demSkew, repSkew, othSkew, allSkew)

states = [x['_id'] for x in db.metadata.find()]

for state in states:
    print digest_state(state)
