import re
import datetime
from collections import defaultdict
import lxml.html
from billy.scrape.bills import BillScraper, Bill
from openstates.utils import LXMLMixin


def chamber_abbr(chamber):
    if chamber == 'upper':
        return 'S'
    else:
        return 'H'


def session_url(session):
    return "http://www.lrc.ky.gov/record/%s/" % session[2:]


class KYBillScraper(BillScraper, LXMLMixin):
    jurisdiction = 'ky'

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

    def scrape(self, chamber, session):
        # Bill page markup changed starting with the 2016 regular session.
        if (self.metadata['session_details'][session]['start_date'] >=
            self.metadata['session_details']['2016RS']['start_date']):
            self._is_post_2016 = True

        self.scrape_subjects(session)
        self.scrape_session(chamber, session)
        for sub in self.metadata['session_details'][session].get('sub_sessions', []):
            self.scrape_session(chamber, sub)

    def scrape_session(self, chamber, session):
        bill_url = session_url(session) + "bills_%s.htm" % chamber_abbr(chamber)
        self.scrape_bill_list(chamber, session, bill_url)

        resolution_url = session_url(session) + "res_%s.htm" % (
            chamber_abbr(chamber))
        self.scrape_bill_list(chamber, session, resolution_url)

    def scrape_bill_list(self, chamber, session, url):
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

                self.parse_bill(chamber, session, bill_id,
                    link.attrib['href'])

    def parse_bill(self, chamber, session, bill_id, url):
        page = self.lxmlize(url)

        short_bill_id = re.sub(r'(H|S)([JC])R', r'\1\2', bill_id)
        version_link_node = self.get_node(
            page,
            '//a[contains(@href, "{bill_id}/bill.doc") or contains(@href,'
            '"{bill_id}/bill.pdf")]'.format(bill_id=short_bill_id))

        if version_link_node is None:
            # Bill withdrawn
            self.logger.warning('Bill withdrawn.')
            return
        else:
            source_url = version_link_node.attrib['href']

            if source_url.endswith('.doc'):
                mimetype='application/msword'
            elif source_url.endswith('.pdf'):
                mimetype='application/pdf'

        if self._is_post_2016:
            title_texts = self.get_nodes(
                page,
                '//div[@class="StandardText leftDivMargin"]/text()')
            title_texts = filter(None, [text.strip() for text in title_texts])\
                [1:]
            title_texts = [s for s in title_texts if s != ',']
            title = ' '.join(title_texts)

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
                    self.warning('walking backwards to get bill title, error prone!')
                    title = pars[0].getprevious().getprevious()
                    while not title.tail:
                        title = title.getprevious()
                    title = title.tail
                    self.warning('got title the dangerous way: %s' % title)
                action_p = pars[0]

            title = re.sub(ur'[\s\xa0]+', ' ', title).strip()
            actions = action_p.xpath("string()").split("\n")

        if 'CR' in bill_id:
            bill_type = 'concurrent resolution'
        elif 'JR' in bill_id:
            bill_type = 'joint resolution'
        elif 'R' in bill_id:
            bill_type = 'resolution'
        else:
            bill_type = 'bill'

        bill = Bill(session, chamber, bill_id, title, type=bill_type)
        bill['subjects'] = self._subjects[bill_id]
        bill.add_source(url)

        bill.add_version("Most Recent Version",
            source_url,
            mimetype=mimetype)

        for link in page.xpath("//a[contains(@href, 'legislator/')]"):
            bill.add_sponsor('primary', link.text.strip())

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
                    action_date_string = '{} {}'.format(action_date_text,
                        session[0:4])

                # This patch is super hacky, but allows us to better
                # capture actions that screw up the formatting such as
                # veto document links.
                try:
                    action_date = datetime.datetime.strptime(
                        action_date_string, '%b %d %Y')
                    cached_action_date = action_date
                    used_cached_action_date = False
                except:
                    action_date = cached_action_date
                    used_cached_action_date = True

                # Separate out the date if first action on the line.
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

                atype = []
                if 'introduced in' in action:
                    atype.append('bill:introduced')
                    if 'to ' in action:
                        atype.append('committee:referred')
                elif 'signed by Governor' in action:
                    atype.append('governor:signed')
                elif 'vetoed' in action:
                    atype.append('governor:vetoed')

                    # Get the accompanying veto message document. There
                    # should only be one.
                    veto_document_link = self.get_node(page,
                        '//div[@class="StandardText leftDivMargin"]/'
                        'div[@class="StandardText"][last()]/a[contains(@href,'
                        '"veto.pdf")]')

                    if veto_document_link is not None:
                        bill.add_document("Veto Message",
                            veto_document_link.attrib['href'])
                elif re.match(r'^to [A-Z]', action):
                    atype.append('committee:referred')
                elif action == 'adopted by voice vote':
                    atype.append('bill:passed')

                if '1st reading' in action:
                    atype.append('bill:reading:1')
                if '3rd reading' in action:
                    atype.append('bill:reading:3')
                    if 'passed' in action:
                        atype.append('bill:passed')
                if '2nd reading' in action:
                    atype.append('bill:reading:2')

                if 'R' in bill_id and 'adopted by voice vote' in action:
                    atype.append('bill:passed')

                amendment_re = (r'floor amendments?( \([a-z\d\-]+\))*'
                                r'( and \([a-z\d\-]+\))? filed')
                if re.search(amendment_re, action):
                    atype.append('amendment:introduced')

                if not atype:
                    atype = ['other']

                # Capitalize the first letter of the action for nicer
                # display. capitalize() won't work for this because it
                # lowercases all other letters.
                action = (action[0].upper() + action[1:])

                if action:
                    bill.add_action(actor, action, action_date, type=atype)

        try:
            votes_link = page.xpath(
                "//a[contains(@href, 'vote_history.pdf')]")[0]
            bill.add_document("Vote History",
                votes_link.attrib['href'])
        except IndexError:
            # No votes
            self.logger.warning(u'No votes found for {}'.format(title))
            pass

        # Ugly Hack Alert!
        # find actions before introduction date and subtract 1 from the year
        # if the date is after introduction
        intro_date = None
        for i, action in enumerate(bill['actions']):
            if 'bill:introduced' in action['type']:
                intro_date = action['date']
                break
            for action in bill['actions'][:i]:
                if action['date'] > intro_date:
                    action['date'] = action['date'].replace(year=action['date'].year-1)
                    self.debug('corrected year for %s', action['action'])

        self.save_bill(bill)
