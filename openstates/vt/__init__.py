from pupa.scrape import Jurisdiction, Organization
from openstates.utils import url_xpath
# from .people import VTPersonScraper
# from .committees import VTCommitteeScraper
from .bills import VTBillScraper
from .events import VTEventScraper


# As of March 2018, Vermont appears to be throttling hits
# to its website. After a week of production failures, we
# tried rate-limiting our requests, and the errors went away
# (Reminder: Pupa default is 60 RPM)
# This limit might also be possible to remove once we switch to
# the official API for bills:
# https://github.com/openstates/openstates/issues/2196
settings = dict(
    SCRAPELIB_RPM=20
)


class Vermont(Jurisdiction):
    division_id = "ocd-division/country:us/state:vt"
    classification = "government"
    name = "Vermont"
    url = "http://legislature.vermont.gov/"
    scrapers = {
        # 'people': VTPersonScraper,
        # 'committees': VTCommitteeScraper,
        'bills': VTBillScraper,
        'events': VTEventScraper
    }
    legislative_sessions = [
        {
            "_scraped_name": "2009-2010 Session",
            "classification": "primary",
            "identifier": "2009-2010",
            "name": "2009-2010 Regular Session"
        },
        {
            "_scraped_name": "2011-2012 Session",
            "classification": "primary",
            "identifier": "2011-2012",
            "name": "2011-2012 Regular Session"
        },
        {
            "_scraped_name": "2013-2014 Session",
            "classification": "primary",
            "identifier": "2013-2014",
            "name": "2013-2014 Regular Session"
        },
        {
            "_scraped_name": "2015-2016 Session",
            "classification": "primary",
            "identifier": "2015-2016",
            "name": "2015-2016 Regular Session"
        },
        {
            "_scraped_name": "2017-2018 Session",
            "classification": "primary",
            "identifier": "2017-2018",
            "name": "2017-2018 Regular Session",
            "start_date": "2017-01-04",
            "end_date": "2018-05-12",
        },
        {
            "_scraped_name": "2018 Special Session",
            "classification": "special",
            "identifier": "2018ss1",
            "name": "2018 Special Session",
            "start_date": "2018-05-22",
        }
    ]
    ignored_scraped_sessions = [
        "2009 Special Session",
    ]

    site_ids = {
        '2018ss1': '2018.1',
    }

    def get_year_slug(self, session):
        return self.site_ids.get(session, session[5:])

    def get_organizations(self):
        legislature_name = "Vermont General Assembly"
        lower_chamber_name = "House"
        lower_title = "Representative"
        upper_title = "Senator"

        legislature = Organization(name=legislature_name,
                                   classification="legislature")
        governor = Organization(name='Office of the Governor', classification='executive')
        upper = Organization('Senate', classification='upper',
                             parent_id=legislature._id)
        lower = Organization(lower_chamber_name, classification='lower',
                             parent_id=legislature._id)

        lower.add_post(label='Addison-1',    # maximum=2,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:addison-1')
        lower.add_post(label='Addison-2',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:addison-2')
        lower.add_post(label='Addison-3',    # maximum=2,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:addison-3')
        lower.add_post(label='Addison-4',    # maximum=2,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:addison-4')
        lower.add_post(label='Addison-5',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:addison-5')
        lower.add_post(label='Addison-Rutland',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:addison-rutland')
        lower.add_post(label='Bennington-1',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:bennington-1')
        lower.add_post(label='Bennington-2-1',    # maximum=2,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:bennington-2-1')
        lower.add_post(label='Bennington-2-2',    # maximum=2,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:bennington-2-2')
        lower.add_post(label='Bennington-3',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:bennington-3')
        lower.add_post(label='Bennington-4',    # maximum=2,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:bennington-4')
        lower.add_post(label='Bennington-Rutland',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:bennington-rutland')
        lower.add_post(label='Caledonia-1',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:caledonia-1')
        lower.add_post(label='Caledonia-2',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:caledonia-2')
        lower.add_post(label='Caledonia-3',    # maximum=2,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:caledonia-3')
        lower.add_post(label='Caledonia-4',    # maximum=2,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:caledonia-4')
        lower.add_post(label='Caledonia-Washington',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:caledonia-washington')
        lower.add_post(label='Chittenden-10',    # maximum=2,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:chittenden-10')
        lower.add_post(label='Chittenden-1',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:chittenden-1')
        lower.add_post(label='Chittenden-2',    # maximum=2,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:chittenden-2')
        lower.add_post(label='Chittenden-3',    # maximum=2,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:chittenden-3')
        lower.add_post(label='Chittenden-4-1',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:chittenden-4-1')
        lower.add_post(label='Chittenden-4-2',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:chittenden-4-2')
        lower.add_post(label='Chittenden-5-1',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:chittenden-5-1')
        lower.add_post(label='Chittenden-5-2',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:chittenden-5-2')
        lower.add_post(label='Chittenden-6-1',    # maximum=2,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:chittenden-6-1')
        lower.add_post(label='Chittenden-6-2',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:chittenden-6-2')
        lower.add_post(label='Chittenden-6-3',    # maximum=2,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:chittenden-6-3')
        lower.add_post(label='Chittenden-6-4',    # maximum=2,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:chittenden-6-4')
        lower.add_post(label='Chittenden-6-5',    # maximum=2,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:chittenden-6-5')
        lower.add_post(label='Chittenden-6-6',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:chittenden-6-6')
        lower.add_post(label='Chittenden-6-7',    # maximum=2,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:chittenden-6-7')
        lower.add_post(label='Chittenden-7-1',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:chittenden-7-1')
        lower.add_post(label='Chittenden-7-2',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:chittenden-7-2')
        lower.add_post(label='Chittenden-7-3',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:chittenden-7-3')
        lower.add_post(label='Chittenden-7-4',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:chittenden-7-4')
        lower.add_post(label='Chittenden-8-1',    # maximum=2,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:chittenden-8-1')
        lower.add_post(label='Chittenden-8-2',    # maximum=2,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:chittenden-8-2')
        lower.add_post(label='Chittenden-8-3',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:chittenden-8-3')
        lower.add_post(label='Chittenden-9-1',    # maximum=2,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:chittenden-9-1')
        lower.add_post(label='Chittenden-9-2',    # maximum=2,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:chittenden-9-2')
        lower.add_post(label='Essex-Caledonia',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:essex-caledonia')
        lower.add_post(label='Essex-Caledonia-Orleans',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:essex-caledonia-orleans')
        lower.add_post(label='Franklin-1',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:franklin-1')
        lower.add_post(label='Franklin-2',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:franklin-2')
        lower.add_post(label='Franklin-3-1',    # maximum=2,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:franklin-3-1')
        lower.add_post(label='Franklin-3-2',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:franklin-3-2')
        lower.add_post(label='Franklin-4',    # maximum=2,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:franklin-4')
        lower.add_post(label='Franklin-5',    # maximum=2,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:franklin-5')
        lower.add_post(label='Franklin-6',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:franklin-6')
        lower.add_post(label='Franklin-7',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:franklin-7')
        lower.add_post(label='Grand Isle-Chittenden',    # maximum=2,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:grand_isle-chittenden')
        lower.add_post(label='Lamoille-1',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:lamoille-1')
        lower.add_post(label='Lamoille-2',    # maximum=2,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:lamoille-2')
        lower.add_post(label='Lamoille-3',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:lamoille-3')
        lower.add_post(label='Lamoille-Washington',    # maximum=2,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:lamoille-washington')
        lower.add_post(label='Orange-1',    # maximum=2,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:orange-1')
        lower.add_post(label='Orange-2',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:orange-2')
        lower.add_post(label='Orange-Caledonia',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:orange-caledonia')
        lower.add_post(
            label='Orange-Washington-Addison',    # maximum=2,
            role=lower_title,
            division_id='ocd-division/country:us/state:vt/sldl:orange-washington-addison')
        lower.add_post(label='Orleans-1',    # maximum=2,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:orleans-1')
        lower.add_post(label='Orleans-2',    # maximum=2,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:orleans-2')
        lower.add_post(label='Orleans-Caledonia',    # maximum=2,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:orleans-caledonia')
        lower.add_post(label='Orleans-Lamoille',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:orleans-lamoille')
        lower.add_post(label='Rutland-1',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:rutland-1')
        lower.add_post(label='Rutland-2',    # maximum=2,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:rutland-2')
        lower.add_post(label='Rutland-3',    # maximum=2,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:rutland-3')
        lower.add_post(label='Rutland-4',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:rutland-4')
        lower.add_post(label='Rutland-5-1',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:rutland-5-1')
        lower.add_post(label='Rutland-5-2',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:rutland-5-2')
        lower.add_post(label='Rutland-5-3',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:rutland-5-3')
        lower.add_post(label='Rutland-5-4',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:rutland-5-4')
        lower.add_post(label='Rutland-6',    # maximum=2,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:rutland-6')
        lower.add_post(label='Rutland-Bennington',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:rutland-bennington')
        lower.add_post(label='Rutland-Windsor-1',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:rutland-windsor-1')
        lower.add_post(label='Rutland-Windsor-2',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:rutland-windsor-2')
        lower.add_post(label='Washington-1',    # maximum=2,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:washington-1')
        lower.add_post(label='Washington-2',    # maximum=2,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:washington-2')
        lower.add_post(label='Washington-3',    # maximum=2,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:washington-3')
        lower.add_post(label='Washington-4',    # maximum=2,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:washington-4')
        lower.add_post(label='Washington-5',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:washington-5')
        lower.add_post(label='Washington-6',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:washington-6')
        lower.add_post(label='Washington-7',    # maximum=2,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:washington-7')
        lower.add_post(label='Washington-Chittenden',    # maximum=2,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:washington-chittenden')
        lower.add_post(label='Windham-1',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:windham-1')
        lower.add_post(label='Windham-2-1',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:windham-2-1')
        lower.add_post(label='Windham-2-2',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:windham-2-2')
        lower.add_post(label='Windham-2-3',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:windham-2-3')
        lower.add_post(label='Windham-3',    # maximum=2,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:windham-3')
        lower.add_post(label='Windham-4',    # maximum=2,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:windham-4')
        lower.add_post(label='Windham-5',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:windham-5')
        lower.add_post(label='Windham-6',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:windham-6')
        lower.add_post(label='Windham-Bennington',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:windham-bennington')
        lower.add_post(
            label='Windham-Bennington-Windsor',    # maximum=1,
            role=lower_title,
            division_id='ocd-division/country:us/state:vt/sldl:windham-bennington-windsor')
        lower.add_post(label='Windsor-1',    # maximum=2,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:windsor-1')
        lower.add_post(label='Windsor-2',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:windsor-2')
        lower.add_post(label='Windsor-3-1',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:windsor-3-1')
        lower.add_post(label='Windsor-3-2',    # maximum=2,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:windsor-3-2')
        lower.add_post(label='Windsor-4-1',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:windsor-4-1')
        lower.add_post(label='Windsor-4-2',    # maximum=2,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:windsor-4-2')
        lower.add_post(label='Windsor-5',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:windsor-5')
        lower.add_post(label='Windsor-Orange-1',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:windsor-orange-1')
        lower.add_post(label='Windsor-Orange-2',    # maximum=2,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:windsor-orange-2')
        lower.add_post(label='Windsor-Rutland',    # maximum=1,
                       role=lower_title,
                       division_id='ocd-division/country:us/state:vt/sldl:windsor-rutland')
        upper.add_post(label='Addison',    # maximum=2,
                       role=upper_title,
                       division_id='ocd-division/country:us/state:vt/sldu:addison')
        upper.add_post(label='Bennington',    # maximum=2,
                       role=upper_title,
                       division_id='ocd-division/country:us/state:vt/sldu:bennington')
        upper.add_post(label='Caledonia',    # maximum=2,
                       role=upper_title,
                       division_id='ocd-division/country:us/state:vt/sldu:caledonia')
        upper.add_post(label='Chittenden',    # maximum=6,
                       role=upper_title,
                       division_id='ocd-division/country:us/state:vt/sldu:chittenden')
        upper.add_post(label='Essex-Orleans',    # maximum=2,
                       role=upper_title,
                       division_id='ocd-division/country:us/state:vt/sldu:essex-orleans')
        upper.add_post(label='Franklin',    # maximum=2,
                       role=upper_title,
                       division_id='ocd-division/country:us/state:vt/sldu:franklin')
        upper.add_post(label='Chittenden-Grand Isle',    # maximum=1,
                       role=upper_title,
                       division_id='ocd-division/country:us/state:vt/sldu:grand_isle-chittenden')
        upper.add_post(label='Lamoille',    # maximum=1,
                       role=upper_title,
                       division_id='ocd-division/country:us/state:vt/sldu:lamoille')
        upper.add_post(label='Orange',    # maximum=1,
                       role=upper_title,
                       division_id='ocd-division/country:us/state:vt/sldu:orange')
        upper.add_post(label='Rutland',    # maximum=3,
                       role=upper_title,
                       division_id='ocd-division/country:us/state:vt/sldu:rutland')
        upper.add_post(label='Washington',    # maximum=3,
                       role=upper_title,
                       division_id='ocd-division/country:us/state:vt/sldu:washington')
        upper.add_post(label='Windham',    # maximum=2,
                       role=upper_title,
                       division_id='ocd-division/country:us/state:vt/sldu:windham')
        upper.add_post(label='Windsor',    # maximum=3,
                       role=upper_title,
                       division_id='ocd-division/country:us/state:vt/sldu:windsor')

        yield legislature
        yield governor
        yield upper
        yield lower

    def get_session_list(self):
        return url_xpath(
                'http://legislature.vermont.gov/bill/search/2016',
                '//fieldset/div[@id="selected_session"]/div/select/option/text()')
