import datetime
import lxml.html

settings = dict(
    SCRAPELIB_RPM=8,
    SCRAPELIB_RETRY_WAIT=30,
)

metadata = dict(
    name='South Dakota',
    abbreviation='sd',
    legislature_name='South Dakota State Legislature',
    capitol_timezone='America/Chicago',
    chambers = {
        'upper': {'name': 'Senate', 'title': 'Senator'},
        'lower': {'name': 'House', 'title': 'Representative'},
    },
    terms=[
        {'name': '2009-2010', 'start_year': 2009, 'end_year': 2010,
         'sessions': ['2009', '2010']},
        {'name': '2011-2012', 'start_year': 2011, 'end_year': 2012,
         'sessions': ['2011', '2011s', '2012']},
        {'name': '2013-2014', 'start_year': 2013, 'end_year': 2014,
         'sessions': ['2013']},
        ],
    session_details={
        '2009': {'display_name': '2009 Regular Session',
                 '_scraped_name': '2009 (84th) Session',
                },
        '2010': {'display_name': '2010 Regular Session',
                 '_scraped_name': '2010 (85th) Session',
                },
        '2011': {'start_date': datetime.date(2011, 1, 11),
                 'display_name': '2011 Regular Session',
                 '_scraped_name': '2011 (86th) Session',
                },
        '2011s': {'display_name': '2011 Special Session',
                  '_scraped_name': '2011 (86th) Special Session',
                 },
        '2012': {'display_name': '2012 Regular Session',
                 '_scraped_name': '2012 (87th) Session',
                },
        '2013': {'display_name': '2013 Regular Session',
                }
    },
    feature_flags=['subjects', 'influenceexplorer'],
    _ignored_scraped_sessions=['2008 (83rd) Session', '2007 (82nd) Session',
                               '2006 (81st) Session',
                               '2005 (80th) Special Session',
                               '2005 (80th) Session', '2004 (79th) Session',
                               '2003 (78th) Special Session',
                               '2003 (78th) Session', '2002 (77th) Session',
                               '2001 (76th) Special Session',
                               '2001 (76th) Session',
                               '2000 (75th) Special Session',
                               '2000 (75th) Session', '1999 (74th) Session',
                               '1998 (73rd) Session',
                               '1997 (72nd) Special Session',
                               '1997 (72nd) Session']
)


def session_list():
    import urllib
    import lxml.html
    # uses urllib because httplib2 has a compression issue on this page
    html = urllib.urlopen('http://legis.state.sd.us/PastSessions.aspx').read()
    doc = lxml.html.fromstring(html)
    return doc.xpath('//span[@class="link"]/text()')

def extract_text(doc, data):
    doc = lxml.html.fromstring(data)
    return ' '.join(div.text_content() for div in
                    doc.xpath('//div[@align="full"]'))
