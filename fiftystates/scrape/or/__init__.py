status = dict(
    bills=False,
    bill_versions=False,
    sponsors=False,
    actions=False,
    votes=False,
    legislators=False,
    contributors=['Gabriel J. Perez-Irizarry'],
    notes="Legislator data available for only 2009. Oregon does not hold annual sessions.",
)

metadata = dict(
    name='Oregon',
    abbreviation='or',
    legislature_name='Oregon Legislative Assembly',
    upper_chamber_name='Senate',
    lower_chamber_name='House of Representatives',
    upper_chamber_title='Senator',
    lower_chamber_title='Representative',
    upper_chamber_term=4,
    lower_chamber_term=2,
       sessions=['1995', '1996 Special Session', '1997', '1999', '2001', \
              '2002 Special Sessions', '2003', '2005', '2006 Special Session', \
               '2007', '2008 Special Session', '2009', '2010 Special Session'],
    session_details={'1995': {'years': [1995], \
                               'sub_sessions': ["1995 Special Session"]}, \
                     '1996 Special Session' : {'years': [1996], \
                               'sub_sessions': []}, \
                     '1997' : {'years': [1997], \
                               'sub_sessions': []}, \
                     '1999' : {'years': [1999], \
                               'sub_sessions': []}, \
                     '2001' : {'years': [2001], \
                               'sub_sessions': []}, \
                     '2002 Special Sessions' : {'years': [2002], \
                               'sub_sessions': ["First Special Session", \
                                                "Second Special Session", \
                                                "Third Special Session", \
                                                "Fourth Special Session", \
                                                "Fifth Special Session"] \
                                                }, \
                     '2003' : {'years': [2003], \
                               'sub_sessions': []}, \
                     '2005' : {'years': [2005], \
                               'sub_sessions': []}, \
                     '2006 Special Session' : {'years': [2006], \
                               'sub_sessions': []}, \
                     '2007' : {'years': [2007], \
                               'sub_sessions': []}, \
                     '2008 Special Session' : {'years': [2008], \
                               'sub_sessions': []}, \
                     '2009' : {'years': [2009], \
                               'sub_sessions': []}, \
                     '2010 Special Session' : {'years': [2010], \
                               'sub_sessions': []}, \
                               
                    }
)