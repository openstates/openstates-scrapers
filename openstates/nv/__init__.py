from utils.lxmlize import url_xpath
from .utils import text_after_line_numbers, pdfdata_to_text

from pupa.scrape import Jurisdiction, Organization
# from .people import NVPeopleScraper
# from .committees import NVCommitteeScraper
from .bills import NVBillScraper
# from .events import NVEventScraper


class Nevada(Jurisdiction):
    division_id = "ocd-division/country:us/state:nv"
    classification = "government"
    name = "Nevada"
    url = "http://www.leg.state.nv.us/"
    scrapers = {
        # 'people': NVPeopleScraper,
        # 'committees': NVCommitteeScraper,
        'bills': NVBillScraper,
        # 'events': NVEventScraper,
    }
    legislative_sessions = [
        {
            "_scraped_name": "26th (2010) Special Session",
            "classification": "special",
            "identifier": "2010Special26",
            "name": "26th Special Session (2010)"
        },
        {
            "_scraped_name": "27th (2013) Special Session",
            "classification": "special",
            "identifier": "2013Special27",
            "name": "27th Special Session (2013)"
        },
        {
            "_scraped_name": "28th (2014) Special Session",
            "classification": "special",
            "identifier": "2014Special28",
            "name": "28th Special Session (2014)"
        },
        {
            "_scraped_name": "29th (2015) Special Session",
            "classification": "special",
            "end_date": "2015-12-19",
            "identifier": "2015Special29",
            "name": "29th Special Session (2015)",
            "start_date": "2015-12-16"
        },
        {
            "_scraped_name": "30th (2016) Special Session",
            "classification": "special",
            "end_date": "2016-10-14",
            "identifier": "2016Special30",
            "name": "30th Special Session (2016)",
            "start_date": "2016-10-10"
        },
        {
            "_scraped_name": "75th (2009) Session",
            "classification": "primary",
            "identifier": "75",
            "name": "2009 Regular Session"
        },
        {
            "_scraped_name": "76th (2011) Session",
            "classification": "primary",
            "identifier": "76",
            "name": "2011 Regular Session"
        },
        {
            "_scraped_name": "77th (2013) Session",
            "classification": "primary",
            "identifier": "77",
            "name": "2013 Regular Session"
        },
        {
            "_scraped_name": "78th (2015) Session",
            "classification": "primary",
            "end_date": "2015-06-01",
            "identifier": "78",
            "name": "2015 Regular Session",
            "start_date": "2015-02-15"
        },
        {
            "_scraped_name": "79th (2017) Session",
            "classification": "primary",
            "end_date": "2017-06-06",
            "identifier": "79",
            "name": "2017 Regular Session",
            "start_date": "2017-02-06"
        },
        # {
        #     "_scraped_name": "80th (2019) Session",
        #     "classification": "primary",
        #     "identifier": "80",
        #     "name": "2019 Regular Session",
        #     "start_date": "2019-02-04"
        # },
    ]
    ignored_scraped_sessions = [
        "80th (2019) Session",
        "25th (2008) Special Session",
        "24th (2008) Special Session",
        "23rd (2007) Special Session",
        "74th (2007) Session",
        "22nd (2005) Special Session",
        "73rd (2005) Session",
        "21st (2004) Special Session",
        "20th (2003) Special Session",
        "19th (2003) Special Session",
        "72nd (2003) Session",
        "18th (2002) Special Session",
        "17th (2001) Special Session",
        "71st (2001) Session",
        "70th (1999) Session",
        "69th (1997) Session",
        "68th (1995) Session",
        "67th (1993) Session",
        "66th (1991) Session",
        "16th (1989) Special Session",
        "65th (1989) Session",
        "64th (1987) Session",
        "63rd (1985) Session"
    ]

    def get_organizations(self):
        legislature_name = "Nevada Legislature"
        lower_chamber_name = "Assembly"
        lower_seats = 42
        lower_title = "Assembly Member"
        upper_chamber_name = "Senate"
        upper_seats = 21
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
        for n in range(1, lower_seats + 1):
            lower.add_post(
                label=str(n), role=lower_title,
                division_id='{}/sldl:{}'.format(self.division_id, n))

        yield Organization('Office of the Governor', classification='executive')
        yield legislature
        yield upper
        yield lower

    def get_session_list(self):
        return url_xpath(
            'https://www.leg.state.nv.us/Session/',
            '//div[contains(@class, "list-group-item-heading")]/text()')

    def get_extract_text(self, doc, data):
        return text_after_line_numbers(pdfdata_to_text(data))

    session_slugs = {
        "2010Special26": "26th2010Special",
        "2013Special27": "27th2013Special",
        "2014Special28": "28th2014Special",
        "2015Special29": "29th2015Special",
        "2016Special30": "30th2016Special",
        "75": "75th2009",
        "76": "76th2011",
        "77": "77th2013",
        "78": "78th2015",
        "79": "79th2017",
        "80": "80th2019",
    }
