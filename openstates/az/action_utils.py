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
                      'action': ['reading-1']
                     },
    'House1stWaived':{'name': 'House First Reading Waived',
                      'action': ['reading-1']
                     },
    'House2ndRead':{'name': 'House Second Reading',
                      'action': ['reading-2']
                     },
    'House2ndWaived':{'name': 'House Second Reading Waived.',
                      'action': ['reading-2']
                     },
    'HouseCaucusConcurRefuse':{'name': 'House Caucus Refuse to Concur',
                        'action': ['']
                     },
    'HouseConsentCalendarDate':{'name': 'House Placed on Consent Calendar',
                      'action': ['']
                     },
    'HouseConsentCalendarObject':{'name': '',
                      'action': ['']
                     },
    'HouseConsentObjectDate':{'name': '',
                            'action': ['']
                      },
    'HouseMajCaucusDate':{'name': '',
                      'action': ['']
                     },
    'HouseMajCaucusDate2':{'name': '',
                      'action': ['']
                     },
    'HouseMajCaucusInd':{'name': '',
                      'action': ['']
                     },
    'HouseMajCaucusInd2':{'name': '',
                      'action': ['']
                     },
    'HouseMinCaucusDate':{'name': '',
                      'action': ['']
                     },
    'HouseMinCaucusDate2':{'name': '',
                      'action': ['']
                     },
    'HouseMinCaucusInd':{'name': '',
                      'action': ['']
                     },
    'HouseMinCaucusInd2':{'name': '',
                      'action': ['']
                     },
    'IntroducedDate':{'name': 'Introduced',
                      'action': ['introduced']
                     },
    'PreFileDate':{'name': 'Prefiled.',
                      'action': ['filing']
                     },
    'RequestforEnactment':{'name': 'Request for Enactment',
                      'action': ['']
                     },
    'Senate1stRead':{'name': 'Senate First Reading',
                      'action': ['reading-1']
                     },
    'Senate1stWaived':{'name': 'Senate First Reading Waived',
                      'action': ['reading-1']
                     },
    'Senate2ndRead':{'name': 'Senate Second Reading',
                      'action': ['reading-2']
                     },
    'Senate2ndWaived':{'name': 'Senate Second Reading Waived',
                      'action': ['reading-2']
                     },
    'SenateCaucusConcurRefuse':{'name': '',
                      'action': ['']
                     },
    'SenateConsentCalendarDate':{'name': '',
                      'action': ['']
                     },
    'SenateConsentCalendarObject':{'name': '',
                      'action': ['']
                     },
    'SenateConsentObjectDate':{'name': '',
                      'action': ['']
                     },
    'SenateMajCaucusDate':{'name': '',
                      'action': ['']
                     },
    'SenateMajCaucusDate2':{'name': '',
                      'action': ['']
                     },
    'SenateMajCaucusInd':{'name': '',
                      'action': ['']
                     },
    'SenateMajCaucusInd2':{'name': '',
                      'action': ['']
                     },
    'SenateMinCaucusDate':{'name': '',
                      'action': ['']
                     },
    'SenateMinCaucusDate2':{'name': '',
                      'action': ['']
                     },
    'SenateMinCaucusInd':{'name': '',
                      'action': ['']
                     },
    'SenateMinCaucusInd2':{'name': '',
                      'action': ['']
                     },
    'VetoOverride':{'name': 'Veto Overridden',
                      'action': ['veto_override-passed']
                     },
    #TODO: How do we tell signed from vetoed?
    'GovernorAction':{'name': '',
                      'action': ['']
                     },
}
