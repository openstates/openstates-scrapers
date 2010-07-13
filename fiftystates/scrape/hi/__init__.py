status = dict(
    bills=True,
    bill_versions=True,
    sponsors=True,
    actions=True,
    votes=True,
    legislators=True,
    contributors=['Gabriel J. Perez-Irizarry'],
    notes="Some changes need to be made to be able to scrape older years. Still can't determine if votes passed",
)

metadata = dict(
    name='Hawaii',
    abbreviation='hi',
    legislature_name='Hawaii State Legislature',
    upper_chamber_name='Senate',
    lower_chamber_name='House of Representatives',
    upper_chamber_title='Senator',
    lower_chamber_title='Representative',
    upper_chamber_term=2,
    lower_chamber_term=2,
    sessions= map(str, xrange(1999, 2010)),
    session_details={'1999' : {'years': [1999], \
                               'sub_sessions': []}, \
                     '2000' : {'years': [2000], \
                               'sub_sessions': []}, \
                     '2001' : {'years': [2001], \
                               'sub_sessions': ["First Special Session", \
                                                "Second Special Session", \
                                                "Third Special Session", \
                                                ]}, \
                     '2002' : {'years': [2002], \
                               'sub_sessions': []}, \
                     '2003' : {'years': [2003], \
                               'sub_sessions': ["First Special Session"]}, \
                     '2004' : {'years': [2005], \
                               'sub_sessions': []}, \
                     '2005' : {'years': [2005], \
                               'sub_sessions': ["First Special Session"]}, \
                     '2006' : {'years': [2006], \
                               'sub_sessions': ["First Special Session"]}, \
                     '2007' : {'years': [2007], \
                               'sub_sessions': ["First Special Session", \
                                                "Second Special Session", \
                                                "Third Special Session", \
                                                ]}, \
                     '2008' : {'years': [2008], \
                               'sub_sessions': ["First Special Session", \
                                                "Second Special Session", \
                                                "Third Special Session", \
                                                ]}, \
                     '2009' : {'years': [2009], \
                               'sub_sessions': ["First Special Session", \
                                                "Second Special Session", \
                                                "Third Special Session", \
                                                ]}, \
                                              
                    }
)

