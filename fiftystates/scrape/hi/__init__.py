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
    state_name='Hawaii',
    abbreviation='hi',
    legislature_name='Hawaii State Legislature',
    upper_chamber_name='Senate',
    lower_chamber_name='House of Representatives',
    upper_chamber_title='Senator',
    lower_chamber_title='Representative',
    upper_chamber_term=4,
    lower_chamber_term=2,
    terms = [
        {'name': '1999-2001',
         'sessions': ['1999 Regular Session',
                      '2000 Regular Session'],
         'start_year': 1999, 'end_year': 2001},
        {'name': '2001-2003',
         'sessions': ['2001 Regular Session',
                      '2001 First Special Session'
                      '2001 Second Special Session'
                      '2001 Third Special Session'
                      '2002 Regular Session'],
         'start_year': 2001, 'end_year': 2003},
        {'name': '2003-2005',
         'sessions': ['2003 Regular Session',
                      '2003 First Special Session'
                      '2004 Regular Session'],
         'start_year': 2003, 'end_year': 2005},
        {'name': '2005-2007',
         'sessions': ['2005 Regular Session',
                      '2005 First Special Session'
                      '2006 Regular Session',
                      '2006 First Special Session'],
         'start_year': 2005, 'end_year': 2007},
        {'name': '2007-2009',
         'sessions': ['2007 Regular Session',
                      '2007 First Special Session'
                      '2007 Second Special Session',
                      '2007 Third Special Session'
                      '2008 Regular Session',
                      '2008 First Special Session'
                      '2008 Second Special Session',
                      '2008 Third Special Session'],
         'start_year': 2007, 'end_year': 2009},
        {'name': '2009-2011',
         'sessions': ['2010 Regular Session',
                      '2010 First Special Session'
                      '2009 Regular Session',
                      '2009 First Special Session',
                      '2009 Third Special Session'],
         'start_year': 2009, 'end_year': 2011},
             ]
)

