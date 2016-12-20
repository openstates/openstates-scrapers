# Return the actor for each action type, or 'chamber' for the bill's home chamber
action_chamber_map = {
    'House': 'upper',
    'Senate': 'lower',
    'RequestforEnactment': 'chamber',
    'IntroducedDate': 'chamber',
    'PreFileDate': 'chamber',
    'Governor': 'executive',
    'Veto': 'executive'
}

action_map = {
    'House1stRead':{'name': 'House First Reading.',
                      'action': ['bill:reading:1']
                     },
    'House1stWaived':{'name': 'House First Reading Waived',
                      'action': ['bill:reading:1']
                     },
    'House2ndRead':{'name': 'House Second Reading',
                      'action': ['bill:reading:2']
                     },                     
    'House2ndWaived':{'name': 'House Second Reading Waived.',
                      'action': ['bill:reading:2']
                     },
    'HouseCaucusConcurRefuse':{'name': 'House Caucus Refuse to Concur',
                        'action': ['other']
                     },
    'HouseConsentCalendarDate':{'name': 'House Placed on Consent Calendar',
                      'action': ['other']
                     },
    'HouseConsentCalendarObject':{'name': '',
                      'action': ['other']
                     },
    'HouseConsentObjectDate':{'name': '',
                            'action': ['other']
                      },
    'HouseMajCaucusDate':{'name': '',
                      'action': ['other']
                     },
    'HouseMajCaucusDate2':{'name': '',
                      'action': ['other']
                     },
    'HouseMajCaucusInd':{'name': '',
                      'action': ['other']
                     },
    'HouseMajCaucusInd2':{'name': '',
                      'action': ['other']
                     },
    'HouseMinCaucusDate':{'name': '',
                      'action': ['other']
                     },
    'HouseMinCaucusDate2':{'name': '',
                      'action': ['other']
                     },
    'HouseMinCaucusInd':{'name': '',
                      'action': ['other']
                     },
    'HouseMinCaucusInd2':{'name': '',
                      'action': ['other']
                     },
    'IntroducedDate':{'name': 'Introduced',
                      'action': ['bill:introduced']
                     },
    'PreFileDate':{'name': 'Prefiled.',
                      'action': ['bill:filed']
                     },
    'RequestforEnactment':{'name': 'Request for Enactment',
                      'action': ['other']
                     },
    'Senate1stRead':{'name': 'Senate First Reading',
                      'action': ['bill:reading:1']
                     },
    'Senate1stWaived':{'name': 'Senate First Reading Waived',
                      'action': ['bill:reading:1']
                     },
    'Senate2ndRead':{'name': 'Senate Second Reading',
                      'action': ['bill:reading:2']
                     },
    'Senate2ndWaived':{'name': 'Senate Second Reading Waived',
                      'action': ['bill:reading:2']
                     },
    'SenateCaucusConcurRefuse':{'name': '',
                      'action': ['other']
                     },
    'SenateConsentCalendarDate':{'name': '',
                      'action': ['other']
                     },
    'SenateConsentCalendarObject':{'name': '',
                      'action': ['other']
                     },
    'SenateConsentObjectDate':{'name': '',
                      'action': ['other']
                     },
    'SenateMajCaucusDate':{'name': '',
                      'action': ['other']
                     },
    'SenateMajCaucusDate2':{'name': '',
                      'action': ['other']
                     },
    'SenateMajCaucusInd':{'name': '',
                      'action': ['other']
                     },
    'SenateMajCaucusInd2':{'name': '',
                      'action': ['other']
                     },
    'SenateMinCaucusDate':{'name': '',
                      'action': ['other']
                     },
    'SenateMinCaucusDate2':{'name': '',
                      'action': ['other']
                     },
    'SenateMinCaucusInd':{'name': '',
                      'action': ['other']
                     },
    'SenateMinCaucusInd2':{'name': '',
                      'action': ['other']
                     },
    'VetoOverride':{'name': 'Veto Overridden',
                      'action': ['bill:veto_override:passed']
                     },
    #TODO: How do we tell signed from vetoed?
    'GovernorAction':{'name': '',
                      'action': ['']
                     },
}