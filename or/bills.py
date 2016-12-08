from billy.scrape.bills import BillScraper, Bill
from billy.scrape.votes import Vote
from openstates.utils import LXMLMixin

import datetime as dt
import re
import lxml.html


class ORBillScraper(BillScraper, LXMLMixin):
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

    def create_url(self, url, bill_id):
        return "https://olis.leg.state.or.us/liz/{session}/{url}".format(
            session=self.slug,
            url=url
        ).format(bill=bill_id)

    def scrape(self, chamber, session):
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
            versions = page.xpath('//ul[@class="dropdown-menu"]/li/span/' +
                    'a[contains(@title, "Get the Pdf")]/@href')

            measure_info = {}
            info = page.xpath("//table[@id='measureOverviewTable']/tr")
            for row in info:
                key, value = row.xpath("./*")
                key = key.text.strip(": ")
                measure_info[key] = value

            for sponsor in measure_info['Chief Sponsors'].xpath("./a"):
                if sponsor.text_content().strip():
                    bill.add_sponsor(
                            type='primary', name=sponsor.text_content())

            for sponsor in measure_info['Regular Sponsors'].xpath("./a"):
                if sponsor.text_content().strip():
                    bill.add_sponsor(
                            type='cosponsor', name=sponsor.text_content())

            title = _clean_ws(measure_info['Bill Title'].text_content())
            # some bill titles need to be added manually
            if self.slug == "2013R1" and bid == "HB2010":
                title = ("Relating to Water Resources Department contested"
                         "case proceedings.")
            bill['title'] = title

            for version in versions:
                name = version.split("/")[-1]
                bill.add_version(name=name, url=version,
                                 mimetype='application/pdf')

            history_url = self.create_url('Measures/Overview/GetHistory/{bill}', bid)
            history = self.lxmlize(history_url).xpath("//table/tr")
            for entry in history:
                wwhere, action = [_clean_ws(x.text_content())
                                  for x in entry.xpath("*")]
                vote_cleaning_re = r'(.*?)((Ayes)|(Nays),\s.*)'
                if re.match(vote_cleaning_re, action):
                    action = re.search(vote_cleaning_re, action).groups()[0]
                wwhere = re.match(
                    r"(?P<when>.*) \((?P<where>.*)\)", wwhere).groupdict()

                action_chamber = {"S": "upper", "H": "lower"}[wwhere['where']]
                when = "%s-%s" % (self.slug[:4], wwhere['when'])
                when = dt.datetime.strptime(when, "%Y-%m-%d")

                types = []
                for expr, types_ in self.action_classifiers:
                    m = re.match(expr, action)
                    if m:
                        types += types_

                if types == []:
                    types = ['other']

                # actor, action, date, type, committees, legislators
                bill.add_action(action_chamber, action, when, type=types)

                # Parse and store Vote information
                vote_id = entry.xpath('./td/a[contains(@href, "otes-")]/@href')
                if not vote_id:
                    continue
                elif "#measureVotes-" in vote_id[0]:
                    vote_id = vote_id[0].split("-")[-1]
                    vote_url = "https://olis.leg.state.or.us/liz/" + \
                            "{0}/Measures/MeasureVotes?id={1}". \
                            format(self.slug, vote_id)
                else:
                    vote_id = vote_id[0].split("-")[-1]
                    vote_url = "https://olis.leg.state.or.us/liz/" + \
                            "{0}/CommitteeReports/MajorityReport/{1}". \
                            format(self.slug, vote_id)

                votes = self._get_votes(vote_url)
                if not any(len(x) for x in votes.values()):
                    self.warning("The votes webpage was empty for " +
                            "action {0} on bill {1}.".format(action, bid))
                    continue

                passed = (
                        float(len(votes["yes_votes"])) /
                        (len(votes["yes_votes"]) + len(votes["no_votes"]))
                        > 0.5
                        )

                vote = Vote(
                        chamber=chamber,
                        date=when,
                        motion=action,
                        passed=passed,
                        yes_count=len(votes["yes_votes"]),
                        no_count=len(votes["no_votes"]),
                        other_count=len(votes["other_votes"]),

                        session=session,
                        bill_id=bid,
                        bill_chamber=action_chamber
                        )

                vote.update(votes)
                bill_url = "https://olis.leg.state.or.us/liz/" + \
                        "{0}/Measures/Overview/{1}".format(self.slug, bid)
                vote.add_source(bill_url)

                bill.add_vote(vote)

            amendments_url = self.create_url(
                    'Measures/ProposedAmendments/{bill}', bid)
            amendments = self.lxmlize(amendments_url).xpath(
                    "//div[@id='amendments']/table//tr")

            for amendment in amendments:
                nodes = amendment.xpath("./td")

                if nodes == []:
                    continue

                pdf_href, date, committee, adopted, when = nodes
                pdf_href, = pdf_href.xpath("./a")
                pdf_link = pdf_href.attrib['href']

                name = "Ammendment %s" % (pdf_href.text_content())

                adopted = adopted.text
                bill.add_document(name=name, url=pdf_link,
                                  adopted=adopted,
                                  mimetype='application/pdf')

            bill.add_source(a.get('href'))
            self.save_bill(bill)

    def _get_votes(self, vote_url):
        # Load the vote list page
        vote_info = self.lxmlize(vote_url)
        if any("Committee Vote" in x for
                x in self.lxmlize(vote_url).xpath('//text()')):
            vote_info = vote_info.xpath('./tbody/tr[4]/td/div')
            member_xpath = './div[1]/text()'
            vote_xpath = './div[2]/text()'
        else:
            vote_info = self.lxmlize(vote_url).xpath('./ul/li')
            member_xpath = './span[1]/text()'
            vote_xpath = './span[2]/text()'

        VOTE_CATEGORIES = {
                "Aye": "yes",
                "Nay": "no",
                "Exc": "other",
                "Abs": "other"
                }
        votes = {}

        # Initialize the vote lists and counts
        for category in VOTE_CATEGORIES.values():
            votes["{}_votes".format(category)] = []

        for category in VOTE_CATEGORIES.keys():
            # Collect the Aye/Nay/Excused/Absent names
            for vote_cast in vote_info:
                if vote_cast.xpath(vote_xpath)[0].startswith(category):
                    votes["{}_votes".format(VOTE_CATEGORIES[category])]. \
                            append(vote_cast.xpath(member_xpath)[0])

        return votes
