import datetime as dt
import re

from openstates.utils import LXMLMixin
from pupa.scrape import Scraper, Bill, VoteEvent
from .apiclient import OregonLegislatorODataClient
from .utils import index_legislators, get_timezone


class ORBillScraper(Scraper, LXMLMixin):
    jurisdiction = 'or'
    tz = get_timezone()

    bill_directory_url = "https://olis.leg.state.or.us/liz/{0}/Measures/list/"
    base_url = "https://olis.leg.state.or.us"

    bill_types = {'B': 'bill',
                  'M': 'memorial',
                  'R': 'resolution',
                  'JM': 'joint memorial',
                  'JR': 'joint resolution',
                  'CR': 'concurrent resolution'}

    chamber_code = {'S': 'upper', 'H': 'lower'}

    action_classifiers = (
        ('.*Introduction and first reading.*',
         ['introduction', 'reading-1']),

        ('.*First reading.*', ['introduction', 'reading-1']),
        ('.*Second reading.*', ['reading-2']),
        ('.*Referred to .*', ['referral-committee']),
        ('.*Assigned to Subcommittee.*', ['referral-committee']),
        ('.*Recommendation: Do pass.*', ['committee-passage-favorable']),
        ('.*Governor signed.*', ['executive-signature']),
        ('.*Third reading.* Passed', ['passage', 'reading-3']),
        ('.*Third reading.* Failed', ['failure', 'reading-3']),
        ('.*President signed.*', ['passage']),
        ('.*Speaker signed.*', ['passage']),
        ('.*Final reading.* Adopted', ['passage']),
        ('.*Read third time .* Passed', ['passage', 'reading-3']),
        ('.*Read\. .* Adopted.*', ['passage']),
    )

    all_bills = {}

    def create_url(self, url, bill_id):
        return "https://olis.leg.state.or.us/liz/{session}/{url}".format(
            session=self.slug,
            url=url
        ).format(bill=bill_id)

    def latest_session(self):
        self.session = self.api_client.get('sessions')[-1]['SessionKey']

    def scrape(self, session=None):
        self.api_client = OregonLegislatorODataClient(self)
        self.session = session
        if not self.session:
            self.latest_session()

        yield from self.scrape_bills()

    def scrape_bills(self):
        measures_response = self.api_client.get('measures', page=100, session=self.session)

        legislators = index_legislators(self)

        for measure in measures_response:
            bid = '{} {}'.format(measure['MeasurePrefix'], measure['MeasureNumber'])

            chamber = self.chamber_code[bid[0]]
            bill = Bill(
                bid,
                legislative_session=self.session,
                chamber=chamber,
                title=measure['RelatingTo'],
                classification=self.bill_types[measure['MeasurePrefix'][1:]]
            )
            for sponsor in measure['MeasureSponsors']:
                legislator_code = sponsor['LegislatoreCode']  # typo in API
                if legislator_code:
                    bill.add_sponsorship(
                        name=legislators[legislator_code],
                        classification={'Chief': 'primary', 'Regular': 'cosponsor'}[
                            sponsor['SponsorLevel']],
                        entity_type='person',
                        primary=True if sponsor['SponsorLevel'] == 'Chief' else False
                    )

            bill.add_source(
                "https://olis.leg.state.or.us/liz/{session}/Measures/Overview/{bid}".format(
                    session=self.session, bid=bid)
            )
            for document in measure['MeasureDocuments']:
                bill.add_version_link(document['VersionDescription'], document['DocumentUrl'])
            for action in measure['MeasureHistoryActions']:
                classifiers = self.determine_action_classifiers(action['ActionText'])
                when = dt.datetime.strptime(action['ActionDate'], '%Y-%m-%dT%H:%M:%S')
                when = self.tz.localize(when)
                bill.add_action(action['ActionText'], when,
                                chamber=self.chamber_code[action['Chamber']],
                                classification=classifiers)

            yield bill

    def scrape_chamber_old(self, chamber, session):
        self.all_bills = {}
        self.slug = session

        page = self.lxmlize(self.bill_directory_url.format(self.slug.upper()))
        page.make_links_absolute(self.base_url)

        ulid = 'senateBills' if chamber == 'upper' else 'houseBills'  # id of <ul>
        header = page.xpath("//ul[@id='{0}_search']".format(ulid))[0]

        # Every ul with a data-load-action and an id
        bill_list_pages = header.xpath(".//ul[boolean(@data-load-action)"
                                       " and boolean(@id)]/@data-load-action")

        bill_anchors = []

        for bill_list_url in bill_list_pages:
            bill_list_page = self.lxmlize('{}{}'.format(self.base_url, bill_list_url))
            bill_list_page.make_links_absolute(self.base_url)
            bill_anchors.extend(bill_list_page.xpath('//a') or [])

        ws = re.compile(r"\s+")

        def _clean_ws(txt):
            """Remove extra whitespace from text."""
            return ws.sub(' ', txt).strip()

        for a in bill_anchors:
            bid = ws.sub('', a.text_content())
            # bill title is added below
            bill = Bill(bid, legislative_session=session, chamber=chamber,
                        title='', classification=self.bill_types[a])
            page = self.lxmlize(a.get('href'))
            versions = page.xpath('//ul[@class="dropdown-menu"]/li/span/' +
                                  'a[contains(@title, "Get the Pdf")]/@href')

            measure_info = {}
            info = page.xpath("//table[@id='measureOverviewTable']/tr")
            for row in info:
                key, value = row.xpath("./*")
                key = key.text.replace(':', '').strip()
                measure_info[key] = value

            for sponsor in measure_info['Chief Sponsors'].xpath("./a"):
                if sponsor.text_content().strip():
                    bill.add_sponsorship(name=sponsor.text_content(),
                                         classification='primary',
                                         entity_type='person',
                                         primary=True)

            for sponsor in measure_info['Regular Sponsors'].xpath("./a"):
                if sponsor.text_content().strip():
                    bill.add_sponsorship(name=sponsor.text_content(),
                                         classification='cosponsor',
                                         entity_type='person',
                                         primary=False)

            title = _clean_ws(measure_info['Bill Title'].text_content())
            # some bill titles need to be added manually
            if self.slug == "2013R1" and bid == "HB2010":
                title = ("Relating to Water Resources Department contested"
                         "case proceedings.")
            bill.title = title

            for version in versions:
                name = version.split("/")[-1]
                bill.add_version_link(name, version, media_type='application/pdf')

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

                types = self.determine_action_classifiers(action)

                bill.add_action(action, when, chamber=action_chamber, classification=types)

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

                yes_votes = len(votes["yes_votes"])
                no_votes = len(votes["no_votes"])
                other_votes = len(votes["other_votes"])
                passed = (float(yes_votes) / (yes_votes + no_votes) > 0.5)

                vote = VoteEvent(
                    start_date=when,
                    bill_chamber=chamber,
                    motion_text=action,
                    classification='passage',
                    result='pass' if passed else 'fail',
                    legislative_session=session,
                    bill=bid,
                    chamber=action_chamber
                )
                vote.set_count('yes', yes_votes)
                vote.set_count('no', no_votes)
                vote.set_count('other', other_votes)

                bill_url = "https://olis.leg.state.or.us/liz/" + \
                           "{0}/Measures/Overview/{1}".format(self.slug, bid)
                vote.add_source(bill_url)

                bill.add_vote_event(vote)

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
                bill.add_document_link(name, url=pdf_link,
                                       adopted=adopted,  # unsure
                                       media_type='application/pdf')

            bill.add_source(a.get('href'))
            yield bill

    def determine_action_classifiers(self, action):
        types = []
        for expr, types_ in self.action_classifiers:
            m = re.match(expr, action)
            if m:
                types += types_
        return types

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
