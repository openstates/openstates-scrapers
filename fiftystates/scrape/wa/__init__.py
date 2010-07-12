status = dict(
    bills=True,
    bill_versions=True,
    sponsors=True,
    actions=True,
    votes=True,
    legislators=True,
    contributors=['Gabriel J. Perez-Irizarry'],
    notes="",
)

metadata = dict(
    name='Washington',
    abbreviation='wa',
    legislature_name='Washington State Legislature',
    upper_chamber_name='Senate',
    lower_chamber_name='House of Representatives',
    upper_chamber_title='Senator',
    lower_chamber_title='Representative',
    upper_chamber_term=4,
    lower_chamber_term=2,
    sessions= map(str, xrange(2001, 2010)),
    session_details={'2001' : {'years': [2001], \
                               'sub_sessions': ["First Special Session", \
                                                "Second Special Session", \
                                                ]}, \
                     '2002' : {'years': [2002], \
                               'sub_sessions': []}, \
                     '2003' : {'years': [2003], \
                               'sub_sessions': ["First Special Session", \
                                                "Second Special Session", \
                                                "Third Special Session"]}, \
                     '2004' : {'years': [2004], \
                               'sub_sessions': []}, \
                     '2005' : {'years': [2005], \
                               'sub_sessions': []}, \
                     '2006' : {'years': [2006], \
                               'sub_sessions': ["First Special Session"]}, \
                     '2007' : {'years': [2007], \
                               'sub_sessions': []}, \
                     '2008 Special Session' : {'years': [2008], \
                               'sub_sessions': []}, \
                     '2009' : {'years': [2009], \
                               'sub_sessions': []}                             
                    }
)

