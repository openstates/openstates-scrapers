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

    baseFtpUrl    = 'ftp://landru.leg.state.or.us'

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
        measure_url = self._resolve_ftp_path(sessionYear, 'measures.txt')
        action_url = self._resolve_ftp_path(sessionYear, 'meashistory.txt')
        self.slug = self.metadata['session_details'][session]['slug']

        self.all_bills = {}
        slug = self.metadata['session_details'][session]['slug']

        # get the actual bills
        bill_data = self.urlopen(measure_url)
        # skip header row
        for line in bill_data.split("\n")[1:]:
            if line:
                self.parse_bill(session, chamber, line.strip())

        for bill_id, bill in self.all_bills.items():
            if bill is None:
                continue  # XXX: ...

            bid = bill_id.replace(" ", "")
            overview = self.create_url("Measures/Overview/{bill}", bid)
            # Right, let's do some versions.

            page = self.lxmlize(overview)
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

            c = lambda x: re.sub("\s+", " ", x).strip()

            title = c(measure_info['Bill Title'].text_content())
            summary = c(measure_info['Catchline/Summary'].text_content())
            bill['summary'] = summary

            for version in versions:
                name = version.text

                link = self.create_url(
                    'Downloads/MeasureDocument/{bill}/%s' % (name), bid)

                bill.add_version(name=name, url=link,
                                 mimetype='application/pdf')


            history = self.create_url('Measures/Overview/GetHistory/{bill}', bid)
            history = self.lxmlize(history).xpath("//table/tr")
            for entry in history:
                wwhere, action = [c(x.text_content()) for x in entry.xpath("*")]
                wwhere = re.match(
                    "(?P<when>.*) \((?P<where>.*)\)", wwhere).groupdict()

                chamber = {"S": "upper", "H": "lower"}[wwhere['where']]
                when = "%s-%s" % (slug[:4], wwhere['when'])
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

            bill.add_source(overview)
            self.save_bill(bill)


    def parse_bill(self, session, chamber, line):
        found = False
        found_thing = None
        splits = [u"\xe4", u"\ufffd", u"\u05d4"]
        for s in splits:
            info = line.split(s)
            if len(info) != 5:
                info = filter(lambda x: x != "", info)

            if len(info) == 5:
                found = True
                found_thing = info
                break

        if not found:
            raise Exception(info)

        info = found_thing

        (type, combined_id, number, title, relating_to) = info
        if ((type[0] == 'H' and chamber == 'lower') or
            (type[0] == 'S' and chamber == 'upper')):

            # basic bill info
            bill_id = "%s %s" % (type, number)
            # lookup type without chamber prefix
            bill_type = self.bill_types[type[1:]]

            # may encounter an ellipsis in the source data
            title = title.replace(u'\x85', '...')

            if title.strip() == "":
                self.all_bills[bill_id] = None
                return

            self.all_bills[bill_id] = Bill(session, chamber, bill_id, title,
                                            type=bill_type)

    def _resolve_ftp_path(self, sessionYear, filename):
        currentYear = dt.datetime.today().year
        currentTwoDigitYear = currentYear % 100
        sessionTwoDigitYear = sessionYear % 100
        if currentTwoDigitYear != sessionTwoDigitYear:
            filename = 'archive/%02d%s' % (sessionTwoDigitYear, filename)

        return "%s/pub/%s" % (self.baseFtpUrl, filename)
