import lxml
from pupa.scrape import Jurisdiction, Organization
from .people import NCPersonScraper
# from .committees import NCCommitteeScraper
from .bills import NCBillScraper


class NorthCarolina(Jurisdiction):
    division_id = "ocd-division/country:us/state:nc"
    classification = "government"
    name = "North Carolina"
    url = "http://www.ncleg.net/"
    scrapers = {
        'people': NCPersonScraper,
        # 'committees': NCCommitteeScraper,
        'bills': NCBillScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "1985-1986 Session",
            "classification": "primary",
            "identifier": "1985",
            "name": "1985-1986 Session",
            "start_date": "1985-02-05"
        },
        {
            "_scraped_name": "1987-1988 Session",
            "classification": "primary",
            "identifier": "1987",
            "name": "1987-1988 Session",
            "start_date": "1987-02-09"
        },
        {
            "_scraped_name": "1991-1992 Session",
            "classification": "primary",
            "identifier": "1991",
            "name": "1991-1992 Session",
            "start_date": "1991-01-30"
        },
        {
            "_scraped_name": "2009-2010 Session",
            "classification": "primary",
            "identifier": "2009",
            "name": "2009-2010 Session",
            "start_date": "2009-01-28"
        },
        {
            "_scraped_name": "2011-2012 Session",
            "classification": "primary",
            "identifier": "2011",
            "name": "2011-2012 Session",
            "start_date": "2011-01-26"
        },
        {
            "_scraped_name": "2013-2014 Session",
            "classification": "primary",
            "identifier": "2013",
            "name": "2013-2014 Session",
            "start_date": "2013-01-30"
        },
        {
            "_scraped_name": "2015-2016 Session",
            "classification": "primary",
            "identifier": "2015",
            "name": "2015-2016 Session",
            "start_date": "2015-01-30"
        },
        {
            "_scraped_name": "2016 Extra Session",
            "classification": "special",
            "identifier": "2015E1",
            "name": "2016 Extra Session 1",
        },
        {
            "_scraped_name": "2016 Second Extra Session",
            "classification": "special",
            "identifier": "2015E2",
            "name": "2016 Extra Session 2",
        },
        {
            "_scraped_name": "2016 Third Extra Session",
            "classification": "special",
            "identifier": "2015E3",
            "name": "2016 Extra Session 3",
        },
        {
            "_scraped_name": "2016 Fourth Extra Session",
            "classification": "special",
            "identifier": "2015E4",
            "name": "2016 Extra Session 4",
        },
        {
            "_scraped_name": "2016 Fifth Extra Session",
            "classification": "special",
            "identifier": "2015E5",
            "name": "2016 Extra Session 5",
        },
        {
            "_scraped_name": "2017-2018 Session",
            "classification": "primary",
            "identifier": "2017",
            "name": "2017-2018 Session",
            "start_date": "2017-01-11",
            "end_date": "2018-08-01"
        },
        {
            "_scraped_name": "2018 First Extra Session",
            "classification": "special",
            "identifier": "2017E1",
            "name": "2018 Extra Session 1",
        },
        {
            "_scraped_name": "2018 Second Extra Session",
            "classification": "special",
            "identifier": "2017E2",
            "name": "2018 Extra Session 2",
            "start_date": "2018-08-24"
        },
        {
            "_scraped_name": "2018 Third Extra Session",
            "classification": "special",
            "identifier": "2017E3",
            "name": "2018 Extra Session 3",
            "start_date": "2018-10-02"
        },
        {
            "_scraped_name": "2019-2020 Session",
            "classification": "primary",
            "identifier": "2019",
            "name": "2019-2020 Session",
            "start_date": "2019-01-03",
            "end_date": "2020-08-01"
        },
    ]
    ignored_scraped_sessions = [
        '2016 First Extra Session',
        '2008 Extra Session',
        '2007-2008 Session',
        '2007 Extra Session',
        '2005-2006 Session',
        '2004 Extra Session',
        '2003-2004 Session',
        '2003 Extra Session',
        '2002 Extra Session',
        '2001-2002 Session',
        '2000 Special Session',
        '1999-2000 Session',
        '1999 Special Session',
        '1998 Special Session',
        '1997-1998 Session',
        '1996 2nd Special Session',
        '1996 1st Special Session',
        '1995-1996 Session',
        '1994 Special Session',
        '1993-1994 Session',
        '1991-1992 Session',
        '1991 Special Session',
        '1990 Special Session',
        '1989-1990 Session',
        '1989 Special Session',
        '1987-1988 Session',
        '1986 Special Session',
        '1985-1986 Session',
    ]

    def get_organizations(self):
        legislature_name = "North Carolina General Assembly"

        legislature = Organization(name=legislature_name,
                                   classification="legislature")
        executive = Organization(name='Executive Office of the Governor',
                                 classification="executive")
        upper = Organization('Senate', classification='upper',
                             parent_id=legislature._id)
        lower = Organization('House', classification='lower',
                             parent_id=legislature._id)

        yield legislature
        yield executive
        yield upper
        yield lower

    def get_session_list(self):
        from openstates.utils.lxmlize import url_xpath
        # This is the URL that populates the session `<select>` in the
        # state homepage header navigation
        return url_xpath('https://webservices.ncleg.net/sessionselectlist/false',
                         '//option/text()')

    def extract_text(self, doc, data):
        doc = lxml.html.fromstring(data)
        text = ' '.join([x.text_content() for x in
                         doc.xpath('//p[starts-with(@class, "a")]')])
        return text
