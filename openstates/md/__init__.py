from pupa.scrape import Jurisdiction, Organization

from openstates.utils import url_xpath

from .bills import MDBillScraper
# from .people import MDPersonScraper
# from .committees import MDCommitteeScraper


class Maryland(Jurisdiction):
    division_id = "ocd-division/country:us/state:md"
    classification = "government"
    name = "Maryland"
    url = "http://mgaleg.maryland.gov/webmga/frm1st.aspx?tab=home"
    scrapers = {
        'bills': MDBillScraper,
        # 'people': MDPersonScraper,
        # 'committees': MDCommitteeScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "2007 Regular Session",
            "classification": "primary",
            "end_date": "2007-04-10",
            "identifier": "2007",
            "name": "2007 Regular Session",
            "start_date": "2007-01-10"
        },
        {
            "_scraped_name": "2007 Special Session 1",
            "classification": "special",
            "end_date": "2007-11-19",
            "identifier": "2007s1",
            "name": "2007, 1st Special Session",
            "start_date": "2007-10-29"
        },
        {
            "_scraped_name": "2008 Regular Session",
            "classification": "primary",
            "end_date": "2008-04-07",
            "identifier": "2008",
            "name": "2008 Regular Session",
            "start_date": "2008-01-09"
        },
        {
            "_scraped_name": "2009 Regular Session",
            "classification": "primary",
            "end_date": "2009-04-13",
            "identifier": "2009",
            "name": "2009 Regular Session",
            "start_date": "2009-01-14"
        },
        {
            "_scraped_name": "2010 Regular Session",
            "classification": "primary",
            "end_date": "2010-04-12",
            "identifier": "2010",
            "name": "2010 Regular Session",
            "start_date": "2010-01-13"
        },
        {
            "_scraped_name": "2011 Regular Session",
            "classification": "primary",
            "end_date": "2011-04-12",
            "identifier": "2011",
            "name": "2011 Regular Session",
            "start_date": "2011-01-12"
        },
        {
            "_scraped_name": "2011 Special Session 1",
            "classification": "special",
            "identifier": "2011s1",
            "name": "2011, 1st Special Session"
        },
        {
            "_scraped_name": "2012 Regular Session",
            "classification": "primary",
            "end_date": "2012-04-09",
            "identifier": "2012",
            "name": "2012 Regular Session",
            "start_date": "2012-01-11"
        },
        {
            "_scraped_name": "2012 Special Session 1",
            "classification": "special",
            "identifier": "2012s1",
            "name": "2012, 1st Special Session"
        },
        {
            "_scraped_name": "2012 Special Session 2",
            "classification": "special",
            "identifier": "2012s2",
            "name": "2012, 2nd Special Session"
        },
        {
            "_scraped_name": "2013 Regular Session",
            "classification": "primary",
            "identifier": "2013",
            "name": "2013 Regular Session"
        },
        {
            "_scraped_name": "2014 Regular Session",
            "classification": "primary",
            "identifier": "2014",
            "name": "2014 Regular Session"
        },
        {
            "_scraped_name": "2015 Regular Session",
            "classification": "primary",
            "identifier": "2015",
            "name": "2015 Regular Session"
        },
        {
            "_scraped_name": "2016 Regular Session",
            "classification": "primary",
            "identifier": "2016",
            "name": "2016 Regular Session"
        },
        {
            "_scraped_name": "2017 Regular Session",
            "classification": "primary",
            "end_date": "2017-04-10",
            "identifier": "2017",
            "name": "2017 Regular Session",
            "start_date": "2017-01-11"
        },
        {
            "_scraped_name": "2018 Regular Session",
            "classification": "primary",
            "end_date": "2018-04-09",
            "identifier": "2018",
            "name": "2018 Regular Session",
            "start_date": "2018-01-10"
        }
    ]
    ignored_scraped_sessions = [
        "1996 Regular Session",
        "1997 Regular Session",
        "1998 Regular Session",
        "1999 Regular Session",
        "2000 Regular Session",
        "2001 Regular Session",
        "2002 Regular Session",
        "2003 Regular Session",
        "2004 Regular Session",
        "2004 Special Session 1",
        "2005 Regular Session",
        "2006 Regular Session",
        "2006 Special Session 1"
    ]

    def get_organizations(self):
        legislature_name = "Maryland General Assembly"
        lower_chamber_name = "House"
        lower_title = "Delegate"
        upper_chamber_name = "Senate"
        upper_seats = 47
        upper_title = "Senator"

        legislature = Organization(name=legislature_name,
                                   classification="legislature")
        upper = Organization(upper_chamber_name, classification='upper',
                             parent_id=legislature._id)
        lower = Organization(lower_chamber_name, classification='lower',
                             parent_id=legislature._id)

        for n in range(1, upper_seats + 1):
            upper.add_post(
                label=str(n), role=upper_title,
                division_id='{}/sldu:{}'.format(self.division_id, n))

        lower.add_post('1A',  # maximum=1,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:1a')
        lower.add_post('1B',  # maximum=1,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:1b')
        lower.add_post('1C',  # maximum=1,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:1c')
        lower.add_post('2A',  # maximum=2,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:2a')
        lower.add_post('2B',  # maximum=1,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:2b')
        lower.add_post('3A',  # maximum=2,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:3a')
        lower.add_post('3B',  # maximum=1,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:3b')
        lower.add_post('4',  # maximum=3,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:4')
        lower.add_post('5',  # maximum=3,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:5')
        lower.add_post('6',  # maximum=3,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:6')
        lower.add_post('7',  # maximum=3,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:7')
        lower.add_post('8',  # maximum=3,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:8')
        lower.add_post('9A',  # maximum=2,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:9a')
        lower.add_post('9B',  # maximum=1,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:9b')
        lower.add_post('10',  # maximum=3,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:10')
        lower.add_post('11',  # maximum=3,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:11')
        lower.add_post('12',  # maximum=3,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:12')
        lower.add_post('13',  # maximum=3,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:13')
        lower.add_post('14',  # maximum=3,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:14')
        lower.add_post('15',  # maximum=3,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:15')
        lower.add_post('16',  # maximum=3,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:16')
        lower.add_post('17',  # maximum=3,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:17')
        lower.add_post('18',  # maximum=3,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:18')
        lower.add_post('19',  # maximum=3,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:19')
        lower.add_post('20',  # maximum=3,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:20')
        lower.add_post('21',  # maximum=3,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:21')
        lower.add_post('22',  # maximum=3,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:22')
        lower.add_post('23A',  # maximum=1,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:23a')
        lower.add_post('23B',  # maximum=2,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:23b')
        lower.add_post('24',  # maximum=3,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:24')
        lower.add_post('25',  # maximum=3,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:25')
        lower.add_post('26',  # maximum=3,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:26')
        lower.add_post('27A',  # maximum=1,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:27a')
        lower.add_post('27B',  # maximum=1,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:27b')
        lower.add_post('27C',  # maximum=1,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:27c')
        lower.add_post('28',  # maximum=3,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:28')
        lower.add_post('29A',  # maximum=1,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:29a')
        lower.add_post('29B',  # maximum=1,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:29b')
        lower.add_post('29C',  # maximum=1,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:29c')
        lower.add_post('30A',  # maximum=2,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:30a')
        lower.add_post('30B',  # maximum=1,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:30b')
        lower.add_post('31A',  # maximum=1,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:31a')
        lower.add_post('31B',  # maximum=2,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:31b')
        lower.add_post('32',  # maximum=3,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:32')
        lower.add_post('33',  # maximum=3,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:33')
        lower.add_post('34A',  # maximum=2,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:34a')
        lower.add_post('34B',  # maximum=1,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:34b')
        lower.add_post('35A',  # maximum=1,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:35a')
        lower.add_post('35B',  # maximum=2,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:35b')
        lower.add_post('36',  # maximum=3,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:36')
        lower.add_post('37A',  # maximum=1,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:37a')
        lower.add_post('37B',  # maximum=2,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:37b')
        lower.add_post('38A',  # maximum=1,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:38a')
        lower.add_post('38B',  # maximum=1,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:38b')
        lower.add_post('38C',  # maximum=1,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:38c')
        lower.add_post('39',  # maximum=3,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:39')
        lower.add_post('40',  # maximum=3,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:40')
        lower.add_post('41',  # maximum=3,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:41')
        lower.add_post('42A',  # maximum=1,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:42a')
        lower.add_post('42B',  # maximum=2,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:42b')
        lower.add_post('43',  # maximum=3,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:43')
        lower.add_post('44A',  # maximum=1,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:44a')
        lower.add_post('44B',  # maximum=2,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:44b')
        lower.add_post('45',  # maximum=3,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:45')
        lower.add_post('46',  # maximum=3,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:46')
        lower.add_post('47A',  # maximum=2,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:47a')
        lower.add_post('47B',  # maximum=1,
                       role=lower_title, division_id='ocd-division/country:us/state:md/sldl:47b')

        yield Organization('Office of the Governor', classification='executive')
        yield legislature
        yield upper
        yield lower

    def get_session_list(self):
        return url_xpath(
            'http://mgaleg.maryland.gov/webmga/frmLegislation.aspx?pid=legisnpage&tab=subject3',
            '//select[contains(@name, "cboSession")]/option/text()')
