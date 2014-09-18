from billy.scrape.utils import convert_pdf
from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
from .utils import year_from_session

from collections import defaultdict
import datetime as dt
import os
import re
import lxml.html
import scrapelib



class ORBillScraper(BillScraper):
    jurisdiction = 'or'

    bill_directory_url = ("https://olis.leg.state.or.us/liz/{0}"
                          "/Navigation/BillNumberSearchForm")
    bill_types = {'B': 'bill',
                  'M': 'memorial',
                  'R': 'resolution',
                  'JM': 'joint memorial',
                  'JR': 'joint resolution',
                  'CR': 'concurrent resolution'}

    action_classifiers = (
        ('.*Introduction and first reading.*',
             ['bill:introduced', 'bill:reading:1']),

        ('.*First reading.*', ['bill:introduced', 'bill:reading:1']),
        ('.*Second reading.*', ['bill:reading:2']),
        ('.*Referred to .*', ['committee:referred']),
        ('.*Assigned to Subcommittee.*', ['committee:referred']),
        ('.*Recommendation: Do pass.*', ['committee:passed:favorable']),
        ('.*Governor signed.*', ['governor:signed']),
        ('.*Third reading.* Passed', ['bill:passed', 'bill:reading:3']),
        ('.*Third reading.* Failed', ['bill:failed', 'bill:reading:3']),
        ('.*President signed.*', ['bill:passed']),
        ('.*Speaker signed.*', ['bill:passed']),
        ('.*Final reading.* Adopted', ['bill:passed']),
        ('.*Read third time .* Passed', ['bill:passed', 'bill:reading:3']),
        ('.*Read\. .* Adopted.*', ['bill:passed']),
    )

    all_bills = {}

    def lxmlize(self, url):
        page = self.urlopen(url)
        page = lxml.html.fromstring(page)
        page.make_links_absolute(url)
        return page

    def create_url(self, url, bill_id):
        return "https://olis.leg.state.or.us/liz/{session}/{url}".format(
            session=self.slug,
            url=url
        ).format(bill=bill_id)

    def scrape(self, chamber, session):
        sessionYear = year_from_session(session)

        self.all_bills = {}
        self.slug = self.metadata['session_details'][session]['slug']

        page = self.lxmlize(self.bill_directory_url.format(self.slug.upper()))
        ulid = 'senateBills' if chamber == 'upper' else 'houseBills'  # id of <ul>
        bill_list = page.xpath("//ul[@id='{0}']".format(ulid))[0]
        bill_anchors = bill_list.xpath(".//a[boolean(@title)]")

        ws = re.compile(r"\s+")
        def _clean_ws(txt):
            """Remove extra whitespace from text."""
            return ws.sub(' ', txt).strip()

        for a in bill_anchors:
            bid = ws.sub('', a.text_content())  # bill id
            bill_summary = _clean_ws(a.get('title'))
            # bill title is added below
            bill = Bill(session, chamber, bid, title='', summary=bill_summary)

            page = self.lxmlize(a.get('href'))
            versions = page.xpath(
                "//ul[@class='dropdown-menu']/li/a[contains(@href, 'Text')]")

            measure_info = {}
            info = page.xpath("//table[@id='measureOverviewTable']/tr")
            for row in info:
                key, value = row.xpath("./*")
                key = key.text.strip(": ")
                measure_info[key] = value

            for sponsor in measure_info['Chief Sponsors'].xpath("./a"):
                bill.add_sponsor(type='primary', name=sponsor.text_content())

            for sponsor in measure_info['Regular Sponsors'].xpath("./a"):
                bill.add_sponsor(type='cosponsor', name=sponsor.text_content())


            bill['title'] = _clean_ws(measure_info['Bill Title'].text_content())

            for version in versions:
                name = version.text

                link = self.create_url(
                    'Downloads/MeasureDocument/{bill}/%s' % (name), bid)

                bill.add_version(name=name, url=link,
                                 mimetype='application/pdf')


            history = self.create_url('Measures/Overview/GetHistory/{bill}', bid)
            history = self.lxmlize(history).xpath("//table/tr")
            for entry in history:
                wwhere, action = [_clean_ws(x.text_content())
                                  for x in entry.xpath("*")]
                wwhere = re.match(
                    "(?P<when>.*) \((?P<where>.*)\)", wwhere).groupdict()

                chamber = {"S": "upper", "H": "lower"}[wwhere['where']]
                when = "%s-%s" % (self.slug[:4], wwhere['when'])
                when = dt.datetime.strptime(when, "%Y-%m-%d")

                types = []
                for expr, types_ in self.action_classifiers:
                    m = re.match(expr, action)
                    if m:
                        types += types_

                if types == []:
                    types = ['other']

                #if types == ['other']:
                #    print(action)

                # actor, action, date, type, committees, legislators
                bill.add_action(chamber, action, when, type=types)

            amendments = self.create_url(
                'Measures/ProposedAmendments/{bill}', bid)
            amendments = self.lxmlize(amendments).xpath(
                "//div[@id='amendments']/table//tr")

            for amendment in amendments:
                nodes = amendment.xpath("./td")

                if nodes == []:
                    continue

                pdf_href, date, committee, adopted = nodes
                pdf_href, = pdf_href.xpath("./a")
                pdf_link = pdf_href.attrib['href']

                name = "Ammendment %s" % (pdf_href.text_content())

                adopted = adopted.text
                bill.add_document(name=name, url=pdf_link,
                                  adopted=adopted,
                                  mimetype='application/pdf')

            bill.add_source(a.get('href'))
            self.save_bill(bill)

