import re
import datetime

import lxml.html
from pupa.scrape import Scraper, Bill, VoteEvent

from pupa.utils.generic import convert_pdf

CHAMBERS = {
    'upper': ('SB', 'SJ'),
    'lower': ('HB', 'HJ'),
}

classifiers = {
    r'Committee Amendment .+? Adopted': 'amendment-passage',
    r'Favorable': 'committee-passage-favorable',
    r'First Reading': 'referral-committee',
    r'Floor (Committee )?Amendment\s?\(.+?\)$': 'amendment-introduction',
    r'Floor Amendment .+? Rejected': 'amendment-failure',
    r'Floor (Committee )?Amendment.+?Adopted': 'amendment-passage',
    r'Floor Amendment.+? Withdrawn': 'amendment-withdrawal',
    r'Pre\-filed': 'introduction',
    r'Withdrawn': 'withdrawal',
    r'Re\-(referred|assigned)': 'referral-committee',
    r'Recommit to Committee': 'referral-committee',
    r'Referred': 'referral-committee',
    r'Third Reading Passed': 'passage',
    r'Third Reading Failed': 'failure',
    r'Unfavorable': 'committee-passage-unfavorable',
    r'Vetoed': 'executive-veto',
    r'Gubernatorial Veto Override': 'veto-override-passage',
    r'Veto overridden': 'veto-override-passage',
    r'Approved by the Governor': 'executive-signature',
}

vote_classifiers = {
    r'third': 'passage',
    r'fla|amend|amd': 'amendment',
}


def _classify_action(action):
    if not action:
        return None

    ctty = None

    for regex, type in classifiers.items():
        if re.match(regex, action):
            if 'referral-committee' in type:
                ctty = re.sub(regex, "", action).strip()
            return (type, ctty)
    return (None, ctty)


def _clean_sponsor(name):
    if name.startswith('Delegate') or name.startswith('Senator'):
        name = name.split(' ', 1)[1]
    if ', District' in name:
        name = name.rsplit(',', 1)[0]
    return name.strip().strip('*')


def _get_td(doc, th_text):
    td = doc.xpath('//th[text()="%s"]/following-sibling::td' % th_text)
    if td:
        return td[0]
    td = doc.xpath('//th/span[text()="%s"]/../following-sibling::td' % th_text)
    if td:
        return td[0]


