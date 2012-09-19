from billy.utils.fulltext import (pdfdata_to_text, oyster_text,
                            text_after_line_numbers)

metadata = dict(
    name='Nevada',
    abbreviation='nv',
    legislature_name='Nevada Legislature',
    capitol_timezone='America/Los_Angeles',
    upper_chamber_name='Senate',
    lower_chamber_name='Assembly',
    upper_chamber_title='Senator',
    lower_chamber_title='Representative',
    upper_chamber_term=4,
    lower_chamber_term=2,
    terms = [
        #{'name': '2001-2002', 'start_year': 2001, 'end_year': 2002,
        # 'sessions': ['2001Special17', '2002Special18', '71'],
        #},
        #{'name': '2003-2004', 'start_year': 2003, 'end_year': 2004,
        # 'sessions': ['2003Special19', '2003Special20', '2004Special21', '72']
        #},
        #{'name': '2005-2006', 'start_year': 2005, 'end_year': 2006,
        # 'sessions': ['2005Special22', '73']
        #},
        #{'name': '2007-2008', 'start_year': 2007, 'end_year': 2008,
        # 'sessions': ['2007Special23', '2008Special24', '2008Special25', '74']
        #},
        {'name': '2009-2010', 'start_year': 2009, 'end_year': 2010,
         'sessions': ['2010Special26', '75'],
        },
        {'name': '2011-2012', 'start_year': 2011, 'end_year': 2012,
         'sessions': ['76', '2011 Session']
        }
    ],
    session_details={
        '2010Special26': {'type':'special',
                          'display_name': '26th Special Session (2010)',
                          '_scraped_name': '26th Special Session (2010)',
                          'slug': '26th2010Special',
                         },
        '75': {'type': 'primary',
               'display_name': '2009 Regular Session',
               '_scraped_name': '2009 Session',
               'slug': '75th2009',
              },
        '2011 Session': {
            "type": "primary",
            "display_name": '2011 Regular Session',
            "_scraped_name": '2011 Session',
            "slug": "2011"
        },
        '76': {'type': 'primary',
               'display_name': '2011 Regular Session',
               '_scraped_name': '76th Session (2011)',
               'slug': '76th2011',
              },
    },
    feature_flags=['subjects', 'capitol_maps', 'influenceexplorer'],
    capitol_maps=[
        {"name": "Floor 1",
         "url": 'http://static.openstates.org/capmaps/nv/Leg1.gif'
        },
        {"name": "Floor 2",
         "url": 'http://static.openstates.org/capmaps/nv/Leg2.gif'
        },
        {"name": "Floor 3",
         "url": 'http://static.openstates.org/capmaps/nv/Leg3.gif'
        },
        {"name": "Floor 4",
         "url": 'http://static.openstates.org/capmaps/nv/Leg4.gif'
        },
    ],
    _ignored_scraped_sessions=['25th Special Session (2008)',
                               '24th Special Session (2008)',
                               '23rd Special Session (2007)',
                               '2007 Session',
                               '22nd Special Session (2005)',
                               '2005 Session',
                               '21st Special (2004)',
                               '20th Special (2003)',
                               '19th Special (2003)',
                               '2003 Session',
                               '18th Special (2002)',
                               '17th Special (2001)',
                               '2001 Session',
                               '1999 Session',
                               '1997 Session',
                               '1995 Session',
                               '1993 Session',
                               '1991 Session',
                               '16th Special (1989)',
                               '1989 Session',
                               '1987 Session',
                               '1985 Session'],

)


def session_list():
    from billy.scrape.utils import url_xpath
    return [x.text_content() for x in
            url_xpath('http://www.leg.state.nv.us/Session/',
                      '//*[@class="MainHeading"]')]

@oyster_text
def extract_text(oyster_doc, data):
    return text_after_line_numbers(pdfdata_to_text(data))

document_class = dict(
    AWS_PREFIX = 'documents/nv/',
    update_mins = 7*24*60,
    extract_text = extract_text,
    onchanged = ['oyster.ext.elasticsearch.ElasticSearchPush']
)
