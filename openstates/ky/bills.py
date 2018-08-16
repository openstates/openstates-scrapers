import re
import datetime
from collections import defaultdict
import lxml.html
from pytz import timezone

from pupa.scrape import Scraper, Bill
from openstates.utils import LXMLMixin


def chamber_abbr(chamber):
    if chamber == 'upper':
        return 'S'
    else:
        return 'H'


def session_url(session):
    return "http://www.lrc.ky.gov/record/%s/" % session[2:]


class KYBillScraper(Scraper, LXMLMixin):

    _subjects = defaultdict(list)
    _is_post_2016 = False

    def scrape_subjects(self, session):
        if self._subjects:
            return

        url = session_url(session) + 'indexhd.htm'
        page = self.lxmlize(url)

        for subj_link in page.xpath('//a[contains(@href, ".htm")]/@href'):
            # subject links are 4 numbers
            if re.match('\d{4}', subj_link):
                subj_html = self.get(session_url(session) + subj_link).text
                sdoc = lxml.html.fromstring(subj_html)
                subject = sdoc.xpath('//p[@class="PageHeader"]/text()')[0]
                for bill in sdoc.xpath('//div[@id="bul"]/a/text()'):
                    self._subjects[bill.replace(' ', '')].append(subject)

    def scrape(self, session=None, chamber=None, prefile=None):
        if not session:
            session = self.latest_session()
            self.info('no session specified, using %s', session)
        # Bill page markup changed starting with the 2016 regular session.
        # kinda gross
        if int(session[0:4]) >= 2016:
            self._is_post_2016 = True

        chambers = [chamber] if chamber else ['upper', 'lower']

        # KY lists prefiles on a seperate page
        # So enable them via CLI arg, eg:
        # pupa update ky bills --scrape prefile=True session=2019RS
        # make sure to set the session explicitly if you do this.
        if prefile:
            for chamber in chambers:
                yield from self.scrape_session(chamber, session, prefile)
        else:
            self.scrape_subjects(session)
            for chamber in chambers:
                yield from self.scrape_session(chamber, session, prefile)

    def scrape_session(self, chamber, session, prefile=None):
        if prefile:
            yield from self.scrape_prefile_list(chamber, session)
        else:
            bill_url = session_url(session) + \
                "bills_%s.htm" % chamber_abbr(chamber)
            yield from self.scrape_bill_list(chamber, session, bill_url)

            resolution_url = session_url(session) + "res_%s.htm" % (
                chamber_abbr(chamber))
            yield from self.scrape_bill_list(chamber, session, resolution_url)

    def scrape_bill_list(self, chamber, session, url, prefile=None):
        bill_abbr = None
        page = self.lxmlize(url)

        for link in page.xpath("//a"):
            if re.search(r"\d{1,4}\.htm", link.attrib.get('href', '')):
                bill_id = link.text

                match = re.match(r'([A-Z]+)\s+\d+', link.text)
                if match:
                    bill_abbr = match.group(1)
                    bill_id = bill_id.replace(' ', '')
                else:
                    bill_id = bill_abbr + bill_id

                yield from self.parse_bill(chamber, session, bill_id, link.attrib['href'], prefile)

    def scrape_prefile_list(self, chamber, session):
        # convert 2019RS to 19RS
        abbr = session.replace('20', '')

        bill_url = 'http://www.lrc.ky.gov/record/{}/prefiled/prefiled_bills.htm'.format(
            abbr)
        if 'upper' == chamber:
            bill_url = 'http://www.lrc.ky.gov/record/{}/prefiled/prefiled_sponsor_senate.htm' \
                .format(abbr)
        elif 'lower' == chamber:
            bill_url = 'http://www.lrc.ky.gov/record/{}/prefiled/prefiled_sponsor_house.htm' \
                .format(abbr)

        yield from self.scrape_bill_list(chamber, session, bill_url, prefile=True)

    def parse_bill(self, chamber, session, bill_id, url, prefile=None):
        page = self.lxmlize(url)

        short_bill_id = re.sub(r'(H|S)([JC])R', r'\1\2', bill_id)
        version_link_node = self.get_node(
            page,
            '//a[contains(@href, "{bill_id}/bill.doc") or contains(@href,'
            '"{bill_id}/bill.pdf")]'.format(bill_id=short_bill_id))

        if version_link_node is None:
            # Bill withdrawn
            if prefile:
                source_url = None
            else:
                self.logger.warning('Bill withdrawn.')
                return

        else:
            source_url = version_link_node.attrib['href']

            if source_url.endswith('.doc'):
                mimetype = 'application/msword'
            elif source_url.endswith('.pdf'):
                mimetype = 'application/pdf'

        if self._is_post_2016:
            title_texts = self.get_nodes(
                page,
                '//div[@class="StandardText leftDivMargin"]/text()')
            title_texts = list(
                filter(None, [text.strip() for text in title_texts]))
            title_texts = [s for s in title_texts if s !=
                           ',' and not s.startswith('(BR ')]
            title = ' '.join(title_texts)

            # strip opening '- ' which occurs on some bills
            if title.startswith('- '):
                title = title[len('- '):]

            actions = self.get_nodes(
                page,
                '//div[@class="StandardText leftDivMargin"]/'
                'div[@class="StandardText"][last()]//text()[normalize-space()]')
        else:
            pars = version_link_node.xpath("following-sibling::p")

            if len(pars) == 2:
                title = pars[0].xpath("string()")
                action_p = pars[1]
            else:
                title = pars[0].getprevious().tail
                if not title:
                    self.warning(
                        'walking backwards to get bill title, error prone!')
                    title = pars[0].getprevious().getprevious()
                    while not title.tail:
                        title = title.getprevious()
                    title = title.tail
                    self.warning('got title the dangerous way: %s' % title)
                action_p = pars[0]

            title = re.sub(r'[\s\xa0]+', ' ', title).strip()
            actions = action_p.xpath("string()").split("\n")

        if 'CR' in bill_id:
            bill_type = 'concurrent resolution'
        elif 'JR' in bill_id:
            bill_type = 'joint resolution'
        elif 'R' in bill_id:
            bill_type = 'resolution'
        else:
            bill_type = 'bill'

        bill = Bill(bill_id, legislative_session=session, chamber=chamber,
                    title=title, classification=bill_type)
        bill.subject = self._subjects[bill_id]
        bill.add_source(url)

        if source_url:
            bill.add_version_link("Most Recent Version",
                                  source_url, media_type=mimetype)

        other_versions = page.xpath('//a[contains(@href, "/recorddocuments/bill/") and'
                                    ' not(contains(@href, "/bill.pdf")) and'
                                    ' not(contains(@href, "/bill.doc")) and'
                                    ' not(contains(@href, "/LM.pdf"))]')

        for version_link in other_versions:
            source_url = version_link.attrib['href']
            if source_url.endswith('.doc'):
                mimetype = 'application/msword'
            elif source_url.endswith('.pdf'):
                mimetype = 'application/pdf'

            version_title = version_link.xpath('text()')[0]
            bill.add_version_link(
                version_title, source_url, media_type=mimetype)

        # LM is "Locally Mandated fiscal impact"
        fiscal_notes = page.xpath('//a[contains(@href, "/LM.pdf")]')
        for fiscal_note in fiscal_notes:
            source_url = fiscal_note.attrib['href']
            if source_url.endswith('.doc'):
                mimetype = 'application/msword'
            elif source_url.endswith('.pdf'):
                mimetype = 'application/pdf'

            bill.add_document_link(
                "Fiscal Note", source_url, media_type=mimetype)

        for link in page.xpath("//a[contains(@href, 'legislator/')]"):
            bill.add_sponsorship(link.text.strip(), classification='primary',
                                 entity_type='person', primary=True)

        for line in actions:
            line_actions = line.strip().split(';')

            for index, action in enumerate(line_actions):
                action = action.strip()
                if not action:
                    continue

                action_date_text = line.split('-')[0].strip()
                if self._is_post_2016:
                    action_date_string = action_date_text.replace(',', '')
                else:
                    action_date_string = '{} {}'.format(
                        action_date_text, session[0:4])

                # This patch is super hacky, but allows us to better
                # capture actions that screw up the formatting such as
                # veto document links.
                try:
                    action_date = datetime.datetime.strptime(
                        action_date_string, '%b %d %Y')
                    cached_action_date = action_date
                    used_cached_action_date = False
                except ValueError:
                    action_date = cached_action_date
                    used_cached_action_date = True

                # Separate out theif first action on the line.
                if index == 0 and not used_cached_action_date:
                    action = '-'.join(action.split('-')[1:]).strip()
                    if not action:
                        continue

                if action.endswith('House') or action.endswith('(H)'):
                    actor = 'lower'
                elif action.endswith('Senate') or action.endswith('(S)'):
                    actor = 'upper'
                else:
                    actor = chamber

                # For chamber passage,
                # the only way to determine chamber correctly is
                # how many total people voted on it
                if action.startswith('3rd reading'):
                    votes = re.search(r'(\d+)\-(\d+)', action)
                    if votes:
                        yeas = int(votes.groups(1)[0])
                        nays = int(votes.groups(1)[1])
                        # 50 is the quorum for the house,
                        # and more than the number of senators
                        if yeas + nays > 50:
                            actor = 'lower'
                        elif (yeas + nays > 20) and (yeas + nays < 50):
                            actor = 'upper'

                atype = []
                if 'introduced in' in action:
                    atype.append('introduction')
                    if 'to ' in action:
                        atype.append('referral-committee')
                elif 'Prefiled by' in action:
                    atype.append('filing')
                elif 'signed by Governor' in action:
                    atype.append('executive-signature')
                elif 'vetoed' in action:
                    atype.append('executive-veto')

                    # Get the accompanying veto message document. There
                    # should only be one.
                    veto_document_link = self.get_node(
                        page, '//div[@class="StandardText leftDivMargin"]/'
                        'div[@class="StandardText"][last()]/a[contains(@href,'
                        '"veto.pdf")]')

                    if veto_document_link is not None:
                        bill.add_document_link("Veto Message",
                                               veto_document_link.attrib['href'],
                                               on_duplicate='ignore')
                elif re.match(r'^to [A-Z]', action):
                    atype.append('referral-committee')
                elif action == 'adopted by voice vote':
                    atype.append('passage')

                if '1st reading' in action:
                    atype.append('reading-1')
                if '3rd reading' in action:
                    atype.append('reading-3')
                    if 'passed' in action:
                        atype.append('passage')
                if '2nd reading' in action:
                    atype.append('reading-2')
                if 'delivered to secretary of state' in action.lower():
                    atype.append('became-law')

                if 'veto overridden' in action.lower():
                    atype.append('veto-override-passage')

                if 'R' in bill_id and 'adopted by voice vote' in action:
                    atype.append('passage')

                amendment_re = (r'floor amendments?( \([a-z\d\-]+\))*'
                                r'( and \([a-z\d\-]+\))? filed')
                if re.search(amendment_re, action):
                    atype.append('amendment-introduction')

                if not atype:
                    atype = None

                # Capitalize the first letter of the action for nicer
                # display. capitalize() won't work for this because it
                # lowercases all other letters.
                action = (action[0].upper() + action[1:])

                action_date = timezone(
                    'America/Kentucky/Louisville').localize(action_date)
                action_date = action_date.strftime('%Y-%m-%d')

                if action:
                    bill.add_action(action, action_date,
                                    chamber=actor, classification=atype)

        try:
            votes_link = page.xpath(
                "//a[contains(@href, 'vote_history.pdf')]")[0]
            bill.add_document_link("Vote History", votes_link.attrib['href'])
        except IndexError:
            # No votes
            self.logger.warning(u'No votes found for {}'.format(title))
            pass

        # Ugly Hack Alert!
        # find actions before introduction date and subtract 1 from the year
        # if the date is after introduction
        intro_date = None

        for i, action in enumerate(bill.actions):
            if 'introduction' in action['classification']:
                intro_date = action['date']
                break
            for action in bill.actions[:i]:
                if action['date'] > intro_date:
                    action['date'] = action['date'].replace(
                        year=action['date'].year-1)
                    self.debug('corrected year for %s', action['action'])

        yield bill
