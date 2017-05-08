from pupa.scrape import Jurisdiction, Organization
from .bills import MNBillScraper
from .committees import MNCommitteeScraper
from .people import MNPersonScraper
from .vote_events import MNVoteScraper
from .events import MNEventScraper
from .common import url_xpath

"""
Minnesota legislative data can be found at the Office of the Revisor
of Statutes:
https://www.revisor.mn.gov/

Votes:
There are not detailed vote data for Senate votes, simply yes and no counts.
Bill pages have vote counts and links to House details, so it makes more
sense to get vote data from the bill pages.
"""


class Minnesota(Jurisdiction):
    division_id = "ocd-division/country:us/state:mn"
    classification = "government"
    name = "Minnesota"
    url = "http://state.mn.us/"
    check_sessions = True
    scrapers = {
        "bills": MNBillScraper,
        "committees": MNCommitteeScraper,
        "people": MNPersonScraper,
        "vote_events": MNVoteScraper,
        "events": MNEventScraper,
    }
    parties = [{'name': 'Republican'},
               {'name': 'Democratic-Farmer-Labor'}]
    legislative_sessions = [
        {
            '_scraped_name': '86th Legislature, 2009-2010',
            'classification': 'primary',
            'identifier': '2009-2010',
            'name': '2009-2010 Regular Session'
        },
        {
            '_scraped_name': '86th Legislature, 2010 1st Special Session',
            'classification': 'special',
            'identifier': '2010 1st Special Session',
            'name': '2010, 1st Special Session'
        },
        {
            '_scraped_name': '86th Legislature, 2010 2nd Special Session',
            'classification': 'special',
            'identifier': '2010 2nd Special Session',
            'name': '2010, 2nd Special Session'
        },
        {
            '_scraped_name': '87th Legislature, 2011-2012',
            'classification': 'primary',
            'identifier': '2011-2012',
            'name': '2011-2012 Regular Session'
        },
        {
            '_scraped_name': '87th Legislature, 2011 1st Special Session',
            'classification': 'special',
            'identifier': '2011s1',
            'name': '2011, 1st Special Session'
        },
        {
            '_scraped_name': '87th Legislature, 2012 1st Special Session',
            'classification': 'special',
            'identifier': '2012s1',
            'name': '2012, 1st Special Session'
        },
        {
            '_scraped_name': '88th Legislature, 2013-2014',
            'classification': 'primary',
            'identifier': '2013-2014',
            'name': '2013-2014 Regular Session'
        },
        {
            '_scraped_name': '88th Legislature, 2013 1st Special Session',
            'classification': 'special',
            'identifier': '2013s1',
            'name': '2013, 1st Special Session'
        },
        {
            '_scraped_name': '89th Legislature, 2015-2016',
            'classification': 'primary',
            'identifier': '2015-2016',
            'name': '2015-2016 Regular Session'
        },
        {
            '_scraped_name': '89th Legislature, 2015 1st Special Session',
            'classification': 'special',
            'identifier': '2015s1',
            'name': '2015, 1st Special Session'
        },
        {
            '_scraped_name': '90th Legislature, 2017-2018',
            'classification': 'primary',
            'identifier': '2017-2018',
            'name': '2017-2018 Regular Session',
            'start_date': '2017-01-03',
            'end_date': '2017-05-22'
        },
    ]
    ignored_scraped_sessions = [
        '85th Legislature, 2007-2008',
        '85th Legislature, 2007 1st Special Session',
        '84th Legislature, 2005-2006',
        '84th Legislature, 2005 1st Special Session',
        '83rd Legislature, 2003-2004',
        '83rd Legislature, 2003 1st Special Session',
        '82nd Legislature, 2001-2002',
        '82nd Legislature, 2002 1st Special Session',
        '82nd Legislature, 2001 1st Special Session',
        '81st Legislature, 1999-2000',
        '80th Legislature, 1997-1998',
        '80th Legislature, 1998 1st Special Session',
        '80th Legislature, 1997 3rd Special Session',
        '80th Legislature, 1997 2nd Special Session',
        '80th Legislature, 1997 1st Special Session',
        '79th Legislature, 1995-1996',
        '79th Legislature, 1995 1st Special Session',
        '89th Legislature, 2015-2016',
    ]

    def get_organizations(self):
        legis = Organization('Minnesota Legislature', classification='legislature')

        upper = Organization('Minnesota Senate', classification='upper',
                             parent_id=legis._id)
        lower = Organization('Minnesota House of Representatives',
                             classification='lower', parent_id=legis._id)

        for n in range(1, 68):
            upper.add_post(label=str(n), role='Senator',
                           division_id='ocd-division/country:us/state:mn/sldu:{}'.format(n))
            lower.add_post(label=str(n) + 'A', role='Representative',
                           division_id='ocd-division/country:us/state:mn/sldl:{}a'.format(n))
            lower.add_post(label=str(n) + 'B', role='Representative',
                           division_id='ocd-division/country:us/state:mn/sldl:{}b'.format(n))

        yield legis
        yield upper
        yield lower

    def get_session_list(self):
        return url_xpath('https://www.revisor.mn.gov/revisor/pages/'
                         'search_status/status_search.php?body=House',
                         '//select[@name="session"]/option/text()')
