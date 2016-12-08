###########################################################
# committee actions
###########################################################

committee_actions = {
    ("REREF GOVOP", "REREF JUD",
     "REREF WM","DISC/S/C")          : "committee:referred",
    ("FAILED",)                      : "committee:failed",
    ("PASSED", "C&P", "PFC",
     "PFC W/FL")                     : "committee:passed",
    ("C&P AS AM BY AP",
     "C&P AS AM BY EN", "C&P AS AM BY APPROP",
     "C&P AS AM BY GO", "C&P AS AM BY HE",
     "C&P AS AM BY JU", "C&P AS AM BY TR",
     "C&P AS AM BY WM", "C&P AS AM BY GOVOP") : "committee:passed", # "committee:amended"],
    ("AMEND C&P", "AM C&P ON RECON",
     "AM C&P ON REREF", "PFCA W/FL",
     "PFCA")                         : "committee:passed", # "committee:amended"
    ("DP", "DP ON RECON",
     "DP ON REREFER", "DP W/MIN RPT",
     "DP/PFC", "DPA/PFC W/FL",
     "DP/PFCA")                      : "committee:passed:favorable",
    ("DPA", "DPA CORRECTED",
     "DPA ON RECON", "DPA ON REREFER",
     "DPA/PFC", "DPA/PFC W/FL",
     "DPA/PFCA", "DPA/PFCA W/FL"): "committee:passed:favorable", # "committee:amended"],
    ("DNP",)                         : "committee:passed:unfavorable",
    ("DPA/SE", "DPA/SE ON RECON",
     "DPA/SE ON REREF")              : ["committee:passed:favorable",
                                        "bill:substituted"],
    ("DISC/HELD", "HELD ON RECON",
     "HELD", "HELD 1 WK",
     "HELD INDEF")                   : "other", # "committee:held"]
}
###########################################################
# Generic actions hopefully classified correctly
###########################################################

generic_actions= {
    ("introduced",)                 : "bill:introduced",
    ("PASSED",)                     : "bill:passed",
    #there are several different fail motions so if the action contains 'FAILED'
    ("FAILED",)                     : "bill:failed",

    ("VETO OVERRIDE: PASSED",)      : "bill_veto_override:passed",
    ("VETO OVERRIDE: FAILED",)      : "bill_veto_override:failed",

    ("TRANSMITTED TO: GOVERNOR")    : "governor:received",
    ("SIGNED",)                     : "governor:signed",
    ("VETOED",)                     : "governor:vetoed",

    ("AMENDMENT: INTRODUCED",)      : "amendment:introduced",
    ("AMENDMENT: PASSED",)          : "amendment:passed",
    ("AMENDMENT", "FAILED")         : "amendment:failed",
    ("FURTHER AMENDED")             : "amendment:amended",
#    ("AMENDMENT", "WITHDRAWN")       : "amendement:withdrawn",
    ("REREF GOVOP", "REREF JUD",
     "REREF WM", "DISC/S/C",
     "REC REREF TO COM",
     "RECOMMIT TO COM")             : "committee:referred",
    # THIRD READ AND FINAL READ
    ("THIRD READ:",)                : "bill:reading:3",
    ("DPA/SE", "DPA/SE ON RECON",
     "DPA/SE ON REREF")              : "bill:substituted",
    ("HOUSE FINAL READ:",
     "SENATE FINAL READ:")          : "other",
}

###########################################################
# get_action_type()
###########################################################
def get_action_type(abbrv, group=None):
    """
    best attempt at classifying committee actions
    """
    if group == 'COMMITTEES:':
        actions = committee_actions
    else:
        actions = generic_actions

    for key in actions:
        if abbrv in key:
            return actions[key]
    return 'other'

###########################################################
# get_action
###########################################################
def get_verbose_action(abbr):
    """
    get_action('PFCA W/FL') -->
    'proper for consideration amended with recommendation for a floor amendment'
    """
    try:
        return common_abbrv[abbr]
    except KeyError:
        return abbr

###########################################################
# annottated abbreviations
###########################################################