class MDBillScraper(Scraper):
    def parse_bill_sponsors(self, doc, bill):
        sponsor_list = doc.xpath('//a[@name="Sponlst"]')
        if sponsor_list:
            # more than one bill sponsor exists
            elems = sponsor_list[0].xpath('../../..//dd/a')
            for elem in elems:
                bill.add_sponsorship(
                    _clean_sponsor(elem.text.strip()),
                    entity_type='person',
                    classification='cosponsor',
                    primary=False,
                )
        else:
            # single bill sponsor
            sponsor = doc.xpath('//a[@name="Sponsors"]/../../dd')[0].text_content()
            bill.add_sponsorship(
                _clean_sponsor(sponsor),
                entity_type='person',
                classification='primary',
                primary=True,
            )

    def parse_bill_actions(self, doc, bill):
        for h5 in doc.xpath('//h5'):
            if h5.text == 'House Action':
                chamber = 'lower'
            elif h5.text == 'Senate Action':
                chamber = 'upper'
            elif h5.text.startswith('Action after passage'):
                chamber = 'governor'
            else:
                break
            dts = h5.getnext().xpath('dl/dt')
            for dt in dts:
                action_date = dt.text.strip()
                if action_date and action_date != 'No Action':
                    year = int(bill.legislative_session[:4])
                    action_date += ('/%s' % year)
                    action_date = datetime.datetime.strptime(action_date,
                                                             '%m/%d/%Y')

                    # no actions after June?, decrement the year on these
                    if action_date.month > 6:
                        year -= 1
                        action_date = action_date.replace(year)

                    # iterate over all dds following the dt
                    dcursor = dt
                    while (dcursor.getnext() is not None and
                           dcursor.getnext().tag == 'dd'):
                        dcursor = dcursor.getnext()
                        actions = dcursor.text_content().split('\r\n')
                        for act in actions:
                            act = act.strip()
                            if not act:
                                continue
                            atype, committee = _classify_action(act)
                            related = (
                                [{'type': 'committee', 'name': committee}]
                                if committee is not None
                                else []
                            )

                            if atype:
                                bill.add_action(
                                    chamber, act, action_date.strftime('%Y-%m-%d'),
                                    related_entities=related)
                            else:
                                self.log('unknown action: %s' % act)

    def parse_bill_documents(self, doc, bill):
        bill_text_b = doc.xpath('//b[contains(text(), "Bill Text")]')[0]
        for sib in bill_text_b.itersiblings():
            if sib.tag == 'a':
                bill.add_version_link(sib.text.strip(','), sib.get('href'),
                                      media_type='application/pdf')

        note_b = doc.xpath('//b[contains(text(), "Fiscal and Policy")]')[0]
        for sib in note_b.itersiblings():
            if sib.tag == 'a' and sib.text == 'Available':
                bill.add_document_link('Fiscal and Policy Note', sib.get('href'))

    def parse_bill_votes(self, doc, bill):
        elems = doc.xpath('//a')

        # MD has a habit of listing votes twice
        seen_votes = set()

        for elem in elems:
            href = elem.get('href')
            if (href and "votes" in href and href.endswith('htm') and href not in seen_votes):
                seen_votes.add(href)
                vote = self.parse_vote_page(href, bill)
                vote.add_source(href)
                yield vote

    def parse_bill_votes_new(self, doc, bill):
        elems = doc.xpath("//table[@class='billdocs']//a")
        # MD has a habit of listing votes twice
        seen_votes = set()

        for elem in elems:
            href = elem.get('href')
            if (href and "votes" in href and href.endswith('pdf') and
                    ("Senate" in href or "House" in href) and href not in seen_votes):
                seen_votes.add(href)
                vote = self.parse_vote_pdf(href, bill)
                vote.add_source(href)
                yield vote

    def parse_vote_pdf(self, vote_url, bill):

        filename, response = self.urlretrieve(vote_url)

        text = convert_pdf(filename, type='text').decode()
        lines = text.splitlines()

        if 'Senate' in vote_url:
            chamber = 'upper'
        else:
            chamber = 'lower'

        date_string = lines[0].split('Calendar Date:')[1].strip()
        date = datetime.datetime.strptime(date_string, "%b %d, %Y %I:%M (%p)")

        page_index = None
        for index, line in enumerate(lines):
            if 'Yeas' in line and 'Nays' in line:
                page_index = index
                break

        vote_counts = 5*[0]
        vote_types = ['yes', 'no', 'not voting', 'excused', 'absent']

        if page_index:

            counts = re.split(r'\s{2,}', lines[page_index].strip())

            for index, count in enumerate(counts):
                number, string = count.split(' ', 1)
                number = int(number)
                vote_counts[index] = number
        else:
            raise ValueError("Vote Counts Not found at %s" % vote_url)

        passed = vote_counts[0] > vote_counts[1]

        # Consent calendar votes address multiple bills in one VoteEvent
        # eg, http://mgaleg.maryland.gov/2018RS/votes/Senate/0478.pdf
        is_consent_calendar = any(['Consent Calendar' in line for line in lines[:page_index]])
        consent_calendar_bills = None
        motion = ""
        if is_consent_calendar:
            motion = re.split(r'\s{2,}', lines[page_index - 4].strip())[0]
            consent_calendar_bills = re.split(r'\s{2,}', lines[page_index-1].strip())
            assert consent_calendar_bills, "Could not find bills for consent calendar vote"

        motion_keywords = ['favorable', 'reading', 'amendment', 'motion', 'introduced',
                           'bill pass', 'committee']
        motion_lines = [3, 2, 4, 5]  # Relative LineNumbers to be checked for existence of motion

        for i in motion_lines:
            if any(motion_keyword in motion.lower() for motion_keyword in motion_keywords):
                break
            motion = re.split(r'\s{2,}', lines[page_index-i].strip())[0]
        else:
            if not any(motion_keyword in motion.lower() for motion_keyword in motion_keywords):
                # This condition covers for the bad formating in SB 1260
                motion = lines[page_index-3]
            if not any(motion_keyword in motion.lower() for motion_keyword in motion_keywords):
                # Check this one for SB 747
                motion = "No motion given"
                self.warning("No motion given")

        vote = VoteEvent(
            bill=bill,
            chamber=chamber,
            start_date=date.strftime('%Y-%m-%d'),
            motion_text=motion,
            classification='passage',
            result='pass' if passed else 'fail',
        )

        # Include bill ID to avoid duplication for consent calendars
        vote.pupa_id = '{}#{}'.format(vote_url, bill.identifier)

        for index, vote_type in enumerate(vote_types):
            vote.set_count(vote_type, vote_counts[index])
        page_index = page_index + 2

        # Keywords for identifying where names are located in the pdf
        show_stoppers = ['Voting Nay', 'Not Voting',
                         'COPY', 'Excused', 'indicates vote change',
                         'Indicates Vote Change']
        vote_index = 0

        # For matching number of names extracted with vote counts(extracted independently)
        vote_name_counts = 5*[0]

        while page_index < len(lines):

            current_line = lines[page_index].strip()

            if not current_line or 'Voting Yea' in current_line:
                page_index += 1
                continue

            if any(show_stopper in current_line for show_stopper in show_stoppers):
                page_index += 1
                vote_index = (vote_index + 1)
                continue

            names = re.split(r'\s{2,}', current_line)

            vote_name_counts[vote_index] += len(names)

            for name in names:
                vote.vote(vote_types[vote_index], name)
            page_index += 1

        if vote_counts != vote_name_counts:
            raise ValueError("Votes Count and Number of Names don't match")

        return vote

    def parse_vote_page(self, vote_url, bill):
        vote_html = self.get(vote_url).text
        doc = lxml.html.fromstring(vote_html)
        # chamber
        if 'senate' in vote_url:
            chamber = 'upper'
        else:
            chamber = 'lower'

        # date in the following format: Mar 23, 2009
        date = doc.xpath('//td[starts-with(text(), "Legislative")]')[0].text
        date = date.replace(u'\xa0', ' ')
        date = datetime.datetime.strptime(date[18:], '%b %d, %Y')

        # motion
        motion = ''.join(x.text_content() for x in
                         doc.xpath('//td[@colspan="23"]'))
        if motion == '':
            motion = "No motion given"  # XXX: Double check this. See SJ 3.
        motion = motion.replace(u'\xa0', ' ')

        # totals
        tot_class = doc.xpath('//td[contains(text(), "Yeas")]')[0].get('class')
        totals = doc.xpath('//td[@class="%s"]/text()' % tot_class)[1:]
        yes_count = int(totals[0].split()[-1])
        no_count = int(totals[1].split()[-1])
        other_count = int(totals[2].split()[-1])
        other_count += int(totals[3].split()[-1])
        other_count += int(totals[4].split()[-1])
        passed = yes_count > no_count

        vote = VoteEvent(
            bill=bill,
            chamber=chamber,
            start_date=date.strftime('%Y-%m-%d'),
            motion_text=motion,
            classification='passage',
            result='pass' if passed else 'fail',
        )
        vote.pupa_id = vote_url     # contains sequence number
        vote.set_count('yes', yes_count)
        vote.set_count('no', no_count)
        vote.set_count('other', other_count)

        # go through, find Voting Yea/Voting Nay/etc. and next tds are voters
        func = None
        for td in doc.xpath('//td/text()'):
            td = td.replace(u'\xa0', ' ')
            if td.startswith('Voting Yea'):
                func = vote.yes
            elif td.startswith('Voting Nay'):
                func = vote.no
            elif td.startswith('Not Voting'):
                func = vote.other
            elif td.startswith('Excused'):
                func = vote.other
            elif func:
                td = td.rstrip('*')
                func(td)

        return vote

    def scrape_bill_2012(self, chamber, session, bill_id, url):
        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)
        # find <a name="Title">, get parent dt, get parent dl, then dd n dl
        title = doc.xpath('//a[@name="Title"][1]/../../dd[1]/text()')[0].strip()

        summary = doc.xpath('//font[@size="3"]/p/text()')[0].strip()

        if 'B' in bill_id:
            _type = ['bill']
        elif 'J' in bill_id:
            _type = ['joint resolution']

        bill = Bill(
            bill_id,
            legislative_session=session,
            classification=_type,
            chamber=chamber,
            title=title,
        )
        bill.add_abstract(summary, note='summary')
        bill.add_source(url)

        self.parse_bill_sponsors(doc, bill)     # sponsors
        self.parse_bill_actions(doc, bill)      # actions
        self.parse_bill_documents(doc, bill)    # documents and versions
        yield from self.parse_bill_votes(doc, bill)        # votes

        # subjects
        subjects = []
        for subj in doc.xpath('//a[contains(@href, "/subjects/")]'):
            subjects.append(subj.text.split('-see also-')[0])
        bill.subject = subjects

        # add bill to collection
        self.save_bill(bill)

    def scrape_bill(self, chamber, session, bill_id, url):
        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)
        try:
            title = doc.xpath('//h3[@class="h3billright"]')[0].text_content()
            # TODO: grab summary (none present at time of writing)
        except IndexError:
            if 'Unable to retrieve the requested information. Please try again' in html:
                self.warning('Soft error page, skipping.')
                return
            else:
                raise

        if 'B' in bill_id:
            _type = ['bill']
        elif 'J' in bill_id:
            _type = ['joint resolution']
        else:
            raise ValueError('unknown bill type ' + bill_id)

        bill = Bill(
            bill_id, legislative_session=session, chamber=chamber, title=title,
            classification=_type)
        bill.add_source(url)

        # process sponsors
        sponsors = _get_td(doc, 'All Sponsors:').text_content()
        sponsors = sponsors.replace('Delegates ', '')
        sponsors = sponsors.replace('Delegate ', '')
        sponsors = sponsors.replace('Senator ', '')
        sponsors = sponsors.replace('Senators ', '')
        sponsor_type = 'primary'

        for sponsor in re.split(', (?:and )?', sponsors):
            sponsor = sponsor.strip()
            if not sponsor:
                continue
            bill.add_sponsorship(
                sponsor,
                sponsor_type,
                primary=sponsor_type == 'primary',
                entity_type='person',
            )
            sponsor_type = 'cosponsor'

        # subjects
        subject_list = []
        for heading in ('Broad Subject(s):', 'Narrow Subject(s):'):
            subjects = _get_td(doc, heading).xpath('a/text()')
            subject_list += [s.split(' -see also-')[0] for s in subjects if s]
        bill.subject = subject_list

        html = self.get(url.replace('stab=01', 'stab=02')).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        # documents
        self.scrape_documents(bill, doc)
        # actions
        self.scrape_actions(bill, url.replace('stab=01', 'stab=03'))
        yield from self.parse_bill_votes_new(doc, bill)
        yield bill

    def scrape_documents(self, bill, doc):
        for td in doc.xpath('//table[@class="billdocs"]//td'):
            a = td.xpath('a')[0]
            description = td.xpath('text()')
            if description:
                description = self.remove_leading_dash(description[0])
            whole = ''.join(td.itertext())

            if a.text == 'Text':
                bill.add_version_link('Bill Text', a.get('href'),
                                      media_type='application/pdf')
            elif a.text == 'Reprint':
                bill.add_version_link(description, a.get('href'),
                                      media_type='application/pdf')
            elif a.text == 'Report':
                bill.add_document_link(description, a.get('href'),
                                       media_type='application/pdf')
            elif a.text == 'Analysis':
                bill.add_document_link(a.tail.replace(' - ', ' ').strip(),
                                       a.get('href'), media_type='application/pdf')
            elif a.text in ('Bond Bill Fact Sheet',
                            "Attorney General's Review Letter",
                            "Governor's Veto Letter",
                            "Joint Chairmen's Report",
                            "Conference Committee Summary Report"):
                bill.add_document_link(a.text, a.get('href'),
                                       media_type='application/pdf')
            elif a.text in ('Amendments', 'Conference Committee Amendment',
                            'Conference Committee Report'):
                bill.add_document_link(whole,
                                       a.get('href'), media_type='application/pdf')
            elif a.text == 'Vote - Senate - Committee':
                bill.add_document_link('Senate %s Committee Vote' %
                                       a.tail.replace(' - ', ' ').strip(),
                                       a.get('href'), media_type='application/pdf')
            elif a.text == 'Vote - House - Committee':
                bill.add_document_link('House %s Committee Vote' %
                                       a.tail.replace(' - ', ' ').strip(),
                                       a.get('href'), media_type='application/pdf')
            elif a.text == 'Vote - Senate Floor':
                # TO DO: Re-write vote scraping
                # See details on https://github.com/openstates/openstates/issues/2093
                pass
            elif a.text == 'Vote - House Floor':
                pass
            else:
                raise ValueError('unknown document type: %s', a.text)

    def scrape_actions(self, bill, url):
        html = self.get(url).text
        doc = lxml.html.fromstring(html)
        doc.make_links_absolute(url)

        for row in doc.xpath('//table[@class="billgrid"]/tr')[1:]:
            new_chamber, cal_date, _leg_date, action, _proceedings = row.xpath('td')

            if new_chamber.text == 'Senate':
                chamber = 'upper'
            elif new_chamber.text == 'House':
                chamber = 'lower'
            elif new_chamber.text == 'Post Passage':
                chamber = 'executive'
            elif new_chamber.text is not None:
                raise ValueError('unexpected chamber: ' + new_chamber.text)

            action = action.text
            if cal_date.text:
                action_date = datetime.datetime.strptime(cal_date.text, '%m/%d/%Y')

            atype, committee = _classify_action(action)
            related = (
                [{'type': 'committee', 'name': committee}]
                if committee is not None
                else []
            )

            bill.add_action(
                action, action_date.strftime('%Y-%m-%d'), chamber=chamber, classification=atype,
                related_entities=related)

    def remove_leading_dash(self, string):
        string = string[3:] if string.startswith(' - ') else string
        return string.strip()

    def scrape(self, chamber=None, session=None):
        if session is None:
            session = self.latest_session()
            self.info('no session specified, using %s', session)
        chambers = [chamber] if chamber is not None else ['upper', 'lower']
        for chamber in chambers:
            yield from self.scrape_chamber(chamber, session)

    def scrape_chamber(self, chamber, session):
        session_slug = session if 's' in session else session + 'rs'

        main_page = (
            'http://mgaleg.maryland.gov/webmga/frmLegislation.aspx?pid=legisnpage&'
            'tab=subject3&ys=' + session_slug
        )
        chamber_prefix = 'S' if chamber == 'upper' else 'H'
        html = self.get(main_page).text
        doc = lxml.html.fromstring(html)

        ranges = doc.xpath('//table[@class="box1leg"]//td/text()')
        for range_text in ranges:
            match = re.match(r'(\w{2})0*(\d+) - \wB0*(\d+)', range_text.strip())
            if match:
                prefix, begin, end = match.groups()
                if prefix[0] == chamber_prefix:
                    self.debug('scraping %ss %s-%s', prefix, begin, end)
                    for number in range(int(begin), int(end) + 1):
                        bill_id = prefix + str(number)
                        url = (
                            'http://mgaleg.maryland.gov/webmga/frmMain.aspx?id=%s&stab=01&'
                            'pid=billpage&tab=subject3&ys=%s'
                        ) % (bill_id, session_slug)
                        if session < '2013':
                            yield from self.scrape_bill_2012(chamber, session, bill_id, url)
                        else:
                            yield from self.scrape_bill(chamber, session, bill_id, url)