common_abbrv = {
    # amended
    'AM C&P ON RECON': 'amended constitutional and in proper form on reconsideration',
    'AM C&P ON REREF': 'amended constitutional and in proper form on rereferral',
    'AMEND C&P': 'amended constitutional and in proper form',

    'C&P': 'constitutional and in proper form',
    # amended
    'C&P AS AM BY AP': 'constitutional and in proper form as amended by the committee on App',
    'C&P AS AM BY APPR': 'constitutional and in proper form as amended by Appropriations',
    'C&P AS AM BY EN': 'constitutional and in proper form as amended by the Committee on ENV',
    'C&P AS AM BY GO': 'constitutional and in proper form as amended by GovOp',
    'C&P AS AM BY HE': 'constitutional and in proper form as amended by HE',
    'C&P AS AM BY JU': 'constitutional and in proper form as amended by Jud',
    'C&P AS AM BY TR': 'constitutional and in proper form as amended by TR',
    'C&P AS AM BY WM': 'constitutional and in proper form as amended by the Committee on Way & Means',
    'C&P AS AM GOVOP': 'Constitutional and in proper form as amended by Government Operations',
    # reconsideration
    'C&P ON RECON': 'constitutional and in proper form on reconsideration',
    'C&P ON REREF': 'constitutional and in proper form on rereferral',
    # amended
    'C&P W/FL': 'constitutional and in proper form with a floor amendment',
    # caucus actions are ceremonial and not actually part of the legislative process
    # but if neither caucus concurs the likelyhood of a bill getting to the committee
    # of the whole or third read is not good.
    'CAUCUS': 'Caucus',
    #
    'CONCUR': 'recommend to concur',
    'CONCUR FAILED': 'motion to concur failed',
    'DISC PETITION': 'discharge petition',
    'DISC/HELD': 'discussed and held',
    'DISC/ONLY': 'discussion only',
    'DISC/S/C': 'discussd and assigned to subcommittee',
    # committee:passed:unfavorable
    'DNP': 'do not pass',
    # committee:passed:favorable from here down a ways
    'DP': 'do pass',
    'DP ON RECON': 'do pass on reconsideration',
    'DP ON REREFER': 'do passed on rereferral',
    'DP W/MIN RPT': 'do pass with minority report',
    'DP/PFC': 'do pass and proper for consideration',
    'DP/PFC W/FL': 'do pass and proper for consideration with recommendation for a floor amendment',
    'DP/PFCA': 'do pass and proper for consideration amended',
    # favorable and amended from here down #
    'DPA': 'do pass amended',
    'DPA CORRECTED': 'do pass amended corrected',
    'DPA ON RECON': 'do pass amended on reconsideration',
    'DPA ON REREFER': 'do pass amended on rereferral',
    'DPA/PFC': 'do pass amended and proper for consideration',
    'DPA/PFC W/FL': 'do pass amended and proper for consideration with recommendation for a floor amendment',
    'DPA/PFCA': 'do pass amended and proper for consideration amended',
    'DPA/PFCA W/FL': 'do pass amended and proper for consideration with recommendation for a floor amendment',
    # strike everything is like amended in the nature of a substitue
    'DPA/SE': 'do pass amended/strike-everything',
    'DPA/SE CORRECTED': 'do pass amended/strike everything corrected',
    'DPA/SE ON RECON': 'do pass amended/strike everything on reconsideration',
    'DPA/SE ON REREF': 'do pass amended/strike everything on rereferral',
    # failed #
    'FAILED': 'failed to pass',
    'FAILED BY S/V 0': 'failed by standing vote', # does this mean there is no vote?
    'FAILED ON RECON': 'failed on reconsideration', # after a succesful motion to reconsider
    # in the house a bill is first read and assigned to committee #
    'FIRST': 'First Reading',
    # amendment amended??? or just another amendment? #
    'FURTHER AMENDED': 'further amended',

    'HELD': 'held',
    'HELD 1 WK': 'held one week',
    'HELD INDEF': 'held indefinitely',
    'HELD ON RECON': 'held on reconsideration',

    'None': 'No Action',

    'NOT CONCUR': 'rec not concur',
    # not read?
    'NOT HEARD': 'not heard',

    'NOT IN ORDER': 'not in order',

    'PASSED': 'Passed',
    # rules committee action #
    'PFC': 'proper for consideration',

    'PFC W/FL': 'proper for consideration with recommendation for a floor amendment',
    'PFCA': 'proper for consideration amended',
    'PFCA W/FL': 'proper for consideration amended with recommendation for a floor amendment',

    'POSTPONE INDEFI': 'postponed indefinitely',
    # vote actions
    'REC REREF TO COM': 'recommend rereferral to committee',
    'RECOMMIT TO COM': 'recommit to committee',
    # not sure when this would take place? I would like to see it in action
    'REMOVAL REQ': 'removal request from Rules Committee',
    # committee:refered
    'REREF GOVOP': 'rereferred to GovOp',
    'REREF JUD': 'rereferred to Judiciary',
    'REREF WM': 'rereferred to Ways & Means',

    'RET FOR CON': 'returned for consideration',

    'RET ON CAL': 'retained on the Calendar',
    'RETAINED': 'retained',

    'RULE 8J PROPER': 'proper legislation and deemed not derogatory or insulting',

    'S/C': 'subcommittee',
    'S/C REPORTED': 'subcommittee reported',

    'W/D': 'withdrawn',
}
